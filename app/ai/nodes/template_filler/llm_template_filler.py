"""
LLM-powered Template Filler for CRS (Customer Requirements Specification) generation.
Maps clarified requirements to a structured CRS template.
"""

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from app.ai.llm_factory import get_template_filler_llm

logger = logging.getLogger(__name__)


@dataclass
class CRSTemplate:
    """Structured CRS Template for requirement documentation."""

    # Project Overview
    project_title: str = ""
    project_description: str = ""
    project_objectives: list = field(default_factory=list)

    # Stakeholders
    target_users: list = field(default_factory=list)
    stakeholders: list = field(default_factory=list)

    # Functional Requirements
    functional_requirements: list = field(default_factory=list)

    # Non-Functional Requirements
    performance_requirements: list = field(default_factory=list)
    security_requirements: list = field(default_factory=list)
    scalability_requirements: list = field(default_factory=list)

    # Technical Specifications
    technology_stack: Dict[str, Any] = field(default_factory=dict)
    integrations: list = field(default_factory=list)

    # Constraints
    budget_constraints: str = ""
    timeline_constraints: str = ""
    technical_constraints: list = field(default_factory=list)

    # Success Criteria
    success_metrics: list = field(default_factory=list)
    acceptance_criteria: list = field(default_factory=list)

    # Additional Notes
    assumptions: list = field(default_factory=list)
    risks: list = field(default_factory=list)
    out_of_scope: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def get_summary_points(self) -> list:
        """Generate summary points from the template."""
        points = []

        if self.project_title:
            points.append(f"Project: {self.project_title}")

        if self.project_objectives:
            points.append(f"Objectives: {len(self.project_objectives)} defined")

        if self.functional_requirements:
            points.append(
                f"Functional Requirements: {len(self.functional_requirements)} items"
            )

        if self.target_users:
            points.append(f"Target Users: {', '.join(self.target_users[:3])}")

        if self.timeline_constraints:
            points.append(f"Timeline: {self.timeline_constraints}")

        if self.budget_constraints:
            points.append(f"Budget: {self.budget_constraints}")

        return points


