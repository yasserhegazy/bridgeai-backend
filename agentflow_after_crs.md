# CRS Document Generation Agent Flow

This document describes the AI-powered Customer Requirements Specification (CRS) generation workflow implemented in BE-17.

## Overview

The system uses a LangGraph-based multi-agent workflow to:
1. Collect requirements through natural conversation
2. Ask clarifying questions when requirements are ambiguous
3. Generate structured CRS documents automatically
4. Persist and version CRS documents in the database

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERACTION                                │
│                                                                              │
│  Client connects via WebSocket: /api/projects/{id}/chats/{id}/ws            │
│  Sends: { "content": "I need an e-commerce app...", "sender_type": "client"}│
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LANGGRAPH AI WORKFLOW                              │
│                              (app/ai/graph.py)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  1. CLARIFICATION NODE (app/ai/nodes/clarification)                   │  │
│  │                                                                        │  │
│  │  Purpose: Ensure requirements are clear before CRS generation         │  │
│  │                                                                        │  │
│  │  - Analyzes user input for ambiguities                                │  │
│  │  - Generates clarifying questions if needed                           │  │
│  │  - Returns to user and waits for answers                              │  │
│  │  - Loops until needs_clarification = False                            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                       │                                      │
│                      (needs_clarification = False)                           │
│                                       ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  2. TEMPLATE FILLER NODE (app/ai/nodes/template_filler)               │  │
│  │                                                                        │  │
│  │  Purpose: Extract structured CRS from conversation                    │  │
│  │                                                                        │  │
│  │  Input:                                                                │  │
│  │    - user_input: Latest message                                       │  │
│  │    - conversation_history: All chat messages                          │  │
│  │    - extracted_fields: Previously extracted data                      │  │
│  │                                                                        │  │
│  │  Process:                                                              │  │
│  │    1. Calls Groq LLM (llama-3.3-70b-versatile)                        │  │
│  │    2. Extracts: project_title, description, requirements, etc.        │  │
│  │    3. Generates summary_points                                        │  │
│  │    4. Checks completeness (title + desc + requirements + 2 optional)  │  │
│  │                                                                        │  │
│  │  Output:                                                               │  │
│  │    - crs_content: Structured JSON                                     │  │
│  │    - crs_is_complete: Boolean                                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                       │                                      │
│                        (crs_is_complete = True)                              │
│                                       ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  3. CRS PERSISTENCE (app/services/crs_service.py)                     │  │
│  │                                                                        │  │
│  │  Purpose: Save and index the generated CRS                            │  │
│  │                                                                        │  │
│  │  Actions:                                                              │  │
│  │    1. Calculate next version number                                   │  │
│  │    2. Save to crs_documents table (MySQL)                             │  │
│  │    3. Store embedding in ChromaDB (semantic search)                   │  │
│  │    4. Return crs_document_id and version                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                       │                                      │
│                                       ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  4. MEMORY NODE (app/ai/nodes/memory_node.py)                         │  │
│  │                                                                        │  │
│  │  Purpose: Store context for future retrieval                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          WEBSOCKET RESPONSE                                  │
│                                                                              │
│  {                                                                           │
│    "id": 15,                                                                 │
│    "sender_type": "ai",                                                      │
│    "content": "I've generated a complete CRS document...",                  │
│    "crs": {                        // Included when CRS is generated        │
│      "crs_document_id": 5,                                                  │
│      "version": 1,                                                           │
│      "is_complete": true,                                                    │
│      "summary_points": ["E-Commerce Platform", "4 requirements", ...]       │
│    }                                                                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## CRS REST API Endpoints

After CRS is generated via chat, these endpoints manage it:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/crs/` | Manual CRS creation (admin/testing) |
| GET | `/api/crs/latest?project_id={id}` | Fetch latest CRS for a project |
| GET | `/api/crs/versions?project_id={id}` | Fetch all CRS versions |
| PUT | `/api/crs/{id}/status` | Update status (approval workflow) |

## CRS Status Workflow

```
  ┌─────────┐     submit      ┌──────────────┐     approve     ┌──────────┐
  │  draft  │ ───────────────▶│ under_review │ ───────────────▶│ approved │
  └─────────┘                 └──────────────┘                 └──────────┘
       ▲                             │
       │                             │ reject
       │         revise              ▼
       └──────────────────────┌──────────┐
                              │ rejected │
                              └──────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `app/ai/graph.py` | LangGraph workflow definition |
| `app/ai/state.py` | Shared state between nodes |
| `app/ai/nodes/clarification/` | Clarification agent |
| `app/ai/nodes/template_filler/` | CRS generation agent |
| `app/ai/nodes/template_filler/llm_template_filler.py` | Groq LLM integration |
| `app/services/crs_service.py` | CRS persistence and retrieval |
| `app/api/crs.py` | REST API endpoints |
| `app/api/chats.py` | WebSocket with CRS metadata |
| `app/models/crs.py` | CRS database model |

## CRS Completeness Criteria

A CRS is considered complete when:

**Required (all must be filled):**
- Project title
- Project description
- At least 1 functional requirement

**Optional (at least 2 must be filled):**
- Project objectives
- Target users
- Timeline constraints
- Budget constraints
- Success metrics

## Environment Requirements

- `GROQ_API_KEY`: Required for LLM-powered CRS generation
- ChromaDB: For semantic memory storage