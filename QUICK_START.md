# Clarification Agent - Quick Start Guide

## 🚀 Getting Started

The Clarification Agent is now fully integrated into BridgeAI and ready to use!

---

## ✅ What's Been Implemented

1. **Ambiguity Detection System** - Detects 6 types of issues in requirements
2. **LangGraph Integration** - Seamlessly integrated into the workflow
3. **RESTful API Endpoints** - Two new endpoints for requirement analysis
4. **Comprehensive Testing** - Full test suite with 4 scenarios
5. **Complete Documentation** - README, architecture diagrams, and examples

---

## 📦 Installation Check

All dependencies are already installed in your venv. Verify with:

```bash
cd /home/abdelrahman/project/bridgeai-backend
source venv/bin/activate
python -c "from app.ai.nodes.clarification import AmbiguityDetector; print('✓ Ready to use!')"
```

---

## 🧪 Quick Test

Run the test suite to see the clarification agent in action:

```bash
python test_clarification_agent.py
```

**Expected Output:**
- Test Case 1: Detects vague requirements ✓
- Test Case 2: Identifies missing critical fields ✓
- Test Case 3: Catches ambiguous quantifiers ✓
- Test Case 4: Handles complete requirements ✓

---

## 🔌 API Endpoints

### 1. Analyze Requirements

```bash
curl -X POST http://localhost:8000/api/ai/analyze-requirements \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "I need a web application",
    "conversation_history": [],
    "extracted_fields": {}
  }'
```

**Response:**
```json
{
  "output": "I'd like to clarify a few points...",
  "clarification_questions": [
    "What would you like to name this project?",
    "Could you provide a brief description..."
  ],
  "ambiguities": [...],
  "needs_clarification": true,
  "last_node": "clarification"
}
```

### 2. Process Complete Requirement

```bash
curl -X POST http://localhost:8000/api/ai/process-requirement \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Your requirement text here",
    "conversation_history": [],
    "extracted_fields": {}
  }'
```

---

## 💻 Code Usage

### Simple Example

```python
from app.ai.nodes.clarification import AmbiguityDetector

# Initialize detector
detector = AmbiguityDetector()

# Analyze user input
user_input = "I want a fast system"
context = {"conversation_history": [], "extracted_fields": {}}

# Detect ambiguities
ambiguities = detector.detect_ambiguities(user_input, context)

# Generate questions
questions = detector.generate_clarification_questions(ambiguities)

for i, question in enumerate(questions, 1):
    print(f"{i}. {question}")
```

### Using LangGraph Workflow

```python
from app.ai.graph import create_graph
from app.ai.state import AgentState

# Create the graph
graph = create_graph()

# Prepare state
state: AgentState = {
    "user_input": "I need a web app",
    "conversation_history": [],
    "extracted_fields": {}
}

# Run workflow
result = graph.invoke(state)

# Check if clarification is needed
if result["needs_clarification"]:
    print("Clarification needed:")
    for q in result["clarification_questions"]:
        print(f"  - {q}")
else:
    print("Requirements are clear!")
```

---

## 🎯 Integration Example

### In Your Chat Handler

```python
from app.ai.graph import create_graph

graph = create_graph()

@router.post("/chat")
async def handle_chat(message: str, session_id: str):
    # Get conversation context
    history = get_conversation_history(session_id)
    extracted = get_extracted_fields(session_id)
    
    # Prepare state
    state = {
        "user_input": message,
        "conversation_history": history,
        "extracted_fields": extracted
    }
    
    # Run through clarification agent
    result = graph.invoke(state)
    
    if result["needs_clarification"]:
        # Send clarification questions to user
        return {
            "message": result["output"],
            "questions": result["clarification_questions"],
            "type": "clarification"
        }
    else:
        # Continue to CRS generation
        return {
            "message": "Requirements captured!",
            "type": "complete"
        }
```

---

## 📊 What Gets Detected

### 1. Missing Critical Fields
- ❌ Project name not specified
- ❌ No project description
- ❌ Target users unclear
- ❌ Main functionality missing
- ❌ Business goals undefined

