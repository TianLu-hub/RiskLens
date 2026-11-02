import type { PositionInput } from './types';

export const MAX_PORTFOLIO_POSITIONS = 50;

export const PORTFOLIO_INPUT_MESSAGES = {
  empty: 'Add at least one position.',
  limit: 'A portfolio supports up to 50 positions.',
  ticker:
    'Use 1–15 letters, numbers, dots or hyphens; start with a letter or number.',
  duplicate: 'Each ticker may appear only once.',
  weight: 'Enter a finite weight between 0% and 100%.',
  total: 'Weights must sum to 100% before analysis.',
  rows: 'Review the highlighted positions before analysis.',
} as const;

/** Input checks only; financial metrics remain in the Python backend. */
export function validatePortfolioInput(positions: PositionInput[]) {
  const tickers = positions.map(({ ticker }) => ticker.trim().toUpperCase());
  const counts = new Map<string, number>();
  for (const ticker of tickers)
    counts.set(ticker, (counts.get(ticker) ?? 0) + 1);
  const rows = positions.map(({ ticker, weight }, index) => ({
    ticker:
      ticker.length > 15 || !/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(tickers[index])
        ? PORTFOLIO_INPUT_MESSAGES.ticker
        : (counts.get(tickers[index]) ?? 0) > 1
          ? PORTFOLIO_INPUT_MESSAGES.duplicate
          : null,
    weight:
      !Number.isFinite(weight) || weight < 0 || weight > 1
        ? PORTFOLIO_INPUT_MESSAGES.weight
        : null,
  }));
  const sum = positions.reduce((total, { weight }) => total + weight, 0);
  const total = Number.isFinite(sum) ? sum : null;
  const message =
    positions.length === 0
      ? PORTFOLIO_INPUT_MESSAGES.empty
      : positions.length > MAX_PORTFOLIO_POSITIONS
        ? PORTFOLIO_INPUT_MESSAGES.limit
        : rows.some((row) => row.ticker || row.weight)
          ? PORTFOLIO_INPUT_MESSAGES.rows
          : total === null || Math.abs(total - 1) > 1e-4
            ? PORTFOLIO_INPUT_MESSAGES.total
            : null;
  return {
    rows,
    total,
    message,
    isValid: message === null,
    canAdd: positions.length < MAX_PORTFOLIO_POSITIONS,
    // Oversized but finite nonnegative weights can be repaired explicitly.
    canNormalize:
      total !== null &&
      total > 0 &&
      positions.every(({ weight }) => Number.isFinite(weight) && weight >= 0),
  };
}
