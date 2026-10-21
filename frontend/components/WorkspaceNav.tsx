'use client';
import { useLanguage } from '@/components/LanguageProvider';

import {
  Activity,
  BarChart3,
  BrainCircuit,
  FlaskConical,
  History,
  ShieldCheck,
  SlidersHorizontal,
} from 'lucide-react';
import {
  navigateToSection,
  type WorkspaceSection,
} from '@/lib/workspace-navigation';

export const workspaceViews = [
  {
    id: 'overview',
    label: 'Overview',
    title: 'Portfolio overview',
    description: 'Historical risk, in perspective.',
    icon: BarChart3,
  },
  {
    id: 'stress-testing',
    label: 'Stress tests',
    title: 'Stress testing',
    description: 'Explore hypothetical shocks and their portfolio impact.',
    icon: FlaskConical,
  },
  {
    id: 'factor-exposure',
    label: 'Factor exposure',
    title: 'Factor exposure',
    description: 'Understand your historical sensitivity to the market.',
    icon: Activity,
  },
  {
    id: 'optimization',
    label: 'Optimization',
    title: 'Portfolio optimization',
    description: 'Compare allocations without changing your holdings.',
    icon: SlidersHorizontal,
  },
  {
    id: 'backtest',
    label: 'Backtest',
    title: 'Walk-forward backtest',
    description: 'Train on the past. Evaluate on subsequent observations.',
    icon: History,
  },
  {
    id: 'var-backtest',
    label: 'VaR validation',
    title: 'VaR model backtest',
    description: 'Compare past-only risk estimates with the next trading day.',
    icon: ShieldCheck,
  },
  {
    id: 'risk-officer',
    label: 'Risk Officer',
    title: 'Ask your Risk Officer',
    description: 'Explore the evidence behind your portfolio risks.',
    icon: BrainCircuit,
  },
] satisfies {
  id: WorkspaceSection;
  label: string;
  title: string;
  description: string;
  icon: typeof Activity;
}[];

export function WorkspaceNav({ active }: { active: WorkspaceSection }) {
  const { t } = useLanguage();
  return (
    <nav
      aria-label={t('Workspace sections')}
      className="flex gap-1 overflow-x-auto border-b border-border p-2 lg:flex-col lg:p-3"
    >
      {workspaceViews.map(({ id, label, icon: Icon }) => (
        <a
          key={id}
          href={`#${id}`}
          aria-current={active === id ? 'page' : undefined}
          onClick={(event) => {
            if (
              event.metaKey ||
              event.ctrlKey ||
              event.shiftKey ||
              event.altKey
            )
              return;
            event.preventDefault();
            navigateToSection(id);
          }}
          className={`flex shrink-0 items-center gap-3 rounded-md border-l-2 px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${active === id ? 'border-primary bg-primary/10 text-primary' : 'border-transparent text-muted-foreground hover:bg-accent hover:text-foreground'}`}
        >
          <Icon className="size-4 shrink-0" aria-hidden="true" />
          {t(label)}
        </a>
      ))}
    </nav>
  );
}
