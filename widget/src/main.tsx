import React from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { KokoValuationWidget } from './components/KokoValuationWidget';
import type { Locale, MountOptions } from './types';
import './styles/index.css';

const ROOTS = new WeakMap<Element, Root>();

function applyPrimaryColor(element: HTMLElement, primaryColor?: string): void {
  if (!primaryColor) return;
  element.style.setProperty('--koko-primary', primaryColor);
  element.style.setProperty('--koko-primary-hover', primaryColor);
}

function mount(element: Element | null, options: MountOptions): () => void {
  if (!element) {
    throw new Error('[KokoValuationWidget] target element is null');
  }
  if (!options || !options.apiUrl) {
    throw new Error('[KokoValuationWidget] apiUrl is required');
  }

  const host = element as HTMLElement;
  host.setAttribute('data-koko-widget', '');
  applyPrimaryColor(host, options.primaryColor);

  const existing = ROOTS.get(element);
  if (existing) existing.unmount();

  const root = createRoot(element);
  ROOTS.set(element, root);

  const locale: Locale = options.locale ?? 'es';

  root.render(
    <React.StrictMode>
      <KokoValuationWidget
        apiUrl={options.apiUrl.replace(/\/$/, '')}
        locale={locale}
        primaryColor={options.primaryColor}
        onCompleted={options.onCompleted}
      />
    </React.StrictMode>,
  );

  return () => {
    root.unmount();
    ROOTS.delete(element);
  };
}

function unmount(element: Element | null): void {
  if (!element) return;
  const root = ROOTS.get(element);
  if (root) {
    root.unmount();
    ROOTS.delete(element);
  }
}

const api = { mount, unmount, version: '0.1.0' };

if (typeof window !== 'undefined') {
  // Expose mount API on window for <script src=...> embedding
  (window as unknown as { KokoValuationWidget: typeof api }).KokoValuationWidget = api;
}

export { KokoValuationWidget } from './components/KokoValuationWidget';
export default api;
