import { GitFork, AlertCircle, CheckCircle2 } from "lucide-react";

interface RepositoryHealthProps {
  metrics: {
    friction_score: number;
    dependency_flags: string[];
  } | null;
}

export default function RepositoryHealth({ metrics }: RepositoryHealthProps) {
  return (
    <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-sm shadow-lg relative">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500"></div>
      <h3 className="text-slate-400 text-xs tracking-widest font-bold mb-6 flex items-center gap-2">
        <GitFork className="w-4 h-4 text-purple-400" /> REPOSITORY HEALTH
      </h3>
      
      {metrics ? (
        <div className="space-y-6">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-slate-300">Setup Friction</span>
              <span className="text-purple-400 font-mono">{metrics.friction_score}/100</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
              <div 
                className="bg-purple-500 h-full" 
                style={{ width: `${metrics.friction_score}%` }}
              ></div>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs text-slate-400 uppercase">Dependency Warnings:</p>
            {metrics.dependency_flags.map((flag: string, i: number) => (
              <div key={i} className="flex items-center gap-2 text-sm text-red-300 bg-red-950/30 p-2 rounded border border-red-900/50">
                <AlertCircle className="w-4 h-4" />
                {flag}
              </div>
            ))}
            {metrics.dependency_flags.length === 0 && (
              <div className="flex items-center gap-2 text-sm text-green-400">
                <CheckCircle2 className="w-4 h-4" /> Standard dependencies found.
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex h-full items-center justify-center text-slate-500 text-sm italic">
          No repository linked to this target.
        </div>
      )}
    </div>
  );
}