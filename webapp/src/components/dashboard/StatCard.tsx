import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string;
  delta?: string;
  icon?: ReactNode;
}

export function StatCard({ label, value, delta, icon }: StatCardProps) {
  return (
    <div className="card relative overflow-hidden group hover:border-base-600 transition-colors">
      <div className="absolute -top-6 -right-6 w-20 h-20 rounded-full bg-accent-dim/10 group-hover:bg-accent-dim/20 transition-colors" />
      <div className="relative flex items-start justify-between">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="stat-value">{value}</span>
            {delta && <span className="badge-up">{delta}</span>}
          </div>
          <p className="stat-label">{label}</p>
        </div>
        {icon && (
          <span className="text-accent-bright bg-accent-dim/15 rounded-lg p-2 shrink-0">
            {icon}
          </span>
        )}
      </div>
    </div>
  );
}
