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
    // timing (findByRole estoura sob carga do CI) e a isolamento entre arquivos
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
    // Sem limite de workers: o Vitest 4 usa N-1 núcleos (3 no runner de 4 vCPU). O antigo
    // `poolOptions.threads.singleThread` foi removido no Vitest 4 e nunca valeu aqui (o CI só
    // imprimia DEPRECATED). NÃO trocar por `maxWorkers: 1`/`fileParallelism: false`: a suíte
    // ficaria serial (~3x mais lenta). O CI ganha tempo dividindo a suíte em partes (frontend-ci.yml).
    pool: 'threads',
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
      // Piso de cobertura, aplicado na junção das partes do Vitest na CI (frontend-ci.yml).
      // Regra: o menor valor de cada métrica na junção do próprio PR e nas 2 junções verdes
      // mais recentes (linha "All files" do log), arredondado para baixo, menos 2 pontos.
      // Quem acrescenta testes sobe o piso num commit final do PR, com a CI verde; baixar só
      // com justificativa no PR. Comando e detalhes: v2/docs/TESTING_POLICY.md, seção Cobertura.
      // FER-55, 13/11/2026: runs 43472545900, 43469156123 e 43466157890 → mínimo
      // 81.69/74.08/75.77/82.92 → 79/72/73/80 (a junção do #2229, base deste PR, mede o mesmo).
      thresholds: {
        statements: 99,
        branches: 72,
        functions: 73,
        lines: 80,
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
});
