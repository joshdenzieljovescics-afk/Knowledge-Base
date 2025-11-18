"""Knowledge base API endpoints."""
import os
import glob
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from database.operations import insert_document
from services.weaviate_service import query_weaviate
from utils.file_utils import generate_kb_filename, save_json
import traceback

kb_bp = Blueprint('kb', __name__)


@kb_bp.route('/upload-to-kb', methods=['POST'])
def upload_to_kb():
    """
    Upload processed chunks to knowledge base.
    
    Expects JSON body with:
    - chunks: list of chunk objects
    - document_metadata: document metadata dict
    - source_filename: name of source PDF
    
    Returns success status and document ID.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    chunks = data.get('chunks', [])
    document_metadata = data.get('document_metadata', {})
    source_filename = data.get('source_filename', 'unknown.pdf')
    
    if not chunks:
        return jsonify({"error": "No chunks provided"}), 400
    
    try:
        # Prepare file metadata for the Document collection
        file_metadata = {
            "file_name": source_filename,
            "page_count": document_metadata.get('total_pages', 0) or max(
                (chunk.get('metadata', {}).get('page', 0) for chunk in chunks), 
                default=0
            )
        }
        
        # Add chunk_id to each chunk if not present
        for i, chunk in enumerate(chunks):
            if not chunk.get('id') and not chunk.get('chunk_id'):
                chunk['chunk_id'] = chunk.get('id', f"chunk-{i}-{str(uuid.uuid4())[:8]}")
            elif chunk.get('id') and not chunk.get('chunk_id'):
                chunk['chunk_id'] = chunk['id']
        
        # Use insert_document function to save to Weaviate
        doc_id = insert_document(file_metadata, chunks)
        
        # Also save to file for backup/debugging
        kb_filename = generate_kb_filename(source_filename)
        kb_entry = {
            "document_metadata": document_metadata,
            "source_filename": source_filename,
            "upload_timestamp": datetime.now().isoformat(),
            "doc_id": doc_id,
            "chunks": chunks
        }
        
        save_json(kb_entry, kb_filename)
        
        print(f"[INFO] Successfully uploaded {len(chunks)} chunks to knowledge base with doc_id: {doc_id}")
        
        return jsonify({
            "success": True, 
            "message": f"Successfully uploaded {len(chunks)} chunks to knowledge base",
            "doc_id": doc_id,
            "filename": kb_filename
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to upload to knowledge base: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "error": f"Internal server error: {str(e)}"
        }), 500


@kb_bp.route('/list-kb', methods=['GET'])
def list_kb_files():
    """
    List all knowledge base files.
    
    Returns list of uploaded KB files with metadata.
    """
    try:
        # Find all files matching the kb_*.json pattern
        kb_files = glob.glob("kb_*.json")
        # Sort by creation time (newest first)
        kb_files.sort(key=os.path.getmtime, reverse=True)
        
        # Create a list of file info
        file_list = []
        for filepath in kb_files:
            filename = os.path.basename(filepath)
            # Extract timestamp and original filename from the kb_filename
            # Example: kb_20240615_143022_sample.json
            parts = filename.replace('kb_', '').rsplit('_', 2)
            if len(parts) >= 3:
                date_str = parts[0]
                time_str = parts[1]
                orig_filename = '_'.join(parts[2:]).replace('.json', '')
                upload_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
            else:
                upload_time = "Unknown"
                orig_filename = filename.replace('kb_', '').replace('.json', '')

            file_list.append({
                "filename": filename,
                "original_filename": orig_filename,
                "upload_time": upload_time,
                "size": os.path.getsize(filepath)
            })

        return jsonify({
            "success": True,
            "files": file_list
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@kb_bp.route('/query', methods=['POST'])
def query_knowledge_base():
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
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    data = request.get_json()
    query_text = data.get('query')
    limit = data.get('limit', 5)
    generate_answer = data.get('generate_answer', True)
    
    if not query_text:
        return jsonify({"error": "Query text is required"}), 400
    
    try:
        # Query the knowledge base
        result = query_weaviate(
            query_text=query_text,
            limit=limit,
            generate_answer=generate_answer
        )
        
        return jsonify({
            "success": True,
            "query": query_text,
            "results": result.get('results', []),
            "answer": result.get('answer'),
            "metadata": {
                "result_count": len(result.get('results', [])),
                "generated_at": datetime.now().isoformat(),
                "limit": limit
            }
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Query failed: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Query failed: {str(e)}"
        }), 500
