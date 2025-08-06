#!/usr/bin/env python3
"""
Script to populate vector database with all local documents from the 'data' folder.
"""
import asyncio
import sys
import os
import glob

# This line is important for your project structure to find the 'app' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document_processor import DocumentProcessor
from app.services.vector_service import VectorService

async def main():
    """Populate vector database with all documents from the local data directory"""
    
    # Define the directory where your PDFs are stored
    DATA_DIR = "data/"
    
    print("Initializing services...")
    document_processor = DocumentProcessor()
    vector_service = VectorService()
    
    # It's crucial that your VectorService is using the correct embedding model
    # ('nomic-ai/nomic-embed-text-v1.5') to match your Pinecone index dimension of 768.
    await document_processor.initialize()
    await vector_service.initialize()
    
    try:
        # Find all PDF files in the data directory
        pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
        
        if not pdf_files:
            print(f"❌ No PDF files found in '{DATA_DIR}'. Make sure your PDFs are in that folder.")
            return

        print(f"Found {len(pdf_files)} documents to process in '{DATA_DIR}'.")

        # Loop through each PDF file
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            print(f"\n--- Processing Document: {filename} ---")
            
            # This assumes your services are updated to handle local paths
            # and use the filename as a unique identifier.
            chunks = await document_processor.process_document_from_path(pdf_path)
            print(f"Created {len(chunks)} chunks.")
            
            print(f"Upserting chunks for {filename}...")
            await vector_service.upsert_chunks(chunks, document_id=filename)
        
        print("\n✅ Successfully populated vector database with all local documents!")
        
    except Exception as e:
        # Print a more detailed error message
        import traceback
        print(f"❌ An error occurred: {e}")
        traceback.print_exc()
    
    finally:
        print("\nClosing services...")
        await document_processor.close()
        await vector_service.close()

if __name__ == "__main__":
    asyncio.run(main())