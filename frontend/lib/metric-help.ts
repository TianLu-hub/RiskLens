/** Reviewed against backend/app/risk. Educational copy only; no calculations or API calls. */
export type MetricHelpId =
  | 'annual-return'
  | 'volatility'
  | 'sharpe'
  | 'var'
  | 'cvar'
  | 'drawdown'
  | 'beta'
  | 'risk-contribution'
  | 'effective-positions';
export type MetricExplanation = {
  title: string;
  definition: string;
  formula: string;
  method: string;
  interpretation: string;
  limitations: string;
};
type BilingualExplanation = {
  en: MetricExplanation;
  zh: MetricExplanation;
  source: string;
};

export const metricHelp = {
  'annual-return': {
    source: 'backend/app/risk/metrics.py',
    en: {
      title: 'Annualized return',
      definition:
        'The compounded return of the selected historical portfolio sample, expressed as an annual rate.',
      formula: 'rₚ,ₜ = Σᵢ wᵢ rᵢ,ₜ\nRₐₙₙ = [Πₜ(1 + rₚ,ₜ)]^(252 / T) − 1',
      method:
        'Daily simple returns use aligned adjusted prices. T is the number of daily returns; the same input weights are applied each day. Annualization assumes 252 trading days.',
      interpretation:
        'This describes the growth rate of the selected sample, not a forecast or an arithmetic average of daily returns.',
      limitations:
        'Sensitive to the start and end dates. Constant daily weights imply rebalancing; overview returns exclude trading costs and do not represent buy-and-hold weight drift.',
    },
    zh: {
      title: '年化收益率',
      definition: '将所选历史样本中组合的复合收益，换算为一年的增长率。',
      formula: 'rₚ,ₜ = Σᵢ wᵢ rᵢ,ₜ\nRₐₙₙ = [Πₜ(1 + rₚ,ₜ)]^(252 / T) − 1',
      method:
        '使用对齐的复权价格计算日简单收益。T 为日收益观测数量，每天使用相同的输入权重，并按每年 252 个交易日年化。',
      interpretation:
        '它描述所选历史样本的复合增长速度，不是未来预测，也不是日收益的算术平均值。',
      limitations:
        '对样本起止日期敏感。每日固定权重隐含再平衡；总览收益不计交易成本，也不模拟买入持有后的权重漂移。',
    },
  },
  volatility: {
    source: 'backend/app/risk/metrics.py',
    en: {
      title: 'Annualized volatility',
      definition:
        'The estimated annual scale of portfolio return fluctuations, including both gains and losses.',
      formula: 'Σₐₙₙ = 252 × Cov(r)\nσₚ = √(wᵀ Σₐₙₙ w)',
      method:
        'The backend uses the sample covariance of aligned asset daily returns (N − 1 denominator), then applies the portfolio weights.',
      interpretation:
        'Higher volatility means larger historical fluctuations. It is neither the probability of a loss nor a maximum-loss estimate.',
      limitations:
        'Covariances change over time. Scaling daily covariance by 252 assumes a stable variance structure and does not capture serial dependence or tail behavior fully.',
    },
    zh: {
      title: '年化波动率',
      definition: '估计组合收益在一年尺度上的波动程度，包含上涨和下跌。',
      formula: 'Σₐₙₙ = 252 × Cov(r)\nσₚ = √(wᵀ Σₐₙₙ w)',
      method:
        '后端使用对齐资产日收益的样本协方差（分母为 N − 1），年化后结合持仓权重计算。',
      interpretation:
        '数值越高，表示历史收益波动越大；它不是亏损概率，也不是最大亏损估计。',
      limitations:
        '协方差会随时间变化。日协方差乘以 252 的年化方式依赖稳定的方差结构，不能完整描述序列相关和尾部行为。',
    },
  },
  sharpe: {
    source: 'backend/app/risk/metrics.py',
    en: {
      title: 'Sharpe ratio estimate',
      definition:
        'Historical return above the configured risk-free rate, per unit of annualized portfolio volatility.',
      formula: 'Sharpe = (Rₐₙₙ − Rf) / σₚ',
      method:
        'RiskLens uses geometric annualized return, the annual risk-free rate in the portfolio controls, and annualized volatility. It returns unavailable when volatility is effectively zero.',
      interpretation:
        'Compare portfolios over the same sample and assumptions. A higher estimate means more historical excess return per unit of volatility.',
      limitations:
        'This geometric-return convention differs from Sharpe estimates based on arithmetic mean excess returns. It penalizes upside and downside volatility alike and does not fully describe tail risk.',
    },
    zh: {
      title: '夏普比率估计',
      definition:
        '每承担一单位年化波动，历史收益相对设定无风险利率的超额部分。',
      formula: 'Sharpe = (Rₐₙₙ − Rf) / σₚ',
      method:
        'RiskLens 使用几何年化收益、组合设置中的年无风险利率和年化波动率。波动率接近零时返回不可用。',
      interpretation:
        '应在相同样本和假设下比较组合。数值较高表示单位波动对应的历史超额收益较高。',
      limitations:
        '此处的几何收益口径不同于基于算术平均超额收益的夏普估计。它同等计入上涨和下跌波动，无法完整描述尾部风险。',
    },
  },
  var: {
    source: 'backend/app/risk/var.py',
    en: {
      title: 'Historical 95% one-day VaR',
      definition:
        'A historical daily-loss threshold based on the lower tail of portfolio returns.',
      formula: 'q = Quantile₀.₀₅(rₚ)\nVaR₉₅ = −q',
      method:
        'The overview uses 95% confidence and a one-trading-day horizon. pandas computes the 5th percentile with linear interpolation; its sign is reversed for loss-based display.',
      interpretation:
        'Approximately 5% of sample days have losses greater than the displayed VaR (returns below q); ties and interpolation affect the exact count. VaR is not the largest possible loss.',
      limitations:
        'The past may omit future crises. VaR does not describe how severe losses beyond the threshold can be. If the return quantile is positive, the signed VaR is negative; it is not clipped to zero.',
    },
    zh: {
      title: '历史 95% 单日 VaR',
      definition: '根据组合日收益的下尾分位数，衡量历史单日损失阈值。',
      formula: 'q = Quantile₀.₀₅(rₚ)\nVaR₉₅ = −q',
      method:
        '总览采用 95% 置信水平、一个交易日的期限。pandas 以线性插值计算第 5 百分位收益，取相反数后按损失口径展示。',
      interpretation:
        '样本中约 5% 的交易日损失大于显示的 VaR（收益低于 q）；重复值和插值会影响实际比例。VaR 不是最大可能亏损。',
      limitations:
        '历史样本可能不包含未来危机；VaR 也不描述超过阈值后的损失有多大。若收益分位数为正，VaR 会为负，后端不会将其截断为零。',
    },
  },
  cvar: {
    source: 'backend/app/risk/var.py',
    en: {
      title: 'Historical 95% one-day CVaR',
      definition:
        'The average loss among sample days whose returns are at or below the VaR return quantile; also called expected shortfall.',
      formula: 'q = Quantile₀.₀₅(rₚ)\nCVaR₉₅ = −Mean(rₚ | rₚ ≤ q)',
      method:
        'Uses the same daily return sample and percentile as VaR. All observed returns at or below q are included, including ties; it is not an average of exactly 5% of observations in every sample.',
      interpretation:
        'Describes the average severity of the historical tail, not a worst-case loss or a guaranteed future bound.',
      limitations:
        'Tail samples can be small and sensitive to individual extreme days. Unobserved crises are absent. The sign is preserved rather than clipped to a nonnegative loss.',
    },
    zh: {
      title: '历史 95% 单日 CVaR',
      definition:
        '对收益低于或等于 VaR 收益分位点的样本日，计算平均损失，也称预期尾部损失。',
      formula: 'q = Quantile₀.₀₅(rₚ)\nCVaR₉₅ = −Mean(rₚ | rₚ ≤ q)',
      method:
        '与 VaR 使用同一日收益样本和分位点。纳入所有低于或等于 q 的观测（包括重复值），因此不一定恰好取 5% 的样本。',
      interpretation:
        '反映历史尾部损失的平均程度，不是最坏情况，也不是未来损失的保证上限。',
      limitations:
        '尾部观测可能较少，容易受个别极端交易日影响，也不包含历史未出现的危机。结果保留符号，不强制截断为非负损失。',
    },
  },
  drawdown: {
    source: 'backend/app/risk/drawdown.py',
    en: {
      title: 'Maximum drawdown',
      definition:
        'The largest observed decline from a previous portfolio wealth peak within the selected sample.',
      formula:
        'Vₜ = Πₛ≤ₜ(1 + rₚ,ₛ)\nMₜ = max(1, V₁, …, Vₜ)\nMDD = minₜ(Vₜ / Mₜ − 1)',
      method:
        'Wealth starts at one. The initial value is included as a possible peak, so a loss on the first day counts. The displayed drawdown is zero or negative.',
      interpretation:
        'More negative values indicate a deeper historical peak-to-trough decline. This is a path-dependent measure, unlike volatility.',
      limitations:
        'Limited to the selected history and daily observations; intraday losses and peaks before the sample are excluded. It does not predict future maximum losses or recovery times.',
    },
    zh: {
      title: '最大回撤',
      definition: '在所选样本内，组合净值相对此前高点出现的最大跌幅。',
      formula:
        'Vₜ = Πₛ≤ₜ(1 + rₚ,ₛ)\nMₜ = max(1, V₁, …, Vₜ)\nMDD = minₜ(Vₜ / Mₜ − 1)',
      method:
        '初始净值设为 1，并计入历史高点，因此首日亏损也会被计算。回撤以零或负数展示。',
      interpretation:
        '数值越负，表示历史峰谷跌幅越深。与波动率不同，回撤依赖收益发生的顺序。',
      limitations:
        '仅覆盖所选区间的日度观测，不包括日内跌幅或区间之前的高点；不能预测未来最大亏损或恢复时间。',
    },
  },
  beta: {
    source: 'backend/app/risk/factors.py',
    en: {
      title: 'Market beta (SPY)',
      definition:
        'The historical sensitivity of portfolio excess returns to SPY excess returns, estimated by a regression with an intercept.',
      formula:
        'rf,d = (1 + Rf)^(1 / 252) − 1\nx = rSPY − rf,d; y = rₚ − rf,d\nβ = Cov(y, x) / Var(x)',
      method:
        'Portfolio and SPY returns are aligned by date. The configured annual risk-free rate is converted geometrically to a daily rate. Rolling beta repeats the covariance/variance estimate over the displayed trailing window.',
      interpretation:
        'A beta near one indicates similar historical market sensitivity; above one indicates greater sensitivity. It is not a correlation coefficient or a guaranteed response to a market move.',
      limitations:
        'SPY is a proxy, not every market risk factor. Beta can change with the sample and market regime. Fewer than three aligned observations or effectively zero benchmark variance makes the estimate unavailable.',
    },
    zh: {
      title: '市场 Beta（SPY）',
      definition:
        '通过含截距的回归，估计组合超额收益对 SPY 超额收益的历史敏感度。',
      formula:
        'rf,d = (1 + Rf)^(1 / 252) − 1\nx = rSPY − rf,d; y = rₚ − rf,d\nβ = Cov(y, x) / Var(x)',
      method:
        '先按日期对齐组合与 SPY 收益，将设定的年无风险利率按几何方式换算为日利率。滚动 Beta 在界面标注的历史窗口内重复计算协方差与方差之比。',
      interpretation:
        '接近 1 表示历史市场敏感度相近，大于 1 表示敏感度更高。Beta 不是相关系数，也不保证组合对未来市场变化作出同等反应。',
      limitations:
        'SPY 只是市场代理，不能覆盖全部风险因子。Beta 会随样本和市场状态变化；对齐观测少于 3 条或基准方差接近零时不可用。',
    },
  },
  'risk-contribution': {
    source: 'backend/app/risk/contribution.py',
    en: {
      title: 'Volatility risk contribution',
      definition:
        'Each holding’s share of total portfolio volatility under the sample covariance model.',
      formula: 'σₚ² = wᵀ Σₐₙₙ w\nPCRᵢ = wᵢ(Σₐₙₙw)ᵢ / σₚ²',
      method:
        'Euler decomposition combines weights, each asset’s volatility, and its covariances with other holdings. Contributions sum to one when portfolio volatility is nonzero.',
      interpretation:
        'Risk share can differ substantially from capital weight. A negative contribution means an asset offsets volatility in this sample; it is not a negative holding or short position.',
      limitations:
        'This is volatility attribution, not loss attribution or causal explanation. It relies on estimated covariances. For effectively zero portfolio volatility, the implementation returns zeros rather than meaningful percentage shares.',
    },
    zh: {
      title: '波动率风险贡献',
      definition: '在样本协方差模型下，每项持仓对组合总波动率的贡献比例。',
      formula: 'σₚ² = wᵀ Σₐₙₙ w\nPCRᵢ = wᵢ(Σₐₙₙw)ᵢ / σₚ²',
      method:
        'Euler 分解结合权重、资产自身波动及其与其他资产的协方差。组合波动非零时，风险贡献比例之和为 1。',
      interpretation:
        '风险占比可能明显不同于资金权重。负贡献表示该资产在当前样本中抵消部分组合波动，不表示负持仓或做空。',
      limitations:
        '这是波动归因，不是亏损归因或因果解释，且依赖估计的协方差。组合波动接近零时，后端返回全零，而不是有意义的百分比份额。',
    },
  },
  'effective-positions': {
    source: 'backend/app/risk/concentration.py',
    en: {
      title: 'Effective number of positions',
      definition:
        'The number of equally weighted holdings that would have the same weight concentration as this long-only, fully invested portfolio.',
      formula: 'HHI = Σᵢ wᵢ²\nNₑff = 1 / HHI',
      method:
        'Uses portfolio weights only. Equal weights give an effective count equal to the nominal holding count; unequal weights reduce it.',
      interpretation:
        'A smaller effective count indicates that capital is concentrated in fewer positions. It need not be a whole number.',
      limitations:
        'It ignores correlations, volatility, sectors, and overlapping ETF holdings. A large effective count does not prove that the portfolio has diversified risk.',
    },
    zh: {
      title: '有效持仓数量',
      definition: '与当前仅做多、满仓组合具有相同权重集中度的等权持仓数量。',
      formula: 'HHI = Σᵢ wᵢ²\nNₑff = 1 / HHI',
      method:
        '仅使用持仓权重计算。等权时，有效数量等于名义持仓数量；权重越不均等，有效数量越低。',
      interpretation:
        '有效数量越小，表示资金越集中于少数持仓。该数值不一定是整数。',
      limitations:
        '不考虑相关性、波动率、行业或 ETF 持仓重叠。有效数量高，不等于组合风险已经充分分散。',
    },
  },
} satisfies Record<MetricHelpId, BilingualExplanation>;

export const metricHelpLabels = {
  en: {
    open: 'Explain',
    close: 'Close explanation',
    definition: 'Definition',
    calculation: 'Calculation',
    reading: 'How to read it',
    limitations: 'Limitations',
    footer: 'Historical methodology · not a forecast or investment advice',
  },
  zh: {
    open: '解释',
    close: '关闭指标说明',
    definition: '含义',
    calculation: '计算方法',
    reading: '如何阅读',
    limitations: '局限',
    footer: '历史方法说明 · 非预测或投资建议',
  },
};
