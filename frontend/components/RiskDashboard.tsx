'use client';

import { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  ChartSpline,
  Database,
  FlaskConical,
  Grid3X3,
  LineChart,
  History,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';

import { ConcentrationPanel } from '@/components/ConcentrationPanel';
import { CorrelationHeatmap } from '@/components/CorrelationHeatmap';
import { DrawdownChart } from '@/components/DrawdownChart';
import { FactorExposureChart } from '@/components/FactorExposureChart';
import { OptimizationPanel } from '@/components/OptimizationPanel';
import { BacktestPanel } from '@/components/BacktestPanel';
import { PortfolioEditor } from '@/components/PortfolioEditor';
import { RiskContributionChart } from '@/components/RiskContributionChart';
import { RiskFlags } from '@/components/RiskFlags';
import { RiskOfficer } from '@/components/RiskOfficer';
import { RiskOverview } from '@/components/RiskOverview';
import { StressTestPanel } from '@/components/StressTestPanel';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';
import { analyzePortfolio } from '@/lib/api';
import { DEMO_ANALYSIS, DEMO_PORTFOLIOS } from '@/lib/demo-data';
import type {
  DemoPortfolioName,
  PortfolioAnalysis,
  PositionInput,
} from '@/lib/types';

const navItems = [
  { label: 'Risk Overview', href: '#overview', icon: BarChart3, ready: true },
  {
    label: 'Risk Contribution',
    href: '#contribution',
    icon: ChartSpline,
    ready: true,
  },
  { label: 'Correlation', href: '#correlation', icon: Grid3X3, ready: true },
  { label: 'Drawdown', href: '#drawdown', icon: LineChart, ready: true },
  {
    label: 'Factor Exposure',
    href: '#factor-exposure',
    icon: Activity,
    ready: true,
  },
  {
    label: 'Stress Testing',
    href: '#stress-testing',
    icon: FlaskConical,
    ready: true,
  },
  {
    label: 'AI Risk Officer',
    href: '#risk-officer',
    icon: BrainCircuit,
    ready: true,
  },
  { label: 'Optimization', href: '#optimization', icon: SlidersHorizontal, ready: true },
  { label: 'Walk-Forward Test', href: '#backtest', icon: History, ready: true },
];

export function RiskDashboard() {
  const [positions, setPositions] = useState<PositionInput[]>(() =>
    DEMO_PORTFOLIOS['Mega-Cap Tech'].map((position) => ({ ...position })),
  );
  const [preset, setPreset] = useState<DemoPortfolioName>('Mega-Cap Tech');
  const [analysis, setAnalysis] = useState<PortfolioAnalysis>(DEMO_ANALYSIS);
  const [lookbackYears, setLookbackYears] = useState(3);
  const [riskFreeRate, setRiskFreeRate] = useState(0.04);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'snapshot' | 'live'>('snapshot');

  const totalWeight = useMemo(
    () => positions.reduce((sum, position) => sum + position.weight, 0),
    [positions],
  );

  function updatePositions(next: PositionInput[]) {
    setPositions(next);
    if (preset !== 'Custom') setPreset('Custom');
  }

  async function runAnalysis() {
    const normalizedTickers = positions.map((position) =>
      position.ticker.trim().toUpperCase(),
    );
    if (normalizedTickers.some((ticker) => !ticker)) {
      setError('Every position needs a ticker.');
      return;
    }
    if (new Set(normalizedTickers).size !== normalizedTickers.length) {
      setError('Each ticker may appear only once.');
      return;
    }
    if (Math.abs(totalWeight - 1) > 0.0001) {
      setError('Weights must sum to 100% before analysis.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const cleanPositions = positions.map((position, index) => ({
        ...position,
        ticker: normalizedTickers[index],
      }));
      const result = await analyzePortfolio({
        positions: cleanPositions,
        lookback_years: lookbackYears,
        risk_free_rate: riskFreeRate,
        confidence_level: 0.95,
      });
      setPositions(cleanPositions);
      setAnalysis(result);
      setMode('live');
      window.localStorage.setItem(
        'risklens-portfolio',
        JSON.stringify(cleanPositions),
      );
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'The analysis could not be completed.',
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/95 px-3 backdrop-blur md:px-5">
        <div className="flex items-center gap-3">
          <div className="grid size-8 place-items-center border border-primary/35 bg-primary/10 text-primary">
            <Activity className="size-4" />
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold tracking-[0.12em]">
                RISKLENS
              </span>
              <span className="hidden text-[9px] tracking-[0.13em] text-muted-foreground sm:inline">
                AI PORTFOLIO RISK TERMINAL
              </span>
            </div>
            <p className="text-[9px] text-muted-foreground">
              PORTFOLIO / MAIN / ANALYTICS
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 md:gap-4">
          <div className="hidden items-center gap-2 lg:flex">
            <span className="text-[9px] uppercase tracking-wider text-muted-foreground">
              Lookback
            </span>
            <NativeSelect
              size="sm"
              value={lookbackYears}
              onChange={(event) => setLookbackYears(Number(event.target.value))}
              aria-label="Lookback period"
            >
              <NativeSelectOption value="1">1 year</NativeSelectOption>
              <NativeSelectOption value="3">3 years</NativeSelectOption>
              <NativeSelectOption value="5">5 years</NativeSelectOption>
            </NativeSelect>
          </div>
          <div className="hidden items-center gap-2 md:flex">
            <span className="text-[9px] uppercase tracking-wider text-muted-foreground">
              Risk-free
            </span>
            <div className="relative w-16">
              <Input
                type="number"
                min="-10"
                max="50"
                step="0.1"
                value={Number((riskFreeRate * 100).toFixed(2))}
                onChange={(event) =>
                  setRiskFreeRate(Number(event.target.value) / 100)
                }
                className="h-7 rounded-sm pr-5 text-right font-mono text-xs"
                aria-label="Annual risk-free rate percent"
              />
              <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-[9px] text-muted-foreground">
                %
              </span>
            </div>
          </div>
          <Badge
            className={
              mode === 'live'
                ? 'rounded-sm border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                : 'rounded-sm border-amber-300/20 bg-amber-300/10 text-amber-200'
            }
          >
            <span
              className={`size-1.5 rounded-full ${mode === 'live' ? 'bg-emerald-400' : 'bg-amber-300'}`}
            />
            {mode === 'live' ? 'LIVE DATA' : 'DEMO SNAPSHOT'}
          </Badge>
        </div>
      </header>

      <div className="grid min-h-[calc(100vh-3.5rem)] grid-cols-1 xl:grid-cols-[264px_minmax(0,1fr)]">
        <aside className="border-b border-border bg-sidebar xl:sticky xl:top-14 xl:h-[calc(100vh-3.5rem)] xl:border-r xl:border-b-0">
          <div className="grid lg:grid-cols-[264px_1fr] xl:block xl:h-full">
            <div className="xl:h-[calc(100%-236px)]">
              <PortfolioEditor
                positions={positions}
                preset={preset}
                onPresetChange={setPreset}
                onChange={updatePositions}
                onAnalyze={runAnalysis}
                isLoading={isLoading}
              />
            </div>
            <nav
              className="hidden border-t border-border p-2 lg:block"
              aria-label="Risk sections"
            >
              <p className="section-label px-2 pb-2 pt-1">Terminal</p>
              <div className="grid grid-cols-2 gap-1 xl:grid-cols-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <a
                      key={item.label}
                      href={item.href}
                      aria-disabled={!item.ready}
                      className={`flex items-center gap-2 px-2 py-1.5 text-[10px] ${item.ready ? 'text-muted-foreground hover:bg-accent hover:text-foreground' : 'cursor-not-allowed text-muted-foreground/45'}`}
                      onClick={(event) =>
                        !item.ready &&
                        item.href === '#' &&
                        event.preventDefault()
                      }
                    >
                      <Icon className="size-3.5" />
                      <span>{item.label}</span>
                      {!item.ready && (
                        <span className="ml-auto font-mono text-[8px]">
                          LATER
                        </span>
                      )}
                    </a>
                  );
                })}
              </div>
            </nav>
          </div>
        </aside>

        <div className="min-w-0 p-3 md:p-4">
          {error && (
            <Alert variant="destructive" className="mb-3 rounded-sm">
              <AlertTriangle />
              <AlertTitle>Analysis unavailable</AlertTitle>
              <AlertDescription>
                {error} The deterministic demo snapshot remains visible.
              </AlertDescription>
            </Alert>
          )}
          <RiskOverview analysis={analysis} />
          <div className="mt-3 grid gap-3 2xl:grid-cols-2">
            <CorrelationHeatmap analysis={analysis} />
            <RiskContributionChart analysis={analysis} />
          </div>
          <div className="mt-3 grid gap-3 xl:grid-cols-[1.25fr_0.75fr]">
            <DrawdownChart analysis={analysis} />
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <ConcentrationPanel analysis={analysis} />
              <RiskFlags analysis={analysis} />
            </div>
          </div>
          <div className="mt-3">
            <FactorExposureChart analysis={analysis} />
          </div>
          <div className="mt-3">
            <StressTestPanel positions={positions} />
          </div>
          <div className="mt-3">
            <RiskOfficer analysis={analysis} />
          </div>
          <div className="mt-3">
            <OptimizationPanel positions={positions} lookbackYears={lookbackYears} riskFreeRate={riskFreeRate} />
          </div>
          <div className="mt-3">
            <BacktestPanel positions={positions} lookbackYears={lookbackYears} riskFreeRate={riskFreeRate} />
          </div>

          <footer className="mt-3 flex flex-col gap-2 border border-border bg-card px-3 py-2 text-[9px] text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <Database className="size-3 text-primary" />
              <span>{analysis.data_quality.source}</span>
              <span>·</span>
              <span>
                {analysis.data_quality.start_date} —{' '}
                {analysis.data_quality.end_date}
              </span>
              <span>·</span>
              <span>{analysis.data_quality.observations} observations</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Sparkles className="size-3" />
              <span>
                All displayed metrics are calculated deterministically.
              </span>
            </div>
          </footer>
          {analysis.data_quality.warnings.map((warning) => (
            <p key={warning} className="mt-2 text-[9px] text-amber-200/75">
              Data note: {warning}
            </p>
          ))}
        </div>
      </div>
    </main>
  );
}
