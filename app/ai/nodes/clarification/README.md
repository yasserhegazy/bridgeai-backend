# Clarification Agent

## Overview

The Clarification Agent is a sophisticated component of the BridgeAI system that automatically detects missing, incomplete, or ambiguous information in client requirements. It generates targeted clarification questions to improve requirement quality and completeness.

## Features

### Ambiguity Detection

The agent detects the following types of issues:

1. **Missing Critical Fields**
   - Project name
   - Project description
   - Target users
   - Main functionality
   - Business goals

2. **Vague Language**
   - Detects non-specific terms like "fast", "user-friendly", "easy to use"
   - Prompts for measurable, specific descriptions

3. **Ambiguous Quantifiers**
   - Identifies unclear quantities: "many", "few", "several", "some"
   - Requests exact numbers or ranges

4. **Incomplete Functional Requirements**
   - Checks for user roles and outcomes
   - Ensures requirements follow best practices

5. **Missing Non-Functional Requirements**
   - Detects absence of performance, security, scalability considerations
   - Prompts for NFR specifications

6. **Undefined Technical Terms**
   - Identifies acronyms and technical jargon
   - Requests definitions or clarifications

## Architecture

### Components

```
app/ai/nodes/clarification/
├── __init__.py                 # Package initialization
├── ambiguity_detector.py       # Core detection logic
└── clarification_node.py       # LangGraph node implementation
```

### Key Classes

#### `AmbiguityDetector`

Core class responsible for analyzing requirements and detecting ambiguities.

**Methods:**
- `detect_ambiguities(user_input, context)` - Analyzes input for issues
- `generate_clarification_questions(ambiguities)` - Creates targeted questions
- `_check_missing_fields()` - Validates critical fields
- `_check_vague_language()` - Detects vague terminology
- `_check_ambiguous_quantifiers()` - Identifies unclear quantities
- `_check_incomplete_functional_requirements()` - Validates functional requirements
- `_check_missing_nonfunctional_requirements()` - Checks for NFRs
- `_check_undefined_terms()` - Identifies technical terms needing definition

#### `Ambiguity`

Data class representing a detected ambiguity:
- `type` - Category: 'missing', 'incomplete', 'ambiguous', 'vague'
- `field` - The aspect needing clarification
- `reason` - Explanation of the issue
- `severity` - Priority level: 'high', 'medium', 'low'
- `suggestion` - Optional recommendation

### LangGraph Integration

The clarification agent is integrated into the LangGraph workflow:

```python
graph.set_entry_point("clarification")
graph.add_conditional_edges(
    "clarification",
    route_after_clarification,
    {
        "end": END,           # If clarification needed
        "continue": "echo"    # If requirements are clear
    }
)
```

**Workflow:**
1. User input enters through clarification node
2. Agent analyzes for ambiguities
3. If issues found, generates questions and returns to user
4. If clear, proceeds to next processing stage

## API Endpoints

### POST `/api/ai/analyze-requirements`

Analyzes user requirements and detects ambiguities.

**Request:**
```json
{
  "user_input": "I want a fast system",
  "conversation_history": [],
  "extracted_fields": {}
}
```

**Response:**
```json
{
  "output": "I'd like to clarify a few points...",
  "clarification_questions": [
    "What would you like to name this project?",
    "Could you provide a brief description..."
  ],
  "ambiguities": [
    {
      "type": "missing",
      "field": "project_name",
      "reason": "Critical field 'project_name' is not specified",
      "severity": "high",
      "suggestion": "Please provide information about project name"
    }
  ],
  "needs_clarification": true,
  "last_node": "clarification"
}
```

### POST `/api/ai/process-requirement`

Processes requirements through the complete workflow.

**Request:** Same as `/analyze-requirements`

**Response:** Complete workflow result including all node outputs

## Usage Examples

### Example 1: Detecting Vague Requirements

```python
from app.ai.nodes.clarification import AmbiguityDetector

detector = AmbiguityDetector()
user_input = "I want a fast and user-friendly system"
context = {"conversation_history": [], "extracted_fields": {}}

ambiguities = detector.detect_ambiguities(user_input, context)
questions = detector.generate_clarification_questions(ambiguities)

# Questions generated:
# 1. What would you like to name this project?
# 2. Could you provide a brief description...
# 3. Could you provide more specific details? For example, what specific metrics...
```

### Example 2: Using the API

```bash
curl -X POST http://localhost:8000/api/ai/analyze-requirements \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "We need a web app with login",
    "conversation_history": [],
    "extracted_fields": {}
  }'
```

### Example 3: Integration in Conversation Flow

```python
# In your chat handler
state = {
    "user_input": client_message,
    "conversation_history": previous_messages,
    "extracted_fields": current_extracted_data
}

result = graph.invoke(state)

if result["needs_clarification"]:
    # Send clarification questions to client
    for question in result["clarification_questions"]:
        send_to_client(question)
else:
    # Proceed with CRS generation
    continue_processing(result)
```

## Configuration

### Severity Levels

- **High**: Critical missing information that must be addressed
- **Medium**: Important clarifications that improve quality
- **Low**: Optional improvements or minor issues

### Question Limits

By default, the agent returns up to 5 clarification questions to avoid overwhelming users. This can be adjusted in `ambiguity_detector.py`:

```python
return questions[:5]  # Adjust limit here
```

## Testing

Run the test suite:

```bash
python test_clarification_agent.py
```

The test covers:
- Vague requirements detection
- Missing critical fields
- Ambiguous quantifiers
- Complete requirements (should not trigger clarification)

## Best Practices

1. **Prioritize High-Severity Issues**: Always address high-severity ambiguities first
2. **Context Matters**: Pass conversation history and extracted fields for better detection
3. **Iterative Clarification**: Handle one round of clarification at a time
4. **User-Friendly Questions**: Questions are conversational and specific
5. **Progressive Enhancement**: Start with critical fields, then refine

## Future Enhancements

- [ ] AI-powered semantic analysis for context understanding
- [ ] Domain-specific templates for different project types
- [ ] Learning from BA feedback to improve detection
- [ ] Multi-language support for requirements in different languages
- [ ] Integration with CRS templates for template-specific validation

## Dependencies

- Python 3.10+
- LangGraph (for workflow orchestration)
- FastAPI (for API endpoints)
- Pydantic (for data validation)

## Contributing

When extending the clarification agent:

1. Add new detection methods to `AmbiguityDetector`
2. Update `CRITICAL_FIELDS` or keyword lists as needed
3. Add corresponding question templates
4. Update tests to cover new scenarios
5. Document new detection capabilities

## License

Part of the BridgeAI platform - Islamic University of Gaza, 2025
