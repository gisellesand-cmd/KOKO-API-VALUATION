/**
 * KOKO border radius tokens.
 * Keep in sync with tailwind.preset.cjs.
 */
export const radii = {
  none: '0',
  xs: '2px',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  full: '9999px',
} as const;

export type Radii = typeof radii;
