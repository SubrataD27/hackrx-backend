# import asyncio
# import time
# import hashlib
# from typing import List, Dict, Any
# from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
# import structlog

# from app.schemas.hackrx import HackRxRequest, HackRxResponse
# from app.services.cache_service import CacheService
# from app.services.vector_service import VectorService
# from app.services.document_processor import DocumentProcessor
# from app.services.llm_service import LLMService
# from app.core.exceptions import DocumentProcessingError, VectorSearchError, LLMGenerationError
# # It's good practice to get dependencies from a central place if they are complex
# from app.main import get_document_processor, get_vector_service, get_llm_service, get_cache_service

# router = APIRouter()
# logger = structlog.get_logger()

# @router.post("/run", response_model=HackRxResponse)
# async def run_hackrx_query(
#     request: HackRxRequest,
#     cache_service: CacheService = Depends(get_cache_service),
#     vector_service: VectorService = Depends(get_vector_service),
#     document_processor: DocumentProcessor = Depends(get_document_processor),
#     llm_service: LLMService = Depends(get_llm_service)
# ) -> HackRxResponse:
#     """
#     Main HackRx endpoint. Handles both live URL processing and local testing via document_id.
#     """
#     start_time = time.time()
    
#     # --- Determine the document identifier ---
#     # This logic makes the endpoint flexible for both local testing and production.
#     document_id: str
#     if request.document_id:
#         # PATH 1: LOCAL TESTING
#         # The request comes from `test_api.py` with a `document_id` (filename).
#         # We assume the document has already been processed by `populate_vectors.py`.
#         document_id = request.document_id
#         logger.info("Processing request for local document", document_id=document_id, q_count=len(request.questions))
    
#     elif request.documents:
#         # PATH 2: LIVE HACKATHON REQUEST
#         # The request comes from the platform with a `documents` URL.
#         document_url = str(request.documents)
#         # Create a stable, unique ID from the URL for caching and vector filtering.
#         document_id = hashlib.md5(document_url.encode()).hexdigest()
#         logger.info("Processing request for URL", document_url=document_url, document_id=document_id, q_count=len(request.questions))
        
#         # Process and ingest the document from the URL.
#         # The service's internal caching will prevent re-processing the same URL.
#         try:
#             await document_processor.process_document_from_url(document_url)
#         except DocumentProcessingError as e:
#             logger.error("Critical failure: Could not process document from URL", url=document_url, error=str(e))
#             raise HTTPException(status_code=500, detail=f"Failed to process the provided document URL: {e}")
    
#     else:
#         # This case should be caught by the Pydantic schema, but it's a good safeguard.
#         raise HTTPException(status_code=400, detail="Request must include either 'documents' (URL) or 'document_id'.")

#     try:
#         # Process all questions concurrently for maximum speed.
#         tasks = [
#             process_single_question(
#                 document_id=document_id,
#                 question=q,
#                 cache_service=cache_service,
#                 vector_service=vector_service,
#                 llm_service=llm_service
#             ) for q in request.questions
#         ]
        
#         results = await asyncio.gather(*tasks, return_exceptions=True)
        
#         # Safely process results, handling any individual errors from the concurrent tasks.
#         final_answers = []
#         for i, res in enumerate(results):
#             if isinstance(res, Exception):
#                 logger.error("Failed to process a question", question_index=i, question=request.questions[i], error=str(res))
#                 final_answers.append("I apologize, but an error occurred while processing this question.")
#             else:
#                 final_answers.append(res)
        
#         total_time = time.time() - start_time
#         logger.info("HackRx request completed successfully", total_time=f"{total_time:.2f}s")
        
#         return HackRxResponse(answers=final_answers)
        
#     except Exception as e:
#         logger.error("A critical error occurred in the main request handler", error=str(e), exc_info=True)
#         raise HTTPException(status_code=500, detail="An unexpected server error occurred.")

# async def process_single_question(
#     document_id: str,
#     question: str,
#     cache_service: CacheService,
#     vector_service: VectorService,
#     llm_service: LLMService
# ) -> str:
#     """Processes a single question against a unique document identifier."""
    
#     # Use a combined key for caching final answers to speed up repeated questions.
#     cache_key = f"answer:{document_id}:{hash(question)}"
#     cached_answer = await cache_service.get(cache_key)
#     if cached_answer:
#         logger.debug("Retrieved final answer from cache", question=question[:50])
#         return cached_answer
    
#     try:
#         # 1. Search for relevant context chunks using the document_id to filter results.
#         relevant_chunks = await vector_service.hybrid_search(
#             query=question,
#             document_id=document_id,
#             top_k=5 # Retrieve the top 5 most relevant chunks for the LLM context.
#         )
        
#         if not relevant_chunks:
#             return "I could not find any relevant information in the document to answer this question."
        
#         # 2. Generate a precise answer using the retrieved context.
#         answer = await llm_service.generate_answer(
#             question=question,
#             context_chunks=relevant_chunks
#         )
        
