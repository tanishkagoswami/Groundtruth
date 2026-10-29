"""Run from the BACKEND folder (the one that contains the `app` package):

    python diagnose_paper.py 2302.13971

Tests each pipeline stage on its own, bypassing FastAPI, so you can see which stage loses the hardware info.
"""
import asyncio
import sys

from app.services.arxiv import fetch_paper_metadata
from app.services.pdf_parser import extract_text_from_pdf_url
from app.services import llm

KEYWORDS = ["A100", "V100", "GPU", "TPU"]


async def main(arxiv_id: str):
    meta = await fetch_paper_metadata(f"https://arxiv.org/abs/{arxiv_id}")
    print("1. arXiv metadata:", meta.get("error") or meta["title"])

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    text = await extract_text_from_pdf_url(pdf_url) or ""
    print(f"2. PDF text: {len(text)} chars")
    print("   keywords in FULL text:    ", {k: (k in text) for k in KEYWORDS})

    selected = llm.select_relevant_text(text)
    print(f"3. Selected for the LLM: {len(selected)} chars")
    print("   keywords in SELECTED text:", {k: (k in selected) for k in KEYWORDS})

    result = await llm.extract_engineering_constraints(text)
    print("4. LLM result:", result)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "2302.13971"))
