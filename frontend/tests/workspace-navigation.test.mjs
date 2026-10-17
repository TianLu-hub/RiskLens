import assert from 'node:assert/strict';
import test from 'node:test';
import {
  sectionFromHash,
  workspaceSections,
  navigateToSection,
  subscribeToSection,
} from '../lib/workspace-navigation.ts';

test('module deep links select the corresponding workspace', () => {
  for (const section of workspaceSections)
    assert.equal(sectionFromHash(`#${section}`), section);
});

test('navigation notifies subscribers once and cleans up history listeners', (t) => {
  const originalWindow = globalThis.window;
  const events = new EventTarget();
  const pushes = [];
  const scrolls = [];
  const location = { hash: '#overview' };
  globalThis.window = {
    location,
    history: {
      pushState(_state, _title, hash) {
        pushes.push(hash);
        location.hash = hash;
      },
    },
    addEventListener: events.addEventListener.bind(events),
    removeEventListener: events.removeEventListener.bind(events),
    dispatchEvent: events.dispatchEvent.bind(events),
    scrollTo: (options) => scrolls.push(options),
  };
  t.after(() => {
    if (originalWindow === undefined) delete globalThis.window;
    else globalThis.window = originalWindow;
  });
  let notifications = 0;
  const unsubscribe = subscribeToSection(() => notifications++);
  navigateToSection('stress-testing');
  navigateToSection('stress-testing');
  assert.deepEqual(pushes, ['#stress-testing']);
  assert.equal(notifications, 1);
  assert.equal(scrolls.length, 2);
  events.dispatchEvent(new Event('popstate'));
  assert.equal(notifications, 2);
  unsubscribe();
  events.dispatchEvent(new Event('popstate'));
  events.dispatchEvent(new Event('hashchange'));
  assert.equal(notifications, 2);
});

test('legacy chart links and unknown hashes fall back to overview', () => {
  for (const hash of [
    '',
    '#contribution',
    '#correlation',
    '#drawdown',
    '#unknown',
  ]) {
    assert.equal(sectionFromHash(hash), 'overview');
  }
});
