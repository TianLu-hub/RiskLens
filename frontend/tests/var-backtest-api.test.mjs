import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

// Compile the real client without a bundler. Its imports are type-only.
const originalUrl = process.env.NEXT_PUBLIC_API_URL;
process.env.NEXT_PUBLIC_API_URL = 'https://example.invalid/';
const source = await readFile(
  new URL('../lib/api.ts', import.meta.url),
  'utf8',
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ESNext,
  },
});
const { backtestVarPortfolio, ApiError } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
);
if (originalUrl === undefined) delete process.env.NEXT_PUBLIC_API_URL;
else process.env.NEXT_PUBLIC_API_URL = originalUrl;

const request = {
  positions: [{ ticker: 'SPY', weight: 1 }],
  lookback_years: 3,
  window_days: 252,
  confidence_level: 0.95,
};

function stubFetch(t, implementation) {
  const original = globalThis.fetch;
  globalThis.fetch = implementation;
  t.after(() => {
    globalThis.fetch = original;
  });
}

test('VaR client posts the typed input, propagates signal, and returns backend values', async (t) => {
  const signal = new AbortController().signal;
  const response = { method: 'historical_simulation', breach_count: 7 };
  stubFetch(t, async (url, options) => {
    assert.equal(url, 'https://example.invalid/portfolio/var-backtest');
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), request);
    assert.equal(options.signal, signal);
    assert.equal(options.headers['Content-Type'], 'application/json');
    return Response.json(response);
  });
  assert.deepEqual(await backtestVarPortfolio(request, signal), response);
});

test('VaR client preserves typed insufficient-history errors for bilingual presentation', async (t) => {
  stubFetch(t, async () =>
    Response.json(
      {
        detail: {
          code: 'INSUFFICIENT_HISTORY',
          message: 'Need a longer sample.',
        },
      },
      { status: 422 },
    ),
  );
  await assert.rejects(backtestVarPortfolio(request), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.code, 'INSUFFICIENT_HISTORY');
    assert.equal(error.status, 422);
    assert.equal(error.message, 'Need a longer sample.');
    return true;
  });
});

test('VaR client handles validation arrays and non-JSON server failures', async (t) => {
  stubFetch(t, async () =>
    Response.json({ detail: [{ msg: 'Invalid window' }] }, { status: 422 }),
  );
  await assert.rejects(backtestVarPortfolio(request), /Invalid window/);
  globalThis.fetch = async () => new Response('Bad Gateway', { status: 502 });
  await assert.rejects(
    backtestVarPortfolio(request),
    /VaR backtest failed with status 502/,
  );
});

test('VaR client does not turn a cancelled stale request into an offline error', async (t) => {
  const aborted = new DOMException('Cancelled', 'AbortError');
  stubFetch(t, async () => {
    throw aborted;
  });
  await assert.rejects(
    backtestVarPortfolio(request),
    (error) => error === aborted,
  );
});

test('VaR client exposes a readable network error', async (t) => {
  stubFetch(t, async () => {
    throw new TypeError('fetch failed');
  });
  await assert.rejects(
    backtestVarPortfolio(request),
    /VaR backtest service could not be reached/,
  );
});
