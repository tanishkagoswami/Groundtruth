import asyncio
import re
import xml.etree.ElementTree as ET

import httpx

# New-style (2302.13971, 2302.13971v2) and old-style (hep-th/9711200) arXiv IDs
NEW_ID = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?!\d)(v\d+)?")
OLD_ID = re.compile(r"([a-z\-]+(?:\.[A-Za-z]{2})?/\d{7})(v\d+)?")
ATOM = {"atom": "http://www.w3.org/2005/Atom"}
HEADERS = {"User-Agent": "Groundtruth/1.0 (research feasibility tool)"}
RETRY_STATUSES = (429, 500, 502, 503, 504)


def extract_arxiv_id(url: str) -> str | None:
    m = NEW_ID.search(url or "") or OLD_ID.search(url or "")
    return m.group(0) if m else None


def _parse_entry(xml_text: str, arxiv_id: str) -> dict:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return {"error": f"arXiv returned unreadable XML ({e})"}

    entry = root.find("atom:entry", namespaces=ATOM)
    if entry is None:
        return {"error": "arXiv returned no entry for this ID"}

    # For an unknown ID, arXiv answers 200 with a fake entry that points at /api/errors
    id_elem = entry.find("atom:id", namespaces=ATOM)
    if id_elem is not None and id_elem.text and "api/errors" in id_elem.text:
        return {"error": f"arXiv has no paper with ID {arxiv_id}"}

    title_elem = entry.find("atom:title", namespaces=ATOM)
    summary_elem = entry.find("atom:summary", namespaces=ATOM)
    title = " ".join((title_elem.text or "").split()) if title_elem is not None else ""
    summary = " ".join((summary_elem.text or "").split()) if summary_elem is not None else ""
    if not title:
        return {"error": "arXiv entry has no title"}
    return {"title": title, "summary": summary, "arxiv_id": arxiv_id}


async def fetch_paper_metadata(arxiv_url: str) -> dict:
    """Returns {"title","summary","arxiv_id"} on success, or {"error": "..."} on any failure."""
    arxiv_id = extract_arxiv_id(arxiv_url)
    if not arxiv_id:
        return {"error": "Invalid arXiv URL"}

    api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    last_error = "unknown error"
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(follow_redirects=True, headers=HEADERS) as client:
                response = await client.get(api_url, timeout=20.0)
            if response.status_code == 200:
                return _parse_entry(response.text, arxiv_id)
            last_error = f"arXiv API HTTP {response.status_code}"
            if response.status_code not in RETRY_STATUSES:
                break
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
        print(f"DEBUG: arXiv fetch attempt {attempt + 1} failed: {last_error}")
        if attempt < 2:
            await asyncio.sleep(3 * (attempt + 1))

    return {"error": f"Could not retrieve arXiv paper ({last_error})"}