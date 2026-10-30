const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// The free host can be slow on the first request, so wait up to 3 minutes before giving up.
const ANALYZE_TIMEOUT_MS = 180_000;

function friendlyMessage(status: number, detail: unknown): string {
  if ([429, 502, 503, 504].includes(status)) {
    return "The analysis service is busy or waking up, or the AI provider's daily usage limit has been reached. Wait a minute and try again. If it keeps failing, try again later today.";
  }
  if ([400, 404, 422].includes(status)) {
    return "That input could not be processed. Check that it is a valid arXiv link, for example https://arxiv.org/abs/1706.03762";
  }
  const text = typeof detail === "string" ? detail : "";
  return text ? `Request failed (${status}): ${text}` : `Request failed (${status}).`;
}

export async function analyzeUrl(inputUrl: string, repoUrl: string) {
  const arxivId = inputUrl.split('/').pop()?.replace('.pdf', '') || "unknown";

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ANALYZE_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        arxiv_url: inputUrl,
        arxiv_id: arxivId,
        github_url: repoUrl,
      }),
      signal: controller.signal,
    });
  } catch (err: any) {
    if (err?.name === "AbortError") {
      throw new Error("The analysis took longer than 3 minutes and was stopped. Please try again, or try a different paper.");
    }
    throw new Error("Could not reach the analysis server. It may be starting up (free hosting sleeps when idle). Wait about a minute and try again.");
  } finally {
    clearTimeout(timer);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(friendlyMessage(response.status, errorData?.detail));
  }

  const data = await response.json();
  const title = String(data?.paper_title ?? "").trim().toLowerCase();
  if (title === "paper not found" || title === "no paper provided") {
    throw new Error("Could not find that paper on arXiv. Check the link and try again.");
  }
  return data;
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