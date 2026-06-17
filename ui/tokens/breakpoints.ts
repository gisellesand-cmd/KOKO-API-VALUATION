/**
 * KOKO breakpoints. Mobile-first (70% of widget traffic is mobile).
 * Keep in sync with tailwind.preset.cjs.
 */
export const breakpoints = {
  xs: '360px',
  sm: '480px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

export type Breakpoints = typeof breakpoints;
