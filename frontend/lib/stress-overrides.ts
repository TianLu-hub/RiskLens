/** Presence enables a total-return override; absence inherits factor shocks. */
export type TickerOverrideDrafts = Record<string, string>;

export const INVALID_OVERRIDE_MESSAGE =
  'Enter a total shock between -100% and 100% for every enabled ticker override. Blank is not 0%.';

export function overrideDrafts(
  shocks: Record<string, number>,
): TickerOverrideDrafts {
  return Object.fromEntries(
    Object.entries(shocks).map(([ticker, pct]) => [ticker, String(pct)]),
  );
}

export function toggleOverride(
  drafts: TickerOverrideDrafts,
  ticker: string,
  enabled: boolean,
): TickerOverrideDrafts {
  const next = { ...drafts };
  if (enabled)
    next[ticker] = Object.hasOwn(drafts, ticker) ? drafts[ticker] : '0';
  else delete next[ticker];
  return next;
}

/** Serialize user inputs only; financial calculations stay in Python. */
export function tickerShockInputs(
  tickers: string[],
  drafts: TickerOverrideDrafts,
): Record<string, number> {
  return Object.fromEntries(
    tickers
      .filter((ticker) => Object.hasOwn(drafts, ticker))
      .map((ticker) => {
        const raw = drafts[ticker].trim();
        const pct = Number(raw);
        if (!raw || !Number.isFinite(pct) || pct < -100 || pct > 100) {
          throw new Error(INVALID_OVERRIDE_MESSAGE);
        }
        return [ticker, pct / 100];
      }),
  );
}
