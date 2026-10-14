'use client';

import { useState } from 'react';
import { AlertTriangle, History, Play } from 'lucide-react';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { backtestPortfolio } from '@/lib/api';
import type { BacktestMetrics, BacktestResult, OptimizationObjective, PositionInput } from '@/lib/types';

const chartConfig = {
  current: { label: 'Current mix', color: '#81929f' },
  optimized: { label: 'Walk-forward optimized', color: '#77bdfb' },
  spy: { label: 'SPY buy-and-hold', color: '#c6a76d' },
} satisfies ChartConfig;

const objectives: Record<OptimizationObjective, string> = {
  minimum_volatility: 'Minimum volatility',
  maximum_sharpe: 'Maximum Sharpe',
  risk_parity: 'Risk parity',
};

function pct(value: number): string { return `${(value * 100).toFixed(2)}%`; }
function decimal(value: number | null): string { return value === null ? '—' : value.toFixed(2); }

function SummaryTable({ result }: { result: BacktestResult }) {
  const rows: Array<[string, (metric: BacktestMetrics) => string]> = [
    ['Cumulative return', (m) => pct(m.cumulative_return)],
    ['Annualized return', (m) => pct(m.annualized_return)],
    ['Annualized volatility', (m) => pct(m.annualized_volatility)],
    ['Sharpe estimate', (m) => decimal(m.sharpe_ratio)],
    ['Maximum drawdown', (m) => pct(m.max_drawdown)],
    ['One-way turnover', (m) => pct(m.total_one_way_turnover)],
    ['Costs / initial capital', (m) => pct(m.total_cost_fraction_of_initial_capital)],
  ];
  return (
    <div className="overflow-x-auto border border-border">
      <table className="w-full min-w-[440px] border-collapse text-[9px]">
        <thead className="bg-muted/30 uppercase tracking-wide text-muted-foreground">
          <tr><th className="px-3 py-2 text-left">Out-of-sample metric</th><th className="px-3 py-2 text-right">Current mix</th><th className="px-3 py-2 text-right">Optimized</th>{result.spy_buy_and_hold && <th className="px-3 py-2 text-right">SPY</th>}</tr>
        </thead>
        <tbody>
          {rows.map(([label, format]) => (
            <tr key={label} className="border-t border-border">
              <td className="px-3 py-2 uppercase tracking-wide text-muted-foreground">{label}</td>
              <td className="px-3 py-2 text-right font-mono">{format(result.current)}</td>
              <td className="px-3 py-2 text-right font-mono text-primary">{format(result.optimized)}</td>
              {result.spy_buy_and_hold && <td className="px-3 py-2 text-right font-mono text-amber-200">{format(result.spy_buy_and_hold)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BacktestPanel({ positions, lookbackYears, riskFreeRate }: {
  positions: PositionInput[];
  lookbackYears: number;
  riskFreeRate: number;
}) {
  const [objective, setObjective] = useState<OptimizationObjective>('minimum_volatility');
  const [trainingDays, setTrainingDays] = useState(504);
  const [costBps, setCostBps] = useState('10');
  const [capPercent, setCapPercent] = useState('');
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [resultKey, setResultKey] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inputKey = JSON.stringify({ positions, lookbackYears, riskFreeRate, objective, trainingDays, costBps, capPercent });
  const current = resultKey === inputKey ? result : null;

  async function runBacktest() {
    setError(null);
    const clean = positions.map((item) => ({ ...item, ticker: item.ticker.trim().toUpperCase() }));
    const tickers = clean.map((item) => item.ticker);
    if (!clean.length || tickers.some((item) => !item) || new Set(tickers).size !== tickers.length) {
      setError('Enter at least one position with unique, nonempty tickers.'); return;
    }
    if (Math.abs(clean.reduce((sum, item) => sum + item.weight, 0) - 1) > 1e-4) {
      setError('Portfolio weights must sum to 100%.'); return;
    }
    if (lookbackYears < 2) {
      setError('Select a 3- or 5-year lookback to reserve separate training and forward periods.'); return;
    }
    const cost = Number(costBps);
    const cap = capPercent.trim() === '' ? null : Number(capPercent) / 100;
    if (!Number.isFinite(cost) || cost < 0 || cost > 100 || costBps.trim() === '') {
      setError('Trading cost must be between 0 and 100 basis points.'); return;
    }
    if (cap !== null && (!Number.isFinite(cap) || cap <= 0 || cap > 1 || clean.length * cap < 1 - 1e-10)) {
      setError(`Maximum position weight must be at least ${(100 / clean.length).toFixed(1)}% for this portfolio.`); return;
    }
    setLoading(true);
    try {
      const response = await backtestPortfolio({
        positions: clean, lookback_years: lookbackYears, risk_free_rate: riskFreeRate,
        objective, max_position_weight: cap, training_days: trainingDays,
        rebalance_days: 21, cost_bps: cost,
      });
      setResult(response);
      setResultKey(inputKey);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The backtest could not be completed.');
    } finally { setLoading(false); }
  }

  const chartData = current?.series.map((point) => ({
    date: point.date,
    current: point.current_wealth * 100,
    optimized: point.optimized_wealth * 100,
    spy: point.spy_wealth === null ? null : point.spy_wealth * 100,
  }));

  return (
    <Card id="backtest" className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-start justify-between border-b border-border py-3">
        <div>
          <div className="flex flex-wrap items-center gap-2"><p className="section-label">Walk-forward backtest</p><Badge className="rounded-sm border-sky-300/25 bg-sky-300/10 text-[7px] text-sky-200">PHASE 6 · OUT-OF-SAMPLE</Badge></div>
          <p className="mt-1 text-[10px] text-muted-foreground">Train on earlier daily returns; test only on subsequent dates</p>
        </div>
        <History className="size-4 text-primary" />
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid xl:grid-cols-[290px_minmax(0,1fr)]">
          <section className="border-b border-border p-4 xl:border-r xl:border-b-0" aria-label="Backtest controls">
            <label htmlFor="backtest-objective" className="block text-[9px] uppercase tracking-wider text-muted-foreground">Objective
              <NativeSelect id="backtest-objective" className="mt-1 w-full" value={objective} onChange={(event) => setObjective(event.target.value as OptimizationObjective)}>
                {Object.entries(objectives).map(([value, label]) => <NativeSelectOption key={value} value={value}>{label}</NativeSelectOption>)}
              </NativeSelect>
            </label>
            <label htmlFor="backtest-training" className="mt-4 block text-[9px] uppercase tracking-wider text-muted-foreground">Trailing training window
              <NativeSelect id="backtest-training" className="mt-1 w-full" value={trainingDays} onChange={(event) => setTrainingDays(Number(event.target.value))}>
                <NativeSelectOption value="252">252 trading days · ~1 year</NativeSelectOption>
                <NativeSelectOption value="504">504 trading days · ~2 years</NativeSelectOption>
              </NativeSelect>
            </label>
            <label htmlFor="backtest-cost" className="mt-4 block text-[9px] uppercase tracking-wider text-muted-foreground">Cost per traded notional · bps
              <Input id="backtest-cost" type="number" min="0" max="100" step="1" value={costBps} onChange={(event) => setCostBps(event.target.value)} className="mt-1 h-8 rounded-sm text-right font-mono text-xs" />
            </label>
            <label htmlFor="backtest-cap" className="mt-4 block text-[9px] uppercase tracking-wider text-muted-foreground">Max position weight · optional %
              <Input id="backtest-cap" type="number" min={positions.length ? 100 / positions.length : 100} max="100" step="1" value={capPercent} onChange={(event) => setCapPercent(event.target.value)} placeholder="No cap" className="mt-1 h-8 rounded-sm text-right font-mono text-xs" />
            </label>
            <p className="mt-3 text-[8px] leading-4 text-muted-foreground">Rebalanced every 21 trading days (~monthly). Same historical source as portfolio analysis. Default lookback: 3 years; first ~2 years train, remaining ~1 year is tested forward.</p>
            <Button type="button" onClick={runBacktest} disabled={loading} className="mt-4 h-9 w-full rounded-sm text-[10px] font-semibold uppercase tracking-wider"><Play className="size-3" /> {loading ? 'Backtesting…' : 'Run backtest'}</Button>
            <div className="mt-3 border border-amber-300/20 bg-amber-300/5 p-3 text-[8px] leading-4 text-muted-foreground"><p className="font-semibold uppercase tracking-wide text-amber-200">Hypothetical historical simulation</p><p className="mt-1">Not live trading, a prediction, or a recommendation. Portfolio selection today may still embed hindsight.</p></div>
          </section>
          <section className="min-w-0 space-y-3 p-4" aria-label="Backtest results">
            {error && <Alert variant="destructive" className="rounded-sm"><AlertTriangle /><AlertTitle>Backtest unavailable</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
            {current ? <>
              <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="section-label">Forward test · {current.series.length} trading days</p><p className="mt-1 text-[9px] text-muted-foreground">{current.data_quality.source} daily prices · {current.series[0]?.date} — {current.series.at(-1)?.date} · {current.folds.length} windows</p></div><Badge variant="outline" className="rounded-sm text-[8px]">API RESULT</Badge></div>
              <ChartContainer config={chartConfig} className="h-[210px] w-full aspect-auto border border-border p-2">
                <LineChart data={chartData} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 4" />
                  <XAxis dataKey="date" minTickGap={40} tickLine={false} axisLine={false} tickFormatter={(value) => String(value).slice(0, 7)} />
                  <YAxis tickLine={false} axisLine={false} width={42} domain={['auto', 'auto']} tickFormatter={(value) => Number(value).toFixed(0)} />
                  <ChartTooltip content={<ChartTooltipContent labelKey="date" formatter={(value) => <span className="font-mono">{Number(value).toFixed(2)} wealth index</span>} />} />
                  <Line dataKey="current" name="Current mix" type="monotone" stroke="var(--color-current)" strokeWidth={1.5} dot={false} />
                  <Line dataKey="optimized" name="Walk-forward optimized" type="monotone" stroke="var(--color-optimized)" strokeWidth={1.7} dot={false} />
                  {current.spy_buy_and_hold && <Line dataKey="spy" name="SPY buy-and-hold" type="monotone" stroke="var(--color-spy)" strokeWidth={1.2} dot={false} />}
                </LineChart>
              </ChartContainer>
              <p className="text-[8px] text-muted-foreground">Wealth index begins at 100. Current mix and optimized strategy both rebalance monthly and pay the same configured cost; SPY is buy-and-hold without costs when SPY is in the portfolio.</p>
              <SummaryTable result={current} />
              <details className="border border-border px-3 py-2 text-[9px]"><summary className="cursor-pointer uppercase tracking-wide text-muted-foreground">Inspect {current.folds.length} training / forward windows</summary><div className="mt-2 max-h-48 overflow-auto"><table className="w-full min-w-[440px] border-collapse font-mono text-[9px]"><thead><tr className="text-left text-muted-foreground"><th className="py-1">Training ends</th><th>Forward test</th><th className="text-right">Optimized turnover</th></tr></thead><tbody>{current.folds.map((fold) => <tr key={fold.test_start} className="border-t border-border"><td className="py-1">{fold.train_end}</td><td>{fold.test_start} — {fold.test_end}</td><td className="text-right">{pct(fold.optimized_one_way_turnover)}</td></tr>)}</tbody></table></div></details>
              {current.data_quality.warnings.map((warning) => <p key={warning} className="text-[8px] text-amber-200">{warning}</p>)}
              <p className="border-l-2 border-amber-300/50 pl-2 text-[8px] leading-4 text-muted-foreground">{current.methodology} {current.limitations.join(' ')}</p>
            </> : <div className="flex min-h-[220px] flex-col items-center justify-center border border-dashed border-border px-5 text-center"><History className="size-6 text-primary" /><p className="mt-3 text-sm font-semibold">Awaiting walk-forward test</p><p className="mt-2 max-w-lg text-[9px] leading-5 text-muted-foreground">Run the Python engine to separate training dates from later test dates and compare net hypothetical wealth.</p></div>}
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
