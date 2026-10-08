interface HardwareProps {
  flags: string[];
}

export default function HardwareWarning({ flags }: HardwareProps) {
  return (
    <div className="space-y-2 mt-6">
      <p className="text-xs text-slate-400 uppercase">Hardware Flags Detected:</p>
      <div className="flex flex-wrap gap-2">
        {flags && flags.length > 0 ? (
          flags.map((flag, i) => (
            <span key={i} className="bg-slate-800 text-cyan-300 border border-cyan-800/50 text-xs px-3 py-1 rounded-full">
              {flag}
            </span>
          ))
        ) : (
          <span className="text-slate-500 text-sm">No specific hardware constraints detected.</span>
        )}
      </div>
    </div>
  );
}