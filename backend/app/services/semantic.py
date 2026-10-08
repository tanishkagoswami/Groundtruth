import httpx

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

async def fetch_citation_context(arxiv_id: str):
    clean_id = arxiv_id.split("/")[-1].replace("arxiv:", "").replace(".pdf", "")
    clean_id = clean_id.split('v')[0] if 'v' in clean_id else clean_id
    
    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Use OpenAlex's global search to find the true ID
            search_url = f"https://api.openalex.org/works?search={clean_id}"
            search_response = await client.get(
                search_url,
                params={"mailto": "your_email@example.com"} # Polite pool authentication
            )
            
            if search_response.status_code != 200:
                return []
                
            search_data = search_response.json()
            results = search_data.get("results", [])
            
            if not results:
                return []
                
            openalex_id = results[0].get("id")
            if not openalex_id:
                return []
                
            short_id = openalex_id.split("/")[-1]
            
            # Step 2: Fetch the actual citations
            cites_url = f"https://api.openalex.org/works?filter=cites:{short_id}"
            cites_response = await client.get(
                cites_url,
                params={"mailto": "your_email@example.com"}
            )
            
            if cites_response.status_code != 200:
                return []
            
            data = cites_response.json()
            
            citations = []
            for work in data.get("results", [])[:5]: 
                raw_index = work.get("abstract_inverted_index")
                readable_abstract = reconstruct_abstract(raw_index)
                
                if readable_abstract:
                    citations.append({
                        "title": work.get("title", "Unknown Title"),
                        "context": readable_abstract
                    })
                
            return citations
            
        except Exception as e:
            print(f"OpenAlex Error: {e}")
            return []