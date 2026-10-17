'use client';

import { useLanguage } from '@/components/LanguageProvider';
import { Link2 } from 'lucide-react';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import type { PortfolioAnalysis } from '@/lib/types';

function cellColor(value: number) {
  const alpha = 0.1 + Math.abs(value) * 0.55;
  return value >= 0
    ? `rgba(67, 139, 197, ${alpha})`
    : `rgba(214, 163, 76, ${alpha})`;
}

export function CorrelationHeatmap({
  analysis,
}: {
  analysis: PortfolioAnalysis;
}) {
  const { t } = useLanguage();
  const { tickers, matrix, highest_correlations: pairs } = analysis.correlation;
  return (
    <Card id="correlation" className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-center justify-between border-b border-border py-3">
        <div>
          <p className="section-label">{t('Correlation')}</p>
          <p className="mt-1 text-[12px] text-muted-foreground">
            {t('Pearson correlation of aligned daily returns')}
          </p>
        </div>
        <Link2 className="size-4 text-primary" />
      </CardHeader>
      <CardContent className="grid gap-4 p-4 lg:grid-cols-[minmax(280px,1fr)_180px]">
        <div className="overflow-x-auto">
          <table
            className="w-full min-w-[310px] table-fixed border-separate border-spacing-1 text-center font-mono text-[12px]"
            aria-label={t('Asset correlation matrix')}
          >
            <thead>
              <tr>
                <th className="pb-1 text-right font-sans text-[11px] font-medium text-muted-foreground">
                  {t('ASSET')}
                </th>
                <>
                  {tickers.map((ticker) => (
                    <th
                      key={ticker}
                      className="pb-1 font-medium text-muted-foreground"
                    >
                      {ticker}
                    </th>
                  ))}
                </>
              </tr>
            </thead>
            <tbody>
              {tickers.map((rowTicker, row) => (
                <tr key={rowTicker}>
                  <th className="pr-1 text-right font-medium text-muted-foreground">
                    {rowTicker}
                  </th>
                  {matrix[row].map((value, column) => (
                    <td
                      key={`${row}-${column}`}
                      className="h-9 border border-white/5 tabular-nums text-foreground"
                      style={{ backgroundColor: cellColor(value) }}
                      title={`${rowTicker} / ${tickers[column]}: ${value.toFixed(3)}`}
                    >
                      {value.toFixed(2)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            {t('Strongest pairs')}
          </p>
          <div className="space-y-1.5">
            {pairs.slice(0, 4).map((pair) => (
              <div
                key={`${pair.asset_1}-${pair.asset_2}`}
                className="flex items-center justify-between border-b border-border pb-1.5 text-[12px]"
              >
                <span className="font-mono">
                  {pair.asset_1} / {pair.asset_2}
                </span>
                <span
                  className={
                    pair.correlation > 0.75
                      ? 'font-mono text-amber-300'
                      : 'font-mono'
                  }
                >
                  {pair.correlation.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
