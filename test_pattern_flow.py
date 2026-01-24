"""
Test script to verify CRS pattern flow end-to-end.
"""
import json
import os

# Set dummy API key for testing initialization logic
os.environ["GROQ_API_KEY"] = "test_key_for_pattern_flow_validation"

from app.ai.nodes.template_filler.llm_template_filler import LLMTemplateFiller

def test_pattern_initialization():
    """Test that different patterns initialize correctly."""
    print("=" * 80)
    print("Testing Pattern Initialization")
    print("=" * 80)
    
    patterns_to_test = [
        "babok",
        "ieee_830",
        "iso_iec_ieee_29148",
        "agile_user_stories",
        # Test variations
        "ieee-830",
        "IEEE 830",
        "iso-iec-ieee-29148",
        "agile",
    ]
    
    for pattern in patterns_to_test:
        try:
            filler = LLMTemplateFiller(pattern=pattern)
            print(f"✓ Pattern '{pattern}' → Normalized to '{filler.pattern}'")
            
            # Check which prompt is selected
            if "BABOK" in str(filler.extraction_prompt):
                prompt_type = "BABOK"
            elif "IEEE 830" in str(filler.extraction_prompt) or "IEEE830" in str(filler.extraction_prompt):
                prompt_type = "IEEE 830"
            elif "29148" in str(filler.extraction_prompt):
                prompt_type = "ISO/IEC/IEEE 29148"
            elif "AGILE" in str(filler.extraction_prompt) or "User Story" in str(filler.extraction_prompt):
                prompt_type = "AGILE"
            else:
                prompt_type = "UNKNOWN"
            
            print(f"  → Using prompt: {prompt_type}")
            
        except Exception as e:
            print(f"✗ Pattern '{pattern}' failed: {e}")
        print()

def test_pattern_prompts():
    """Test that pattern-specific prompts contain the right vocabulary."""
    print("=" * 80)
    print("Testing Pattern-Specific Prompts")
    print("=" * 80)
    
    # Test BABOK
    filler_babok = LLMTemplateFiller(pattern="babok")
    babok_prompt = str(filler_babok.extraction_prompt)
    print("\n1. BABOK Prompt Vocabulary Check:")
    babok_terms = ["MUST", "NEEDS TO", "WANT", "VERIFY", "VALIDATE"]
    for term in babok_terms:
        if term in babok_prompt:
            print(f"   ✓ Contains '{term}'")
        else:
            print(f"   ✗ Missing '{term}'")
    
    # Test IEEE 830
    filler_ieee = LLMTemplateFiller(pattern="ieee_830")
    ieee_prompt = str(filler_ieee.extraction_prompt)
    print("\n2. IEEE 830 Prompt Vocabulary Check:")
    ieee_terms = ["SHALL", "SHOULD", "MAY", "WILL", "CAN"]
    for term in ieee_terms:
        if term in ieee_prompt:
            print(f"   ✓ Contains '{term}'")
        else:
            print(f"   ✗ Missing '{term}'")
    
    # Test ISO 29148
    filler_iso = LLMTemplateFiller(pattern="iso_iec_ieee_29148")
    iso_prompt = str(filler_iso.extraction_prompt)
    print("\n3. ISO/IEC/IEEE 29148 Prompt Vocabulary Check:")
    iso_terms = ["SHALL", "SHOULD", "MAY", "Quality Attributes", "Operational Concepts"]
    for term in iso_terms:
        if term in iso_prompt:
            print(f"   ✓ Contains '{term}'")
        else:
            print(f"   ✗ Missing '{term}'")
    
    # Test AGILE
    filler_agile = LLMTemplateFiller(pattern="agile_user_stories")
    agile_prompt = str(filler_agile.extraction_prompt)
    print("\n4. AGILE Prompt Vocabulary Check:")
    agile_terms = ["AS A", "I WANT TO", "SO THAT", "GIVEN", "WHEN", "THEN"]
    for term in agile_terms:
        if term in agile_prompt:
            print(f"   ✓ Contains '{term}'")
        else:
            print(f"   ✗ Missing '{term}'")

def test_schema_validation():
    """Test that schemas properly define pattern enum."""
    print("\n" + "=" * 80)
    print("Testing Schema Definitions")
    print("=" * 80)
    
    from app.schemas.chat import CRSPatternEnum
    from app.models.crs import CRSPattern
    
    print("\n1. CRSPatternEnum (API Schema):")
    for pattern in CRSPatternEnum:
        print(f"   • {pattern.name} = {pattern.value}")
    
    print("\n2. CRSPattern (Database Model):")
    for pattern in CRSPattern:
        print(f"   • {pattern.name} = {pattern.value}")
    
    # Check alignment
    print("\n3. Alignment Check:")
    schema_values = {p.value for p in CRSPatternEnum}
    model_values = {p.value for p in CRSPattern}
    
    if schema_values == model_values:
        print("   ✓ Schema and Model patterns are aligned")
    else:
        print("   ✗ Mismatch detected:")
        print(f"     Schema only: {schema_values - model_values}")
        print(f"     Model only: {model_values - schema_values}")

def test_pattern_persistence():
    """Test pattern validation in CRS service."""
    print("\n" + "=" * 80)
    print("Testing Pattern Persistence Logic")
    print("=" * 80)
    
    from app.models.crs import CRSPattern
    
    test_cases = [
        ("babok", CRSPattern.babok),
        ("ieee_830", CRSPattern.ieee_830),
        ("iso_iec_ieee_29148", CRSPattern.iso_iec_ieee_29148),
        (None, CRSPattern.babok),  # Default
        ("invalid_pattern", CRSPattern.babok),  # Should fall back to default
    ]
    
    for input_pattern, expected in test_cases:
        try:
            crs_pattern = CRSPattern(input_pattern or "babok")
        except ValueError:
            crs_pattern = CRSPattern.babok
        
        status = "✓" if crs_pattern == expected else "✗"
        print(f"{status} Input: {input_pattern!r} → {crs_pattern.value} (expected: {expected.value})")

if __name__ == "__main__":
    try:
        test_pattern_initialization()
        test_pattern_prompts()
        test_schema_validation()
        test_pattern_persistence()
        
        print("\n" + "=" * 80)
        print("✓ All pattern flow tests completed")
        print("=" * 80)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
