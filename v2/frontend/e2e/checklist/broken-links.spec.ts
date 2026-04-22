/**
 * CHECKLIST_FRONTEND.md - Broken Links Tests
 *
 * Testa itens da seção "HTML > Validação":
 * - 🔴 Links funcionais: Nenhum link quebrado (404)
 *
 * Crawl das páginas principais verificando:
 * - Links internos (mesmo domínio)
 * - Links de navegação
 * - Imagens (src)
 * - Scripts e CSS (href/src)
 */
import { test, expect, Page } from '@playwright/test';
import { mockChecklistAuthBootstrap } from './checklist-network-mocks';

test.beforeEach(async ({ page }) => {
  await mockChecklistAuthBootstrap(page);
});

interface LinkResult {
  url: string;
  status: number;
  source: string;
  type: 'link' | 'image' | 'script' | 'style';
}

// Páginas para crawlear
const PAGES_TO_CRAWL = ['/', '/solicitacoes', '/agenda', '/dashboard'];

// URLs para ignorar (externos, mailto, tel, etc.)
const IGNORE_PATTERNS = [
  /^mailto:/,
  /^tel:/,
  /^javascript:/,
  /^#/,
  /^data:/,
  /fonts\.googleapis\.com/,
  /fonts\.gstatic\.com/,
  /unpkg\.com/,
  /cdn\./,
  /localhost:8002/, // Backend API
];

function shouldIgnoreUrl(url: string): boolean {
  return IGNORE_PATTERNS.some((pattern) => pattern.test(url));
}

async function extractLinks(page: Page): Promise<{ url: string; type: LinkResult['type'] }[]> {
  return page.evaluate(() => {
    const results: { url: string; type: 'link' | 'image' | 'script' | 'style' }[] = [];

    // Links <a>
    document.querySelectorAll('a[href]').forEach((el) => {
      const href = el.getAttribute('href');
      if (href) results.push({ url: href, type: 'link' });
    });

    // Imagens
    document.querySelectorAll('img[src]').forEach((el) => {
      const src = el.getAttribute('src');
      if (src) results.push({ url: src, type: 'image' });
    });

    // Scripts
    document.querySelectorAll('script[src]').forEach((el) => {
      const src = el.getAttribute('src');
      if (src) results.push({ url: src, type: 'script' });
    });

    // Stylesheets
    document.querySelectorAll('link[rel="stylesheet"][href]').forEach((el) => {
      const href = el.getAttribute('href');
      if (href) results.push({ url: href, type: 'style' });
    });

    return results;
  });
}

function resolveUrl(base: string, url: string): string | null {
  try {
    return new URL(url, base).href;
  } catch {
    return null;
  }
}

test.describe('Checklist: Broken Links', () => {
  test('🔴 página inicial não deve ter links quebrados', async ({ page, request }) => {
    const brokenLinks: LinkResult[] = [];
    const checkedUrls = new Set<string>();

    await page.goto('/');
    await page.waitForLoadState('load');

    const links = await extractLinks(page);
    const baseUrl = page.url();

    for (const { url, type } of links) {
      if (shouldIgnoreUrl(url)) continue;

      const resolvedUrl = resolveUrl(baseUrl, url);
      if (!resolvedUrl) continue;
      if (checkedUrls.has(resolvedUrl)) continue;

      checkedUrls.add(resolvedUrl);

      // Só verifica URLs do mesmo domínio ou relativas
      const urlObj = new URL(resolvedUrl);
      const baseObj = new URL(baseUrl);

      if (urlObj.hostname !== baseObj.hostname) continue;

      try {
        const response = await request.get(resolvedUrl, {
          failOnStatusCode: false,
          timeout: 5000,
        });

        if (response.status() >= 400) {
          brokenLinks.push({
            url: resolvedUrl,
            status: response.status(),
            source: '/',
            type,
          });
        }
      } catch (error) {
        brokenLinks.push({
          url: resolvedUrl,
          status: 0,
          source: '/',
          type,
        });
      }
    }

    if (brokenLinks.length > 0) {
      const report = brokenLinks
        .map((l) => `  [${l.status}] ${l.type}: ${l.url}`)
        .join('\n');
      console.log(`Links quebrados encontrados:\n${report}`);
    }

    expect(
      brokenLinks,
      `${brokenLinks.length} links quebrados encontrados`
    ).toHaveLength(0);
  });

  test('🔴 imagens devem carregar corretamente', async ({ page }) => {
    const brokenImages: string[] = [];

    await page.goto('/');
    await page.waitForLoadState('load');

    // Verifica se imagens carregaram
    const images = await page.locator('img').all();

    for (const img of images) {
      const src = await img.getAttribute('src');
      const naturalWidth = await img.evaluate(
        (el: HTMLImageElement) => el.naturalWidth
      );
      const complete = await img.evaluate(
        (el: HTMLImageElement) => el.complete
      );

      // Imagem quebrada tem naturalWidth = 0 e complete = true
      if (complete && naturalWidth === 0 && src) {
        brokenImages.push(src);
      }
    }

    expect(
      brokenImages,
      `Imagens quebradas: ${brokenImages.join(', ')}`
    ).toHaveLength(0);
  });

  test('🔴 recursos estáticos devem existir', async ({ page, request }) => {
    const missingResources: string[] = [];

    // Monitora requisições de recursos
    page.on('response', (response) => {
      const url = response.url();
      const status = response.status();

      if (
        status === 404 &&
        (url.endsWith('.js') ||
          url.endsWith('.css') ||
          url.endsWith('.woff2') ||
          url.endsWith('.png') ||
          url.endsWith('.jpg') ||
          url.endsWith('.svg'))
      ) {
        missingResources.push(url);
      }
    });

    await page.goto('/');
    await page.waitForLoadState('load');

    expect(
      missingResources,
      `Recursos faltando: ${missingResources.join(', ')}`
    ).toHaveLength(0);
  });
});

test.describe('Checklist: Navigation Links', () => {
  test('🔴 links de navegação devem funcionar', async ({ page }) => {
    const failedNavigations: string[] = [];

    await page.goto('/');
    await page.waitForLoadState('load');

    // Encontra links de navegação
    const navLinks = await page.locator('nav a, [role="navigation"] a, .nav a').all();

    for (const link of navLinks.slice(0, 10)) {
      // Limita a 10 links
      const href = await link.getAttribute('href');
      if (!href || shouldIgnoreUrl(href)) continue;

      const text = await link.textContent();

      try {
        await link.click();
        await page.waitForLoadState('load');

        // Verifica se não é página de erro
        const title = await page.title();
        if (title.toLowerCase().includes('404') || title.toLowerCase().includes('error')) {
          failedNavigations.push(`${text}: ${href}`);
        }

        // Volta para a página inicial
        await page.goto('/');
        await page.waitForLoadState('load');
      } catch (error) {
        failedNavigations.push(`${text}: ${href} (erro: ${error})`);
      }
    }

    expect(
      failedNavigations,
      `Navegações falharam: ${failedNavigations.join(', ')}`
    ).toHaveLength(0);
  });
});
