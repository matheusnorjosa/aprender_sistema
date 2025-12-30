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
  username: 'admin',
  password: 'admin123',
};

setup('authenticate', async ({ page }) => {
  // Navegar para login
  await page.goto('/');

  // Verificar que está na página de login
  await expect(page.locator('h2:has-text("Login")')).toBeVisible({ timeout: 10000 });

  // Preencher formulário
  await page.fill('input[id="login_username"]', ADMIN_USER.username);
  await page.fill('input[id="login_password"]', ADMIN_USER.password);

  // Submeter
  await page.click('button[type="submit"]');

  // Aguardar que não esteja mais na página de login (login heading desaparece)
  await expect(page.locator('h2:has-text("Login")')).not.toBeVisible({ timeout: 20000 });

  // Verificar que está logado (sidebar visível)
  await expect(page.locator('.ant-layout-sider')).toBeVisible({ timeout: 5000 });

  // Salvar estado de autenticação
  await page.context().storageState({ path: authFile });
});