#         # 3. Cache the newly generated answer for future requests.
#         await cache_service.set(cache_key, answer, ttl=3600)
        
#         return answer
        
#     except (VectorSearchError, LLMGenerationError) as e:
#         logger.error("Error in single question processing pipeline", question=question, error=str(e))
#         return "I encountered an issue while retrieving information or generating an answer. Please try again."
#     except Exception as e:
#         logger.error("Unexpected error in single question processing", question=question, error=str(e), exc_info=True)
#         return "An unexpected error occurred while processing this question."


import asyncio
import time
import hashlib
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
import structlog

from app.schemas.hackrx import HackRxRequest, HackRxResponse
from app.services.cache_service import CacheService
from app.services.vector_service import VectorService
from app.services.document_processor import DocumentProcessor
from app.services.llm_service import LLMService
from app.core.exceptions import DocumentProcessingError, VectorSearchError, LLMGenerationError

# --- CRITICAL FIX: Import dependencies from the new dependencies file to prevent circular imports ---
from app.api.dependencies import get_document_processor, get_vector_service, get_llm_service, get_cache_service

router = APIRouter()
logger = structlog.get_logger()

@router.post("/run", response_model=HackRxResponse)
async def run_hackrx_query(
    request: HackRxRequest,
    cache_service: CacheService = Depends(get_cache_service),
    vector_service: VectorService = Depends(get_vector_service),
    document_processor: DocumentProcessor = Depends(get_document_processor),
    llm_service: LLMService = Depends(get_llm_service)
) -> HackRxResponse:
    """
    Main HackRx endpoint. Handles both live URL processing and local testing via document_id.
    """
    start_time = time.time()
    
    document_id: str
    # --- CRITICAL FIX: Add logic to handle both local testing and live requests ---
    if request.document_id:
        # PATH 1: LOCAL TESTING
        # The request comes from `test_api.py` with a `document_id` (filename).
        # We assume the document has already been processed by `populate_vectors.py`.
        document_id = request.document_id
        logger.info("Processing request for local document", document_id=document_id, q_count=len(request.questions))
    
    elif request.documents:
        # PATH 2: LIVE HACKATHON REQUEST
        # The request comes from the platform with a `documents` URL.
        document_url = str(request.documents)
        # Create a stable, unique ID from the URL for caching and vector filtering.
        document_id = hashlib.md5(document_url.encode()).hexdigest()
        logger.info("Processing request for URL", url=document_url, doc_id=document_id, q_count=len(request.questions))
        
        # Process and ingest the document from the URL.
        # The service's internal caching will prevent re-processing the same URL.
        try:
            await document_processor.process_document_from_url(document_url)
        except DocumentProcessingError as e:
            logger.error("Failed to process document from URL", url=document_url, error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to process the provided document URL: {e}")
    
    else:
        # This case should be caught by the Pydantic schema, but it's a good safeguard.
        raise HTTPException(status_code=400, detail="Request must include either 'documents' or 'document_id'.")

    try:
        # Process all questions concurrently for maximum speed.
        tasks = [
            process_single_question(
                document_id=document_id, question=q,
                cache_service=cache_service, vector_service=vector_service, llm_service=llm_service
            ) for q in request.questions
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_answers = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error("Failed to process a question", index=i, question=request.questions[i], error=str(res))
                final_answers.append("An error occurred while processing this question.")
            else:
                final_answers.append(res)
        
        total_time = time.time() - start_time
        logger.info("Request completed", total_time=f"{total_time:.2f}s")
        return HackRxResponse(answers=final_answers)
        
    except Exception as e:
        logger.error("Critical error in main handler", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected server error occurred.")

async def process_single_question(
    document_id: str, question: str,
    cache_service: CacheService, vector_service: VectorService, llm_service: LLMService
) -> str:
    """Processes a single question against a unique document identifier."""
    cache_key = f"answer:{document_id}:{hash(question)}"
    cached_answer = await cache_service.get(cache_key)
    if cached_answer:
        logger.debug("Answer cache hit", question=question[:50])
        return cached_answer
    
    try:
        # --- CRITICAL FIX: Use the generic document_id for the search filter ---
        relevant_chunks = await vector_service.hybrid_search(
            query=question, document_id=document_id, top_k=5
        )
        if not relevant_chunks:
            return "No relevant information found in the document to answer this question."
        
        answer = await llm_service.generate_answer(
            question=question, context_chunks=relevant_chunks
        )
        await cache_service.set(cache_key, answer, ttl=3600)
        return answer
        
    except (VectorSearchError, LLMGenerationError) as e:
        logger.error("Error in question processing pipeline", question=question, error=str(e))
        return "An issue occurred while retrieving information or generating an answer."
    except Exception as e:
        logger.error("Unexpected error processing question", question=question, error=str(e), exc_info=True)
        return "An unexpected error occurred."
