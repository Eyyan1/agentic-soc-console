import { severityColors } from "../lib/utils";

function resolveSeverityFill(name) {
  if (name === "Critical") return "#ef4444";
  if (name === "High") return "#f97316";
  if (name === "Medium") return "#eab308";
  if (name === "Low") return "#3b82f6";
  return "#64748b";
}

export function SeverityPieChart({ data }) {
  const total = data.reduce((sum, item) => sum + item.count, 0) || 1;
  let angle = 0;

  return (
    <div className="grid gap-4 md:grid-cols-[11rem_minmax(0,1fr)]">
      <svg viewBox="0 0 120 120" className="mx-auto h-44 w-44">
        {data.map((item) => {
          const portion = item.count / total;
          const nextAngle = angle + portion * Math.PI * 2;
          const largeArc = nextAngle - angle > Math.PI ? 1 : 0;
          const x1 = 60 + 42 * Math.cos(angle - Math.PI / 2);
          const y1 = 60 + 42 * Math.sin(angle - Math.PI / 2);
          const x2 = 60 + 42 * Math.cos(nextAngle - Math.PI / 2);
          const y2 = 60 + 42 * Math.sin(nextAngle - Math.PI / 2);
          const path = `M 60 60 L ${x1} ${y1} A 42 42 0 ${largeArc} 1 ${x2} ${y2} Z`;
          angle = nextAngle;
          return <path key={item.name} d={path} fill={resolveSeverityFill(item.name)} opacity="0.9" />;
        })}
        <circle cx="60" cy="60" r="20" fill="#020617" />
      </svg>
      <div className="space-y-3">
        {data.map((item) => (
          <div key={item.name} className={`flex items-center justify-between rounded-2xl border px-3 py-2 text-sm ${severityColors[item.name] || severityColors.Unknown}`}>
            <span>{item.name}</span>
            <span>{item.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LineChart({ data, titleKey, valueKey }) {
  const values = data.map((item) => item[valueKey]);
  const max = Math.max(...values, 1);
  const points = data.map((item, index) => {
    const x = (index / Math.max(data.length - 1, 1)) * 100;
    const y = 100 - (item[valueKey] / max) * 100;
    return `${x},${y}`;
  }).join(" ");

  return (
    <div className="space-y-4">
      <svg viewBox="0 0 100 100" className="h-44 w-full overflow-visible">
        <polyline fill="none" stroke="#22d3ee" strokeWidth="3" points={points} />
        {data.map((item, index) => {
          const x = (index / Math.max(data.length - 1, 1)) * 100;
          const y = 100 - (item[valueKey] / max) * 100;
          return <circle key={item[titleKey]} cx={x} cy={y} r="3.5" fill="#f8fafc" />;
        })}
      </svg>
      <div className="grid grid-cols-4 gap-2 text-xs text-slate-400">
        {data.map((item) => (
          <div key={item[titleKey]} className="truncate">{item[titleKey]}</div>
        ))}
      </div>
    </div>
  );
}

export function BarChart({ data, labelKey = "name", valueKey = "count" }) {
  const max = Math.max(...data.map((item) => item[valueKey]), 1);
  return (
    <div className="space-y-3">
      {data.map((item) => (
        <div key={item[labelKey]}>
          <div className="mb-2 flex items-center justify-between text-sm text-slate-300">
            <span className="truncate pr-3">{item[labelKey]}</span>
            <span>{item[valueKey]}</span>
          </div>
          <div className="h-2 rounded-full bg-white/10">
            <div className="h-2 rounded-full bg-cyan-400" style={{ width: `${(item[valueKey] / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
