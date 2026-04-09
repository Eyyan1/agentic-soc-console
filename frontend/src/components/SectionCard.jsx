export function SectionCard({ title, subtitle, actions, children, className = "", contentClassName = "" }) {
  return (
    <section className={`rounded-3xl border border-white/10 bg-white/[0.04] shadow-panel ${className}`.trim()}>
      <div className="flex flex-col gap-4 border-b border-white/10 px-5 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-slate-400">{subtitle}</p> : null}
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
      <div className={`p-5 ${contentClassName}`.trim()}>{children}</div>
    </section>
  );
}
