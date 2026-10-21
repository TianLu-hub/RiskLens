'use client';
import { LanguageSwitch, useLanguage } from '@/components/LanguageProvider';

import { useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Info,
  ChevronDown,
  ShieldCheck,
} from 'lucide-react';

import { ConcentrationPanel } from '@/components/ConcentrationPanel';
import { DataProvenance } from '@/components/DataProvenance';
import { provenanceCopy } from '@/lib/data-provenance';
import { CorrelationHeatmap } from '@/components/CorrelationHeatmap';
import { DrawdownChart } from '@/components/DrawdownChart';
import { FactorExposureChart } from '@/components/FactorExposureChart';
import { OptimizationPanel } from '@/components/OptimizationPanel';
import { BacktestPanel } from '@/components/BacktestPanel';
import { VarBacktestPanel } from '@/components/VarBacktestPanel';
import { PortfolioEditor } from '@/components/PortfolioEditor';
import { RiskContributionChart } from '@/components/RiskContributionChart';
import { RiskFlags } from '@/components/RiskFlags';
import { RiskOfficer } from '@/components/RiskOfficer';
import { RiskOverview, PortfolioPerformance } from '@/components/RiskOverview';
import { StressTestPanel } from '@/components/StressTestPanel';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { WorkspaceNav, workspaceViews } from '@/components/WorkspaceNav';
import {
  getCurrentSection,
  getServerSection,
  subscribeToSection,
  navigateToSection,
} from '@/lib/workspace-navigation';
import { Input } from '@/components/ui/input';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';
import { analyzePortfolio } from '@/lib/api';
import {
  analysisInputKey,
  parseSavedPortfolio,
  PORTFOLIO_STORAGE_KEY,
  savePortfolio,
} from '@/lib/portfolio-state';
import { DEMO_ANALYSIS, DEMO_PORTFOLIOS } from '@/lib/demo-data';
import type {
  DemoPortfolioName,
  PortfolioAnalysis,
  PositionInput,
} from '@/lib/types';

