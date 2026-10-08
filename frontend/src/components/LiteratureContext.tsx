import { BookOpen } from "lucide-react";

export default function LiteratureContext({ citations }: { citations: any[] }) {
  return (
    <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-sm shadow-lg relative w-full">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-teal-500"></div>
      <h3 className="text-slate-400 text-xs tracking-widest font-bold mb-6 flex items-center gap-2">
        <BookOpen className="w-4 h-4 text-emerald-400" /> LITERATURE CONTEXT
      </h3>
      
      {citations && citations.length > 0 ? (
        <div className="space-y-4 h-64 overflow-y-auto pr-4 custom-scrollbar">
          {citations.map((cite: any, i: number) => (
            <div key={i} className="bg-slate-950/80 border border-slate-800/80 p-4 rounded hover:border-emerald-900/50 transition-colors">
              <h4 className="text-emerald-300/90 font-semibold text-sm mb-2 font-sans leading-tight">
                {cite.title}
              </h4>
              <p className="text-slate-400 text-xs leading-relaxed font-sans">
                {cite.context}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-slate-500 text-sm italic text-center py-8">
          No external citation context available.
        </div>
      )}
    </div>
  );
}