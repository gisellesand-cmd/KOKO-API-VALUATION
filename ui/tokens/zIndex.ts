/**
 * KOKO z-index stacking scale.
 * Keep in sync with tailwind.preset.cjs.
 */
export const zIndex = {
  base: 0,
  raised: 10,
  dropdown: 1000,
  sticky: 1100,
  overlay: 1200,
  modal: 1300,
  popover: 1400,
  tooltip: 1500,
  toast: 1600,
} as const;

export type ZIndex = typeof zIndex;
