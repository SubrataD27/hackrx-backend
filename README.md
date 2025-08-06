# HackRx 6.0 - Production-Grade RAG System

## 🏆 Competition Overview

This is a production-ready, LLM-powered intelligent query-retrieval system designed specifically for the HackRx 6.0 competition. The system implements advanced RAG (Retrieval-Augmented Generation) techniques to analyze insurance policy documents and provide accurate, contextual answers.

## 🚀 Key Features

### Advanced RAG Architecture
- **Multi-stage "Retrieval Gauntlet"** with hybrid search capabilities
- **Parent-Child Chunking Strategy** for optimal context retrieval
- **Semantic + Keyword Search** using Pinecone vector database
- **Context-aware Answer Generation** with Google Gemini

### Performance Optimizations
- **Sub-30s Response Times** with multi-level caching
- **Concurrent Processing** for multiple questions
- **Token-efficient Prompting** for cost optimization
- **Intelligent Document Processing** with table extraction

### Production Features
- **FastAPI Async Framework** for high performance
- **Comprehensive Error Handling** and retry mechanisms
- **Bearer Token Authentication** as required
- **Health Checks and Monitoring** with Prometheus metrics
- **Docker Containerization** for consistent deployment

## 📋 System Requirements

- Python 3.11+
- Docker (optional, for containerized deployment)
- Pinecone account with vector index
- Google AI Studio account for Gemini API

## ⚙️ Setup Instructions

### 1. Environment Configuration

Create a `.env` file with your API keys:

```bash
# API Keys
PINECONE_API_KEY=your_pinecone_api_key
GEMINI_API_KEY=your_gemini_api_key

# Pinecone Configuration
PINECONE_INDEX_NAME=hackrx-solution
PINECONE_ENVIRONMENT=us-east-1

# HackRx Configuration
HACKRX_AUTH_TOKEN=95800130f4487ff2c0c78496571ca520ebd16fea4d78ff1a34b65406b1a189b2
```

### 2. Pinecone Index Setup

Create a Pinecone index with these specifications:
- **Name**: `hackrx-solution`
- **Dimensions**: `384` (for sentence-transformers/all-MiniLM-L6-v2)
- **Metric**: `cosine`
- **Pod Type**: `p1.x1` (recommended for low latency)

### 3. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Populate vector database (first time only)
python scripts/populate_vectors.py

# Start the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Test the API
python scripts/test_api.py
```

### 4. Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t hackrx-app .
docker run -p 8000:8000 --env-file .env hackrx-app
```

## 🚀 Cloud Deployment

### Railway Deployment (Recommended)

1. Push code to GitHub repository
2. Connect Railway to your GitHub repo
3. Set environment variables in Railway dashboard
4. Deploy automatically on push

### Vercel Deployment

1. Install Vercel CLI: `npm i -g vercel`
2. Configure environment variables
3. Deploy: `vercel --prod`

### Manual Cloud Deployment

The application can be deployed on any cloud platform that supports Docker:
- AWS ECS/Elastic Beanstalk
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform

## 📊 API Documentation

### Main Endpoint

**POST** `/hackrx/run`

**Headers:**
```
Authorization: Bearer 95800130f4487ff2c0c78496571ca520ebd16fea4d78ff1a34b65406b1a189b2
Content-Type: application/json
Accept: application/json
```

**Request Body:**
```json
{
  "documents": "https://example.com/policy.pdf",
  "questions": [
    "What is the grace period for premium payment?",
    "What are the waiting periods for pre-existing diseases?"
  ]
}
```

**Response:**
```json
{
  "answers": [
    "A grace period of thirty days is provided for premium payment...",
    "There is a waiting period of thirty-six (36) months of continuous coverage..."
  ]
}
```

### Health Check

**GET** `/health`

Returns system health status and service availability.

### Metrics

**GET** `/metrics`

Returns Prometheus-compatible metrics for monitoring.

## 🏗️ Architecture Overview

### Document Processing Pipeline
1. **PDF Download & Parsing** - Extract text and tables with layout awareness
2. **Intelligent Chunking** - Parent-child strategy for optimal retrieval
3. **Embedding Generation** - Create semantic vectors using sentence transformers
4. **Vector Storage** - Index chunks in Pinecone with metadata

### Query Processing Pipeline
1. **Hybrid Search** - Combine semantic and keyword search
2. **Context Assembly** - Retrieve parent chunks for rich context
3. **Answer Generation** - Use Gemini with optimized prompts
4. **Response Caching** - Cache answers for improved latency

## 🎯 Competition Optimization

### Evaluation Criteria Alignment

- **Accuracy**: Advanced RAG with re-ranking and parent-child chunking
- **Token Efficiency**: Optimized prompts and context selection
- **Latency**: Multi-level caching and async processing
- **Reusability**: Modular architecture with clear separation
- **Explainability**: Source attribution and transparent reasoning

### Performance Tuning

- **Concurrent Processing**: Handle multiple questions in parallel
- **Smart Caching**: Document, embedding, and answer level caching
- **Optimized Chunking**: Balance between precision and context
- **Efficient Embeddings**: Fast, lightweight sentence transformers

## 🔧 Development Tools

### Testing
```bash
# Run API tests
python scripts/test_api.py

# Test individual components
python -m pytest tests/ -v
```

### Monitoring
```bash
# View logs
docker-compose logs -f hackrx-app

# Monitor metrics
curl http://localhost:8000/metrics
```

### Debugging
```bash
# Interactive shell with services
python -c "
import asyncio
from app.services.document_processor import DocumentProcessor
# ... debug code
"
```

## 📈 Performance Metrics

Expected performance benchmarks:
- **Response Time**: < 10s average, < 30s maximum
- **Accuracy**: > 85% on insurance domain questions
- **Throughput**: 10+ concurrent requests
- **Memory Usage**: < 2GB in production

## 🤝 Team Collaboration

### Code Structure
- **Modular Design**: Each service is independently testable
- **Clear Interfaces**: Well-defined APIs between components
- **Comprehensive Logging**: Structured logs for debugging
- **Error Handling**: Graceful failure handling at all levels

### Best Practices
- Follow PEP 8 code style
- Add docstrings to all functions
- Use type hints throughout
- Implement comprehensive error handling
- Write tests for critical components

