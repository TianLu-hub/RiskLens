/** UI translations only. API payloads, tickers, and quantitative values are never translated. */
export type Locale = 'en' | 'zh';
export const LANGUAGE_STORAGE_KEY = 'risklens.language.v1';
export const zhMessages: Record<string, string> = {
  Overview: '总览',
  'Stress tests': '压力测试',
  'Factor exposure': '因子暴露',
  Optimization: '组合优化',
  Backtest: '样本外回测',
  'VaR validation': 'VaR 验证',
  'VaR model backtest': 'VaR 风险模型回测',
  'Compare past-only risk estimates with the next trading day.':
    '只用过去数据估计风险，再与下一交易日的实际收益比较。',
  'MODEL VALIDATION': '模型验证',
  'Risk Officer': '风险官',
  'Portfolio overview': '组合风险总览',
  'Historical risk, in perspective.': '从历史数据理解组合风险。',
  'Stress testing': '压力测试',
  'Explore hypothetical shocks and their portfolio impact.':
    '探索假设冲击对组合的影响。',
  'Understand your historical sensitivity to the market.':
    '了解组合对市场的历史敏感度。',
  'Portfolio optimization': '投资组合优化',
  'Compare allocations without changing your holdings.':
    '比较不同配置，不改动当前持仓。',
  'Walk-forward backtest': '滚动样本外回测',
  'Train on the past. Evaluate on subsequent observations.':
    '用过去的数据训练，在之后的样本上评估。',
  'Ask your Risk Officer': '向风险官提问',
  'Explore the evidence behind your portfolio risks.':
    '了解组合风险背后的数据依据。',
  'Workspace sections': '工作台导航',
  'Skip to analysis': '跳转到分析内容',
  'PORTFOLIO RISK TERMINAL': '投资组合风险终端',
  'Python-computed metrics': 'Python 确定性计算',
  'HISTORICAL DATA': '历史数据',
  'DEMO SNAPSHOT': '演示快照',
  'Portfolio workspace': '投资组合工作区',
  'Portfolio ·': '组合 ·',
  positions: '项持仓',
  Lookback: '回看区间',
  '1 year': '1 年',
  '3 years': '3 年',
  '5 years': '5 年',
  'Risk-free rate': '无风险利率',
  'Holdings stay in this browser.': '持仓保存在当前浏览器。',
  'Analyze to update historical results.': '点击分析以更新历史结果。',
  'Main portfolio / Research workspace': '主组合 / 研究工作台',
  'Demo data.': '演示数据。',
  'The charts below use a fixed synthetic example. Select a portfolio and click Analyze portfolio to load historical prices.':
    '以下图表为固定的合成数据示例。选择组合并点击“分析组合”以加载历史行情。',
  'Inputs changed — analysis needs updating.': '输入已更改，需要重新分析。',
  'The risk charts still show': '风险图表当前仍显示',
  'the demo portfolio': '演示组合',
  'the last analyzed portfolio': '上次分析的组合',
  '. Click Analyze portfolio to refresh them. Stress testing, optimization, and backtesting use your current inputs.':
    '。点击“分析组合”以更新。压力测试、优化和回测使用当前输入。',
  'Analysis unavailable': '暂时无法分析',
  'The labeled demo snapshot remains visible.': '当前保留已标注的演示快照。',
  'The previous historical analysis remains visible.':
    '当前保留上次历史分析结果。',
  'Explore with Risk Officer': '向风险官了解详情',
  'Understand the risks behind these numbers →': '理解这些数字背后的风险 →',
  'Risk Officer needs an updated analysis': '风险官需要最新分析结果',
  'Analyze the current portfolio before asking about its risks.':
    '请先分析当前组合，再向风险官提问。',
  observations: '条观测',
  'Historical analysis · Hypothetical scenarios': '历史分析 · 假设情景',
  'Data note:': '数据说明：',
  'Saved portfolio restored on this device. Analyze it to load historical results.':
    '已恢复本设备保存的组合。点击分析以加载历史结果。',
  'Saved portfolio could not be restored. The default portfolio is shown.':
    '无法恢复已保存的组合，当前显示默认组合。',
  'Browser storage is unavailable. Changes will not persist after reload.':
    '浏览器存储不可用，刷新后将无法保留更改。',
  'Every position needs a ticker.': '每项持仓都需要股票或 ETF 代码。',
  'Each ticker may appear only once.': '同一代码不能重复。',
  'Weights must sum to 100% before analysis.': '分析前，权重之和必须为 100%。',
  'The analysis could not be completed.': '未能完成分析。',
  Portfolio: '投资组合',
  'Select demo portfolio': '选择示例组合',
  'Mega-Cap Tech': '大型科技组合',
  'Balanced 60/40': '60/40 平衡组合',
  'Risk-Off': '防御组合',
  Growth: '成长组合',
  Custom: '自定义',
  Instrument: '资产代码',
  Weight: '权重',
  Position: '新增持仓',
  Normalize: '归一化',
  'Total weight': '总权重',
  Valid: '有效',
  Review: '需检查',
  'Calculating…': '计算中…',
  'Analyze portfolio': '分析组合',
  'Ticker {index}': '资产代码 {index}',
  '{ticker} weight percent': '{ticker} 权重百分比',
  'Remove {ticker}': '移除 {ticker}',
  'Portfolio risk metrics': '组合风险指标',
  'Annualized return': '年化收益率',
  'Geometric · 252-day': '几何年化 · 252 日',
  'Annualized volatility': '年化波动率',
  'Sample covariance': '样本协方差估计',
  'Sharpe ratio': '夏普比率',
  '95% 1-day VaR': '95% 单日 VaR',
  'Historical loss threshold': '历史损失分位阈值',
  '95% 1-day CVaR': '95% 单日 CVaR',
  'Expected shortfall': '预期尾部损失',
  'Max drawdown': '最大回撤',
  'Maximum drawdown': '最大回撤',
  'Historical peak to trough': '历史峰值至谷值',
  'Portfolio performance': '组合历史表现',
  'Growth from the first aligned observation': '从首个对齐观测日起的累计增长',
  'Cumulative return': '累计收益率',
  'Risk contribution': '风险贡献',
  'Portfolio weight vs. share of volatility': '持仓权重与波动风险占比',
  Asset: '资产',
  'Relative scale': '相对比例',
  Wgt: '权重',
  Risk: '风险',
  'Portfolio weight': '持仓权重',
  'Risk share': '风险占比',
  Diversifier: '分散风险贡献',
  Correlation: '相关性',
  'Pearson correlation of aligned daily returns':
    '对齐日收益率的 Pearson 相关系数',
  'Asset correlation matrix': '资产相关性矩阵',
  'Strongest pairs': '最强相关资产对',
  Concentration: '集中度',
  'Position-level diversification measures': '持仓层面的分散化指标',
  'Effective positions': '有效持仓数量',
  'of {count} nominal': '名义持仓 {count} 项',
  'Weight concentration': '权重集中程度',
  'Largest position': '最大单一持仓',
  'Top 3 weight': '前三大持仓权重',
  'Combined exposure': '合计敞口',
  'Rule-based flags': '规则风险提示',
  'Deterministic thresholds · no LLM judgment':
    '确定性阈值触发 · 不依赖模型判断',
  'No Phase 1 thresholds triggered.': '未触发基础风险阈值。',
  'High concentration': '集中度偏高',
  'High correlation': '相关性偏高',
  'Risk dominated by one asset': '单一资产主导风险',
  'Elevated tail risk': '尾部风险偏高',
  'Expected shortfall exceeds 1.5 times historical VaR.':
    '预期尾部损失超过历史 VaR 的 1.5 倍。',
  high: '高',
  medium: '中',
  low: '低',
  'Drawdown analysis': '回撤分析',
  Drawdown: '回撤',
  'Decline from the running wealth high-water mark':
    '相对历史累计净值高点的跌幅',
  Maximum: '最大回撤',
  'PHASE 4 · REGRESSION': '阶段 4 · 回归分析',
  'Daily excess-return regression against the SPY market proxy':
    '以 SPY 为市场代理的日超额收益回归',
  'Factor estimate unavailable': '因子估计暂不可用',
  'The benchmark regression could not be estimated from the aligned history.':
    '无法使用对齐后的历史数据估计基准回归。',
  'Market beta': '市场 Beta',
  'Sensitivity to SPY excess returns': '对 SPY 超额收益的敏感度',
  'Annualized alpha': '年化 Alpha',
  'Historical intercept · not forecast': '历史回归截距 · 非预测',
  'Regression R²': '回归 R²',
  'Variation explained by market proxy': '市场代理解释的收益变动比例',
  'Idiosyncratic vol': '特质波动率',
  'Annualized regression residual': '年化回归残差波动',
  Rolling: '滚动',
  '-day beta': '日 Beta',
  'Rolling market beta': '滚动市场 Beta',
  estimates: '个估计值',
  'More history is required for rolling beta.':
    '滚动 Beta 需要更长的历史数据。',
  'Model scope': '模型范围',
  'Model:': '模型：',
  'SMB / HML:': 'SMB / HML：',
  'Portfolio could not be saved on this device. You can still run analyses.':
    '无法在本设备保存组合，但仍可正常运行分析。',
  'Benchmark:': '基准：',
  'Observations:': '观测数量：',
  'unavailable — no factor series was supplied': '不可用 — 未提供相应因子序列',
  'Historical regression estimate. It describes the selected sample and does not predict future exposure.':
    '这是历史回归估计，仅描述所选样本，不预测未来敞口。',
  'Benchmark source unavailable': '基准数据源不可用',
  Unavailable: '不可用',
  'Not provided': '未提供',
  'Same historical sample': '相同历史样本',
  Current: '当前',
  Optimized: '优化后',
  'Sharpe estimate': '夏普比率估计',
  'PHASE 5 · HISTORICAL': '阶段 5 · 历史估计',
  'Compare an allocation fitted to the selected return history':
    '比较基于所选历史收益拟合的配置',
  'Optimization controls': '优化参数',
  Objective: '优化目标',
  'Minimum volatility': '最小波动率',
  'Maximum Sharpe': '最大夏普比率',
  'Risk parity': '风险平价',
  'Max position weight · optional': '单一持仓上限 · 可选',
  'No cap': '不设上限',
  'Maximum position weight percent': '最大持仓权重百分比',
  'Long-only, fully invested. Minimum feasible cap:':
    '仅做多、满仓配置。可行的最低权重上限：',
  'Comparison only': '仅供比较',
  'This tool never changes your portfolio. Results are in-sample estimates, not forecasts or trade recommendations.':
    '此工具不会更改你的组合。结果为样本内估计，不是预测或交易建议。',
  'Optimization comparison': '优化对比',
  'Optimization unavailable': '暂时无法优化',
  comparison: '对比',
  'aligned daily returns': '条对齐日收益',
  Change: '变动',
  'One-way turnover': '单边换手率',
  'Half the total absolute weight change. Trading costs are excluded.':
    '权重绝对变动之和的一半，不含交易成本。',
  'Run the deterministic solver to compare current and optimized weights on the same historical sample.':
    '运行确定性求解器，在同一历史样本上比较当前与优化后的权重。',
  'Inputs changed': '输入已更改',
  'Awaiting optimization': '等待运行优化',
  'Solving…': '求解中…',
  'Run optimization': '运行优化',
  'Out-of-sample metric': '样本外指标',
  'Current mix': '当前配置',
  'PHASE 6 · OUT-OF-SAMPLE': '阶段 6 · 样本外验证',
  'Train on earlier daily returns; test only on subsequent dates':
    '用较早的日收益训练，仅在之后的日期测试',
  'Backtest controls': '回测参数',
  'Trailing training window': '滚动训练窗口',
  '252 trading days · ~1 year': '252 个交易日 · 约 1 年',
  '504 trading days · ~2 years': '504 个交易日 · 约 2 年',
  'Cost per traded notional · bps': '按交易金额计费 · 基点',
  'Max position weight · optional %': '持仓权重上限 · 可选 %',
  'Rebalanced every 21 trading days (~monthly). Same historical source as portfolio analysis. Default lookback: 3 years; first ~2 years train, remaining ~1 year is tested forward.':
    '每 21 个交易日（约每月）再平衡。与组合分析使用相同历史数据源。默认回看 3 年，前约 2 年用于训练，剩余约 1 年用于向前测试。',
  'Hypothetical historical simulation': '假设性历史模拟',
  'Not live trading, a prediction, or a recommendation. Portfolio selection today may still embed hindsight.':
    '不是实盘交易、预测或投资建议。以今天的资产选择进行回测，仍可能包含事后偏差。',
  'Backtest results': '回测结果',
  'Backtest unavailable': '回测暂不可用',
  'Forward test ·': '向前测试 ·',
  'trading days': '个交易日',
  'daily prices ·': '日价格 ·',
  windows: '个窗口',
  'API RESULT': '后端计算结果',
  'wealth index': '净值指数',
  'Walk-forward optimized': '滚动优化配置',
  'SPY buy-and-hold': 'SPY 买入持有',
  'Wealth index begins at 100. Current mix and optimized strategy both rebalance monthly and pay the same configured cost; SPY is buy-and-hold without costs when SPY is in the portfolio.':
    '净值指数从 100 开始。当前配置与优化策略均按月再平衡，并采用相同交易成本。组合包含 SPY 时，另展示不计交易成本的 SPY 买入持有基准。',
  Inspect: '查看',
  'training / forward windows': '个训练 / 测试窗口',
  'Training ends': '训练截止',
  'Forward test': '向前测试',
  'Optimized turnover': '优化组合换手率',
  'Awaiting walk-forward test': '等待滚动回测',
  'Run the Python engine to separate training dates from later test dates and compare net hypothetical wealth.':
    '运行 Python 引擎，分离训练期和后续测试期，比较扣除成本后的假设净值。',
  'Costs / initial capital': '成本 / 初始资金',
  'Backtesting…': '回测中…',
  'Run backtest': '运行回测',
  'AI Risk Officer': 'AI 风险官',
  'PHASE 3 · ZERO-COST': '阶段 3 · 无外部 AI 费用',
  'Deterministic interpretation and evidence-grounded explanation over Python results':
    '基于 Python 结果，以确定性规则提供有依据的解释',
  'Ask the AI Risk Officer': '向 AI 风险官提问',
  'Officer briefing': '风险问题',
  'No raw prices': '不接收原始价格',
  'Ask for a risk diagnosis, or try: What happens if tech drops 15% and rates rise 100 bps?':
    '询问组合风险，或试试：如果科技股下跌 15%，利率上升 100 个基点会怎样？',
  'Question for the AI Risk Officer': '风险官问题输入框',
  'Scenario portfolio value': '情景组合金额',
  'Numerical control boundary': '数值计算边界',
  'Python rules select the qualitative findings. Evidence values are attached from calculated metrics or explicit scenario inputs. No external AI service is required.':
    'Python 规则筛选定性结论，证据数值来自已计算的指标或明确的情景输入，不需要外部 AI 服务。',
  'Risk Officer unavailable': '风险官暂不可用',
  'Awaiting risk question': '等待风险问题',
  'The officer diagnoses concentration, correlation, volatility contribution, tail risk, and drawdown. It also supports bounded English and Chinese shock phrases; use the structured Stress Testing panel for complex scenarios.':
    '风险官解释集中度、相关性、波动贡献、尾部风险和回撤。支持有限范围的中英文冲击描述；复杂情景请使用结构化压力测试面板。',
  'Parsing supported language · validating context · preparing explanation':
    '解析支持的表述 · 验证上下文 · 准备解释',
  'Engine:': '引擎：',
  'Python stress engine result': 'Python 压力引擎结果',
  'Hypothetical · not a prediction': '假设情景 · 非预测',
  'Estimated return': '估计收益率',
  'Estimated P&L': '估计盈亏',
  Before: '冲击前',
  After: '冲击后',
  'Known limitations': '已知局限',
  'NO BUY / SELL ADVICE': '不提供买卖建议',
  'Applying deterministic rules…': '正在应用确定性规则…',
  'Ask Risk Officer': '询问风险官',
  'HYPOTHETICAL SCENARIO': '假设情景',
  'PORTFOLIO DIAGNOSIS': '组合风险诊断',
  'DETERMINISTIC RULE ENGINE': '确定性规则引擎',
  'OPENAI STRUCTURED OUTPUT': 'OpenAI 结构化输出',
  'Diagnose the dominant risks in this portfolio.': '分析这个组合的主要风险。',
  'What happens if tech drops 15% and rates rise 100 bps?':
    '如果科技股下跌15%，利率上升100个基点会怎样？',
  'Explain the portfolio tail risk and diversification quality.':
    '解释这个组合的尾部风险和分散化程度。',
  'historical statistic': '历史统计',
  'historical statistic result': '历史统计结果',
  'observed historical statistic': '历史观测统计',
  'model assumption': '模型假设',
  'hypothetical scenario result': '假设情景结果',
  'Stress scenario controls': '压力情景参数',
  'Deterministic, linear portfolio shock analysis with disclosed assumptions':
    '基于明确假设的确定性线性组合冲击分析',
  'Scenario inputs': '情景输入',
  'User-defined': '用户定义',
  'Presets are simplified hypothetical stress scenarios. Their names are labels, not exact historical reproductions.':
    '预设是简化的假设压力情景，名称仅作标识，不是对历史事件的精确重现。',
  '2008-style Crisis': '2008 式危机',
  'COVID-style Crash': '疫情式暴跌',
  '2022 Rate Shock': '2022 式利率冲击',
  'Tech Selloff': '科技股抛售',
  'Custom Scenario': '自定义情景',
  'Market shock': '大盘冲击',
  'Tech shock': '科技板块冲击',
  'Rate shock': '利率冲击',
  bps: '基点',
  'Portfolio value': '组合金额（美元）',
  'Ticker-specific total shock': '单一资产总冲击',
  'Overrides factor total': '覆盖因子冲击合计',
  '{ticker} stress percent': '{ticker} 冲击百分比',
  'Inputs changed · run to refresh results': '输入已更改 · 运行以更新结果',
  'Stress test results': '压力测试结果',
  'Stress test unavailable': '压力测试暂不可用',
  'The last deterministic result remains visible.':
    '当前保留上次确定性计算结果。',
  'Historical data used:': '是否使用历史数据：',
  No: '否',
  '· Classification: hypothetical': '· 类型：假设情景',
  'STALE RESULT': '待更新结果',
  'Portfolio before': '冲击前组合价值',
  'Portfolio after': '冲击后组合价值',
  'Asset P&L attribution': '资产盈亏归因',
  'Weight × shocked return': '权重 × 冲击收益率',
  'Asset shock': '资产冲击',
  'Portfolio contrib.': '组合贡献',
  'P&L': '盈亏',
  'Risk-factor attribution': '风险因子归因',
  'Assumptions & provenance': '模型假设与来源',
  'No live factor data': '非实时因子数据',
  'FALLBACK MODELING ASSUMPTION': '兜底建模假设',
  'MODEL METHODOLOGY': '模型方法',
  'Running deterministic engine…': '确定性引擎运行中…',
  'Run stress test': '运行压力测试',
  'Broad market shock': '大盘冲击',
  'Technology shock': '科技板块冲击',
  'Ticker-specific override': '单一资产覆盖调整',
  'Interest-rate duration shock': '利率久期冲击',
  'Scenario classification': '情景分类',
  Hypothetical: '假设情景',
  'This scenario is not a forecast and does not reproduce a historical event.':
    '该情景不是预测，也不是对历史事件的重现。',
  'Shock aggregation method': '冲击汇总方法',
  'Linear and additive': '线性加总',
  'Broad-market, technology, and duration effects are added without second-order, liquidity, volatility, or correlation feedback.':
    '大盘、科技板块和久期效应线性加总，未考虑二阶效应、流动性、波动率或相关性反馈。',
  'Ticker-specific shock treatment': '单一资产冲击处理',
  'Overrides total asset shock': '覆盖资产总冲击',
  "An explicit ticker shock is treated as that asset's total stressed return, not as an additional shock on top of market and sector inputs.":
    '指定资产冲击作为该资产的总压力收益，不再额外叠加市场或板块冲击。',
  'Broad-market exposure assumption': '大盘暴露假设',
  '100% non-bond / 0% mapped bond ETFs': '非债券 100% / 久期表中债券 ETF 0%',
  'The broad-market shock is applied fully to non-bond positions and not applied to ETFs listed in the static duration map.':
    '大盘冲击全额作用于非债券持仓，不作用于静态久期表中的债券 ETF。',
  'Interest-rate method': '利率建模方法',
  'First-order duration approximation only; convexity and spread changes are excluded.':
    '仅采用一阶久期近似，不包含凸性和利差变化。',
  'Static fallback exposure used only for this hypothetical technology-sector shock; it is not live holdings data.':
    '该静态兜底敞口仅用于本次假设科技板块冲击，不是实时持仓数据。',
  'Static effective-duration fallback used in ΔP/P ≈ -DΔy; it is not a real-time duration measurement.':
    'ΔP/P ≈ -DΔy 使用静态有效久期兜底值，不是实时久期测量。',
  'Simplified hypothetical stress scenario. Results are deterministic linear estimates based on user inputs and disclosed fallback assumptions; they are not predictions or personalized financial advice.':
    '简化的假设压力情景。结果是基于用户输入与已披露兜底假设的确定性线性估计，不是预测或个性化投资建议。',
  'Enter a portfolio risk question or a hypothetical stress scenario.':
    '请输入组合风险问题或假设压力情景。',
  'The Risk Officer could not respond.': '风险官未能返回结果。',
  'Every portfolio position needs a ticker before stress testing.':
    '压力测试前，每项持仓都需要资产代码。',
  'The stress test could not be completed.': '未能完成压力测试。',
  'Add at least one position before optimizing.': '优化前请至少添加一项持仓。',
  'Enter a unique ticker for every position.':
    '请为每项持仓输入不重复的资产代码。',
  'Portfolio weights must sum to 100%.': '组合权重之和必须为 100%。',
  'The optimization could not be completed.': '未能完成优化。',
  'Enter at least one position with unique, nonempty tickers.':
    '请至少输入一项持仓，代码不能为空或重复。',
  'Select a 3- or 5-year lookback to reserve separate training and forward periods.':
    '请选择 3 年或 5 年回看区间，以保留独立的训练期与测试期。',
  'Trading cost must be between 0 and 100 basis points.':
    '交易成本必须介于 0 至 100 个基点。',
  'The backtest could not be completed.': '未能完成回测。',
  'Deterministic demo snapshot': '确定性演示快照',
  'The Python analytics service could not be reached. Confirm the backend deployment and CORS configuration, then try again.':
    '无法连接 Python 分析服务。请确认后端部署和 CORS 配置后重试。',
  'The optimization service could not be reached.': '无法连接组合优化服务。',
  'The Python backtest service could not be reached.':
    '无法连接 Python 回测服务。',
  'Demo mode uses a fixed synthetic history. Start the Python API for live Yahoo Finance data.':
    '演示模式使用固定的合成历史数据。连接 Python API 后可加载 Yahoo Finance 历史行情。',
};

