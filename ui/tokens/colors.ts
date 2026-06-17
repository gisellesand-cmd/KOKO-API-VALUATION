/**
 * KOKO color tokens.
 *
 * Real-estate premium palette: deep emerald greens with a warm gold accent.
 * Neutral grayscale (zinc family) for surfaces and text.
 * Semantic colors for feedback states.
 * Confidence colors map to the "cero datos inventados" principle:
 * alta (≥8 comparables), media (4-7), baja (1-3), insuficiente (0).
 *
 * Keep in sync with tailwind.preset.cjs.
 */
export const colors = {
  brand: {
    primary: '#0F5132',
    primaryDark: '#0A3D24',
    primaryLight: '#1A7A4F',
    accent: '#D4A047',
  },
  gray: {
    50: '#FAFAFA',
    100: '#F4F4F5',
    200: '#E4E4E7',
    300: '#D4D4D8',
    400: '#A1A1AA',
    500: '#71717A',
    600: '#52525B',
    700: '#3F3F46',
    800: '#27272A',
    900: '#18181B',
    950: '#09090B',
  },
  semantic: {
    success: {
      light: '#DCFCE7',
      base: '#16A34A',
      dark: '#15803D',
    },
    warning: {
      light: '#FEF3C7',
      base: '#F59E0B',
      dark: '#B45309',
    },
    danger: {
      light: '#FEE2E2',
      base: '#DC2626',
      dark: '#B91C1C',
    },
    info: {
      light: '#DBEAFE',
      base: '#2563EB',
      dark: '#1D4ED8',
    },
  },
  confidence: {
    alta: {
      base: '#16A34A',
      bg: '#DCFCE7',
      text: '#14532D',
    },
    media: {
      base: '#F59E0B',
      bg: '#FEF3C7',
      text: '#78350F',
    },
    baja: {
      base: '#F97316',
      bg: '#FFEDD5',
      text: '#7C2D12',
    },
    insuficiente: {
      base: '#71717A',
      bg: '#F4F4F5',
      text: '#3F3F46',
    },
  },
  surface: {
    page: '#FFFFFF',
    muted: '#FAFAFA',
    subtle: '#F4F4F5',
    overlay: 'rgba(9, 9, 11, 0.5)',
  },
  border: {
    default: '#E4E4E7',
    strong: '#D4D4D8',
    focus: '#0F5132',
  },
  text: {
    primary: '#18181B',
    secondary: '#52525B',
    tertiary: '#71717A',
    inverse: '#FFFFFF',
    disabled: '#A1A1AA',
  },
} as const;

export type Colors = typeof colors;
export type ConfidenceLevel = keyof typeof colors.confidence;
