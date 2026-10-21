import type { PortfolioAnalysis, PositionInput } from './types';
import type { KupiecTestResult } from './kupiec';

export type VarBacktestRequest = {
  positions: PositionInput[];
  lookback_years: number;
  confidence_level: number;
  window_days: number;
};

export type VarBacktestPoint = {
  date: string;
  training_start: string;
  training_end: string;
  var_loss: number;
  realized_return: number;
  realized_loss: number;
  breach: boolean;
};

export type VarBacktestResponse = {
  method: 'historical_simulation';
  confidence_level: number;
  window_days: number;
  forecast_horizon_days: 1;
  test_observations: number;
  breach_count: number;
  expected_breach_count: number;
  breach_rate: number;
  expected_breach_rate: number;
  kupiec_test?: KupiecTestResult | null;
  test_start: string;
  test_end: string;
  series: VarBacktestPoint[];
  data_quality: PortfolioAnalysis['data_quality'];
  methodology: string;
  limitations: string[];
};

/** Normalize identifiers, not weights. Capital is irrelevant to return-based VaR. */
export function varBacktestRequest(
  positions: PositionInput[],
  lookbackYears: number,
  windowDays: number,
  confidenceLevel: number,
): VarBacktestRequest {
  return {
    positions: positions.map(({ ticker, weight }) => ({
      ticker: ticker.trim().toUpperCase(),
      weight,
    })),
    lookback_years: lookbackYears,
    window_days: windowDays,
    confidence_level: confidenceLevel,
  };
}

/** A response belongs only to these exact model inputs, never to the newest form. */
export function varBacktestKey(request: VarBacktestRequest): string {
  return JSON.stringify(request);
}

export type VarInputIssue = 'positions' | 'weights' | 'parameters';

export function validateVarBacktestInput(
  request: VarBacktestRequest,
): VarInputIssue | null {
  const { positions, lookback_years, window_days, confidence_level } = request;
  const tickers = positions.map(({ ticker }) => ticker);
  if (
    positions.length < 1 ||
    positions.length > 50 ||
    tickers.some((ticker) => !/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(ticker)) ||
    new Set(tickers).size !== tickers.length
  )
    return 'positions';
  if (
    positions.some(
      ({ weight }) => !Number.isFinite(weight) || weight < 0 || weight > 1,
    ) ||
    Math.abs(positions.reduce((sum, { weight }) => sum + weight, 0) - 1) > 1e-4
  )
    return 'weights';
  if (
    !Number.isInteger(lookback_years) ||
    lookback_years < 1 ||
    lookback_years > 10 ||
    !Number.isInteger(window_days) ||
    window_days < 60 ||
    window_days > 1260 ||
    !Number.isFinite(confidence_level) ||
    confidence_level < 0.9 ||
    confidence_level > 0.999
  )
    return 'parameters';
  return null;
}

/** Presentation only: use backend breach flags; do not recalculate decisions in JS. */
export function varBreachRows(result: VarBacktestResponse): VarBacktestPoint[] {
  return result.series.filter((point) => point.breach);
}

/** Translate known backend notices while preserving their supplied counts. */
export function localizeVarNotice(
  message: string,
  locale: 'en' | 'zh',
): string {
  if (locale === 'en') return message;
  const smallSample = message.match(
    /^Only (\d+) out-of-sample returns are available \(fewer than 252 trading days\); the observed breach rate may be unstable\.$/,
  );
  if (smallSample)
    return `仅有 ${smallSample[1]} 条样本外收益（不足 252 个交易日），观察到的突破率可能不稳定。`;
  const sparseTail = message.match(
    /^The nominal expected breach count is ([\d.]+), below 5; this sample provides limited evidence about tail coverage\.$/,
  );
  if (sparseTail)
    return `名义预期突破次数为 ${sparseTail[1]}，少于 5 次；该样本对尾部风险覆盖的验证能力有限。`;
  return message;
}

