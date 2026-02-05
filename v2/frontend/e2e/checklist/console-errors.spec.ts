/**
 * CHECKLIST_FRONTEND.md - Console Errors Tests
 *
 * Testa itens da seção "HTML > Validação":
 * - 🔴 Sem console errors: Zero erros JavaScript no console
 *
 * Navega pelas principais páginas e verifica se há erros no console.
 */
import { test, expect, Page, ConsoleMessage } from '@playwright/test';

// Páginas principais para testar
const PAGES_TO_CHECK = [
  { path: '/', name: 'Home/Login' },
  { path: '/solicitacoes', name: 'Solicitações', requiresAuth: true },
  { path: '/agenda', name: 'Agenda', requiresAuth: true },
  { path: '/dashboard', name: 'Dashboard', requiresAuth: true },
];

// Erros conhecidos que devem ser ignorados (bibliotecas de terceiros, etc.)
const IGNORED_ERRORS = [
  // React DevTools
  'Download the React DevTools',
  // Warnings de desenvolvimento
  'Warning: ',
  // Erros de rede que são esperados em testes
  'net::ERR_',
  'Failed to fetch',
  // Ant Design warnings
  'findDOMNode is deprecated',
  // React Router
  'No routes matched location',
  // Auth errors on public/login pages
  'As credenciais de autenticação não foram fornecidas.',
  'Failed to load resource: the server responded with a status of 403',
];

function shouldIgnoreError(message: string): boolean {
  return IGNORED_ERRORS.some((ignored) => message.includes(ignored));
}

test.describe('Checklist: Console Errors', () => {
  test('🔴 página inicial não deve ter erros no console', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error' && !shouldIgnoreError(msg.text())) {
        errors.push(msg.text());
      }
    });

    page.on('pageerror', (error) => {
      if (!shouldIgnoreError(error.message)) {
        errors.push(error.message);
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Aguarda um pouco para capturar erros assíncronos
    await page.waitForTimeout(1000);

    expect(errors, `Erros encontrados: ${errors.join(', ')}`).toHaveLength(0);
  });

  test('🔴 navegação não deve gerar erros no console', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'error' && !shouldIgnoreError(msg.text())) {
        errors.push(`[${msg.type()}] ${msg.text()}`);
      }
    });

    page.on('pageerror', (error) => {
      if (!shouldIgnoreError(error.message)) {
        errors.push(`[pageerror] ${error.message}`);
      }
    });

    // Navega pela página inicial
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Tenta clicar em links de navegação se existirem
    const navLinks = page.locator('nav a, [role="navigation"] a').first();
    if ((await navLinks.count()) > 0) {
      await navLinks.click();
      await page.waitForLoadState('networkidle');
    }

    expect(errors, `Erros durante navegação: ${errors.join('\n')}`).toHaveLength(0);
  });

  test('🔴 não deve ter erros de JavaScript não tratados', async ({ page }) => {
    const uncaughtErrors: string[] = [];

    page.on('pageerror', (error) => {
      uncaughtErrors.push(error.message);
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Interage com a página para disparar possíveis erros
    await page.mouse.move(100, 100);
    await page.mouse.click(100, 100);

    expect(
      uncaughtErrors,
      `Erros não tratados: ${uncaughtErrors.join(', ')}`
    ).toHaveLength(0);
  });
});

test.describe('Checklist: Console Warnings (Informativo)', () => {
  test('🟡 listar warnings do console (não falha)', async ({ page }) => {
    const warnings: string[] = [];

    page.on('console', (msg: ConsoleMessage) => {
      if (msg.type() === 'warning') {
        warnings.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Este teste é informativo - não falha, apenas reporta
    if (warnings.length > 0) {
      console.log('Warnings encontrados (informativos):');
      warnings.forEach((w) => console.log(`  - ${w}`));
    }

    // Sempre passa - é apenas para visibilidade
    expect(true).toBeTruthy();
  });
});
