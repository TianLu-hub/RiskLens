export const workspaceSections = [
  'overview',
  'stress-testing',
  'factor-exposure',
  'optimization',
  'backtest',
  'risk-officer',
] as const;
export type WorkspaceSection = (typeof workspaceSections)[number];

/** Keep existing shared chart links working inside the new overview workspace. */
export function sectionFromHash(hash: string): WorkspaceSection {
  const section = hash.replace(/^#/, '');
  return workspaceSections.find((item) => item === section) ?? 'overview';
}

export function subscribeToSection(onChange: () => void): () => void {
  window.addEventListener('hashchange', onChange);
  window.addEventListener('popstate', onChange);
  return () => {
    window.removeEventListener('hashchange', onChange);
    window.removeEventListener('popstate', onChange);
  };
}

export function getCurrentSection(): WorkspaceSection {
  return sectionFromHash(window.location.hash);
}

export function getServerSection(): WorkspaceSection {
  return 'overview';
}

export function navigateToSection(section: WorkspaceSection): void {
  if (window.location.hash !== `#${section}`) {
    window.history.pushState(null, '', `#${section}`);
    window.dispatchEvent(new Event('hashchange'));
  }
  window.scrollTo({ top: 0, behavior: 'instant' });
}
