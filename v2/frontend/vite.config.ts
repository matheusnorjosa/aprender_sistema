import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import { existsSync } from 'fs'

// Backend URL para proxy (servidor-side apenas)
// PROXY_TARGET é usado apenas pelo servidor Vite, não pelo browser
const isDocker = existsSync('/.dockerenv')
const API_URL: string = process.env.PROXY_TARGET || (isDocker ? 'http://web:8000' : 'http://localhost:8002')

// Gap 8 - PLAN_maturity_gaps.md: Bundle analysis
const ANALYZE: boolean = process.env.ANALYZE === 'true'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Bundle visualizer - generates stats.html when ANALYZE=true
    ANALYZE && visualizer({
      filename: 'dist/stats.html',
      open: true,
      gzipSize: true,
      brotliSize: true,
      template: 'treemap', // 'sunburst', 'treemap', 'network'
    }),
  ].filter(Boolean),
  server: {
    host: true, // Permite acesso externo (necessário para Docker)
    // Vite 7 bloqueia hosts desconhecidos por padrão; liberar host do compose
    // evita resposta "Blocked request" nos testes E2E rodando em container.
    allowedHosts: ['frontend', 'localhost', '127.0.0.1'],
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
          // Vendor chunks - separar bibliotecas pesadas para cache e paralelismo
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-antd': ['antd'],
          'vendor-antd-icons': ['@ant-design/icons'],
          'vendor-leaflet': ['leaflet', 'react-leaflet'],
        },
      },
    },
    // Aumentar limite de warning para 600kB (após splitting)
    chunkSizeWarningLimit: 600,
    // CSS code splitting — carrega CSS por chunk em vez de inline
    cssCodeSplit: true,
  },
})
