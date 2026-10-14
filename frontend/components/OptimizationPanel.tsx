'use client';

import { useState } from 'react';
import { AlertTriangle, ArrowRight, Info, Play, SlidersHorizontal } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { optimizePortfolio } from '@/lib/api';
import type {
  OptimizationMetrics,
  OptimizationObjective,
  OptimizationResult,
  PositionInput,
} from '@/lib/types';

const objectiveLabels: Record<OptimizationObjective, string> = {
  minimum_volatility: 'Minimum volatility',
  maximum_sharpe: 'Maximum Sharpe',
  risk_parity: 'Risk parity',
};

function percent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function signedPercent(value: number): string {
  return `${value > 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
}

function ComparisonMetric({
  label,
  current,
  optimized,
}: {
  label: string;
  current: string;
  optimized: string;
}) {
  return (
    <div className="grid grid-cols-[1fr_90px_90px] items-center gap-2 border-b border-border px-3 py-2.5 last:border-0">
      <span className="text-[9px] uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-right font-mono text-[11px] text-muted-foreground">{current}</span>
      <span className="text-right font-mono text-[11px] text-primary">{optimized}</span>
    </div>
  );
}

function MetricComparison({ result }: { result: OptimizationResult }) {
  const metric = (key: keyof OptimizationMetrics) => {
    if (key === 'sharpe_ratio') {
      return [result.current.sharpe_ratio?.toFixed(2) ?? '—', result.optimized.sharpe_ratio?.toFixed(2) ?? '—'];
    }
    if (key === 'effective_positions') {
      return [result.current.effective_positions.toFixed(2), result.optimized.effective_positions.toFixed(2)];
    }
    return [percent(result.current[key] as number), percent(result.optimized[key] as number)];
  };
  const [returnCurrent, returnOptimized] = metric('annualized_return');
  const [volCurrent, volOptimized] = metric('annualized_volatility');
  const [sharpeCurrent, sharpeOptimized] = metric('sharpe_ratio');
  const [effectiveCurrent, effectiveOptimized] = metric('effective_positions');

  return (
    <div className="border border-border">
      <div className="grid grid-cols-[1fr_90px_90px] gap-2 bg-muted/30 px-3 py-2 text-[8px] uppercase tracking-wider text-muted-foreground">
        <span>Same historical sample</span><span className="text-right">Current</span><span className="text-right">Optimized</span>
      </div>
      <ComparisonMetric label="Annualized return" current={returnCurrent} optimized={returnOptimized} />
      <ComparisonMetric label="Annualized volatility" current={volCurrent} optimized={volOptimized} />
      <ComparisonMetric label="Sharpe estimate" current={sharpeCurrent} optimized={sharpeOptimized} />
      <ComparisonMetric label="Effective positions" current={effectiveCurrent} optimized={effectiveOptimized} />
    </div>
  );
}

export function OptimizationPanel({
  positions,
  lookbackYears,
  riskFreeRate,
}: {
  positions: PositionInput[];
  lookbackYears: number;
  riskFreeRate: number;
}) {
  const [objective, setObjective] = useState<OptimizationObjective>('minimum_volatility');
  const [capPercent, setCapPercent] = useState('');
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [resultKey, setResultKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputKey = JSON.stringify({ positions, lookbackYears, riskFreeRate, objective, capPercent });
  const currentResult = resultKey === inputKey ? result : null;
  const cleanPositions = positions.map((position) => ({
    ...position,
    ticker: position.ticker.trim().toUpperCase(),
  }));
  const maxWeight = capPercent.trim() === '' ? null : Number(capPercent) / 100;
  const minFeasibleCap = positions.length > 0 ? 100 / positions.length : 100;

  async function runOptimization() {
    setError(null);
    if (cleanPositions.length === 0) {
      setError('Add at least one position before optimizing.');
      return;
    }
    const tickers = cleanPositions.map((position) => position.ticker);
    if (tickers.some((ticker) => !ticker) || new Set(tickers).size !== tickers.length) {
      setError('Enter a unique ticker for every position.');
      return;
    }
    if (Math.abs(cleanPositions.reduce((total, item) => total + item.weight, 0) - 1) > 1e-4) {
      setError('Portfolio weights must sum to 100%.');
      return;
    }
    if (maxWeight !== null && (!Number.isFinite(maxWeight) || maxWeight <= 0 || maxWeight > 1 || positions.length * maxWeight < 1 - 1e-10)) {
      setError(`The maximum position must be between ${minFeasibleCap.toFixed(1)}% and 100% for ${positions.length} assets.`);
      return;
    }

    setLoading(true);
    try {
      const response = await optimizePortfolio({
        positions: cleanPositions,
        lookback_years: lookbackYears,
        risk_free_rate: riskFreeRate,
        objective,
        max_position_weight: maxWeight,
      });
      setResult(response);
      setResultKey(inputKey);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The optimization could not be completed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card id="optimization" className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-start justify-between border-b border-border py-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="section-label">Optimization</p>
            <Badge className="rounded-sm border-sky-300/25 bg-sky-300/10 text-[7px] text-sky-200">PHASE 5 · HISTORICAL</Badge>
          </div>
          <p className="mt-1 text-[10px] text-muted-foreground">Compare an allocation fitted to the selected return history</p>
        </div>
        <SlidersHorizontal className="size-4 text-primary" />
      </CardHeader>

      <CardContent className="p-0">
        <div className="grid xl:grid-cols-[290px_minmax(0,1fr)]">
          <section className="border-b border-border p-4 xl:border-r xl:border-b-0" aria-label="Optimization controls">
            <label htmlFor="optimization-objective" className="text-[9px] uppercase tracking-wider text-muted-foreground">
              Objective
              <NativeSelect id="optimization-objective" className="mt-1 w-full" value={objective} onChange={(event) => setObjective(event.target.value as OptimizationObjective)}>
                {Object.entries(objectiveLabels).map(([value, label]) => (
                  <NativeSelectOption key={value} value={value}>{label}</NativeSelectOption>
                ))}
              </NativeSelect>
            </label>
            <label htmlFor="optimization-cap" className="mt-4 block text-[9px] uppercase tracking-wider text-muted-foreground">
              Max position weight · optional
              <div className="relative mt-1">
                <Input id="optimization-cap" type="number" min={minFeasibleCap} max="100" step="1" value={capPercent} onChange={(event) => setCapPercent(event.target.value)} placeholder="No cap" className="h-8 rounded-sm pr-6 text-right font-mono text-xs" aria-label="Maximum position weight percent" />
                <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[9px]">%</span>
              </div>
            </label>
            <p className="mt-2 text-[8px] leading-4 text-muted-foreground">
              Long-only, fully invested. Minimum feasible cap: {minFeasibleCap.toFixed(1)}%.
            </p>
            <Button type="button" onClick={runOptimization} disabled={loading} className="mt-4 h-9 w-full rounded-sm text-[10px] font-semibold uppercase tracking-wider">
              <Play className="size-3" /> {loading ? 'Solving…' : 'Run optimization'}
            </Button>
            <div className="mt-3 border border-primary/20 bg-primary/5 p-3 text-[8px] leading-4 text-muted-foreground">
              <p className="flex items-center gap-1.5 font-semibold uppercase tracking-wide text-primary"><Info className="size-3" /> Comparison only</p>
              <p className="mt-1">This tool never changes your portfolio. Results are in-sample estimates, not forecasts or trade recommendations.</p>
            </div>
          </section>

          <section className="min-w-0 p-4" aria-label="Optimization comparison">
            {error && (
              <Alert variant="destructive" className="mb-3 rounded-sm">
                <AlertTriangle /><AlertTitle>Optimization unavailable</AlertTitle><AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            {currentResult ? (
              <>
                <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="section-label">{objectiveLabels[currentResult.objective]} comparison</p>
                    <p className="mt-1 text-[9px] text-muted-foreground">{currentResult.data_quality.source} · {currentResult.data_quality.observations} aligned daily returns</p>
                  </div>
                  <Badge variant="outline" className="rounded-sm text-[8px]">API RESULT</Badge>
                </div>
                <MetricComparison result={currentResult} />
                <div className="mt-3 grid gap-3 2xl:grid-cols-[1fr_180px]">
                  <div className="overflow-x-auto border border-border">
                    <table className="w-full min-w-[380px] border-collapse text-[9px]">
                      <thead className="bg-muted/30 text-left uppercase tracking-wide text-muted-foreground">
                        <tr><th className="px-2 py-2">Asset</th><th className="px-2 py-2 text-right">Current</th><th className="px-2 py-2 text-right">Optimized</th><th className="px-2 py-2 text-right">Change</th></tr>
                      </thead>
                      <tbody>
                        {currentResult.allocations.map((item) => (
                          <tr key={item.ticker} className="border-t border-border font-mono">
                            <td className="px-2 py-2 font-semibold text-foreground">{item.ticker}</td>
                            <td className="px-2 py-2 text-right text-muted-foreground">{percent(item.current_weight)}</td>
                            <td className="px-2 py-2 text-right text-primary">{percent(item.optimized_weight)}</td>
                            <td className={`px-2 py-2 text-right ${item.weight_change > 0 ? 'text-emerald-300' : item.weight_change < 0 ? 'text-rose-300' : 'text-muted-foreground'}`}>{signedPercent(item.weight_change)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="flex flex-col justify-center border border-border bg-background/35 p-3">
                    <p className="text-[8px] uppercase tracking-wider text-muted-foreground">One-way turnover</p>
                    <p className="mt-1 font-mono text-xl text-primary">{percent(currentResult.one_way_turnover)}</p>
                    <p className="mt-2 text-[8px] leading-4 text-muted-foreground">Half the total absolute weight change. Trading costs are excluded.</p>
                  </div>
                </div>
                <p className="mt-3 border-l-2 border-amber-300/50 pl-2 text-[8px] leading-4 text-muted-foreground">
                  {currentResult.methodology} {currentResult.limitations.join(' ')}
                </p>
                {currentResult.data_quality.warnings.map((warning) => (
                  <p key={warning} className="mt-2 text-[8px] text-amber-200/75">Data note: {warning}</p>
                ))}
              </>
            ) : (
              <div className="grid min-h-[220px] place-items-center border border-dashed border-border px-5 text-center">
                <div>
                  <SlidersHorizontal className="mx-auto size-6 text-primary" />
                  <p className="mt-3 text-sm font-semibold">{result ? 'Inputs changed' : 'Awaiting optimization'}</p>
                  <p className="mt-2 text-[9px] leading-5 text-muted-foreground">Run the deterministic solver to compare current and optimized weights on the same historical sample.</p>
                  <ArrowRight className="mx-auto mt-3 size-3.5 text-muted-foreground" />
                </div>
              </div>
            )}
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
