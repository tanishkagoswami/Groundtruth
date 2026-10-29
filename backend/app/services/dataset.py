import re
import httpx

_PLACEHOLDERS = {"unknown", "none", "not specified", "private dataset", "n/a", "na", "null"}
# Words that describe "a dataset" without naming one. A query made only of these is not a dataset name.
_GENERIC = {
    "dataset", "datasets", "data", "set", "sets", "corpus", "corpora", "benchmark", "benchmarks",
    "training", "train", "test", "testing", "validation", "eval", "evaluation",
    "the", "a", "an", "of", "our", "their", "own", "this", "that", "and", "for", "in", "on",
    "internal", "custom", "private", "proprietary", "collected", "curated", "new", "synthetic",
    "web", "text", "texts", "large", "scale", "various", "several", "public", "publicly", "available",
}


def _tokens(name: str):
    return [t for t in re.findall(r"[a-z0-9]+", name.lower())]


def _significant(name: str):
    return [t for t in _tokens(name) if t not in _GENERIC]


def _matches(name: str, repo_id: str) -> bool:
    """
    True when a Hugging Face repo id plausibly IS the dataset the paper names.
    The HF search is fuzzy (any hit for 'custom dataset'), so a hit alone proves nothing.
    """
    sig = _significant(name)
    if not sig:
        return False
    segs = [s for s in re.split(r"[/_\-.\s]+", repo_id.lower()) if s]
    joined_id = re.sub(r"[^a-z0-9]", "", repo_id.lower())
    if "".join(sig) in joined_id:  # 'cifar10' in 'uoft-cs/cifar10'
        return True
    if all(t in joined_id for t in sig):
        return True
    lead = sig[0]  # 'wmt' for 'WMT 2014 English-German' -> wmt/wmt14
    return len(lead) >= 3 and any(s == lead or re.fullmatch(re.escape(lead) + r"\d+", s) for s in segs)


async def validate_dataset_access(dataset_name: str) -> bool:
    """
    True when Hugging Face hosts a dataset whose id matches the name the paper uses.
    Fuzzy search alone is not enough, so each returned repo id is checked against the name.
    """
    if not dataset_name or dataset_name.strip().lower() in _PLACEHOLDERS:
        return False
    if not _significant(dataset_name):
        return False

    api_url = "https://huggingface.co/api/datasets"
    sig = _significant(dataset_name)
    # HF search needs every word to hit, so a long phrase like 'WMT 2014 English-German' returns nothing
    # although wmt/wmt14 exists. Try the full name first, then just its leading word.
    queries = [dataset_name] + ([sig[0]] if len(sig) > 1 and len(sig[0]) >= 3 else [])

    async with httpx.AsyncClient() as client:
        for q in queries:
            try:
                response = await client.get(api_url, params={"search": q, "limit": 10}, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and any(_matches(dataset_name, d.get("id", "")) for d in data):
                        return True
            except Exception as e:
                print(f"DEBUG: Dataset validation failed for '{dataset_name}' (query '{q}'): {e}")
    return False
