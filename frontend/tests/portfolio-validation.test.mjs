import assert from 'node:assert/strict';
import test from 'node:test';
import {
  validatePortfolioInput,
  PORTFOLIO_INPUT_MESSAGES as messages,
} from '../lib/portfolio-validation.ts';
import { translate, zhMessages } from '../lib/translations.ts';

const position = (ticker = 'AAPL', weight = 1) => ({ ticker, weight });

test('valid long-only inputs include zero weights and supported ticker punctuation', () => {
  const input = [
    position('BRK-B', 0.5),
    position('0700.HK', 0.5),
    position('MSFT', 0),
  ];
  const result = validatePortfolioInput(input);
  assert.equal(result.isValid, true);
  assert.equal(result.total, 1);
  assert.equal(result.message, null);
  assert.ok(
    result.rows.every((row) => row.ticker === null && row.weight === null),
  );
});

test('duplicate detection trims and folds case, marking every matching row', () => {
  const result = validatePortfolioInput([
    position('aapl ', 0.5),
    position(' AAPL', 0.5),
  ]);
  assert.equal(result.isValid, false);
  assert.deepEqual(
    result.rows.map((row) => row.ticker),
    [messages.duplicate, messages.duplicate],
  );
  assert.equal(result.message, messages.rows);
});

test('invalid ticker syntax and API field length are rejected without market-data lookup', () => {
  for (const ticker of [
    '',
    ' ',
    '^SPX',
    'AAPL,MSFT',
    'A/B',
    '.SPY',
    '-SPY',
    'A'.repeat(16),
    ' A'.padEnd(16),
  ]) {
    const result = validatePortfolioInput([position(ticker)]);
    assert.equal(result.isValid, false, ticker);
    assert.equal(result.rows[0].ticker, messages.ticker, ticker);
  }
  assert.equal(
    validatePortfolioInput([position('A'.repeat(15))]).isValid,
    true,
  );
});

test('empty and oversized portfolios are invalid; adding stops at the API limit', () => {
  assert.equal(validatePortfolioInput([]).message, messages.empty);
  const fifty = Array.from({ length: 50 }, (_, i) => position(`T${i}`, 0.02));
  assert.equal(validatePortfolioInput(fifty).isValid, true);
  assert.equal(validatePortfolioInput(fifty).canAdd, false);
  assert.equal(validatePortfolioInput(fifty.slice(1)).canAdd, true);
  const oversized = validatePortfolioInput([...fifty, position('EXTRA', 0)]);
  assert.equal(oversized.message, messages.limit);
  assert.equal(oversized.canAdd, false);
});

test('weights must be finite and within long-only limits', () => {
  for (const weight of [NaN, Infinity, -Infinity, -0.01, 1.01]) {
    const result = validatePortfolioInput([position('AAPL', weight)]);
    assert.equal(result.isValid, false);
    assert.equal(result.rows[0].weight, messages.weight);
  }
});

test('total weight tolerance matches the API, with no silent normalization', () => {
  const input = [position('AAPL', 0.4), position('MSFT', 0.4)];
  const before = structuredClone(input);
  assert.equal(validatePortfolioInput(input).message, messages.total);
  assert.deepEqual(input, before);
  assert.equal(
    validatePortfolioInput([position('AAPL', 0.99995)]).isValid,
    true,
  );
  assert.equal(
    validatePortfolioInput([position('AAPL', 0.9998)]).isValid,
    false,
  );
});

test('normalization rejects zero, negative, nonfinite or overflowing totals', () => {
  for (const input of [
    [],
    [position('AAPL', 0)],
    [position('AAPL', -1)],
    [position('AAPL', NaN)],
    [position('AAPL', Infinity)],
    [position('AAPL', Number.MAX_VALUE), position('MSFT', Number.MAX_VALUE)],
  ]) {
    assert.equal(validatePortfolioInput(input).canNormalize, false);
  }
  assert.equal(
    validatePortfolioInput([position('AAPL', Infinity)]).total,
    null,
  );
});

test('explicit normalization can repair finite oversized weights independently of ticker edits', () => {
  assert.equal(validatePortfolioInput([position('', 2)]).canNormalize, true);
  assert.equal(
    validatePortfolioInput([position('AAPL', 0.2)]).canNormalize,
    true,
  );
});

test('correcting a duplicate clears only the remaining input problems', () => {
  const input = [position('AAPL', 0.5), position('AAPL', 0.5)];
  assert.equal(validatePortfolioInput(input).isValid, false);
  input[1].ticker = 'MSFT';
  assert.equal(validatePortfolioInput(input).isValid, true);
  input[1].weight = 0.3;
  assert.equal(validatePortfolioInput(input).message, messages.total);
});

test('every dynamic validation message has English and Chinese copy', () => {
  for (const message of Object.values(messages)) {
    assert.ok(Object.hasOwn(zhMessages, message), message);
    assert.equal(translate('en', message), message);
    assert.notEqual(translate('zh', message), message);
  }
});

test('invalid drafts expose no ticker-keyed controls or partial request portfolio', () => {
  const invalid = [
    [],
    [position('AAPL', 0.5), position(' aapl ', 0.5)],
    [position('', 0.5), position('', 0.5)],
    [position('AAPL', 0.5), position('A/B', 0.5)],
    [position('AAPL', 0.5)],
    [position('AAPL', NaN)],
    [position('AAPL', -0.1), position('MSFT', 1.1)],
    Array.from({ length: 51 }, (_, i) => position(`T${i}`, 1 / 51)),
  ];
  for (const input of invalid) {
    const before = structuredClone(input);
    const result = validatePortfolioInput(input);
    assert.equal(result.isValid, false);
    assert.deepEqual(result.validPositions, []);
    assert.deepEqual(input, before);
  }
});

test('valid request holdings normalize identifiers, not weights or capital', () => {
  const input = [
    { ticker: ' aapl ', weight: 0.99995, initial_value: 12345 },
    position('msft', 0),
  ];
  const before = structuredClone(input);
  const result = validatePortfolioInput(input);
  assert.equal(result.isValid, true);
  assert.deepEqual(result.validPositions, [
    { ticker: 'AAPL', weight: 0.99995, initial_value: 12345 },
    position('MSFT', 0),
  ]);
  assert.deepEqual(input, before);
  assert.notEqual(result.validPositions[0], input[0]);
});

test('fixing duplicate and blank draft rows restores exactly the current unique holdings', () => {
  const input = [position('AAPL', 0.5), position('AAPL', 0.5)];
  assert.deepEqual(validatePortfolioInput(input).validPositions, []);
  input[1].ticker = '';
  assert.deepEqual(validatePortfolioInput(input).validPositions, []);
  input[1].ticker = 'MSFT';
  assert.deepEqual(validatePortfolioInput(input).validPositions, input);
});

test('stress draft validation guidance is bilingual', () => {
  const message =
    'Fix the portfolio inputs before configuring ticker overrides or running a stress test.';
  assert.equal(translate('en', message), message);
  assert.equal(
    translate('zh', message),
    '请先修正组合输入，再设置个股冲击或运行压力测试。',
  );
});
