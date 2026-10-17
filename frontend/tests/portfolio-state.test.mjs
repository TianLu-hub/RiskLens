import assert from 'node:assert/strict';
import test from 'node:test';
import {
  analysisInputKey,
  parseSavedPortfolio,
  savePortfolio,
} from '../lib/portfolio-state.ts';

const settings = {
  positions: [
    { ticker: 'SPY', weight: 0.6 },
    { ticker: 'TLT', weight: 0.4 },
  ],
  lookbackYears: 5,
  riskFreeRate: 0.03,
};

test('saved portfolio restores positions and analysis settings', () => {
  let raw;
  assert.equal(
    savePortfolio(
      {
        setItem: (_key, value) => {
          raw = value;
        },
      },
      settings,
    ),
    true,
  );
  assert.deepEqual(parseSavedPortfolio(raw), settings);
});

test('legacy positions migrate with default settings', () => {
  assert.deepEqual(parseSavedPortfolio(JSON.stringify(settings.positions)), {
    ...settings,
    lookbackYears: 3,
    riskFreeRate: 0.04,
  });
});

test('unfinished weight edits survive reload without normalization', () => {
  const draft = { ...settings, positions: [{ ticker: '', weight: 0.25 }] };
  assert.deepEqual(
    parseSavedPortfolio(JSON.stringify({ version: 1, ...draft })),
    draft,
  );
});

test('malformed and unsupported saved data is ignored safely', () => {
  for (const raw of [
    '{',
    'null',
    '{}',
    '[]',
    JSON.stringify({ version: 2, ...settings }),
    JSON.stringify({ version: 1, ...settings, riskFreeRate: '0.04' }),
    JSON.stringify({
      version: 1,
      ...settings,
      positions: [{ ticker: 'SPY', weight: -1 }],
    }),
    JSON.stringify({ version: 1, ...settings, lookbackYears: 99 }),
  ]) {
    assert.equal(parseSavedPortfolio(raw), null);
  }
});

test('blocked storage does not throw into the analysis flow', () => {
  assert.equal(
    savePortfolio(
      {
        setItem: () => {
          throw new Error('Storage blocked');
        },
      },
      settings,
    ),
    false,
  );
});

test('stale detection covers weight and parameter changes and clears on revert', () => {
  const original = analysisInputKey(settings);
  assert.notEqual(
    analysisInputKey({ ...settings, riskFreeRate: 0.05 }),
    original,
  );
  assert.notEqual(
    analysisInputKey({ ...settings, lookbackYears: 1 }),
    original,
  );
  assert.notEqual(
    analysisInputKey({
      ...settings,
      positions: [{ ticker: 'SPY', weight: 1 }],
    }),
    original,
  );
  assert.equal(analysisInputKey(structuredClone(settings)), original);
  assert.equal(
    analysisInputKey({
      ...settings,
      positions: [
        { ticker: ' tlt ', weight: 0.4 },
        { ticker: 'spy', weight: 0.6 },
      ],
    }),
    original,
  );
});
