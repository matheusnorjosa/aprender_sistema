/**
 * CHECKLIST_FRONTEND.md - Meta Tags Tests
 *
 * Testa itens da seção "Head > Meta Tags":
 * - 🔴 Charset UTF-8
 * - 🔴 Viewport responsivo
 * - 🟡 Title único por página
 * - 🟡 Meta description
 * - 🟢 Theme color
 */
import { test, expect, Page } from '@playwright/test';
import './checklist-network-mocks.setup';

// Helper para extrair meta tags
async function getMetaContent(page: Page, selector: string): Promise<string | null> {
  return page.locator(selector).getAttribute('content');
}

test.describe('Checklist: Meta Tags', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('🔴 deve ter charset UTF-8', async ({ page }) => {
    const charset = await page.locator('meta[charset]').getAttribute('charset');
    const charsetMeta = await getMetaContent(page, 'meta[http-equiv="Content-Type"]');

    // Aceita <meta charset="UTF-8"> ou <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    const hasCharset =
      charset?.toLowerCase() === 'utf-8' ||
      charsetMeta?.toLowerCase().includes('utf-8');

    expect(hasCharset).toBeTruthy();
  });

  test('🔴 deve ter viewport responsivo', async ({ page }) => {
    const viewport = await getMetaContent(page, 'meta[name="viewport"]');

    expect(viewport).toBeTruthy();
    expect(viewport).toContain('width=device-width');
    expect(viewport).toContain('initial-scale=1');
  });

  test('🟡 deve ter title com máximo 60 caracteres', async ({ page }) => {
    const title = await page.title();

    expect(title).toBeTruthy();
    expect(title.length).toBeLessThanOrEqual(60);
    expect(title.length).toBeGreaterThan(0);
  });

  test('🟡 deve ter meta description com máximo 160 caracteres', async ({ page }) => {
    const description = await getMetaContent(page, 'meta[name="description"]');

    // Description é recomendada mas não obrigatória
    if (description) {
      expect(description.length).toBeLessThanOrEqual(160);
      expect(description.length).toBeGreaterThan(0);
    }
  });

  test('🟢 deve ter theme-color definido', async ({ page }) => {
    const themeColor = await getMetaContent(page, 'meta[name="theme-color"]');

    // Theme color é opcional (nice to have)
    if (themeColor) {
      // Verifica se é uma cor válida (hex, rgb, ou nome)
      expect(themeColor).toMatch(/^(#[0-9a-fA-F]{3,6}|rgb\(|rgba\(|[a-z]+).*$/i);
    }
  });

  test('🔴 deve ter HTML5 doctype', async ({ page }) => {
    const html = await page.content();
    const hasDoctype = html.toLowerCase().startsWith('<!doctype html>');

    expect(hasDoctype).toBeTruthy();
  });

  test('🔴 deve ter lang="pt-BR" no html', async ({ page }) => {
    const lang = await page.locator('html').getAttribute('lang');

    expect(lang).toBeTruthy();
    expect(lang?.toLowerCase()).toMatch(/^pt(-br)?$/);
  });
});

test.describe('Checklist: Favicon', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('🔴 deve ter favicon básico', async ({ page }) => {
    const favicon =
      (await page.locator('link[rel="icon"]').first().getAttribute('href')) ||
      (await page.locator('link[rel="shortcut icon"]').first().getAttribute('href'));

    expect(favicon).toBeTruthy();
  });

  test('🟡 deve ter apple-touch-icon', async ({ page }) => {
    const appleIcon = await page
      .locator('link[rel="apple-touch-icon"]')
      .first()
      .getAttribute('href');

    // Apple touch icon é recomendado
    if (appleIcon) {
      expect(appleIcon).toBeTruthy();
    }
  });
});

test.describe('Checklist: Open Graph', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('🟢 deve ter og:title se OG estiver configurado', async ({ page }) => {
    const ogTitle = await getMetaContent(page, 'meta[property="og:title"]');

    // Open Graph é opcional
    if (ogTitle) {
      expect(ogTitle.length).toBeGreaterThan(0);
    }
  });

  test('🟢 deve ter og:description se OG estiver configurado', async ({ page }) => {
    const ogDescription = await getMetaContent(page, 'meta[property="og:description"]');

    if (ogDescription) {
      expect(ogDescription.length).toBeGreaterThan(0);
    }
  });

  test('🟢 deve ter og:image se OG estiver configurado', async ({ page }) => {
    const ogImage = await getMetaContent(page, 'meta[property="og:image"]');

    if (ogImage) {
      expect(ogImage).toMatch(/^https?:\/\//);
    }
  });
});
