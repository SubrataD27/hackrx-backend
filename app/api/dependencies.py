# --- THIS LINE IS REMOVED TO PREVENT THE CIRCULAR IMPORT ---
# from app.main import cache_service, vector_service, document_processor, llm_service

from app.services.cache_service import CacheService
from app.services.vector_service import VectorService
from app.services.document_processor import DocumentProcessor
from app.services.llm_service import LLMService

# These functions allow FastAPI's dependency injection system to provide
# the globally initialized service instances to your API endpoints without
# creating a circular import.

async def get_cache_service() -> CacheService:
    """Dependency to get the global cache service instance."""
    # This will be dynamically resolved by FastAPI at runtime
    from app.main import cache_service
    return cache_service

async def get_vector_service() -> VectorService:
    """Dependency to get the global vector service instance."""
    from app.main import vector_service
    return vector_service

async def get_document_processor() -> DocumentProcessor:
    """Dependency to get the global document processor instance."""
    from app.main import document_processor
    return document_processor

async def get_llm_service() -> LLMService:
    """Dependency to get the global LLM service instance."""
    from app.main import llm_service
    return llm_service
