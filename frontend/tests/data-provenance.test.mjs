import assert from 'node:assert/strict';
import test from 'node:test';
import {
  fetchedAtUtc,
  provenanceCopy,
  provenanceView,
} from '../lib/data-provenance.ts';

const quality = {
  source: 'Yahoo Finance',
  observations: 69,
  start_date: '2025-01-03',
  end_date: '2025-04-09',
  requested_lookback_years: 3,
  warnings: [],
};
const provenance = {
  data_type: 'historical',
  fetched_at: '2025-04-10T12:00:00Z',
  cache_hit: false,
  cache_ttl_seconds: 900,
  price_basis: 'adjusted_close',
  price_start_date: '2025-01-02',
  price_end_date: '2025-04-09',
  raw_price_rows: 70,
  aligned_price_rows: 70,
  dropped_price_rows: 0,
  forward_fill_limit: 3,
  assets: [
    {
      ticker: 'SPY',
      observed_prices: 70,
      missing_prices: 0,
      filled_prices: 0,
      first_observed_date: '2025-01-02',
      last_observed_date: '2025-04-09',
    },
  ],
};

test('legacy APIs never imply a fresh download or gap-free data', () => {
  const view = provenanceView(quality);
  assert.equal(view.fetchedAt, null);
  assert.equal(view.cache, 'unknown');
  assert.equal(view.hasGaps, null);
  assert.equal(view.asOf, quality.end_date);
});

test('demo data never claims a fetch time or a cache hit', () => {
  for (const view of [
    provenanceView({ ...quality, provenance }, true),
    provenanceView({
      ...quality,
      provenance: { ...provenance, data_type: 'synthetic' },
    }),
  ]) {
    assert.equal(view.synthetic, true);
    assert.equal(view.fetchedAt, null);
    assert.equal(view.cache, 'not-applicable');
    assert.equal(view.metadata, null);
  }
});

test('cache hits preserve provider time and missing rows stay visible', () => {
  const fresh = provenanceView({ ...quality, provenance });
  const cached = provenanceView({
    ...quality,
    provenance: { ...provenance, cache_hit: true, dropped_price_rows: 2 },
  });
  assert.equal(fresh.cache, 'miss');
  assert.equal(cached.cache, 'hit');
  assert.equal(cached.fetchedAt, fresh.fetchedAt);
  assert.equal(fresh.hasGaps, false);
  assert.equal(cached.hasGaps, true);
  assert.equal(
    provenanceView({
      ...quality,
      provenance: {
        ...provenance,
        assets: [
          { ...provenance.assets[0], missing_prices: 1, filled_prices: 1 },
        ],
      },
    }).hasGaps,
    true,
  );
});

test('timestamps are explicit UTC; missing, ambiguous and malformed values remain unknown', () => {
  assert.equal(
    fetchedAtUtc('2025-04-10T08:00:00-04:00'),
    '2025-04-10 12:00:00 UTC',
  );
  for (const value of [
    null,
    undefined,
    '',
    'invalid',
    '2025-04-10',
    '2025-04-10T08:00:00',
  ])
    assert.equal(fetchedAtUtc(value), null);
});

test('all provenance labels and cautions have both English and Chinese copy', () => {
  assert.deepEqual(
    Object.keys(provenanceCopy.en).sort(),
    Object.keys(provenanceCopy.zh).sort(),
  );
  for (const text of Object.values(provenanceCopy.zh))
    assert.match(text, /[\u4e00-\u9fff]/);
});
