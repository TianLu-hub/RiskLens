'use client';

import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, LoaderCircle, Play, ShieldCheck } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts';

import { DataProvenance } from '@/components/DataProvenance';
import { KupiecTest } from '@/components/KupiecTest';
import { useLanguage } from '@/components/LanguageProvider';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';
import { ApiError, backtestVarPortfolio } from '@/lib/api';
import type { PositionInput } from '@/lib/types';
import {
  localizeVarNotice,
  validateVarBacktestInput,
  varBacktestCopy,
  varBacktestKey,
  varBacktestRequest,
  varBreachRows,
  type VarBacktestResponse,
  type VarInputIssue,
} from '@/lib/var-backtest';

function pct(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

type PanelError = {
  key: string;
  kind:
    | VarInputIssue
    | 'insufficient'
    | 'invalidTicker'
    | 'unavailable'
    | 'error';
  detail?: string;
};

export function VarBacktestPanel({
  positions,
  lookbackYears,
  active,
}: {
  positions: PositionInput[];
  lookbackYears: number;
  active: boolean;
}) {
  const { locale, t } = useLanguage();
  const c = varBacktestCopy[locale];
  const [windowDays, setWindowDays] = useState(252);
  const [confidence, setConfidence] = useState(0.95);
  const [saved, setSaved] = useState<{
    key: string;
    result: VarBacktestResponse;
  } | null>(null);
  const [error, setError] = useState<PanelError | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const request = varBacktestRequest(
    positions,
    lookbackYears,
    windowDays,
    confidence,
  );
  const inputKey = varBacktestKey(request);
  const current = saved?.key === inputKey ? saved.result : null;
  const visibleError = error?.key === inputKey ? error : null;
  const loading = pending === inputKey;
  const stale = saved !== null && saved.key !== inputKey;

  // Cancel requests when model inputs change or the panel unmounts. The generation
  // guard below also protects against transports that resolve after cancellation.
  useEffect(() => () => controller.current?.abort(), [inputKey]);

  async function run() {
    const issue = validateVarBacktestInput(request);
    if (issue) {
      setError({ key: inputKey, kind: issue });
      return;
    }
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    const sequence = ++generation.current;
    setError(null);
    setPending(inputKey);
    setExpanded(false);
    try {
      const result = await backtestVarPortfolio(request, abort.signal);
      if (abort.signal.aborted || sequence !== generation.current) return;
      setSaved({ key: inputKey, result });
    } catch (reason) {
      if (abort.signal.aborted || sequence !== generation.current) return;
      const code = reason instanceof ApiError ? reason.code : undefined;
      const detail = reason instanceof Error ? reason.message : undefined;
      const kind =
        code === 'INSUFFICIENT_HISTORY'
          ? 'insufficient'
          : code === 'INVALID_TICKER'
            ? 'invalidTicker'
            : reason instanceof ApiError && reason.status === undefined
              ? 'unavailable'
              : 'error';
      setError({ key: inputKey, kind, detail });
    } finally {
      if (sequence === generation.current) setPending(null);
    }
  }

  const breachRows = current ? varBreachRows(current) : [];
  const displayedRows = expanded ? breachRows : breachRows.slice(0, 10);
  const chartConfig = {
    var_loss: { label: c.var, color: '#77bdfb' },
    realized_loss: { label: c.loss, color: '#81929f' },
    breach_loss: { label: c.breach, color: '#f87171' },
  };
  const chartData = current?.series.map((point) => ({
    ...point,
    breach_loss: point.breach ? point.realized_loss : null,
  }));
  const notices =
    current?.data_quality.warnings.map((message) =>
      localizeVarNotice(t(message), locale),
    ) ?? [];

  return (
    <Card id="var-backtest" className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-start justify-between gap-4 border-b border-border py-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="section-label">{c.title}</h2>
            <Badge className="rounded-sm border-primary/25 bg-primary/10 text-primary">
              {c.badge}
            </Badge>
          </div>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            {c.subtitle}
          </p>
        </div>
        <ShieldCheck
          className="mt-1 size-5 shrink-0 text-primary"
          aria-hidden="true"
        />
      </CardHeader>
      <CardContent className="p-0">
        <div className="grid xl:grid-cols-[280px_minmax(0,1fr)]">
          <form
            aria-label={c.controls}
            onSubmit={(event) => {
              event.preventDefault();
              void run();
            }}
            className="space-y-5 border-b border-border p-4 xl:border-r xl:border-b-0"
          >
            <p className="text-sm font-medium text-primary">{c.method}</p>
            <label
              htmlFor="var-confidence"
              className="block text-sm text-muted-foreground"
            >
              {c.confidence}
              <NativeSelect
                id="var-confidence"
                className="mt-2 w-full"
                value={confidence}
                onChange={(event) => setConfidence(Number(event.target.value))}
              >
                <NativeSelectOption value={0.95}>95%</NativeSelectOption>
                <NativeSelectOption value={0.99}>99%</NativeSelectOption>
              </NativeSelect>
            </label>
            <label
              htmlFor="var-window"
              className="block text-sm text-muted-foreground"
            >
              {c.window}
              <NativeSelect
                id="var-window"
                className="mt-2 w-full"
                value={windowDays}
                onChange={(event) => setWindowDays(Number(event.target.value))}
              >
                {[126, 252, 504].map((days) => (
                  <NativeSelectOption key={days} value={days}>
                    {days} {c.tradingDays}
                  </NativeSelectOption>
                ))}
              </NativeSelect>
            </label>
            <div className="rounded-sm border border-border bg-muted/15 p-3 text-sm">
              <p className="text-muted-foreground">{c.history}</p>
              <p className="mt-1 font-mono text-base">
                {lookbackYears} {c.years}
              </p>
              <p className="mt-2 leading-6 text-muted-foreground">
                {c.historyNote}
              </p>
            </div>
            <Button
              type="submit"
              className="w-full rounded-sm"
              disabled={loading}
            >
              {loading ? (
                <LoaderCircle
                  className="size-4 animate-spin"
                  aria-hidden="true"
                />
              ) : (
                <Play className="size-4" aria-hidden="true" />
              )}
              {loading ? c.loading : c.run}
            </Button>
            <p className="text-xs leading-5 text-muted-foreground">
              {c.assumption}
            </p>
          </form>
          <div className="min-w-0 space-y-5 p-4" aria-busy={loading}>
            <output aria-live="polite" className="sr-only">
              {loading ? c.loading : ''}
            </output>
            {stale && (
              <output className="block border border-amber-300/25 bg-amber-300/5 p-3 text-sm leading-6 text-amber-200">
                {c.stale}
              </output>
            )}
            {visibleError && (
              <Alert variant="destructive">
                <AlertTriangle aria-hidden="true" />
                <AlertTitle>{c.failed}</AlertTitle>
                <AlertDescription>
                  <p>{c[visibleError.kind]}</p>
                  {visibleError.detail && (
                    <details className="mt-2">
                      <summary className="cursor-pointer">{c.details}</summary>
                      <p className="mt-2 break-words text-xs">
                        {t(visibleError.detail)}
                      </p>
                    </details>
                  )}
                </AlertDescription>
              </Alert>
            )}
            {!current && (
              <div className="flex min-h-64 flex-col items-center justify-center border border-dashed border-border px-6 py-12 text-center">
                <ShieldCheck
                  className="mb-4 size-8 text-primary"
                  aria-hidden="true"
                />
                <h3 className="text-base font-semibold">{c.empty}</h3>
                <p className="mt-3 max-w-lg text-sm leading-6 text-muted-foreground">
                  {c.emptyNote}
                </p>
              </div>
            )}
            {current && (
              <>
                <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-border bg-border lg:grid-cols-3">
                  {[
                    [c.observed, String(current.breach_count)],
                    [c.expected, current.expected_breach_count.toFixed(2)],
                    [c.testSample, String(current.test_observations)],
                    [c.observedRate, pct(current.breach_rate)],
                    [c.expectedRate, pct(current.expected_breach_rate)],
                    [
                      c.testDates,
                      `${current.test_start} → ${current.test_end}`,
                    ],
                  ].map(([label, value]) => (
                    <div key={label} className="bg-card p-3">
                      <dt className="text-xs leading-5 text-muted-foreground">
                        {label}
                      </dt>
                      <dd
                        className={`mt-1 font-mono ${label === c.testDates ? 'text-xs leading-6' : 'text-xl'}`}
                      >
                        {value}
                      </dd>
                    </div>
                  ))}
                </dl>
                <p className="text-xs leading-5 text-muted-foreground">
                  {c.expectedNote}
                </p>
                <KupiecTest result={current.kupiec_test} />
                {notices.length > 0 && (
                  <Alert className="border-amber-300/25 bg-amber-300/5 text-amber-200">
                    <AlertTriangle aria-hidden="true" />
                    <AlertTitle>{c.notices}</AlertTitle>
                    <AlertDescription>
                      <ul className="list-disc space-y-1 pl-4">
                        {notices.map((notice) => (
                          <li key={notice}>{notice}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}
                <section aria-label={c.chart}>
                  <h3 className="text-sm font-semibold">{c.chart}</h3>
                  <div className="my-3 flex flex-wrap gap-4 text-xs">
                    {Object.entries(chartConfig).map(([key, item]) => (
                      <span
                        key={key}
                        className="inline-flex items-center gap-2"
                      >
                        <span
                          className={`size-2 ${key === 'breach_loss' ? 'rounded-full' : ''}`}
                          style={{ backgroundColor: item.color }}
                          aria-hidden="true"
                        />
                        {item.label}
                      </span>
                    ))}
                  </div>
                  {active && (
                    <ChartContainer
                      config={chartConfig}
                      className="h-[280px] w-full sm:h-[320px]"
                      aria-label={c.chart}
                    >
                      <LineChart
                        data={chartData}
                        accessibilityLayer
                        margin={{ left: 2, right: 12, top: 12, bottom: 6 }}
                      >
                        <CartesianGrid vertical={false} strokeDasharray="3 3" />
                        <XAxis
                          dataKey="date"
                          tickLine={false}
                          axisLine={false}
                          minTickGap={60}
                          tickFormatter={(date: string) => date.slice(0, 7)}
                        />
                        <YAxis
                          tickFormatter={pct}
                          tickLine={false}
                          axisLine={false}
                          width={64}
                        />
                        <ReferenceLine
                          y={0}
                          stroke="#81929f"
                          strokeOpacity={0.6}
                        />
                        <ChartTooltip
                          content={
                            <ChartTooltipContent
                              formatter={(value, name) => (
                                <span className="flex w-full items-center justify-between gap-4">
                                  <span>
                                    {chartConfig[
                                      name as keyof typeof chartConfig
                                    ]?.label ?? String(name)}
                                  </span>
                                  <span className="font-mono">
                                    {typeof value === 'number'
                                      ? pct(value)
                                      : '—'}
                                  </span>
                                </span>
                              )}
                            />
                          }
                        />
                        <Line
                          type="linear"
                          dataKey="realized_loss"
                          stroke="var(--color-realized_loss)"
                          strokeWidth={1}
                          dot={false}
                          isAnimationActive={false}
                        />
                        <Line
                          type="linear"
                          dataKey="var_loss"
                          stroke="var(--color-var_loss)"
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                        <Line
                          dataKey="breach_loss"
                          stroke="none"
                          dot={{
                            fill: 'var(--color-breach_loss)',
                            stroke: 'var(--color-breach_loss)',
                            r: 3,
                          }}
                          activeDot={{ r: 5 }}
                          connectNulls={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ChartContainer>
                  )}
                  <p className="mt-3 text-xs leading-5 text-muted-foreground">
                    {c.sign}
                  </p>
                </section>
                <section aria-label={c.breachTable}>
                  <h3 className="mb-3 text-sm font-semibold">
                    {c.breachTable}
                  </h3>
                  {breachRows.length === 0 ? (
                    <p className="border border-border p-3 text-sm leading-6 text-muted-foreground">
                      {c.noBreaches}
                    </p>
                  ) : (
                    <>
                      <div className="overflow-x-auto border border-border">
                        <table className="w-full min-w-[560px] border-collapse text-sm">
                          <caption className="sr-only">{c.breachTable}</caption>
                          <thead className="bg-muted/20 text-xs text-muted-foreground">
                            <tr>
                              {[c.date, c.training, c.var, c.loss].map(
                                (label) => (
                                  <th
                                    key={label}
                                    scope="col"
                                    className="px-3 py-2 text-left font-medium"
                                  >
                                    {label}
                                  </th>
                                ),
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {displayedRows.map((point) => (
                              <tr
                                key={point.date}
                                className="border-t border-border font-mono text-xs"
                              >
                                <th
                                  scope="row"
                                  className="px-3 py-2 text-left font-normal"
                                >
                                  {point.date}
                                </th>
                                <td className="px-3 py-2 text-muted-foreground">
                                  {point.training_start} → {point.training_end}
                                </td>
                                <td className="px-3 py-2">
                                  {pct(point.var_loss)}
                                </td>
                                <td className="px-3 py-2 text-red-300">
                                  {pct(point.realized_loss)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {breachRows.length > 10 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="mt-2"
                          onClick={() => setExpanded(!expanded)}
                          aria-expanded={expanded}
                        >
                          {expanded ? c.showLess : c.showAll}
                        </Button>
                      )}
                    </>
                  )}
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    {c.tableNote}
                  </p>
                </section>
                <div>
                  <p className="mb-2 text-xs leading-5 text-muted-foreground">
                    {c.provenance}
                  </p>
                  <DataProvenance
                    quality={{ ...current.data_quality, warnings: notices }}
                  />
                </div>
                <details className="border-t border-border pt-3 text-sm">
                  <summary className="cursor-pointer font-medium text-primary focus-visible:outline-2 focus-visible:outline-primary">
                    {c.methodology}
                  </summary>
                  <p className="mt-3 leading-6 text-muted-foreground">
                    {c.methodNote}
                  </p>
                  <p className="mt-2 leading-6 text-muted-foreground">
                    {c.assumption}
                  </p>
                  <ul className="mt-3 list-disc space-y-2 pl-5 text-muted-foreground">
                    {c.limitations.map((limitation) => (
                      <li key={limitation}>{limitation}</li>
                    ))}
                  </ul>
                </details>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
