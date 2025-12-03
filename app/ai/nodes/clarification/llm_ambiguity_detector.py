from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


@dataclass
class Ambiguity:
    type: str
    field: str
    reason: str
    severity: str
    suggestion: Optional[str] = None


class LLMAmbiguityDetector:
    """
    Pure LLM-based ambiguity detector.
    No rules, no regex — fully dynamic.
    """

    ANALYSIS_PROMPT = """
You are a senior Business Analyst specialized in requirement clarity and ambiguity detection.

Analyze the client requirement below and identify:
- Missing critical information
- Vague or unclear details
- Inconsistencies
- Missing constraints
- Missing functional or non-functional requirements
- Any ambiguity that could impact development

Consider the conversation context and previously extracted fields.

CONTEXT:
Conversation History:
{conversation_history}

Extracted Fields:
{extracted_fields}

USER REQUIREMENT:
{user_input}

Return ONLY valid JSON in this structure:

{{
  "ambiguities": [
    {{
      "type": "missing|vague|incomplete|ambiguous|inconsistent",
      "field": "the area needing clarification",
      "reason": "why it is ambiguous",
      "severity": "high|medium|low",
      "suggestion": "a good clarification question"
    }}
  ],
  "overall_clarity_score": 0-100,
  "summary": "short summary of requirement quality"
}}
"""

    QUESTION_PROMPT = """
You are a Business Analyst generating follow-up clarification questions.

Given these ambiguities:
{ambiguity_json}

Generate 3–5 conversational questions that:
- Address the highest severity ambiguities first
- Are clear and non-technical
- Help the client provide missing info
- Feel like natural conversation

Return JSON:
{{
  "questions": ["q1", "q2", ...]
}}
"""

    def __init__(self, model_name="gpt-4o-mini", temperature=0.2):
        from app.core.config import settings
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment.")
        
        self.llm = ChatOpenAI(model=model_name, temperature=temperature, api_key=settings.OPENAI_API_KEY)
        self.json_parser = JsonOutputParser()

        self.analysis_chain = (
            ChatPromptTemplate.from_template(self.ANALYSIS_PROMPT)
            | self.llm
            | self.json_parser
        )

        self.question_chain = (
            ChatPromptTemplate.from_template(self.QUESTION_PROMPT)
            | self.llm
            | self.json_parser
        )

    # ----------------------------------------------------
    # Core Analysis
    # ----------------------------------------------------
    def analyze(self, user_input: str, context: Dict[str, Any]):
        history_str = "\n".join(context.get("conversation_history", [])) or "No history"
        extracted_str = json.dumps(context.get("extracted_fields", {}), indent=2)

        result = self.analysis_chain.invoke({
            "user_input": user_input,
            "conversation_history": history_str,
            "extracted_fields": extracted_str
        })

        ambiguities = [
            Ambiguity(
                type=a["type"],
                field=a["field"],
                reason=a["reason"],
                severity=a["severity"],
                suggestion=a.get("suggestion")
            ) for a in result.get("ambiguities", [])
        ]

        return ambiguities, result["overall_clarity_score"], result["summary"]

    # ----------------------------------------------------
    # Generate Clarification Questions
    # ----------------------------------------------------
    def generate_questions(self, ambiguities: List[Ambiguity]):
        if not ambiguities:
            return []

        ambiguity_json = json.dumps([
            {
                "type": a.type,
                "field": a.field,
                "reason": a.reason,
                "severity": a.severity,
                "suggestion": a.suggestion
            } for a in ambiguities
        ], indent=2)

        result = self.question_chain.invoke({
            "ambiguity_json": ambiguity_json
        })

        return result.get("questions", [])

    # ----------------------------------------------------
    # Main Entry (Used by Clarification Node)
    # ----------------------------------------------------
    def analyze_and_generate_questions(self, user_input: str, context: Dict[str, Any]):
        ambiguities, clarity_score, summary = self.analyze(user_input, context)
        questions = self.generate_questions(ambiguities)

        return {
            "ambiguities": ambiguities,
            "clarification_questions": questions,
            "clarity_score": clarity_score,
            "summary": summary,
            "needs_clarification": len(questions) > 0
        }
