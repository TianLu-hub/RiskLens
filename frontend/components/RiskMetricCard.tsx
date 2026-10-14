import type { LucideIcon } from 'lucide-react';

type Props = {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: 'default' | 'negative';
};

export function RiskMetricCard({ label, value, detail, icon: Icon, tone = 'default' }: Props) {
  return (
    <div className="bg-card px-3 py-3.5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">{label}</p>
        <Icon className="size-3 text-muted-foreground" />
      </div>
      <p className={`mt-2 font-mono text-xl font-medium tabular-nums ${tone === 'negative' ? 'text-rose-300' : ''}`}>{value}</p>
      <p className="mt-1 text-[10px] text-muted-foreground">{detail}</p>
    </div>
  );
}
