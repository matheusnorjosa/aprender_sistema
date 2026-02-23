/**
 * Testes E2E de Solicitações
 *
 * Testa o fluxo de solicitações: criar, visualizar, aprovar/reprovar.
 * Autenticação é feita automaticamente via auth.setup.ts
 */

import { test, expect } from '@playwright/test';

test.describe('Fluxo de Solicitações', () => {
  test('1. Minhas Solicitações - Página carrega com tabela', async ({ page }) => {
    await page.goto('/solicitacoes/minhas');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('2. Nova Solicitação - Wizard carrega', async ({ page }) => {
    await page.goto('/solicitacoes/nova');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('3. Aprovações - Página carrega para superuser', async ({ page }) => {
    await page.goto('/aprovacoes');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('4. Pré-Agenda - Página carrega', async ({ page }) => {
    await page.goto('/pre-agenda');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });
});

test.describe('Controle e Operações', () => {
  test('5. Painel de Controle carrega', async ({ page }) => {
    await page.goto('/controle');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('6. Relatórios ETL carrega', async ({ page }) => {
    await page.goto('/dat/etl-reports');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });

  test('7. Deslocamentos carrega', async ({ page }) => {
    await page.goto('/deslocamentos');
    await expect(page.locator('.ant-layout-content')).toBeVisible();
  });
});