const lookup = new Map(
  Object.entries(zhMessages).map(([key, value]) => [key.toLowerCase(), value]),
);

export function parseLocale(value: string | null): Locale {
  return value === 'zh' ? 'zh' : 'en';
}

/** Unknown server prose is retained verbatim rather than machine-translated or inferred. */
export function translate(
  locale: Locale,
  text: string,
  values: Record<string, string | number> = {},
): string {
  const normalized = text.replace(/\s+/g, ' ').trim();
  let message =
    locale === 'zh' ? (lookup.get(normalized.toLowerCase()) ?? text) : text;
  if (locale === 'zh' && message === text) {
    message = text
      .replace(
        /^([A-Z0-9.^=-]+) technology exposure assumption$/,
        '$1 科技暴露假设',
      )
      .replace(/^([A-Z0-9.^=-]+) duration assumption$/, '$1 久期假设')
      .replace(/^(\d+(?:\.\d+)?) years$/, '$1 年');
    message = message
      .replace(
        /^Effective position count is (\d+\.\d+), below 3\.0\.$/,
        '有效持仓数量为 $1，低于 3.0。',
      )
      .replace(
        /^Maximum pairwise correlation is (-?\d+\.\d+)\.$/,
        '最高资产对相关系数为 $1。',
      )
      .replace(
        /^The largest volatility contribution is (\d+\.\d+%)\.$/,
        '最大单一资产波动风险贡献为 $1。',
      );
  }
  return message.replace(/\{(\w+)\}/g, (match, key) =>
    String(values[key] ?? match),
  );
}
