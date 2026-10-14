import { CircleGauge } from 'lucide-react';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import type { PortfolioAnalysis } from '@/lib/types';

export function ConcentrationPanel({ analysis }: { analysis: PortfolioAnalysis }) {
  const concentration = analysis.concentration;
  const metrics = [
    ['Effective positions', concentration.effective_positions.toFixed(2), `of ${concentration.position_count} nominal`],
    ['HHI', concentration.hhi.toFixed(3), 'Weight concentration'],
    ['Largest position', `${(concentration.largest_position * 100).toFixed(1)}%`, concentration.largest_position_ticker],
    ['Top 3 weight', `${(concentration.top_3_concentration * 100).toFixed(1)}%`, 'Combined exposure'],
  ];
  return (
    <Card className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-center justify-between border-b border-border py-3">
        <div><p className="section-label">Concentration</p><p className="mt-1 text-[10px] text-muted-foreground">Position-level diversification measures</p></div>
        <CircleGauge className="size-4 text-primary" />
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-px bg-border p-0">
        {metrics.map(([label, value, detail]) => <div key={label} className="bg-card p-4"><p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-2 font-mono text-lg">{value}</p><p className="mt-1 text-[9px] text-muted-foreground">{detail}</p></div>)}
      </CardContent>
    </Card>
  );
}
