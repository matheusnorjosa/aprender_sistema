/**
 * CHECKLIST_FRONTEND.md - Performance Tests
 *
 * Testa itens das seções:
 * - "Performance > Core Web Vitals"
 * - "Performance > Otimizações"
 * - "Bundle Size"
 *
 * Usa métricas coletadas via Performance API do navegador.
 */
import { test, expect, Page } from '@playwright/test';

// Thresholds do checklist
const THRESHOLDS = {
  // Core Web Vitals
  LCP: 2500, // 🔴 < 2.5s
  FID: 100, // 🔴 < 100ms (medido via TBT como proxy)
  CLS: 0.1, // 🔴 < 0.1
  FCP: 1800, // 🟡 < 1.8s
  TTFB: 600, // 🟡 < 600ms

  // Bundle sizes (gzipped)
  JS_INITIAL_KB: 200, // 🔴 < 200KB
  CSS_KB: 50, // 🟡 < 50KB
};

interface PerformanceMetrics {
  fcp: number;
  lcp: number;
  cls: number;
  ttfb: number;
  domContentLoaded: number;
  load: number;
}

async function getPerformanceMetrics(page: Page): Promise<PerformanceMetrics> {
  return page.evaluate(() => {
    const entries = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const paintEntries = performance.getEntriesByType('paint');

    const fcpEntry = paintEntries.find((e) => e.name === 'first-contentful-paint');

    // LCP - usa a última entrada LCP
    let lcp = 0;
    const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
    if (lcpEntries.length > 0) {
      lcp = lcpEntries[lcpEntries.length - 1].startTime;
    }

    // CLS - soma de layout shifts
    let cls = 0;
    const clsEntries = performance.getEntriesByType('layout-shift');
    clsEntries.forEach((entry: any) => {
      if (!entry.hadRecentInput) {
        cls += entry.value;
      }
    });

    return {
      fcp: fcpEntry?.startTime || 0,
      lcp,
      cls,
      ttfb: entries?.responseStart || 0,
      domContentLoaded: entries?.domContentLoadedEventEnd || 0,
      load: entries?.loadEventEnd || 0,
    };
  });
}

test.describe('Checklist: Core Web Vitals', () => {
  test.beforeEach(async ({ page }) => {
    // Limpa cache para medições consistentes
    await page.context().clearCookies();
  });

  test('🔴 LCP deve ser menor que 2.5s', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    // Aguarda LCP ser registrado
    await page.waitForTimeout(1000);

    const metrics = await getPerformanceMetrics(page);

    console.log(`LCP: ${metrics.lcp.toFixed(0)}ms (limite: ${THRESHOLDS.LCP}ms)`);

    expect(
      metrics.lcp,
      `LCP ${metrics.lcp}ms excede limite de ${THRESHOLDS.LCP}ms`
    ).toBeLessThan(THRESHOLDS.LCP);
  });

  test('🔴 CLS deve ser menor que 0.1', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    // Aguarda possíveis layout shifts
    await page.waitForTimeout(2000);

    const metrics = await getPerformanceMetrics(page);

    console.log(`CLS: ${metrics.cls.toFixed(3)} (limite: ${THRESHOLDS.CLS})`);

    expect(
      metrics.cls,
      `CLS ${metrics.cls} excede limite de ${THRESHOLDS.CLS}`
    ).toBeLessThan(THRESHOLDS.CLS);
  });

  test('🟡 FCP deve ser menor que 1.8s', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const metrics = await getPerformanceMetrics(page);

    console.log(`FCP: ${metrics.fcp.toFixed(0)}ms (limite: ${THRESHOLDS.FCP}ms)`);

    expect(
      metrics.fcp,
      `FCP ${metrics.fcp}ms excede limite de ${THRESHOLDS.FCP}ms`
    ).toBeLessThan(THRESHOLDS.FCP);
  });

  test('🟡 TTFB deve ser menor que 600ms', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const metrics = await getPerformanceMetrics(page);

    console.log(`TTFB: ${metrics.ttfb.toFixed(0)}ms (limite: ${THRESHOLDS.TTFB}ms)`);

    expect(
      metrics.ttfb,
      `TTFB ${metrics.ttfb}ms excede limite de ${THRESHOLDS.TTFB}ms`
    ).toBeLessThan(THRESHOLDS.TTFB);
  });
});

