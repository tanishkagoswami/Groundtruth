import sys
import os
import asyncio
from dotenv import load_dotenv

# This forces Python to look in the current folder for the 'app' module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

load_dotenv(".env")
# Import your services
from app.services.github import fetch_github_metrics
from app.services.semantic import fetch_citation_context
from app.services.dataset import validate_dataset_access
from app.services.llm import extract_engineering_constraints

async def run_tests():
    print("--- 1. Testing GitHub API ---")
    # Using a known, popular repository
    github_res = await fetch_github_metrics("https://github.com/karpathy/minGPT")
    print(github_res)

    print("\n--- 2. Testing OpenAlex API ---")
    # Using the original Attention Is All You Need arXiv ID (1706.03762)
    # 1. Removed the 's' from the function name
# 2. Removed the limit=3 argument
# 3. Added 'arxiv:' prefix so OpenAlex knows what type of ID it is
    semantic_res = await fetch_citation_context("arxiv:1706.03762")
    print(semantic_res)

    print("\n--- 3. Testing Hugging Face Dataset Validator ---")
    # Testing a valid dataset
    dataset_res = await validate_dataset_access("wikitext")
    print(f"Dataset Accessible: {dataset_res}")

    print("\n--- 4. Testing Groq LLM Extraction ---")
    sample_text = """
    We train our novel architecture using a cluster of 8 A100 GPUs over 72 hours. 
    The model was evaluated on the proprietary Corporate-Net dataset, which is not publicly available.
    """
    groq_res = await extract_engineering_constraints(sample_text)
    print(groq_res)

if __name__ == "__main__":
    asyncio.run(run_tests())