### 2. Vague Language
- ❌ "fast", "user-friendly", "easy"
- ❌ "good", "better", "best"
- ❌ "simple", "clean", "nice"

### 3. Ambiguous Quantifiers
- ❌ "many", "few", "several"
- ❌ "some", "most", "often"
- ❌ "usually", "rarely", "sometimes"

### 4. Incomplete Requirements
- ❌ Missing user roles
- ❌ No outcome specified
- ❌ Lacks "so that" clause

### 5. Missing Non-Functional Requirements
- ❌ No performance criteria
- ❌ Security not addressed
- ❌ Scalability unclear
- ❌ Usability not specified

### 6. Undefined Technical Terms
- ❌ Acronyms without definition
- ❌ Technical jargon

---

## 🔄 Typical Workflow

```
1. Client enters requirement
   ↓
2. Clarification agent analyzes
   ↓
3. Are there ambiguities?
   ├─ YES → Return questions
   │         ↓
   │    Client answers
   │         ↓
   │    Go to step 2
   │
   └─ NO → Continue to template filling
             ↓
        Continue to CRS generation
```

---

## 🎓 Examples

### Example 1: Vague Input

**Input:** "I want a fast and user-friendly system"

**Detected Issues:**
- Missing: project name, description, users, functionality, goals
- Vague terms: "fast", "user-friendly"

**Questions Generated:**
1. What would you like to name this project?
2. Could you provide a brief description of what this project aims to achieve?
3. What are the main features or functionalities you need in this system?
4. What are the key business goals or objectives this system should support?
5. Could you provide more specific details? For example, what specific metrics define success?

### Example 2: Better Input

**Input:** 
```
Project name: Employee Management System
Description: A web-based system to manage employee records and attendance
Target users: HR managers and department heads
Main functionality: CRUD operations for employees, attendance tracking, monthly reports
Business goals: Reduce HR paperwork by 80% and streamline processes
```

**Result:** ✓ No clarification needed - requirements are clear!

---

## 📁 File Locations

```
Implementation:
  app/ai/nodes/clarification/
    ├── ambiguity_detector.py    # Core logic
    ├── clarification_node.py    # LangGraph node
    └── README.md                # Detailed docs

Integration:
  app/ai/state.py               # State definition
  app/ai/graph.py               # Workflow
  app/api/ai.py                 # API endpoints

Testing:
  test_clarification_agent.py   # Test suite

Documentation:
  CLARIFICATION_AGENT_SUMMARY.md        # Implementation summary
  CLARIFICATION_AGENT_ARCHITECTURE.md   # Architecture diagrams
  QUICK_START.md                        # This file
```

---

## 🐛 Troubleshooting

### Import Errors

```bash
# Ensure you're in the project directory and venv is activated
cd /home/abdelrahman/project/bridgeai-backend
source venv/bin/activate
```

### Module Not Found

```bash
# Verify the clarification package exists
ls -la app/ai/nodes/clarification/
# Should show: __init__.py, ambiguity_detector.py, clarification_node.py
```

### Test Failures

```bash
# Run with verbose output
python -v test_clarification_agent.py
```

---

## 📚 Further Reading

- **Full Documentation:** `app/ai/nodes/clarification/README.md`
- **Architecture:** `CLARIFICATION_AGENT_ARCHITECTURE.md`
- **Implementation Details:** `CLARIFICATION_AGENT_SUMMARY.md`
- **API Reference:** Check FastAPI docs at `/docs` when server is running

---

## 🎉 You're Ready!

The Clarification Agent is fully functional and integrated. Start using it by:

1. ✅ Running the test suite to verify
2. ✅ Testing the API endpoints
3. ✅ Integrating into your chat flow
4. ✅ Monitoring clarification quality

**Questions or Issues?** 
- Check the comprehensive README in the clarification folder
- Review the test_clarification_agent.py for examples
- Examine the API responses for debugging

---

**Implementation Date:** December 1, 2025  
**Status:** ✅ Production Ready  
**Version:** 1.0.0
