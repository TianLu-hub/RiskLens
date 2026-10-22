import assert from 'node:assert/strict';
import test from 'node:test';
import {
  INVALID_OVERRIDE_MESSAGE,
  overrideDrafts,
  tickerShockInputs,
  toggleOverride,
} from '../lib/stress-overrides.ts';
import { translate } from '../lib/translations.ts';
import { STRESS_PRESETS } from '../lib/stress-data.ts';

test('zero override is serialized, while an unchecked asset inherits factors', () => {
  assert.deepEqual(
    tickerShockInputs(['NVDA', 'TLT', 'SPY'], { NVDA: '0', TLT: '0.0' }),
    {
      NVDA: 0,
      TLT: 0,
    },
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(tickerShockInputs(['NVDA'], { NVDA: '0' }))),
    { NVDA: 0 },
  );
  assert.deepEqual(tickerShockInputs(['NVDA'], {}), {});
});

test('enabling starts at explicit zero and disabling removes the override without mutation', () => {
  const initial = { NVDA: '-30' };
  const enabled = toggleOverride(initial, 'TLT', true);
  assert.deepEqual(initial, { NVDA: '-30' });
  assert.deepEqual(enabled, { NVDA: '-30', TLT: '0' });
  assert.deepEqual(toggleOverride(enabled, 'NVDA', true), enabled);
  const disabled = toggleOverride(enabled, 'NVDA', false);
  assert.deepEqual(tickerShockInputs(['NVDA', 'TLT'], disabled), { TLT: 0 });
  assert.deepEqual(enabled, { NVDA: '-30', TLT: '0' });
});

test('presets replace overrides; historical-style presets inherit and custom retains NVDA', () => {
  for (const preset of STRESS_PRESETS) {
    const drafts = overrideDrafts(preset.tickerShocksPct);
    const inputs = tickerShockInputs(
      ['AAPL', 'MSFT', 'NVDA', 'SPY', 'TLT'],
      drafts,
    );
    assert.deepEqual(inputs, preset.id === 'custom' ? { NVDA: -0.3 } : {});
  }
  assert.deepEqual(overrideDrafts({ NVDA: 0 }), { NVDA: '0' });
});

test('removed holdings and inherited object properties never become ticker shocks', () => {
  const drafts = Object.assign(Object.create({ SPY: '-50' }), {
    NVDA: '-30',
    TLT: '',
  });
  assert.deepEqual(tickerShockInputs(['SPY'], drafts), {});
  assert.deepEqual(tickerShockInputs(['NVDA'], drafts), { NVDA: -0.3 });
});

test('signed percentage inputs are converted without calculating asset or portfolio returns', () => {
  assert.deepEqual(
    tickerShockInputs(['NVDA', 'TLT', 'SPY'], {
      NVDA: '-100',
      TLT: '100',
      SPY: ' 2.5 ',
    }),
    {
      NVDA: -1,
      TLT: 1,
      SPY: 0.025,
    },
  );
});

for (const value of [
  '',
  ' ',
  '-',
  'NaN',
  'Infinity',
  '-Infinity',
  '101',
  '-101',
  'abc',
]) {
  test(`enabled invalid input ${JSON.stringify(value)} is rejected, never silently dropped or made zero`, () => {
    assert.throws(() => tickerShockInputs(['NVDA'], { NVDA: value }), {
      message: INVALID_OVERRIDE_MESSAGE,
    });
  });
}

test('override semantics and errors are available in English and Chinese', () => {
  const keys = [
    INVALID_OVERRIDE_MESSAGE,
    'Total shock override',
    'Uses factor shocks',
    'Check a ticker to replace its total shock. Unchecked uses factor shocks; enabled 0% keeps that asset unchanged.',
  ];
  for (const key of keys) {
    assert.equal(translate('en', key), key);
    assert.notEqual(translate('zh', key), key);
  }
  assert.equal(
    translate('zh', 'Override {ticker} total shock', { ticker: 'NVDA' }),
    '覆盖 NVDA 总冲击',
  );
});
