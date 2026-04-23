/**
 * J02 — Wizard de nova solicitação: estrutura e navegação (UI).
 *
 * Primeiro spec UI-heavy da matriz. Exercita o POM `SolicitacaoWizardPage`
 * (criado na Fase 2b mas até agora não usado em spec real) e valida o
 * fluxo de navegação sem preencher o form inteiro — campos usam
 * `ComboBox` com lookup assíncrono, o que seria custoso e flaky para
 * automatizar nesta primeira jornada.
 *
 * Escopo: estrutura, navegação e gate de acesso. Preenchimento completo
 * e submit de fato ficam para uma jornada futura (J02b) após
 * estabilizarmos o padrão de interação com ComboBox.
 *
 * Três camadas:
 *
 * 1. **Canônica (estrutura)**: coord_vidas abre `/solicitacoes/nova` →
 *    shell + heading + nav de passos + botão "Próximo" visíveis; botão
 *    "Anterior" não aparece no Step 1 (condicional currentStep > 0).
 * 2. **Borda (validação)**: clicar "Próximo" com campos vazios não avança
 *    o passo — o spec valida que o indicador de passo permanece no primeiro.
 * 3. **Operação (RBAC)**: formador_vidas tenta acessar `/solicitacoes/nova`
 *    → rota protegida (menu não mostra, frontend bloqueia via
 *    `canCoordenador`). Valida auditoria #1169 (gate fraco em /editar) NÃO
 *    se aplica aqui — o gate de nova solicitação é correto.
 */
import { test, expect } from '../fixtures';
import { SolicitacaoWizardPage } from '../pages/SolicitacaoWizardPage';
import { waitForRouteReady } from '../helpers/wait';

test.describe('J02 — Wizard de nova solicitação: estrutura e navegação', { tag: ['@critical', '@ux', '@rf01'] }, () => {
  test('canônica: wizard carrega com step 1 e navegação correta', async ({ authedPage }) => {
    const page = await authedPage('coord_vidas');
    const wizard = new SolicitacaoWizardPage(page);
    await wizard.goto();

    // Shell autenticado
    await expect(wizard.main).toBeVisible();

    // Heading da página
    await expect(page.getByRole('heading', { name: /nova solicita[cç][aã]o/i })).toBeVisible();

    // Navegação de passos do wizard visível
    await expect(wizard.passosNav).toBeVisible();

    // Step 1: botão "Próximo" disponível, "Anterior" oculto (currentStep === 0)
    await expect(wizard.btnProximo).toBeVisible();
    await expect(wizard.btnAnterior).toHaveCount(0);

    // "Confirmar Solicitação" só aparece no último step
    await expect(wizard.btnConfirmar).toHaveCount(0);
  });

  test('borda (validação): clicar Próximo com campos vazios não avança o passo', async ({ authedPage }) => {
    const page = await authedPage('coord_vidas');
    const wizard = new SolicitacaoWizardPage(page);
    await wizard.goto();

    // Captura snapshot do step atual antes do click (procura o elemento com aria-current ou active)
    // AntD Steps marca o current via classe `.ant-steps-item-active` dentro do <nav>.
    const activeStepBefore = await wizard.passosNav.locator('.ant-steps-item-active').innerText();

    // Tenta avançar sem preencher obrigatórios
    await wizard.btnProximo.click();

    // Aguarda debounce de validação
    await page.waitForTimeout(300);

    // Step atual deve continuar o mesmo (validação bloqueou o avanço)
    const activeStepAfter = await wizard.passosNav.locator('.ant-steps-item-active').innerText();
    expect(activeStepAfter).toBe(activeStepBefore);
  });

  test('operação (RBAC): formador_vidas não acessa /solicitacoes/nova (rota bloqueada)', async ({
    authedPage,
  }) => {
    const page = await authedPage('formador_vidas');
    await page.goto('/solicitacoes/nova');
    await waitForRouteReady(page);

    // Formador não tem canCoordenador → rota deve mostrar <Forbidden /> ou equivalente.
    // Heurísticas (qualquer uma satisfaz):
    //  (a) texto "Forbidden/403/acesso negado"
    //  (b) redirecionamento para outra rota
    //  (c) ausência do heading "Nova Solicitação" e do botão "Próximo"
    const hasForbiddenMessage = await page.getByText(/forbidden|403|acesso negado|permiss/i).count();
    const hasWizardHeading = await page.getByRole('heading', { name: /nova solicita[cç][aã]o/i }).count();
    const hasProximoButton = await page.getByRole('button', { name: 'Ir para proximo passo' }).count();
    const urlChanged = !page.url().includes('/solicitacoes/nova');

    const blockedByAny = hasForbiddenMessage > 0 || urlChanged || (hasWizardHeading === 0 && hasProximoButton === 0);
    expect(
      blockedByAny,
      `formador não deveria acessar o wizard. url=${page.url()} forbidden=${hasForbiddenMessage} heading=${hasWizardHeading} proximo=${hasProximoButton}`
    ).toBeTruthy();
  });
});
