/** @type {import('dependency-cruiser').CruiseOptions} */
module.exports = {
  options: {
    includeOnly: '^src',
    tsConfig: {
      fileName: 'tsconfig.json',
    },
    doNotFollow: {
      path: '^node_modules',
    },
    exclude: {
      path: [
        '^src/test/',
        '\\.test\\.[jt]sx?$',
        '\\.spec\\.[jt]sx?$',
      ],
    },
  },
  forbidden: [
    {
      name: 'no-circular-dependencies',
      severity: 'error',
      comment: 'Evita regressao com ciclos de import no frontend.',
      from: { path: '^src' },
      to: { circular: true },
    },
    {
      name: 'no-runtime-import-from-tests',
      severity: 'error',
      comment: 'Codigo de runtime nao deve importar codigo de teste.',
      from: { path: '^src/(?!test/)' },
      to: { path: '(^src/test/|\\.test\\.[jt]sx?$|\\.spec\\.[jt]sx?$)' },
    },
    {
      name: 'no-entrypoint-imports',
      severity: 'error',
      comment: 'Modulos internos nao devem depender de App/main entrypoints.',
      from: {
        path: '^src/(api|components|constants|contexts|hooks|pages|services|types|utils|data)/',
      },
      to: { path: '^src/(App\\.tsx|main\\.tsx)$' },
    },
  ],
};
