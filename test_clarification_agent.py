"""
Test script for the Clarification Agent

This script demonstrates the clarification agent's ability to detect
ambiguities and generate targeted clarification questions.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.nodes.clarification.ambiguity_detector import AmbiguityDetector


def test_ambiguity_detection():
    """Test various types of ambiguity detection."""
    
    print("=" * 80)
    print("CLARIFICATION AGENT - TEST SCENARIOS")
    print("=" * 80)
    print()
    
    detector = AmbiguityDetector()
    
    # Test Case 1: Vague requirements
    print("Test Case 1: Vague Requirements")
    print("-" * 80)
    user_input_1 = "I want a fast and user-friendly system that can handle some users."
    context_1 = {"conversation_history": [], "extracted_fields": {}}
    
    print(f"Input: {user_input_1}")
    print()
    
    ambiguities_1 = detector.detect_ambiguities(user_input_1, context_1)
    questions_1 = detector.generate_clarification_questions(ambiguities_1)
    
    print("Detected Ambiguities:")
    for amb in ambiguities_1:
        print(f"  - Type: {amb.type}, Field: {amb.field}")
        print(f"    Reason: {amb.reason}")
        print(f"    Severity: {amb.severity}")
        print()
    
    print("Clarification Questions:")
    for i, q in enumerate(questions_1, 1):
        print(f"  {i}. {q}")
    print()
    print()
    
    # Test Case 2: Missing critical fields
    print("Test Case 2: Missing Critical Information")
    print("-" * 80)
    user_input_2 = "We need a web application with login functionality."
    context_2 = {
        "conversation_history": ["I need a new system"],
        "extracted_fields": {}
    }
    
    print(f"Input: {user_input_2}")
    print()
    
    ambiguities_2 = detector.detect_ambiguities(user_input_2, context_2)
    questions_2 = detector.generate_clarification_questions(ambiguities_2)
    
    print("Detected Ambiguities:")
    for amb in ambiguities_2:
        print(f"  - Type: {amb.type}, Field: {amb.field}")
        print(f"    Reason: {amb.reason}")
        print(f"    Severity: {amb.severity}")
        print()
    
    print("Clarification Questions:")
    for i, q in enumerate(questions_2, 1):
        print(f"  {i}. {q}")
    print()
    print()
    
    # Test Case 3: Ambiguous quantifiers
    print("Test Case 3: Ambiguous Quantifiers")
    print("-" * 80)
    user_input_3 = "The system should support many concurrent users and process requests quickly. Most users will access it often."
    context_3 = {
        "conversation_history": [],
        "extracted_fields": {
            "project_name": "User Management System"
        }
    }
    
    print(f"Input: {user_input_3}")
    print()
    
    ambiguities_3 = detector.detect_ambiguities(user_input_3, context_3)
    questions_3 = detector.generate_clarification_questions(ambiguities_3)
    
    print("Detected Ambiguities:")
    for amb in ambiguities_3:
        print(f"  - Type: {amb.type}, Field: {amb.field}")
        print(f"    Reason: {amb.reason}")
        print(f"    Severity: {amb.severity}")
        print()
    
    print("Clarification Questions:")
    for i, q in enumerate(questions_3, 1):
        print(f"  {i}. {q}")
    print()
    print()
    
    # Test Case 4: Complete and clear requirements
    print("Test Case 4: Complete Requirements (No Clarification Needed)")
    print("-" * 80)
    user_input_4 = """
    Project name: Employee Management System
    Description: A web-based system to manage employee records and attendance
    Target users: HR managers and department heads
    Main functionality: The system shall allow HR managers to create, read, update, 
    and delete employee records. It shall track attendance and generate monthly reports.
    Business goals: Streamline HR processes and reduce manual paperwork by 80%
    """
    context_4 = {
        "conversation_history": ["Let me describe our requirements"],
        "extracted_fields": {
            "project_name": "Employee Management System",
            "project_description": "A web-based system to manage employee records",
            "target_users": "HR managers and department heads",
            "main_functionality": "Employee management and attendance tracking",
            "business_goals": "Streamline HR processes"
        }
    }
    
    print(f"Input: {user_input_4.strip()}")
    print()
    
    ambiguities_4 = detector.detect_ambiguities(user_input_4, context_4)
    questions_4 = detector.generate_clarification_questions(ambiguities_4)
    
    if ambiguities_4:
        print("Detected Ambiguities:")
        for amb in ambiguities_4:
            print(f"  - Type: {amb.type}, Field: {amb.field}")
            print(f"    Severity: {amb.severity}")
            print()
    else:
        print("No significant ambiguities detected!")
        print()
    
    if questions_4:
        print("Clarification Questions:")
        for i, q in enumerate(questions_4, 1):
            print(f"  {i}. {q}")
    else:
        print("No clarification needed - requirements are clear!")
    print()
    print()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_ambiguity_detection()
