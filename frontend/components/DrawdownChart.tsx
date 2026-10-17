'use client';
import { useLanguage } from '@/components/LanguageProvider';
import { MetricHelp } from '@/components/MetricHelp';

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts';

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import type { PortfolioAnalysis } from '@/lib/types';

const config = {
  value: { label: 'Drawdown', color: '#e06c75' },
} satisfies ChartConfig;

export function DrawdownChart({ analysis }: { analysis: PortfolioAnalysis }) {
  const { t } = useLanguage();
  const data = analysis.drawdown.series.map((point) => ({
    ...point,
    value: point.value * 100,
  }));
  return (
    <Card id="drawdown" className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-center justify-between border-b border-border py-3">
        <div>
          <p className="section-label flex items-center gap-1">
            {t('Drawdown analysis')}
            <MetricHelp metric="drawdown" />
          </p>
          <p className="mt-1 text-[12px] text-muted-foreground">
            {t('Decline from the running wealth high-water mark')}
          </p>
        </div>
        <div className="text-right">
          <p className="font-mono text-sm text-rose-300">
            {(analysis.drawdown.max_drawdown * 100).toFixed(2)}%
          </p>
          <p className="text-[11px] text-muted-foreground">{t('Maximum')}</p>
        </div>
      </CardHeader>
      <CardContent className="p-3">
        <ChartContainer
          config={{ value: { ...config.value, label: t('Drawdown') } }}
          className="h-[180px] w-full aspect-auto"
        >
          <AreaChart
            data={data}
            margin={{ left: 4, right: 4, top: 8, bottom: 0 }}
          >
            <defs>
              <linearGradient id="drawdown-fill" x1="0" x2="0" y1="0" y2="1">
                <stop
                  offset="0"
                  stopColor="var(--color-value)"
                  stopOpacity={0.04}
                />
                <stop
                  offset="1"
                  stopColor="var(--color-value)"
                  stopOpacity={0.32}
                />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 4" />
            <ReferenceLine y={0} stroke="#51606b" />
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
              fill="url(#drawdown-fill)"
              stroke="var(--color-value)"
              strokeWidth={1.5}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
