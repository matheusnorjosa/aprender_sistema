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
      // Grupo B — promise-safety (a classe de falha silenciosa que motiva o programa).
      // Promise não-tratada = erro engolido sem UI/log. Convenção do projeto: `void`
      // para fire-and-forget intencional (o handler/efeito não pode ser async e a fn
      // chamada já trata o próprio erro), `.catch(...)` quando o erro precisa aflorar.
      '@typescript-eslint/no-floating-promises': 'error',
      // Grupo C — no-misused-promises. `checksVoidReturn.attributes/properties:false`
      // porque handler async em atributo JSX (onClick={async...}) e em objeto-config de
      // handlers (ColumnHandlers, getColumns({onEdit,onDelete})) é idioma legítimo do React
      // — o React/AntD não aguarda o retorno e nossos handlers já tratam o próprio erro
      // (try/catch + message/logger). As checagens de VALOR seguem ATIVAS: `arguments`
      // (Promise passada a callback void — ex.: setTimeout(async...)), `conditionals`
      // (Promise num if/&&) e `spreads`. Os sites de `arguments` foram corrigidos no código.
      '@typescript-eslint/no-misused-promises': [
        'error',
        { checksVoidReturn: { attributes: false, properties: false } },
      ],
      // Grupo D — require-await: função async sem await = async ocioso (ou await
      // esquecido). Em PROD trava o smell; nos testes é DESLIGADO abaixo (mocks
      // `async () => data` são async de propósito p/ o contrato Promise).
      '@typescript-eslint/require-await': 'error',
      // Grupo E — no-unsafe-* (type-safety ponta a ponta): valor `any` fluindo = buraco
      // de tipo (acesso/atribuição/retorno/argumento/chamada). Fontes externas não-tipadas
      // (`response.json()`/`JSON.parse`/`import.meta.env`) recebem cast p/ a shape real;
      // respostas de API ganham interface (ex.: `MonthlyGridData = MonthlyGridResponse`).
      // DESLIGADO em testes (fixtures/mocks são frouxos por natureza) — override abaixo.
      '@typescript-eslint/no-unsafe-member-access': 'error',
      '@typescript-eslint/no-unsafe-assignment': 'error',
      '@typescript-eslint/no-unsafe-argument': 'error',
      '@typescript-eslint/no-unsafe-return': 'error',
      '@typescript-eslint/no-unsafe-call': 'error',
      // DX de Fast-Refresh (HMR), não correção — arquivos que exportam um
      // componente + util (ex: PerfilPage + maskCpf). Fica `warn`.
      'react-refresh/only-export-components': 'warn',
    },
  },
  // Testes: regras type-aware frouxas — mocks/fakes/fixtures usam `async () => data`
  // sem await (contrato Promise) e dados `any` de propósito. O parser/plugin type-aware
  // do bloco src/** acima continua valendo (só sobrescreve as regras). Prod segue ATIVO.
  {
    files: [
      'src/**/*.{test,spec}.{ts,tsx}',
      'src/**/__tests__/**/*.{ts,tsx}',
      'src/test/**/*.{ts,tsx}',
    ],
    rules: {
      '@typescript-eslint/require-await': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-argument': 'off',
      '@typescript-eslint/no-unsafe-return': 'off',
      '@typescript-eslint/no-unsafe-call': 'off',
    },
  },
])
