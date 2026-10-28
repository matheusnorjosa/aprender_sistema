/**
 * J02 — Nova solicitação: estrutura da página única e validação (UI).
 *
 * Exercita o POM `SolicitacaoWizardPage` (o nome ficou do tempo do wizard). Desde 28/10/2026
 * (decisão do dono) a tela é uma página só: o evento é um cartão com os campos lado a lado e um
 * botão "Criar solicitação" no fim. O spec valida a estrutura sem preencher o form inteiro —
 * campos usam `ComboBox` com lookup assíncrono, o que seria custoso e flaky para automatizar nesta
 * jornada.
 *
 * Escopo: estrutura, validação e gate de acesso. Preenchimento completo e submit de fato ficam
 * para uma jornada futura (J02b) após estabilizarmos o padrão de interação com ComboBox.
 *
 * Três camadas:
 *
 * 1. **Canônica (estrutura)**: coord_vidas abre `/solicitacoes/nova` → shell + heading + cartão
 *    "Evento 1" + "Mais detalhes" recolhido + botão "Criar solicitação"; nenhum passo nem
 *    "Próximo".
 * 2. **Borda (validação)**: clicar "Criar solicitação" com campos vazios não envia nada — a tela
 *    fica e o resumo do que falta aparece no topo.
 * 3. **Operação (RBAC)**: formador_vidas tenta acessar `/solicitacoes/nova`
 *    → rota protegida (menu não mostra, frontend bloqueia via
 *    `RequirePolicy create_solicitation`: o papel FORMADOR não tem direito
 *    de evento). Valida auditoria #1169 (gate fraco em /editar) NÃO
 *    se aplica aqui — o gate de nova solicitação é correto.
 */
import { test, expect } from '../fixtures';
import { SolicitacaoWizardPage } from '../pages/SolicitacaoWizardPage';
import { waitForRouteReady } from '../helpers/wait';

test.describe('J02 — Nova solicitação: página única', { tag: ['@critical', '@ux', '@rf01'] }, () => {
  test('canônica: a página carrega com o cartão do evento e sem passos', async ({ authedPage }) => {
    const page = await authedPage('coord_vidas');
    const nova = new SolicitacaoWizardPage(page);
    await nova.goto();

    // Shell autenticado
    await expect(nova.main).toBeVisible();

    // Heading da página e o cartão do evento
    await expect(page.getByRole('heading', { level: 2, name: /nova solicita[cç][aã]o/i })).toBeVisible();
    await expect(nova.cartao()).toBeVisible();
    await expect(page.getByRole('heading', { level: 3, name: 'Evento 1' })).toBeVisible();

    // Os detalhes opcionais começam recolhidos
    await expect(nova.maisDetalhes).toHaveAttribute('aria-expanded', 'false');

    // Um botão só para criar; nada de passos
    await expect(nova.btnCriar).toBeVisible();
    await expect(page.getByRole('button', { name: /pr[oó]ximo/i })).toHaveCount(0);
    await expect(page.getByRole('navigation', { name: /passos/i })).toHaveCount(0);
  });

  test('borda (validação): Criar com campos vazios não envia e mostra o resumo do que falta', async ({ authedPage }) => {
    const page = await authedPage('coord_vidas');
    const nova = new SolicitacaoWizardPage(page);
    await nova.goto();

    const envios: string[] = [];
    page.on('request', (req) => {
      if (req.method() === 'POST' && /\/api\/solicitacoes\/$/.test(new URL(req.url()).pathname)) envios.push(req.url());
    });

    await nova.btnCriar.click();

    await expect(nova.resumoDeErros).toBeVisible();
    await expect(nova.resumoDeErros).toContainText('Evento 1');
    await expect(page).toHaveURL(/\/solicitacoes\/nova$/);
    expect(envios).toHaveLength(0);
  });

  test('operação (RBAC): formador_vidas não acessa /solicitacoes/nova (rota bloqueada)', async ({
    authedPage,
  }) => {
    const page = await authedPage('formador_vidas');
    await page.goto('/solicitacoes/nova');
    await waitForRouteReady(page);

    // Formador não tem a policy create_solicitation (papel FORMADOR sem direito de evento) → rota deve mostrar <Forbidden /> ou equivalente.
    // Heurísticas (qualquer uma satisfaz):
    //  (a) texto "Forbidden/403/acesso negado"
    //  (b) redirecionamento para outra rota
    //  (c) ausência do heading "Nova Solicitação" e do botão "Criar solicitação"
    const hasForbiddenMessage = await page.getByText(/forbidden|403|acesso negado|permiss/i).count();
    const hasHeading = await page.getByRole('heading', { name: /nova solicita[cç][aã]o/i }).count();
    const hasCriarButton = await page.getByRole('button', { name: 'Criar solicitação' }).count();
    const urlChanged = !page.url().includes('/solicitacoes/nova');

    const blockedByAny = hasForbiddenMessage > 0 || urlChanged || (hasHeading === 0 && hasCriarButton === 0);
    expect(
      blockedByAny,
      `formador não deveria acessar a Nova Solicitação. url=${page.url()} forbidden=${hasForbiddenMessage} heading=${hasHeading} criar=${hasCriarButton}`
    ).toBeTruthy();
  });
});
