import assert from 'node:assert/strict';
import test from 'node:test';
import { metricHelp, metricHelpLabels } from '../lib/metric-help.ts';

test('all nine metrics have complete English and Chinese explanations', () => {
  assert.deepEqual(
    Object.keys(metricHelp).sort(),
    [
      'annual-return',
      'volatility',
      'sharpe',
      'var',
      'cvar',
      'drawdown',
      'beta',
      'risk-contribution',
      'effective-positions',
    ].sort(),
  );
  for (const entry of Object.values(metricHelp)) {
    assert.match(entry.source, /^backend\/app\/risk\/.+\.py$/);
    for (const key of [
      'title',
      'definition',
      'formula',
      'method',
      'interpretation',
      'limitations',
    ]) {
      assert.ok(entry.en[key].length > 10, `Missing English ${key}`);
      assert.ok(
        entry.zh[key].length >= (key === 'title' ? 2 : 6),
        `Missing Chinese ${key}`,
      );
      if (key !== 'formula') assert.match(entry.zh[key], /[\u4e00-\u9fff]/);
    }
    assert.equal(
      entry.en.formula,
      entry.zh.formula,
      'Language must not change a formula',
    );
    assert.deepEqual(
      entry.zh.formula.match(/\d+/g),
      entry.en.formula.match(/\d+/g),
    );
  }
});

test('methodology copy captures implementation-specific boundaries in both languages', () => {
  assert.match(metricHelp.sharpe.en.method, /geometric/);
  assert.match(metricHelp.sharpe.zh.method, /几何/);
  assert.match(metricHelp.var.en.method, /linear interpolation/);
  assert.match(metricHelp.var.zh.method, /线性插值/);
  assert.match(metricHelp.cvar.en.formula, /≤ q/);
  assert.match(metricHelp.drawdown.en.formula, /max\(1,/);
  assert.match(metricHelp.beta.en.formula, /1 \/ 252/);
  assert.match(metricHelp['risk-contribution'].en.limitations, /zeros/);
  assert.match(metricHelp['risk-contribution'].zh.limitations, /全零/);
  assert.match(
    metricHelp['effective-positions'].en.limitations,
    /correlations/,
  );
  assert.match(metricHelp['effective-positions'].zh.limitations, /相关性/);
});

test('both languages include accessible controls and all four reading sections', () => {
  for (const locale of ['en', 'zh']) {
    for (const key of [
      'open',
      'close',
      'definition',
      'calculation',
      'reading',
      'limitations',
      'footer',
    ])
      assert.ok(metricHelpLabels[locale][key]);
  }
});
