'use client';

import { Activity, Database, Info, Sigma } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import type { PortfolioAnalysis } from '@/lib/types';

const config = {
  value: { label: 'Rolling market beta', color: '#77bdfb' },
} satisfies ChartConfig;

function decimal(value: number | null) {
  return value === null ? 'Unavailable' : value.toFixed(2);
}

function percent(value: number | null) {
  if (value === null) return 'Unavailable';
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
}

export function FactorExposureChart({
  analysis,
}: {
  analysis: PortfolioAnalysis;
}) {
  const factor = analysis.factor_exposure;
  const rollingData = factor.rolling_beta;

  return (
    <Card id="factor-exposure" className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-start justify-between border-b border-border py-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="section-label">Factor exposure</p>
            <Badge className="rounded-sm border-sky-300/25 bg-sky-300/10 text-[7px] text-sky-200">
              PHASE 4 · REGRESSION
            </Badge>
          </div>
          <p className="mt-1 text-[10px] text-muted-foreground">
            Daily excess-return regression against the SPY market proxy
          </p>
        </div>
        <Activity className="size-4 text-primary" />
      </CardHeader>

      <CardContent className="p-0">
        {!factor.available ? (
          <div className="m-4 border border-amber-300/20 bg-amber-300/5 p-4">
            <p className="flex items-center gap-2 text-[10px] font-semibold text-amber-200">
              <Info className="size-3.5" /> Factor estimate unavailable
            </p>
            <p className="mt-2 text-[9px] leading-4 text-muted-foreground">
              {factor.unavailable_reason ??
                'The benchmark regression could not be estimated from the aligned history.'}
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-px bg-border lg:grid-cols-4">
              <div className="bg-card p-3">
                <p className="text-[8px] uppercase tracking-wider text-muted-foreground">
                  Market beta
                </p>
                <p className="mt-1 font-mono text-lg text-primary">
                  {decimal(factor.market_beta)}
                </p>
                <p className="mt-1 text-[8px] text-muted-foreground">
                  Sensitivity to SPY excess returns
                </p>
              </div>
              <div className="bg-card p-3">
                <p className="text-[8px] uppercase tracking-wider text-muted-foreground">
                  Annualized alpha
                </p>
                <p
                  className={`mt-1 font-mono text-lg ${
                    (factor.alpha_annualized ?? 0) >= 0
                      ? 'text-emerald-300'
                      : 'text-rose-300'
                  }`}
                >
                  {percent(factor.alpha_annualized)}
                </p>
                <p className="mt-1 text-[8px] text-muted-foreground">
                  Historical intercept · not forecast
                </p>
              </div>
              <div className="bg-card p-3">
                <p className="text-[8px] uppercase tracking-wider text-muted-foreground">
                  Regression R²
                </p>
                <p className="mt-1 font-mono text-lg">
                  {factor.r_squared === null
                    ? 'Unavailable'
                    : `${(factor.r_squared * 100).toFixed(1)}%`}
                </p>
                <p className="mt-1 text-[8px] text-muted-foreground">
                  Variation explained by market proxy
                </p>
              </div>
              <div className="bg-card p-3">
                <p className="text-[8px] uppercase tracking-wider text-muted-foreground">
                  Idiosyncratic vol
                </p>
                <p className="mt-1 font-mono text-lg">
                  {factor.idiosyncratic_volatility === null
                    ? 'Unavailable'
                    : `${(factor.idiosyncratic_volatility * 100).toFixed(2)}%`}
                </p>
                <p className="mt-1 text-[8px] text-muted-foreground">
                  Annualized regression residual
                </p>
              </div>
            </div>

            <div className="grid gap-3 p-3 xl:grid-cols-[minmax(0,1fr)_230px]">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Rolling {factor.rolling_window_days}-day beta
                  </p>
                  <span className="font-mono text-[8px] text-muted-foreground">
                    {rollingData.length} estimates
                  </span>
                </div>
                {rollingData.length > 0 ? (
                  <ChartContainer
                    config={config}
                    className="h-[170px] w-full aspect-auto"
                  >
                    <LineChart
                      data={rollingData}
                      margin={{ left: 4, right: 6, top: 8, bottom: 0 }}
                    >
                      <CartesianGrid vertical={false} strokeDasharray="3 4" />
                      <ReferenceLine
                        y={1}
                        stroke="#d6a34c"
                        strokeDasharray="4 4"
                      />
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
                        width={34}
                        domain={['auto', 'auto']}
                        tickFormatter={(value) => Number(value).toFixed(2)}
                      />
                      <ChartTooltip
                        cursor={false}
                        content={
                          <ChartTooltipContent
                            labelKey="date"
                            formatter={(value) => (
                              <span className="font-mono">
                                {Number(value).toFixed(3)}
                              </span>
                            )}
                          />
                        }
                      />
                      <Line
                        dataKey="value"
                        type="monotone"
                        dot={false}
                        stroke="var(--color-value)"
                        strokeWidth={1.5}
                      />
                    </LineChart>
                  </ChartContainer>
                ) : (
                  <div className="grid h-[170px] place-items-center border border-dashed border-border text-[9px] text-muted-foreground">
                    More history is required for rolling beta.
                  </div>
                )}
              </div>

              <div className="space-y-2 border border-border bg-background/35 p-3">
                <p className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wider text-foreground">
                  <Sigma className="size-3 text-primary" /> Model scope
                </p>
                <div className="space-y-2 text-[8px] leading-4 text-muted-foreground">
                  <p>
                    <span className="text-foreground">Model:</span>{' '}
                    {factor.model.replace('_', ' ')}
                  </p>
                  <p>
                    <span className="text-foreground">Benchmark:</span>{' '}
                    {factor.benchmark_ticker}
                  </p>
                  <p>
                    <span className="text-foreground">Observations:</span>{' '}
                    {factor.observations}
                  </p>
                  <p>
                    <span className="text-foreground">SMB / HML:</span>{' '}
                    unavailable — no factor series was supplied
                  </p>
                </div>
                <div className="border-t border-border pt-2 text-[8px] leading-4 text-muted-foreground">
                  Historical regression estimate. It describes the selected
                  sample and does not predict future exposure.
                </div>
              </div>
            </div>
          </>
        )}

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border px-3 py-2 text-[8px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Database className="size-3 text-primary" />
            {factor.benchmark_source ?? 'Benchmark source unavailable'}
          </span>
          <span>{factor.methodology}</span>
        </div>
      </CardContent>
    </Card>
  );
}
