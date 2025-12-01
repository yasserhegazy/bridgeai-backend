"""
Ambiguity Detector Module

This module implements the core logic for detecting missing, incomplete, 
or ambiguous information in client requirements. It analyzes user input
against a set of quality criteria and generates targeted clarification questions.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class Ambiguity:
    """Represents a detected ambiguity in requirements."""
    type: str  # 'missing', 'incomplete', 'ambiguous', 'vague'
    field: str  # The field or aspect that needs clarification
    reason: str  # Why this is considered ambiguous
    severity: str  # 'high', 'medium', 'low'
    suggestion: Optional[str] = None  # Suggested clarification


class AmbiguityDetector:
    """
    Detects ambiguities and missing information in requirements.
    
    This class analyzes requirement text for:
    - Missing critical information
    - Vague or unclear descriptions
    - Ambiguous terminology
    - Incomplete functional requirements
    - Missing non-functional requirements
    """
    
    # Critical fields that should be present in requirements
    CRITICAL_FIELDS = [
        "project_name",
        "project_description",
        "target_users",
        "main_functionality",
        "business_goals"
    ]
    
    # Keywords that indicate vagueness
    VAGUE_KEYWORDS = [
        "some", "maybe", "possibly", "might", "could",
        "approximately", "around", "about", "roughly",
        "user-friendly", "easy to use", "simple", "fast",
        "good", "better", "best", "nice", "clean"
    ]
    
    # Keywords that indicate ambiguous quantifiers
    AMBIGUOUS_QUANTIFIERS = [
        "many", "few", "several", "some", "most",
        "often", "rarely", "sometimes", "usually"
    ]
    
    def __init__(self):
        """Initialize the ambiguity detector."""
        self.detected_ambiguities: List[Ambiguity] = []
    
    def detect_ambiguities(self, user_input: str, context: Optional[Dict] = None) -> List[Ambiguity]:
        """
        Detect ambiguities in user input.
        
        Args:
            user_input: The user's requirement input text
            context: Optional context including conversation history and extracted fields
            
        Returns:
            List of detected ambiguities
        """
        self.detected_ambiguities = []
        context = context or {}
        
        # Check for missing critical fields
        self._check_missing_fields(user_input, context)
        
        # Check for vague language
        self._check_vague_language(user_input)
        
        # Check for ambiguous quantifiers
        self._check_ambiguous_quantifiers(user_input)
        
        # Check for incomplete functional requirements
        self._check_incomplete_functional_requirements(user_input)
        
        # Check for missing non-functional requirements
        self._check_missing_nonfunctional_requirements(user_input, context)
        
        # Check for undefined technical terms
        self._check_undefined_terms(user_input)
        
        return self.detected_ambiguities
    
    def _check_missing_fields(self, user_input: str, context: Dict):
        """Check for missing critical fields."""
        extracted_fields = context.get("extracted_fields", {})
        
        for field in self.CRITICAL_FIELDS:
            if field not in extracted_fields or not extracted_fields[field]:
                # Check if it's mentioned in current input
                if not self._is_field_mentioned(field, user_input):
                    self.detected_ambiguities.append(Ambiguity(
                        type="missing",
                        field=field,
                        reason=f"Critical field '{field}' is not specified",
                        severity="high",
                        suggestion=f"Please provide information about {field.replace('_', ' ')}"
                    ))
    
    def _check_vague_language(self, user_input: str):
        """Check for vague or unclear language."""
        text_lower = user_input.lower()
        found_vague = []
        
        for vague_word in self.VAGUE_KEYWORDS:
            if re.search(r'\b' + re.escape(vague_word) + r'\b', text_lower):
                found_vague.append(vague_word)
        
        if found_vague:
            self.detected_ambiguities.append(Ambiguity(
                type="vague",
                field="language_clarity",
                reason=f"Vague terms detected: {', '.join(found_vague[:3])}",
                severity="medium",
                suggestion="Please provide specific, measurable descriptions instead of vague terms"
            ))
    
    def _check_ambiguous_quantifiers(self, user_input: str):
        """Check for ambiguous quantifiers that need clarification."""
        text_lower = user_input.lower()
        found_quantifiers = []
        
        for quantifier in self.AMBIGUOUS_QUANTIFIERS:
            if re.search(r'\b' + re.escape(quantifier) + r'\b', text_lower):
                found_quantifiers.append(quantifier)
        
        if found_quantifiers:
            self.detected_ambiguities.append(Ambiguity(
                type="ambiguous",
                field="quantifiers",
                reason=f"Ambiguous quantifiers detected: {', '.join(found_quantifiers[:3])}",
                severity="medium",
                suggestion="Please specify exact numbers or ranges instead of ambiguous quantities"
            ))
    
    def _check_incomplete_functional_requirements(self, user_input: str):
        """Check if functional requirements are complete."""
        text_lower = user_input.lower()
        
        # Check for action verbs that indicate functionality
        has_action = any(word in text_lower for word in [
            "shall", "must", "will", "should", "need to",
            "want to", "allow", "enable", "provide", "support"
        ])
        
        # Check for user roles
        has_user_role = any(word in text_lower for word in [
            "user", "admin", "client", "customer", "ba",
            "business analyst", "stakeholder"
        ])
        
        # Check for outcomes/results
        has_outcome = any(word in text_lower for word in [
            "so that", "in order to", "to enable", "resulting in",
            "leading to", "achieve", "accomplish"
        ])
        
        if has_action and not (has_user_role or has_outcome):
            self.detected_ambiguities.append(Ambiguity(
                type="incomplete",
                field="functional_requirement",
                reason="Functional requirement lacks user role or outcome description",
                severity="high",
                suggestion="Please specify who will use this feature and what outcome it should achieve"
            ))
    
    def _check_missing_nonfunctional_requirements(self, user_input: str, context: Dict):
        """Check for missing non-functional requirements."""
        text_lower = user_input.lower()
        conversation_history = context.get("conversation_history", [])
        
        # Categories of non-functional requirements
        nfr_categories = {
            "performance": ["performance", "speed", "response time", "latency"],
            "security": ["security", "authentication", "authorization", "encryption"],
            "scalability": ["scalability", "concurrent users", "load", "capacity"],
            "usability": ["usability", "user experience", "accessibility"],
            "reliability": ["reliability", "availability", "uptime", "fault tolerance"]
        }
        
        # Check if any NFR has been discussed
        all_text = user_input + " " + " ".join(conversation_history)
        mentioned_categories = []
        
        for category, keywords in nfr_categories.items():
            if any(keyword in all_text.lower() for keyword in keywords):
                mentioned_categories.append(category)
        
        # If less than 2 NFR categories mentioned and conversation has progressed
        if len(mentioned_categories) < 2 and len(conversation_history) > 3:
            missing = [cat for cat in nfr_categories.keys() if cat not in mentioned_categories]
            self.detected_ambiguities.append(Ambiguity(
                type="missing",
                field="non_functional_requirements",
                reason=f"Non-functional requirements not sufficiently addressed",
                severity="medium",
                suggestion=f"Consider specifying requirements for: {', '.join(missing[:3])}"
            ))
    
    def _check_undefined_terms(self, user_input: str):
        """Check for technical terms that might need definition."""
        # Common technical terms that might need clarification
        technical_patterns = [
            r'\b([A-Z]{2,})\b',  # Acronyms
            r'\b(API|SDK|UI|UX|CRS|SRS|BA)\b',  # Common acronyms
        ]
        
        found_terms = set()
        for pattern in technical_patterns:
            matches = re.findall(pattern, user_input)
            found_terms.update(matches)
        
        # Filter out common acronyms that don't need definition
        common_terms = {"API", "UI", "UX", "BA", "CRS", "SRS", "PDF"}
        undefined_terms = found_terms - common_terms
        
        if undefined_terms:
            self.detected_ambiguities.append(Ambiguity(
                type="ambiguous",
                field="technical_terms",
                reason=f"Technical terms or acronyms detected: {', '.join(list(undefined_terms)[:3])}",
                severity="low",
                suggestion="Please define or clarify any technical terms or acronyms"
            ))
    
    def _is_field_mentioned(self, field: str, text: str) -> bool:
        """Check if a field is mentioned in the text."""
        field_keywords = {
            "project_name": ["project name", "called", "named", "title"],
            "project_description": ["description", "about", "overview", "summary"],
            "target_users": ["users", "clients", "customers", "audience", "stakeholders"],
            "main_functionality": ["features", "functionality", "capabilities", "functions"],
            "business_goals": ["goals", "objectives", "purpose", "aim", "benefit"]
        }
        
        keywords = field_keywords.get(field, [field.replace("_", " ")])
        text_lower = text.lower()
        
        return any(keyword in text_lower for keyword in keywords)
    
    def generate_clarification_questions(self, ambiguities: List[Ambiguity]) -> List[str]:
        """
        Generate targeted clarification questions based on detected ambiguities.
        
        Args:
            ambiguities: List of detected ambiguities
            
        Returns:
            List of clarification questions
        """
        questions = []
        
        # Sort by severity
        sorted_ambiguities = sorted(
            ambiguities,
            key=lambda x: {"high": 0, "medium": 1, "low": 2}[x.severity]
        )
        
        # Generate questions for high and medium severity issues
        for amb in sorted_ambiguities:
            if amb.severity in ["high", "medium"]:
                question = self._generate_question_for_ambiguity(amb)
                if question:
                    questions.append(question)
        
        # Limit to top 3-5 questions to avoid overwhelming the user
        return questions[:5]
    
    def _generate_question_for_ambiguity(self, ambiguity: Ambiguity) -> Optional[str]:
        """Generate a specific question for an ambiguity."""
        question_templates = {
            "missing": {
                "project_name": "What would you like to name this project?",
                "project_description": "Could you provide a brief description of what this project aims to achieve?",
                "target_users": "Who are the intended users or target audience for this system?",
                "main_functionality": "What are the main features or functionalities you need in this system?",
                "business_goals": "What are the key business goals or objectives this system should support?",
                "non_functional_requirements": "Have you considered non-functional requirements such as performance, security, or scalability?"
            },
            "incomplete": {
                "functional_requirement": "Could you clarify who will use this feature and what specific outcome they should achieve?",
            },
            "vague": {
                "language_clarity": "Could you provide more specific details? For example, what specific metrics or criteria define success?",
            },
            "ambiguous": {
                "quantifiers": "Could you specify exact numbers or ranges? For example, how many users or what specific timeframe?",
                "technical_terms": "Could you define or provide more context for the technical terms mentioned?",
            }
        }
        
        template = question_templates.get(ambiguity.type, {}).get(ambiguity.field)
        return template or ambiguity.suggestion
