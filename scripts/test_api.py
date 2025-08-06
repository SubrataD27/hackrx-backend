#!/usr/bin/env python3
"""
Test script for HackRx API, updated for local development and testing.
"""
import asyncio
import httpx
import json
import time
import os
from dotenv import load_dotenv

# --- CRITICAL FIX: Load environment variables from .env at the very top ---
# This ensures that os.getenv() can find the correct auth token.
load_dotenv()

# --- Test Configuration ---
BASE_URL = "http://localhost:8000"
# This token will now be correctly loaded from your .env file
AUTH_TOKEN = os.getenv("HACKRX_AUTH_TOKEN")

# --- Sample Test Data for a Locally Ingested Document ---
# IMPORTANT: This test assumes you have already run `populate_vectors.py`
# and that the following document is in your Pinecone index.
TEST_DOCUMENT_ID = "Arogya Sanjeevani Policy.pdf"

# --- Questions that correctly match the TEST_DOCUMENT_ID ---
TEST_QUESTIONS = [
    "What is the range for the Sum Insured in this policy?",
    "Is there a co-payment clause, and if so, what is the percentage?",
    "What is the waiting period for treatment of joint replacement surgery?",
    "Are AYUSH treatments like Ayurveda and Homeopathy covered?",
    "What are the sub-limits on Room Rent and ICU Charges?"
]

async def test_health_check():
    """Tests the /health endpoint to ensure the server is running."""
    print("Testing health check...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
            print(f"Health check status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            print(f"Health check failed: Could not connect to the server at {BASE_URL}.")
            print("Please ensure the FastAPI server is running in another terminal.")
            return False
        except Exception as e:
            print(f"Health check failed with an unexpected error: {e}")
            return False

async def test_hackrx_endpoint():
    """Tests the main /hackrx/run endpoint with a local document ID."""
    print("\nTesting HackRx endpoint...")
    
    if not AUTH_TOKEN:
        print("Error: HACKRX_AUTH_TOKEN not found in environment. Please check your .env file.")
        return False
        
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "document_id": TEST_DOCUMENT_ID,
        "questions": TEST_QUESTIONS
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client: # Increased timeout for LLM
        try:
            start_time = time.time()
            response = await client.post(f"{BASE_URL}/hackrx/run", json=payload, headers=headers)
            end_time = time.time()
            
            print(f"Response status: {response.status_code}")
            print(f"Response time: {end_time - start_time:.2f} seconds")
            
            if response.status_code == 200:
                result = response.json()
                answers = result.get('answers', [])
                print(f"Number of answers received: {len(answers)}")
                
                for i, (question, answer) in enumerate(zip(TEST_QUESTIONS, answers), 1):
                    print("-" * 80)
                    print(f"Question {i}: {question}")
                    print(f"Answer {i}: {answer}")
                return True
            else:
                print(f"Error response from server: {response.text}")
                return False
        except Exception as e:
            print(f"Test failed with an unexpected error: {e}")
            return False

async def test_invalid_auth():
    """Tests that the endpoint correctly rejects requests with an invalid token."""
    print("\nTesting invalid authentication...")
    headers = {"Authorization": "Bearer invalid-token"}
    payload = {"document_id": "test.pdf", "questions": ["test"]}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(f"{BASE_URL}/hackrx/run", json=payload, headers=headers)
            print(f"Response status: {response.status_code}")
            print(f"Response: {response.json()}")
            return response.status_code == 401
        except Exception as e:
            print(f"Auth test failed with an unexpected error: {e}")
            return False

async def main():
    """Runs all API tests in sequence."""
    print("Starting HackRx API Tests")
    print("=" * 80)
    
    health_ok = await test_health_check()
    if not health_ok:
        return # Stop tests if the server isn't running

    main_ok = await test_hackrx_endpoint()
    auth_ok = await test_invalid_auth()
    
    print("\n" + "=" * 80)
    print("Test Results:")
    print(f"  Health Check:   {'✓ Passed' if health_ok else '✗ Failed'}")
    print(f"  Main Endpoint:  {'✓ Passed' if main_ok else '✗ Failed'}")
    print(f"  Authentication: {'✓ Passed' if auth_ok else '✗ Failed'}")
    
    if all([health_ok, main_ok, auth_ok]):
        print("\n🎉 All tests passed! Your local API is working correctly.")
    else:
        print("\n❌ Some tests failed. Please review the logs above.")

if __name__ == "__main__":
    asyncio.run(main())
