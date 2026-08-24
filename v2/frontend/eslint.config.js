import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'
import { fileURLToPath } from 'node:url'

export default defineConfig([
  globalIgnores(['dist', 'lighthouserc.cjs']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
      },
    },
    rules: {
      'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z_]' }],
    },
  },
  // #1602: cobertura de lint para o app TypeScript (antes o flat config só
  // cobria .js/.jsx — todo o src/ .tsx passava sem lint). typescript-eslint
  // recommended sem type-checking (sem `project`) — rápido, não exige tsconfig
  // no lint. Escopo src/**: onde vive o app (e os callers de autz do #1281).
  // e2e/ (Playwright) precisa de override próprio (o plugin react-hooks
  // confunde o `use()` de fixture com hook) — follow-up. O sweep de tipagem
  // (DAT #1806) zerou os `any` de produção, então `no-explicit-any` passou a
  // `error` (trava regressão). Warnings de HMR/exhaustive-deps seguem `warn`.
  {
    files: ['src/**/*.{ts,tsx}'],
    extends: [
      tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaVersion: 'latest',
        ecmaFeatures: { jsx: true },
        sourceType: 'module',
        // Lint TYPE-AWARE (adoção incremental de recommendedTypeChecked). `project`
        // aponta p/ tsconfig.eslint.json — que INCLUI os testes (o tsconfig de build
        // os exclui, mas o eslint linta src/** inteiro; o parser type-aware exige que
        // todo arquivo lintado esteja num projeto). Habilita a info de tipos; as regras
        // type-aware entram uma por vez (por grupo) — ver `rules` abaixo.
        project: ['./tsconfig.eslint.json'],
        tsconfigRootDir: fileURLToPath(new URL('.', import.meta.url)),
      },
    },
    rules: {
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        { varsIgnorePattern: '^[A-Z_]', argsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      // Adoção incremental de recommendedTypeChecked (medido: 381 erros no total).
      // Grupo A (mecânico/seguro) LIGADO aqui: remove asserção de tipo redundante
      // (auto-fix) e simplifica união com constituinte redundante. Os grupos de alto
      // valor mas intent-heavy — no-floating-promises (101), no-misused-promises (93),
      // require-await (22) e no-unsafe-* (96) — entram em PRs dedicados de burn-down.
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/no-redundant-type-constituents': 'error',
      // DX de Fast-Refresh (HMR), não correção — arquivos que exportam um
      // componente + util (ex: PerfilPage + maskCpf). Fica `warn`.
      'react-refresh/only-export-components': 'warn',
    },
  },
])
