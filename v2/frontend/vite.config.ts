import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import license from 'rollup-plugin-license'
import { existsSync } from 'fs'
import { fileURLToPath } from 'node:url'

// Backend URL para proxy (servidor-side apenas)
// PROXY_TARGET é usado apenas pelo servidor Vite, não pelo browser
const isDocker = existsSync('/.dockerenv')
const API_URL: string = process.env.PROXY_TARGET || (isDocker ? 'http://web:8000' : 'http://localhost:8002')

// Gap 8 - PLAN_maturity_gaps.md: Bundle analysis
const ANALYZE: boolean = process.env.ANALYZE === 'true'

// FER-63: licenças das dependências que entram no bundle, geradas a cada build em
// dist/THIRD-PARTY-NOTICES.txt (servido em /THIRD-PARTY-NOTICES.txt). Só passam as licenças desta lista;
// qualquer outra, ou pacote sem licença, faz o build falhar e vai para o dono decidir (nada AGPL).
// Hippocratic-2.1: react-leaflet, aceita antes (memória reference-license-audit-agpl).
// Limite: o plugin só vê pacotes com código JS no bundle; um pacote que entre só como CSS, fonte ou
// imagem (ex.: @fontsource/*) não é checado e precisa de conferência à mão.
const LICENCAS_PERMITIDAS = '(MIT OR ISC OR 0BSD OR BSD-2-Clause OR BSD-3-Clause OR Apache-2.0 OR Hippocratic-2.1)'

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
    {
      ...license({
        thirdParty: {
          includePrivate: false,
          // Sem isto o plugin guarda só a 1ª versão de um pacote que entra em duas (ex.: @ant-design/icons
          // 5 e 6): a outra sairia do arquivo e da trava.
          multipleVersions: true,
          output: { file: fileURLToPath(new URL('./dist/THIRD-PARTY-NOTICES.txt', import.meta.url)) },
          allow: { test: LICENCAS_PERMITIDAS, failOnUnlicensed: true, failOnViolation: true },
        },
      }),
      apply: 'build' as const,
    },
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
    chunkSizeWarningLimit: 1500,
    // CSS code splitting — carrega CSS por chunk em vez de inline
    cssCodeSplit: true,
    // No source maps in production — sem Sentry, maps não têm uso remoto e
    // vazariam o código-fonte se servidos. Ver #1463 (audit 2026-06-19).
    sourcemap: false,
  },
})
