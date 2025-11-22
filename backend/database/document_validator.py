"""Document validation and duplicate detection for knowledge base uploads."""
import hashlib
from typing import Optional, Dict, Any
from database.weaviate_client import get_weaviate_client


def calculate_file_hash(file_bytes: bytes) -> str:
    """
    Calculate SHA256 hash of file content.
    
    Args:
        file_bytes: Raw file bytes
        
    Returns:
        Hex string of SHA256 hash
    """
    return hashlib.sha256(file_bytes).hexdigest()


def check_document_exists_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    """
    Check if a document with the given filename already exists in Weaviate.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        Dictionary with document info if exists, None otherwise.
        Format: {"doc_id": str, "file_name": str, "page_count": int}
    """
    client = get_weaviate_client()
    documents = client.collections.get("Document")
    
    try:
        # Query for documents with matching filename
        response = documents.query.fetch_objects(
            filters={
                "path": ["file_name"],
                "operator": "Equal",
                "valueText": filename
            },
            limit=1
        )
        
        if response.objects and len(response.objects) > 0:
            doc = response.objects[0]
            return {
                "doc_id": str(doc.uuid),
                "file_name": doc.properties.get("file_name"),
                "page_count": doc.properties.get("page_count")
            }
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to check document by filename: {str(e)}")
        return None


def check_document_exists_by_hash(content_hash: str) -> Optional[Dict[str, Any]]:
    """
    Check if a document with the given content hash already exists in Weaviate.
    
    Note: This requires adding content_hash property to Document collection.
    
    Args:
        content_hash: SHA256 hash of file content
        
    Returns:
        Dictionary with document info if exists, None otherwise.
        Format: {"doc_id": str, "file_name": str, "content_hash": str}
    """
    client = get_weaviate_client()
    documents = client.collections.get("Document")
    
    try:
        # Query for documents with matching content hash
        response = documents.query.fetch_objects(
            filters={
                "path": ["content_hash"],
                "operator": "Equal",
                "valueText": content_hash
            },
            limit=1
        )
        
        if response.objects and len(response.objects) > 0:
            doc = response.objects[0]
            return {
                "doc_id": str(doc.uuid),
                "file_name": doc.properties.get("file_name"),
                "content_hash": doc.properties.get("content_hash")
            }
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to check document by hash: {str(e)}")
        return None


def validate_document_upload(
    filename: str,
    file_bytes: bytes,
    allow_duplicates: bool = False
) -> Dict[str, Any]:
    """
    Validate document before upload, checking for duplicates.
    
    Args:
        filename: Name of the file
        file_bytes: Raw file content
        allow_duplicates: If True, skip duplicate checks
        
    Returns:
        Dictionary with validation results:
        {
            "is_valid": bool,
            "error": str (if not valid),
            "existing_doc": dict (if duplicate found),
            "content_hash": str,
            "duplicate_type": str ("filename", "content", or None)
        }
    """
    result = {
        "is_valid": True,
        "error": None,
        "existing_doc": None,
        "content_hash": None,
        "duplicate_type": None
    }
    
    # Calculate content hash
    content_hash = calculate_file_hash(file_bytes)
    result["content_hash"] = content_hash
    
    # Skip validation if duplicates are allowed
    if allow_duplicates:
        return result
    
    # Check for filename duplicate
    existing_by_name = check_document_exists_by_filename(filename)
    if existing_by_name:
        result["is_valid"] = False
        result["duplicate_type"] = "filename"
        result["existing_doc"] = existing_by_name
        result["error"] = (
            f"Document with filename '{filename}' already exists "
            f"(doc_id: {existing_by_name['doc_id']}). "
            "Use force_replace=true to overwrite."
        )
        return result
    
    # Check for content hash duplicate
    existing_by_hash = check_document_exists_by_hash(content_hash)
    if existing_by_hash:
        result["is_valid"] = False
        result["duplicate_type"] = "content"
        result["existing_doc"] = existing_by_hash
        result["error"] = (
            f"Document with identical content already exists as '{existing_by_hash['file_name']}' "
            f"(doc_id: {existing_by_hash['doc_id']}). "
            "This appears to be a renamed duplicate."
        )
        return result
    
    return result
