/**
 * KOKO motion tokens.
 *
 * Curves follow Material 3 emphasis principles: `standard` for most interaction,
 * `emphasized` for state changes that should feel deliberate (revealing a result),
 * `decelerate` for entrances, `accelerate` for exits.
 *
 * Keep in sync with tailwind.preset.cjs.
 */
export const motion = {
  duration: {
    instant: '0ms',
    fast: '120ms',
    base: '200ms',
    moderate: '300ms',
    slow: '480ms',
  },
  easing: {
    standard: 'cubic-bezier(0.2, 0, 0, 1)',
    emphasized: 'cubic-bezier(0.3, 0, 0, 1)',
    decelerate: 'cubic-bezier(0, 0, 0, 1)',
    accelerate: 'cubic-bezier(0.3, 0, 1, 1)',
  },
} as const;

export type Motion = typeof motion;
