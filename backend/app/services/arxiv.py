import httpx
import xml.etree.ElementTree as ET
import re

async def fetch_paper_metadata(arxiv_url: str):
    # Updated regex to handle versioned URLs (e.g., v1, v2)
    match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", arxiv_url)
    if not match:
        return {"title": "Invalid arXiv URL", "summary": ""}
        
    arxiv_id = match.group(1)
    api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(api_url, timeout=10.0)
            
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            entry = root.find('atom:entry', namespaces=ns)
            
            if entry is not None:
                title_elem = entry.find('atom:title', namespaces=ns)
                title = title_elem.text.replace('\n', ' ').strip() if title_elem is not None else "Title Missing"
                
                # CRITICAL ADDITION: Extracting the summary to feed the LLM
                summary_elem = entry.find('atom:summary', namespaces=ns)
                summary = summary_elem.text.replace('\n', ' ').strip() if summary_elem is not None else ""
                
                return {"title": title, "summary": summary}
            else:
                print("DEBUG: arXiv API returned 200, but no <entry> tag was found.")
        else:
            print(f"DEBUG: arXiv API HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"DEBUG: Code execution failed with error: {e}")
        
    return {"title": "Paper not found", "summary": ""}