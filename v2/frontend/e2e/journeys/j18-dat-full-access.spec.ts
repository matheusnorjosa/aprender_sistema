/**
 * J18 — DAT tem acesso total ao frontend.
 *
 * Ref: Regra PO confirmada em 2026-04-22, memória
 * `project_rbac_invariants`: DAT é o administrador operacional da plataforma;
 * deve navegar em todas as telas sem receber 403/404 no frontend. Desde o
 * PR 10 o DAT também aprova solicitações (base `capacidade_aprovar` do
 * pacote `ADMIN_OPERACIONAL` em `solicitation_approval_basis`).
 *
 * Esta jornada valida que um usuário com o vínculo EQUIPE na GERENCIA DAT
 * (pacote `ADMIN_OPERACIONAL`), sem `Superuser`, consegue carregar todas as
 * rotas principais do sistema; o group `DAT` é só etiqueta.
 *
 * Três camadas:
 *
 * 1. **Canônica**: DAT abre rotas autenticadas comuns → todas carregam
 *    o shell (`<main>`) sem redirecionar para `/login` ou mostrar
 *    `<Forbidden />`.
 * 2. **Borda**: `/api/me/policies/` do DAT traz as policies do pacote do
 *    administrador operacional (`manage_admin_registries`,
 *    `access_solicitation_approvals`). É essa lista que menu e rotas leem
 *    (`RequirePolicy`); o grupo `DAT` no `/api/me/` é só etiqueta desde o PR 12.
 * 3. **Operação**: DAT consegue chamar endpoints de manutenção — ex:
 *    `/api/dat/compras-materiais/dashboard/` retorna 200 (`CanViewComprasDashboard`).
 *
 * **Nota**: issue #1166 (normalizar dashboards para Diretoria+DAT+superuser)
 * está aberta — quando resolvida, expandir este spec para validar acesso a
 * todos os 5 dashboards. Por ora valida apenas Compras (que já funciona).
 */
import { test, expect, createApiContext, ROLE_CREDENTIALS } from '../fixtures';
import { waitForRouteReady } from '../helpers/wait';

/**
 * Rotas que um usuário DAT puro deve conseguir abrir sem 403.
 * Excluídos: rotas legacy, rotas que redirecionam para outro lugar, rotas
 * que exigem dado seedado específico.
 */
const DAT_ACCESSIBLE_ROUTES = [
  '/home',
  '/solicitacoes/minhas',
  '/solicitacoes/nova',
  '/aprovacoes', // access_solicitation_approvals (base capacidade_aprovar do pacote)
  '/pre-agenda', // access_controle_section
  '/deslocamentos', // access_travel
  '/dat/admin',
  '/dat/cadastros',
  '/dat/registros',
  '/dashboards/compras', // view_compras_dashboard (manage_admin_registries)
];

test.describe(
  'J18 — DAT tem acesso total ao frontend',
  { tag: ['@critical', '@rbac', '@dat'] },
  () => {
    for (const route of DAT_ACCESSIBLE_ROUTES) {
      test(`canônica: DAT abre ${route} sem receber Forbidden`, async ({ authedPage }) => {
        const page = await authedPage('dat_e2e');
        await page.goto(route);
        await waitForRouteReady(page);

        // Shell autenticado carregado (role="main" presente no AppShell)
        await expect(page.getByRole('main')).toBeVisible();

        // Não deve ter chegado na tela genérica do RequirePolicy nem no ErrorBoundary
        await expect(page.getByText('Recurso indisponível')).toHaveCount(0);
        await expect(page.getByText('Algo deu errado')).toHaveCount(0);

        // Não deve ter redirecionado para /login
        expect(page.url()).not.toContain('/login');
      });
    }

    test('borda: /api/me/policies/ do DAT traz as policies do pacote', async ({ baseURL }) => {
      const datApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.dat_e2e.username,
        password: ROLE_CREDENTIALS.dat_e2e.password,
      });
      const res = await datApi.get('/api/me/policies/');
      expect(res.ok()).toBeTruthy();
      const policies = (await res.json()) as string[];

      // O poder vem do vínculo EQUIPE na GERENCIA DAT (pacote ADMIN_OPERACIONAL), não do grupo.
      expect(policies).toEqual(
        expect.arrayContaining(['manage_admin_registries', 'access_solicitation_approvals']),
      );
    });

    test('operação: DAT consegue chamar endpoint de manutenção do dashboard Compras', async ({
      baseURL,
    }) => {
      const datApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.dat_e2e.username,
        password: ROLE_CREDENTIALS.dat_e2e.password,
      });
      // Endpoint conhecido que DAT acessa hoje (pode_acessar_dashboard_compras
      // inclui DAT + Diretoria no functional_permissions_seed).
      const res = await datApi.get('/api/dat/compras-materiais/dashboard/');
      expect(res.status(), `DAT deveria acessar dashboard Compras`).toBeLessThan(400);
    });
  }
);
