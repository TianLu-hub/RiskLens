"""Zero-cost, deterministic intent parsing and portfolio-risk explanations."""

from __future__ import annotations

import re

from pydantic import ValidationError

from app.ai.scenario_parser import ScenarioInterpretationError
from app.models.ai import (
    EvidenceKey,
    OfficerFindingDraft,
    OfficerIntent,
    OfficerNarrativeDraft,
    ParsedRiskIntent,
    ParsedTickerShock,
    RiskOfficerAnalysisContext,
)
from app.models.stress import StressTestResponse


_NUMBER = r"(?P<value>\d+(?:\.\d+)?)"
_PERCENT_UNIT = r"(?:\s*%|\s*percent|\s*per\s*cent|\s*百分之)"
_RATE_UNIT = r"(?:\s*bps?\b|\s*basis\s+points?\b|\s*个?基点)"

_DOWN_WORDS = (
    "drop",
    "drops",
    "dropped",
    "fall",
    "falls",
    "decline",
    "declines",
    "selloff",
    "sell-off",
    "crash",
    "crashes",
    "down",
    "下跌",
    "下降",
    "跌",
    "暴跌",
    "回落",
)
_UP_WORDS = (
    "rise",
    "rises",
    "increase",
    "increases",
    "up",
    "上升",
    "上涨",
    "提高",
    "升高",
)

_SUBJECTS = {
    "market_shock": (
        "broad market",
        "overall market",
        "market",
        "大盘",
        "整体市场",
        "市场",
    ),
    "tech_shock": (
        "technology sector",
        "technology",
        "tech sector",
        "tech",
        "科技板块",
        "科技股",
        "科技",
    ),
}


class DeterministicRiskOfficer:
    """Bounded language grammar plus evidence-grounded narrative templates."""

    model = "risklens-deterministic-officer"
    narrative_source = "deterministic_rule_engine"

    def parse_intent(self, question: str, tickers: list[str]) -> ParsedRiskIntent:
        """Translate supported explicit shocks without an external model call."""

        normalized = _normalize(question)
        percentage_shocks: dict[str, float | None] = {
            "market_shock": None,
            "tech_shock": None,
        }
        for field, subjects in _SUBJECTS.items():
            percentage_shocks[field] = _extract_directional_value(
                normalized,
                subjects=subjects,
                negative_words=_DOWN_WORDS,
                positive_words=_UP_WORDS,
                unit_pattern=_PERCENT_UNIT,
                scale=100.0,
            )

        rates_shock_bps = _extract_directional_value(
            normalized,
            subjects=(
                "interest rates",
                "interest rate",
                "rates",
                "rate",
                "利率",
                "收益率",
            ),
            negative_words=(
                "fall",
                "falls",
                "decline",
                "declines",
                "down",
                "cut",
                "cuts",
                "下降",
                "下调",
                "降低",
            ),
            positive_words=(
                "rise",
                "rises",
                "increase",
                "increases",
                "up",
                "hike",
                "hikes",
                "上升",
                "上调",
                "提高",
            ),
            unit_pattern=_RATE_UNIT,
            scale=1.0,
        )

        ticker_shocks: list[ParsedTickerShock] = []
        for ticker in tickers:
            shock = _extract_directional_value(
                normalized,
                subjects=(ticker.lower(),),
                negative_words=_DOWN_WORDS,
                positive_words=_UP_WORDS,
                unit_pattern=_PERCENT_UNIT,
                scale=100.0,
            )
            if shock is not None:
                ticker_shocks.append(ParsedTickerShock(ticker=ticker, shock=shock))

        values = [
            percentage_shocks["market_shock"],
            percentage_shocks["tech_shock"],
            rates_shock_bps,
            *(item.shock for item in ticker_shocks),
        ]
        has_scenario = any(value is not None for value in values)

        if not has_scenario:
            if _looks_like_unparsed_scenario(normalized):
                raise ScenarioInterpretationError(
                    "The zero-cost parser could not safely interpret that scenario. "
                    "Use an explicit percentage or basis-point shock, or enter it in "
                    "the structured Stress Testing panel."
                )
            return ParsedRiskIntent(
                intent=OfficerIntent.PORTFOLIO_ANALYSIS,
                scenario_name=None,
                market_shock=None,
                tech_shock=None,
                rates_shock_bps=None,
                ticker_shocks=[],
            )

        try:
            return ParsedRiskIntent(
                intent=OfficerIntent.STRESS_SCENARIO,
                scenario_name="Deterministic natural-language scenario",
                market_shock=percentage_shocks["market_shock"],
                tech_shock=percentage_shocks["tech_shock"],
                rates_shock_bps=rates_shock_bps,
                ticker_shocks=ticker_shocks,
            )
        except ValidationError as error:
            raise ScenarioInterpretationError(
                "A parsed shock is outside the supported scenario bounds."
            ) from error

    def create_narrative(
        self,
        question: str,
        analysis: RiskOfficerAnalysisContext,
        stress_test: StressTestResponse | None,
    ) -> OfficerNarrativeDraft:
        """Select qualitative findings from deterministic thresholds and rankings."""

        if _contains_cjk(question):
            return _chinese_narrative(analysis, stress_test)
        return _english_narrative(analysis, stress_test)


