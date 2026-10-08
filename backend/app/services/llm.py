import os
import json
from groq import AsyncGroq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the async client using the key from your .env file
client = AsyncGroq(
    api_key=os.environ.get("GROQ_API_KEY")
)

async def extract_engineering_constraints(paper_text: str) -> dict:
    """
    Feeds the paper's text to Groq and extracts hardware requirements and feasibility.
    """
    
    system_prompt = """
    You are an expert AI engineering assistant analyzing research papers for undergraduate students.
    Read the provided paper abstract/methodology and extract the hardware constraints.
    You MUST respond with ONLY valid JSON. No markdown formatting, no backticks, no explanations.
    
    Format:
    {
        "hardware_flags": ["list of strings..."],
        "dataset_mentioned": "Name of the primary dataset used, or 'None'",
        "student_feasibility_score": integer between 0 and 100
    }
    """

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract constraints from this text:\n\n{paper_text}"}
            ],
            model="openai/gpt-oss-20b", 
            temperature=0.0, 
            max_tokens=1500,  # Increased to match the scaffold function
            # CRITICAL FIX: Removed response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Safe fallback: Strip markdown backticks if the model wraps the JSON
        if raw_content.startswith("```"):
            lines = raw_content.split("\n")
            if lines[0].startswith("```"): lines = lines[1:]
            if lines[-1].startswith("```"): lines = lines[:-1]
            raw_content = "\n".join(lines).strip()
            
        extracted_data = json.loads(raw_content)
        
        return {
            "hardware_flags": extracted_data.get("hardware_flags", []),
            "dataset_mentioned": extracted_data.get("dataset_mentioned", "None"),
            "student_feasibility_score": extracted_data.get("student_feasibility_score", 50)
        }
        
    except Exception as e:
        print(f"DEBUG: Groq API Error: {e}")
        return {
            "hardware_flags": ["Error analyzing hardware constraints"],
            "dataset_mentioned": "None",
            "student_feasibility_score": 50
        }
async def generate_environment_scaffold(github_url: str, hardware_flags: list, missing_files: list) -> dict:
    """Generates the missing setup files by asking for plain text and wrapping it in Python."""
    
    hw_context = ", ".join(hardware_flags) if hardware_flags else "Standard CPU/GPU compute"
    files_context = ", ".join(missing_files) if missing_files else "requirements.txt and Dockerfile"

    # HARDENED PROMPT: We ask for PURE text, no JSON.
    system_prompt = """You are an AI DevOps Engineer. Write the required setup script (Dockerfile or bash).
CRITICAL: Output ONLY the raw code. Do NOT use markdown code blocks (like ```bash). Do NOT add conversational text or explanations. Just the code."""
    
    user_prompt = f"""Repository: {github_url}
Constraints: {hw_context}
Missing: {files_context}"""

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="openai/gpt-oss-20b", 
            temperature=0.0, 
            max_tokens=1500
            # CRITICAL FIX: We removed response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Bulletproof markdown stripper
        if raw_content.startswith("```"):
            lines = raw_content.split("\n")
            if len(lines) > 2:
                # Standard multi-line markdown block
                raw_content = "\n".join(lines[1:-1]).strip()
            else:
                # Single-line markdown block edge case
                raw_content = raw_content.replace("```", "").replace("bash", "").replace("dockerfile", "").strip()

        # We safely build the dictionary in Python, guaranteeing 100% valid JSON for the frontend
        return {
            "setup_script": raw_content,
            "explanation": "Auto-generated environment configuration based on extracted hardware constraints."
        }
        
    except Exception as e:
        print(f"DEBUG: Scaffold Generation Error: {e}")
        return {
            "setup_script": "# Error generating scaffold. Please create environments manually.",
            "explanation": "Failed to connect to the LLM engine."
        }