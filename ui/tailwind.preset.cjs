/**
 * @koko/ui Tailwind preset.
 *
 * Keep in sync with tokens/*.ts — this preset is CommonJS so it inlines the
 * literal values instead of importing the TypeScript token files.
 *
 * Usage in a consumer's tailwind.config.js:
 *
 *   module.exports = {
 *     presets: [require('@koko/ui/tailwind.preset')],
 *     content: ['./src/**\/*.{ts,tsx}', './node_modules/@koko/ui/**\/*.{ts,tsx}'],
 *   };
 */

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './components/**/*.{ts,tsx}',
    './patterns/**/*.{ts,tsx}',
    './icons/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Brand — KOKO emerald + warm gold accent
        'koko-primary': '#0F5132',
        'koko-primary-dark': '#0A3D24',
        'koko-primary-light': '#1A7A4F',
        'koko-accent': '#D4A047',

        // Confidence (cero datos inventados)
        'confidence-alta': '#16A34A',
        'confidence-media': '#F59E0B',
        'confidence-baja': '#F97316',
        'confidence-insuficiente': '#71717A',
        'confidence-alta-bg': '#DCFCE7',
        'confidence-media-bg': '#FEF3C7',
        'confidence-baja-bg': '#FFEDD5',
        'confidence-insuficiente-bg': '#F4F4F5',
        'confidence-alta-text': '#14532D',
        'confidence-media-text': '#78350F',
        'confidence-baja-text': '#7C2D12',
        'confidence-insuficiente-text': '#3F3F46',

        // Grayscale (zinc-family)
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

        // Semantic — light / base / dark
        success: {
          light: '#DCFCE7',
          DEFAULT: '#16A34A',
          dark: '#15803D',
        },
        warning: {
          light: '#FEF3C7',
          DEFAULT: '#F59E0B',
          dark: '#B45309',
        },
        danger: {
          light: '#FEE2E2',
          DEFAULT: '#DC2626',
          dark: '#B91C1C',
        },
        info: {
          light: '#DBEAFE',
          DEFAULT: '#2563EB',
          dark: '#1D4ED8',
        },

        // Surface
        'surface-page': '#FFFFFF',
        'surface-muted': '#FAFAFA',
        'surface-subtle': '#F4F4F5',
        'surface-overlay': 'rgba(9, 9, 11, 0.5)',

        // Border
        'border-default': '#E4E4E7',
        'border-strong': '#D4D4D8',
        'border-focus': '#0F5132',

        // Text
        'text-primary': '#18181B',
        'text-secondary': '#52525B',
        'text-tertiary': '#71717A',
        'text-inverse': '#FFFFFF',
        'text-disabled': '#A1A1AA',
      },

      fontFamily: {
        display: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },

      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.875rem', { lineHeight: '1.25rem' }],
        base: ['1rem', { lineHeight: '1.5rem' }],
        lg: ['1.125rem', { lineHeight: '1.75rem' }],
        xl: ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
        '5xl': ['3rem', { lineHeight: '1.1' }],
        '6xl': ['3.75rem', { lineHeight: '1.05' }],
        'display-sm': [
          '2.5rem',
          { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '700' },
        ],
        'display-md': [
          '3.5rem',
          { lineHeight: '1.05', letterSpacing: '-0.025em', fontWeight: '700' },
        ],
        'display-lg': [
          '4.5rem',
          { lineHeight: '1', letterSpacing: '-0.03em', fontWeight: '700' },
        ],
      },

      fontWeight: {
        regular: '400',
        medium: '500',
        semibold: '600',
        bold: '700',
      },

      letterSpacing: {
        tight: '-0.02em',
        normal: '0',
        wide: '0.02em',
      },

      spacing: {
        0: '0',
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        5: '20px',
        6: '24px',
        8: '32px',
        10: '40px',
        12: '48px',
        16: '64px',
        20: '80px',
        24: '96px',
      },

      borderRadius: {
        none: '0',
        xs: '2px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '24px',
        full: '9999px',
      },

      boxShadow: {
        xs: '0 1px 2px 0 rgba(15, 81, 50, 0.04)',
        sm: '0 1px 3px 0 rgba(15, 81, 50, 0.06), 0 1px 2px -1px rgba(15, 81, 50, 0.04)',
        md: '0 4px 8px -2px rgba(15, 81, 50, 0.08), 0 2px 4px -2px rgba(15, 81, 50, 0.04)',
        lg: '0 12px 20px -4px rgba(15, 81, 50, 0.10), 0 4px 8px -4px rgba(15, 81, 50, 0.06)',
        xl: '0 24px 40px -8px rgba(15, 81, 50, 0.12), 0 8px 16px -8px rgba(15, 81, 50, 0.08)',
        focus: '0 0 0 3px rgba(15, 81, 50, 0.25)',
        none: 'none',
      },

      zIndex: {
        base: '0',
        raised: '10',
        dropdown: '1000',
        sticky: '1100',
        overlay: '1200',
        modal: '1300',
        popover: '1400',
        tooltip: '1500',
        toast: '1600',
      },

      screens: {
        xs: '360px',
        sm: '480px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
        '2xl': '1536px',
      },

      transitionDuration: {
        instant: '0ms',
        fast: '120ms',
        base: '200ms',
        moderate: '300ms',
        slow: '480ms',
      },

      transitionTimingFunction: {
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
        emphasized: 'cubic-bezier(0.3, 0, 0, 1)',
        decelerate: 'cubic-bezier(0, 0, 0, 1)',
        accelerate: 'cubic-bezier(0.3, 0, 1, 1)',
      },
    },
  },
  plugins: [],
};
