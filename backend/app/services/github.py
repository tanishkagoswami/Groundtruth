import os
import httpx
from app.models.schemas import GitHubMetrics # Import the schema

async def fetch_github_metrics(repo_url: str) -> GitHubMetrics | dict:
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return {"error": "Invalid GitHub URL"}
    
    owner, name = parts[-2], parts[-1]
    
    # ADDED: The requirements.txt check block in the query
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        openIssues: issues(states: OPEN) { totalCount }
        closedIssues: issues(states: CLOSED) { totalCount }
        requirements: object(expression: "HEAD:requirements.txt") {
          ... on Blob { text }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 1) {
                edges { node { committedDate } }
              }
            }
          }
        }
      }
    }
    """
    
    variables = {"owner": owner, "name": name}
    headers = {
        "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.github.com/graphql",
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=10.0
            )
            data = response.json()
            
            repo_data = data.get("data", {}).get("repository")
            if not repo_data:
                return {"error": "Repository not found or access denied"}

            open_issues = repo_data["openIssues"]["totalCount"]
            closed_issues = repo_data["closedIssues"]["totalCount"]
            
            try:
                last_commit = repo_data["defaultBranchRef"]["target"]["history"]["edges"][0]["node"]["committedDate"].split("T")[0]
            except (KeyError, TypeError, IndexError):
                last_commit = "Unknown"

            total_issues = open_issues + closed_issues
            friction = (open_issues / total_issues * 100) if total_issues > 0 else 0

            # ADDED: Logic to populate dependency_flags
            flags = []
            req_text = repo_data.get("requirements", {}).get("text", "") if repo_data.get("requirements") else ""
            if not req_text:
                flags.append("Missing requirements.txt")
            elif "torch==1." in req_text:
                flags.append("Legacy PyTorch version detected")

            # ADDED: Returning the Pydantic model instead of a raw dict
            return GitHubMetrics(
                repo_url=repo_url,
                friction_score=int(friction),
                open_issues=open_issues,
                closed_issues=closed_issues,
                last_commit_date=last_commit,
                dependency_flags=flags 
            )
            
        except Exception as e:
            return {"error": str(e)}