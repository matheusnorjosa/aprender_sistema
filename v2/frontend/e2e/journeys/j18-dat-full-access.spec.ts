/**
 * J18 — DAT tem acesso total ao frontend.
 *
 * Ref: Regra PO confirmada em 2026-04-22, memória
 * `project_rbac_invariants`: DAT é o grupo de manutenção da plataforma;
 * deve navegar em todas as telas sem receber 403/404 no frontend, embora
 * não receba autonomia de decisão de negócio (ex: aprovar solicitações —
 * isso já é permitido pela `IsSuperintendencia` que aceita DAT também).
 *
 * Esta jornada valida que um usuário com **apenas** o group `DAT` (sem
 * `Superuser`, sem função adicional) consegue carregar todas as rotas
 * principais do sistema.
 *
 * Três camadas:
 *
 * 1. **Canônica**: DAT abre rotas autenticadas comuns → todas carregam
 *    o shell (`<main>`) sem redirecionar para `/login` ou mostrar
 *    `<Forbidden />`.
 * 2. **Borda**: DAT tem flags de menu correspondentes via `/api/me/`
 *    (permissões funcionais retornadas pelo endpoint incluem as de DAT).
 * 3. **Operação**: DAT consegue chamar endpoints de manutenção — ex:
 *    `/api/dat/compras-materiais/dashboard/` retorna 200 (canDashboardCompras).
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
  '/aprovacoes', // DAT aprova (IsSuperintendencia inclui DAT)
  '/pre-agenda', // IsControleOrDAT
  '/deslocamentos', // IsControleOrDAT
  '/dat/admin',
  '/dat/cadastros',
  '/dat/importacao',
  '/dat/registros',
  '/dashboards/compras', // canDashboardCompras (atual já permite DAT)
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

        // Não deve ter chegado em <Forbidden /> (rota de 403 do frontend)
        await expect(page.getByText(/403|forbidden|acesso negado/i)).toHaveCount(0);

        // Não deve ter redirecionado para /login
        expect(page.url()).not.toContain('/login');
      });
    }

    test('borda: /api/me/ retorna grupos com DAT e flag canDAT=true derivável', async ({ baseURL }) => {
      const datApi = await createApiContext({
        baseURL: baseURL!,
        username: ROLE_CREDENTIALS.dat_e2e.username,
        password: ROLE_CREDENTIALS.dat_e2e.password,
      });
      const res = await datApi.get('/api/me/');
      expect(res.ok()).toBeTruthy();
      const me = (await res.json()) as { username: string; groups?: string[]; setores?: string[] };

      expect(me.username).toBe('dat_e2e@test.com');
      // O backend expõe groups OU setores/funcoes (dependendo da versão do /me/).
      // Ambos os caminhos devem incluir DAT.
      const hasDatViaGroups = !!me.groups?.some((g) => g === 'DAT');
      const hasDatViaSetores = !!me.setores?.some((s) => s === 'DAT');
      expect(hasDatViaGroups || hasDatViaSetores).toBeTruthy();
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
