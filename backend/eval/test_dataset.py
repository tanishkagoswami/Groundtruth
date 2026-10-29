"""Probes validate_dataset_access. Run from the backend folder (venv active):

    python eval/test_dataset.py

Needs network to huggingface.co. Uses no Groq tokens.
"""
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.services.dataset import validate_dataset_access

GROUPS = [
    ("A. real HF names (expect True)", True, ["squad", "imdb", "glue", "mnist", "cifar10", "wikitext"], True),
    ("B. names as papers write them (informational)", None, ["CIFAR-10", "ImageNet", "MNIST", "SQuAD", "Penn Treebank",
        "WMT 2014 English-German", "COCO", "LibriSpeech", "Common Crawl", "The Pile"], False),
    ("C. should be False", False, ["xq9zv_not_a_dataset_83921", "None", "unknown", "", "private dataset"], True),
    ("D. generic non-names (expect False; True = false positive)", False,
        ["internal dataset", "custom dataset", "web text", "the training data", "our dataset"], False),
]


async def main():
    hard_fail = 0
    for title, expect, names, strict in GROUPS:
        print(f"\n{title}")
        for n in names:
            got = await validate_dataset_access(n)
            mark = "  " if expect is None else ("ok" if got == expect else ("FAIL" if strict else "!!"))
            if mark == "FAIL":
                hard_fail += 1
            print(f"  {mark:4} {n!r:32} -> {got}")
            await asyncio.sleep(0.4)
    print("\nFAIL = hard failure; !! = false positive in the check (fuzzy search returns any hit)")
    sys.exit(1 if hard_fail else 0)


asyncio.run(main())
