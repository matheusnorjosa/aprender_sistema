/**
 * Testes E2E de Dashboards
 *
 * Smoke de shell: confere só que o <main> aparece nas rotas de dashboards e visualizações.
 * Autenticação é feita automaticamente via auth.setup.ts, com o storageState padrão
 * (coord_e2e: papel COORDENADOR na GERENCIA E2E, perfil PADRAO). Pela lotação essa persona
 * não tem view_overview_dashboard, view_team_dashboard, view_gcal_dashboard nem
 * view_map_metrics: nessas rotas o RequirePolicy mostra "Recurso indisponível" dentro do
 * <main>, e o teste passa sem ter aberto o dashboard. Abrir de fato exige uma persona com
 * a policy (authedPage de e2e/fixtures/roles.ts) e conferir o título da tela. Grade e
 * Bloqueios (/disponibilidade e /bloqueios redirecionam para /solicitacoes/...) abrem para
 * coord_e2e pelo papel COORDENADOR vigente (TELAS_DE_ESCOPO).
 */

import { test, expect } from '@playwright/test';

test.describe('Dashboards', () => {
  test('1. Dashboard Geral carrega', async ({ page }) => {
    await page.goto('/dashboards');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('2. Dashboard Equipe carrega', async ({ page }) => {
    await page.goto('/dashboards/equipe');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('3. Dashboard GCal carrega', async ({ page }) => {
    await page.goto('/dashboards/gcal');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('4. Mapa do Brasil carrega com visualização', async ({ page }) => {
    await page.goto('/mapa-brasil');
    await expect(page.getByRole('main')).toBeVisible();
  });
});

test.describe('Disponibilidade e Grade', () => {
  test('5. Grade Mensal carrega', async ({ page }) => {
    await page.goto('/disponibilidade');
    await expect(page.getByRole('main')).toBeVisible();
  });

  test('6. Bloqueios carrega', async ({ page }) => {
    await page.goto('/bloqueios');
    await expect(page.getByRole('main')).toBeVisible();
  });
});
