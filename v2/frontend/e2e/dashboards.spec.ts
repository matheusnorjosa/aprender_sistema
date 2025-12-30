/**
 * Testes E2E de Dashboards
 *
 * Testa todas as páginas de dashboards e visualizações.
 * Autenticação é feita automaticamente via auth.setup.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Dashboards', () => {
  test('1. Dashboard Geral carrega', async ({ page }) => {
    await page.goto('/dashboards');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('2. Dashboard Equipe carrega', async ({ page }) => {
    await page.goto('/dashboards/equipe');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('3. Dashboard GCal carrega', async ({ page }) => {
    await page.goto('/dashboard/gcal');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('4. Mapa do Brasil carrega com visualização', async ({ page }) => {
    await page.goto('/mapa-brasil');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });
});

test.describe('Disponibilidade e Grade', () => {
  test('5. Grade Mensal carrega', async ({ page }) => {
    await page.goto('/disponibilidade');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('6. Bloqueios carrega', async ({ page }) => {
    await page.goto('/bloqueios');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });
});
