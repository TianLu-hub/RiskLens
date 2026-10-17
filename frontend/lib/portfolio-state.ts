import type { PositionInput } from './types';

export const PORTFOLIO_STORAGE_KEY = 'risklens-portfolio';

export type PortfolioSettings = {
  positions: PositionInput[];
  lookbackYears: number;
  riskFreeRate: number;
};

/** Compare the inputs behind a result, regardless of ticker casing or row order. */
export function analysisInputKey(settings: PortfolioSettings): string {
  return JSON.stringify({
    ...settings,
    positions: settings.positions
      .map(({ ticker, weight, initial_value }) => ({
        ticker: ticker.trim().toUpperCase(),
        weight,
        initial_value,
      }))
      .sort((a, b) => a.ticker.localeCompare(b.ticker)),
  });
}

/** Validate browser storage, including drafts whose weights are not yet normalized. */
export function parseSavedPortfolio(raw: string): PortfolioSettings | null {
  try {
    const parsed = JSON.parse(raw);
    // Migrate the original positions-only storage format.
    const data = Array.isArray(parsed)
      ? { version: 1, positions: parsed, lookbackYears: 3, riskFreeRate: 0.04 }
      : parsed;
    if (
      !data ||
      data.version !== 1 ||
      !Array.isArray(data.positions) ||
      data.positions.length < 1 ||
      data.positions.length > 50 ||
      ![1, 3, 5].includes(data.lookbackYears) ||
      typeof data.riskFreeRate !== 'number' ||
      !Number.isFinite(data.riskFreeRate) ||
      data.riskFreeRate < -0.1 ||
      data.riskFreeRate > 0.5
    )
      return null;

    const positions: PositionInput[] = [];
    for (const position of data.positions) {
      if (
        !position ||
        typeof position.ticker !== 'string' ||
        !/^(?:[A-Z0-9][A-Z0-9.-]{0,14})?$/.test(
          position.ticker.trim().toUpperCase(),
        ) ||
        typeof position.weight !== 'number' ||
        !Number.isFinite(position.weight) ||
        position.weight < 0 ||
        position.weight > 1 ||
        (position.initial_value != null &&
          (typeof position.initial_value !== 'number' ||
            !Number.isFinite(position.initial_value) ||
            position.initial_value <= 0))
      )
        return null;
      positions.push({
        ticker: position.ticker.trim().toUpperCase(),
        weight: position.weight,
        ...(position.initial_value != null
          ? { initial_value: position.initial_value }
          : {}),
      });
    }
    return {
      positions,
      lookbackYears: data.lookbackYears,
      riskFreeRate: data.riskFreeRate,
    };
  } catch {
    return null;
  }
}

/** Storage failures must never turn a successful analysis into an API error. */
export function savePortfolio(
  storage: Pick<Storage, 'setItem'>,
  settings: PortfolioSettings,
): boolean {
  try {
    const raw = JSON.stringify({ version: 1, ...settings });
    if (!parseSavedPortfolio(raw)) return false;
    storage.setItem(PORTFOLIO_STORAGE_KEY, raw);
    return true;
  } catch {
    return false;
  }
}
