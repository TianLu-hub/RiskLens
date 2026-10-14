import { CheckCircle2, ShieldAlert } from 'lucide-react';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import type { PortfolioAnalysis } from '@/lib/types';

export function RiskFlags({ analysis }: { analysis: PortfolioAnalysis }) {
  return (
    <Card className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-center justify-between border-b border-border py-3">
        <div><p className="section-label">Rule-based flags</p><p className="mt-1 text-[10px] text-muted-foreground">Deterministic thresholds · no LLM judgment</p></div>
        <ShieldAlert className="size-4 text-amber-300" />
      </CardHeader>
      <CardContent className="p-0">
        {analysis.risk_flags.length === 0 ? (
          <div className="flex items-center gap-2 p-4 text-xs text-muted-foreground"><CheckCircle2 className="size-4 text-emerald-300" />No Phase 1 thresholds triggered.</div>
        ) : analysis.risk_flags.map((flag) => (
          <div key={flag.code} className="grid grid-cols-[8px_1fr_auto] gap-3 border-b border-border p-3 last:border-b-0">
            <span className={`mt-1 size-1.5 ${flag.severity === 'high' ? 'bg-rose-400' : 'bg-amber-300'}`} />
            <div><p className="text-xs font-medium">{flag.title}</p><p className="mt-1 text-[10px] leading-4 text-muted-foreground">{flag.detail}</p></div>
            <span className="font-mono text-[9px] uppercase text-muted-foreground">{flag.severity}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
