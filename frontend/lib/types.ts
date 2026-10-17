export type PositionInput = {
  ticker: string;
  weight: number;
  initial_value?: number;
};

export type AnalyzeRequest = {
  positions: PositionInput[];
  lookback_years: number;
  risk_free_rate: number;
  confidence_level?: number;
};

export type OptimizationObjective =
  | 'minimum_volatility'
  | 'maximum_sharpe'
  | 'risk_parity';

export type OptimizeRequest = AnalyzeRequest & {
  objective: OptimizationObjective;
  max_position_weight: number | null;
};

export type OptimizationMetrics = {
  annualized_return: number;
  annualized_volatility: number;
  sharpe_ratio: number | null;
  hhi: number;
  effective_positions: number;
};

export type OptimizationResult = {
  objective: OptimizationObjective;
  max_position_weight: number | null;
  current: OptimizationMetrics;
  optimized: OptimizationMetrics;
  allocations: Array<{
    ticker: string;
    current_weight: number;
    optimized_weight: number;
    weight_change: number;
  }>;
  one_way_turnover: number;
  data_quality: PortfolioAnalysis['data_quality'];
  methodology: string;
  limitations: string[];
};

export type BacktestRequest = OptimizeRequest & {
  training_days: number;
  rebalance_days: number;
  cost_bps: number;
};

export type BacktestMetrics = {
  cumulative_return: number;
  annualized_return: number;
  annualized_volatility: number;
  sharpe_ratio: number | null;
  max_drawdown: number;
  final_wealth: number;
  total_one_way_turnover: number;
  total_cost_fraction_of_initial_capital: number;
};

export type BacktestResult = {
  objective: OptimizationObjective;
  current: BacktestMetrics;
  optimized: BacktestMetrics;
  spy_buy_and_hold: BacktestMetrics | null;
  series: Array<{
    date: string;
    current_wealth: number;
    optimized_wealth: number;
    spy_wealth: number | null;
  }>;
  folds: Array<{
    train_start: string;
    train_end: string;
    test_start: string;
    test_end: string;
    optimized_weights: Record<string, number>;
    optimized_one_way_turnover: number;
    current_one_way_turnover: number;
  }>;
  data_quality: PortfolioAnalysis['data_quality'];
  training_days: number;
  rebalance_days: number;
  cost_bps: number;
  methodology: string;
  limitations: string[];
};

export type TimeSeriesPoint = { date: string; value: number };

export type RiskMetrics = {
  annualized_return: number;
  annualized_volatility: number;
  sharpe_ratio: number | null;
  var: number;
  cvar: number;
  confidence_level: number;
  var_horizon_days: number;
  risk_free_rate: number;
};

export type RiskContributionItem = {
  ticker: string;
  weight: number;
  marginal_risk: number;
  absolute_risk_contribution: number;
  risk_contribution: number;
};

export type CorrelationPair = {
  asset_1: string;
  asset_2: string;
  correlation: number;
};

export type RiskFlag = {
  code: string;
  severity: string;
  title: string;
  detail: string;
};

export type FactorExposure = {
  model: string;
  benchmark_ticker: string;
  benchmark_source: string | null;
  available: boolean;
  alpha_annualized: number | null;
  market_beta: number | null;
  smb_beta: number | null;
  hml_beta: number | null;
  r_squared: number | null;
  idiosyncratic_volatility: number | null;
  observations: number;
  rolling_window_days: number;
  rolling_beta: TimeSeriesPoint[];
  methodology: string;
  unavailable_reason: string | null;
};

export type PortfolioAnalysis = {
  metrics: RiskMetrics;
  performance: TimeSeriesPoint[];
  drawdown: {
    current_drawdown: number;
    max_drawdown: number;
    series: TimeSeriesPoint[];
  };
  correlation: {
    tickers: string[];
    matrix: number[][];
    highest_correlations: CorrelationPair[];
  };
  risk_contributions: RiskContributionItem[];
  concentration: {
    hhi: number;
    effective_positions: number;
    largest_position: number;
    largest_position_ticker: string;
    top_3_concentration: number;
    position_count: number;
  };
  factor_exposure: FactorExposure;
  risk_flags: RiskFlag[];
  data_quality: {
    source: string;
    observations: number;
    start_date: string;
    end_date: string;
    requested_lookback_years: number;
    warnings: string[];
    provenance?: MarketDataProvenance | null;
  };
};

