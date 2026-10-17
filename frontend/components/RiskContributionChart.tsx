'use client';

import { useLanguage } from '@/components/LanguageProvider';
import { GitCompareArrows } from 'lucide-react';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import type { PortfolioAnalysis } from '@/lib/types';

export function RiskContributionChart({
  analysis,
}: {
  analysis: PortfolioAnalysis;
}) {
  const { t } = useLanguage();
  const rows = [...analysis.risk_contributions].sort(
    (a, b) => b.risk_contribution - a.risk_contribution,
  );
  return (
    <Card id="contribution" className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-center justify-between border-b border-border py-3">
        <div>
          <p className="section-label">{t('Risk contribution')}</p>
          <p className="mt-1 text-[12px] text-muted-foreground">
            {t('Portfolio weight vs. share of volatility')}
          </p>
        </div>
        <GitCompareArrows className="size-4 text-primary" />
      </CardHeader>
      <CardContent className="p-4">
        <div className="mb-2 grid grid-cols-[44px_1fr_44px_44px] gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          <span>{t('Asset')}</span>
          <span>{t('Relative scale')}</span>
          <span className="text-right">{t('Wgt')}</span>
          <span className="text-right">{t('Risk')}</span>
        </div>
        <div className="space-y-3">
          {rows.map((item) => {
            const risk = item.risk_contribution * 100;
            return (
              <div
                key={item.ticker}
                className="grid grid-cols-[44px_1fr_44px_44px] items-center gap-2 text-[12px]"
              >
                <span className="font-mono font-medium">{item.ticker}</span>
                <div className="relative h-4 bg-muted">
                  <div
                    className="absolute inset-y-0 left-0 bg-primary/65"
                    style={{ width: `${Math.max(item.weight * 100, 1)}%` }}
                  />
                  <div
                    className={`absolute bottom-0 top-1/2 left-0 ${risk >= 0 ? 'bg-amber-300' : 'bg-emerald-400'}`}
                    style={{ width: `${Math.min(Math.abs(risk), 100)}%` }}
                  />
                </div>
                <span className="text-right font-mono">
                  {(item.weight * 100).toFixed(1)}%
                </span>
                <span
                  className={`text-right font-mono ${risk < 0 ? 'text-emerald-300' : ''}`}
                >
                  {risk.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex gap-4 border-t border-border pt-3 text-[11px] text-muted-foreground">
          <span>
            <i className="mr-1 inline-block size-1.5 bg-primary" />
            {t('Portfolio weight')}
          </span>
          <span>
            <i className="mr-1 inline-block size-1.5 bg-amber-300" />
            {t('Risk share')}
          </span>
          <span>
            <i className="mr-1 inline-block size-1.5 bg-emerald-400" />
            {t('Diversifier')}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
