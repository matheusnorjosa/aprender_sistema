/**
 * Spec de validação do scaffolding (Fase 2b).
 *
 * Objetivo: exercitar cada peça nova (fixtures de roles, helper waitForAppReady,
 * POMs, multi-auth setup) em um teste smoke leve. Se este spec passa, a
 * infra está pronta para a Fase 3 (matriz de 12+ jornadas profundas).
 *
 * Este NÃO é um dos testes da matriz oficial — é o teste da própria infra.
 */
import { test, expect } from './fixtures';
import { SolicitacaoWizardPage } from './pages/SolicitacaoWizardPage';
import { DisponibilidadePage } from './pages/DisponibilidadePage';
import { waitForAppReady } from './helpers/wait';

test.describe('Scaffolding Fase 2b — infra de testes', () => {
  test('authedPage(coord_vidas) carrega sessão persistida', async ({ authedPage }) => {
    const page = await authedPage('coord_vidas');
    await page.goto('/home');
    await waitForAppReady(page);

    // Deve estar autenticado — `/api/me/` retorna 200
    const meRes = await page.request.get('/api/me/');
    expect(meRes.ok()).toBeTruthy();
    const me = (await meRes.json()) as { username: string };
    expect(me.username).toBe('coord_vidas@test.com');
  });

  test('authedPage(formador_vidas) é isolado de coord_vidas', async ({ authedPage }) => {
    const pageCoord = await authedPage('coord_vidas');
    const pageForm = await authedPage('formador_vidas');

    await pageCoord.goto('/home');
    await pageForm.goto('/home');

    const meCoord = await (await pageCoord.request.get('/api/me/')).json();
    const meForm = await (await pageForm.request.get('/api/me/')).json();

    expect(meCoord.username).toBe('coord_vidas@test.com');
    expect(meForm.username).toBe('formador_vidas@test.com');
  });

  test('SolicitacaoWizardPage navega e expõe locators semânticos', async ({ authedPage }) => {
    const page = await authedPage('coord_vidas');
    const wizard = new SolicitacaoWizardPage(page);

    await wizard.goto();
    await expect(wizard.main).toBeVisible();
  });

  test('DisponibilidadePage carrega e expõe a grade', async ({ authedPage }) => {
    const page = await authedPage('coord_vidas');
    const disp = new DisponibilidadePage(page);

    await disp.goto();
    await expect(disp.main).toBeVisible();
  });

  test('waitForAppReady aguarda #root popular', async ({ authedPage }) => {
    const page = await authedPage('coord_vidas');
    await page.goto('/home');
    await waitForAppReady(page);

    const rootHasChildren = await page.evaluate(() => {
      const root = document.getElementById('root');
      return !!root && root.children.length > 0;
    });
    expect(rootHasChildren).toBeTruthy();
  });
});
