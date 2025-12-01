"""Knowledge base API endpoints."""

import os
import glob
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from database.operations import (
    insert_document,
    replace_document,
    delete_document_and_chunks,
)
from services.weaviate_service import query_weaviate
from middleware.security_middleware import (
    validate_string_length,
    sanitize_filename,
    MAX_QUERY_LENGTH,
    MAX_FILENAME_LENGTH,
)
import traceback

kb_router = APIRouter(prefix="/kb", tags=["knowledge-base"])


# Request models with validation
class UploadToKBRequest(BaseModel):
    chunks: List[Dict[str, Any]] = Field(..., min_length=1, max_length=10000)
    document_metadata: Dict[str, Any] = Field(default_factory=dict)
    source_filename: str = Field(..., min_length=1, max_length=MAX_FILENAME_LENGTH)
    content_hash: Optional[str] = Field(
        None, description="SHA256 hash of file content for duplicate detection"
    )
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    force_replace: bool = Field(
        False, description="If true, replace existing document with same filename"
    )

    @field_validator("source_filename")
    @classmethod
    def validate_filename(cls, v):
        if not v or not v.strip():
            raise ValueError("Filename cannot be empty")
        return sanitize_filename(v)

    @field_validator("chunks")
    @classmethod
    def validate_chunks(cls, v):
        if not v:
            raise ValueError("At least one chunk is required")
        if len(v) > 10000:
            raise ValueError("Maximum 10000 chunks allowed per document")
        return v


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    limit: Optional[int] = Field(5, ge=1, le=100)
    generate_answer: Optional[bool] = True

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return validate_string_length(v.strip(), MAX_QUERY_LENGTH, "query")


def _get_document_database():
    """Lazy getter for DocumentDatabase to avoid circular imports."""
    from config import get_documents_db

    return get_documents_db()