export type MarketDataProvenance = {
  data_type: 'historical' | 'synthetic';
  fetched_at: string;
  cache_hit: boolean;
  cache_ttl_seconds: number;
  price_basis: 'adjusted_close' | 'unadjusted_close';
  price_start_date: string;
  price_end_date: string;
  raw_price_rows: number;
  aligned_price_rows: number;
  dropped_price_rows: number;
  forward_fill_limit: number;
  assets: Array<{
    ticker: string;
    observed_prices: number;
    missing_prices: number;
    filled_prices: number;
    first_observed_date: string;
    last_observed_date: string;
  }>;
};

export type DemoPortfolioName =
  | 'Mega-Cap Tech'
  | 'Balanced 60/40'
  | 'Risk-Off'
  | 'Growth'
  | 'Custom';

export type StressTestRequest = {
  positions: PositionInput[];
  portfolio_value?: number;
  scenario_name: string;
  market_shock?: number;
  tech_shock?: number;
  rates_shock_bps?: number;
  ticker_shocks: Record<string, number>;
};

export type StressAssumption = {
  id: string;
  label: string;
  value: string;
  source_type:
    | 'user_input'
    | 'fallback_modeling_assumption'
    | 'model_methodology';
  description: string;
};

export type StressTestResult = {
  scenario_name: string;
  scenario_classification: 'hypothetical';
  historical_data_used: false;
  scenario_inputs: {
    market_shock: number | null;
    tech_shock: number | null;
    rates_shock_bps: number | null;
    ticker_shocks: Record<string, number>;
  };
  estimated_portfolio_return: number;
  estimated_dollar_pnl: number | null;
  portfolio_value_before: number | null;
  portfolio_value_after: number | null;
  asset_contributions: Array<{
    ticker: string;
    weight: number;
    estimated_asset_return: number;
    portfolio_contribution: number;
    estimated_dollar_pnl: number | null;
    position_value_before: number | null;
    position_value_after: number | null;
    factor_shocks: Record<string, number>;
  }>;
  factor_contributions: Array<{
    factor: string;
    label: string;
    portfolio_contribution: number;
    estimated_dollar_pnl: number | null;
  }>;
  assumptions: StressAssumption[];
  disclaimer: string;
};

export type RiskOfficerAnalysisContext = {
  metrics: RiskMetrics;
  drawdown: {
    current_drawdown: number;
    max_drawdown: number;
  };
  correlation: {
    highest_correlations: CorrelationPair[];
  };
  risk_contributions: RiskContributionItem[];
  concentration: PortfolioAnalysis['concentration'];
  factor_exposure: FactorExposure;
  risk_flags: RiskFlag[];
  data_quality: PortfolioAnalysis['data_quality'];
};

export type RiskOfficerRequest = {
  question: string;
  positions: PositionInput[];
  portfolio_value?: number;
  analysis: RiskOfficerAnalysisContext;
};

export type ParsedRiskIntent = {
  intent: 'portfolio_analysis' | 'stress_scenario';
  scenario_name: string | null;
  market_shock: number | null;
  tech_shock: number | null;
  rates_shock_bps: number | null;
  ticker_shocks: Array<{ ticker: string; shock: number }>;
};

export type OfficerEvidence = {
  key: string;
  label: string;
  value: string;
  source_type:
    | 'observed_historical_statistic'
    | 'model_assumption'
    | 'hypothetical_scenario_result';
};

export type RiskOfficerResult = {
  intent: 'portfolio_analysis' | 'stress_scenario';
  headline: string;
  summary: string;
  findings: Array<{
    title: string;
    explanation: string;
    evidence: OfficerEvidence[];
  }>;
  limitations: string[];
  parsed_scenario: ParsedRiskIntent | null;
  stress_test: StressTestResult | null;
  narrative_source: 'openai_structured_output' | 'deterministic_rule_engine';
  model: string;
  numerical_policy: string;
  disclaimer: string;
};
