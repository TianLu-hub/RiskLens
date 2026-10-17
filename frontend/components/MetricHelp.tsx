'use client';

import { useState, useSyncExternalStore } from 'react';
import { Info, X } from 'lucide-react';
import { Popover as PopoverPrimitive } from '@base-ui/react/popover';
import { useLanguage } from '@/components/LanguageProvider';
import {
  Popover,
  PopoverContent,
  PopoverDescription,
  PopoverTitle,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import {
  metricHelp,
  metricHelpLabels,
  type MetricHelpId,
} from '@/lib/metric-help';

const smallScreen = '(max-width: 767px)';
function subscribeToScreen(callback: () => void) {
  const query = window.matchMedia(smallScreen);
  query.addEventListener('change', callback);
  return () => query.removeEventListener('change', callback);
}
function getSmallScreen() {
  return window.matchMedia(smallScreen).matches;
}
function getServerScreen() {
  return false;
}

/** Accessible click-to-open help; no hover-only content or requests to an AI service. */
export function MetricHelp({ metric }: { metric: MetricHelpId }) {
  const { locale } = useLanguage();
  const entry = metricHelp[metric][locale];
  const copy = metricHelpLabels[locale];
  const [open, setOpen] = useState(false);
  const mobile = useSyncExternalStore(
    subscribeToScreen,
    getSmallScreen,
    getServerScreen,
  );
  const triggerProps = {
    'aria-label': `${copy.open}: ${entry.title}`,
    className:
      'inline-flex size-7 shrink-0 items-center justify-center rounded text-muted-foreground hover:bg-primary/10 hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
  };
  const body = (
    <>
      <dl className="space-y-4 text-sm leading-relaxed">
        <div>
          <dt className="font-semibold text-foreground">{copy.calculation}</dt>
          <dd className="mt-1.5">
            <pre className="whitespace-pre-wrap break-words rounded border border-border bg-background p-3 font-mono text-xs leading-6 text-primary">
              {entry.formula}
            </pre>
            <p className="mt-2 text-muted-foreground">{entry.method}</p>
          </dd>
        </div>
        <div>
          <dt className="font-semibold text-foreground">{copy.reading}</dt>
          <dd className="mt-1 text-muted-foreground">{entry.interpretation}</dd>
        </div>
        <div>
          <dt className="font-semibold text-amber-200">{copy.limitations}</dt>
          <dd className="mt-1 text-muted-foreground">{entry.limitations}</dd>
        </div>
      </dl>
      <p className="mt-4 border-t border-border pt-3 text-xs text-muted-foreground">
        {copy.footer}
      </p>
    </>
  );
  const closeClass =
    'inline-flex size-8 shrink-0 items-center justify-center rounded hover:bg-accent focus-visible:outline-2 focus-visible:outline-primary';
  if (mobile)
    return (
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger {...triggerProps}>
          <Info className="size-3.5" aria-hidden="true" />
        </SheetTrigger>
        <SheetContent
          side="bottom"
          showCloseButton={false}
          className="max-h-[85dvh] overflow-y-auto rounded-t-xl border-border p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]"
          lang={locale === 'zh' ? 'zh-CN' : 'en'}
        >
          <div className="flex items-start justify-between gap-3">
            <SheetTitle>{entry.title}</SheetTitle>
            <SheetClose className={closeClass} aria-label={copy.close}>
              <X className="size-4" aria-hidden="true" />
            </SheetClose>
          </div>
          <div>
            <p className="mb-1 text-sm font-semibold">{copy.definition}</p>
            <SheetDescription className="leading-relaxed">
              {entry.definition}
            </SheetDescription>
          </div>
          {body}
        </SheetContent>
      </Sheet>
    );
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger {...triggerProps}>
        <Info className="size-3.5" aria-hidden="true" />
      </PopoverTrigger>
      <PopoverContent
        align="end"
        sideOffset={8}
        className="max-h-[min(80dvh,var(--available-height))] w-[min(400px,calc(100vw-2rem))] overflow-y-auto border border-border p-5 shadow-xl"
        lang={locale === 'zh' ? 'zh-CN' : 'en'}
      >
        <div className="flex items-start justify-between gap-3">
          <PopoverTitle className="text-base">{entry.title}</PopoverTitle>
          <PopoverPrimitive.Close
            className={closeClass}
            aria-label={copy.close}
          >
            <X className="size-4" aria-hidden="true" />
          </PopoverPrimitive.Close>
        </div>
        <div>
          <p className="mb-1 font-semibold">{copy.definition}</p>
          <PopoverDescription className="leading-relaxed">
            {entry.definition}
          </PopoverDescription>
        </div>
        {body}
      </PopoverContent>
    </Popover>
  );
}
