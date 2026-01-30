# ChromaDB Setup Guide

## Overview
BridgeAI uses ChromaDB as a vector database for semantic search and RAG (Retrieval Augmented Generation). ChromaDB stores conversation embeddings and retrieves relevant context to enhance AI responses.

## Setup Steps

### 1. Install ChromaDB
```bash
pip install chromadb
```

### 2. Create Data Directory
From the **backend root directory** (bridgeai-backend/), create the ChromaDB data directory:
```bash
mkdir chroma_data
```

### 3. Start ChromaDB Server
Run the ChromaDB server from the **backend root directory**:
```bash
chroma run --host 0.0.0.0 --port 8001 --path ./chroma_data
```

**Important:** Always run this command from `bridgeai-backend/` so the path `./chroma_data` resolves correctly.

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and ensure these settings are correct:
```env
CHROMA_SERVER_HOST=localhost
CHROMA_SERVER_HTTP_PORT=8001
CHROMA_COLLECTION_NAME=project_memories
```

### 5. Start the Backend
In a separate terminal, start the FastAPI backend:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Directory Structure
```
bridgeai/
├── bridgeai-backend/
│   ├── chroma_data/          # ChromaDB vector storage (gitignored)
│   ├── app/
│   ├── .env
│   └── .env.example
└── bridgeai-frontend/
```

## How It Works

1. **Memory Storage**: When users send clear requirements in chat, they're saved to ChromaDB with embeddings
2. **Context Retrieval**: When processing new messages, ChromaDB performs semantic search to find relevant past conversations
3. **Enhanced Responses**: The AI uses retrieved context to provide more informed, contextually-aware responses

## Troubleshooting

### ChromaDB Connection Error
If you see connection errors, ensure:
- ChromaDB server is running on port 8001
- The `chroma_data/` directory exists in the backend root
- No firewall is blocking localhost:8001

### Empty Results
If semantic search returns no results:
- Check that the collection "project_memories" exists
- Verify that messages are being stored (check logs)
- Ensure the similarity threshold isn't too high (default: 0.3)

## Production Deployment

For production, consider:
- Running ChromaDB as a persistent service (systemd, docker, etc.)
- Using absolute paths instead of relative paths
- Setting up authentication if ChromaDB is exposed
- Regular backups of the `chroma_data/` directory
