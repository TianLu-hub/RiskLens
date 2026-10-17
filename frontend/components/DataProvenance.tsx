'use client';

import { Database } from 'lucide-react';
import { useLanguage } from '@/components/LanguageProvider';
import {
  provenanceCopy,
  provenanceView,
  type DataQuality,
} from '@/lib/data-provenance';

export function DataProvenance({
  quality,
  demo = false,
  context = 'portfolio',
}: {
  quality: DataQuality;
  demo?: boolean;
  context?: 'portfolio' | 'optimization' | 'backtest';
}) {
  const { locale, t } = useLanguage();
  const c = provenanceCopy[locale];
  const view = provenanceView(quality, demo);
  const meta = view.metadata;
  const cacheText =
    view.cache === 'hit'
      ? c.hit
      : view.cache === 'miss'
        ? c.miss
        : view.cache === 'not-applicable'
          ? c.na
          : c.unknown;
  return (
    <section
      aria-label={c.title}
      className="mb-4 rounded-md border border-border bg-card px-4 py-3 text-xs leading-5"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold">
          <Database className="size-4 text-primary" aria-hidden="true" />
          {c.title}
        </h2>
        <span className={view.synthetic ? 'text-amber-200' : 'text-primary'}>
          {view.synthetic ? c.demo : c.historical} · {t(quality.source)}
        </span>
      </div>
      <p className="mt-1 text-muted-foreground">
        {view.synthetic ? c.demoNote : c.historicalNote}
      </p>
      {context !== 'portfolio' && (
        <p className="mt-1 text-amber-200">{c[context]}</p>
      )}
      <dl className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div>
          <dt className="text-muted-foreground">
            {view.synthetic ? c.demoAsOf : c.asOf}
          </dt>
          <dd className="font-mono text-sm">{view.asOf}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{c.fetched}</dt>
          <dd className="font-mono">
            {view.synthetic ? c.na : (view.fetchedAt ?? c.unknown)}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{c.sample}</dt>
          <dd>
            <span className="font-mono text-sm">{quality.observations}</span>{' '}
            {c.observations}
            <br />
            <span className="text-muted-foreground">
              {quality.start_date} → {quality.end_date}
              <br />
              {c.requested}: {quality.requested_lookback_years} {c.years}
            </span>
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{c.cache}</dt>
          <dd>
            {cacheText}
            {meta && (
              <span className="block text-muted-foreground">
                {c.ttl}: {meta.cache_ttl_seconds} {c.seconds}
              </span>
            )}
          </dd>
        </div>
      </dl>
      {!view.synthetic && (
        <p className="mt-2 text-muted-foreground">{c.cacheNote}</p>
      )}
      {!view.synthetic && (
        <p
          className={`mt-2 ${view.hasGaps === false ? 'text-muted-foreground' : 'text-amber-200'}`}
        >
          {view.hasGaps === null
            ? c.unreported
            : view.hasGaps
              ? c.gap
              : c.noGap}
        </p>
      )}
      {meta?.price_basis === 'unadjusted_close' && (
        <p className="mt-2 text-amber-200">{c.unadjusted}</p>
      )}
      {(meta || quality.warnings.length > 0) && (
        <details className="mt-3 border-t border-border pt-2">
          <summary className="cursor-pointer font-medium text-primary focus-visible:outline-2 focus-visible:outline-primary">
            {c.details}
            {quality.warnings.length > 0 ? ` · ${quality.warnings.length}` : ''}
          </summary>
          {meta && (
            <>
              <p className="mt-2 text-muted-foreground">{c.policy}</p>
              <p className="mt-1">
                {c.basis}:{' '}
                {meta.price_basis === 'adjusted_close'
                  ? c.adjusted
                  : c.unadjusted}{' '}
                · {c.limit}: {meta.forward_fill_limit}
              </p>
              <p className="mt-1">
                {c.raw}: {meta.raw_price_rows} · {c.aligned}:{' '}
                {meta.aligned_price_rows} · {c.dropped}:{' '}
                {meta.dropped_price_rows}
              </p>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full min-w-[660px] border-collapse text-left text-xs">
                  <caption className="sr-only">{c.details}</caption>
                  <thead>
                    <tr>
                      {[
                        c.ticker,
                        c.observed,
                        c.missing,
                        c.filled,
                        c.first,
                        c.last,
                      ].map((label) => (
                        <th
                          scope="col"
                          key={label}
                          className="border-b border-border p-2 font-medium text-muted-foreground"
                        >
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {meta.assets.map((asset) => (
                      <tr key={asset.ticker}>
                        <th scope="row" className="p-2 font-mono">
                          {asset.ticker}
                        </th>
                        {[
                          asset.observed_prices,
                          asset.missing_prices,
                          asset.filled_prices,
                          asset.first_observed_date,
                          asset.last_observed_date,
                        ].map((value, index) => (
                          <td key={index} className="p-2 font-mono">
                            {value}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-muted-foreground">{c.scope}</p>
            </>
          )}
          {quality.warnings.length > 0 && (
            <div className="mt-2">
              <p className="font-medium">{c.notices}</p>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-amber-200">
                {quality.warnings.map((warning) => (
                  <li key={warning}>{t(warning)}</li>
                ))}
              </ul>
            </div>
          )}
        </details>
      )}
    </section>
  );
}
