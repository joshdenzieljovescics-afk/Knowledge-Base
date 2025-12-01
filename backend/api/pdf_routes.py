"""PDF upload and management routes."""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional
import uuid
import io
from datetime import datetime
from pydantic import BaseModel

from config import Config
from middleware.jwt_middleware import get_current_user
from services.pdf_service import PDFService


# Response models for PDF routes
class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    uploaded_at: str
    chunk_count: int = 0
    file_size: int = 0
    status: str = "unknown"
    storage_location: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


# Constants
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

pdf_router = APIRouter(prefix="/pdf", tags=["PDF Management"])
pdf_service = PDFService()


@pdf_router.post("/upload", response_model=DocumentResponse)
async def upload_pdf(
    file: UploadFile = File(...), current_user: dict = Depends(get_current_user)
):
    """
    Upload a PDF document.

    Works in both local and Lambda environments:
    - Local: Saves to filesystem
    - Lambda: Uploads to S3
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed"
        )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size
    if file_size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_UPLOAD_SIZE / (1024*1024)}MB",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file"
        )

    document_id = str(uuid.uuid4())
    user_id = current_user.get("user_id", current_user.get("sub", "anonymous"))

    try:
        if Config.IS_LAMBDA:
            # Lambda: Upload to S3 and store metadata in DynamoDB
            from utils.s3_storage import get_s3_storage
            from database.dynamodb_adapter import get_dynamodb_adapter

            s3_storage = get_s3_storage()
            db_adapter = get_dynamodb_adapter()

            # Upload to S3
            s3_key = s3_storage.upload_file(
                file_data=file_content,
                filename=file.filename,
                content_type="application/pdf",
                metadata={
                    "document_id": document_id,
                    "user_id": user_id,
                    "original_filename": file.filename,
                },
            )

            # Process PDF and create chunks
            chunks = await pdf_service.process_pdf(
                pdf_content=file_content,
                document_id=document_id,
                filename=file.filename,
                user_id=user_id,
            )

            # Store metadata in DynamoDB
            doc_record = db_adapter.create_document(
                document_id=document_id,
                filename=file.filename,
                user_id=user_id,
                s3_key=s3_key,
                chunk_count=len(chunks),
                file_size=file_size,
                metadata={
                    "content_type": "application/pdf",
                    "processing_status": "completed",
                },
            )

            return DocumentResponse(
                document_id=document_id,
                filename=file.filename,
                uploaded_at=doc_record["uploaded_at"],
                chunk_count=len(chunks),
                file_size=file_size,
                status="processed",
                storage_location=f"s3://{s3_storage.bucket}/{s3_key}",
            )

        else:
            # Local: Save to filesystem
            import os

            file_path = os.path.join(Config.UPLOAD_DIR, f"{document_id}.pdf")
            with open(file_path, "wb") as f:
                f.write(file_content)

            # Process PDF
            chunks = await pdf_service.process_pdf(
                pdf_content=file_content,
                document_id=document_id,
                filename=file.filename,
                user_id=user_id,
            )

            # Store in local SQLite database (your existing logic)
            # TODO: Add your existing database storage logic here

            return DocumentResponse(
                document_id=document_id,
                filename=file.filename,
                uploaded_at=datetime.utcnow().isoformat(),
                chunk_count=len(chunks),
                file_size=file_size,
                status="processed",
                storage_location=f"file://{file_path}",
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}",
        )


@pdf_router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_user: dict = Depends(get_current_user), limit: int = 100
):
    """
    List all documents for the current user.
    """
    user_id = current_user.get("user_id", current_user.get("sub", "anonymous"))

    try:
        if Config.IS_LAMBDA:
            from database.dynamodb_adapter import get_dynamodb_adapter

            db_adapter = get_dynamodb_adapter()
            documents = db_adapter.list_user_documents(user_id=user_id, limit=limit)

            return DocumentListResponse(
                documents=[
                    DocumentResponse(
                        document_id=doc["document_id"],
                        filename=doc["filename"],
                        uploaded_at=doc["uploaded_at"],
                        chunk_count=doc.get("chunk_count", 0),
                        file_size=doc.get("file_size", 0),
                        status=doc.get("status", "unknown"),
                        storage_location=f"s3://{doc['s3_key']}",
                    )
                    for doc in documents
                ],
                total=len(documents),
            )
        else:
            # Local: Query SQLite database
            # TODO: Add your existing database query logic
            return DocumentListResponse(documents=[], total=0)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@pdf_router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Get document details by ID.
    """
    try:
        if Config.IS_LAMBDA:
            from database.dynamodb_adapter import get_dynamodb_adapter

            db_adapter = get_dynamodb_adapter()
            doc = db_adapter.get_document(document_id)
            if not doc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
                )

            # Verify user owns document
            user_id = current_user.get("user_id", current_user.get("sub", "anonymous"))
            if doc["user_id"] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
                )

            return DocumentResponse(
                document_id=doc["document_id"],
                filename=doc["filename"],
                uploaded_at=doc["uploaded_at"],
                chunk_count=doc.get("chunk_count", 0),
                file_size=doc.get("file_size", 0),
                status=doc.get("status", "unknown"),
                storage_location=f"s3://{doc['s3_key']}",
            )
        else:
            # Local: Query SQLite
            # TODO: Add your existing logic
            raise HTTPException(
                status_code=404, detail="Not implemented for local mode"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}",
        )


