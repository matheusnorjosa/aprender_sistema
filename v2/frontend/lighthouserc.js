/**
 * Lighthouse CI Configuration
 *
 * CHECKLIST_FRONTEND.md - Lighthouse Score (Mínimo):
 * - 🔴 Performance: ≥ 70
 * - 🔴 Accessibility: ≥ 90
 * - 🟡 Best Practices: ≥ 90
 * - 🟡 SEO: ≥ 90
 *
 * Documentação: https://github.com/GoogleChrome/lighthouse-ci
 */

module.exports = {
  ci: {
    collect: {
      // Número de execuções por URL (média dos resultados)
      numberOfRuns: 3,

      // URLs para testar
      url: ['http://localhost:5173/'],

      // Configurações do Lighthouse
      settings: {
        // Preset de desktop (mais rápido que mobile)
        preset: 'desktop',

        // Categorias para auditar
        onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],

        // Throttling moderado para CI
        throttling: {
          cpuSlowdownMultiplier: 2,
        },

        // Skip audits que requerem rede real
        skipAudits: [
          'uses-http2',
          'uses-long-cache-ttl',
          'canonical',
        ],
      },

      // Comando para iniciar o servidor
      startServerCommand: 'npm run preview',
      startServerReadyPattern: 'Local:',
      startServerReadyTimeout: 30000,
    },

    assert: {
      // Assertions baseadas no CHECKLIST_FRONTEND.md
      assertions: {
        // 🔴 Performance ≥ 70
        'categories:performance': ['error', { minScore: 0.7 }],

        // 🔴 Accessibility ≥ 90
        'categories:accessibility': ['error', { minScore: 0.9 }],

        // 🟡 Best Practices ≥ 90
        'categories:best-practices': ['warn', { minScore: 0.9 }],

        // 🟡 SEO ≥ 90
        'categories:seo': ['warn', { minScore: 0.9 }],

        // Core Web Vitals - 🔴
        'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        'total-blocking-time': ['error', { maxNumericValue: 300 }],

        // 🔴 Acessibilidade crítica
        'color-contrast': 'error',
        'image-alt': 'error',
        'label': 'error',
        'button-name': 'error',
        'link-name': 'error',
        'html-has-lang': 'error',
        'document-title': 'error',
        'meta-viewport': 'error',

        // 🟡 Boas práticas
        'viewport': 'warn',
        'charset': 'warn',
        'doctype': 'warn',

        // 🟢 Nice to have (não falha)
        'structured-data': 'off',
        'robots-txt': 'off',
      },
    },

    upload: {
      // Armazenamento local (sem servidor LHCI)
      target: 'filesystem',
      outputDir: '.lighthouseci',

      // Alternativa: usar temporary-public-storage para PRs
      // target: 'temporary-public-storage',
    },
  },
};
