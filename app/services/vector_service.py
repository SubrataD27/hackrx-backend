import asyncio
from typing import List, Dict, Any
import structlog
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import numpy as np
import hashlib
import functools # Import functools

from app.core.config import get_settings
from app.core.exceptions import VectorSearchError

logger = structlog.get_logger()
settings = get_settings()

class VectorService:
    """Vector database service using Pinecone."""
    
    def __init__(self):
        self.pinecone_client = None
        self.index = None
        self.embedding_model = None
    
    async def initialize(self):
        """Initializes the vector service."""
        try:
            logger.info("Initializing vector service")
            self.pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index = self.pinecone_client.Index(settings.PINECONE_INDEX_NAME)
            
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, trust_remote_code=True)
            
            test_embedding = self.embedding_model.encode("test")
            if test_embedding.shape[0] != int(settings.EMBEDDING_DIM):
                 raise VectorSearchError(f"Model dimension ({test_embedding.shape[0]}) does not match index dimension ({settings.EMBEDDING_DIM})")

            logger.info("Vector service initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize vector service", error=str(e))
            raise VectorSearchError(f"Vector service initialization failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """Health check for vector service."""
        try:
            return self.index.describe_index_stats() is not None
        except:
            return False
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of texts."""
        try:
            loop = asyncio.get_event_loop()
            
            # --- THIS IS THE CORRECTED LOGIC ---
            # Use functools.partial to correctly pass keyword arguments to the executor.
            encode_func = functools.partial(
                self.embedding_model.encode, 
                batch_size=32, 
                show_progress_bar=False
            )
            
            embeddings = await loop.run_in_executor(
                None, 
                encode_func,
                texts
            )
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error("Failed to generate embeddings", error=str(e))
            raise VectorSearchError(f"Embedding generation failed: {str(e)}")

    async def upsert_chunks(self, chunks: List[Dict[str, Any]], document_id: str):
        """Upserts document chunks to the vector database using a document_id."""
        if not chunks:
            logger.warning("No chunks to upsert", document_id=document_id)
            return

        logger.info("Upserting chunks", chunk_count=len(chunks), document_id=document_id)
        try:
            texts_to_embed = [chunk["text"] for chunk in chunks]
            embeddings = await self.embed_texts(texts_to_embed)

            vectors = []
            for i, chunk in enumerate(chunks):
                chunk_hash = hashlib.md5(chunk["text"].encode()).hexdigest()
                vector_id = f"{document_id}_{i}_{chunk_hash[:8]}"
                
                metadata = {
                    "document_id": document_id,
                    "text": chunk["text"][:1000],
                    "page_number": chunk.get("page_number", 0),
                    "chunk_type": chunk.get("type", "text"),
                    "parent_text": chunk.get("parent_text", "")[:2000]
                }
                
                vectors.append({"id": vector_id, "values": embeddings[i], "metadata": metadata})
            
            for i in range(0, len(vectors), 100):
                batch = vectors[i:i + 100]
                self.index.upsert(vectors=batch)
            
            logger.info("Successfully upserted chunks", chunk_count=len(chunks), document_id=document_id)
        except Exception as e:
            logger.error("Failed to upsert chunks", error=str(e))
            raise VectorSearchError(f"Chunk upsert failed: {str(e)}")

    async def hybrid_search(self, query: str, document_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Performs hybrid search filtered by a specific document_id."""
        logger.debug("Performing hybrid search", query=query[:100], document_id=document_id)
        try:
            query_embedding = (await self.embed_texts([query]))[0]
            
            search_results = self.index.query(
                vector=query_embedding, top_k=top_k * 2,
                filter={"document_id": document_id}, include_metadata=True
            )
            
            results = [{**match.metadata, "id": match.id, "score": float(match.score)} for match in search_results.matches]
            
            boosted_results = self._apply_keyword_boost(results, query)
            boosted_results.sort(key=lambda x: x["score"], reverse=True)
            
            return boosted_results[:top_k]
        except Exception as e:
            logger.error("Hybrid search failed", error=str(e))
            raise VectorSearchError(f"Hybrid search failed: {str(e)}")

    def _apply_keyword_boost(self, results: List[Dict], query: str) -> List[Dict]:
        """Apply keyword-based boosting to semantic search results"""
        query_terms = set(query.lower().split())
        for result in results:
            text_lower = result.get("text", "").lower()
            keyword_matches = sum(1 for term in query_terms if term in text_lower)
            if keyword_matches > 0:
                result["score"] *= 1.0 + (keyword_matches * 0.1)
        return results
    
    async def close(self):
        """Closes the vector service."""
        logger.info("Closing vector service")
        pass
