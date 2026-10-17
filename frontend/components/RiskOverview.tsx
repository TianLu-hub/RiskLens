'use client';
import { useLanguage } from '@/components/LanguageProvider';

import {
  Activity,
  ArrowDownRight,
  ChartNoAxesCombined,
  Gauge,
  Sigma,
  Waves,
} from 'lucide-react';
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts';

import { RiskMetricCard } from '@/components/RiskMetricCard';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import type { PortfolioAnalysis } from '@/lib/types';

const chartConfig = {
  value: { label: 'Cumulative return', color: '#77bdfb' },
} satisfies ChartConfig;
const pct = (value: number) => `${(value * 100).toFixed(2)}%`;

export function RiskOverview({ analysis }: { analysis: PortfolioAnalysis }) {
  const { t } = useLanguage();
  const { metrics, drawdown } = analysis;
  const cards = [
    {
      label: 'Annualized return',
      value: pct(metrics.annualized_return),
      detail: 'Geometric · 252-day',
      icon: ChartNoAxesCombined,
    },
    {
      label: 'Annualized volatility',
      value: pct(metrics.annualized_volatility),
      detail: 'Sample covariance',
      icon: Waves,
    },
    {
      label: 'Sharpe ratio',
      value: metrics.sharpe_ratio?.toFixed(2) ?? 'N/A',
      detail: `Rf ${pct(metrics.risk_free_rate)}`,
      icon: Gauge,
    },
    {
      label: '95% 1-day VaR',
      value: pct(metrics.var),
      detail: 'Historical loss threshold',
      icon: Sigma,
    },
    {
      label: '95% 1-day CVaR',
      value: pct(metrics.cvar),
      detail: 'Expected shortfall',
      icon: Activity,
    },
    {
      label: 'Max drawdown',
      value: pct(drawdown.max_drawdown),
      detail: 'Historical peak to trough',
      icon: ArrowDownRight,
      tone: 'negative' as const,
    },
  ];

  return (
    <section id="overview" aria-label={t('Portfolio risk metrics')}>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-border bg-border md:grid-cols-3 xl:grid-cols-6">
        {cards.map((card) => (
          <RiskMetricCard key={card.label} {...card} />
        ))}
      </div>
    </section>
  );
}

export function PortfolioPerformance({
  analysis,
}: {
  analysis: PortfolioAnalysis;
}) {
  const { t } = useLanguage();
  const chartData = analysis.performance.map((point) => ({
    ...point,
    value: point.value * 100,
  }));
  return (
    <Card className="rounded-md bg-card ring-border">
      <CardHeader className="flex-row items-center justify-between border-b border-border py-3">
        <div>
          <p className="section-label">{t('Portfolio performance')}</p>
          <p className="mt-1 text-[12px] text-muted-foreground">
            {t('Growth from the first aligned observation')}
          </p>
        </div>
        <span className="font-mono text-lg text-primary">
          {pct(analysis.performance.at(-1)?.value ?? 0)}
        </span>
      </CardHeader>
      <CardContent className="p-3">
        <ChartContainer
          config={{
            value: { ...chartConfig.value, label: t('Cumulative return') },
          }}
          className="h-[260px] w-full aspect-auto"
        >
          <AreaChart
            data={chartData}
            margin={{ left: 4, right: 4, top: 10, bottom: 0 }}
          >
            <defs>
              <linearGradient id="performance-fill" x1="0" x2="0" y1="0" y2="1">
                <stop
                  offset="0"
                  stopColor="var(--color-value)"
                  stopOpacity={0.3}
                />
                <stop
                  offset="1"
                  stopColor="var(--color-value)"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 4" />
            <XAxis
              dataKey="date"
              minTickGap={48}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => String(value).slice(0, 7)}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={42}
              tickFormatter={(value) => `${Number(value).toFixed(0)}%`}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  labelKey="date"
                  formatter={(value) => (
                    <span className="font-mono">
                      {Number(value).toFixed(2)}%
                    </span>
                  )}
                />
              }
            />
            <Area
              dataKey="value"
              type="monotone"
              fill="url(#performance-fill)"
              stroke="var(--color-value)"
              strokeWidth={2}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
