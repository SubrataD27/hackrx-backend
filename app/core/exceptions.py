from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import structlog
from typing import Any

logger = structlog.get_logger()

class DocumentProcessingError(Exception):
    """Document processing related errors"""
    pass

class VectorSearchError(Exception):
    """Vector search related errors"""
    pass

class LLMGenerationError(Exception):
    """LLM generation related errors"""
    pass

class CacheError(Exception):
    """Cache related errors"""
    pass

def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""
    
    @app.exception_handler(DocumentProcessingError)
    async def document_processing_error_handler(request: Request, exc: DocumentProcessingError):
        logger.error("Document processing error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=422,
            content={
                "error": "Document processing failed",
                "detail": str(exc),
                "type": "document_processing_error"
            }
        )
    
    @app.exception_handler(VectorSearchError)
    async def vector_search_error_handler(request: Request, exc: VectorSearchError):
        logger.error("Vector search error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=503,
            content={
                "error": "Vector search service unavailable",
                "detail": str(exc),
                "type": "vector_search_error"
            }
        )
    
    @app.exception_handler(LLMGenerationError)
    async def llm_generation_error_handler(request: Request, exc: LLMGenerationError):
        logger.error("LLM generation error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=503,
            content={
                "error": "LLM service unavailable",
                "detail": str(exc),
                "type": "llm_generation_error"
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning("HTTP exception", status_code=exc.status_code, detail=exc.detail, path=request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "type": "http_error"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("Unexpected error", error=str(exc), path=request.url.path, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": "An unexpected error occurred",
                "type": "internal_error"
            }
        )