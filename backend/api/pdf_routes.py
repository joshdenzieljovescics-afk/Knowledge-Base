"""PDF-related API endpoints."""
from fastapi import APIRouter, File, UploadFile, HTTPException, status, Header
from typing import Optional
from services.pdf_service import parse_and_chunk_pdf_file
from database.document_validator import calculate_file_hash
from database.document_db import DocumentDatabase
from middleware.security_middleware import (
    sanitize_filename,
    validate_file_type,
    MAX_FILE_SIZE_MB,
    ALLOWED_FILE_TYPES
)
import traceback

pdf_router = APIRouter(prefix='/pdf', tags=['pdf'])


@pdf_router.post('/parse-pdf')
async def parse_pdf(
    file: UploadFile = File(...),
    force_reparse: bool = False,
    authorization: Optional[str] = Header(None)
):
    """
    Parse PDF file and return semantic chunks with coordinates.
    
    Checks for duplicates BEFORE parsing to save processing costs.
    
    Args:
        file: PDF file upload
        force_reparse: If true, skip duplicate check and reparse anyway
        authorization: JWT token for user identification
    
    Expects multipart/form-data with 'file' field containing PDF.
    Returns JSON with chunks and metadata.
    """
    print("[DEBUG] Starting parse-pdf endpoint")
    
    # Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )
    
    # Sanitize filename
    sanitized_filename = sanitize_filename(file.filename)
    
    # Validate file type
    if not validate_file_type(sanitized_filename, ALLOWED_FILE_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Accepted types: {', '.join(ALLOWED_FILE_TYPES)}"
        )
    
    # Validate file size
    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB"
        )
    
    # Validate minimum size (empty file check)
    if len(file_bytes) < 100:  # PDFs have header, should be at least 100 bytes
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File appears to be empty or corrupted"
        )

    try:
        # Calculate content hash for duplicate detection
        content_hash = calculate_file_hash(file_bytes)
        file_size_bytes = len(file_bytes)
        
        # ==================== DUPLICATE CHECK BEFORE PARSING ====================
        # This saves expensive OpenAI API calls and processing time
        if not force_reparse:
            doc_db = DocumentDatabase()
            
            # Check by filename first (fastest)
            existing_by_name = doc_db.check_duplicate_by_filename(sanitized_filename)
            if existing_by_name:
                print(f"[DUPLICATE] Found existing file by name: {sanitized_filename}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "duplicate_filename",
                        "message": f"Document '{sanitized_filename}' has already been uploaded and parsed.",
                        "existing_doc": {
                            "doc_id": existing_by_name["doc_id"],
                            "file_name": existing_by_name["file_name"],
                            "upload_date": existing_by_name["upload_date"],
                            "chunks": existing_by_name["chunks"],
                            "file_size_bytes": existing_by_name["file_size_bytes"]
                        },
                    }
                )
            
            # Check by content hash (detects renamed duplicates)
            existing_by_hash = doc_db.check_duplicate_by_hash(content_hash)
            if existing_by_hash:
                print(f"[DUPLICATE] Found existing file by content hash (renamed): {existing_by_hash['file_name']}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "duplicate_content",
                        "message": f"This file content has already been uploaded as '{existing_by_hash['file_name']}'.",
                        "existing_doc": {
                            "doc_id": existing_by_hash["doc_id"],
                            "file_name": existing_by_hash["file_name"],
                            "upload_date": existing_by_hash["upload_date"],
                            "chunks": existing_by_hash["chunks"],
                            "file_size_bytes": existing_by_hash["file_size_bytes"]
                        },
                    }
                )
        
        # ==================== PARSE PDF ====================
        print(f"[INFO] No duplicate found or force_reparse=true. Proceeding with parsing...")
        result = parse_and_chunk_pdf_file(file_bytes, sanitized_filename)
        
        # Add content hash and file size to the result
        result['content_hash'] = content_hash
        result['file_size_bytes'] = file_size_bytes
        
        # DEBUG: Log what we're returning
        print(f"[DEBUG] Result keys: {list(result.keys())}")
        print(f"[DEBUG] content_hash: {result.get('content_hash')}")
        print(f"[DEBUG] file_size_bytes: {result.get('file_size_bytes')}")
        print(f"[DEBUG] chunks count: {len(result.get('chunks', []))}")
        
        # Note: Document will be saved to database when uploaded to KB
        print(f"[INFO] Parsing complete. Ready for upload to KB.")
        
        return result

    except HTTPException:
        # Re-raise HTTP exceptions (like 409 Conflict) without modification
        raise
    except Exception as e:
        print(f"\n[ERROR] PDF processing failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process PDF file. Please ensure the file is a valid PDF."
        )
