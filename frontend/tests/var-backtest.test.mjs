import assert from 'node:assert/strict';
import test from 'node:test';
import {
  localizeVarNotice,
  validateVarBacktestInput,
  varBacktestCopy,
  varBacktestKey,
  varBacktestRequest,
  varBreachRows,
} from '../lib/var-backtest.ts';

const positions = [
  { ticker: 'AAPL', weight: 0.4 },
  { ticker: 'SPY', weight: 0.6 },
];
const baseline = varBacktestRequest(positions, 3, 252, 0.95);

test('request uses current portfolio inputs without adjusting weights or adding financial statistics', () => {
  assert.deepEqual(baseline, {
    positions,
    lookback_years: 3,
    window_days: 252,
    confidence_level: 0.95,
  });
  assert.equal(validateVarBacktestInput(baseline), null);
  assert.deepEqual(positions, [
    { ticker: 'AAPL', weight: 0.4 },
    { ticker: 'SPY', weight: 0.6 },
  ]);
});

test('ticker whitespace and capital do not invalidate an equivalent return-based request', () => {
  const equivalent = varBacktestRequest(
    [
      { ticker: ' aapl ', weight: 0.4, initial_value: 100000 },
      { ticker: 'spy', weight: 0.6, initial_value: 80000 },
    ],
    3,
    252,
    0.95,
  );
  assert.equal(varBacktestKey(equivalent), varBacktestKey(baseline));
});

test('a change to any model input invalidates the prior response key', () => {
  const changes = [
    varBacktestRequest(
      [{ ticker: 'MSFT', weight: 0.4 }, positions[1]],
      3,
      252,
      0.95,
    ),
    varBacktestRequest(
      [
        { ticker: 'AAPL', weight: 0.5 },
        { ticker: 'SPY', weight: 0.5 },
      ],
      3,
      252,
      0.95,
    ),
    varBacktestRequest(positions, 5, 252, 0.95),
    varBacktestRequest(positions, 3, 126, 0.95),
    varBacktestRequest(positions, 3, 252, 0.99),
  ];
  for (const changed of changes)
    assert.notEqual(varBacktestKey(changed), varBacktestKey(baseline));
});

test('invalid, empty, duplicate and excessive ticker lists are rejected before fetching', () => {
  for (const invalid of [
    [],
    [{ ticker: '', weight: 1 }],
    [{ ticker: 'SPY AAPL', weight: 1 }],
    [
      { ticker: 'SPY', weight: 0.5 },
      { ticker: ' spy ', weight: 0.5 },
    ],
    Array.from({ length: 51 }, (_, index) => ({
      ticker: `A${index}`,
      weight: 1 / 51,
    })),
  ])
    assert.equal(
      validateVarBacktestInput(varBacktestRequest(invalid, 3, 252, 0.95)),
      'positions',
    );
});

test('weights are validated but never silently normalized', () => {
  for (const invalid of [
    [{ ticker: 'SPY', weight: 0.9 }],
    [{ ticker: 'SPY', weight: Number.NaN }],
    [{ ticker: 'SPY', weight: Number.POSITIVE_INFINITY }],
    [
      { ticker: 'SPY', weight: 1.1 },
      { ticker: 'TLT', weight: -0.1 },
    ],
  ])
    assert.equal(
      validateVarBacktestInput(varBacktestRequest(invalid, 3, 252, 0.95)),
      'weights',
    );
  assert.equal(
    validateVarBacktestInput(
      varBacktestRequest([{ ticker: 'SPY', weight: 0.99999 }], 3, 252, 0.95),
    ),
    null,
  );
});

test('model parameter validation rejects nonfinite, fractional and out-of-range settings', () => {
  for (const invalid of [
    { ...baseline, lookback_years: 0 },
    { ...baseline, lookback_years: 1.5 },
    { ...baseline, window_days: 59 },
    { ...baseline, window_days: 1261 },
    { ...baseline, window_days: Number.NaN },
    { ...baseline, confidence_level: 1 },
    { ...baseline, confidence_level: Number.NaN },
  ])
    assert.equal(validateVarBacktestInput(invalid), 'parameters');
  // History sufficiency is based on real aligned observations in Python, not an invented frontend count.
  assert.equal(
    validateVarBacktestInput({ ...baseline, lookback_years: 1 }),
    null,
  );
});

test('breach table follows backend flags, including signed VaR, without recomputing decisions', () => {
  const points = [
    {
      date: '2025-01-01',
      var_loss: -0.01,
      realized_loss: -0.005,
      breach: true,
    },
    { date: '2025-01-02', var_loss: 0.01, realized_loss: 0.01, breach: false },
    { date: '2025-01-03', var_loss: 0.01, realized_loss: 0.02, breach: false },
  ];
  // The last intentionally inconsistent fixture proves this helper trusts the API,
  // rather than hiding a second implementation of the risk engine in JavaScript.
  assert.deepEqual(varBreachRows({ series: points }), [points[0]]);
  assert.equal(points.length, 3);
});

test('sample warnings retain backend-supplied values when switching language', () => {
  const short =
    'Only 34 out-of-sample returns are available (fewer than 252 trading days); the observed breach rate may be unstable.';
  const sparse =
    'The nominal expected breach count is 0.34, below 5; this sample provides limited evidence about tail coverage.';
  assert.equal(localizeVarNotice(short, 'en'), short);
  assert.match(localizeVarNotice(short, 'zh'), /34 条样本外收益/);
  assert.match(localizeVarNotice(sparse, 'zh'), /0\.34/);
  assert.equal(
    localizeVarNotice('Unexpected provider notice', 'zh'),
    'Unexpected provider notice',
  );
});

test('all UI copy has English and Chinese equivalents, including limitations', () => {
  assert.deepEqual(
    Object.keys(varBacktestCopy.en).sort(),
    Object.keys(varBacktestCopy.zh).sort(),
  );
  for (const value of Object.values(varBacktestCopy.zh)) {
    for (const text of Array.isArray(value) ? value : [value])
      assert.match(text, /[\u4e00-\u9fff]/);
  }
  assert.equal(
    varBacktestCopy.en.limitations.length,
    varBacktestCopy.zh.limitations.length,
  );
});