@kb_router.post("/upload-to-kb")
async def upload_to_kb(
    request: UploadToKBRequest, authorization: Optional[str] = Header(None)
):
    """
    Upload processed chunks to knowledge base and save metadata to document database.

    IMPORTANT: Duplicate detection happens in /pdf/parse-pdf endpoint to save parsing costs.
    This endpoint focuses on uploading pre-validated chunks to Weaviate and tracking in local database.

    Expects JSON body with:
    - chunks: list of chunk objects (required)
    - document_metadata: document metadata dict
    - source_filename: name of source PDF (required)
    - content_hash: SHA256 hash (saved to local DB only)
    - file_size_bytes: file size in bytes (saved to local DB only)
    - force_replace (optional): if true, replace existing document

    Returns success status and document ID.
    """
    # DEBUG: Log what we received
    print(f"[DEBUG] Upload request received:")
    print(f"[DEBUG] - source_filename: {request.source_filename}")
    print(f"[DEBUG] - content_hash: {request.content_hash}")
    print(f"[DEBUG] - file_size_bytes: {request.file_size_bytes}")
    print(f"[DEBUG] - chunks count: {len(request.chunks)}")
    print(f"[DEBUG] - force_replace: {request.force_replace}")

    if not request.chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No chunks provided"
        )

    # Extract user from JWT token
    uploaded_by = None  # Will be set if token is valid

    if authorization:
        try:
            token = authorization.replace("Bearer ", "")

            # Google OAuth uses RS256, not HS256, so we need to decode WITHOUT verification
            # The token was already verified by the auth server
            import jwt as jose_jwt

            payload = jose_jwt.decode(token, options={"verify_signature": False})

            # Extract name from JWT payload
            uploaded_by = payload.get("name") or payload.get("email")

            if uploaded_by:
                print(f"[DEBUG] ✅ Successfully extracted uploaded_by: {uploaded_by}")
                print(f"[DEBUG] JWT payload keys: {list(payload.keys())}")
            else:
                print(f"[WARNING] ⚠️ JWT payload missing 'name' and 'email' fields")
                print(f"[WARNING] Available fields: {list(payload.keys())}")

        except Exception as e:
            print(f"[WARNING] ⚠️ Failed to decode JWT token: {str(e)}")
            uploaded_by = None
    else:
        print(f"[WARNING] ⚠️ No authorization header provided")

    # Final check - if still None, we have a problem
    if not uploaded_by:
        print(f"[ERROR] ❌ Could not extract user information from JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid JWT token with user information.",
        )

    try:
        doc_db = _get_document_database()

        # Check if document already exists in our database
        existing_doc = doc_db.check_duplicate_by_filename(request.source_filename)

        if existing_doc and not request.force_replace:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "duplicate_filename",
                    "message": f"Document '{request.source_filename}' already exists in database.",
                    "existing_doc": existing_doc,
                    "suggestion": "Set force_replace=true to overwrite the existing document.",
                },
            )

        # Prepare file metadata for Weaviate Document collection (minimal fields only)
        file_metadata = {
            "file_name": request.source_filename,
            "page_count": request.document_metadata.get("total_pages", 0)
            or max(
                (chunk.get("metadata", {}).get("page", 0) for chunk in request.chunks),
                default=0,
            ),
        }
        # Add chunk_id to each chunk if not present
        for i, chunk in enumerate(request.chunks):
            if not chunk.get("id") and not chunk.get("chunk_id"):
                chunk["chunk_id"] = chunk.get(
                    "id", f"chunk-{i}-{str(uuid.uuid4())[:8]}"
                )
            elif chunk.get("id") and not chunk.get("chunk_id"):
                chunk["chunk_id"] = chunk["id"]

        # Replace or insert document in Weaviate
        if existing_doc and request.force_replace:
            # Delete from document database first
            doc_db.delete_document(existing_doc["doc_id"])
            # Delete from Weaviate
            weaviate_doc_id = existing_doc.get("doc_id")
            delete_document_and_chunks(weaviate_doc_id)
            # Insert new
            weaviate_doc_id = insert_document(file_metadata, request.chunks)
            action = "replaced"
        else:
            weaviate_doc_id = insert_document(file_metadata, request.chunks)
            action = "uploaded"

        # Save to document tracking database
        doc_id = str(uuid.uuid4())  # Separate ID for our database

        # Generate a temporary hash if not provided (use doc_id to ensure uniqueness)
        content_hash = request.content_hash or f"temp-{doc_id}"

        doc_db.insert_document(
            {
                "doc_id": doc_id,
                "file_name": request.source_filename,
                "file_size_bytes": request.file_size_bytes or 0,
                "chunks": len(request.chunks),
                "uploaded_by": uploaded_by,
                "content_hash": content_hash,
                "page_count": file_metadata["page_count"],
                "weaviate_doc_id": weaviate_doc_id,
                "metadata": request.document_metadata,
            }
        )

        print(
            f"[INFO] Successfully {action} {len(request.chunks)} chunks to knowledge base"
        )
        print(f"[INFO] Document saved to database: {doc_id}")
        print(f"[INFO] Weaviate doc_id: {weaviate_doc_id}")
        print(f"[INFO] Uploaded by: {uploaded_by or 'anonymous'}")

        return {
            "success": True,
            "message": f"Successfully {action} {len(request.chunks)} chunks to knowledge base",
            "doc_id": doc_id,
            "weaviate_doc_id": weaviate_doc_id,
            "action": action,
        }

    except HTTPException:
        # Re-raise HTTP exceptions (like 409 Conflict)
        raise
    except Exception as e:
        print(f"[ERROR] Failed to upload to knowledge base: {str(e)}")
        print(
            f"[ERROR] Request data - filename: {request.source_filename}, chunks: {len(request.chunks)}, content_hash: {request.content_hash}, file_size: {request.file_size_bytes}"
        )
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@kb_router.get("/list-kb")
async def list_kb_files(
    limit: int = 100,
    offset: int = 0,
    uploaded_by: Optional[str] = None,
    order_by: str = "upload_date",
    order_dir: str = "DESC",
    authorization: Optional[str] = Header(None),
):
    """
    List all knowledge base files from document database.

    Query params:
    - limit: Maximum number of results (default: 100)
    - offset: Number of results to skip for pagination (default: 0)
    - uploaded_by: Filter by user (optional)
    - order_by: Field to sort by (default: upload_date)
    - order_dir: Sort direction ASC/DESC (default: DESC)

    Returns list of uploaded documents with:
    - file_name: Original filename
    - upload_date: When file was uploaded
    - file_size_bytes: File size in bytes
    - chunks: Number of chunks created
    - uploaded_by: User who uploaded the file
    """
    try:
        doc_db = _get_document_database()

        # Get documents from database
        documents = doc_db.list_documents(
            limit=limit,
            offset=offset,
            uploaded_by=uploaded_by,
            order_by=order_by,
            order_dir=order_dir,
        )

        # Get total count for pagination
        total_count = doc_db.get_document_count(uploaded_by=uploaded_by)

        # Format response with human-readable file sizes
        formatted_docs = []
        for doc in documents:
            # Convert bytes to readable format
            size_bytes = doc["file_size_bytes"]
            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.2f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

            formatted_docs.append(
                {
                    "doc_id": doc["doc_id"],
                    "file_name": doc["file_name"],
                    "upload_date": doc["upload_date"],
                    "file_size_bytes": doc["file_size_bytes"],
                    "file_size_formatted": size_str,
                    "chunks": doc["chunks"],
                    "uploaded_by": doc["uploaded_by"] or "anonymous",
                    "page_count": doc.get("page_count"),
                }
            )

        return {
            "success": True,
            "total_count": total_count,
            "count": len(formatted_docs),
            "offset": offset,
            "limit": limit,
            "documents": formatted_docs,
        }

    except Exception as e:
        print(f"[ERROR] Failed to list documents: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@kb_router.post("/query")
async def query_knowledge_base(request: QueryRequest):
    """
    Query the knowledge base with a question.

    Expects JSON body with:
    - query: the question to ask (required)
    - limit: max number of results to return (optional, default: 5)
    - generate_answer: whether to generate AI answer (optional, default: True)

    Returns:
    - results: list of relevant chunks
    - answer: AI-generated answer (if generate_answer=True)
    - metadata: query metadata
    """
    if not request.query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Query text is required"
        )

    try:
        # Query the knowledge base
        result = query_weaviate(
            query_text=request.query,
            limit=request.limit,
            generate_answer=request.generate_answer,
        )

        return {
            "success": True,
            "query": request.query,
            "results": result.get("results", []),
            "answer": result.get("answer"),
            "metadata": {
                "result_count": len(result.get("results", [])),
                "generated_at": datetime.now().isoformat(),
                "limit": request.limit,
            },
        }

    except Exception as e:
        print(f"[ERROR] Query failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        )


@kb_router.delete("/delete/{doc_id}")
async def delete_document(doc_id: str, authorization: Optional[str] = Header(None)):
    """
    Delete a document from the knowledge base and local database.

    Args:
        doc_id: Document ID to delete

    Returns:
        Success message and deleted document info
    """
    try:
        doc_db = _get_document_database()

        # Get document info before deleting
        doc_info = doc_db.get_document(doc_id)

        if not doc_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{doc_id}' not found",
            )

        # Delete from Weaviate
        weaviate_doc_id = doc_info.get("weaviate_doc_id")
        if weaviate_doc_id:
            delete_document_and_chunks(weaviate_doc_id)

        # Delete from local database
        doc_db.delete_document(doc_id)

        print(f"[INFO] Successfully deleted document: {doc_id}")
        print(f"[INFO] File name: {doc_info['file_name']}")

        return {
            "success": True,
            "message": f"Successfully deleted document '{doc_info['file_name']}'",
            "deleted_doc": {
                "doc_id": doc_id,
                "file_name": doc_info["file_name"],
                "chunks": doc_info["chunks"],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to delete document: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
