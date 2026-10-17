import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import test from 'node:test';
import ts from 'typescript';
import {
  parseLocale,
  translate,
  zhMessages,
  LANGUAGE_STORAGE_KEY,
} from '../lib/translations.ts';

test('locale parsing is explicit, stable, and separate from portfolio storage', () => {
  assert.equal(parseLocale('zh'), 'zh');
  for (const value of [null, '', 'fr', 'ZH', 'en'])
    assert.equal(parseLocale(value), 'en');
  assert.equal(LANGUAGE_STORAGE_KEY, 'risklens.language.v1');
});

test('Chinese labels preserve financial acronyms and interpolate without arithmetic', () => {
  assert.equal(translate('zh', '95% 1-day VaR'), '95% 单日 VaR');
  assert.equal(
    translate('zh', '{ticker} weight percent', { ticker: 'NVDA' }),
    'NVDA 权重百分比',
  );
  assert.equal(
    translate('zh', 'of {count} nominal', { count: 5 }),
    '名义持仓 5 项',
  );
  assert.equal(
    translate('en', 'of {count} nominal', { count: 5 }),
    'of 5 nominal',
  );
  assert.equal(translate('zh', 'TLT duration assumption'), 'TLT 久期假设');
  assert.equal(translate('zh', '16.0 years'), '16.0 年');
  assert.equal(
    translate('zh', 'Maximum pairwise correlation is 0.81.'),
    '最高资产对相关系数为 0.81。',
  );
});

test('unknown server messages, tickers, financial numbers, and English remain unchanged', () => {
  for (const text of [
    'NVDA',
    '-21.325%',
    '$78,675',
    '2026-10-16',
    'New backend warning: 3.14159',
    '__proto__',
  ]) {
    assert.equal(translate('zh', text), text);
    assert.equal(translate('en', text), text);
  }
  for (const key of Object.keys(zhMessages))
    assert.equal(translate('en', key), key);
});

test('every literal UI translation call has a Chinese catalog entry', () => {
  const keys = new Set(Object.keys(zhMessages).map((key) => key.toLowerCase()));
  const missing = [];
  const directory = new URL('../components/', import.meta.url);
  for (const file of readdirSync(directory).filter((name) =>
    name.endsWith('.tsx'),
  )) {
    const source = ts.createSourceFile(
      file,
      readFileSync(new URL(file, directory), 'utf8'),
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const visit = (node) => {
      if (
        ts.isCallExpression(node) &&
        node.expression.getText(source) === 't' &&
        node.arguments[0] &&
        ts.isStringLiteral(node.arguments[0])
      ) {
        const key = node.arguments[0].text.replace(/\s+/g, ' ').trim();
        if (!keys.has(key.toLowerCase())) missing.push(`${file}: ${key}`);
      }
      ts.forEachChild(node, visit);
    };
    visit(source);
  }
  assert.deepEqual(missing, []);
});
