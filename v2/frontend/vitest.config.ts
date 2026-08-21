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
    setupFiles: './src/test/setup.js',
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
      // Ratchet de cobertura fixado no baseline REAL medido (2026-08), não numa meta
      // aspiracional. O gate estava DORMENTE — o CI rodava `vitest` sem `--coverage`,
      // então os 70% nunca eram avaliados e a cobertura real caiu para ~42%. Ligar em
      // 70% reprovaria o CI na hora; fixar no piso atual TRAVA a regressão (nenhum PR
      // baixa a cobertura) e sobe por ratchet conforme os testes entram.
      thresholds: {
        statements: 40,
        branches: 31,
        functions: 29,
        lines: 41,
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
});
