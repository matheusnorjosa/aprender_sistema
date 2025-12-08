/**
 * Testes E2E para fluxo RBAC (Setor + Função)
 *
 * Fase 5.3 do plano RBAC_SETOR_FUNCAO.md
 *
 * Testa:
 * - Página de login carrega corretamente
 * - Login funciona e redireciona para dashboard
 */

import { test, expect } from '@playwright/test';

// Credenciais de teste
const ADMIN_USER = {
  username: 'admin',
  password: 'admin123',
};

test.describe('RBAC Basic Flow', () => {
  test('1. Página de login carrega corretamente', async ({ page }) => {
    await page.goto('/');

    // Deve mostrar formulário de login
    await expect(page.locator('text=Bem-vindo de volta!')).toBeVisible();
    await expect(page.locator('input[id="login_username"]')).toBeVisible();
    await expect(page.locator('input[id="login_password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('2. Login com superuser funciona e mostra dashboard', async ({ page }) => {
    await page.goto('/');

    // Preencher formulário
    await page.fill('input[id="login_username"]', ADMIN_USER.username);
    await page.fill('input[id="login_password"]', ADMIN_USER.password);

    // Clicar no botão de login
    await page.click('button[type="submit"]');

    // Aguardar resposta
    await page.waitForTimeout(3000);

    // Verificar que não há erro e que logou (sidebar visível)
    const errorCount = await page.locator('.ant-message-error').count();
    expect(errorCount).toBe(0);

    // Verificar que o sidebar está visível (indica que logou)
    await expect(page.locator('.ant-layout-sider').first()).toBeVisible({ timeout: 5000 });
  });
});
