import asyncio
import hashlib
import json
from typing import List, Dict, Any
import structlog
import httpx
import pdfplumber
from io import BytesIO
import re
import os

from app.core.config import get_settings
from app.core.exceptions import DocumentProcessingError
from app.services.cache_service import CacheService

logger = structlog.get_logger()
settings = get_settings()

class DocumentProcessor:
    """Advanced document processing service for both local paths and URLs."""

    def __init__(self):
        self.http_client = None
        self.cache_service = None

    async def initialize(self):
        """Initialize document processor."""
        logger.info("Initializing document processor")
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.cache_service = CacheService()
        await self.cache_service.initialize()

    # --- NEW METHOD TO FIX THE ERROR ---
    async def process_document_from_path(self, file_path: str) -> List[Dict[str, Any]]:
        """Processes a document from a local file path for the ingestion script."""
        logger.info("Processing local document", path=file_path)
        doc_id = os.path.basename(file_path)
        cache_key = f"doc_chunks:{doc_id}"

        cached_chunks_str = await self.cache_service.get(cache_key)
        if cached_chunks_str:
            logger.info("Retrieved local document chunks from cache", doc_id=doc_id)
            return json.loads(cached_chunks_str)

        try:
            with open(file_path, "rb") as f:
                pdf_content = f.read()
            
            extracted_data = self._extract_pdf_content(pdf_content)
            chunks = self._create_intelligent_chunks(extracted_data)
            
            await self.cache_service.set(cache_key, json.dumps(chunks), ttl=7200)
            logger.info("Local document processing completed", doc_id=doc_id, chunk_count=len(chunks))
            return chunks
        except FileNotFoundError:
            logger.error("Local document not found", path=file_path)
            raise DocumentProcessingError(f"File not found: {file_path}")
        except Exception as e:
            logger.error("Local document processing failed", path=file_path, error=str(e))
            raise DocumentProcessingError(f"Failed to process local file: {str(e)}")

    # --- RENAMED ORIGINAL METHOD FOR THE API ---
    async def process_document_from_url(self, document_url: str) -> List[Dict[str, Any]]:
        """Processes a document from a URL and returns structured chunks."""
        logger.info("Processing document from URL", url=document_url)
        doc_hash = hashlib.md5(document_url.encode()).hexdigest()
        cache_key = f"doc_chunks:{doc_hash}"
        
        cached_chunks_str = await self.cache_service.get(cache_key)
        if cached_chunks_str:
            logger.info("Retrieved URL document chunks from cache")
            return json.loads(cached_chunks_str)
        
        try:
            pdf_content = await self._download_document(document_url)
            extracted_data = self._extract_pdf_content(pdf_content)
            chunks = self._create_intelligent_chunks(extracted_data)
            
            await self.cache_service.set(cache_key, json.dumps(chunks), ttl=7200)
            logger.info("URL document processing completed", chunk_count=len(chunks))
            return chunks
        except Exception as e:
            logger.error("URL document processing failed", url=document_url, error=str(e))
            raise DocumentProcessingError(f"Failed to process document from URL: {str(e)}")

    async def _download_document(self, url: str) -> bytes:
        """Download document from URL"""
        logger.debug("Downloading document", url=url)
        response = await self.http_client.get(url)
        response.raise_for_status()
        if not response.content:
            raise DocumentProcessingError("Downloaded document is empty")
        logger.debug("Document downloaded successfully", size=len(response.content))
        return response.content

    def _extract_pdf_content(self, pdf_content: bytes) -> Dict[str, Any]:
        """Extract content from PDF with layout awareness"""
        logger.debug("Extracting PDF content")
        extracted_data = {"pages": [], "tables": [], "metadata": {}}
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            extracted_data["metadata"] = {
                "page_count": len(pdf.pages),
                "title": getattr(pdf.metadata, 'title', 'Unknown') if pdf.metadata else 'Unknown'
            }
            for page_num, page in enumerate(pdf.pages, 1):
                page_data = {"page_number": page_num, "text": "", "tables": []}
                page_text = page.extract_text() or ""
                page_data["text"] = self._clean_text(page_text)
                tables = page.extract_tables()
                if tables:
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 1:
                            table_markdown = self._table_to_markdown(table)
                            page_data["tables"].append({
                                "table_index": table_idx,
                                "markdown": table_markdown,
                                "raw": table
                            })
                            extracted_data["tables"].append({
                                "page": page_num, "index": table_idx, "markdown": table_markdown
                            })
                extracted_data["pages"].append(page_data)
        logger.debug("PDF content extraction completed", page_count=len(extracted_data["pages"]), table_count=len(extracted_data["tables"]))
        return extracted_data

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text: return ""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'Page \d+.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        text = text.replace('\u00a0', ' ').replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
        return text.strip()

    def _table_to_markdown(self, table: List[List[str]]) -> str:
        """Convert table to markdown format"""
        if not table or len(table) < 2: return ""
        header = [str(cell or "") for cell in table[0]]
        separator = ["-" * max(3, len(cell)) for cell in header]
        markdown_lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(separator) + " |"]
        for row in table[1:]:
            cleaned_row = [str(cell or "") for cell in row]
            while len(cleaned_row) < len(header): cleaned_row.append("")
            markdown_lines.append("| " + " | ".join(cleaned_row[:len(header)]) + " |")
        return "\n".join(markdown_lines)

    def _create_intelligent_chunks(self, extracted_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create intelligent chunks using parent-child strategy"""
        logger.debug("Creating intelligent chunks")
        chunks = []
        for page_data in extracted_data["pages"]:
            page_num, text, tables = page_data["page_number"], page_data["text"], page_data["tables"]
            full_page_content = text
            for table in tables:
                full_page_content += f"\n\n**Table {table['table_index'] + 1}:**\n{table['markdown']}\n"
            parent_chunks = self._split_into_parent_chunks(full_page_content, page_num)
            for parent_idx, parent_chunk in enumerate(parent_chunks):
                child_chunks = self._split_into_child_chunks(parent_chunk["text"])
                for child_idx, child_text in enumerate(child_chunks):
                    chunks.append({
                        "text": child_text, "parent_text": parent_chunk["text"], "page_number": page_num,
                        "parent_index": parent_idx, "child_index": child_idx, "type": "text"
                    })
            for table in tables:
                chunks.append({
                    "text": table["markdown"], "parent_text": table["markdown"], "page_number": page_num,
                    "parent_index": -1, "child_index": table["table_index"], "type": "table"
                })
        chunks = [chunk for chunk in chunks if len(chunk["text"].strip()) > 50]
        logger.debug("Intelligent chunking completed", chunk_count=len(chunks))
        return chunks

    def _split_into_parent_chunks(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """Split text into parent chunks (larger sections)"""
        if not text.strip(): return []
        paragraphs = re.split(r'\n\s*\n', text)
        parent_chunks, current_chunk = [], ""
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph: continue
            if len(current_chunk) + len(paragraph) > settings.MAX_PARENT_CHUNK_SIZE and current_chunk:
                parent_chunks.append({"text": current_chunk.strip(), "page_number": page_num})
                current_chunk = paragraph
            else:
                current_chunk += ("\n\n" if current_chunk else "") + paragraph
        if current_chunk.strip():
            parent_chunks.append({"text": current_chunk.strip(), "page_number": page_num})
        return parent_chunks

    def _split_into_child_chunks(self, text: str) -> List[str]:
        """Split text into child chunks (smaller, precise chunks)"""
        if not text.strip(): return []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        child_chunks, current_chunk = [], ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence: continue
            if len(current_chunk) + len(sentence) > settings.CHUNK_SIZE and current_chunk:
                child_chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += (" " if current_chunk else "") + sentence
        if current_chunk.strip():
            child_chunks.append(current_chunk.strip())
        return child_chunks

    async def close(self):
        """Close document processor"""
        logger.info("Closing document processor")
        if self.http_client:
            await self.http_client.aclose()
        if self.cache_service:
            await self.cache_service.close()
# ```

# After replacing the code in `app/services/document_processor.py` with the version above, your next step is to run the ingestion script again. The `AttributeError` will be resolved.

# **Run this command in your terminal:**
# ```bash
# python scripts/populate_vectors.py
