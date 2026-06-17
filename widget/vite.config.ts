import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'node:path';

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'es2019',
    cssCodeSplit: false,
    sourcemap: true,
    lib: {
      entry: resolve(__dirname, 'src/main.tsx'),
      name: 'KokoValuationWidget',
      formats: ['umd'],
      fileName: () => 'koko-valuation-widget.js',
    },
    rollupOptions: {
      output: {
        assetFileNames: (asset) => {
          if (asset.name && asset.name.endsWith('.css')) {
            return 'koko-valuation-widget.css';
          }
          return 'assets/[name]-[hash][extname]';
        },
        inlineDynamicImports: true,
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
        },
      },
    },
  },
  server: {
    port: 5173,
    open: '/demo.html',
  },
});
