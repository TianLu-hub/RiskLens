import type { LucideIcon } from 'lucide-react';

type Props = {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: 'default' | 'negative';
};

export function RiskMetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = 'default',
}: Props) {
  return (
    <div className="min-w-0 bg-card px-3 py-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <Icon
          className="size-3.5 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
      </div>
      <p
        className={`mt-2 font-mono text-2xl font-semibold tracking-tight tabular-nums ${tone === 'negative' ? 'text-rose-300' : ''}`}
      >
        {value}
      </p>
      <p className="mt-1 text-[12px] text-muted-foreground">{detail}</p>
    </div>
  );
}
