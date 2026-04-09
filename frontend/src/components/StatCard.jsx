const toneClasses = {
  neutral: "border-white/10 bg-white/[0.04]",
  danger: "border-red-400/20 bg-red-500/[0.07]",
  warning: "border-amber-300/20 bg-amber-400/[0.07]",
  info: "border-cyan-400/20 bg-cyan-400/[0.07]",
  success: "border-emerald-400/20 bg-emerald-400/[0.07]"
};

export function StatCard({ label, value, hint, icon: Icon, tone = "neutral" }) {
  return (
    <div className={`rounded-3xl border p-5 shadow-panel ${toneClasses[tone] || toneClasses.neutral}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
          <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
          <p className="mt-2 text-sm text-slate-400">{hint}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/[0.05] p-3">
          <Icon className="h-5 w-5 text-slate-200" />
        </div>
      </div>
    </div>
  );
}
