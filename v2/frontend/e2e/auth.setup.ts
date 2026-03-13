/**
 * Setup de Autenticação para Testes E2E
 *
 * Faz login uma vez e salva o estado para reutilizar em todos os testes.
 */

import { test as setup, expect } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const authFile = join(__dirname, '.auth/user.json');

const ADMIN_USER = {
  username: 'coord_e2e@test.com',
  password: 'testpass123',
};

setup('authenticate', async ({ page }) => {
  // Navega para app shell e obtém CSRF via fetch.
  // Evita navegar diretamente para /api/csrf/ (response com CSP
  // "upgrade-insecure-requests" pode forçar requests seguintes para https).
  await page.goto('/');
  const csrfToken = await page.evaluate(async () => {
    const resp = await fetch('/api/csrf/', { credentials: 'include' });
    if (!resp.ok) return null;
    const data = await resp.json();
    return data?.csrfToken ?? null;
  });
  expect(csrfToken).toBeTruthy();

  // Login via fetch no browser (cookies ficam no contexto do page)
  const loginOk = await page.evaluate(async ({ username, password, token }) => {
    const resp = await fetch('/api/auth/login/', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': token,
      },
      body: JSON.stringify({ username, password }),
    });
    return resp.ok;
  }, { username: ADMIN_USER.username, password: ADMIN_USER.password, token: csrfToken });
  expect(loginOk).toBeTruthy();

  // Validar sessão via API no contexto do browser
  const meOk = await page.evaluate(async () => {
    const resp = await fetch('/api/me/', { credentials: 'include' });
    return resp.ok;
  });
  expect(meOk).toBeTruthy();

  // Salvar estado de autenticação
  await page.context().storageState({ path: authFile });
});
