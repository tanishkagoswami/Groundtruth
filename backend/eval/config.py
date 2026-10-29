"""EDIT THIS FILE to match your FastAPI contract. Everything else reads from here."""
import os
from pathlib import Path

# Reuse the backend's .env so the eval gets the same GITHUB_TOKEN as the server
# (the repo oracle in graders.py needs it, or GitHub rate-limits it to 60 requests/hour).
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

API_URL = os.getenv("GT_API_URL", "http://localhost:8000/api/analyze")
TIMEOUT_S = 240          # paper fetch + 2 LLM calls can be slow
MAX_WORKERS = 2          # keep low: Groq rate limits will 429 you otherwise
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # needed for the repo oracle (rate limits)

def build_request(case: dict) -> dict:
    """JSON body sent to your backend. (run_eval.py currently builds its own payload.)"""
    body = {"arxiv_url": case["arxiv_url"]}
    if case.get("github_url"):
        body["github_url"] = case["github_url"]
    return body

# Dotted paths into YOUR response JSON. Change the right-hand sides.
FIELDS = {
    "score": "student_feasibility_score",
    "gpus": "hardware_flags",
    "compute_text": "hardware_flags",
    "scaffold": "scaffold",
    "repo_requirements_txt": "github_metrics.dependency_flags",
    "repo_dockerfile": "github_metrics.dependency_flags",
    "dataset_open": "dataset_validity",
}

REQUIRED_FIELDS = ["score", "gpus"]
