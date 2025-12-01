# Clarification Agent Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                               │
│                  (Client Requirement Text)                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Endpoint                              │
│          POST /api/ai/analyze-requirements                       │
│                                                                   │
│  Input: {user_input, conversation_history, extracted_fields}    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                            │
│                                                                   │
│    Entry Point ──────────────┐                                  │
│                               │                                   │
│                               ▼                                   │
│                    ┌──────────────────┐                          │
│                    │  Clarification   │                          │
│                    │      Node        │                          │
│                    │                  │                          │
│                    │ - Analyze Input  │                          │
│                    │ - Detect Issues  │                          │
│                    │ - Generate Qs    │                          │
│                    └────────┬─────────┘                          │
│                             │                                     │
│                   ┌─────────┴──────────┐                         │
│                   │                    │                          │
│         needs_clarification?          │                          │
│                   │                    │                          │
│            ┌──────┴────┐        ┌─────┴────┐                    │
│            │   YES     │        │    NO    │                     │
│            │           │        │          │                     │
│            ▼           │        │          ▼                     │
│          ┌───┐         │        │      ┌──────────┐             │
│          │END│         │        │      │Next Node │             │
│          └───┘         │        │      │ (Echo)   │             │
│            │           │        │      └────┬─────┘             │
│            └───────────┘        └───────────┘                   │
│                                                                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Response                                    │
│                                                                   │
│  {                                                               │
│    output: "I'd like to clarify...",                            │
│    clarification_questions: [...],                              │
│    ambiguities: [...],                                          │
│    needs_clarification: true/false                              │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Clarification Agent Internal Architecture

```
┌────────────────────────────────────────────────────────────────┐
│              clarification_node(state)                          │
│                                                                  │
│  1. Extract context from state:                                │
│     - user_input                                               │
│     - conversation_history                                      │
│     - extracted_fields                                          │
│                                                                  │
│  2. Initialize AmbiguityDetector                               │
│                                                                  │
│  3. Call detect_ambiguities()         ┌──────────────────────┐│
│              │                          │ AmbiguityDetector   ││
│              └─────────────────────────▶│                     ││
│                                         │ Detection Methods:  ││
│                                         │ ├─ Missing Fields   ││
│                                         │ ├─ Vague Language   ││
│                                         │ ├─ Quantifiers      ││
│                                         │ ├─ Incomplete FRs   ││
│                                         │ ├─ Missing NFRs     ││
│                                         │ └─ Undefined Terms  ││
│                                         └──────────┬───────────┘│
│                                                    │             │
│  4. Receive ambiguities list ◀────────────────────┘            │
│                                                                  │
│  5. Generate questions                 ┌──────────────────────┐│
│              │                          │ Question Generator   ││
│              └─────────────────────────▶│                     ││
│                                         │ - Prioritize by     ││
│                                         │   severity          ││
│                                         │ - Limit to 5        ││
│                                         │ - Use templates     ││
│                                         └──────────┬───────────┘│
│                                                    │             │
│  6. Build response      ◀──────────────────────────┘            │
│                                                                  │
│  7. Update state and return                                    │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

## Ambiguity Detection Logic Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                  detect_ambiguities(input, context)             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌───────────────┐         ┌──────────────────┐
│ Check Missing │         │  Check Language  │
│ Critical      │         │  Quality         │
│ Fields        │         │                  │
│               │         │ - Vague terms    │
│ - project_    │         │ - Quantifiers    │
│   name        │         │ - Technical      │
│ - description │         │   terms          │
│ - users       │         │                  │
│ - functions   │         └────────┬─────────┘
│ - goals       │                  │
└───────┬───────┘                  │
        │                          │
        └──────────┬───────────────┘
                   │
                   ▼
        ┌──────────────────┐
        │  Check           │
        │  Completeness    │
        │                  │
        │ - Functional     │
        │   Requirements   │
        │ - Non-Functional │
        │   Requirements   │
        └────────┬─────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Compile        │
        │ Ambiguities    │
        │ List           │
        │                │
        │ Sort by        │
        │ Severity:      │
        │ High → Med     │
        │ → Low          │
        └────────┬───────┘
                 │
                 ▼
        ┌────────────────┐
        │ Return         │
        │ Ambiguities    │
        └────────────────┘
```

## Data Flow

```
┌──────────────┐
│ User Input   │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ AgentState                               │
├──────────────────────────────────────────┤
│ user_input: str                          │
│ conversation_history: List[str]          │
│ extracted_fields: Dict[str, Any]         │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Clarification Node Processing            │
├──────────────────────────────────────────┤
│ 1. Extract context                       │
│ 2. Detect ambiguities                    │
│ 3. Generate questions                    │
│ 4. Build response                        │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│ Updated AgentState                       │
├──────────────────────────────────────────┤
│ clarification_questions: List[str]       │
│ ambiguities: List[Dict]                  │
│ needs_clarification: bool                │
│ output: str                              │
│ last_node: "clarification"               │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ API Response │
└──────────────┘
```

## Severity-Based Prioritization

```
┌─────────────────────────────────────────────────────────────┐
│                    Detected Ambiguities                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴──────────┬──────────────┐
                │                      │              │
                ▼                      ▼              ▼
        ┌───────────────┐     ┌──────────────┐  ┌─────────┐
        │ HIGH SEVERITY │     │MED SEVERITY  │  │   LOW   │
        ├───────────────┤     ├──────────────┤  ├─────────┤
        │ - Missing     │     │ - Vague      │  │ - Tech  │
        │   critical    │     │   language   │  │   terms │
        │   fields      │     │ - Ambiguous  │  │         │
        │ - Incomplete  │     │   quantifiers│  │         │
        │   functional  │     │ - Missing    │  │         │
        │   reqs        │     │   NFRs       │  │         │
        └───────┬───────┘     └──────┬───────┘  └────┬────┘
                │                    │               │
                │    Priority: 1     │   Priority: 2 │ Priority: 3
                │                    │               │
                └────────────────────┴───────────────┘
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │ Generate Questions     │
                        │ (Max 5, prioritized)   │
                        └────────────────────────┘
```

## Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                        app/api/ai.py                             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ POST /api/ai/analyze-requirements                       │   │
│  │                                                          │   │
│  │  1. Receive RequirementInput                            │   │
│  │  2. Prepare AgentState                                  │   │
│  │  3. Invoke graph.invoke(state)                          │   │
│  │  4. Return ClarificationResponse                        │   │
│  └───────────────────────┬─────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      app/ai/graph.py                             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ create_graph()                                          │   │
│  │                                                          │   │
│  │  - Add clarification node                              │   │
│  │  - Set entry point                                      │   │
│  │  - Add conditional edges                                │   │
│  │  - Return compiled graph                                │   │
│  └───────────────────────┬─────────────────────────────────┘   │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│            app/ai/nodes/clarification/                           │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ clarification_node.py                                 │     │
│  │                                                        │     │
│  │  clarification_node(state) ───────┐                  │     │
│  │                                    │                   │     │
│  └────────────────────────────────────┼───────────────────┘     │
│                                       │                          │
│  ┌────────────────────────────────────┼───────────────────┐     │
│  │ ambiguity_detector.py             │                   │     │
│  │                                    ▼                   │     │
│  │  AmbiguityDetector                                    │     │
│  │  │                                                     │     │
│  │  ├─ detect_ambiguities() ◀────────┘                  │     │
│  │  ├─ generate_clarification_questions()               │     │
│  │  ├─ _check_missing_fields()                          │     │
│  │  ├─ _check_vague_language()                          │     │
│  │  ├─ _check_ambiguous_quantifiers()                   │     │
│  │  ├─ _check_incomplete_functional_requirements()      │     │
│  │  ├─ _check_missing_nonfunctional_requirements()      │     │
│  │  └─ _check_undefined_terms()                         │     │
│  │                                                        │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Integration with BridgeAI Conversation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client Chat Interface                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │ User sends message
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API Gateway                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│               Clarification Agent (Entry Point)                  │
│                                                                   │
│  Analyzes input → Detects ambiguities → Generates questions     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
         ┌────────────┴──────────────┐
         │                           │
         ▼ needs_clarification       ▼ requirements_clear
┌──────────────────┐         ┌──────────────────────┐
│ Return Questions │         │ Continue to Next     │
│ to Client        │         │ Agent:               │
│                  │         │ - Template Filling   │
│ Wait for         │         │ - Validation         │
│ Response         │         │ - CRS Generation     │
└──────────────────┘         └──────────────────────┘
         │
         │ Client responds
         ▼
┌──────────────────┐
│ Update Context   │
│ - conversation_  │
│   history        │
│ - extracted_     │
│   fields         │
└────────┬─────────┘
         │
         │ Re-analyze
         ▼
┌──────────────────┐
│ Clarification    │
│ Agent            │
│ (Loop until      │
│  clear)          │
└──────────────────┘
```

---

## File Structure Summary

```
app/ai/nodes/clarification/
├── __init__.py                    # Package exports
├── ambiguity_detector.py          # Core detection logic (294 lines)
├── clarification_node.py          # LangGraph node (63 lines)
└── README.md                      # Documentation

Integration Points:
├── app/ai/state.py               # Extended AgentState
├── app/ai/graph.py               # LangGraph workflow
└── app/api/ai.py                 # API endpoints

Testing:
└── test_clarification_agent.py   # Test suite
```

---

**Total Lines of Code:** 401 lines (Python implementation)
**Documentation:** Comprehensive README + inline docstrings
**Test Coverage:** 4 comprehensive test scenarios
**API Endpoints:** 2 new endpoints + 1 legacy endpoint
