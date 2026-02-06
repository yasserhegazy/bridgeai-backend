# 🌉 BridgeAI Backend

<div align="center">

**AI-Powered Requirements Engineering Backend - Multi-Agent System**

*Intelligent CRS generation through conversational AI and deep reasoning*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6B6B?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Anthropic](https://img.shields.io/badge/Claude-3.5_Sonnet-191919?style=for-the-badge)](https://www.anthropic.com/)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Core Features](#-core-features)
- [AI Architecture](#-ai-architecture)
- [Technology Stack](#-technology-stack)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Database Schema](#-database-schema)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

---

## 🎯 Overview

**BridgeAI Backend** is a sophisticated FastAPI-based server that powers an AI-native requirements engineering platform. It leverages **LangGraph** for multi-agent orchestration and **Claude 3.5 Sonnet** for advanced natural language understanding and structured data extraction.

### What Makes This Backend Unique

- 🤖 **Multi-Agent AI Pipeline**: LangGraph-orchestrated agents that collaborate to deliver professional CRS documents
- 🔄 **Real-time Streaming**: WebSocket-based live CRS generation with progressive updates
- 🎯 **Ambiguity Detection**: Proactive clarification before document generation
- 📊 **Industry Standards**: Support for BABOK, IEEE 830, ISO/IEC/IEEE 29148, and Agile formats
- 🔍 **Vector Memory**: ChromaDB for semantic requirement storage and retrieval
- 📝 **Audit Trail**: Complete versioning and change tracking for all documents
- 🚀 **Background Processing**: Asynchronous CRS generation with task queuing

---

## ✨ Core Features

### 🤖 Multi-Agent AI System

#### Agent Architecture
BridgeAI implements a sophisticated multi-agent system using **LangGraph** for orchestration:

1. **Clarification Agent** (`app/ai/nodes/clarification/`)
   - **Purpose**: Detect ambiguities and request clarification
   - **Model**: Claude 3.5 Sonnet (reasoning & structured output)
   - **Capabilities**:
     - Semantic ambiguity detection in user requirements
     - Context-aware clarification question generation
     - Intent classification (requirement vs. greeting vs. question)
     - Conversation state tracking
   - **Output**: Targeted questions to resolve unclear requirements

2. **Template Filler Agent** (`app/ai/nodes/template_filler/`)
   - **Purpose**: Extract and map requirements to structured CRS templates
   - **Model**: Claude 3.5 Sonnet (structured extraction)
   - **Capabilities**:
     - Multi-pattern support (BABOK, IEEE 830, ISO 29148, Agile)
     - 15+ section extraction (objectives, requirements, constraints, etc.)
     - Field source tracking for transparency
     - Completeness validation with quality checks
     - Vocabulary enforcement (SHALL, SHOULD, MUST, MAY, WILL)
   - **Output**: Fully structured CRS document with metadata

3. **Memory Agent** (`app/ai/nodes/memory_node.py`)
   - **Purpose**: Store and retrieve requirements from vector database
   - **Technology**: ChromaDB with sentence transformers
   - **Capabilities**:
     - Semantic embedding of requirements
     - Context-aware memory retrieval
     - Project-specific memory isolation
     - Conversation history management
   - **Output**: Relevant historical context for current conversation

4. **Suggestions Agent** (`app/ai/nodes/suggestions/`)
   - **Purpose**: Generate intelligent suggestions for requirement improvements
   - **Model**: Claude 3 Haiku (speed & cost optimization)
   - **Capabilities**:
     - Suggest missing requirements based on project context
     - Identify gaps in functional/non-functional requirements
     - Recommend industry best practices
   - **Output**: Actionable suggestions for requirement completeness

#### LangGraph Workflow

```python
User Input
    ↓
Clarification Agent
    ├─→ [Ambiguities Found] → Return clarification questions → END
    └─→ [No Ambiguities] → Template Filler Agent
                               ↓
                    Extract & Structure Requirements
                               ↓
                     Memory Agent (Store in ChromaDB)
                               ↓
                         Suggestions Agent
                               ↓
                      Return CRS Document → END
```

### 🔄 Real-time CRS Generation

#### Streaming Architecture
- **WebSocket Server**: Real-time bidirectional communication
- **Background Worker**: Asynchronous task processing with retry logic
- **Event Bus**: Publish/subscribe pattern for progressive updates
- **JSON Patch Streaming**: Efficient incremental document updates
- **Progress Tracking**: Step-by-step status, progress percentage, and error handling

#### Background Generation Features
- **Task Queue**: FIFO queue with priority support
- **Retry Mechanism**: Exponential backoff with configurable max retries
- **Error Recovery**: Graceful degradation and error reporting
- **Resource Management**: Worker lifecycle management and cleanup
- **Status Monitoring**: Real-time task status tracking

### 📊 CRS Pattern Support

#### Supported Standards

1. **BABOK** (Business Analysis Body of Knowledge)
   - Business need and gap analysis focused
   - Stakeholder-centric requirements
   - Current state vs. future state analysis
   - Solution scope definition

2. **IEEE 830** (Software Requirements Specification)
   - Traditional waterfall-style specification
   - Detailed functional and non-functional requirements
   - Interface specifications
   - System operations and use cases

3. **ISO/IEC/IEEE 29148** (Systems & Software Engineering)
   - International standard for requirements engineering
   - Stakeholder needs and system requirements
   - Verification and validation criteria
   - Compliance and interoperability focus

4. **Agile User Stories**
   - User story format (As a... I want to... So that...)
   - Acceptance criteria with Gherkin syntax
   - Sprint-ready backlog items
   - Epic and story hierarchy

### 🔐 Authentication & Authorization

#### Authentication Methods
- **JWT Tokens**: Secure stateless authentication
- **Google OAuth 2.0**: Social login integration
- **Bcrypt Hashing**: Password encryption with salt
- **Token Refresh**: Auto-renewal for extended sessions
- **OTP Support**: Email-based verification (future enhancement)

#### Authorization System
- **Role-Based Access Control (RBAC)**:
  - **Client**: Create projects, chat with AI, submit CRS
  - **Business Analyst (BA)**: Review, approve/reject CRS, manage teams
  - **Owner**: Full team management, member invitation
  - **Admin**: User management, system configuration
  - **Member**: Read-only project access
  - **Viewer**: Browse-only permissions

- **Permission Service**: Centralized authorization checks
- **Project-Level Security**: Team-based access control
- **CRS Access Control**: Creator and team member validation

### 💾 Database Management

#### SQLAlchemy ORM
- **Models**: 12+ database models with full relationships
- **Migrations**: Alembic for version-controlled schema changes
- **Connection Pooling**: Optimized database connections
- **Transaction Management**: ACID compliance

#### Key Models
- **User**: Authentication, profiles, roles
- **Team**: Collaborative workspaces
- **Invitation**: Team member onboarding
- **Project**: Project metadata and status
- **ChatSession**: Conversation management
- **Message**: Chat history storage
- **CRSDocument**: Versioned requirement specifications
- **CRSAudit**: Document change tracking
- **Comment**: Inline CRS feedback
- **Notification**: User activity alerts
- **AIMemoryIndex**: Vector database references

### 🔍 Vector Memory (ChromaDB)

#### Semantic Storage
- **Embedding Model**: Sentence transformers for requirement vectors
- **Collections**: Project-isolated memory spaces
- **Metadata**: Rich contextual information with each embedding
- **Similarity Search**: Fast semantic retrieval

#### Memory Features
- **Conversation Context**: Store and retrieve chat history
- **Requirement Indexing**: Semantic search across requirements
- **Project Memory**: Isolated memory per project
- **Relevance Scoring**: Confidence-based retrieval

### 📤 Export System

#### Supported Formats

1. **PDF Export**
   - Professional corporate styling with headers and footers
   - Custom fonts and branded layout
   - Table of contents generation
   - Page numbering and sections
   - **Library**: xhtml2pdf (WeasyPrint) for HTML-to-PDF conversion

2. **Markdown Export**
   - Clean, readable plain text format
   - Compatible with version control systems
   - Easy editing and collaboration
   - Portable across platforms

3. **CSV Export**
   - Structured tabular data
   - Requirements-only option for filtering
   - Excel-compatible format
   - Integration-friendly output

#### Export Features
- **Custom Templates**: Industry-standard document formatting
- **Version Stamping**: Automatic version numbers in filenames
- **Batch Export**: Export multiple documents at once
- **Streaming Response**: Memory-efficient large file handling

### 🔔 Notification System

#### Notification Types
- **Project Events**: Approval, rejection, status changes
- **Team Events**: Invitations, member additions, role changes
- **CRS Events**: Creation, updates, review status, comments
- **System Events**: Errors, maintenance, updates

#### Notification Features
- **Real-time Delivery**: WebSocket push notifications
- **Email Notifications**: SMTP integration for alerts
- **In-App Notifications**: Persistent notification center
- **Read Status**: Track viewed notifications
- **Action Links**: Direct navigation to relevant content

### 🔒 Security Features

#### Security Measures
- **CORS Protection**: Configurable allowed origins
- **Rate Limiting**: SlowAPI for request throttling (429 responses)
- **Request Size Limits**: 10MB max request body
- **Input Validation**: Pydantic schema validation
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy
- **XSS Protection**: Output sanitization
- **Security Headers**: Custom middleware for security headers
- **Password Policies**: Minimum length, complexity requirements

#### Security Headers Middleware
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HSTS)

---

## 🏗️ AI Architecture

### Neural Extraction Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                   NEURAL EXTRACTION PIPELINE                     │
└─────────────────────────────────────────────────────────────────┘

1️⃣ User Message Received
   └─> WebSocket: /api/projects/{id}/chats/{id}/ws
   └─> Authenticated via JWT token
   └─> Message persisted to MySQL

2️⃣ LangGraph Workflow Initiated
   └─> Entry Point: Clarification Agent
   └─> AgentState initialized with:
       • user_input (latest message)
       • conversation_history (full chat context)
       • extracted_fields (previous CRS data)
       • project_id, user_id, db session

3️⃣ Clarification Agent (Claude 3.5 Sonnet)
   ├─> Detect Ambiguities:
   │   • Vague requirements
   │   • Missing critical details
   │   • Unclear success criteria
   │   • Conflicting specifications
   │
   ├─> Analyze Intent:
   │   • "greeting" → Friendly response
   │   • "question" → Answer question
   │   • "requirement" → Extract requirement
   │
   └─> Generate Questions (if needed):
       • 2-4 targeted clarification questions
       • Context-aware and specific
       • Actionable and easy to answer

4️⃣ Routing Decision
   ├─> [Clarification Needed]
   │   └─> Return questions to client via WebSocket
   │   └─> END → Wait for user response
   │
   └─> [No Clarification Needed]
       └─> Proceed to Template Filler Agent

5️⃣ Template Filler Agent (Claude 3.5 Sonnet)
   ├─> Select Pattern (BABOK, IEEE 830, ISO 29148, Agile)
   │
   ├─> Extract Structured Data:
   │   • Project Title & Description
   │   • Objectives (min 2, each 15+ words)
   │   • Functional Requirements (min 5, each 30+ words)
   │   • Non-Functional Requirements (performance, security, scalability)
   │   • Target Users & Stakeholders
   │   • Technology Stack (frontend, backend, database, other)
   │   • Integrations & Third-party services
   │   • Constraints (budget, timeline, technical)
   │   • Success Metrics & Acceptance Criteria
   │   • Assumptions, Risks, Out-of-Scope items
   │
   ├─> Apply Vocabulary Rules:
   │   • SHALL: Mandatory functional requirements
   │   • SHOULD: Recommended features
   │   • MAY: Optional features
   │   • MUST: Non-negotiable constraints
   │   • WILL: Future events
   │   • CAN: Capabilities
   │
   ├─> Validate Completeness:
   │   • Essential fields populated
   │   • Quality thresholds met (30+ char descriptions)
   │   • Requirements count sufficient
   │   • No hallucinated content
   │
   └─> Generate Summary:
       • 3-5 key extraction points
       • Overall quality summary
       • Completeness percentage
       • Missing/weak fields identification

6️⃣ Memory Agent (ChromaDB)
   ├─> Embed Requirements:
   │   • Convert to vector embeddings
   │   • Store with metadata (project_id, timestamp, source)
   │
   └─> Store Conversation:
       • Save chat context for retrieval
       • Enable semantic search
       • Project-isolated collections

7️⃣ Background CRS Generation (Async Worker)
   ├─> Task Queue:
   │   • FIFO queue with priority support
   │   • Retry logic (exponential backoff)
   │   • Max 3 retries per task
   │
   ├─> Streaming Updates (JSON Patch):
   │   • Progressive CRS generation
   │   • Real-time progress percentage
   │   • Step-by-step status updates
   │   • Error reporting
   │
   └─> Persistence:
       • Save to MySQL (CRSDocument table)
       • Versioning (auto-increment)
       • Audit trail creation
       • Field source tracking

8️⃣ Response to Client
   ├─> WebSocket Message:
   │   • AI message (summary + completion status)
   │   • CRS preview (structured JSON)
   │   • Completeness metadata
   │   • Summary points
   │
   └─> Frontend Update:
       • CRS Panel live update
       • Progress bar animation
       • Section-by-section reveal
```

### Agent State Management

```python
class AgentState(TypedDict):
    """Shared state across all agents in LangGraph workflow"""
    
    # Input
    user_input: str                    # Latest user message
    conversation_history: list         # Full chat context
    
    # Context
    project_id: Optional[int]          # Current project
    user_id: Optional[int]             # Current user
    session_id: Optional[int]          # Chat session
    db: Optional[Session]              # Database session
    
    # Extracted Data
    extracted_fields: dict             # Previous CRS data
    crs_pattern: str                   # BABOK, IEEE 830, ISO 29148, Agile
    
    # Agent Outputs
    clarification_needed: bool         # If questions required
    clarification_questions: list      # Questions to ask
    intent: str                        # greeting/question/requirement
    
    crs_template: Optional[dict]       # Structured CRS document
    crs_content: Optional[str]         # JSON string of CRS
    summary_points: list               # Key extraction points
    field_sources: dict                # Traceability mapping
    
    # Memory
    memory_results: list               # ChromaDB retrieval
    
    # Workflow Control
    output: str                        # Response to client
    last_node: str                     # Last executed agent
```

### LLM Configuration

#### Model Selection Strategy

```python
# Clarification: Needs reasoning → Claude 3.5 Sonnet
LLM_CLARIFICATION_MODEL = "claude-3-5-sonnet-20240620"
LLM_CLARIFICATION_TEMPERATURE = 0.3  # Balanced creativity
LLM_CLARIFICATION_MAX_TOKENS = 2048

# Template Filler: Needs structured extraction → Claude 3.5 Sonnet
LLM_TEMPLATE_FILLER_MODEL = "claude-3-5-sonnet-20240620"
LLM_TEMPLATE_FILLER_TEMPERATURE = 0.2  # More deterministic
LLM_TEMPLATE_FILLER_MAX_TOKENS = 4096  # Large documents

# Suggestions: Speed & cost → Claude 3 Haiku
LLM_SUGGESTIONS_MODEL = "claude-3-haiku-20240307"
LLM_SUGGESTIONS_TEMPERATURE = 0.4
LLM_SUGGESTIONS_MAX_TOKENS = 1024
```

#### LLM Factory Pattern

Centralized LLM instance creation in `app/ai/llm_factory.py`:
- **Singleton Pattern**: Reusable LLM instances
- **Configuration Injection**: Environment-based model selection
- **Error Handling**: Graceful fallback to default models
- **Type Safety**: Fully typed with Pydantic

---

## 🛠️ Technology Stack

### Core Framework
- **FastAPI** - Modern async web framework
- **Uvicorn** - ASGI server with WebSocket support
- **Python 3.11+** - Latest Python features

### AI & LLM
- **LangGraph** - Multi-agent workflow orchestration
- **LangChain Core** - LLM abstraction layer
- **Anthropic Claude 3.5 Sonnet** - Primary reasoning model
- **Anthropic Claude 3 Haiku** - Fast inference model
- **Sentence Transformers** - Semantic embeddings

### Database
- **SQLAlchemy 2.0** - Modern async ORM
- **PyMySQL** - MySQL database driver
- **Alembic** - Database migration management
- **MySQL** - Relational database

### Vector Database
- **ChromaDB** - Vector storage for semantic search
- **Sentence Transformers** - Embedding generation

### Authentication & Security
- **python-jose** - JWT token handling
- **passlib** - Password hashing (bcrypt)
- **bcrypt** - Secure password encryption
- **google-auth** - Google OAuth integration
- **SlowAPI** - Rate limiting middleware

### Export & Document Generation
- **xhtml2pdf** - PDF generation from HTML
- **Markdown** - Markdown to HTML conversion
- **Jinja2** - HTML templating

### Testing
- **pytest** - Testing framework
- **httpx** - Async HTTP client for testing
- **pytest-asyncio** - Async test support

### Utilities
- **python-dotenv** - Environment variable management
- **pydantic** - Data validation with type hints
- **pydantic-settings** - Settings management
- **email-validator** - Email validation
- **python-multipart** - Form data parsing

### Communication
- **WebSockets** - Real-time bidirectional communication
- **SMTP** - Email notifications

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.11 or higher
- **MySQL** 8.0 or higher
- **pip** or **poetry** for package management
- **Anthropic API Key** (Claude access)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/KhaledJamalKwaik/bridgeai-backend.git
   cd bridgeai-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   
   Create a `.env` file in the root directory:
   ```env
   # Database
   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/bridgeai
   
   # Authentication
   SECRET_KEY=your-secret-key-here-min-32-chars
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   
   # Google OAuth
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   
   # AI Models
   ANTHROPIC_API_KEY=your-anthropic-api-key
   LLM_CLARIFICATION_MODEL=claude-3-5-sonnet-20240620
   LLM_TEMPLATE_FILLER_MODEL=claude-3-5-sonnet-20240620
   
   # Email (Optional)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_FROM_EMAIL=noreply@bridgeai.com
   
   # Frontend
   FRONTEND_URL=http://localhost:3000
   ```

5. **Database Setup**
   
   Create MySQL database:
   ```bash
   mysql -u root -p
   CREATE DATABASE bridgeai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   EXIT;
   ```

6. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

7. **Start the server**
   ```bash
   # Development
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Production
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

8. **Verify Installation**
   
   Open [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI

### Quick Start

1. **Register a new user**
   ```bash
   POST http://localhost:8000/api/auth/register
   {
     "email": "user@example.com",
     "password": "SecurePass123",
     "full_name": "John Doe",
     "role": "client"
   }
   ```

2. **Login**
   ```bash
   POST http://localhost:8000/api/auth/login
   {
     "username": "user@example.com",
     "password": "SecurePass123"
   }
   ```

3. **Create a team**
   ```bash
   POST http://localhost:8000/api/teams
   Authorization: Bearer <your-token>
   {
     "name": "My Team",
     "description": "Team description"
   }
   ```

4. **Create a project**
   ```bash
   POST http://localhost:8000/api/projects
   Authorization: Bearer <your-token>
   {
     "name": "My Project",
     "description": "Project description",
     "team_id": 1
   }
   ```

5. **Start a chat session** (via WebSocket)
   ```
   ws://localhost:8000/api/projects/1/chats/1/ws?token=<your-token>
   ```

---

## 📁 Project Structure

```
bridgeai-backend/
├── alembic/                      # Database migrations
│   ├── versions/                 # Migration scripts
│   ├── env.py                    # Migration environment
│   └── script.py.mako            # Migration template
│
├── app/                          # Main application package
│   ├── __init__.py               # App version
│   ├── main.py                   # FastAPI application entry
│   │
│   ├── ai/                       # AI/LLM Module
│   │   ├── graph.py              # LangGraph workflow definition
│   │   ├── state.py              # AgentState TypedDict
│   │   ├── llm_factory.py        # LLM instance factory
│   │   ├── chroma_manager.py     # ChromaDB initialization
│   │   ├── memory_service.py     # Vector memory operations
│   │   ├── memory_utils.py       # Memory utilities
│   │   │
│   │   └── nodes/                # LangGraph Agent Nodes
│   │       ├── clarification/    # Clarification Agent
│   │       │   ├── clarification_node.py      # Node entry point
│   │       │   └── llm_ambiguity_detector.py  # Ambiguity detection
│   │       │
│   │       ├── template_filler/  # Template Filler Agent
│   │       │   ├── template_filler_node.py    # Node entry point
│   │       │   └── llm_template_filler.py     # CRS extraction
│   │       │
│   │       ├── suggestions/      # Suggestions Agent
│   │       │   ├── suggestions_node.py        # Node entry point
│   │       │   └── llm_suggestions_generator.py
│   │       │
│   │       ├── memory_node.py    # Memory storage node
│   │       └── echo_node.py      # Echo/test node
│   │
│   ├── api/                      # API Routes
│   │   ├── __init__.py           # API router aggregation
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── ai.py                 # AI/LLM test endpoints
│   │   ├── memory.py             # Memory management endpoints
│   │   ├── projects.py           # Project CRUD
│   │   ├── invitations.py        # Team invitations
│   │   ├── notifications.py      # Notifications
│   │   ├── comments.py           # CRS comments
│   │   ├── suggestions.py        # Requirement suggestions
│   │   ├── exports.py            # Generic export endpoints
│   │   │
│   │   ├── chats/                # Chat endpoints
│   │   │   ├── rest.py           # REST endpoints for chats
│   │   │   └── websocket.py      # WebSocket chat endpoint
│   │   │
│   │   ├── crs/                  # CRS endpoints
│   │   │   ├── crud.py           # CRS CRUD operations
│   │   │   ├── export.py         # CRS export (PDF/CSV/MD)
│   │   │   ├── versioning.py     # CRS version management
│   │   │   └── workflow.py       # CRS workflow (submit/approve)
│   │   │
│   │   └── teams/                # Team endpoints
│   │       ├── crud.py           # Team CRUD
│   │       └── members.py        # Team member management
│   │
│   ├── core/                     # Core configuration
│   │   ├── config.py             # Settings (Pydantic)
│   │   ├── security.py           # Auth utilities (JWT, hashing)
│   │   ├── middleware.py         # Security headers middleware
│   │   ├── rate_limit.py         # Rate limiting config
│   │   └── events.py             # Event bus for streaming
│   │
│   ├── db/                       # Database
│   │   └── session.py            # SQLAlchemy session factory
│   │
│   ├── exceptions/               # Custom exceptions
│   │   └── custom_exceptions.py  # App-specific errors
│   │
│   ├── models/                   # SQLAlchemy Models
│   │   ├── user.py               # User model
│   │   ├── team.py               # Team model
│   │   ├── invitation.py         # Invitation model
│   │   ├── project.py            # Project model
│   │   ├── session_model.py      # ChatSession model
│   │   ├── message.py            # Message model
│   │   ├── crs.py                # CRSDocument model
│   │   ├── audit.py              # CRSAudit model
│   │   ├── comment.py            # Comment model
│   │   ├── notification.py       # Notification model
│   │   ├── ai_memory_index.py    # Memory index model
│   │   └── user_otp.py           # OTP model (future)
│   │
│   ├── repositories/             # Data Access Layer
│   │   └── (future repository pattern)
│   │
│   ├── schemas/                  # Pydantic Schemas
│   │   ├── auth.py               # Auth request/response schemas
│   │   ├── project.py            # Project schemas
│   │   ├── team.py               # Team schemas
│   │   ├── chat.py               # Chat schemas
│   │   ├── crs.py                # CRS schemas
│   │   ├── comment.py            # Comment schemas
│   │   └── notification.py       # Notification schemas
│   │
│   ├── services/                 # Business Logic Layer
│   │   ├── auth_service.py       # Authentication logic
│   │   ├── project_service.py    # Project operations
│   │   ├── team_service.py       # Team operations
│   │   ├── invitation_service.py # Invitation logic
│   │   ├── chat_service.py       # Chat operations
│   │   ├── crs_service.py        # CRS operations
│   │   ├── comment_service.py    # Comment operations
│   │   ├── notification_service.py # Notification logic
│   │   ├── permission_service.py # Authorization checks
│   │   ├── file_storage_service.py # File upload handling
│   │   ├── export_service.py     # Export formatting
│   │   └── background_crs_generator.py # Background CRS worker
│   │
│   └── utils/                    # Utility functions
│       └── (utility modules)
│
├── chroma/                       # ChromaDB storage
├── chroma_db/                    # Alternative ChromaDB path
├── project_memories/             # Project-specific memory files
├── public/                       # Public assets
│   └── avatars/                  # User avatar uploads
│
├── tests/                        # Test suite
│   ├── api/                      # API endpoint tests
│   ├── services/                 # Service layer tests
│   └── conftest.py               # Pytest fixtures
│
├── docs/                         # Documentation
│   └── CSV_EXPORT.md             # CSV export documentation
│
├── htmlcov/                      # Test coverage reports
│
├── alembic.ini                   # Alembic configuration
├── coverage.json                 # Coverage data
├── Dockerfile                    # Production Docker image
├── Dockerfile.dev                # Development Docker image
├── nixpacks.toml                 # Nixpacks deployment config
├── requirements.txt              # Python dependencies
├── requirements-test.txt         # Test dependencies
├── pytest.ini                    # Pytest configuration
├── pre_commit_check.py           # Pre-commit validation
├── quick_fix_flake8.py           # Code formatting helper
└── README.md                     # This file
```

---

## 📚 API Documentation

### Interactive Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Core API Endpoints

#### Authentication (`/api/auth`)
```
POST   /api/auth/register          Register new user
POST   /api/auth/login             Login with email/password
POST   /api/auth/google            Login with Google OAuth
POST   /api/auth/refresh           Refresh JWT token
GET    /api/auth/me                Get current user profile
```

#### Teams (`/api/teams`)
```
GET    /api/teams                  List user's teams
POST   /api/teams                  Create new team
GET    /api/teams/{id}             Get team details
PUT    /api/teams/{id}             Update team
DELETE /api/teams/{id}             Delete team
GET    /api/teams/{id}/members     List team members
POST   /api/teams/{id}/invite      Invite team member
DELETE /api/teams/{id}/members/{user_id}  Remove member
```

#### Projects (`/api/projects`)
```
GET    /api/projects               List user's projects
POST   /api/projects               Create new project
GET    /api/projects/{id}          Get project details
PUT    /api/projects/{id}          Update project
DELETE /api/projects/{id}          Delete project
POST   /api/projects/{id}/approve  Approve project (BA only)
POST   /api/projects/{id}/reject   Reject project (BA only)
```

#### Chats (`/api/projects/{id}/chats`)
```
GET    /api/projects/{id}/chats              List project chats
POST   /api/projects/{id}/chats              Create chat session
GET    /api/projects/{id}/chats/{chat_id}    Get chat details
WS     /api/projects/{id}/chats/{chat_id}/ws WebSocket connection
GET    /api/projects/{id}/chats/{chat_id}/messages  Get messages
```

#### CRS (`/api/crs`)
```
GET    /api/crs                    List all CRS documents
GET    /api/crs/{id}               Get CRS document
PUT    /api/crs/{id}               Update CRS content
DELETE /api/crs/{id}               Delete CRS
POST   /api/crs/{id}/submit        Submit for review
POST   /api/crs/{id}/approve       Approve CRS (BA only)
POST   /api/crs/{id}/reject        Reject CRS (BA only)
POST   /api/crs/{id}/export        Export as PDF/CSV/Markdown
GET    /api/crs/{id}/versions      Get version history
GET    /api/crs/{id}/audit         Get audit trail
GET    /api/crs/project/{project_id}/latest  Get latest CRS
GET    /api/crs/session/{session_id}         Get session CRS
GET    /api/crs/session/{session_id}/preview Preview CRS
```

#### Comments (`/api/comments`)
```
GET    /api/comments/crs/{crs_id}  Get CRS comments
POST   /api/comments               Add comment
PUT    /api/comments/{id}          Update comment
DELETE /api/comments/{id}          Delete comment
```

#### Notifications (`/api/notifications`)
```
GET    /api/notifications          List user notifications
PUT    /api/notifications/{id}/read  Mark as read
DELETE /api/notifications/{id}    Delete notification
```

#### Invitations (`/api/invitations`)
```
GET    /api/invitations/pending    List pending invitations
POST   /api/invitations/{token}/accept  Accept invitation
POST   /api/invitations/{token}/decline Decline invitation
```

### WebSocket Protocol

#### Connection
```
ws://localhost:8000/api/projects/{project_id}/chats/{chat_id}/ws?token={jwt_token}
```

#### Message Format (Client → Server)
```json
{
  "type": "message",
  "content": "I want to build an e-commerce platform",
  "session_id": 1
}
```

#### Message Format (Server → Client)
```json
{
  "type": "ai_message",
  "content": "I'll help you build an e-commerce platform. Can you tell me more about your target audience?",
  "sender_type": "ai",
  "timestamp": "2026-02-06T12:00:00Z",
  "crs_preview": {
    "content": "{\"project_title\": \"E-commerce Platform\", ...}",
    "completeness_percentage": 45,
    "summary_points": ["Extracted e-commerce requirements", "Identified target users"]
  }
}
```

#### CRS Streaming Events
```json
{
  "type": "crs_update",
  "status": "generating",
  "progress": 65,
  "step": "Extracting functional requirements",
  "crs_template": { ... },
  "summary_points": ["Point 1", "Point 2"]
}
```

---

## 💾 Database Schema

### Core Tables

#### users
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
email           VARCHAR(255) UNIQUE NOT NULL
password_hash   VARCHAR(255)
full_name       VARCHAR(255)
role            ENUM('client', 'ba', 'admin')
google_id       VARCHAR(255) UNIQUE
avatar_url      VARCHAR(500)
is_active       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### teams
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
name            VARCHAR(255) NOT NULL
description     TEXT
status          ENUM('active', 'archived')
created_by      INT FOREIGN KEY → users(id)
created_at      TIMESTAMP
```

#### invitations
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
team_id         INT FOREIGN KEY → teams(id)
email           VARCHAR(255) NOT NULL
role            ENUM('owner', 'admin', 'member', 'viewer')
token           VARCHAR(255) UNIQUE
invited_by      INT FOREIGN KEY → users(id)
status          ENUM('pending', 'accepted', 'declined')
expires_at      TIMESTAMP
created_at      TIMESTAMP
```

#### projects
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
name            VARCHAR(255) NOT NULL
description     TEXT
team_id         INT FOREIGN KEY → teams(id)
created_by      INT FOREIGN KEY → users(id)
status          ENUM('pending', 'approved', 'rejected', 'active', 'completed', 'archived')
approved_by     INT FOREIGN KEY → users(id)
approved_at     TIMESTAMP
rejection_reason TEXT
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### chat_sessions
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
project_id      INT FOREIGN KEY → projects(id)
title           VARCHAR(255)
status          ENUM('active', 'archived')
created_by      INT FOREIGN KEY → users(id)
created_at      TIMESTAMP
```

#### messages
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
session_id      INT FOREIGN KEY → chat_sessions(id)
sender_type     ENUM('client', 'ba', 'ai')
sender_id       INT FOREIGN KEY → users(id)
content         TEXT NOT NULL
timestamp       TIMESTAMP
```

#### crs_documents
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
project_id      INT FOREIGN KEY → projects(id)
chat_session_id INT FOREIGN KEY → chat_sessions(id)
content         LONGTEXT (JSON)
status          ENUM('draft', 'under_review', 'approved', 'rejected')
pattern         ENUM('babok', 'ieee_830', 'iso_iec_ieee_29148', 'agile_user_stories')
version         INT DEFAULT 1
edit_version    INT DEFAULT 1
summary_points  JSON
field_sources   JSON
created_by      INT FOREIGN KEY → users(id)
approved_by     INT FOREIGN KEY → users(id)
reviewed_at     TIMESTAMP
rejection_reason TEXT
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### crs_audits
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
crs_id          INT FOREIGN KEY → crs_documents(id)
action          ENUM('created', 'updated', 'submitted', 'approved', 'rejected')
performed_by    INT FOREIGN KEY → users(id)
changed_fields  JSON
reason          TEXT
timestamp       TIMESTAMP
```

#### comments
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
crs_id          INT FOREIGN KEY → crs_documents(id)
user_id         INT FOREIGN KEY → users(id)
content         TEXT NOT NULL
section         VARCHAR(255)
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### notifications
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
user_id         INT FOREIGN KEY → users(id)
type            VARCHAR(50)
reference_id    INT
title           VARCHAR(255)
message         TEXT
metadata        JSON
is_read         BOOLEAN DEFAULT FALSE
created_at      TIMESTAMP
```

#### ai_memory_index
```sql
id              INT PRIMARY KEY AUTO_INCREMENT
project_id      INT FOREIGN KEY → projects(id)
session_id      INT FOREIGN KEY → chat_sessions(id)
chroma_doc_id   VARCHAR(255) UNIQUE
content_preview TEXT
embedding_model VARCHAR(100)
created_at      TIMESTAMP
```

---

## ⚙️ Configuration

### Environment Variables

#### Required Settings
```env
# Database
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db

# Security
SECRET_KEY=min-32-character-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AI
ANTHROPIC_API_KEY=sk-ant-...
```

#### Optional Settings
```env
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-password

# LLM Configuration
LLM_CLARIFICATION_MODEL=claude-3-5-sonnet-20240620
LLM_CLARIFICATION_TEMPERATURE=0.3
LLM_TEMPLATE_FILLER_MODEL=claude-3-5-sonnet-20240620
LLM_TEMPLATE_FILLER_TEMPERATURE=0.2

# Security
MAX_REQUEST_SIZE=10485760  # 10MB
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5

# Frontend
FRONTEND_URL=http://localhost:3000
```

### Alembic Configuration

#### Create Migration
```bash
alembic revision --autogenerate -m "Description"
```

#### Apply Migrations
```bash
alembic upgrade head
```

#### Rollback Migration
```bash
alembic downgrade -1
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/api/test_auth.py

# Run specific test
pytest tests/api/test_auth.py::test_register_user

# Run with verbose output
pytest -v
```

### Test Coverage

View coverage report:
```bash
open htmlcov/index.html  # Mac/Linux
start htmlcov/index.html  # Windows
```

### Pre-commit Checks

```bash
python pre_commit_check.py
```

This runs:
- Flake8 linting
- Code formatting checks
- Import sorting

---

## 🚢 Deployment

### Docker Deployment

#### Build Image
```bash
docker build -f Dockerfile -t bridgeai-backend .
```

#### Run Container
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=mysql+pymysql://... \
  -e ANTHROPIC_API_KEY=... \
  -e SECRET_KEY=... \
  bridgeai-backend
```

### Production Checklist

- [ ] Set `SECRET_KEY` to random 32+ character string
- [ ] Configure production `DATABASE_URL`
- [ ] Set up HTTPS/SSL certificates
- [ ] Configure CORS for production frontend URL
- [ ] Set up environment variables securely (not in code)
- [ ] Enable request logging and monitoring
- [ ] Configure rate limiting
- [ ] Set up database backups
- [ ] Configure email SMTP for notifications
- [ ] Set up ChromaDB persistent storage
- [ ] Configure file upload limits
- [ ] Set up error tracking (Sentry, etc.)

### Uvicorn Production

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --access-log
```

### Environment-Specific Configuration

```python
# app/core/config.py
from functools import lru_cache

@lru_cache()
def get_settings():
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return ProductionSettings()
    return DevelopmentSettings()
```

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linting (`python pre_commit_check.py`)
6. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
7. Push to the branch (`git push origin feature/AmazingFeature`)
8. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Write docstrings for all public functions
- Keep functions under 50 lines when possible
- Use meaningful variable names
- Add comments for complex logic

### Commit Message Format

```
feat: Add new feature
fix: Fix bug
docs: Update documentation
test: Add tests
refactor: Refactor code
style: Format code
chore: Update dependencies
```

---

## 📄 License

This project is part of a Graduation Project. All rights reserved.

---

## 📞 Support

For questions or support:
- **GitHub Issues**: [Report bugs or request features](https://github.com/KhaledJamalKwaik/bridgeai-backend/issues)
- **Email**: support@bridgeai.com (if available)

---

## 🙏 Acknowledgments

- **LangChain AI** - For the amazing LangGraph framework
- **Anthropic** - For Claude 3.5 Sonnet and Haiku models
- **FastAPI** - For the modern async web framework
- **ChromaDB** - For efficient vector storage

---

<div align="center">

**Made with ❤️ by the BridgeAI Team**

*Transforming Requirements Engineering with Multi-Agent AI*

**Backend Version: 1.0.0**

</div>
