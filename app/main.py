import asyncio
import logging
import os  # Import the os module to check for file existence
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import uvicorn

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.exceptions import setup_exception_handlers
from app.api.endpoints.hackrx import router as hackrx_router
from app.services.cache_service import CacheService
from app.services.vector_service import VectorService
from app.services.document_processor import DocumentProcessor
from app.services.llm_service import LLMService

# Metrics
REQUEST_COUNT = Counter('hackrx_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('hackrx_request_duration_seconds', 'Request duration')
PROCESSING_TIME = Histogram('hackrx_processing_time_seconds', 'Processing time')

# Security
security = HTTPBearer()

logger = structlog.get_logger()
settings = get_settings()

# Global services
cache_service = None
vector_service = None
document_processor = None
llm_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global cache_service, vector_service, document_processor, llm_service
    
    logger.info("Starting HackRx RAG System...")
    
    try:
        # Initialize services
        cache_service = CacheService()
        vector_service = VectorService()
        document_processor = DocumentProcessor()
        llm_service = LLMService()
        
        # Initialize connections
        await cache_service.initialize()
        await vector_service.initialize()
        await document_processor.initialize()
        await llm_service.initialize()
        
        logger.info("All services initialized successfully")
        
        # Warm up the system with a local sample document
        await warm_up_system()
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise
    finally:
        logger.info("Shutting down services...")
        if cache_service:
            await cache_service.close()
        if vector_service:
            await vector_service.close()

# --- THIS IS THE CORRECTED FUNCTION ---
async def warm_up_system():
    """Warm up the system with a local sample document."""
    try:
        # Use a reliable, local file from your 'data' directory for warm-up
        sample_path = "data/Arogya Sanjeevani Policy.pdf"
        
        if os.path.exists(sample_path):
            logger.info("Warming up system with local sample document", path=sample_path)
            
            # This assumes your document_processor can handle local paths.
            # You might need to add a flag, e.g., is_local_path=True
            await document_processor.process_document_from_path(sample_path)
            
            logger.info("System warm-up completed successfully")
        else:
            logger.warning("Sample document for warm-up not found. Skipping.", path=sample_path)
            
    except Exception as e:
        import traceback
        logger.warning("System warm-up failed", error=str(e), exc_info=traceback.format_exc())

# Create FastAPI app
app = FastAPI(
    title="HackRx 6.0 - Intelligent Query-Retrieval System",
    description="Production-grade LLM-powered RAG system for insurance document analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Setup logging
setup_logging()

# Setup exception handlers
setup_exception_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get services
async def get_cache_service() -> CacheService:
    return cache_service

async def get_vector_service() -> VectorService:
    return vector_service

async def get_document_processor() -> DocumentProcessor:
    return document_processor

async def get_llm_service() -> LLMService:
    return llm_service

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != settings.HACKRX_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return credentials.credentials

# Include routers
app.include_router(
    hackrx_router,
    prefix="/hackrx",
    dependencies=[Depends(verify_token)]
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "cache": cache_service is not None and await cache_service.health_check(),
            "vector": vector_service is not None and await vector_service.health_check(),
            "llm": llm_service is not None and await llm_service.health_check()
        }
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        access_log=True
    )
# ```

# I've updated the `warm_up_system` function to use a local file path instead of the unreliable URL. This will fix the error you were seeing on startup.

# **Next Steps:**

# 1.  **Replace the Code:** Copy the code from the document above and paste it into your `app/main.py` file.
# 2.  **Check Your `DocumentProcessor`:** Make sure the `document_processor.py` service has a method like `process_document_from_path()` that can handle a local file path.
# 3.  **Restart Your Server:** Run `python -m uvicorn app.main:app --reload`. It should now start up without any "warm-up failed" erro