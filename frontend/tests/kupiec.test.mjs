import assert from 'node:assert/strict';
import test from 'node:test';

import {
  formatKupiecPValue,
  formatKupiecStatistic,
  kupiecCopy,
  kupiecDecision,
  kupiecWarnings,
} from '../lib/kupiec.ts';

// These are presentation fixtures, not a JavaScript implementation of the test.
const result = {
  method: 'kupiec_unconditional_coverage',
  statistic: 0.01,
  p_value: 0.92,
  degrees_of_freedom: 1,
  significance_level: 0.05,
  reject_null: false,
  null_breach_probability: 0.05,
  observed_breach_probability: 0.049,
  observations: 1000,
  breaches: 49,
  warning_codes: [],
};

test('older backend responses do not acquire an invented Kupiec decision', () => {
  assert.equal(kupiecDecision(), 'unavailable');
  assert.equal(kupiecDecision(null), 'unavailable');
  assert.equal(kupiecDecision({}.kupiec_test), 'unavailable');
});

test('verdict uses the backend flag rather than recomputing from p-value or breach count', () => {
  assert.equal(kupiecDecision(result), 'notRejected');
  assert.equal(kupiecDecision({ ...result, reject_null: true }), 'reject');
  // Deliberately inconsistent fixture: this proves the UI does not implement a
  // competing hypothesis test from either supplied or rounded numbers.
  assert.equal(kupiecDecision({ ...result, p_value: 0.001 }), 'notRejected');
  assert.equal(kupiecDecision({ ...result, breaches: 0 }), 'notRejected');
});

test('tiny p-values never display as a rounded literal zero', () => {
  for (const value of [0, Number.MIN_VALUE, 1e-20, 0.00009999]) {
    assert.equal(formatKupiecPValue(value), '< 0.0001');
  }
  assert.equal(formatKupiecPValue(0.0001), '0.000100');
});

test('p-value formatting preserves which side of the significance boundary it is on', () => {
  assert.equal(formatKupiecPValue(0.05), '0.050000');
  for (const value of [0.0499999, 0.04999999999999999]) {
    assert.equal(formatKupiecPValue(value), String(value));
    assert.ok(Number(formatKupiecPValue(value)) < 0.05);
  }
  for (const value of [0.0500001, 0.05000000000000001]) {
    assert.equal(formatKupiecPValue(value), String(value));
    assert.ok(Number(formatKupiecPValue(value)) > 0.05);
  }
  assert.equal(formatKupiecPValue(1), '1.000000');
});

test('p-value formatting does not replace invalid values with valid probabilities', () => {
  for (const value of [Number.NaN, Infinity, -Infinity, -0.01, 1.01]) {
    assert.equal(formatKupiecPValue(value), '—');
  }
});

test('LR statistic is only formatted, retaining zero and small positive values', () => {
  assert.equal(formatKupiecStatistic(0), '0.000000');
  assert.equal(formatKupiecStatistic(3.841459), '3.841459');
  assert.equal(formatKupiecStatistic(1e-12), '1.000e-12');
  assert.equal(formatKupiecStatistic(Number.NaN), '—');
  assert.equal(formatKupiecStatistic(-1), '—');
});

test('warning messages follow backend codes without client-side threshold tests', () => {
  assert.deepEqual(kupiecWarnings(result, 'en'), []);
  assert.deepEqual(
    kupiecWarnings({ ...result, observations: 1, breaches: 0 }, 'zh'),
    [],
  );
  const flagged = {
    ...result,
    warning_codes: ['low_expected_counts', 'boundary_breach_count'],
  };
  assert.deepEqual(kupiecWarnings(flagged, 'en'), [
    kupiecCopy.en.low_expected_counts,
    kupiecCopy.en.boundary_breach_count,
  ]);
  assert.deepEqual(kupiecWarnings(flagged, 'zh'), [
    kupiecCopy.zh.low_expected_counts,
    kupiecCopy.zh.boundary_breach_count,
  ]);
});

test('Kupiec headings, decisions, limitations and warnings all have bilingual copy', () => {
  assert.deepEqual(
    Object.keys(kupiecCopy.en).sort(),
    Object.keys(kupiecCopy.zh).sort(),
  );
  for (const message of Object.values(kupiecCopy.zh))
    assert.match(message, /[\u4e00-\u9fff]/);
  assert.match(kupiecCopy.en.notRejected, /^Do not reject/);
  assert.match(kupiecCopy.zh.notRejected, /^不拒绝/);
  assert.match(kupiecCopy.en.decisionNote, /p < 0\.05/);
  assert.match(kupiecCopy.zh.decisionNote, /p < 0\.05/);
  assert.match(kupiecCopy.en.rejectNote, /too many or too few/);
  assert.match(kupiecCopy.en.scope, /independent/);
  assert.match(kupiecCopy.en.scope, /severe/);
});
