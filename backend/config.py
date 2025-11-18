"""Configuration management for the application."""
import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    """Application configuration class."""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE")
    OPENAI_MODEL = "gpt-4o"
    OPENAI_MINI_MODEL = "gpt-4o-mini"
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    
    # Weaviate Configuration
    WEAVIATE_URL = os.environ.get("WEAVIATE_URL")
    WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY")
    
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
    
    # Flask Configuration
    DEBUG = True
    PORT = 8009
    
    # File paths
    OUTPUT_DIR = "outputs"
    
    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.OPENAI_API_KEY:
            # Fallback to dotenv
            from dotenv import dotenv_values
            env_vars = dotenv_values(".env")
            cls.OPENAI_API_KEY = env_vars.get("OPENAI_APIKEY")
            
        if not cls.OPENAI_API_KEY:
            raise RuntimeError("❌ OPENAI_API_KEY environment variable is not set!")
        
        if not cls.WEAVIATE_URL or not cls.WEAVIATE_API_KEY:
            raise RuntimeError("❌ Weaviate configuration is missing!")
        
        return True
