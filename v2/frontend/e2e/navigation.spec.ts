/**
 * Testes E2E de Navegação Principal
 *
 * Testa navegação entre todas as páginas do sistema.
 * Autenticação é feita automaticamente via auth.setup.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Navegação Principal', () => {
  test('1. Página Inicial carrega corretamente', async ({ page }) => {
    await page.goto('/home');
    await expect(page.locator('.ant-layout-sider')).toBeVisible();
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('2. Grade Mensal (Disponibilidade) carrega', async ({ page }) => {
    await page.goto('/disponibilidade');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('3. Bloqueios carrega', async ({ page }) => {
    await page.goto('/bloqueios');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('4. Minhas Solicitações carrega', async ({ page }) => {
    await page.goto('/solicitacoes/minhas');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('5. Nova Solicitação carrega wizard', async ({ page }) => {
    await page.goto('/solicitacoes/nova');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('6. Aprovações carrega para superuser', async ({ page }) => {
    await page.goto('/aprovacoes');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('7. Pré-Agenda carrega', async ({ page }) => {
    await page.goto('/pre-agenda');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('8. Deslocamentos carrega', async ({ page }) => {
    await page.goto('/deslocamentos');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('9. Dashboard Geral carrega', async ({ page }) => {
    await page.goto('/dashboards');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('10. Dashboard Equipe carrega', async ({ page }) => {
    await page.goto('/dashboards/equipe');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('11. Dashboard GCal carrega', async ({ page }) => {
    await page.goto('/dashboards/gcal');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('12. Mapa do Brasil carrega', async ({ page }) => {
    await page.goto('/mapa-brasil');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('13. Painel de Controle carrega', async ({ page }) => {
    await page.goto('/controle');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('14. Relatórios ETL carrega', async ({ page }) => {
    await page.goto('/dat/etl-reports');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });
});