class LLMTemplateFiller:
    """
    LLM-powered CRS template filler using Groq LLM.
    Extracts and maps requirements from conversation to structured CRS format.
    Supports multiple CRS patterns: BABOK, IEEE 830, ISO/IEC/IEEE 29148.
    """

    # Pattern-specific prompts
    BABOK_EXTRACTION_PROMPT = """
You are a Senior Business Analyst following the BABOK (Business Analysis Body of Knowledge) guide.

Your task is to synthesize the conversation into a well-structured Customer Requirements Specification (CRS) document adhering to BABOK standards.

BABOK FOCUS AREAS:
- Business Need: Problem statement, desired outcome, strategic alignment
- Stakeholders: Users, customers, and their roles
- Current State vs. Future State: Gap analysis
- Solution Scope: In-scope and out-of-scope items
- Requirements Classification: Business, Stakeholder, Solution, and Transition requirements

CRITICAL VOCABULARY ENFORCEMENT for BABOK:
You MUST use the following terms precisely as defined:
- **MUST**: Use to describe Constraints (non-negotiable limitations like deadlines, budgets, laws). Example: "The project must be compliant with GDPR laws."
- **NEEDS TO**: Use to describe a Business Gap (currently missing requiring a solution). Example: "The warehouse needs to reduce inventory counting time by 20%."
- **WANT**: Use in User Stories (desire or goal of a specific stakeholder). Example: "As a customer, I want to track my order so I know when it arrives."
- **VERIFY**: Use when checking if the product was built correctly (matches requirements).
- **VALIDATE**: Use when checking if the right product was built (solves the business problem).

CRITICAL INSTRUCTIONS:
1. DO NOT copy raw conversation text into the output
2. DO NOT include chat messages or dialogue in any field
3. SYNTHESIZE information from multiple messages into concise, professional statements
4. Each requirement should be a clear, specific, actionable item
5. Focus on BUSINESS VALUE and STAKEHOLDER NEEDS
6. USE THE DEFINED VOCABULARY TERMS (MUST, NEEDS TO, WANT) CORRECTLY

USER'S LATEST INPUT:
{user_input}

CONVERSATION HISTORY:
{conversation_history}

PREVIOUSLY EXTRACTED FIELDS:
{extracted_fields}

Return ONLY a valid JSON object:
{{
    "project_title": "Short Project Name",
    "project_description": "A concise 2-4 sentence description summarizing business need and desired outcome.",
    "project_objectives": ["Business objective 1", "Business objective 2"],
    "target_users": ["User type 1", "User type 2"],
    "stakeholders": ["Stakeholder 1", "Stakeholder 2"],
    "functional_requirements": [
        {{
            "id": "BR-001",
            "title": "Business Requirement Title",
            "description": "How this requirement delivers business value.",
            "priority": "high"
        }}
    ],
    "performance_requirements": ["Requirement 1"],
    "security_requirements": ["Requirement 1"],
    "scalability_requirements": ["Requirement 1"],
    "technology_stack": {{"frontend": [], "backend": [], "database": [], "other": []}},
    "integrations": ["Integration 1"],
    "budget_constraints": "Budget information or 'Not specified'",
    "timeline_constraints": "Timeline information or 'Not specified'",
    "technical_constraints": ["Constraint 1"],
    "success_metrics": ["Metric 1"],
    "acceptance_criteria": ["Criteria 1"],
    "assumptions": ["Assumption 1"],
    "risks": ["Risk 1"],
    "out_of_scope": ["Out of scope item 1"]
}}

Return pure JSON now:
"""

    IEEE830_EXTRACTION_PROMPT = """
You are a Technical Systems Analyst generating a Software Requirements Specification (SRS) based on IEEE 830-1998 standard.

Your task is to synthesize the conversation into a well-structured CRS document following IEEE 830 standard structure.

IEEE 830 FOCUS AREAS:
- Introduction: Purpose, scope, definitions, references
- Overall Description: Product perspective, functions, user characteristics, constraints, assumptions
- Specific Requirements: Functional, interface, performance, design constraints, software attributes

CRITICAL VOCABULARY ENFORCEMENT for IEEE 830:
You MUST use these words precisely. They carry legal weight:
- **SHALL**: Mandatory. The system has to do this. If it fails, the product is broken. Example: "The system shall encrypt all user passwords." (Do NOT use "Must").
- **SHOULD**: Recommended / "Nice to have". Desirable but not critical. Example: "The system should support dark mode."
- **MAY**: Permitted / Optional. Allowed or offers a choice. Example: "The report may be exported as a PDF."
- **WILL**: Facts / Future Events. Happen outside software control. Example: "The GPS satellite will transmit coordinates."
- **CAN**: Capability / Possibility (physics/hardware). Example: "The camera sensor can capture 4K video."

CRITICAL INSTRUCTIONS:
1. DO NOT copy raw conversation text into the output
2. Focus on TECHNICAL SPECIFICATIONS and DETAILED REQUIREMENTS
3. Each requirement must be verifiable and testable
4. Use clear, unambiguous language
5. Include external interface specifications
6. STRICTLY FOLLOW THE VOCABULARY RULES (SHALL, SHOULD, MAY, WILL, CAN)

USER'S LATEST INPUT:
{user_input}

CONVERSATION HISTORY:
{conversation_history}

PREVIOUSLY EXTRACTED FIELDS:
{extracted_fields}

Return ONLY a valid JSON object:
{{
    "project_title": "Software System Name",
    "project_description": "Detailed technical description of the software system and its purpose.",
    "project_objectives": ["Technical objective 1", "Technical objective 2"],
    "target_users": ["User type 1", "User type 2"],
    "stakeholders": ["Stakeholder 1", "Stakeholder 2"],
    "functional_requirements": [
        {{
            "id": "SRS-001",
            "title": "Verifiable Technical Requirement",
            "description": "Specific, testable requirement using shall/should/may correctly.",
            "priority": "high"
        }}
    ],
    "performance_requirements": ["The system shall respond within 2 seconds", "The system shall handle 100 concurrent users"],
    "security_requirements": ["The system shall encrypt sensitive data"],
    "scalability_requirements": ["The system should scale to 10,000 users"],
    "technology_stack": {{"frontend": [], "backend": [], "database": [], "other": []}},
    "integrations": ["External system 1"],
    "budget_constraints": "Budget information or 'Not specified'",
    "timeline_constraints": "Timeline information or 'Not specified'",
    "technical_constraints": ["The system shall use existing APIs"],
    "success_metrics": ["Test coverage > 80%", "Zero critical bugs"],
    "acceptance_criteria": ["Passes all regression tests", "Performance targets met"],
    "assumptions": ["Assumption 1"],
    "risks": ["Risk 1"],
    "out_of_scope": ["Out of scope item 1"]
}}

Return pure JSON now:
"""

    ISO29148_EXTRACTION_PROMPT = """
You are a Lead Systems Engineer compiling requirements into a Specification document compliant with ISO/IEC/IEEE 29148.

Your task is to synthesize the conversation into a well-structured CRS document following ISO/IEC/IEEE 29148 standard.

ISO/IEC/IEEE 29148 FOCUS AREAS:
- Operational Concepts: User needs and operational environment
- System Requirements: Organized by user goal or business process
- Quality Attributes: Reliability, usability, efficiency, maintainability, portability
- Interface Requirements: APIs, UI, external system connections
- Verification Criteria: Acceptance criteria and validation methods

CRITICAL VOCABULARY ENFORCEMENT for ISO 29148:
You MUST use these words precisely. They carry legal weight:
- **SHALL**: Mandatory. The system has to do this. If it fails, the product is broken. Example: "The system shall encrypt all user passwords." (Do NOT use "Must").
- **SHOULD**: Recommended / "Nice to have". Desirable but not critical. Example: "The system should support dark mode."
- **MAY**: Permitted / Optional. Allowed or offers a choice. Example: "The report may be exported as a PDF."
- **WILL**: Facts / Future Events. Happen outside software control. Example: "The GPS satellite will transmit coordinates."
- **CAN**: Capability / Possibility (physics/hardware). Example: "The camera sensor can capture 4K video."

CRITICAL INSTRUCTIONS:
1. DO NOT copy raw conversation text into the output
2. Focus on OPERATIONAL CONCEPTS and QUALITY ATTRIBUTES
3. Organize requirements by business process or user goal
4. Ensure verifiable and traceable requirements
5. Use clear, unambiguous, concise language
6. STRICTLY FOLLOW THE VOCABULARY RULES (SHALL, SHOULD, MAY, WILL, CAN)

USER'S LATEST INPUT:
{user_input}

CONVERSATION HISTORY:
{conversation_history}

PREVIOUSLY EXTRACTED FIELDS:
{extracted_fields}

Return ONLY a valid JSON object:
{{
    "project_title": "System Name",
    "project_description": "Concise description of system operational concept and purpose.",
    "project_objectives": ["System objective 1", "System objective 2"],
    "target_users": ["User type 1", "User type 2"],
    "stakeholders": ["Stakeholder 1", "Stakeholder 2"],
    "functional_requirements": [
        {{
            "id": "SYS-001",
            "title": "User Goal or Business Process",
            "description": "Verifiable requirement organized by user goal using shall/should/may correctly.",
            "priority": "high"
        }}
    ],
    "performance_requirements": ["Latency requirements", "Throughput requirements"],
    "security_requirements": ["Authentication requirements", "Data protection requirements"],
    "scalability_requirements": ["Capacity requirements", "Growth trajectory"],
    "technology_stack": {{"frontend": [], "backend": [], "database": [], "other": []}},
    "integrations": ["System integration 1"],
    "budget_constraints": "Budget or 'Not specified'",
    "timeline_constraints": "Timeline or 'Not specified'",
    "technical_constraints": ["Interoperability requirements", "Compliance requirements"],
    "success_metrics": ["Quality metrics", "Acceptance metrics"],
    "acceptance_criteria": ["The system shall pass acceptance tests"],
    "assumptions": ["Environmental assumption 1"],
    "risks": ["Operational risk 1"],
    "out_of_scope": ["Out of scope item 1"]
}}

Return pure JSON now:
"""

    AGILE_EXTRACTION_PROMPT = """
You are an Agile Product Owner and Scrum Master creating a set of User Stories for the backlog.

Your task is to synthesize the conversation into a well-structured CRS document following AGILE / SCRUM standards.

AGILE FOCUS AREAS:
- User Value: Focus on the "Who", "What", and "Why"
- Acceptance Criteria: Clear conditions for "Done"
- Independence: Stories should be implementable separately where possible
- Conversation: Capture the intent, not just technical details

CRITICAL VOCABULARY ENFORCEMENT for AGILE:
You MUST use the User Story Template:
- **As a**: The Role (Who is asking?)
- **I want to**: The Action (What are they doing?)
- **So that**: The Value (Why does this matter?)

You MUST use Gherkin Syntax for Acceptance Criteria:
- **Given**: The starting state
- **When**: The user action
- **Then**: The expected result

CRITICAL INSTRUCTIONS:
1. Do NOT use phrases like "The system shall"
2. Focus on USER CAPABILITIES and BUSINESS VALUE
3. Break down large requirements into smaller User Stories
4. Every Functional Requirement MUST be formatted as a User Story
5. Include GHERKIN syntax in acceptance criteria

USER'S LATEST INPUT:
{user_input}

CONVERSATION HISTORY:
{conversation_history}

PREVIOUSLY EXTRACTED FIELDS:
{extracted_fields}

Return ONLY a valid JSON object:
{{
    "project_title": "Project Name",
    "project_description": "Vision statement or Elevator Pitch for the project.",
    "project_objectives": ["Business Goal 1", "Business Goal 2"],
    "target_users": ["User Persona 1", "User Persona 2"],
    "stakeholders": ["Product Owner", "Stakeholder 1"],
    "functional_requirements": [
        {{
            "id": "US-001",
            "title": "Short User Story Title",
            "description": "As a [Role]\\n, I want to [Action]\\nSo that [Value]",
            "priority": "high"
        }}
    ],
    "performance_requirements": ["Performance constraint (non-functional requirement)"],
    "security_requirements": ["Security constraint"],
    "scalability_requirements": ["Scalability constraint"],
    "technology_stack": {{"frontend": [], "backend": [], "database": [], "other": []}},
    "integrations": ["Integration 1"],
    "budget_constraints": "Budget info",
    "timeline_constraints": "Sprints / Milestones",
    "technical_constraints": ["Technical constraints"],
    "success_metrics": ["Key Result 1"],
    "acceptance_criteria": [
        "**Scenario 1:**\\n**Given** [Context]\\n**When** [Action]\\n**Then** [Outcome]"
    ],
    "assumptions": ["Assumption 1"],
    "risks": ["Risk 1"],
    "out_of_scope": ["Out of scope item"]
}}

Return pure JSON now:
"""

    # Original prompt kept as default
    EXTRACTION_PROMPT = """
You are an expert Business Analyst specializing in requirements documentation.

Your task is to EXTRACT information from the conversation and map it to a structured CRS document.

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. ONLY extract information that was EXPLICITLY STATED by the user in the conversation
2. DO NOT infer, assume, or generate any content that wasn't directly mentioned
3. DO NOT copy raw conversation text - synthesize mentioned points into professional statements
4. If a field wasn't discussed, leave it EMPTY (empty string or empty array)
5. Mark fields as "Not specified" ONLY if the user explicitly said they don't know or it's not applicable
6. For functional requirements, ONLY include features the user specifically requested
7. Project description should summarize what the user said, not what you think the project should be

USER'S LATEST INPUT:
{user_input}

CONVERSATION HISTORY:
{conversation_history}

PREVIOUSLY EXTRACTED FIELDS:
{extracted_fields}

EXTRACTION RULES - BE SPECIFIC AND DETAILED:
- project_title: Use ONLY the title the user mentioned (3-10 words). Leave empty if not stated.
- project_description: Summarize ONLY what the user described (minimum 50 words with SPECIFIC details). Avoid vague terms like "fast", "simple", "good". Include concrete information about purpose, scope, and key features.
- project_objectives: ONLY goals the user explicitly mentioned. Minimum 2 detailed items (each 15+ words explaining the goal).
- functional_requirements: ONLY features the user specifically requested. Minimum 5 detailed requirements.
  - id: Format "FR-001", "FR-002", etc.
  - title: Specific feature name from user's words (3-8 words)
  - description: DETAILED explanation (minimum 30 words) including behavior, inputs, outputs, or user interaction
  - priority: Infer from user's language ("must have"=high, "would be nice"=low)
  - Include acceptance criteria when mentioned
- target_users: ONLY user types mentioned. Minimum 2 types with characteristics (e.g., "Students aged 18-25" not just "Students")
- budget_constraints: ONLY if user provided SPECIFIC budget information:
  - Must be 50+ characters
  - Must include BREAKDOWN (e.g., "development: $X, infrastructure: $Y, testing: $Z")
  - Must mention what the budget covers
  - Avoid vague ranges without context
- timeline_constraints: ONLY if user provided SPECIFIC timeline information:
  - Must be 40+ characters  
  - Must include PHASES or MILESTONES (e.g., "Week 1-2: Design, Week 3-10: Development")
  - Must mention specific durations or dates
  - Include dependencies or critical path if mentioned
- All other fields: ONLY if explicitly discussed with sufficient detail

QUALITY STANDARDS - REJECT VAGUE CONTENT:
- Avoid generic adjectives: "fast", "simple", "good", "nice", "modern", "efficient"
- Require SPECIFIC metrics, numbers, dates, or technical details
- Each functional requirement description: Minimum 30 words with clear acceptance criteria
- Budget: Minimum 50 characters with breakdown of allocations
- Timeline: Minimum 40 characters with phases and milestones
- Project objectives: Minimum 15 words per objective
- Target users: Minimum 15 words per user type with characteristics

CRITICAL: If the user's information is vague or lacks detail, leave that field EMPTY or mark it as incomplete.
Do NOT fill fields with generic or assumed content.

Return ONLY a valid JSON object (no markdown, no code blocks):
{{
    "project_title": "Title user mentioned or empty string",
    "project_description": "Summary of what user described or empty string",
    "project_objectives": ["Objective user mentioned", "Another if stated"],
    "target_users": ["User type mentioned"],
    "stakeholders": ["Stakeholder mentioned"],
    "functional_requirements": [
        {{
            "id": "FR-001",
            "title": "Feature user requested",
            "description": "What user said about this feature.",
            "priority": "high"
        }}
    ],
    "performance_requirements": ["Only if user mentioned performance needs"],
    "security_requirements": ["Only if user mentioned security needs"],
    "scalability_requirements": ["Only if user mentioned scalability needs"],
    "technology_stack": {{
        "frontend": ["Only if user specified"],
        "backend": ["Only if user specified"],
        "database": ["Only if user specified"],
        "other": []
    }},
    "integrations": ["Only if user mentioned integrations"],
    "budget_constraints": "Specific budget info user provided with amounts, or empty string",
    "timeline_constraints": "Specific timeline user provided with dates, or empty string",
    "technical_constraints": ["Only constraints user mentioned"],
    "success_metrics": ["Only metrics user mentioned"],
    "acceptance_criteria": ["Only criteria user mentioned"],
    "assumptions": ["Only assumptions user stated"],
    "risks": ["Only risks user identified"],
    "out_of_scope": ["Only exclusions user mentioned"]
}}

REMEMBER: Extract ONLY what was explicitly mentioned. Leave fields empty if not discussed. Quality over quantity.

Return pure JSON now:
"""

    SUMMARY_PROMPT = """
You are a Business Analyst creating a concise summary of a CRS document.

CRS CONTENT:
{crs_content}

Generate a brief, executive-level summary (3-5 bullet points) highlighting:
1. What the project is about
2. Key features/requirements
3. Target audience
4. Any important constraints or timelines

IMPORTANT: Return ONLY a valid JSON object without any markdown formatting.

{{
    "summary_points": ["Point 1", "Point 2", "Point 3"],
    "overall_summary": "One paragraph summary of the entire CRS"
}}

Return pure JSON now:
"""

    def __init__(
        self,
        pattern: str = "babok",
    ):
        """
        Initialize the template filler with Groq LLM.
        
        Model configuration is now centralized in app.core.config.
        To change the model, update the LLM_TEMPLATE_FILLER_MODEL setting in your .env file.
        """
        # Use centralized LLM factory
        self.llm = get_template_filler_llm()

        if pattern:
            self.pattern = str(pattern).lower().replace(" ", "_").replace("-", "_")
        else:
            self.pattern = "babok"
        
        logger.info(f"Initializing LLMTemplateFiller with pattern: {self.pattern} (original: {pattern})")

        # Select prompt based on pattern
        if "ieee_830" in self.pattern or "ieee830" in self.pattern:
            self.pattern = "ieee_830" # Normalize for internal use
            extraction_prompt = self.IEEE830_EXTRACTION_PROMPT
        elif "29148" in self.pattern:  # stronger match for ISO 29148
            self.pattern = "iso_iec_ieee_29148" # Normalize for internal use
            extraction_prompt = self.ISO29148_EXTRACTION_PROMPT
        elif "agile" in self.pattern or "scrum" in self.pattern or "kanban" in self.pattern:
            self.pattern = "agile_user_stories"
            extraction_prompt = self.AGILE_EXTRACTION_PROMPT
        else:  # default to babok
            self.pattern = "babok"
            extraction_prompt = self.BABOK_EXTRACTION_PROMPT

        self.extraction_prompt = ChatPromptTemplate.from_template(extraction_prompt)
        self.summary_prompt = ChatPromptTemplate.from_template(self.SUMMARY_PROMPT)

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find any JSON object in the text
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

            raise ValueError(
                f"Could not extract valid JSON from response: {text[:200]}..."
            )

    def _call_llm(self, messages) -> str:
        """Call Groq LLM and return the response content."""
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise

    def _track_field_sources(
        self, template: CRSTemplate, previous_template: Optional[CRSTemplate] = None
    ) -> Dict[str, str]:
        """
        Track which fields contain user-provided content vs LLM inference.
        Compares current template with previous to identify newly filled fields.

        Args:
            template: Current CRS template
            previous_template: Previously extracted template (if any)

        Returns:
            dict: Mapping of field names to sources ("explicit_user_input" or "llm_inference")
        """
        field_sources = {}

        # List of all trackable fields
        trackable_fields = [
            "project_title",
            "project_description",
            "project_objectives",
            "target_users",
            "stakeholders",
            "functional_requirements",
            "performance_requirements",
            "security_requirements",
            "scalability_requirements",
            "technology_stack",
            "integrations",
            "budget_constraints",
            "timeline_constraints",
            "technical_constraints",
            "success_metrics",
            "acceptance_criteria",
            "assumptions",
            "risks",
            "out_of_scope",
        ]

        for field_name in trackable_fields:
            current_value = getattr(template, field_name)
            previous_value = (
                getattr(previous_template, field_name) if previous_template else None
            )

            # Check if field has content
            has_content = False
            if isinstance(current_value, str):
                has_content = bool(current_value and current_value.strip())
            elif isinstance(current_value, (list, dict)):
                has_content = bool(current_value)

            if not has_content:
                field_sources[field_name] = "empty"
                continue

            # Check if this is a new field (wasn't in previous template)
            is_new_or_updated = True
            if previous_value is not None:
                if isinstance(current_value, str):
                    is_new_or_updated = current_value != previous_value
                elif isinstance(current_value, list):
                    is_new_or_updated = (
                        len(current_value) != len(previous_value)
                        or current_value != previous_value
                    )
                elif isinstance(current_value, dict):
                    is_new_or_updated = current_value != previous_value

            # Determine source based on quality validation and update status
            # High quality = likely explicit user input
            # Low quality = likely LLM inference or weak input
            is_quality = self._validate_field_quality(field_name, current_value)

            # Use both quality and new/updated status to determine source
            if is_new_or_updated and is_quality:
                field_sources[field_name] = "explicit_user_input"
            elif not is_new_or_updated and is_quality:
                # Content unchanged from previous iteration but still high quality
                field_sources[field_name] = "explicit_user_input"
            else:
                field_sources[field_name] = "llm_inference"

        return field_sources

    def extract_requirements(
        self,
        user_input: str,
        conversation_history: list,
        extracted_fields: Dict[str, Any],
    ) -> CRSTemplate:
        """
        Extract requirements from conversation and map to CRS template.

        Args:
            user_input: Latest user message
            conversation_history: List of previous messages
            extracted_fields: Previously extracted requirement fields

        Returns:
            CRSTemplate: Populated CRS template
        """
        try:
            # Format conversation history - handle both dict and string formats
            if conversation_history:
                formatted_history = []
                for msg in conversation_history:
                    if isinstance(msg, dict):
                        # New format: {"role": "user", "content": "..."}
                        formatted_history.append(f"{msg['role']}: {msg['content']}")
                    else:
                        # Old format: already a string
                        formatted_history.append(msg)
                # Limit conversation history to last 10 messages
                MAX_HISTORY = 10
                if len(formatted_history) > MAX_HISTORY:
                    formatted_history = formatted_history[-MAX_HISTORY:]
                    logger.warning(f"Truncated conversation history to last {MAX_HISTORY} messages")

                history_text = "\n".join(formatted_history)
            else:
                history_text = "No previous conversation"

            fields_text = (
                json.dumps(extracted_fields, indent=2)
                if extracted_fields
                else "No previously extracted fields"
            )

            messages = self.extraction_prompt.format_messages(
                user_input=user_input,
                conversation_history=history_text,
                extracted_fields=fields_text,
            )

            raw = self._call_llm(messages)
            logger.info(f"LLM Extraction Response: {raw[:300]}...")

            result = self._extract_json(raw)

            # Map JSON to CRSTemplate
            template = CRSTemplate(
                project_title=result.get("project_title", ""),
                project_description=result.get("project_description", ""),
                project_objectives=result.get("project_objectives", []),
                target_users=result.get("target_users", []),
                stakeholders=result.get("stakeholders", []),
                functional_requirements=result.get("functional_requirements", []),
                performance_requirements=result.get("performance_requirements", []),
                security_requirements=result.get("security_requirements", []),
                scalability_requirements=result.get("scalability_requirements", []),
                technology_stack=result.get("technology_stack", {}),
                integrations=result.get("integrations", []),
                budget_constraints=result.get("budget_constraints", ""),
                timeline_constraints=result.get("timeline_constraints", ""),
                technical_constraints=result.get("technical_constraints", []),
                success_metrics=result.get("success_metrics", []),
                acceptance_criteria=result.get("acceptance_criteria", []),
                assumptions=result.get("assumptions", []),
                risks=result.get("risks", []),
                out_of_scope=result.get("out_of_scope", []),
            )

            return template

        except Exception as e:
            logger.error(f"Requirement extraction failed: {str(e)}")
            # Return empty template on error
            return CRSTemplate()

    def generate_summary(self, crs_template: CRSTemplate) -> Dict[str, Any]:
        """
        Generate a summary of the CRS document.

        Args:
            crs_template: Populated CRS template

        Returns:
            Dictionary with summary_points and overall_summary
        """
        try:
            crs_content = crs_template.to_json()

            messages = self.summary_prompt.format_messages(crs_content=crs_content)

            raw = self._call_llm(messages)
            logger.info(f"LLM Summary Response: {raw[:200]}...")

            result = self._extract_json(raw)

            return {
                "summary_points": result.get(
                    "summary_points", crs_template.get_summary_points()
                ),
                "overall_summary": result.get("overall_summary", ""),
            }

        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return {
                "summary_points": crs_template.get_summary_points(),
                "overall_summary": f"CRS document for: {crs_template.project_title}",
            }

    def fill_template(
        self,
        user_input: str,
        conversation_history: list,
        extracted_fields: Dict[str, Any],
        previous_template: Optional[CRSTemplate] = None,
    ) -> Dict[str, Any]:
        """
        Complete workflow: Extract requirements, fill template, generate summary, track sources.

        Args:
            user_input: Latest user message
            conversation_history: List of previous messages
            extracted_fields: Previously extracted fields
            previous_template: Previous CRS template for tracking changes

        Returns:
            Dictionary containing:
                - crs_template: The populated CRS template as dict
                - crs_content: JSON string of the CRS
                - summary_points: List of key points
                - overall_summary: Executive summary
                - is_complete: Whether the CRS has sufficient information
                - completeness_percentage: Progress percentage (0-100)
                - missing_required_fields: List of missing required fields
                - missing_optional_fields: List of missing optional fields
                - filled_optional_count: Count of filled optional fields
                - weak_fields: Fields with content but low quality
                - field_sources: Mapping of fields to sources (explicit_user_input/llm_inference/empty)
        """
        logger.info(f"Filling CRS template from input: {user_input[:100]}...")

        # Extract requirements and fill template
        template = self.extract_requirements(
            user_input=user_input,
            conversation_history=conversation_history,
            extracted_fields=extracted_fields,
        )

        # Track field sources
        field_sources = self._track_field_sources(template, previous_template)

        # Generate summary
        summary = self.generate_summary(template)

        # Check completeness
        is_complete = self._check_completeness(template)

        # Get completeness metadata (with conversation history for clarification mode detection)
        completeness_info = self._get_completeness_metadata(
            template, conversation_history
        )

        return {
            "crs_template": template.to_dict(),
            "crs_content": template.to_json(),
            "summary_points": summary["summary_points"],
            "overall_summary": summary["overall_summary"],
            "is_complete": is_complete,
            "completeness_percentage": completeness_info["percentage"],
            "missing_required_fields": completeness_info["missing_required"],
            "missing_optional_fields": completeness_info["missing_optional"],
            "filled_optional_count": completeness_info["filled_optional_count"],
            "weak_fields": completeness_info["weak_fields"],
            "field_sources": field_sources,
        }

    def _has_vague_language(self, text: str) -> bool:
        """Check if text contains vague, generic language."""
        vague_terms = [
            "fast",
            "slow",
            "good",
            "bad",
            "nice",
            "simple",
            "easy",
            "hard",
            "modern",
            "advanced",
            "basic",
            "standard",
            "normal",
            "regular",
            "efficient",
            "effective",
            "optimized",
            "best",
            "great",
            "excellent",
        ]
        text_lower = text.lower()
        vague_count = sum(1 for term in vague_terms if term in text_lower)
        # If more than 2 vague terms or vague terms make up significant portion, it's too vague
        return vague_count > 2 or (vague_count > 0 and len(text.split()) < 15)

    def _has_required_keywords(self, text: str, keywords: list) -> bool:
        """Check if text contains at least one of the required keywords."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    def _calculate_specificity_score(self, text: str) -> float:
        """
        Calculate specificity score (0-1) based on content quality.
        Higher score = more specific and detailed.
        """
        if not text or not text.strip():
            return 0.0

        score = 0.0
        words = text.split()

        # Length bonus (up to 0.3)
        if len(text) >= 100:
            score += 0.3
        elif len(text) >= 50:
            score += 0.2
        elif len(text) >= 30:
            score += 0.1

        # Numbers/dates bonus (0.2)
        if any(char.isdigit() for char in text):
            score += 0.2

        # Specific terms bonus (0.2)
        specific_indicators = [
            "$",
            "%",
            "week",
            "month",
            "day",
            "phase",
            "milestone",
            "allocated",
            "breakdown",
            "specific",
            "exactly",
            "precisely",
        ]
        if any(indicator in text.lower() for indicator in specific_indicators):
            score += 0.2

        # Word count bonus (0.15)
        if len(words) >= 20:
            score += 0.15
        elif len(words) >= 10:
            score += 0.1

        # Penalize vague language (-0.3)
        if self._has_vague_language(text):
            score -= 0.3

        # Technical terms bonus (0.15)
        technical_terms = [
            "api",
            "backend",
            "frontend",
            "database",
            "server",
            "cloud",
            "authentication",
            "encryption",
            "scalability",
            "performance",
        ]
        if any(term in text.lower() for term in technical_terms):
            score += 0.15

        return max(0.0, min(1.0, score))  # Clamp between 0 and 1

    def _is_in_clarification_mode(self, conversation_history: list) -> bool:
        """
        Check if AI is still asking clarification questions.
        Returns True if the last AI message contains questions.
        """
        if not conversation_history:
            return False

        # Get the last AI message
        for message in reversed(conversation_history):
            if message.get("role") == "assistant":
                content = message.get("content", "")
                # Count question marks
                question_count = content.count("?")
                # Check for clarification keywords
                clarification_keywords = [
                    "could you clarify",
                    "can you provide more detail",
                    "what about",
                    "how do you want",
                    "could you tell me",
                    "what would you like",
                    "can you specify",
                    "do you have",
                    "would you prefer",
                    "what is your",
                    "any specific",
                ]
                has_clarification = any(
                    keyword in content.lower() for keyword in clarification_keywords
                )

                # If AI asked 2+ questions or used clarification language, still in clarification mode
                return question_count >= 2 or has_clarification

        return False

    def _validate_field_quality(self, field_name: str, field_value: Any) -> bool:
        """
        Validate if a field has sufficient quality content, not just existence.
        Weak values are accepted but don't count toward progress.

        Args:
            field_name: Name of the field being validated
            field_value: The field value

        Returns:
            bool: True if field meets quality standards, False for weak values
        """
        # String field validation
        if isinstance(field_value, str):
            if not field_value or not field_value.strip():
                return False

            value_lower = field_value.strip().lower()

            # Reject placeholder values
            weak_values = [
                "not specified",
                "n/a",
                "none",
                "tbd",
                "to be determined",
                "pending",
                "unknown",
                "not applicable",
                "not available",
            ]
            if value_lower in weak_values:
                return False

            # Check specificity score first
            specificity = self._calculate_specificity_score(field_value)

            # Field-specific minimum content requirements
            if field_name in ["project_description"]:
                # Project description must be at least 50 characters with good specificity
                return len(field_value.strip()) >= 50 and specificity >= 0.4

            if field_name == "budget_constraints":
                # Budget must be at least 50 characters and contain breakdown keywords
                if len(field_value.strip()) < 50:
                    return False
                # Must contain numbers
                if not any(char.isdigit() for char in field_value):
                    return False
                # Must mention breakdown or allocation
                breakdown_keywords = [
                    "breakdown",
                    "allocated",
                    "phase",
                    "development",
                    "infrastructure",
                    "testing",
                    "total",
                    "budget",
                ]
                if not self._has_required_keywords(field_value, breakdown_keywords):
                    return False
                return specificity >= 0.5

            if field_name == "timeline_constraints":
                # Timeline must be at least 40 characters with phases/milestones
                if len(field_value.strip()) < 40:
                    return False
                # Must contain specific time indicators
                time_keywords = [
                    "week",
                    "month",
                    "day",
                    "date",
                    "milestone",
                    "phase",
                    "deadline",
                    "start",
                    "end",
                    "january",
                    "february",
                    "march",
                    "april",
                    "may",
                    "june",
                    "july",
                    "august",
                    "september",
                    "october",
                    "november",
                    "december",
                ]
                if not self._has_required_keywords(field_value, time_keywords):
                    return False
                return specificity >= 0.5

            # Default string validation: at least 10 characters
            return len(field_value.strip()) >= 10 and specificity >= 0.3

        # List field validation
        if isinstance(field_value, list):
            if not field_value:
                return False

            # Field-specific minimum count requirements
            if field_name == "functional_requirements":
                # Need at least 5 functional requirements with detailed descriptions
                if len(field_value) < 5:
                    return False

                # Each requirement should have sufficient detail
                for req in field_value:
                    if isinstance(req, dict):
                        description = req.get("description", "")
                        # Description should be at least 30 characters
                        if not description or len(str(description).strip()) < 30:
                            return False
                    elif isinstance(req, str):
                        # String requirement should be at least 30 characters
                        if len(req.strip()) < 30:
                            return False

                return True

            if field_name in ["project_objectives", "target_users"]:
                # Need at least 2 items, each with reasonable detail
                if len(field_value) < 2:
                    return False

                # Each item should be meaningful (at least 15 chars)
                for item in field_value:
                    item_text = str(item).strip()
                    if len(item_text) < 15:
                        return False

                return True

            # Default list validation: at least 1 item
            return len(field_value) >= 1

        # Dict field validation
        if isinstance(field_value, dict):
            # Check if dict has meaningful content
            return bool(field_value and any(v for v in field_value.values() if v))

        return bool(field_value)

    def _get_completeness_metadata(
        self, template: CRSTemplate, conversation_history: list = None
    ) -> dict:
        """
        Calculate detailed completeness metadata for the CRS template.
        Uses quality validation - weak values don't count toward progress.
        Caps at 95% if AI is still in clarification mode.

        Args:
            template: CRS template to evaluate
            conversation_history: List of conversation messages to detect clarification mode

        Returns:
            dict: Contains percentage, missing required fields, missing optional fields,
                  filled optional count, and weak fields.
        """
        # Required fields with quality validation
        required_fields = {
            "project_title": self._validate_field_quality(
                "project_title", template.project_title
            ),
            "project_description": self._validate_field_quality(
                "project_description", template.project_description
            ),
            "functional_requirements": self._validate_field_quality(
                "functional_requirements", template.functional_requirements
            ),
        }

        # Optional fields (at least 2 needed) with quality validation
        optional_fields = {
            "project_objectives": self._validate_field_quality(
                "project_objectives", template.project_objectives
            ),
            "target_users": self._validate_field_quality(
                "target_users", template.target_users
            ),
            "timeline_constraints": self._validate_field_quality(
                "timeline_constraints", template.timeline_constraints
            ),
            "budget_constraints": self._validate_field_quality(
                "budget_constraints", template.budget_constraints
            ),
            "success_metrics": self._validate_field_quality(
                "success_metrics", template.success_metrics
            ),
        }

        # Identify weak fields (have content but don't meet quality standards)
        weak_fields = []

        # Check for weak required fields
        for field_name in [
            "project_title",
            "project_description",
            "functional_requirements",
        ]:
            field_value = getattr(template, field_name)
            has_content = (
                bool(field_value)
                if not isinstance(field_value, str)
                else bool(field_value and field_value.strip())
            )
            is_quality = required_fields.get(field_name, False)
            if has_content and not is_quality:
                weak_fields.append(field_name)

        # Check for weak optional fields
        for field_name in [
            "project_objectives",
            "target_users",
            "timeline_constraints",
            "budget_constraints",
            "success_metrics",
        ]:
            field_value = getattr(template, field_name)
            has_content = (
                bool(field_value)
                if not isinstance(field_value, str)
                else bool(field_value and field_value.strip())
            )
            is_quality = optional_fields.get(field_name, False)
            if has_content and not is_quality:
                weak_fields.append(field_name)

        # Calculate missing fields
        missing_required = [
            field for field, filled in required_fields.items() if not filled
        ]
        missing_optional = [
            field for field, filled in optional_fields.items() if not filled
        ]
        filled_optional_count = sum(optional_fields.values())

        # Calculate percentage (required fields + at least 2 optional)
        required_filled = len(required_fields) - len(missing_required)
        total_required = len(required_fields)
        optional_needed = min(
            filled_optional_count, 2
        )  # Max 2 count towards completion

        # Total completion out of (3 required + 2 optional = 5)
        total_filled = required_filled + optional_needed
        total_needed = total_required + 2
        percentage = int((total_filled / total_needed) * 100)

        # Cap at 95% if AI is still asking clarification questions
        if conversation_history and self._is_in_clarification_mode(
            conversation_history
        ):
            percentage = min(percentage, 95)
            logger.info("Capping completeness at 95% - AI still in clarification mode")

        return {
            "percentage": percentage,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "filled_optional_count": filled_optional_count,
            "weak_fields": weak_fields,  # Fields with content but low quality
        }

    def _check_completeness(
        self, template: CRSTemplate, strict_mode: bool = True
    ) -> bool:
        """
        Check if the CRS template has sufficient information.

        Args:
            template: The CRS template to check
            strict_mode: If True, enforces all completeness criteria.
                        If False, returns True for any partial content (for preview mode).

        Returns True if essential fields are populated (in strict mode) or if any content exists (in preview mode).
        """
        # In non-strict mode (preview), consider it complete if any content exists
        if not strict_mode:

            def has_content(value: str) -> bool:
                if not value:
                    return False
                value_stripped = value.strip()
                return value_stripped and value_stripped.lower() not in [
                    "not specified",
                    "n/a",
                    "none",
                    "",
                ]

            has_any_content = (
                has_content(template.project_title)
                or has_content(template.project_description)
                or len(template.functional_requirements) > 0
                or len(template.project_objectives) > 0
                or len(template.target_users) > 0
            )
            return has_any_content

        # Strict mode: enforce all completeness criteria
        essential_filled = all(
            [
                template.project_title,
                template.project_description,
                len(template.functional_requirements) > 0,
            ]
        )

        # Count how many optional fields are filled
        optional_filled = sum(
            [
                len(template.project_objectives) > 0,
                len(template.target_users) > 0,
                bool(
                    template.timeline_constraints
                    and template.timeline_constraints != "Not specified"
                ),
                bool(
                    template.budget_constraints
                    and template.budget_constraints != "Not specified"
                ),
                len(template.success_metrics) > 0,
            ]
        )

        # Consider complete if essentials are filled and at least 2 optional fields
        return essential_filled and optional_filled >= 2
