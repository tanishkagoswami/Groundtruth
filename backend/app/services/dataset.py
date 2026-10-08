import httpx

async def validate_dataset_access(dataset_name: str) -> bool:
    """
    Pings the Hugging Face Datasets API to verify if a dataset exists 
    and is publicly accessible.
    """
    # Guard clauses for empty or generic LLM extractions
    if not dataset_name or dataset_name.strip().lower() in ["unknown", "none", "not specified", "private dataset"]:
        return False
        
    # We use the search endpoint because the LLM might extract a common name 
    # (e.g., "ImageNet") rather than the exact Hugging Face repo ID.
    api_url = "https://huggingface.co/api/datasets"
    params = {
        "search": dataset_name,
        "limit": 1 # We only need to know if at least one valid match exists
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url, params=params, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                
                # If the search returns at least one result, the dataset is accessible
                if isinstance(data, list) and len(data) > 0:
                    return True
                    
            # If we get a 401, 404, or an empty list, it's locked or doesn't exist
            return False
            
        except Exception as e:
            print(f"DEBUG: Dataset validation failed for '{dataset_name}': {e}")
            return False