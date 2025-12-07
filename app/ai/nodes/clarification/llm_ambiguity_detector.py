import os
import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


@dataclass
class Ambiguity:
    type: str
    field: str
    reason: str
    severity: str
    suggestion: Optional[str] = None


class LLMAmbiguityDetector:
    """
    Pure LLM-powered ambiguity detector using Groq LLM.
    No rules, no regex — dynamic, semantic analysis only.
    """

    ANALYSIS_PROMPT = """
You are a senior Business Analyst specialized in requirements analysis.

Analyze the client's requirement below and identify any ambiguities or missing information that would prevent a developer from implementing the requirement.

USER INPUT:
{user_input}

CONTEXT:
Conversation History:
{conversation_history}

Extracted Fields:
{extracted_fields}

IMPORTANT: Return ONLY a valid JSON object without any markdown formatting or code blocks. Do not wrap the JSON in ```json or any other markers.

Your response must be a pure JSON object with this exact structure:
{{
  "ambiguities": [
    {{
      "type": "missing",
      "field": "budget",
      "reason": "No budget or cost constraints specified",
      "severity": "high",
      "suggestion": "Specify budget range or cost expectations"
    }}
  ],
  "overall_clarity_score": 45,
  "summary": "Brief summary of the analysis"
}}

Return pure JSON now:
"""

    QUESTION_PROMPT = """
You are a Business Analyst generating follow-up clarification questions.

Given the ambiguities identified:
{ambiguity_json}

Generate 2-4 specific, actionable questions to clarify these ambiguities.

IMPORTANT: Return ONLY a valid JSON object without any markdown formatting or code blocks.

Your response must be a pure JSON object with this exact structure:
{{
  "questions": [
    "What is your target budget for this project?",
    "Who is your target audience?"
  ]
}}

Return pure JSON now:
"""

    def __init__(self, model: str = "llama-3.3-70b-versatile", temperature: float = 0.3):
        """
        Initialize the ambiguity detector with Groq LLM.
        
        Available models (as of Dec 2024):
        - llama-3.3-70b-versatile (recommended for structured output)
        - llama-3.1-8b-instant (faster but less capable)
        - mixtral-8x7b-32768 (good alternative)
        - gemma2-9b-it (smaller, faster)
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY missing in environment.")

        self.llm = ChatGroq(
            model=model,
            groq_api_key=api_key,
            temperature=temperature,
            max_tokens=2048
        )

        self.analysis_prompt = ChatPromptTemplate.from_template(self.ANALYSIS_PROMPT)
        self.question_prompt = ChatPromptTemplate.from_template(self.QUESTION_PROMPT)

    # -----------------------------------
    # Helper: Clean and Parse JSON
    # -----------------------------------
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        try:
            # Try to parse directly first
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\\s*({.*?})\\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to find any JSON object in the text
            json_match = re.search(r'{.*}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")

    # -----------------------------------
    # LLM Wrapper
    # -----------------------------------
    def _call_llm(self, messages):
        """Call Groq LLM and return the response content."""
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise

    # -----------------------------------
    # Analysis
    # -----------------------------------
    def analyze(self, user_input: str, context: Dict[str, Any]):
        """Analyze user input for ambiguities using Groq LLM."""
        try:
            # Format conversation history
            conv_history = context.get("conversation_history", [])
            history_text = "\n".join(conv_history) if conv_history else "No previous conversation"
            
            # Format extracted fields
            fields = context.get("extracted_fields", {})
            fields_text = json.dumps(fields, indent=2) if fields else "No extracted fields yet"
            
            messages = self.analysis_prompt.format_messages(
                user_input=user_input,
                conversation_history=history_text,
                extracted_fields=fields_text,
            )

            raw = self._call_llm(messages)
            logger.info(f"LLM Analysis Response: {raw[:200]}...")
            
            result = self._extract_json(raw)

            ambiguities = [
                Ambiguity(
                    type=a.get("type", "unknown"),
                    field=a.get("field", "general"),
                    reason=a.get("reason", "No reason provided"),
                    severity=a.get("severity", "medium"),
                    suggestion=a.get("suggestion")
                )
                for a in result.get("ambiguities", [])
            ]

            clarity_score = result.get("overall_clarity_score", 50)
            summary = result.get("summary", "Analysis completed")

            return ambiguities, clarity_score, summary
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            # Return safe defaults on error
            return [], 50, f"Analysis error: {str(e)}"

    # -----------------------------------
    # Question Generation
    # -----------------------------------
    def generate_questions(self, ambiguities: List[Ambiguity]):
        """Generate clarification questions based on detected ambiguities."""
        if not ambiguities:
            return []

        try:
            ambiguity_json = json.dumps([a.__dict__ for a in ambiguities], indent=2)

            messages = self.question_prompt.format_messages(
                ambiguity_json=ambiguity_json
            )

            raw = self._call_llm(messages)
            logger.info(f"LLM Questions Response: {raw[:200]}...")
            
            result = self._extract_json(raw)

            questions = result.get("questions", [])
            
            # Fallback: generate basic questions if LLM fails
            if not questions:
                questions = [f"Can you provide more details about: {a.field}?" for a in ambiguities[:3]]
            
            return questions
            
        except Exception as e:
            logger.error(f"Question generation failed: {str(e)}")
            # Return fallback questions
            return [f"Can you clarify: {a.field}?" for a in ambiguities[:3]]

    # -----------------------------------
    # Full Workflow
    # -----------------------------------
    def analyze_and_generate_questions(self, user_input: str, context: Dict[str, Any]):
        """Complete workflow: analyze requirements and generate questions."""
        logger.info(f"Analyzing requirement: {user_input[:100]}...")
        
        ambiguities, score, summary = self.analyze(user_input, context)
        
        # Only generate questions for significant ambiguities or low clarity scores
        needs_clarification = len(ambiguities) > 0 or score < 70
        
        questions = []
        if needs_clarification:
            questions = self.generate_questions(ambiguities)

        logger.info(f"Analysis complete. Score: {score}, Questions: {len(questions)}")
        
        return {
            "ambiguities": ambiguities,
            "clarification_questions": questions,
            "clarity_score": score,
            "summary": summary,
            "needs_clarification": needs_clarification and len(questions) > 0
        }
