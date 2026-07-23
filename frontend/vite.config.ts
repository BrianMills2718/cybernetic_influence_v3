import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  plugins: [react()],
  define: {
    'process.env.NODE_ENV': '"production"',
  },
  build: {
    outDir: fileURLToPath(new URL('../web', import.meta.url)),
    emptyOutDir: false,
    cssCodeSplit: false,
    lib: {
      entry: fileURLToPath(new URL('./src/main.tsx', import.meta.url)),
      name: 'CyberneticGraphBundle',
      formats: ['iife'],
      fileName: () => 'graph-canvas.js',
    },
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) =>
          assetInfo.name?.endsWith('.css') ? 'graph-canvas.css' : '[name][extname]',
      },
    },
  },
})
