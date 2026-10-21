import type {
  AnalyzeRequest,
  BacktestRequest,
  BacktestResult,
  OptimizeRequest,
  OptimizationResult,
  PortfolioAnalysis,
  RiskOfficerRequest,
  RiskOfficerResult,
  StressTestRequest,
  StressTestResult,
} from '@/lib/types';
import type {
  VarBacktestRequest,
  VarBacktestResponse,
} from '@/lib/var-backtest';

const CONFIGURED_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.replace(
  /\/$/,
  '',
);

function getApiBaseUrl(): string {
  if (CONFIGURED_API_BASE_URL) return CONFIGURED_API_BASE_URL;

  if (
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1')
  ) {
    return 'http://localhost:8000';
  }

  throw new ApiError(
    'The deployed frontend has no backend URL. Deploy FastAPI, then set NEXT_PUBLIC_API_URL to its HTTPS origin and rebuild the frontend.',
    undefined,
    'API_URL_NOT_CONFIGURED',
  );
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
  ) {
    super(message);
  }
}

export async function analyzePortfolio(
  payload: AnalyzeRequest,
  signal?: AbortSignal,
): Promise<PortfolioAnalysis> {
  const apiBaseUrl = getApiBaseUrl();
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/portfolio/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error;
    throw new ApiError(
      'The Python analytics service could not be reached. Confirm the backend deployment and CORS configuration, then try again.',
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string | { message?: string; code?: string };
    } | null;
    const detail = body?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : (detail?.message ??
          `Analysis failed with status ${response.status}.`);
    throw new ApiError(
      message,
      response.status,
      typeof detail === 'object' ? detail.code : undefined,
    );
  }

  return response.json() as Promise<PortfolioAnalysis>;
}

export async function optimizePortfolio(
  payload: OptimizeRequest,
  signal?: AbortSignal,
): Promise<OptimizationResult> {
  const apiBaseUrl = getApiBaseUrl();
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/portfolio/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error;
    throw new ApiError('The optimization service could not be reached.');
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string | Array<{ msg?: string }> | { message?: string; code?: string };
    } | null;
    const detail = body?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item.msg).filter(Boolean).join('; ')
        : detail?.message ?? `Optimization failed with status ${response.status}.`;
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<OptimizationResult>;
}

export async function backtestPortfolio(
  payload: BacktestRequest,
  signal?: AbortSignal,
): Promise<BacktestResult> {
  const apiBaseUrl = getApiBaseUrl();
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/portfolio/backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('The Python backtest service could not be reached.');
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string | Array<{ msg?: string }> | { message?: string; code?: string };
    } | null;
    const detail = body?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((item) => item.msg).filter(Boolean).join('; ')
        : detail?.message ?? `Backtest failed with status ${response.status}.`;
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<BacktestResult>;
}

export async function backtestVarPortfolio(
  payload: VarBacktestRequest,
  signal?: AbortSignal,
): Promise<VarBacktestResponse> {
  const apiBaseUrl = getApiBaseUrl();
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/portfolio/var-backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error;
    throw new ApiError('The Python VaR backtest service could not be reached.');
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?:
        | string
        | Array<{ msg?: string }>
        | { message?: string; code?: string };
    } | null;
    const detail = body?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item) => item.msg)
              .filter(Boolean)
              .join('; ')
          : (detail?.message ??
            `VaR backtest failed with status ${response.status}.`);
    throw new ApiError(
      message,
      response.status,
      !Array.isArray(detail) && typeof detail === 'object'
        ? detail?.code
        : undefined,
    );
  }
  return response.json() as Promise<VarBacktestResponse>;
}

export async function runStressTest(
  payload: StressTestRequest,
  signal?: AbortSignal,
): Promise<StressTestResult> {
  const apiBaseUrl = getApiBaseUrl();
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/portfolio/stress-test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error;
    throw new ApiError(
      'The Python stress engine is offline. Start the FastAPI service on port 8000 and try again.',
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?:
        | string
        | Array<{ msg?: string }>
        | { message?: string; code?: string };
    } | null;
    const detail = body?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item) => item.msg)
              .filter(Boolean)
              .join('; ')
          : (detail?.message ??
            `Stress test failed with status ${response.status}.`);
    throw new ApiError(
      message,
      response.status,
      !Array.isArray(detail) && typeof detail === 'object'
        ? detail?.code
        : undefined,
    );
  }

  return response.json() as Promise<StressTestResult>;
}

export async function askRiskOfficer(
  payload: RiskOfficerRequest,
  signal?: AbortSignal,
): Promise<RiskOfficerResult> {
  const apiBaseUrl = getApiBaseUrl();
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/ai/risk-officer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error;
    throw new ApiError(
      'The AI Risk Officer backend is unreachable. Confirm that the FastAPI service is online.',
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?:
        | string
        | Array<{ msg?: string }>
        | { message?: string; code?: string };
    } | null;
    const detail = body?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item) => item.msg)
              .filter(Boolean)
              .join('; ')
          : (detail?.message ??
            `Risk Officer request failed with status ${response.status}.`);
    throw new ApiError(
      message,
      response.status,
      !Array.isArray(detail) && typeof detail === 'object'
        ? detail?.code
        : undefined,
    );
  }

  return response.json() as Promise<RiskOfficerResult>;
}