def _normalize(question: str) -> str:
    return (
        question.lower()
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("％", "%")
        .replace("，", ",")
    )


def _alternation(values: tuple[str, ...]) -> str:
    return "(?:" + "|".join(re.escape(value) for value in values) + ")"


def _extract_directional_value(
    text: str,
    *,
    subjects: tuple[str, ...],
    negative_words: tuple[str, ...],
    positive_words: tuple[str, ...],
    unit_pattern: str,
    scale: float,
) -> float | None:
    """Extract one explicit bounded shock using a lexicon-backed grammar."""

    subject = _alternation(subjects)
    negative = _alternation(negative_words)
    positive = _alternation(positive_words)
    separator = r"(?:\s|[:;,，]|would|by|of|shock|moves?|move|is|to){0,28}"

    patterns: tuple[tuple[str, float | None], ...] = (
        (rf"{subject}{separator}{negative}{separator}{_NUMBER}{unit_pattern}", -1.0),
        (rf"{subject}{separator}{positive}{separator}{_NUMBER}{unit_pattern}", 1.0),
        (rf"{subject}{separator}(?P<sign>[+-])\s*{_NUMBER}{unit_pattern}", None),
        (rf"{_NUMBER}{unit_pattern}{separator}{negative}{separator}{subject}", -1.0),
        (rf"{_NUMBER}{unit_pattern}{separator}{positive}{separator}{subject}", 1.0),
    )
    for pattern, fixed_sign in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match is None:
            continue
        sign = fixed_sign
        if sign is None:
            sign = -1.0 if match.group("sign") == "-" else 1.0
        return sign * float(match.group("value")) / scale
    return None


def _looks_like_unparsed_scenario(text: str) -> bool:
    scenario_terms = (
        "what happens if",
        "what if",
        "scenario",
        "shock",
        "drops",
        "falls",
        "rises",
        "stress",
        "如果",
        "情景",
        "冲击",
        "下跌",
        "上升",
    )
    return any(term in text for term in scenario_terms)


def _contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def _tail_is_elevated(analysis: RiskOfficerAnalysisContext) -> bool:
    return (
        analysis.metrics.var > 0 and analysis.metrics.cvar > analysis.metrics.var * 1.5
    )


def _correlation_is_elevated(analysis: RiskOfficerAnalysisContext) -> bool:
    return bool(
        analysis.correlation.highest_correlations
        and analysis.correlation.highest_correlations[0].correlation > 0.75
    )


def _risk_is_dominated(analysis: RiskOfficerAnalysisContext) -> bool:
    return max(item.risk_contribution for item in analysis.risk_contributions) > 0.35


def _concentration_is_elevated(analysis: RiskOfficerAnalysisContext) -> bool:
    return analysis.concentration.effective_positions < 3.0


def _factor_finding_english(
    analysis: RiskOfficerAnalysisContext,
) -> OfficerFindingDraft | None:
    factor = analysis.factor_exposure
    if not factor.available or factor.market_beta is None:
        return None
    if factor.market_beta > 1.1:
        title = "Market sensitivity is amplified"
        explanation = (
            "The historical market beta indicates that broad equity moves have been "
            "amplified in the portfolio over the selected sample."
        )
    elif factor.market_beta < 0.8:
        title = "Market sensitivity is comparatively defensive"
        explanation = (
            "The historical market beta indicates lower sensitivity to broad equity "
            "moves over the selected sample."
        )
    else:
        title = "Market sensitivity is close to the benchmark"
        explanation = (
            "The historical market beta indicates broadly benchmark-like sensitivity, "
            "while unexplained variation remains outside the single-factor model."
        )
    evidence_keys = [EvidenceKey.MARKET_BETA]
    if factor.r_squared is not None:
        evidence_keys.append(EvidenceKey.FACTOR_R_SQUARED)
    if factor.idiosyncratic_volatility is not None:
        evidence_keys.append(EvidenceKey.IDIOSYNCRATIC_VOLATILITY)
    return OfficerFindingDraft(
        title=title,
        explanation=explanation,
        evidence_keys=evidence_keys,
    )


def _factor_finding_chinese(
    analysis: RiskOfficerAnalysisContext,
) -> OfficerFindingDraft | None:
    factor = analysis.factor_exposure
    if not factor.available or factor.market_beta is None:
        return None
    if factor.market_beta > 1.1:
        title = "市场敏感度被放大"
        explanation = "历史市场贝塔显示，所选样本中组合放大了大盘权益市场的共同波动。"
    elif factor.market_beta < 0.8:
        title = "市场敏感度相对防御"
        explanation = "历史市场贝塔显示，所选样本中组合对大盘权益市场的敏感度较低。"
    else:
        title = "市场敏感度接近基准"
        explanation = "历史市场贝塔显示组合敏感度与基准较为接近，同时仍存在单因子模型无法解释的波动。"
    evidence_keys = [EvidenceKey.MARKET_BETA]
    if factor.r_squared is not None:
        evidence_keys.append(EvidenceKey.FACTOR_R_SQUARED)
    if factor.idiosyncratic_volatility is not None:
        evidence_keys.append(EvidenceKey.IDIOSYNCRATIC_VOLATILITY)
    return OfficerFindingDraft(
        title=title,
        explanation=explanation,
        evidence_keys=evidence_keys,
    )


def _english_narrative(
    analysis: RiskOfficerAnalysisContext,
    stress_test: StressTestResponse | None,
) -> OfficerNarrativeDraft:
    findings: list[OfficerFindingDraft] = []

    if stress_test is not None:
        findings.append(
            OfficerFindingDraft(
                title="Hypothetical loss channel",
                explanation=(
                    "The supplied shocks flow through affected holdings in the Python "
                    "stress engine, with the leading loss source shown in the evidence."
                ),
                evidence_keys=[
                    EvidenceKey.STRESS_PORTFOLIO_RETURN,
                    EvidenceKey.STRESS_TOP_CONTRIBUTOR,
                    EvidenceKey.STRESS_DOLLAR_PNL,
                ],
            )
        )

    if _risk_is_dominated(analysis):
        title = "Volatility risk is dominated by one holding"
        explanation = (
            "The largest volatility contributor carries a disproportionate share of "
            "the portfolio risk budget relative to the broader allocation."
        )
    else:
        title = "Volatility contribution is distributed"
        explanation = (
            "No single holding crosses the deterministic dominance threshold, although "
            "the leading contributor remains the primary risk channel."
        )
    findings.append(
        OfficerFindingDraft(
            title=title,
            explanation=explanation,
            evidence_keys=[
                EvidenceKey.LARGEST_RISK_CONTRIBUTOR,
                EvidenceKey.ANNUALIZED_VOLATILITY,
            ],
        )
    )

    factor_finding = _factor_finding_english(analysis)
    if factor_finding is not None:
        findings.append(factor_finding)

    if _concentration_is_elevated(analysis):
        concentration_text = (
            "Effective diversification is materially below the nominal position count, "
            "so allocation concentration can amplify common shocks."
        )
    else:
        concentration_text = (
            "Position concentration is not extreme under the effective position rule, "
            "but the largest weights still deserve attention alongside risk contribution."
        )
    findings.append(
        OfficerFindingDraft(
            title="Diversification capacity",
            explanation=concentration_text,
            evidence_keys=[
                EvidenceKey.EFFECTIVE_POSITIONS,
                EvidenceKey.LARGEST_POSITION,
                EvidenceKey.TOP_THREE_CONCENTRATION,
            ],
        )
    )

    if _correlation_is_elevated(analysis):
        findings.append(
            OfficerFindingDraft(
                title="Correlation weakens diversification",
                explanation=(
                    "The strongest observed pair moves closely together, reducing the "
                    "protection expected from holding separate instruments."
                ),
                evidence_keys=[EvidenceKey.HIGHEST_CORRELATION],
            )
        )
    elif _tail_is_elevated(analysis):
        findings.append(
            OfficerFindingDraft(
                title="Losses deepen beyond the usual tail cutoff",
                explanation=(
                    "Expected shortfall is materially worse than the historical tail "
                    "threshold, indicating sensitivity to severe loss days."
                ),
                evidence_keys=[EvidenceKey.VAR, EvidenceKey.CVAR],
            )
        )

    if stress_test is not None:
        headline = "The hypothetical scenario exposes a concentrated loss channel"
        summary = (
            "The deterministic stress engine applies only the supplied shocks and "
            "disclosed fallback assumptions. The result is a sensitivity estimate, not "
            "a prediction."
        )
    else:
        headline = "Calculated evidence identifies the leading portfolio risk channels"
        summary = (
            "The briefing prioritizes volatility contribution, diversification, "
            "correlation, and tail behavior using fixed backend rules over the supplied "
            "historical analysis."
        )

    return OfficerNarrativeDraft(
        headline=headline,
        summary=summary,
        findings=findings[:4],
        limitations=[
            (
                "Size and value factor exposures are unavailable because no validated factor series was supplied."
                if analysis.factor_exposure.available
                else "Market factor exposure is unavailable for the selected sample."
            ),
            "The language parser supports a bounded set of explicit English and Chinese shock phrases.",
            "Historical statistics and hypothetical stress results are not forecasts or personalized advice.",
        ],
    )


def _chinese_narrative(
    analysis: RiskOfficerAnalysisContext,
    stress_test: StressTestResponse | None,
) -> OfficerNarrativeDraft:
    findings: list[OfficerFindingDraft] = []

    if stress_test is not None:
        findings.append(
            OfficerFindingDraft(
                title="假设情景损失通道",
                explanation="输入的冲击由 Python 压力引擎作用于相关持仓，证据栏显示主要损失来源。",
                evidence_keys=[
                    EvidenceKey.STRESS_PORTFOLIO_RETURN,
                    EvidenceKey.STRESS_TOP_CONTRIBUTOR,
                    EvidenceKey.STRESS_DOLLAR_PNL,
                ],
            )
        )

    if _risk_is_dominated(analysis):
        risk_title = "波动风险由单一持仓主导"
        risk_text = "最大波动贡献者占用了不成比例的风险预算，是组合的首要风险来源。"
    else:
        risk_title = "波动风险贡献较为分散"
        risk_text = "没有单一持仓越过固定的主导阈值，但最大贡献者仍是主要风险通道。"
    findings.append(
        OfficerFindingDraft(
            title=risk_title,
            explanation=risk_text,
            evidence_keys=[
                EvidenceKey.LARGEST_RISK_CONTRIBUTOR,
                EvidenceKey.ANNUALIZED_VOLATILITY,
            ],
        )
    )

    factor_finding = _factor_finding_chinese(analysis)
    if factor_finding is not None:
        findings.append(factor_finding)

    if _concentration_is_elevated(analysis):
        concentration_text = (
            "有效分散程度明显低于名义持仓数量，集中配置可能放大共同冲击。"
        )
    else:
        concentration_text = (
            "按有效持仓规则看，集中度并不极端，但仍需结合风险贡献审视最大权重。"
        )
    findings.append(
        OfficerFindingDraft(
            title="分散化能力",
            explanation=concentration_text,
            evidence_keys=[
                EvidenceKey.EFFECTIVE_POSITIONS,
                EvidenceKey.LARGEST_POSITION,
                EvidenceKey.TOP_THREE_CONCENTRATION,
            ],
        )
    )

    if _correlation_is_elevated(analysis):
        findings.append(
            OfficerFindingDraft(
                title="相关性削弱分散效果",
                explanation="历史上最相关的一组资产走势较为接近，降低了多持仓带来的保护作用。",
                evidence_keys=[EvidenceKey.HIGHEST_CORRELATION],
            )
        )
    elif _tail_is_elevated(analysis):
        findings.append(
            OfficerFindingDraft(
                title="尾部亏损进一步加深",
                explanation="期望损失明显高于历史尾部阈值，组合对严重亏损日较为敏感。",
                evidence_keys=[EvidenceKey.VAR, EvidenceKey.CVAR],
            )
        )

    if stress_test is not None:
        headline = "假设情景显示了集中的损失通道"
        summary = (
            "确定性压力引擎仅使用明确输入和披露的备用假设，结果是敏感性估计而不是预测。"
        )
    else:
        headline = "计算证据显示了组合的主要风险通道"
        summary = (
            "本简报依据固定后端规则，对波动贡献、分散程度、相关性和尾部特征进行排序。"
        )

    return OfficerNarrativeDraft(
        headline=headline,
        summary=summary,
        findings=findings[:4],
        limitations=[
            (
                "由于未提供经过验证的因子序列，当前不报告规模和价值因子暴露。"
                if analysis.factor_exposure.available
                else "所选样本无法估计市场因子暴露。"
            ),
            "免费语言解析器只支持有限的中英文显式冲击表达。",
            "历史统计和假设压力结果不是预测，也不构成个性化投资建议。",
        ],
    )
