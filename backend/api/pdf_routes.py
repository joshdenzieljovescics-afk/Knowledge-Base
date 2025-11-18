"""PDF-related API endpoints."""
from flask import Blueprint, request, jsonify
from services.pdf_service import parse_and_chunk_pdf_file
import traceback

pdf_bp = Blueprint('pdf', __name__)


@pdf_bp.route('/parse-pdf', methods=['POST'])
def parse_pdf():
    """
    Parse PDF file and return semantic chunks with coordinates.
    
    Expects multipart/form-data with 'file' field containing PDF.
    Returns JSON with chunks and metadata.
    """
    print("[DEBUG] Starting parse-pdf endpoint")
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "File is not a PDF"}), 400

    source_filename = file.filename

    try:
        file_bytes = file.read()
        result = parse_and_chunk_pdf_file(file_bytes, source_filename)
        return jsonify(result), 200

    except Exception as e:
        print(f"\n[ERROR] PDF processing failed: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
