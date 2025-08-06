import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file, if it exists
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables and .env file.
    This class now fully matches the provided .env structure.
    """
    
    # --- API Keys (loaded from .env) ---
    PINECONE_API_KEY: str
    GEMINI_API_KEY: str
    
    # --- Pinecone Configuration ---
    PINECONE_INDEX_NAME: str = "hackrx-solution"
    PINECONE_ENVIRONMENT: Optional[str] = "us-east-1"
    
    # --- HackRx Configuration ---
    HACKRX_AUTH_TOKEN: str
    
    # --- CRITICAL FIX: Model Configuration ---
    # Use the powerful model that matches your Pinecone index dimension
    EMBEDDING_MODEL: str = "nomic-ai/nomic-embed-text-v1.5"
    
    # --- CRITICAL FIX: Dimension Configuration ---
    # Use the correct dimension (768) and variable name ('EMBEDDING_DIM')
    EMBEDDING_DIM: int = 768
    
    # --- LLM & Processing Configuration ---
    MAX_TOKENS: int = 4000
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANK: int = 5 # Added this setting from your .env
    MAX_PARENT_CHUNK_SIZE: int = 1500
    
    # --- Optional Service Configurations ---
    REDIS_URL: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    CACHE_TTL: int = 3600
    
    # --- Performance & Logging ---
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False # Best practice to avoid case sensitivity issues

@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the application settings.
    Using lru_cache ensures the settings are loaded only once.
    """
    return Settings()
