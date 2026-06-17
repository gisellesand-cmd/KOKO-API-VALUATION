/**
 * KOKO design tokens — barrel.
 *
 * Re-exports every token group and a combined `tokens` object for ergonomic
 * consumption (e.g. `import { tokens } from '@koko/ui/tokens'`).
 */
export * from './colors';
export * from './typography';
export * from './spacing';
export * from './radii';
export * from './shadows';
export * from './zIndex';
export * from './breakpoints';
export * from './motion';

import { colors } from './colors';
import { typography } from './typography';
import { spacing } from './spacing';
import { radii } from './radii';
import { shadows } from './shadows';
import { zIndex } from './zIndex';
import { breakpoints } from './breakpoints';
import { motion } from './motion';

export const tokens = {
  colors,
  typography,
  spacing,
  radii,
  shadows,
  zIndex,
  breakpoints,
  motion,
} as const;

export type Tokens = typeof tokens;

export default tokens;