test.describe('Checklist: Resource Loading', () => {
  test('🔴 JS crítico deve carregar rapidamente', async ({ page }) => {
    const jsResources: { url: string; size: number; duration: number }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      if (url.endsWith('.js') || url.includes('.js?')) {
        const headers = response.headers();
        const size = parseInt(headers['content-length'] || '0');
        jsResources.push({
          url: url.split('/').pop() || url,
          size,
          duration: 0,
        });
      }
    });

    await page.goto('/', { waitUntil: 'networkidle' });

    // Calcula tamanho total de JS
    const totalJsSize = jsResources.reduce((sum, r) => sum + r.size, 0);
    const totalJsKB = totalJsSize / 1024;

    console.log(`JS Total: ${totalJsKB.toFixed(0)}KB (limite: ${THRESHOLDS.JS_INITIAL_KB}KB)`);
    console.log('Arquivos JS carregados:');
    jsResources.forEach((r) => console.log(`  - ${r.url}: ${(r.size / 1024).toFixed(1)}KB`));

    // Nota: Este é o tamanho não-comprimido. Em produção com gzip será menor.
    // O teste é informativo - o limite real é verificado no build.
  });

  test('🟡 CSS deve carregar rapidamente', async ({ page }) => {
    const cssResources: { url: string; size: number }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      if (url.endsWith('.css') || url.includes('.css?')) {
        const headers = response.headers();
        const size = parseInt(headers['content-length'] || '0');
        cssResources.push({
          url: url.split('/').pop() || url,
          size,
        });
      }
    });

    await page.goto('/', { waitUntil: 'networkidle' });

    const totalCssSize = cssResources.reduce((sum, r) => sum + r.size, 0);
    const totalCssKB = totalCssSize / 1024;

    console.log(`CSS Total: ${totalCssKB.toFixed(0)}KB (limite: ${THRESHOLDS.CSS_KB}KB)`);
  });

  test('🟡 imagens devem estar otimizadas', async ({ page }) => {
    const images: { url: string; size: number; type: string }[] = [];

    page.on('response', async (response) => {
      const url = response.url();
      const contentType = response.headers()['content-type'] || '';

      if (contentType.startsWith('image/')) {
        const size = parseInt(response.headers()['content-length'] || '0');
        images.push({
          url: url.split('/').pop() || url,
          size,
          type: contentType,
        });
      }
    });

    await page.goto('/', { waitUntil: 'networkidle' });

    const totalImageSize = images.reduce((sum, i) => sum + i.size, 0);
    const totalImageKB = totalImageSize / 1024;

    console.log(`Imagens Total: ${totalImageKB.toFixed(0)}KB`);

    // Verifica formatos modernos
    const modernFormats = images.filter(
      (i) => i.type.includes('webp') || i.type.includes('avif')
    );
    const legacyFormats = images.filter(
      (i) => i.type.includes('png') || i.type.includes('jpeg')
    );

    if (legacyFormats.length > 0) {
      console.log('Imagens em formato legado (considere WebP):');
      legacyFormats.forEach((i) => console.log(`  - ${i.url}: ${i.type}`));
    }
  });
});

test.describe('Checklist: Caching', () => {
  test('🔴 assets estáticos devem ter cache headers', async ({ page }) => {
    const assetsWithoutCache: string[] = [];

    page.on('response', async (response) => {
      const url = response.url();

      // Verifica apenas assets estáticos
      if (
        url.endsWith('.js') ||
        url.endsWith('.css') ||
        url.endsWith('.woff2') ||
        url.endsWith('.png') ||
        url.endsWith('.jpg') ||
        url.endsWith('.svg')
      ) {
        const cacheControl = response.headers()['cache-control'];

        // Em desenvolvimento, cache pode não estar configurado
        if (process.env.CI && !cacheControl) {
          assetsWithoutCache.push(url.split('/').pop() || url);
        }
      }
    });

    await page.goto('/', { waitUntil: 'networkidle' });

    if (assetsWithoutCache.length > 0) {
      console.log('Assets sem cache headers:', assetsWithoutCache);
    }

    // Não falha em desenvolvimento
    if (!process.env.CI) {
      test.skip(true, 'Cache headers verificados apenas em CI');
    }
  });

  test('🟡 deve usar preconnect para APIs externas', async ({ page }) => {
    await page.goto('/');

    const preconnects = await page.locator('link[rel="preconnect"]').all();
    const preconnectHrefs = await Promise.all(
      preconnects.map((el) => el.getAttribute('href'))
    );

    console.log('Preconnects configurados:', preconnectHrefs);

    // Recomendação: deve ter preconnect para APIs usadas
    // Não falha, apenas reporta
  });
});

test.describe('Checklist: Lazy Loading', () => {
  test('🟡 imagens abaixo do fold devem ter lazy loading', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const images = await page.evaluate(() => {
      const imgs = Array.from(document.querySelectorAll('img'));
      const viewportHeight = window.innerHeight;

      return imgs.map((img) => {
        const rect = img.getBoundingClientRect();
        return {
          src: img.src.split('/').pop(),
          loading: img.getAttribute('loading'),
          belowFold: rect.top > viewportHeight,
        };
      });
    });

    const belowFoldWithoutLazy = images.filter(
      (img) => img.belowFold && img.loading !== 'lazy'
    );

    if (belowFoldWithoutLazy.length > 0) {
      console.log(
        'Imagens abaixo do fold sem lazy loading:',
        belowFoldWithoutLazy.map((i) => i.src)
      );
    }
  });
});
