'use client';

import { LoaderCircle, Plus, Scale, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { DEMO_PORTFOLIOS } from '@/lib/demo-data';
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
  const total = positions.reduce((sum, position) => sum + position.weight, 0);
  const isValid =
    positions.length > 0 &&
    positions.every((position) => position.ticker.trim() && position.weight >= 0) &&
    Math.abs(total - 1) <= 0.0001;

  function updatePosition(index: number, patch: Partial<PositionInput>) {
    onChange(positions.map((position, itemIndex) => itemIndex === index ? { ...position, ...patch } : position));
  }

  function selectPreset(nextPreset: DemoPortfolioName) {
    onPresetChange(nextPreset);
    onChange(DEMO_PORTFOLIOS[nextPreset].map((position) => ({ ...position })));
  }

  function normalize() {
    if (total <= 0) return;
    onChange(positions.map((position) => ({ ...position, weight: position.weight / total })));
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-4">
        <label className="section-label" htmlFor="portfolio-preset">Portfolio</label>
        <NativeSelect
          className="mt-2 w-full"
          size="sm"
          id="portfolio-preset"
          value={preset}
          onChange={(event) => selectPreset(event.target.value as DemoPortfolioName)}
          aria-label="Select demo portfolio"
        >
          {Object.keys(DEMO_PORTFOLIOS).map((name) => <NativeSelectOption key={name} value={name}>{name}</NativeSelectOption>)}
        </NativeSelect>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="grid grid-cols-[1fr_72px_28px] gap-2 border-b border-border px-3 py-2 text-[9px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
          <span>Instrument</span><span className="text-right">Weight</span><span />
        </div>
        {positions.map((position, index) => (
          <div key={`${index}-${position.ticker}`} className="grid grid-cols-[1fr_72px_28px] items-center gap-2 border-b border-border px-3 py-2">
            <Input
              value={position.ticker}
              onChange={(event) => updatePosition(index, { ticker: event.target.value.toUpperCase() })}
              className="h-7 rounded-sm border-transparent bg-transparent px-1 font-mono text-xs font-semibold hover:border-input focus:border-ring"
              aria-label={`Ticker ${index + 1}`}
            />
            <div className="relative">
              <Input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={Number((position.weight * 100).toFixed(4))}
                onChange={(event) => updatePosition(index, { weight: Math.max(0, Number(event.target.value) / 100) })}
                className="h-7 rounded-sm pr-5 text-right font-mono text-xs"
                aria-label={`${position.ticker || `Position ${index + 1}`} weight percent`}
              />
              <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-[10px] text-muted-foreground">%</span>
            </div>
            <Button
              size="icon-xs"
              variant="ghost"
              aria-label={`Remove ${position.ticker || `position ${index + 1}`}`}
              disabled={positions.length === 1}
              onClick={() => onChange(positions.filter((_, itemIndex) => itemIndex !== index))}
            ><Trash2 /></Button>
          </div>
        ))}
      </div>

      <div className="border-t border-border p-3">
        <div className="grid grid-cols-2 gap-2">
          <Button
            size="sm"
            variant="outline"
            className="rounded-sm"
            onClick={() => onChange([...positions, { ticker: '', weight: 0 }])}
          ><Plus /> Position</Button>
          <Button size="sm" variant="outline" className="rounded-sm" onClick={normalize} disabled={total <= 0}><Scale /> Normalize</Button>
        </div>
        <div className="mt-3 flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
          <span>Total weight</span>
          <span className={isValid ? 'font-mono text-emerald-300' : 'font-mono text-amber-300'}>{(total * 100).toFixed(2)}% · {isValid ? 'Valid' : 'Review'}</span>
        </div>
        <div className="mt-1.5 h-1 overflow-hidden bg-muted"><div className={isValid ? 'h-full bg-emerald-400' : 'h-full bg-amber-400'} style={{ width: `${Math.min(total * 100, 100)}%` }} /></div>
        <Button className="mt-3 w-full rounded-sm" size="sm" disabled={!isValid || isLoading} onClick={onAnalyze}>
          {isLoading ? <><LoaderCircle className="animate-spin" /> Calculating…</> : 'Analyze portfolio'}
        </Button>
      </div>
    </div>
  );
}
