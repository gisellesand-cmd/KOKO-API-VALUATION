/** @type {import('tailwindcss').Config} */
export default {
  prefix: 'koko-',
  important: '[data-koko-widget]',
  content: ['./index.html', './demo.html', './src/**/*.{ts,tsx}'],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        koko: {
          primary: 'var(--koko-primary, #0E4F39)',
          'primary-hover': 'var(--koko-primary-hover, #0a3b2b)',
          'primary-soft': 'var(--koko-primary-soft, #E6F1ED)',
          ink: '#1B1F23',
          muted: '#5F6B7A',
          line: '#E5E7EB',
          surface: '#FFFFFF',
          bg: '#F7F8FA',
          danger: '#B42318',
          warning: '#B54708',
          warningSoft: '#FEF6E7',
          success: '#067647',
          successSoft: '#ECFDF3',
          orange: '#C4320A',
          orangeSoft: '#FFF4ED',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      boxShadow: {
        card: '0 4px 24px -8px rgba(15, 23, 42, 0.12)',
      },
      borderRadius: {
        koko: '14px',
      },
    },
  },
  plugins: [],
};
