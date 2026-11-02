'use client';
import { useLanguage } from '@/components/LanguageProvider';
import { useId } from 'react';

import { LoaderCircle, Plus, Scale, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  NativeSelect,
  NativeSelectOption,
} from '@/components/ui/native-select';
import { DEMO_PORTFOLIOS } from '@/lib/demo-data';
import { validatePortfolioInput } from '@/lib/portfolio-validation';
import type { DemoPortfolioName, PositionInput } from '@/lib/types';

type Props = {
  positions: PositionInput[];
  preset: DemoPortfolioName;
  onPresetChange: (preset: DemoPortfolioName) => void;
  onChange: (positions: PositionInput[]) => void;
  onAnalyze: () => void;
  isLoading: boolean;
};

export function PortfolioEditor({
  positions,
  preset,
  onPresetChange,
  onChange,
  onAnalyze,
  isLoading,
}: Props) {
  const { t } = useLanguage();
  const inputId = useId();
  const validation = validatePortfolioInput(positions);
  const { total, isValid } = validation;

  function updatePosition(index: number, patch: Partial<PositionInput>) {
    onChange(
      positions.map((position, itemIndex) =>
        itemIndex === index ? { ...position, ...patch } : position,
      ),
    );
  }

  function selectPreset(nextPreset: DemoPortfolioName) {
    onChange(DEMO_PORTFOLIOS[nextPreset].map((position) => ({ ...position })));
    onPresetChange(nextPreset);
  }

  function normalize() {
    if (!validation.canNormalize || total === null) return;
    onChange(
      positions.map((position) => ({
        ...position,
        weight: position.weight / total,
      })),
    );
  }

  return (
    <div className="flex flex-col" aria-busy={isLoading}>
      <div className="border-b border-border px-4 py-3">
        <label className="section-label" htmlFor="portfolio-preset">
          {t('Portfolio')}
        </label>
        <NativeSelect
          className="mt-2 w-full"
          size="sm"
          id="portfolio-preset"
          value={preset}
          disabled={isLoading}
          onChange={(event) =>
            selectPreset(event.target.value as DemoPortfolioName)
          }
          aria-label={t('Select demo portfolio')}
        >
          {Object.keys(DEMO_PORTFOLIOS).map((name) => (
            <NativeSelectOption key={name} value={name}>
              {t(name)}
            </NativeSelectOption>
          ))}
        </NativeSelect>
      </div>

      <div className="max-h-80 overflow-y-auto">
        <div className="grid grid-cols-[1fr_72px_28px] gap-2 border-b border-border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
          <span>{t('Instrument')}</span>
          <span className="text-right">{t('Weight')}</span>
          <span />
        </div>
        {positions.map((position, index) => (
          <div
            key={index}
            className="grid grid-cols-[1fr_72px_28px] items-center gap-2 border-b border-border px-3 py-2"
          >
            <Input
              value={position.ticker}
              disabled={isLoading}
              onChange={(event) =>
                updatePosition(index, {
                  ticker: event.target.value.toUpperCase(),
                })
              }
              className="h-8 rounded border-transparent bg-transparent px-1 font-mono text-sm font-semibold hover:border-input focus:border-ring"
              aria-label={t('Ticker {index}', { index: index + 1 })}
              aria-invalid={Boolean(validation.rows[index].ticker)}
              aria-describedby={
                validation.rows[index].ticker
                  ? `${inputId}-${index}-ticker`
                  : undefined
              }
            />
            <div className="relative">
              <Input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={
                  Number.isFinite(position.weight)
                    ? Number((position.weight * 100).toFixed(4))
                    : ''
                }
                disabled={isLoading}
                onChange={(event) =>
                  updatePosition(index, {
                    weight: Math.max(0, Number(event.target.value) / 100),
                  })
                }
                className="h-8 rounded pr-5 text-right font-mono text-sm"
                aria-label={t('{ticker} weight percent', {
                  ticker: position.ticker || String(index + 1),
                })}
                aria-invalid={Boolean(validation.rows[index].weight)}
                aria-describedby={
                  validation.rows[index].weight
                    ? `${inputId}-${index}-weight`
                    : undefined
                }
              />
              <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-[12px] text-muted-foreground">
                %
              </span>
            </div>
            <Button
              size="icon-xs"
              variant="ghost"
              aria-label={t('Remove {ticker}', {
                ticker: position.ticker || String(index + 1),
              })}
              disabled={isLoading || positions.length === 1}
              onClick={() =>
                onChange(
                  positions.filter((_, itemIndex) => itemIndex !== index),
                )
              }
            >
              <Trash2 />
            </Button>
            {validation.rows[index].ticker && (
              <p
                id={`${inputId}-${index}-ticker`}
                className="col-span-3 text-xs leading-relaxed text-amber-300"
              >
                {t(validation.rows[index].ticker)}
              </p>
            )}
            {validation.rows[index].weight && (
              <p
                id={`${inputId}-${index}-weight`}
                className="col-span-3 text-xs leading-relaxed text-amber-300"
              >
                {t(validation.rows[index].weight)}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="border-t border-border p-3">
        <div className="grid grid-cols-2 gap-2">
          <Button
            size="sm"
            variant="outline"
            className="rounded-sm"
            disabled={isLoading || !validation.canAdd}
            aria-describedby={
              !validation.canAdd ? `${inputId}-limit` : undefined
            }
            onClick={() => {
              if (validation.canAdd)
                onChange([...positions, { ticker: '', weight: 0 }]);
            }}
          >
            <Plus /> {t('Position')}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="rounded-sm"
            onClick={normalize}
            disabled={isLoading || !validation.canNormalize}
          >
            <Scale /> {t('Normalize')}
          </Button>
        </div>
        {!validation.canAdd && (
          <p id={`${inputId}-limit`} className="mt-2 text-xs text-amber-300">
            {t('A portfolio supports up to 50 positions.')}
          </p>
        )}
        <div className="mt-3 flex items-center justify-between text-[12px] uppercase tracking-wider text-muted-foreground">
          <span>{t('Total weight')}</span>
          <span
            className={
              isValid
                ? 'font-mono text-emerald-300'
                : 'font-mono text-amber-300'
            }
          >
            {total === null ? '—' : `${(total * 100).toFixed(2)}%`} ·{' '}
            {isValid ? t('Valid') : t('Review')}
          </span>
        </div>
        <div className="mt-1.5 h-1 overflow-hidden bg-muted">
          <div
            className={
              isValid ? 'h-full bg-emerald-400' : 'h-full bg-amber-400'
            }
            style={{
              width: `${Math.max(0, Math.min((total ?? 0) * 100, 100))}%`,
            }}
          />
        </div>
        <div aria-live="polite" aria-atomic="true">
          {validation.message && (
            <p className="mt-2 text-xs leading-relaxed text-amber-300">
              {t(validation.message)}
            </p>
          )}
        </div>
        <Button
          className="mt-3 h-10 w-full rounded font-semibold"
          size="sm"
          disabled={!isValid || isLoading}
          onClick={onAnalyze}
        >
          {isLoading ? (
            <>
              <LoaderCircle className="animate-spin" /> {t('Calculating…')}
            </>
          ) : (
            t('Analyze portfolio')
          )}
        </Button>
      </div>
    </div>
  );
}
