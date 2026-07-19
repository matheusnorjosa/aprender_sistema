import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

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
  // confunde o `use()` de fixture com hook) — follow-up. Regras estilísticas
  // ruidosas (no-explicit-any: 63 ocorrências) ficam `warn`; endurecer é
  // follow-up incremental.
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
      },
    },
    rules: {
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        { varsIgnorePattern: '^[A-Z_]', argsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      // DX de Fast-Refresh (HMR), não correção — arquivos que exportam um
      // componente + util (ex: PerfilPage + maskCpf). Fica `warn`.
      'react-refresh/only-export-components': 'warn',
    },
  },
])
