import os
import re

import httpx

from app.services.arxiv import extract_arxiv_id

OPENALEX = "https://api.openalex.org"


def reconstruct_abstract(inverted_index: dict) -> str:
    """Converts OpenAlex's inverted index format back into a readable string."""
    if not inverted_index:
        return ""
    try:
        # The 'if positions' check prevents the ValueError crash
        max_pos = max(max(positions) for positions in inverted_index.values() if positions)
        words = [""] * (max_pos + 1)

        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word

        return " ".join(words).strip()
    except Exception:
        # Fails gracefully without crashing the FastAPI endpoint
        return ""


def _norm_title(title) -> str:
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())


def _params(extra: dict | None = None) -> dict:
    params = dict(extra or {})
    email = os.environ.get("OPENALEX_EMAIL")  # optional: puts you in OpenAlex's "polite pool"
    if email:
        params["mailto"] = email
    return params


def _doi_for(paper_id: str) -> str | None:
    """arXiv ID -> its DataCite DOI (10.48550/arXiv.<id>); a DOI passes through unchanged."""
    pid = (paper_id or "").strip()
    if pid.lower().startswith("10."):
        return pid
    arxiv_id = extract_arxiv_id(pid)
    if arxiv_id:
        bare_id = re.sub(r"v\d+$", "", arxiv_id)
        return "10.48550/arXiv." + bare_id
    return None


async def _resolve_work(client: httpx.AsyncClient, paper_id: str, title_hint: str | None):
    # 1) Exact lookup by DOI. The old code searched the text "2302.13971", which returns unrelated papers.
    doi = _doi_for(paper_id)
    if doi:
        r = await client.get(f"{OPENALEX}/works", params=_params({"filter": f"doi:{doi.lower()}"}), timeout=20.0)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                return results[0]

    # 2) Title search, accepted only when the returned title actually matches.
    #    No match -> no citations (an empty list beats unrelated papers).
    if title_hint:
        r = await client.get(f"{OPENALEX}/works", params=_params({"search": title_hint, "per-page": 5}), timeout=20.0)
        if r.status_code == 200:
            want = _norm_title(title_hint)
            for work in r.json().get("results", []):
                got = _norm_title(work.get("title"))
                if got and want and (got == want or got.startswith(want) or want.startswith(got)):
                    return work
    return None


def _dedupe_citations(items: list[dict], limit: int = 5) -> list[dict]:
    """OpenAlex often lists one paper twice (e.g. the arXiv preprint and the conference version).
    Merge records that share a normalised title and keep the fuller abstract, so the list shows
    each paper once, in the original most-cited-first order."""
    by_title: dict[str, dict] = {}
    order: list[str] = []
    for item in items:
        abstract = reconstruct_abstract(item.get("abstract_inverted_index"))
        if not abstract:
            continue
        title = item.get("title") or "Unknown Title"
        key = _norm_title(title) or title
        if key in by_title:
            if len(abstract) > len(by_title[key]["context"]):
                by_title[key]["context"] = abstract
            continue
        by_title[key] = {"title": title, "context": abstract}
        order.append(key)
    return [by_title[k] for k in order[:limit]]


async def fetch_citation_context(arxiv_id: str, title_hint: str | None = None):
    async with httpx.AsyncClient() as client:
        try:
            work = await _resolve_work(client, arxiv_id, title_hint)
            if not work or not work.get("id"):
                return []

            short_id = work["id"].split("/")[-1]

            # Most-cited papers that cite this one = its downstream influence
            cites_response = await client.get(
                f"{OPENALEX}/works",
                params=_params({"filter": f"cites:{short_id}", "sort": "cited_by_count:desc", "per-page": 10}),
                timeout=20.0,
            )
            if cites_response.status_code != 200:
                return []

            return _dedupe_citations(cites_response.json().get("results", []))

        except Exception as e:
            print(f"OpenAlex Error: {e}")
            return []