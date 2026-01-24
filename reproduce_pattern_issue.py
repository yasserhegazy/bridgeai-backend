
import logging
from app.ai.nodes.template_filler.llm_template_filler import LLMTemplateFiller

# Mock environment variable
import os
os.environ["GROQ_API_KEY"] = "mock_key"

def test_pattern_selection():
    patterns = [
        "babok", 
        "ieee_830", 
        "iso_iec_ieee_29148", 
        None, 
        "IEEE_830", 
        "ieee830"
    ]
    
    for p in patterns:
        try:
            filler = LLMTemplateFiller(pattern=p)
            print(f"Input: {p}, Selected Prompt: {'BABOK' if filler.extraction_prompt.messages[0].prompt.template.startswith('You are a Senior Business Analyst') else 'OTHER'}")
            # We can inspect the prompt content to be sure
            template = filler.extraction_prompt.messages[0].prompt.template
            if "BABOK" in template:
                print(f"  -> Mapped to BABOK")
            elif "IEEE 830" in template:
                print(f"  -> Mapped to IEEE 830")
            elif "ISO/IEC/IEEE 29148" in template:
                print(f"  -> Mapped to ISO 29148")
            else:
                print(f"  -> Mapped to UNKNOWN")
        except Exception as e:
            print(f"Input: {p}, Error: {e}")

if __name__ == "__main__":
    test_pattern_selection()
