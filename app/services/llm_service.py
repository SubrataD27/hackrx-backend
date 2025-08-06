import asyncio
from typing import List, Dict, Any, Optional
import structlog
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import LLMGenerationError

logger = structlog.get_logger()
settings = get_settings()

class LLMService:
    """LLM service using Google Gemini"""
    
    def __init__(self):
        self.model = None
        self.generation_config = None
    
    async def initialize(self):
        """Initialize LLM service"""
        try:
            logger.info("Initializing LLM service")
            
            # Configure Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Initialize model
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Configure generation parameters
            self.generation_config = genai.types.GenerationConfig(
                max_output_tokens=1000,
                temperature=0.1,
                top_p=0.8,
                top_k=40
            )
            
            logger.info("LLM service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize LLM service", error=str(e))
            raise LLMGenerationError(f"LLM service initialization failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """Health check for LLM service"""
        try:
            if self.model:
                # Try a simple generation
                response = self.model.generate_content(
                    "Test", 
                    generation_config=genai.types.GenerationConfig(max_output_tokens=1)
                )
                return response is not None
            return False
        except:
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_answer(
        self, 
        question: str, 
        context_chunks: List[Dict[str, Any]]
    ) -> str:
        """Generate answer using LLM with context"""
        try:
            logger.debug("Generating answer", question=question[:100])
            
            if not context_chunks:
                return "I couldn't find relevant information in the document to answer your question."
            
            # Prepare context
            context = self._prepare_context(context_chunks)
            
            # Create prompt
            prompt = self._create_prompt(question, context)
            
            # Generate response
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._generate_with_model,
                prompt
            )
            
            # Extract and clean answer
            answer = self._extract_answer(response)
            
            logger.debug("Answer generated successfully", answer_length=len(answer))
            
            return answer
            
        except Exception as e:
            logger.error("Answer generation failed", error=str(e))
            raise LLMGenerationError(f"Failed to generate answer: {str(e)}")
    
    def _generate_with_model(self, prompt: str) -> str:
        """Generate with model (blocking call)"""
        response = self.model.generate_content(
            prompt,
            generation_config=self.generation_config
        )
        return response.text
    
    def _prepare_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Prepare context from chunks"""
        context_parts = []
        
        for i, chunk in enumerate(chunks[:5], 1):  # Limit to top 5 chunks
            # Use parent text if available for better context
            text = chunk.get("parent_text", chunk.get("text", ""))
            
            # Add source information
            page_num = chunk.get("page_number", "unknown")
            chunk_type = chunk.get("type", "text")
            
            context_part = f"**Source {i} (Page {page_num}, {chunk_type}):**\n{text}\n"
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)
    
    def _create_prompt(self, question: str, context: str) -> str:
        """Create optimized prompt for insurance domain"""
        
        prompt = f"""You are an expert assistant specializing in analyzing insurance policy documents. Your task is to provide accurate, concise answers based strictly on the provided document context.

**INSTRUCTIONS:**
1. Answer the question using ONLY the information provided in the context below
2. Be direct and specific in your response
3. If the answer involves specific terms, conditions, or amounts, quote them exactly
4. If the information is not in the context, state clearly that the information is not available
5. Keep your answer focused and avoid unnecessary elaboration
6. When mentioning specific clauses or conditions, reference the source if possible

**CONTEXT FROM DOCUMENT:**
{context}

**QUESTION:**
{question}

**ANSWER:**
Based on the provided document context, """

        return prompt
    
    def _extract_answer(self, response: str) -> str:
        """Extract and clean the answer from LLM response"""
        if not response:
            return "I couldn't generate a response. Please try again."
        
        # Clean up the response
        answer = response.strip()
        
        # Remove any prompt artifacts
        if answer.startswith("Based on the provided document context,"):
            answer = answer[len("Based on the provided document context,"):].strip()
        
        # Ensure minimum answer quality
        if len(answer) < 10:
            return "I couldn't find sufficient information in the document to provide a complete answer."
        
        # Limit answer length
        if len(answer) > 1000:
            # Find a good break point
            sentences = answer.split('. ')
            truncated = '. '.join(sentences[:3])
            if len(truncated) < 500:
                truncated += '. ' + '. '.join(sentences[3:5])
            answer = truncated + '.' if not truncated.endswith('.') else truncated
        
        return answer
    
    async def close(self):
        """Close LLM service"""
        logger.info("Closing LLM service")
        # Gemini doesn't need explicit closing
        pass