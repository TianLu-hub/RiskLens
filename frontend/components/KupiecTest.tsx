'use client';

import { AlertTriangle } from 'lucide-react';

import { useLanguage } from '@/components/LanguageProvider';
import {
  formatKupiecPValue,
  formatKupiecStatistic,
  kupiecCopy,
  kupiecDecision,
  kupiecWarnings,
  type KupiecTestResult,
} from '@/lib/kupiec';

export function KupiecTest({ result }: { result?: KupiecTestResult | null }) {
  const { locale } = useLanguage();
  const c = kupiecCopy[locale];
  const decision = kupiecDecision(result);
  const warnings = result == null ? [] : kupiecWarnings(result, locale);

  return (
    <section
      aria-label={c.title}
      className="rounded-sm border border-border bg-muted/10 p-4"
    >
      <h3 className="text-sm font-semibold">{c.title}</h3>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        {c.subtitle}
      </p>
      {result == null ? (
        <div className="mt-3 border-t border-border pt-3">
          <p className="text-sm font-medium text-muted-foreground">
            {c.unavailable}
          </p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {c.unavailableNote}
          </p>
        </div>
      ) : (
        <>
          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {[
              [c.statistic, formatKupiecStatistic(result.statistic)],
              [c.pValue, formatKupiecPValue(result.p_value)],
              [
                c.significance,
                `${(result.significance_level * 100).toFixed(0)}%`,
              ],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs leading-5 text-muted-foreground">
                  {label}
                </dt>
                <dd className="mt-1 break-all font-mono text-lg">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            {c.significanceNote}
          </p>
          <p className="mt-3 text-xs leading-5">
            <span className="font-medium">{c.nullLabel}: </span>
            <span className="text-muted-foreground">{c.nullDescription} </span>
            <span className="font-mono">
              {(result.null_breach_probability * 100).toFixed(2)}%
            </span>
          </p>
          <div
            className={`mt-3 border-l-2 pl-3 ${decision === 'reject' ? 'border-amber-300/70' : 'border-primary/50'}`}
          >
            <p
              className={`text-sm font-medium ${decision === 'reject' ? 'text-amber-200' : 'text-primary'}`}
            >
              {c[decision]}
            </p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {decision === 'reject' ? c.rejectNote : c.notRejectedNote}
            </p>
          </div>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            {c.decisionNote}
          </p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            {c.scope}
          </p>
          {warnings.length > 0 && (
            <div className="mt-3 border-t border-amber-300/20 pt-3 text-amber-200">
              <p className="flex items-center gap-2 text-xs font-medium">
                <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
                {c.warnings}
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}
