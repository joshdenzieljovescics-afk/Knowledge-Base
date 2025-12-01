"""Configuration management for the application."""

import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    """Application configuration class."""

    # Lambda Detection
    IS_LAMBDA = os.getenv("IS_LAMBDA", "false").lower() == "true"

    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE")
    OPENAI_MODEL = "gpt-4o"
    OPENAI_MINI_MODEL = "gpt-4o-mini"
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    # Weaviate Configuration (works in both environments)
    WEAVIATE_URL = os.environ.get("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY")

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

    # Security Configuration
    ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
    ALLOWED_ORIGINS = os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")

    # Rate Limiting
    RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"

    # HTTPS/TLS (Production only)
    USE_HTTPS = os.environ.get("USE_HTTPS", "false").lower() == "true"
    SSL_CERTFILE = os.environ.get("SSL_CERTFILE")
    SSL_KEYFILE = os.environ.get("SSL_KEYFILE")

    # Processing Configuration
    BATCH_SIZE = 100
    MAX_TOKENS = 1000
    TEMPERATURE = 0.0
    TOP_M_RERANK = 10
    HYBRID_SEARCH_ALPHA = 0.5
    HYBRID_SEARCH_LIMIT = 20

    # PDF Processing Configuration
    LINE_TOLERANCE = 5
    WORD_TOLERANCE_MULTIPLIER = 0.4
    GAP_MULTIPLIER = 1.5
    MATCH_SCORE_THRESHOLD = 80
    CROSS_PAGE_LINE_WINDOW = 20

    # FastAPI Configuration
    DEBUG = True if not IS_LAMBDA else False
    PORT = 8009

    # File paths
    OUTPUT_DIR = "outputs"

    # ═══════════════════════════════════════════════════════════════
    # LAMBDA-SPECIFIC CONFIGURATION
    # ═══════════════════════════════════════════════════════════════
    if IS_LAMBDA:
        # AWS Resources
        AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")

        # S3 for PDF/file storage
        PDF_STORAGE_BUCKET = os.environ.get("PDF_STORAGE_BUCKET")

        # DynamoDB tables
        DOCUMENTS_TABLE = os.environ.get("DOCUMENTS_TABLE")
        CHAT_SESSIONS_TABLE = os.environ.get("CHAT_SESSIONS_TABLE")
        CHAT_MESSAGES_TABLE = os.environ.get("CHAT_MESSAGES_TABLE")
        DOCUMENT_VERSIONS_TABLE = os.environ.get("DOCUMENT_VERSIONS_TABLE")
    else:
        # Local development
        AWS_REGION = None
        PDF_STORAGE_BUCKET = None
        DOCUMENTS_TABLE = None
        CHAT_SESSIONS_TABLE = None
        CHAT_MESSAGES_TABLE = None
        DOCUMENT_VERSIONS_TABLE = None

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.OPENAI_API_KEY:
            from dotenv import dotenv_values

            env_vars = dotenv_values(".env")
            cls.OPENAI_API_KEY = env_vars.get("OPENAI_APIKEY")

        if not cls.OPENAI_API_KEY:
            raise RuntimeError("❌ OPENAI_API_KEY environment variable is not set!")

        if not cls.WEAVIATE_URL or not cls.WEAVIATE_API_KEY:
            raise RuntimeError("❌ Weaviate configuration is missing!")

        # Lambda-specific validation
        if cls.IS_LAMBDA:
            required_lambda_vars = [
                "PDF_STORAGE_BUCKET",
                "DOCUMENTS_TABLE",
                "CHAT_SESSIONS_TABLE",
                "CHAT_MESSAGES_TABLE",
            ]

            missing = [var for var in required_lambda_vars if not getattr(cls, var)]
            if missing:
                raise RuntimeError(
                    f"❌ Missing Lambda configuration: {', '.join(missing)}"
                )

        return True

    @classmethod
    def get_storage_info(cls):
        """Get current storage configuration for debugging."""
        return {
            "is_lambda": cls.IS_LAMBDA,
            "storage_type": "S3" if cls.IS_LAMBDA else "Local Filesystem",
            "database_type": "DynamoDB" if cls.IS_LAMBDA else "SQLite",
            "pdf_bucket": cls.PDF_STORAGE_BUCKET if cls.IS_LAMBDA else "uploads/",
            "documents_table": (
                cls.DOCUMENTS_TABLE if cls.IS_LAMBDA else "database/documents.db"
            ),
            "chat_table": (
                cls.CHAT_SESSIONS_TABLE
                if cls.IS_LAMBDA
                else "database/chat_sessions.db"
            ),
        }


# ═══════════════════════════════════════════════════════════════
# LAZY ADAPTER INITIALIZATION - NO MODULE-LEVEL IMPORTS
# ═══════════════════════════════════════════════════════════════
# These are initialized lazily when first accessed to avoid circular imports

_documents_db = None
_chat_db = None


def get_documents_db():
    """Lazy getter for documents database adapter."""
    global _documents_db
    if _documents_db is None:
        if Config.IS_LAMBDA:
            from database.dynamodb_adapter import get_documents_adapter

            _documents_db = get_documents_adapter()
            print("✅ Lambda mode: DynamoDB documents adapter initialized")
        else:
            from database.document_db import DocumentDatabase

            _documents_db = DocumentDatabase()
            print("✅ Local mode: SQLite documents adapter initialized")
    return _documents_db


def get_chat_db():
    """Lazy getter for chat database adapter."""
    global _chat_db
    if _chat_db is None:
        if Config.IS_LAMBDA:
            from database.dynamodb_chat import get_chat_adapter

            _chat_db = get_chat_adapter()
            print("✅ Lambda mode: DynamoDB chat adapter initialized")
        else:
            from database.chat_db import ChatDatabase

            _chat_db = ChatDatabase()
            print("✅ Local mode: SQLite chat adapter initialized")
    return _chat_db


# For backwards compatibility - these are now properties that call the lazy getters
# But ONLY when accessed, not at module load time
class _LazyAdapterProxy:
    """Proxy class that lazily initializes adapters on first access."""

    @property
    def documents_db(self):
        return get_documents_db()

    @property
    def chat_db(self):
        return get_chat_db()


# Create proxy instance
_adapter_proxy = _LazyAdapterProxy()

# These will raise AttributeError if accessed directly at module level during import
# Instead, use get_documents_db() and get_chat_db() functions
# Or access via: from config import get_documents_db, get_chat_db
