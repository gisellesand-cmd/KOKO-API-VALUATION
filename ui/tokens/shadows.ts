/**
 * KOKO elevation tokens.
 *
 * Shadows are tinted with the brand emerald (0F5132) at low alpha so elevation
 * feels native to the palette instead of generic gray-black.
 * `focus` is the 3px ring used by all interactive primitives.
 *
 * Keep in sync with tailwind.preset.cjs.
 */
export const shadows = {
  xs: '0 1px 2px 0 rgba(15, 81, 50, 0.04)',
  sm: '0 1px 3px 0 rgba(15, 81, 50, 0.06), 0 1px 2px -1px rgba(15, 81, 50, 0.04)',
  md: '0 4px 8px -2px rgba(15, 81, 50, 0.08), 0 2px 4px -2px rgba(15, 81, 50, 0.04)',
  lg: '0 12px 20px -4px rgba(15, 81, 50, 0.10), 0 4px 8px -4px rgba(15, 81, 50, 0.06)',
  xl: '0 24px 40px -8px rgba(15, 81, 50, 0.12), 0 8px 16px -8px rgba(15, 81, 50, 0.08)',
  focus: '0 0 0 3px rgba(15, 81, 50, 0.25)',
  none: 'none',
} as const;

export type Shadows = typeof shadows;
