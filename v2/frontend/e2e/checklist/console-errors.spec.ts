/**
 * CHECKLIST_FRONTEND.md - Console Errors Tests
 *
 * Testa itens da seção "HTML > Validação":
 * - 🔴 Sem console errors: Zero erros JavaScript no console
 *
 * Navega pelas principais páginas e verifica se há erros no console.
 */
import { test, expect, ConsoleMessage, Page, Request } from '@playwright/test';
import { mockChecklistAuthBootstrap } from './checklist-network-mocks';

// Páginas principais para testar
const PAGES_TO_CHECK = [
  { path: '/', name: 'Home/Login' },
  { path: '/solicitacoes', name: 'Solicitações', requiresAuth: true },
  { path: '/agenda', name: 'Agenda', requiresAuth: true },
  { path: '/dashboard', name: 'Dashboard', requiresAuth: true },
];

// Ruídos não bloqueantes (bibliotecas/ambiente)
const NON_BLOCKING_ERRORS = [
  'Download the React DevTools',
  'findDOMNode is deprecated',
  'No routes matched location',
];

// Auth não autenticado esperado para bootstrap do app no checklist.
const AUTH_ENDPOINT_PATTERN = /\/api\/me\/?(\?.*)?$/;
const EXPECTED_AUTH_STATUSES = new Set([401, 403]);
const AUTH_CONSOLE_FAILURE_PATTERN = /Failed to load resource: the server responded with a status of (401|403)/;

// Mocks explícitos permitidos neste contexto (não devem falhar como requestfailed).
const MOCKED_BOOTSTRAP_ENDPOINTS = [
  /\/api\/csrf\/?(\?.*)?$/,
];

interface CollectedErrors {
  consoleErrors: string[];
  pageErrors: string[];
  networkErrors: string[];
}

function isApiUrl(url: string): boolean {
  return url.includes('/api/');
}

function shouldIgnoreConsoleError(message: string): boolean {
  return NON_BLOCKING_ERRORS.some((ignored) => message.includes(ignored));
}

function isExpectedAuthResponse(url: string, status: number): boolean {
  return AUTH_ENDPOINT_PATTERN.test(url) && EXPECTED_AUTH_STATUSES.has(status);
}

function isMockedBootstrapUrl(url: string): boolean {
  return MOCKED_BOOTSTRAP_ENDPOINTS.some((pattern) => pattern.test(url));
}

function shouldIgnoreRequestFailed(request: Request): boolean {
  const url = request.url();

  if (!isApiUrl(url)) {
    return true;
  }

  if (isMockedBootstrapUrl(url)) {
    return true;
  }

  // Requests abortadas por navegação não representam degradação de backend.
  const errorText = request.failure()?.errorText || '';
  return errorText.includes('ERR_ABORTED');
}

function attachCollectors(page: Page): CollectedErrors {
  let expectedAuthResponseBudget = 0;

  const collected: CollectedErrors = {
    consoleErrors: [],
    pageErrors: [],
    networkErrors: [],
  };

  page.on('console', (msg: ConsoleMessage) => {
    if (msg.type() !== 'error') {
      return;
    }

    const messageText = msg.text();
    if (AUTH_CONSOLE_FAILURE_PATTERN.test(messageText) && expectedAuthResponseBudget > 0) {
      expectedAuthResponseBudget -= 1;
      return;
    }

    if (!shouldIgnoreConsoleError(messageText)) {
      collected.consoleErrors.push(messageText);
    }
  });

  page.on('pageerror', (error) => {
    if (!shouldIgnoreConsoleError(error.message)) {
      collected.pageErrors.push(error.message);
    }
  });

  page.on('response', (response) => {
    const url = response.url();
    if (!isApiUrl(url)) {
      return;
    }

    const status = response.status();
    if (isExpectedAuthResponse(url, status)) {
      expectedAuthResponseBudget += 1;
      return;
    }

    if (status >= 500) {
      collected.networkErrors.push(
        `[api ${status}] ${response.request().method()} ${url}`
      );
    }
  });

  page.on('requestfailed', (request) => {
    if (shouldIgnoreRequestFailed(request)) {
      return;
    }

    const failure = request.failure()?.errorText || 'unknown request failure';
    collected.networkErrors.push(
      `[api requestfailed] ${request.method()} ${request.url()} :: ${failure}`
    );
  });

  return collected;
}

function assertNoCollectedErrors(collected: CollectedErrors, context: string): void {
  const allErrors = [
    ...collected.consoleErrors.map((entry) => `[console] ${entry}`),
    ...collected.pageErrors.map((entry) => `[pageerror] ${entry}`),
    ...collected.networkErrors.map((entry) => `[network] ${entry}`),
  ];

  expect(allErrors, `${context}:\n${allErrors.join('\n')}`).toHaveLength(0);
}

// Neste spec endurecido, NÃO mascaramos /api/me para capturar 5xx/proxy reais.
test.beforeEach(async ({ page }) => {
  await mockChecklistAuthBootstrap(page, { mockMeUnauthorized: false });
});

test.describe('Checklist: Console Errors', () => {
  test('🔴 página inicial não deve ter erros no console', async ({ page }) => {
    const collected = attachCollectors(page);

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Aguarda um pouco para capturar erros assíncronos
    await page.waitForTimeout(1000);

    assertNoCollectedErrors(collected, 'Erros encontrados na página inicial');
  });

  test('🔴 navegação não deve gerar erros no console', async ({ page }) => {
    const collected = attachCollectors(page);

    for (const pageToCheck of PAGES_TO_CHECK) {
      await page.goto(pageToCheck.path);
      await page.waitForLoadState('networkidle');
    }

    assertNoCollectedErrors(collected, 'Erros durante navegação');
  });

  test('🔴 não deve ter erros de JavaScript não tratados', async ({ page }) => {
    const collected = attachCollectors(page);

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Interage com a página para disparar possíveis erros
    await page.mouse.move(100, 100);
    await page.mouse.click(100, 100);

    assertNoCollectedErrors(collected, 'Erros não tratados');
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