export function RiskDashboard() {
  const { t, locale } = useLanguage();
  const dataCopy = provenanceCopy[locale];
  const activeSection = useSyncExternalStore(
    subscribeToSection,
    getCurrentSection,
    getServerSection,
  );
  const view = workspaceViews.find((item) => item.id === activeSection)!;
  const [portfolioOpen, setPortfolioOpen] = useState(false);
  const [analysisRevision, setAnalysisRevision] = useState(0);
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
  const [analyzedInputKey, setAnalyzedInputKey] = useState(() =>
    analysisInputKey({
      positions: DEMO_PORTFOLIOS['Mega-Cap Tech'],
      lookbackYears: 3,
      riskFreeRate: 0.04,
    }),
  );
  const [storageReady, setStorageReady] = useState(false);
  const [storageNotice, setStorageNotice] = useState<string | null>(null);
  const [storageUnavailable, setStorageUnavailable] = useState(false);
  const inputsDirty =
    analysisInputKey({ positions, lookbackYears, riskFreeRate }) !==
    analyzedInputKey;

  // Browser storage is an external system unavailable during server rendering.
  // Hydrate once after mount; gate writes so defaults cannot overwrite saved inputs.
  /* eslint-disable react/react-compiler */
  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(PORTFOLIO_STORAGE_KEY);
      if (raw) {
        const saved = parseSavedPortfolio(raw);
        if (saved) {
          setPositions(saved.positions);
          setLookbackYears(saved.lookbackYears);
          setRiskFreeRate(saved.riskFreeRate);
          setPreset('Custom');
          setStorageNotice(
            'Saved portfolio restored on this device. Analyze it to load historical results.',
          );
        } else {
          setStorageNotice(
            'Saved portfolio could not be restored. The default portfolio is shown.',
          );
        }
      }
    } catch {
      setStorageUnavailable(true);
    }
    setStorageReady(true);
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    try {
      setStorageUnavailable(
        !savePortfolio(window.localStorage, {
          positions,
          lookbackYears,
          riskFreeRate,
        }),
      );
    } catch {
      setStorageUnavailable(true);
    }
  }, [positions, lookbackYears, riskFreeRate, storageReady]);
  /* eslint-enable react/react-compiler */

  const totalWeight = useMemo(
    () => positions.reduce((sum, position) => sum + position.weight, 0),
    [positions],
  );

  function updatePositions(next: PositionInput[]) {
    setPositions(next);
    setStorageNotice(null);
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
      setAnalysisRevision((revision) => revision + 1);
      setMode('live');
      setAnalyzedInputKey(
        analysisInputKey({
          positions: cleanPositions,
          lookbackYears,
          riskFreeRate,
        }),
      );
      setStorageNotice(null);
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
    <main className="risk-workspace min-h-screen bg-background text-foreground">
      <a
        href="#workspace-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById('workspace-content')?.focus();
        }}
        className="sr-only z-50 bg-primary p-3 text-primary-foreground focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        {t('Skip to analysis')}
      </a>
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-border bg-background px-4 lg:px-5">
        <div className="flex items-center gap-3">
          <Activity className="size-7 text-primary" aria-hidden="true" />
          <span className="text-xl font-semibold tracking-tight">RiskLens</span>
          <span className="hidden border-l border-border pl-3 text-xs text-muted-foreground sm:block">
            {t('PORTFOLIO RISK TERMINAL')}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <LanguageSwitch />
          <span className="hidden items-center gap-1.5 text-xs text-muted-foreground md:flex">
            <ShieldCheck className="size-3.5 text-emerald-300" />
            {t('Python-computed metrics')}
          </span>
          <Badge
            className={
              mode === 'live'
                ? 'rounded border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                : 'rounded border-amber-300/20 bg-amber-300/10 text-amber-200'
            }
          >
            <span
              className={`size-1.5 rounded-full ${mode === 'live' ? 'bg-emerald-400' : 'bg-amber-300'}`}
            />
            {activeSection === 'var-backtest'
              ? t('MODEL VALIDATION')
              : activeSection === 'stress-testing'
                ? dataCopy.stressBadge
                : activeSection === 'optimization' ||
                    activeSection === 'backtest'
                  ? dataCopy.simulationBadge
                  : mode === 'live'
                    ? t('HISTORICAL DATA')
                    : t('DEMO SNAPSHOT')}
          </Badge>
        </div>
      </header>

      <div className="grid min-h-[calc(100dvh-4rem)] lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside
          aria-label={t('Portfolio workspace')}
          className="min-w-0 border-b border-border bg-sidebar lg:sticky lg:top-16 lg:h-[calc(100dvh-4rem)] lg:overflow-y-auto lg:border-r lg:border-b-0"
        >
          <WorkspaceNav active={activeSection} />
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3 text-sm lg:hidden"
            aria-expanded={portfolioOpen}
            aria-controls="portfolio-controls"
            onClick={() => setPortfolioOpen(!portfolioOpen)}
          >
            <span>
              {t('Portfolio ·')} {positions.length} {t('positions')}
            </span>
            <ChevronDown
              className={`size-4 transition-transform ${portfolioOpen ? 'rotate-180' : ''}`}
            />
          </button>
          <div
            id="portfolio-controls"
            className={portfolioOpen ? 'block' : 'hidden lg:block'}
          >
            <div className="grid grid-cols-2 gap-3 border-b border-border px-4 py-3">
              <div>
                <label
                  htmlFor="analysis-lookback"
                  className="text-xs text-muted-foreground"
                >
                  {t('Lookback')}
                </label>
                <NativeSelect
                  id="analysis-lookback"
                  className="mt-1 w-full"
                  size="sm"
                  value={lookbackYears}
                  disabled={isLoading}
                  onChange={(event) => {
                    setLookbackYears(Number(event.target.value));
                    setStorageNotice(null);
                  }}
                >
                  <NativeSelectOption value="1">
                    {t('1 year')}
                  </NativeSelectOption>
                  <NativeSelectOption value="3">
                    {t('3 years')}
                  </NativeSelectOption>
                  <NativeSelectOption value="5">
                    {t('5 years')}
                  </NativeSelectOption>
                </NativeSelect>
              </div>
              <div>
                <label
                  htmlFor="analysis-risk-free"
                  className="text-xs text-muted-foreground"
                >
                  {t('Risk-free rate')}
                </label>
                <div className="relative mt-1">
                  <Input
                    id="analysis-risk-free"
                    type="number"
                    min="-10"
                    max="50"
                    step="0.1"
                    value={Number((riskFreeRate * 100).toFixed(2))}
                    disabled={isLoading}
                    onChange={(event) => {
                      setRiskFreeRate(Number(event.target.value) / 100);
                      setStorageNotice(null);
                    }}
                    className="h-8 rounded pr-6 font-mono text-sm"
                  />
                  <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                    %
                  </span>
                </div>
              </div>
            </div>
            <PortfolioEditor
              positions={positions}
              preset={preset}
              onPresetChange={setPreset}
              onChange={updatePositions}
              onAnalyze={runAnalysis}
              isLoading={isLoading}
            />
            <p className="px-4 py-3 text-xs leading-5 text-muted-foreground">
              {t('Holdings stay in this browser.')}
              <br />
              {t('Analyze to update historical results.')}
            </p>
          </div>
        </aside>

        <div
          id="workspace-content"
          className="min-w-0 p-4 lg:p-5"
          tabIndex={-1}
        >
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-widest text-primary">
                {t('Main portfolio / Research workspace')}
              </p>
              <h1 className="text-2xl font-semibold tracking-tight">
                {t(view.title)}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {t(view.description)}
              </p>
            </div>
          </div>
          {(storageNotice || storageUnavailable) && (
            <output className="mb-3 block text-xs leading-5 text-muted-foreground">
              {storageUnavailable
                ? t(
                    'Portfolio could not be saved on this device. You can still run analyses.',
                  )
                : storageNotice && t(storageNotice)}
            </output>
          )}
          {mode === 'snapshot' &&
            (activeSection === 'overview' ||
              activeSection === 'factor-exposure' ||
              activeSection === 'risk-officer') && (
              <div className="mb-3 flex items-start gap-2 border border-amber-300/25 bg-amber-300/5 px-3 py-2.5 text-xs leading-5 text-amber-100">
                <Info
                  className="mt-0.5 size-4 shrink-0 text-amber-300"
                  aria-hidden="true"
                />
                <p>
                  <span className="font-semibold">{t('Demo data.')}</span>{' '}
                  {t(
                    'The charts below use a fixed synthetic example. Select a portfolio and click Analyze portfolio to load historical prices.',
                  )}
                </p>
              </div>
            )}
          {inputsDirty && activeSection !== 'var-backtest' && (
            <output className="mb-3 flex items-start gap-2 border border-primary/30 bg-primary/5 px-3 py-2.5 text-xs leading-5 text-foreground">
              <Info
                className="mt-0.5 size-4 shrink-0 text-primary"
                aria-hidden="true"
              />
              <p>
                <span className="font-semibold">
                  {t('Inputs changed — analysis needs updating.')}
                </span>{' '}
                {t('The risk charts still show')}{' '}
                {mode === 'snapshot'
                  ? t('the demo portfolio')
                  : t('the last analyzed portfolio')}
                {t(
                  '. Click Analyze portfolio to refresh them. Stress testing, optimization, and backtesting use your current inputs.',
                )}
              </p>
            </output>
          )}
          {error && activeSection !== 'var-backtest' && (
            <Alert variant="destructive" className="mb-3 rounded-sm">
              <AlertTriangle />
              <AlertTitle>{t('Analysis unavailable')}</AlertTitle>
              <AlertDescription>
                {t(error)}{' '}
                {mode === 'snapshot'
                  ? t('The labeled demo snapshot remains visible.')
                  : t('The previous historical analysis remains visible.')}
              </AlertDescription>
            </Alert>
          )}

          <div hidden={activeSection !== 'overview'}>
            <DataProvenance
              quality={analysis.data_quality}
              demo={mode === 'snapshot'}
            />
            <RiskOverview analysis={analysis} />
            <div className="mt-4 grid items-start gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(310px,1fr)]">
              <div className="grid min-w-0 gap-4">
                {activeSection === 'overview' && (
                  <PortfolioPerformance analysis={analysis} />
                )}
                {activeSection === 'overview' && (
                  <DrawdownChart analysis={analysis} />
                )}
              </div>
              <div className="grid min-w-0 gap-4">
                <RiskContributionChart analysis={analysis} />
                <RiskFlags analysis={analysis} />
                <button
                  type="button"
                  className="flex items-center gap-3 rounded-md border border-primary/25 bg-primary/5 p-4 text-left hover:bg-primary/10 focus-visible:outline-2 focus-visible:outline-primary"
                  onClick={() => navigateToSection('risk-officer')}
                >
                  <BrainCircuit className="size-5 shrink-0 text-primary" />
                  <span>
                    <span className="block text-sm font-semibold">
                      {t('Explore with Risk Officer')}
                    </span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {t('Understand the risks behind these numbers →')}
                    </span>
                  </span>
                </button>
              </div>
            </div>
            <div className="mt-4 grid items-start gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(310px,1fr)]">
              <CorrelationHeatmap analysis={analysis} />
              <ConcentrationPanel analysis={analysis} />
            </div>
          </div>
          <div hidden={activeSection !== 'factor-exposure'}>
            <DataProvenance
              quality={analysis.data_quality}
              demo={mode === 'snapshot'}
            />
            {activeSection === 'factor-exposure' && (
              <FactorExposureChart analysis={analysis} />
            )}
          </div>
          <div hidden={activeSection !== 'stress-testing'}>
            <p className="mb-3 border border-amber-300/20 bg-amber-300/5 p-3 text-sm text-amber-200">
              {dataCopy.stress}
            </p>
            <StressTestPanel positions={positions} />
          </div>
          <div hidden={activeSection !== 'risk-officer'}>
            <DataProvenance
              quality={analysis.data_quality}
              demo={mode === 'snapshot'}
            />
            {inputsDirty ? (
              <output
                id="risk-officer"
                className="block rounded-md border border-primary/30 bg-card p-5 text-sm"
              >
                <p className="font-semibold">
                  {t('Risk Officer needs an updated analysis')}
                </p>
                <p className="mt-2 text-muted-foreground">
                  {t(
                    'Analyze the current portfolio before asking about its risks.',
                  )}
                </p>
              </output>
            ) : (
              <RiskOfficer key={analysisRevision + mode} analysis={analysis} />
            )}
          </div>
          <div hidden={activeSection !== 'optimization'}>
            <OptimizationPanel
              positions={positions}
              lookbackYears={lookbackYears}
              riskFreeRate={riskFreeRate}
            />
          </div>
          <div hidden={activeSection !== 'backtest'}>
            <BacktestPanel
              positions={positions}
              lookbackYears={lookbackYears}
              riskFreeRate={riskFreeRate}
            />
          </div>
          <div hidden={activeSection !== 'var-backtest'}>
            <VarBacktestPanel
              positions={positions}
              lookbackYears={lookbackYears}
              active={activeSection === 'var-backtest'}
            />
          </div>
          <footer className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-border py-3 text-xs text-muted-foreground">
            <span>{t('Historical analysis · Hypothetical scenarios')}</span>
          </footer>
          {locale === 'zh' && (
            <p className="text-xs leading-5 text-muted-foreground">
              金额单位为美元。部分后端自由文本保留英文原文；语言切换不改变数据、计算结果或模型假设。
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
