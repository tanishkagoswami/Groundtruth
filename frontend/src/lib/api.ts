const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function analyzeUrl(inputUrl: string, repoUrl: string) {
  const arxivId = inputUrl.split('/').pop()?.replace('.pdf', '') || "unknown";

  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ 
      arxiv_url: inputUrl,
      arxiv_id: arxivId,
      github_url: repoUrl 
    }), 
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const errorMessage = errorData?.detail ? JSON.stringify(errorData.detail) : response.statusText;
    throw new Error(`API Error: ${errorMessage}`);
  }
  return response.json();
}

// UNTOUCHED: Kept exactly as you wrote it
export async function uploadPdf(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData, 
  });

  if (!response.ok) {
    throw new Error(`Upload Error: ${response.statusText}`);
  }
  return response.json();
}
export async function generateScaffold(githubUrl: string, hardwareFlags: string[], missingFiles: string[]) {
  const response = await fetch(`${API_BASE}/api/scaffold`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      github_url: githubUrl,
      hardware_flags: hardwareFlags,
      missing_files: missingFiles
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to generate workspace scaffold.");
  }

  return response.json();
}