from pydantic import BaseModel, HttpUrl, validator, model_validator
from typing import List, Optional, Any # --- CRITICAL FIX: Import 'Any' ---

class HackRxRequest(BaseModel):
    """
    Request schema for HackRx endpoint.
    This is now flexible to support both a URL for production and a document_id for local testing.
    """
    documents: Optional[str] = None 
    document_id: Optional[str] = None
    questions: List[str]

    # --- THIS IS THE CORRECTED VALIDATOR ---
    # Replaced the deprecated `@root_validator` with the modern `@model_validator`.
    @model_validator(mode='before')
    @classmethod
    def check_document_source(cls, data: Any) -> Any:
        """
        Ensures that exactly one of 'documents' (URL) or 'document_id' is provided.
        """
        if isinstance(data, dict):
            if 'documents' not in data and 'document_id' not in data:
                raise ValueError('Either a "documents" URL or a "document_id" must be provided.')
            
            if 'documents' in data and data.get('documents') is not None and \
               'document_id' in data and data.get('document_id') is not None:
                raise ValueError('Provide either a "documents" URL or a "document_id", but not both.')
        
        return data

    @validator('questions')
    def validate_questions(cls, v):
        if not v:
            raise ValueError('Questions list cannot be empty')
        if len(v) > 50:
            raise ValueError('Too many questions (max 50)')
        return v
    
    @validator('documents')
    def validate_documents_url(cls, v):
        # This validator only runs if 'documents' is not None
        if v and not v.lower().endswith('.pdf'):
            raise ValueError('Only PDF document URLs are supported')
        return v

class HackRxResponse(BaseModel):
    """Response schema for HackRx endpoint"""
    answers: List[str]
    
    @validator('answers')
    def validate_answers(cls, v):
        # Cleans up answers, providing a default if an answer is empty
        return [str(answer).strip() if answer else "Information not found in the document." for answer in v]

class ProcessingMetrics(BaseModel):
    """Processing metrics for monitoring (no changes needed here)"""
    document_processing_time: float
    embedding_time: float
    search_time: float
    generation_time: float
    total_time: float
    chunks_processed: int
    chunks_retrieved: int
    tokens_used: int
