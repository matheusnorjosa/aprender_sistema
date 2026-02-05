/**
 * Authentication Helpers - Playwright E2E Tests
 *
 * Helper functions for login, logout and authentication state management.
 * Fase 2 - Plano DAT/GCal 2025-10-29
 */

import { Page, expect } from '@playwright/test';

/**
 * Realiza login no sistema e valida sucesso.
 *
 * @param page - Playwright Page object
 * @param username - Username or email
 * @param password - Password
 * @throws Se login falhar ou timeout
 */
export async function loginAs(page: Page, username: string, password: string): Promise<void> {
  // Navegar para home (redireciona para login se não autenticado)
  await page.goto('/');

  // Aguardar formulário de login estar visível
  await page.waitForSelector('input[name="username"], input[type="text"]', { timeout: 10000 });

  // Preencher credenciais
  const usernameInput = page.locator('input[name="username"], input[type="text"]').first();
  const passwordInput = page.locator('input[name="password"], input[type="password"]').first();

  await usernameInput.fill(username);
  await passwordInput.fill(password);

  // Submeter formulário
  const submitButton = page.locator('button[type="submit"], button:has-text("Entrar")').first();
  await submitButton.click();

  // Validar sucesso: aguardar elementos de layout pós-login (sidebar/nav)
  await expect(page.locator('nav[role="navigation"], .ant-layout-sider').first()).toBeVisible({ timeout: 15000 });

  // Validar que logo/header do sistema está visível
  await expect(page.locator('text=Aprender Sistema')).toBeVisible({ timeout: 5000 });

  console.log(`✅ Login bem-sucedido: ${username}`);
}

/**
 * Realiza logout completo do sistema.
 *
 * @param page - Playwright Page object
 */
export async function logout(page: Page): Promise<void> {
  // Clicar em botão de logout (diversos possíveis selectors)
  const logoutButton = page.locator('button:has-text("Sair"), button:has-text("Logout"), a:has-text("Sair")').first();

  if (await logoutButton.isVisible({ timeout: 2000 })) {
    await logoutButton.click();

    // Aguardar redirecionamento para login
    await page.waitForURL(/\/(login)?$/, { timeout: 10000 });

    console.log('✅ Logout bem-sucedido');
  } else {
    console.warn('⚠️  Botão de logout não encontrado, pulando...');
  }
}

/**
 * Aguarda resposta de API específica.
 *
 * @param page - Playwright Page object
 * @param urlPattern - Pattern de URL (string ou RegExp)
 * @param method - HTTP method (opcional, default: qualquer)
 * @returns Response object
 */
export async function waitForAPIResponse(
  page: Page,
  urlPattern: string | RegExp,
  method?: string
): Promise<any> {
  const response = await page.waitForResponse(
    (resp) => {
      const urlMatches = typeof urlPattern === 'string'
        ? resp.url().includes(urlPattern)
        : urlPattern.test(resp.url());

      const methodMatches = method ? resp.request().method() === method : true;

      return urlMatches && methodMatches;
    },
    { timeout: 30000 }
  );

  if (!response.ok()) {
    console.warn(`⚠️  API response not OK: ${response.status()} ${response.url()}`);
  }

  return response.json();
}

/**
 * Captura cookies de autenticação (se necessário).
 *
 * @param page - Playwright Page object
 * @returns Cookies array
 */
export async function getAuthCookies(page: Page): Promise<any[]> {
  const cookies = await page.context().cookies();
  return cookies.filter((c) => c.name.includes('session') || c.name.includes('token'));
}

/**
 * Aguarda elemento estar visível com retry.
 *
 * @param page - Playwright Page object
 * @param selector - CSS selector ou texto
 * @param timeout - Timeout em ms (default: 10000)
 */
export async function waitForVisible(page: Page, selector: string, timeout: number = 10000): Promise<void> {
  await page.locator(selector).first().waitFor({ state: 'visible', timeout });
}