export const varBacktestCopy = {
  en: {
    title: 'VaR model backtest',
    badge: 'OUT-OF-SAMPLE VALIDATION',
    subtitle:
      'Estimate each daily loss threshold using only earlier returns, then compare with the following day.',
    controls: 'VaR backtest settings',
    method: 'Historical simulation · 1-day horizon',
    confidence: 'Confidence level',
    window: 'Rolling training window',
    tradingDays: 'trading days',
    years: 'years',
    history: 'History selected in Portfolio',
    historyNote:
      'Uses the current holdings and weights. Select a longer history in the portfolio panel if there are not enough training and test observations.',
    run: 'Run VaR backtest',
    loading: 'Validating historical VaR…',
    empty: 'How often did losses exceed the estimate?',
    emptyNote:
      'Run a rolling test on historical daily prices. No demonstration results are shown here, and no AI service is required.',
    stale:
      'Inputs changed. Run again to validate the current portfolio and settings. Previous results are not shown as current.',
    failed: 'VaR backtest unavailable',
    error:
      'The backtest could not be completed. Check the service and try again.',
    unavailable:
      'The Python service could not be reached. Check the backend connection and try again.',
    insufficient:
      'There is not enough aligned history for this training window and at least 20 test days. Select a longer history or a shorter rolling window.',
    invalidTicker:
      'A ticker has no usable history. Check the symbols and try again.',
    positions: 'Enter 1–50 unique, valid tickers in the portfolio panel.',
    weights:
      'Weights must be finite, nonnegative, and total 100%. Update or normalize the portfolio weights.',
    parameters:
      'Check the selected history, training window, and confidence level.',
    details: 'Service details',
    observed: 'Observed breaches',
    expected: 'Nominal expected count',
    observedRate: 'Observed breach rate',
    expectedRate: 'Nominal expected rate',
    testSample: 'Out-of-sample days',
    testDates: 'Evaluation period',
    expectedNote:
      'Nominal expectations are reference values, not a pass/fail test or a guarantee.',
    chart: 'Daily loss vs. prior-window VaR',
    var: '1-day VaR threshold',
    loss: 'Realized daily loss',
    breach: 'VaR breach',
    sign: 'Positive values are losses; negative values are gains. Signed VaR is retained, even when negative. A breach means loss > VaR, not loss = VaR.',
    noBreaches:
      'No breaches were observed in this test sample. This does not establish that the model is safe.',
    breachTable: 'Breach-day audit trail',
    date: 'Test date',
    training: 'Prior training dates',
    showAll: 'Show all breach days',
    showLess: 'Show fewer breach days',
    tableNote:
      'The table shows only days marked as breaches by Python. Each training period ends before its test date.',
    provenance:
      'The source sample below includes training and testing. Out-of-sample days above count only evaluated forecasts.',
    methodology: 'Method & limitations',
    methodNote:
      'Python uses the negative lower-tail sample quantile with linear interpolation. Each rolling window excludes the day being tested. The risk-free rate is not used.',
    assumption:
      'Hypothetical fixed-weight portfolio, rebalanced daily; not your account’s realized trading history.',
    limitations: [
      'Historical validation does not guarantee future risk coverage or performance.',
      'Today’s choice of holdings can introduce hindsight and survivorship bias.',
      'Trading costs, taxes, spreads, slippage, and market impact are excluded.',
      'Overlapping windows and dependent returns limit breach-count interpretation. Kupiec tests overall frequency only; it does not establish independence or guarantee future coverage.',
      'Kupiec p-values use an asymptotic chi-square approximation. Small expected counts, boundary outcomes, and dependent returns can make that approximation unreliable.',
      'Historical quantiles have limited tail resolution, especially at high confidence levels, and can miss losses beyond the observed sample.',
    ],
    notices: 'Sample cautions',
  },
  zh: {
    title: 'VaR 风险模型回测',
    badge: '样本外验证',
    subtitle:
      '每天仅使用此前收益估计单日损失阈值，再与下一交易日的实际收益比较。',
    controls: 'VaR 回测设置',
    method: '历史模拟法 · 单日预测期',
    confidence: '置信水平',
    window: '滚动训练窗口',
    tradingDays: '个交易日',
    years: '年',
    history: '组合面板选择的历史区间',
    historyNote:
      '使用当前持仓和权重。若训练及测试样本不足，请在组合面板选择更长的历史区间。',
    run: '运行 VaR 回测',
    loading: '正在验证历史 VaR…',
    empty: '历史损失有多少次超过了估计阈值？',
    emptyNote:
      '使用历史日度行情运行滚动验证。这里不展示演示结果，也不需要调用 AI 服务。',
    stale:
      '输入已改变。请重新运行以验证当前组合及参数；之前的结果不会被当作当前结果展示。',
    failed: 'VaR 回测暂不可用',
    error: '回测未能完成，请检查服务后重试。',
    unavailable: '无法连接 Python 服务，请检查后端连接后重试。',
    insufficient:
      '对齐后的历史样本不足，无法满足训练窗口及至少 20 个测试日。请选择更长的历史区间或更短的滚动窗口。',
    invalidTicker: '某个代码没有可用行情，请检查证券代码后重试。',
    positions: '请在组合面板输入 1–50 个不重复、格式正确的证券代码。',
    weights: '权重必须是有效非负数且合计 100%，请修改或归一化组合权重。',
    parameters: '请检查历史区间、训练窗口和置信水平。',
    details: '查看服务详情',
    observed: '实际突破次数',
    expected: '名义预期突破次数',
    observedRate: '实际突破比例',
    expectedRate: '名义预期突破比例',
    testSample: '样本外测试天数',
    testDates: '评估区间',
    expectedNote: '名义预期值仅供比较，不是通过／不通过标准，也不是风险保证。',
    chart: '日损失与此前窗口估计的 VaR',
    var: '单日 VaR 阈值',
    loss: '实际日损失',
    breach: 'VaR 突破',
    sign: '正值表示损失，负值表示盈利。VaR 保留原始符号，也可能为负。突破定义为损失 > VaR；恰好等于阈值不算突破。',
    noBreaches: '本次测试样本没有观察到突破，这并不能证明模型安全。',
    breachTable: '突破日期审计表',
    date: '测试日期',
    training: '此前训练区间',
    showAll: '显示全部突破日期',
    showLess: '收起突破日期',
    tableNote:
      '仅列出 Python 标记为突破的日期；每个训练区间均在对应测试日之前结束。',
    provenance:
      '下方数据来源样本包含训练期和测试期；上方样本外天数仅统计实际评估的预测日。',
    methodology: '计算方法与局限',
    methodNote:
      'Python 对样本的下尾分位数取负，采用线性插值。每个滚动窗口均排除待测试日；计算不使用无风险利率。',
    assumption:
      '假设权重固定、每日再平衡的组合，不代表你账户真实发生的交易历史。',
    limitations: [
      '历史验证不保证未来风险覆盖程度或投资表现。',
      '以今天选择的证券回看历史，可能包含事后选择或幸存者偏差。',
      '未计入交易成本、税费、买卖价差、滑点或市场冲击。',
      '重叠训练窗口及收益间的依赖性会限制突破次数的解释。Kupiec 仅检验总体频率，不证明突破相互独立，也不保证未来风险覆盖。',
      'Kupiec p 值采用渐近卡方近似。预期次数较少、边界结果及收益间的依赖性都可能使该近似不可靠。',
      '历史分位数的尾部信息有限，尤其在高置信水平下，可能遗漏超出已有样本的极端损失。',
    ],
    notices: '样本提示',
  },
} as const;
