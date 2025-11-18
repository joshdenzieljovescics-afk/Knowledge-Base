"""API routes for the application."""
from flask import jsonify
from api.pdf_routes import pdf_bp
from api.kb_routes import kb_bp


def register_routes(app):
    """Register all route blueprints with the Flask app."""
    
    # Register blueprints
    app.register_blueprint(pdf_bp)
    app.register_blueprint(kb_bp)
    
    # Health check endpoint
    @app.route('/', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "message": "PDF Processing API is running"}), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    print("✅ All routes registered successfully")
