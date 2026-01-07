/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend URL para proxy (servidor-side apenas)
// PROXY_TARGET é usado apenas pelo servidor Vite, não pelo browser
// eslint-disable-next-line no-undef
const API_URL = process.env.PROXY_TARGET || 'http://localhost:8002'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    include: ['src/**/*.{test,spec}.{js,jsx,ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{js,jsx}'],
      exclude: [
        'src/test/**',
        'src/main.jsx',
        'src/**/*.test.{js,jsx}',
        'src/**/*.spec.{js,jsx}',
      ],
    },
  },
  server: {
    host: true, // Permite acesso externo (necessário para Docker)
    port: 5173,
    watch: {
      usePolling: true, // Necessário para HMR funcionar em Docker no Windows
    },
    proxy: {
      '/api': {
        target: API_URL,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks - separar bibliotecas pesadas
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-antd': ['antd', '@ant-design/icons'],
          'vendor-leaflet': ['leaflet', 'react-leaflet'],
        },
      },
    },
    // Aumentar limite de warning para 600kB (após splitting)
    chunkSizeWarningLimit: 600,
  },
})
