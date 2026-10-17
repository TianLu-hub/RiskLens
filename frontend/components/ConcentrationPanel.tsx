'use client';

import { useLanguage } from '@/components/LanguageProvider';
import { MetricHelp } from '@/components/MetricHelp';
import { CircleGauge } from 'lucide-react';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import type { PortfolioAnalysis } from '@/lib/types';

export function ConcentrationPanel({
  analysis,
}: {
  analysis: PortfolioAnalysis;
}) {
  const { t } = useLanguage();
  const concentration = analysis.concentration;
  const metrics = [
    [
      'Effective positions',
      concentration.effective_positions.toFixed(2),
      t('of {count} nominal', { count: concentration.position_count }),
    ],
    ['HHI', concentration.hhi.toFixed(3), 'Weight concentration'],
    [
      'Largest position',
      `${(concentration.largest_position * 100).toFixed(1)}%`,
      concentration.largest_position_ticker,
    ],
    [
      'Top 3 weight',
      `${(concentration.top_3_concentration * 100).toFixed(1)}%`,
      'Combined exposure',
    ],
  ];
  return (
    <Card className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-center justify-between border-b border-border py-3">
        <div>
          <p className="section-label">{t('Concentration')}</p>
          <p className="mt-1 text-[12px] text-muted-foreground">
            {t('Position-level diversification measures')}
          </p>
        </div>
        <CircleGauge className="size-4 text-primary" />
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-px bg-border p-0">
        {metrics.map(([label, value, detail]) => (
          <div key={label} className="bg-card p-4">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
              {t(label)}
              {label === 'Effective positions' && (
                <MetricHelp metric="effective-positions" />
              )}
            </p>
            <p className="mt-2 font-mono text-lg">{value}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {t(detail)}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
