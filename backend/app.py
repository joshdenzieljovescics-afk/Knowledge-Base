"""
Flask application entry point for PDF processing and knowledge base system.
This file initializes the Flask app and registers all routes.
"""
from flask import Flask
from flask_cors import CORS
from api.routes import register_routes
from api.chat_routes import chat_bp
from config import Config
from database.weaviate_client import get_weaviate_client
import atexit

def create_app():
    """Create and configure the Flask application"""
    # Validate configuration at startup
    Config.validate()
    
    # Initialize Flask
    app = Flask(__name__)
    CORS(app)
    
    # Register all routes (PDF processing, KB management)
    register_routes(app)
    
    # Register chat routes
    app.register_blueprint(chat_bp)
    
    return app

def cleanup_on_exit():
    """Cleanup function to run when script exits"""
    try:
        client = get_weaviate_client()
        if client.is_connected():
            client.close()
            print("✓ Weaviate connection closed")
    except:
        pass

if __name__ == '__main__':
    # Register cleanup on exit
    atexit.register(cleanup_on_exit)
    
    app = create_app()
    
    try:
        app.run(debug=Config.DEBUG, port=Config.PORT)
    finally:
        # Ensure cleanup on normal exit
        cleanup_on_exit()
