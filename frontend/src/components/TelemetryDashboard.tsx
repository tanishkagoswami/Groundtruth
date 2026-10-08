export default function TelemetryDashboard({ data, githubUrl }: { data: any, githubUrl: string }) {
  if (!data) return null;

  return (
    <div className="space-y-4 mt-8">
      {/* ROW 1: Compute & Repository Health */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 border border-blue-900 bg-slate-900/50 p-4 rounded">
          <div className="text-blue-500 mb-4 text-sm font-bold tracking-widest">COMPUTE FEASIBILITY</div>
          <div className="text-4xl font-bold text-rose-400 mb-4">
            {data.hardware_flags?.length > 0 ? "20" : "0"} <span className="text-sm text-slate-500">/ 100</span>
          </div>
          <div className="text-xs text-slate-400 mb-2">HARDWARE FLAGS DETECTED:</div>
          <div className="flex flex-wrap gap-2">
            {data.hardware_flags?.length > 0 ? (
              data.hardware_flags.map((flag: string, i: number) => (
                <span key={i} className="bg-blue-950 border border-blue-800 text-blue-300 px-2 py-1 rounded text-xs">{flag}</span>
              ))
            ) : (
              <span className="text-slate-500 text-sm">No specific hardware constraints detected.</span>
            )}
          </div>
        </div>

        <div className="flex-1 border border-fuchsia-900 bg-slate-900/50 p-4 rounded">
          <div className="text-fuchsia-500 mb-4 text-sm font-bold tracking-widest">REPOSITORY HEALTH</div>
          {githubUrl ? (
            <>
              <div className="flex justify-between items-center mb-2">
                <span className="text-slate-300 text-sm">Setup Friction</span>
                <span className="text-fuchsia-300 text-sm">{data.github_metrics?.friction_score || 0}/100</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 mb-6">
                <div className="bg-fuchsia-500 h-2 rounded-full" style={{ width: `${data.github_metrics?.friction_score || 0}%` }}></div>
              </div>
              <div className="text-xs text-slate-400 mb-2">DEPENDENCY WARNINGS:</div>
              {data.github_metrics?.dependency_flags?.length > 0 ? (
                <div className="space-y-2">
                  {data.github_metrics.dependency_flags.map((flag: string, i: number) => (
                    <div key={i} className="text-rose-400 border border-rose-950 bg-rose-950/20 p-2 rounded text-sm flex items-center">
                      <span className="mr-2">!</span> {flag}
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-slate-500 text-sm">No dependency warnings found.</span>
              )}
            </>
          ) : (
            <div className="h-full flex items-center justify-center text-slate-600 text-sm italic mt-8">No repository linked to this target.</div>
          )}
        </div>
      </div>

      {/* ROW 2: Researcher & Beginner Features */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 border border-emerald-900 bg-slate-900/50 p-4 rounded">
          <div className="text-emerald-500 mb-4 text-sm font-bold tracking-widest">LITERATURE CONTEXT</div>
          {data.citations?.length > 0 ? (
            <div className="space-y-3 h-48 overflow-y-auto pr-2 custom-scrollbar">
              {data.citations.map((cite: any, index: number) => (
                <div key={index} className="border-l-2 border-emerald-800 pl-3">
                  <h4 className="text-emerald-300 text-xs font-semibold mb-1">{cite.title}</h4>
                  <p className="text-slate-400 text-xs italic line-clamp-2">{cite.context}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-32 flex items-center justify-center text-slate-600 text-sm italic">No contextual literature found.</div>
          )}
        </div>

        <div className="flex-1 border border-amber-900 bg-slate-900/50 p-4 rounded">
          <div className="text-amber-500 mb-4 text-sm font-bold tracking-widest">BEGINNER ASSESSMENT</div>
          <div className="flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <span className="text-slate-400 text-sm">Dataset Availability</span>
              <span className={data.dataset_validity ? "text-emerald-400 text-sm font-bold" : "text-rose-400 text-sm font-bold"}>
                {data.dataset_validity ? "VERIFIED" : "MISSING"}
              </span>
            </div>
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <span className="text-slate-400 text-sm">Student Feasibility</span>
              <span className="text-amber-400 text-sm font-mono font-bold">
                {data.student_feasibility_score || 0} / 100
              </span>
            </div>
            <div className="text-xs text-slate-500 mt-2">
              {data.student_feasibility_score > 60 
                ? "Verdict: Highly recommended for undergraduate engineering projects. Good documentation and reasonable compute." 
                : "Verdict: High friction. Requires advanced architectural knowledge or significant hardware allocation."}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}