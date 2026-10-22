'use client';
import { useLanguage } from '@/components/LanguageProvider';

import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CircleDollarSign,
  FlaskConical,
  Info,
  Play,
  ShieldAlert,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { runStressTest } from '@/lib/api';
import {
  overrideDrafts,
  tickerShockInputs,
  toggleOverride,
  type TickerOverrideDrafts,
} from '@/lib/stress-overrides';
import {
  DEMO_STRESS_RESULT,
  STRESS_PRESETS,
  type StressPreset,
} from '@/lib/stress-data';
import type { PositionInput, StressTestResult } from '@/lib/types';

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

function formatPercent(value: number, digits = 2) {
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(digits)}%`;
}

function formatMoney(value: number | null) {
  if (value === null) return 'Not provided';
  return `${value >= 0 ? '+' : '-'}${currency.format(Math.abs(value))}`;
}

function metricTone(value: number | null) {
  if (value === null || value === 0) return 'text-foreground';
  return value < 0 ? 'text-rose-300' : 'text-emerald-300';
}

export function StressTestPanel({ positions }: { positions: PositionInput[] }) {
  const { t } = useLanguage();
  const defaultPreset = STRESS_PRESETS.find(
    (preset) => preset.id === 'custom',
  )!;
  const [activePreset, setActivePreset] =
    useState<StressPreset['id']>('custom');
  const [scenarioName, setScenarioName] = useState(defaultPreset.name);
  const [marketPct, setMarketPct] = useState(defaultPreset.marketPct);
  const [techPct, setTechPct] = useState(defaultPreset.techPct);
  const [ratesBps, setRatesBps] = useState(defaultPreset.ratesBps);
  const [tickerShocksPct, setTickerShocksPct] = useState<TickerOverrideDrafts>(
    () => overrideDrafts(defaultPreset.tickerShocksPct),
  );
  const [portfolioValue, setPortfolioValue] = useState(100_000);
  const [result, setResult] = useState<StressTestResult>(DEMO_STRESS_RESULT);
  const [resultMode, setResultMode] = useState<'demo' | 'computed'>('demo');
  const [inputsChanged, setInputsChanged] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cleanPositions = useMemo(
    () =>
      positions.map((position) => ({
        ...position,
        ticker: position.ticker.trim().toUpperCase(),
      })),
    [positions],
  );
  const maxFactorContribution = Math.max(
    ...result.factor_contributions.map((factor) =>
      Math.abs(factor.portfolio_contribution),
    ),
    0.0001,
  );

  function markChanged() {
    setInputsChanged(true);
    setActivePreset('custom');
  }

  function applyPreset(preset: StressPreset) {
    setActivePreset(preset.id);
    setScenarioName(preset.name);
    setMarketPct(preset.marketPct);
    setTechPct(preset.techPct);
    setRatesBps(preset.ratesBps);
    setTickerShocksPct(overrideDrafts(preset.tickerShocksPct));
    setInputsChanged(true);
    setError(null);
  }

  function updateTickerShock(ticker: string, value: string) {
    setTickerShocksPct((current) => ({ ...current, [ticker]: value }));
    markChanged();
  }

  async function submitScenario() {
    const tickers = cleanPositions.map((position) => position.ticker);
    if (tickers.some((ticker) => !ticker)) {
      setError(
        'Every portfolio position needs a ticker before stress testing.',
      );
      return;
    }

    let tickerShocks: Record<string, number>;
    try {
      tickerShocks = tickerShockInputs(tickers, tickerShocksPct);
    } catch (reason) {
      setError((reason as Error).message);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const nextResult = await runStressTest({
        positions: cleanPositions,
        portfolio_value: portfolioValue,
        scenario_name: scenarioName,
        market_shock: marketPct / 100,
        tech_shock: techPct / 100,
        rates_shock_bps: ratesBps,
        ticker_shocks: tickerShocks,
      });
      setResult(nextResult);
      setResultMode('computed');
      setInputsChanged(false);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'The stress test could not be completed.',
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card id="stress-testing" className="rounded-sm bg-card ring-border">
      <CardHeader className="flex-row items-center justify-between border-b border-border py-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="section-label">{t('Stress testing')}</p>
            <Badge className="rounded-sm border-amber-300/25 bg-amber-300/10 text-[11px] text-amber-200">
              {t('HYPOTHETICAL · NOT A PREDICTION')}
            </Badge>
          </div>
          <p className="mt-1 text-[12px] text-muted-foreground">
            {t(
              'Deterministic, linear portfolio shock analysis with disclosed assumptions',
            )}
          </p>
        </div>
        <FlaskConical className="size-4 text-primary" />
      </CardHeader>

      <CardContent className="p-0">
        <div className="grid xl:grid-cols-[330px_minmax(0,1fr)]">
          <section
            className="border-b border-border p-4 xl:border-r xl:border-b-0"
            aria-label={t('Stress scenario controls')}
          >
            <div className="flex items-center justify-between">
              <p className="section-label">{t('Scenario inputs')}</p>
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
                {t('User-defined')}
              </span>
            </div>
            <p className="mt-2 border-l-2 border-amber-300/50 pl-2 text-[11px] leading-relaxed text-muted-foreground">
              {t(
                'Presets are simplified hypothetical stress scenarios. Their names are labels, not exact historical reproductions.',
              )}
            </p>

            <div className="mt-3 grid grid-cols-2 gap-1.5">
              {STRESS_PRESETS.map((preset) => (
                <Button
                  key={preset.id}
                  type="button"
                  variant={activePreset === preset.id ? 'secondary' : 'outline'}
                  size="sm"
                  className={`h-auto min-h-8 justify-start rounded-sm px-2 py-1.5 text-left text-[11px] ${preset.id === 'custom' ? 'col-span-2' : ''}`}
                  onClick={() => applyPreset(preset)}
                >
                  {t(preset.name)}
                </Button>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <label
                htmlFor="stress-market"
                className="text-[11px] uppercase tracking-wider text-muted-foreground"
              >
                {t('Market shock')}
                <div className="relative mt-1">
                  <Input
                    id="stress-market"
                    type="number"
                    min="-100"
                    max="100"
                    step="1"
                    value={marketPct}
                    onChange={(event) => {
                      setMarketPct(Number(event.target.value));
                      markChanged();
                    }}
                    className="h-8 rounded-sm pr-6 text-right font-mono text-xs"
                  />
                  <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[11px]">
                    %
                  </span>
                </div>
              </label>
              <label
                htmlFor="stress-tech"
                className="text-[11px] uppercase tracking-wider text-muted-foreground"
              >
                {t('Tech shock')}
                <div className="relative mt-1">
                  <Input
                    id="stress-tech"
                    type="number"
                    min="-100"
                    max="100"
                    step="1"
                    value={techPct}
                    onChange={(event) => {
                      setTechPct(Number(event.target.value));
                      markChanged();
                    }}
                    className="h-8 rounded-sm pr-6 text-right font-mono text-xs"
                  />
                  <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[11px]">
                    %
                  </span>
                </div>
              </label>
              <label
                htmlFor="stress-rates"
                className="text-[11px] uppercase tracking-wider text-muted-foreground"
              >
                {t('Rate shock')}
                <div className="relative mt-1">
                  <Input
                    id="stress-rates"
                    type="number"
                    min="-1000"
                    max="1000"
                    step="25"
                    value={ratesBps}
                    onChange={(event) => {
                      setRatesBps(Number(event.target.value));
                      markChanged();
                    }}
                    className="h-8 rounded-sm pr-8 text-right font-mono text-xs"
                  />
                  <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[11px]">
                    {t('bps')}
                  </span>
                </div>
              </label>
              <label
                htmlFor="stress-value"
                className="text-[11px] uppercase tracking-wider text-muted-foreground"
              >
                {t('Portfolio value')}
                <div className="relative mt-1">
                  <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[11px]">
                    $
                  </span>
                  <Input
                    id="stress-value"
                    type="number"
                    min="1"
                    max="1000000000000"
                    step="1000"
                    value={portfolioValue}
                    onChange={(event) => {
                      setPortfolioValue(Number(event.target.value));
                      markChanged();
                    }}
                    className="h-8 rounded-sm pl-5 text-right font-mono text-xs"
                  />
                </div>
              </label>
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {t('Ticker-specific total shock')}
                </p>
                <span className="text-[11px] text-muted-foreground">
                  {t('Overrides factor total')}
                </span>
              </div>
              <p
                id="stress-ticker-help"
                className="mt-2 text-xs leading-relaxed text-muted-foreground"
              >
                {t(
                  'Check a ticker to replace its total shock. Unchecked uses factor shocks; enabled 0% keeps that asset unchanged.',
                )}
              </p>
              <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-3 xl:grid-cols-2">
                {cleanPositions.map((position) => {
                  const enabled = Object.hasOwn(
                    tickerShocksPct,
                    position.ticker,
                  );
                  return (
                    <div
                      key={position.ticker}
                      className="border border-border bg-background px-2 py-2"
                    >
                      <label className="flex cursor-pointer items-center gap-2 font-mono text-[12px] text-foreground">
                        <input
                          type="checkbox"
                          checked={enabled}
                          disabled={isLoading || !position.ticker}
                          onChange={(event) => {
                            setTickerShocksPct((current) =>
                              toggleOverride(
                                current,
                                position.ticker,
                                event.target.checked,
                              ),
                            );
                            markChanged();
                          }}
                          aria-label={t('Override {ticker} total shock', {
                            ticker: position.ticker,
                          })}
                          aria-describedby="stress-ticker-help"
                          className="size-4 shrink-0 accent-sky-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
                        />
                        <span className="truncate">
                          {position.ticker || '—'}
                        </span>
                      </label>
                      <div className="mt-2 flex items-center gap-1">
                        <Input
                          type="number"
                          min="-100"
                          max="100"
                          step="1"
                          disabled={!enabled || isLoading}
                          value={
                            enabled ? tickerShocksPct[position.ticker] : ''
                          }
                          placeholder="—"
                          onChange={(event) =>
                            updateTickerShock(
                              position.ticker,
                              event.target.value,
                            )
                          }
                          aria-label={t('{ticker} stress percent', {
                            ticker: position.ticker,
                          })}
                          aria-describedby="stress-ticker-help"
                          className="h-7 min-w-0 flex-1 rounded-sm px-2 text-right font-mono text-[12px]"
                        />
                        <span className="ml-1 text-[11px] text-muted-foreground">
                          %
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        {enabled
                          ? t('Total shock override')
                          : t('Uses factor shocks')}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            <Button
              type="button"
              onClick={submitScenario}
              disabled={isLoading}
              className="mt-4 h-9 w-full rounded-sm text-[12px] font-semibold uppercase tracking-wider"
            >
              <Play className="size-3" />
              {isLoading
                ? t('Running deterministic engine…')
                : t('Run stress test')}
            </Button>
            {inputsChanged && (
              <p className="mt-2 text-center text-[11px] uppercase tracking-wider text-amber-200">
                {t('Inputs changed · run to refresh results')}
              </p>
            )}
          </section>

          <section
            className="min-w-0 p-4"
            aria-label={t('Stress test results')}
          >
            {error && (
              <Alert variant="destructive" className="mb-3 rounded-sm">
                <AlertTriangle />
                <AlertTitle>{t('Stress test unavailable')}</AlertTitle>
                <AlertDescription>
                  {t(error)}{' '}
                  {t('The last deterministic result remains visible.')}
                </AlertDescription>
              </Alert>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="section-label">{t(result.scenario_name)}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {t('Historical data used:')}{' '}
                  <span className="font-semibold text-foreground">
                    {t('No')}
                  </span>{' '}
                  {t('· Classification: hypothetical')}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                {inputsChanged && (
                  <Badge className="rounded-sm border-amber-300/25 bg-amber-300/10 text-[11px] text-amber-200">
                    {t('STALE RESULT')}
                  </Badge>
                )}
                <Badge variant="outline" className="rounded-sm text-[11px]">
                  {resultMode === 'computed'
                    ? t('API RESULT')
                    : t('DEMO SNAPSHOT')}
                </Badge>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-px bg-border lg:grid-cols-4">
              <div className="bg-background p-3">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {t('Estimated return')}
                </p>
                <p
                  className={`mt-2 font-mono text-lg ${metricTone(result.estimated_portfolio_return)}`}
                >
                  {formatPercent(result.estimated_portfolio_return)}
                </p>
              </div>
              <div className="bg-background p-3">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {t('Estimated P&L')}
                </p>
                <p
                  className={`mt-2 font-mono text-lg ${metricTone(result.estimated_dollar_pnl)}`}
                >
                  {formatMoney(result.estimated_dollar_pnl)}
                </p>
              </div>
              <div className="bg-background p-3">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {t('Portfolio before')}
                </p>
                <p className="mt-2 font-mono text-lg">
                  {result.portfolio_value_before === null
                    ? '—'
                    : currency.format(result.portfolio_value_before)}
                </p>
              </div>
              <div className="bg-background p-3">
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {t('Portfolio after')}
                </p>
                <p className="mt-2 flex items-center gap-2 font-mono text-lg">
                  <ArrowRight className="size-3 text-muted-foreground" />
                  {result.portfolio_value_after === null
                    ? '—'
                    : currency.format(result.portfolio_value_after)}
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-4 2xl:grid-cols-[1.15fr_0.85fr]">
              <div className="min-w-0">
                <div className="mb-2 flex items-center justify-between">
                  <p className="section-label">{t('Asset P&L attribution')}</p>
                  <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
                    {t('Weight × shocked return')}
                  </span>
                </div>
                <div className="overflow-x-auto border border-border">
                  <table className="w-full min-w-[540px] border-collapse text-[11px]">
                    <thead className="bg-muted/40 text-left uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="px-2 py-2">{t('Asset')}</th>
                        <th className="px-2 py-2 text-right">{t('Weight')}</th>
                        <th className="px-2 py-2 text-right">
                          {t('Asset shock')}
                        </th>
                        <th className="px-2 py-2 text-right">
                          {t('Portfolio contrib.')}
                        </th>
                        <th className="px-2 py-2 text-right">{t('P&L')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.asset_contributions.map((asset) => (
                        <tr
                          key={asset.ticker}
                          className="border-t border-border font-mono"
                        >
                          <td className="px-2 py-2 font-semibold text-foreground">
                            {asset.ticker}
                          </td>
                          <td className="px-2 py-2 text-right">
                            {(asset.weight * 100).toFixed(1)}%
                          </td>
                          <td
                            className={`px-2 py-2 text-right ${metricTone(asset.estimated_asset_return)}`}
                          >
                            {formatPercent(asset.estimated_asset_return)}
                          </td>
                          <td
                            className={`px-2 py-2 text-right ${metricTone(asset.portfolio_contribution)}`}
                          >
                            {formatPercent(asset.portfolio_contribution)}
                          </td>
                          <td
                            className={`px-2 py-2 text-right ${metricTone(asset.estimated_dollar_pnl)}`}
                          >
                            {formatMoney(asset.estimated_dollar_pnl)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="section-label">
                    {t('Risk-factor attribution')}
                  </p>
                  <CircleDollarSign className="size-3.5 text-primary" />
                </div>
                <div className="space-y-3 border border-border p-3">
                  {result.factor_contributions.map((factor) => (
                    <div key={factor.factor}>
                      <div className="flex items-center justify-between gap-3 text-[11px]">
                        <span className="truncate text-muted-foreground">
                          {t(factor.label)}
                        </span>
                        <span
                          className={`shrink-0 font-mono ${metricTone(factor.portfolio_contribution)}`}
                        >
                          {formatPercent(factor.portfolio_contribution)} ·{' '}
                          {formatMoney(factor.estimated_dollar_pnl)}
                        </span>
                      </div>
                      <div className="mt-1.5 h-1.5 bg-muted">
                        <div
                          className={
                            factor.portfolio_contribution < 0
                              ? 'h-full bg-rose-400/75'
                              : 'h-full bg-emerald-400/75'
                          }
                          style={{
                            width: `${Math.max(2, (Math.abs(factor.portfolio_contribution) / maxFactorContribution) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-4 border border-border">
              <div className="flex items-center justify-between border-b border-border bg-muted/25 px-3 py-2">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="size-3.5 text-amber-200" />
                  <p className="section-label">
                    {t('Assumptions & provenance')}
                  </p>
                </div>
                <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  {t('No live factor data')}
                </span>
              </div>
              <div className="grid gap-px bg-border md:grid-cols-2">
                {result.assumptions.map((assumption) => (
                  <div key={assumption.id} className="bg-card p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="text-[11px] font-semibold text-foreground">
                          {t(assumption.label)}
                        </p>
                        <p className="mt-1 font-mono text-[12px] text-primary">
                          {t(assumption.value)}
                        </p>
                      </div>
                      <Badge
                        className={
                          assumption.source_type ===
                          'fallback_modeling_assumption'
                            ? 'rounded-sm border-amber-300/25 bg-amber-300/10 text-[11px] text-amber-200'
                            : 'rounded-sm border-border bg-muted text-[11px] text-muted-foreground'
                        }
                      >
                        {assumption.source_type ===
                        'fallback_modeling_assumption'
                          ? t('FALLBACK MODELING ASSUMPTION')
                          : t('MODEL METHODOLOGY')}
                      </Badge>
                    </div>
                    <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                      {t(assumption.description)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-3 flex items-start gap-2 border border-primary/20 bg-primary/5 px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
              <Info className="mt-0.5 size-3 shrink-0 text-primary" />
              <span>{t(result.disclaimer)}</span>
            </div>
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