@pdf_router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Download a PDF document.

    Returns a presigned URL in Lambda, or streams file directly in local mode.
    """
    try:
        if Config.IS_LAMBDA:
            from database.dynamodb_adapter import get_dynamodb_adapter
            from utils.s3_storage import get_s3_storage

            db_adapter = get_dynamodb_adapter()
            s3_storage = get_s3_storage()

            # Get document metadata
            doc = db_adapter.get_document(document_id)

            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")

            # Verify ownership
            user_id = current_user.get("user_id", current_user.get("sub", "anonymous"))
            if doc["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Increment download counter
            db_adapter.increment_document_downloads(document_id)

            # Generate presigned URL (valid for 1 hour)
            download_url = s3_storage.generate_presigned_url(
                s3_key=doc["s3_key"], expiration=3600
            )

            return {
                "download_url": download_url,
                "expires_in": 3600,
                "filename": doc["filename"],
            }

        else:
            # Local: Stream file directly
            import os

            file_path = os.path.join(Config.UPLOAD_DIR, f"{document_id}.pdf")
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")

            def iter_file():
                with open(file_path, "rb") as f:
                    yield from f

            return StreamingResponse(
                iter_file(),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={document_id}.pdf"
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download document: {str(e)}",
        )


@pdf_router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Delete a document and its chunks from vector database.
    """
    try:
        if Config.IS_LAMBDA:
            from database.dynamodb_adapter import get_dynamodb_adapter
            from utils.s3_storage import get_s3_storage

            db_adapter = get_dynamodb_adapter()
            s3_storage = get_s3_storage()

            # Get document
            doc = db_adapter.get_document(document_id)

            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")

            # Verify ownership
            user_id = current_user.get("user_id", current_user.get("sub", "anonymous"))
            if doc["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Delete from S3
            s3_storage.delete_file(doc["s3_key"])

            # Delete from vector database
            await pdf_service.delete_document_chunks(document_id)

            # Delete from DynamoDB
            db_adapter.delete_document(document_id)

            return {
                "message": "Document deleted successfully",
                "document_id": document_id,
            }

        else:
            # Local: Delete from filesystem and database
            import os

            file_path = os.path.join(Config.UPLOAD_DIR, f"{document_id}.pdf")
            if os.path.exists(file_path):
                os.remove(file_path)

            # Delete from vector database
            await pdf_service.delete_document_chunks(document_id)

            # TODO: Delete from SQLite

            return {
                "message": "Document deleted successfully",
                "document_id": document_id,
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )
