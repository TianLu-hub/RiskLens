export type KupiecTestResult = {
  method: 'kupiec_unconditional_coverage';
  statistic: number;
  p_value: number;
  degrees_of_freedom: 1;
  significance_level: 0.05;
  reject_null: boolean;
  null_breach_probability: number;
  observed_breach_probability: number;
  observations: number;
  breaches: number;
  warning_codes: Array<'low_expected_counts' | 'boundary_breach_count'>;
};

/** Presentation only. The Python decision must never be rebuilt from rounded p-values. */
export function kupiecDecision(
  result?: KupiecTestResult | null,
): 'unavailable' | 'reject' | 'notRejected' {
  if (result == null) return 'unavailable';
  return result.reject_null ? 'reject' : 'notRejected';
}

/** Preserve the side of the 5% threshold when rounding would obscure it. */
export function formatKupiecPValue(value: number): string {
  if (!Number.isFinite(value) || value < 0 || value > 1) return '—';
  if (value < 0.0001) return '< 0.0001';
  const rounded = value.toFixed(6);
  return Number(rounded) === 0.05 && value !== 0.05 ? String(value) : rounded;
}

/** The browser only formats the LR statistic supplied by Python. */
export function formatKupiecStatistic(value: number): string {
  if (!Number.isFinite(value) || value < 0) return '—';
  if (value > 0 && value < 0.000001) return value.toExponential(3);
  return value.toFixed(6);
}

/** Localize only the warning flags supplied by the backend; infer no extra tests. */
export function kupiecWarnings(
  result: KupiecTestResult,
  locale: 'en' | 'zh',
): string[] {
  return result.warning_codes.map((code) => kupiecCopy[locale][code]);
}

export const kupiecCopy = {
  en: {
    title: 'Kupiec coverage test',
    subtitle: 'Does the overall breach frequency match the nominal rate?',
    unavailable: 'Not available from this backend',
    unavailableNote:
      'The returned response does not include a Kupiec test. No statistic, p-value, or decision has been inferred. Update the backend and run again.',
    statistic: 'Likelihood ratio (LR)',
    pValue: 'p-value',
    significance: 'Test significance level',
    reject: 'Reject the null hypothesis',
    notRejected: 'Do not reject the null hypothesis',
    nullLabel: 'Null hypothesis (H₀)',
    nullDescription: 'The breach probability equals the nominal rate:',
    significanceNote:
      'The test uses a 5% significance level. This is not the VaR confidence level selected above.',
    decisionNote:
      'Reject only when p < 0.05. The decision is supplied by Python using the unrounded p-value. Display rounding never changes the decision.',
    rejectNote:
      'The observed breach frequency differs from the nominal rate at this significance level. A rejection can reflect too many or too few breaches.',
    notRejectedNote:
      'This sample does not provide sufficient evidence to reject the nominal rate. It does not prove that the model is accurate or safe.',
    scope:
      'Two-sided unconditional coverage test with an asymptotic chi-square reference (one degree of freedom). It does not test whether breaches are independent or how severe losses are.',
    warnings: 'Interpretation cautions',
    low_expected_counts:
      'At least one nominal expected count (breaches or non-breaches) is below five. The asymptotic p-value may be unreliable in this sample.',
    boundary_breach_count:
      'The sample has either no breaches or breaches on every test day. This boundary case requires caution when interpreting the asymptotic result.',
  },
  zh: {
    title: 'Kupiec 覆盖率检验',
    subtitle: '总体突破频率是否与名义水平一致？',
    unavailable: '当前后端未提供此检验',
    unavailableNote:
      '返回结果不包含 Kupiec 检验。本页不会自行推算统计量、p 值或结论；请更新后端后重新运行。',
    statistic: '似然比统计量（LR）',
    pValue: 'p 值',
    significance: '检验显著性水平',
    reject: '拒绝原假设',
    notRejected: '不拒绝原假设',
    nullLabel: '原假设（H₀）',
    nullDescription: '突破概率等于名义水平：',
    significanceNote:
      '检验采用 5% 的显著性水平，与上方选择的 VaR 置信水平不是同一个概念。',
    decisionNote:
      '仅当 p < 0.05 时拒绝原假设。结论由 Python 根据未四舍五入的 p 值给出，显示精度不会改变检验结论。',
    rejectNote:
      '在该显著性水平下，观察到的突破频率与名义水平存在差异。突破过多或过少都可能导致拒绝原假设。',
    notRejectedNote:
      '本样本尚无充分证据拒绝名义水平；这不等于证明模型准确或安全。',
    scope:
      '双侧无条件覆盖率检验，采用自由度为一的渐近卡方分布作为参照。不检验突破是否独立，也不衡量损失严重程度。',
    warnings: '解读注意事项',
    low_expected_counts:
      '名义预期突破次数或未突破次数至少有一项小于五次。本样本的渐近 p 值可能不可靠。',
    boundary_breach_count:
      '本样本没有突破，或每个测试日都发生突破。此类边界情况需谨慎解读渐近检验结果。',
  },
} as const;
