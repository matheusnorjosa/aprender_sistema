import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    // Mitigacao de flakiness do suite: alguns testes de componente sao sensiveis a
    // timing (findByRole estoura sob carga do CI) e a isolamento no `singleThread`
    // (ex.: DatImportsLegacyRemoval, useTableFilters), falhando de forma nao-
    // deterministica e bloqueando ate PRs que nem tocam o frontend (#1691/#1696).
    // `retry` re-executa o teste que falha; uma falha DETERMINISTICA continua falhando
    // (todas as tentativas falham). Estabilizar cada teste na fonte e' follow-up.
    retry: 2,
    environment: 'jsdom',
    // Run jsdom under HTTPS so tests that set `Secure` cookies (frontend hardening
    // against CodeQL js/clear-text-cookie) are accepted by the cookie jar.
    environmentOptions: {
      jsdom: {
        url: 'https://localhost/',
      },
    },
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.{test,spec}.{js,jsx,ts,tsx}'],
    exclude: ['**/node_modules/**', '**/dist/**', '**/e2e/**'],
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: true,
      },
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.{js,jsx,ts,tsx}'],
      exclude: [
        'node_modules/',
        'src/test/**',
        '**/*.config.{js,ts}',
        '**/dist/**',
        '**/*.test.{js,jsx,ts,tsx}',
        '**/*.spec.{js,jsx,ts,tsx}',
        '**/e2e/**',
        'src/main.tsx',
      ],
      // Ratchet de cobertura fixado no baseline REAL medido, não numa meta aspiracional.
      // O gate estava DORMENTE (CI rodava `vitest` sem `--coverage`); ligado em #1800 no
      // piso de então (~42%). Sobe a cada leva de testes: #1815 (clientes de API) + #1816
      // (hooks) levaram a 44/34/32/44; agora, pós #1825 (4 páginas críticas), o suite mede
      // 45.33/35.29/33.68/45.85 — fixado ~0.3-0.8pt abaixo pra travar a regressão sem
      // reprovar por flutuação. Cobertura é determinística num suite verde, então a margem
      // só protege de teste flaky que perca as retries.
      thresholds: {
        statements: 45,
        branches: 35,
        functions: 33,
        lines: 45,
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
});
