import type { PortfolioAnalysis } from './types';

export type DataQuality = PortfolioAnalysis['data_quality'];

/** Format only provider timestamps. Never replace missing timestamps with Date.now(). */
export function fetchedAtUtc(value?: string | null): string | null {
  if (!value || !/(Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? null
    : date
        .toISOString()
        .replace('T', ' ')
        .replace(/\.\d{3}Z$/, ' UTC');
}

export function provenanceView(quality: DataQuality, demo = false) {
  const synthetic = demo || quality.provenance?.data_type === 'synthetic';
  // A bundled demo never acquires a network-fetch time or a cache badge.
  const metadata = synthetic ? null : quality.provenance;
  return {
    synthetic,
    metadata,
    fetchedAt: fetchedAtUtc(metadata?.fetched_at),
    asOf: metadata?.price_end_date ?? quality.end_date,
    cache: synthetic
      ? 'not-applicable'
      : metadata == null
        ? 'unknown'
        : metadata.cache_hit
          ? 'hit'
          : 'miss',
    hasGaps:
      metadata == null
        ? null
        : metadata.dropped_price_rows > 0 ||
          metadata.assets.some((asset) => asset.missing_prices > 0),
  };
}

/** Stable bilingual copy; data, counts and dates are never translated or invented. */
export const provenanceCopy = {
  en: {
    title: 'Data source & sample',
    historical: 'Historical daily prices',
    demo: 'Synthetic demo',
    asOf: 'Prices through',
    demoAsOf: 'Demo sample through',
    fetched: 'Fetched from provider',
    sample: 'Actual return sample',
    observations: 'daily returns',
    requested: 'Requested lookback',
    years: 'years',
    cache: 'Backend cache',
    hit: 'Cache hit',
    miss: 'Fetched for this request',
    unknown: 'Not reported by backend',
    na: 'Not applicable',
    ttl: 'Cache TTL',
    seconds: 'seconds',
    cacheNote:
      'A cache hit preserves the original fetch time. Fetch time is not a quote timestamp. No real-time or freshness guarantee.',
    historicalNote:
      'Historical daily data, not streaming quotes. The latest available date may lag the market.',
    demoNote:
      'Fixed synthetic example. These dates are illustrative, not Yahoo Finance quotes. No market-data request was made for this sample.',
    optimization:
      'Historical in-sample comparison · not a forecast or an executed portfolio.',
    backtest:
      'Hypothetical historical simulation · the sample below includes training and testing, not only forward-test days.',
    stress:
      'Hypothetical scenario · results use entered shocks and explicit model assumptions, not observed market losses or forecasts.',
    details: 'Coverage & missing-data details',
    gap: 'Missing prices / alignment adjustments recorded',
    noGap: 'No missing prices detected in returned rows',
    unreported:
      'Missing-data checks were not reported. This does not mean the dataset has no gaps.',
    policy:
      'Missingness is measured only on dates returned by the provider, not against a complete exchange calendar. Short gaps use forward fill; remaining incomplete dates are removed. No backward fill.',
    limit: 'Forward-fill limit (rows)',
    raw: 'Provider price rows',
    aligned: 'Aligned price rows',
    dropped: 'Rows excluded',
    basis: 'Price basis',
    adjusted: 'Adjusted close',
    unadjusted:
      'Unadjusted close fallback — dividend/split treatment may differ',
    ticker: 'Asset',
    observed: 'Observed prices',
    missing: 'Missing before fill',
    filled: 'Filled in retained sample',
    first: 'First observed',
    last: 'Last observed',
    notices: 'Provider / analysis notes',
    scope:
      'Portfolio price sample only. A separately fetched factor benchmark may have a different sample.',
    stressBadge: 'Hypothetical scenario',
    simulationBadge: 'Historical model',
    portfolioBadge: 'Portfolio data',
  },
  zh: {
    title: '数据来源与样本',
    historical: '历史日度行情',
    demo: '合成演示数据',
    asOf: '行情截至（对齐后）',
    demoAsOf: '演示样本截至',
    fetched: '从数据源获取时间',
    sample: '实际收益样本',
    observations: '条日收益',
    requested: '请求回看区间',
    years: '年',
    cache: '后端缓存',
    hit: '命中缓存',
    miss: '本次请求获取',
    unknown: '后端未提供',
    na: '不适用',
    ttl: '缓存有效期',
    seconds: '秒',
    cacheNote:
      '命中缓存保留最初获取时间。获取时间不是行情报价时间，也不保证数据实时或最新。',
    historicalNote:
      '历史日度数据，不是实时行情流；最新可用日期可能落后于市场。',
    demoNote:
      '固定合成示例。日期仅用于演示，不代表 Yahoo Finance 行情；该样本没有对应的行情获取请求。',
    optimization: '历史样本内比较 · 不是预测，也不是实际执行的持仓。',
    backtest:
      '假设性历史模拟 · 下方样本包含训练期和测试期，不仅是样本外测试天数。',
    stress:
      '假设情景 · 结果来自输入的冲击和明确的模型假设，不代表已发生的市场损失，也不是预测。',
    details: '查看覆盖范围与缺失数据',
    gap: '发现缺失价格或对齐调整',
    noGap: '返回的数据行中未发现缺失价格',
    unreported: '后端未提供缺失数据检查信息，不代表数据没有缺口。',
    policy:
      '缺失统计仅针对数据源返回的日期，不等于完整交易所日历核验。短缺口沿用此前价格，仍不完整的日期被剔除；不使用未来价格回填。',
    limit: '前向填充上限（行）',
    raw: '数据源价格行数',
    aligned: '对齐后价格行数',
    dropped: '剔除日期数',
    basis: '价格口径',
    adjusted: '复权收盘价',
    unadjusted: '未复权收盘价兜底 — 分红和拆股处理可能不同',
    ticker: '资产',
    observed: '原始有效价格数',
    missing: '填充前缺失数',
    filled: '保留样本填充数',
    first: '首次有效价格日期',
    last: '最后有效价格日期',
    notices: '数据源／分析提示',
    scope: '此处仅描述组合价格样本；单独获取的因子基准可能使用不同样本。',
    stressBadge: '假设情景',
    simulationBadge: '历史模型',
    portfolioBadge: '组合数据',
  },
};
