'use client';

import { useState } from 'react';
import {
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  FlaskConical,
  LockKeyhole,
  Send,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { askRiskOfficer } from '@/lib/api';
import type { PortfolioAnalysis, RiskOfficerResult } from '@/lib/types';

const SUGGESTED_QUESTIONS = [
  'Diagnose the dominant risks in this portfolio.',
  'What happens if tech drops 15% and rates rise 100 bps?',
  'Explain the portfolio tail risk and diversification quality.',
];

function percent(value: number) {
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
}

function money(value: number | null) {
  if (value === null) return 'Unavailable';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

function evidenceTone(source: string) {
  if (source === 'hypothetical_scenario_result') {
    return 'border-amber-300/25 bg-amber-300/10 text-amber-200';
  }
  if (source === 'model_assumption') {
    return 'border-sky-300/25 bg-sky-300/10 text-sky-200';
  }
  return 'border-emerald-300/25 bg-emerald-300/10 text-emerald-200';
}

type RiskOfficerProps = {
  analysis: PortfolioAnalysis;
};

export function RiskOfficer({ analysis }: RiskOfficerProps) {
  const [question, setQuestion] = useState('');
  const [portfolioValue, setPortfolioValue] = useState(100_000);
  const [result, setResult] = useState<RiskOfficerResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitQuestion() {
    const cleanQuestion = question.trim();
    if (cleanQuestion.length < 2) {
      setError(
        'Enter a portfolio risk question or a hypothetical stress scenario.',
      );
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await askRiskOfficer({
        question: cleanQuestion,
        positions: analysis.risk_contributions.map((position) => ({
          ticker: position.ticker,
          weight: position.weight,
        })),
        portfolio_value: portfolioValue,
        analysis: {
          metrics: analysis.metrics,
          drawdown: {
            current_drawdown: analysis.drawdown.current_drawdown,
            max_drawdown: analysis.drawdown.max_drawdown,
          },
          correlation: {
            highest_correlations: analysis.correlation.highest_correlations,
          },
          risk_contributions: analysis.risk_contributions,
          concentration: analysis.concentration,
          factor_exposure: analysis.factor_exposure,
          risk_flags: analysis.risk_flags,
          data_quality: analysis.data_quality,
        },
      });
      setResult(response);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'The Risk Officer could not respond.',
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card
      id="risk-officer"
      className="rounded-sm border-l-2 border-l-primary bg-card ring-border"
    >
      <CardHeader className="flex-row items-start justify-between border-b border-border px-4 py-3">
        <div className="flex items-start gap-3">
          <div className="grid size-8 shrink-0 place-items-center bg-primary/10 text-primary">
            <BrainCircuit className="size-4" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="section-label">AI Risk Officer</p>
              <Badge className="rounded-sm border-emerald-300/25 bg-emerald-300/10 text-[8px] text-emerald-200">
                PHASE 3 · ZERO-COST
              </Badge>
            </div>
            <p className="mt-1 text-[10px] text-muted-foreground">
              Deterministic interpretation and evidence-grounded explanation
              over Python results
            </p>
          </div>
        </div>
        <ShieldCheck className="size-4 text-emerald-300" />
      </CardHeader>

      <CardContent className="p-0">
        <div className="grid xl:grid-cols-[390px_minmax(0,1fr)]">
          <section
            className="border-b border-border p-4 xl:border-r xl:border-b-0"
            aria-label="Ask the AI Risk Officer"
          >
            <div className="flex items-center justify-between">
              <p className="section-label">Officer briefing</p>
              <span className="flex items-center gap-1 text-[8px] uppercase tracking-wider text-muted-foreground">
                <LockKeyhole className="size-3" /> No raw prices
              </span>
            </div>
            <Textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === 'Enter')
                  void submitQuestion();
              }}
              className="mt-3 min-h-24 rounded-sm text-xs leading-5"
              placeholder="Ask for a risk diagnosis, or try: What happens if tech drops 15% and rates rise 100 bps?"
              aria-label="Question for the AI Risk Officer"
            />

            <div className="mt-2 flex flex-wrap gap-1.5">
              {SUGGESTED_QUESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setQuestion(suggestion)}
                  className="border border-border bg-background px-2 py-1 text-left text-[8px] leading-relaxed text-muted-foreground hover:border-primary/40 hover:text-foreground"
                >
                  {suggestion}
                </button>
              ))}
            </div>

            <label
              htmlFor="officer-portfolio-value"
              className="mt-3 block text-[8px] uppercase tracking-wider text-muted-foreground"
            >
              Scenario portfolio value
              <div className="relative mt-1">
                <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[9px]">
                  $
                </span>
                <Input
                  id="officer-portfolio-value"
                  type="number"
                  min="1"
                  max="1000000000000"
                  step="1000"
                  value={portfolioValue}
                  onChange={(event) =>
                    setPortfolioValue(Number(event.target.value))
                  }
                  className="h-8 rounded-sm pl-5 text-right font-mono text-xs"
                />
              </div>
            </label>

            <Button
              type="button"
              onClick={submitQuestion}
              disabled={isLoading}
              className="mt-3 h-9 w-full rounded-sm text-[10px] font-semibold uppercase tracking-wider"
            >
              {isLoading ? (
                <Sparkles className="size-3 animate-pulse" />
              ) : (
                <Send className="size-3" />
              )}
              {isLoading ? 'Applying deterministic rules…' : 'Ask Risk Officer'}
            </Button>

            <div className="mt-3 border border-primary/20 bg-primary/5 p-2.5 text-[8px] leading-relaxed text-muted-foreground">
              <p className="flex items-center gap-1.5 font-semibold uppercase tracking-wider text-primary">
                <ShieldCheck className="size-3" /> Numerical control boundary
              </p>
              <p className="mt-1.5">
                Python rules select the qualitative findings. Evidence values
                are attached from calculated metrics or explicit scenario
                inputs. No external AI service is required.
              </p>
            </div>
          </section>

          <section className="min-w-0 p-4" aria-live="polite">
            {error && (
              <Alert variant="destructive" className="mb-3 rounded-sm">
                <AlertTriangle />
                <AlertTitle>Risk Officer unavailable</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {!result && !isLoading && (
              <div className="grid min-h-64 place-items-center border border-dashed border-border bg-background/30 px-6 text-center">
                <div className="max-w-md">
                  <BrainCircuit className="mx-auto size-7 text-primary/70" />
                  <p className="mt-3 text-sm font-semibold">
                    Awaiting risk question
                  </p>
                  <p className="mt-2 text-[10px] leading-5 text-muted-foreground">
                    The officer diagnoses concentration, correlation, volatility
                    contribution, tail risk, and drawdown. It also supports
                    bounded English and Chinese shock phrases; use the
                    structured Stress Testing panel for complex scenarios.
                  </p>
                </div>
              </div>
            )}

            {isLoading && (
              <div className="grid min-h-64 place-items-center border border-border bg-background/30 px-6 text-center">
                <div>
                  <Sparkles className="mx-auto size-6 animate-pulse text-primary" />
                  <p className="mt-3 text-[10px] uppercase tracking-wider text-muted-foreground">
                    Parsing supported language · validating context · preparing
                    explanation
                  </p>
                </div>
              </div>
            )}

            {result && !isLoading && (
              <div>
                <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-3">
                  <div className="max-w-2xl">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        variant="outline"
                        className="rounded-sm text-[8px]"
                      >
                        {result.intent === 'stress_scenario'
                          ? 'HYPOTHETICAL SCENARIO'
                          : 'PORTFOLIO DIAGNOSIS'}
                      </Badge>
                      <span className="text-[8px] uppercase tracking-wider text-muted-foreground">
                        Engine: {result.model}
                      </span>
                      <Badge
                        variant="outline"
                        className="rounded-sm text-[7px] text-muted-foreground"
                      >
                        {result.narrative_source === 'deterministic_rule_engine'
                          ? 'DETERMINISTIC RULE ENGINE'
                          : 'OPENAI STRUCTURED OUTPUT'}
                      </Badge>
                    </div>
                    <h3 className="mt-2 text-base font-semibold tracking-tight">
                      {result.headline}
                    </h3>
                    <p className="mt-2 text-[11px] leading-5 text-muted-foreground">
                      {result.summary}
                    </p>
                  </div>
                  <CheckCircle2 className="size-4 shrink-0 text-emerald-300" />
                </div>

                {result.stress_test && (
                  <div className="mt-3 border border-amber-300/20 bg-amber-300/5">
                    <div className="flex items-center justify-between border-b border-amber-300/15 px-3 py-2">
                      <p className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wider text-amber-200">
                        <FlaskConical className="size-3" /> Python stress engine
                        result
                      </p>
                      <span className="text-[8px] uppercase tracking-wider text-muted-foreground">
                        Hypothetical · not a prediction
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-px bg-border sm:grid-cols-4">
                      <div className="bg-card p-2.5">
                        <p className="text-[8px] uppercase text-muted-foreground">
                          Estimated return
                        </p>
                        <p className="mt-1 font-mono text-sm text-rose-300">
                          {percent(
                            result.stress_test.estimated_portfolio_return,
                          )}
                        </p>
                      </div>
                      <div className="bg-card p-2.5">
                        <p className="text-[8px] uppercase text-muted-foreground">
                          Estimated P&amp;L
                        </p>
                        <p className="mt-1 font-mono text-sm text-rose-300">
                          {money(result.stress_test.estimated_dollar_pnl)}
                        </p>
                      </div>
                      <div className="bg-card p-2.5">
                        <p className="text-[8px] uppercase text-muted-foreground">
                          Before
                        </p>
                        <p className="mt-1 font-mono text-sm">
                          {money(result.stress_test.portfolio_value_before)}
                        </p>
                      </div>
                      <div className="bg-card p-2.5">
                        <p className="text-[8px] uppercase text-muted-foreground">
                          After
                        </p>
                        <p className="mt-1 font-mono text-sm">
                          {money(result.stress_test.portfolio_value_after)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="mt-3 grid gap-2 2xl:grid-cols-2">
                  {result.findings.map((finding) => (
                    <article
                      key={`${finding.title}-${finding.explanation}`}
                      className="border border-border bg-background/35 p-3"
                    >
                      <p className="text-[10px] font-semibold text-foreground">
                        {finding.title}
                      </p>
                      <p className="mt-1.5 text-[9px] leading-4 text-muted-foreground">
                        {finding.explanation}
                      </p>
                      <div className="mt-2 space-y-1.5">
                        {finding.evidence.map((item) => (
                          <div
                            key={item.key}
                            className="flex flex-wrap items-center justify-between gap-2 border-t border-border/70 pt-1.5 text-[8px]"
                          >
                            <span className="text-muted-foreground">
                              {item.label}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-[9px] text-foreground">
                                {item.value}
                              </span>
                              <Badge
                                className={`rounded-sm px-1 py-0 text-[6px] ${evidenceTone(item.source_type)}`}
                              >
                                {item.source_type.replaceAll('_', ' ')}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>

                <div className="mt-3 grid gap-2 border border-border p-3 sm:grid-cols-[1fr_auto]">
                  <div>
                    <p className="section-label">Known limitations</p>
                    {result.limitations.map((limitation) => (
                      <p
                        key={limitation}
                        className="mt-1.5 text-[8px] leading-relaxed text-muted-foreground"
                      >
                        • {limitation}
                      </p>
                    ))}
                  </div>
                  <Badge
                    variant="outline"
                    className="h-fit rounded-sm text-[7px] text-muted-foreground"
                  >
                    NO BUY / SELL ADVICE
                  </Badge>
                </div>

                <p className="mt-2 text-[8px] leading-relaxed text-muted-foreground">
                  {result.numerical_policy} {result.disclaimer}
                </p>
              </div>
            )}
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
