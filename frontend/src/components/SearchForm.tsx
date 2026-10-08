export default function SearchForm({ 
  arxivUrl, 
  setArxivUrl, 
  githubUrl, 
  setGithubUrl, 
  handleInitialize, 
  loading 
}: {
  arxivUrl: string;
  setArxivUrl: (url: string) => void;
  githubUrl: string;
  setGithubUrl: (url: string) => void;
  handleInitialize: () => void;
  loading: boolean;
}) {
  return (
    <div className="flex flex-col gap-4 max-w-3xl">
      <div className="flex items-center border border-cyan-900 bg-slate-900/50 p-2 rounded">
        <span className="text-cyan-500 mr-2 text-sm">TARGET_INPUT</span>
        <input 
          type="text" 
          value={arxivUrl}
          onChange={(e) => setArxivUrl(e.target.value)}
          placeholder="https://arxiv.org/abs/..."
          className="bg-transparent text-slate-300 outline-none w-full text-sm"
        />
      </div>
      <div className="flex items-center border border-fuchsia-900 bg-slate-900/50 p-2 rounded">
        <span className="text-fuchsia-500 mr-2 text-sm">REPO_INPUT</span>
        <input 
          type="text" 
          value={githubUrl}
          onChange={(e) => setGithubUrl(e.target.value)}
          placeholder="https://github.com/... (Optional)"
          className="bg-transparent text-slate-300 outline-none w-full text-sm"
        />
        <button 
          onClick={handleInitialize}
          disabled={loading}
          className="ml-auto px-4 py-1 border border-cyan-700 text-cyan-400 hover:bg-cyan-900/30 text-sm disabled:opacity-50 transition-colors"
        >
          {loading ? "PROCESSING..." : "INITIALIZE"}
        </button>
      </div>
    </div>
  );
}