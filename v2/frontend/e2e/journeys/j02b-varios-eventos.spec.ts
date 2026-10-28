/**
 * J02b — Nova solicitação: criar vários eventos de uma vez (PR 5, decisões do dono de 28/10/2026).
 *
 * Preenche os cartões pela tela (o J02 só olha a estrutura) e envia pelo lote
 * (`POST /api/solicitacoes/lote/`, tudo ou nada).
 *
 * 1. **Canônica**: coord_vidas cria 2 eventos de projetos diferentes (um SUPER, um NAO_SUPER) num
 *    clique em "Criar 2 eventos"; os dois aparecem em Minhas Solicitações.
 * 2. **Borda (choque)**: a mesma pessoa no mesmo horário nos 2 cartões. Quem confere é o servidor:
 *    os 2 cartões ficam vermelhos com o motivo e nada é criado. Com os erros à vista, a 360 px a
 *    página não rola na horizontal.
 *
 * As datas são sorteadas num futuro distante (sem choque com o que outros specs criam) e os
 * eventos criados são apagados no fim.
 */
import type { APIRequestContext } from '@playwright/test';
import { test, expect, createApiContext, ROLE_CREDENTIALS } from '../fixtures';
import { SolicitacaoWizardPage } from '../pages/SolicitacaoWizardPage';
import { medirRolagemHorizontal, resumir, temProblema } from '../checklist/sem-rolagem-horizontal.medicao';

const FORMADOR = ROLE_CREDENTIALS.formador_vidas.displayName;

/** Um dia sorteado entre ~3 e ~4 anos à frente, no formato da tela (DD/MM/AAAA) e em ISO (AAAA-MM-DD). */
function diaDistante(): { tela: string; iso: string } {
  const d = new Date();
  d.setDate(d.getDate() + 1100 + Math.floor(Math.random() * 365));
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return { tela: `${dd}/${mm}/${d.getFullYear()}`, iso: `${d.getFullYear()}-${mm}-${dd}` };
}

async function apiDoCoord(baseURL: string): Promise<APIRequestContext> {
  return createApiContext({
    baseURL,
    username: ROLE_CREDENTIALS.coord_vidas.username,
    password: ROLE_CREDENTIALS.coord_vidas.password,
  });
}

/** Eventos de quem cria naquele dia (para conferir que nada foi criado). */
async function eventosNoDia(api: APIRequestContext, iso: string): Promise<number> {
  const res = await api.get(`/api/solicitacoes/?mine=true&date_from=${iso}&date_to=${iso}`);
  expect(res.ok()).toBeTruthy();
  const corpo = (await res.json()) as { count?: number; results?: unknown[] } | unknown[];
  return Array.isArray(corpo) ? corpo.length : (corpo.count ?? corpo.results?.length ?? 0);
}

test.describe('J02b — Nova solicitação: vários eventos', { tag: ['@critical', '@ux', '@rf01'] }, () => {
  test('canônica: 2 eventos de projetos diferentes num envio só, e os 2 em Minhas Solicitações', async ({
    authedPage,
    baseURL,
  }) => {
    test.setTimeout(90_000);
    const api = await apiDoCoord(baseURL!);
    const dia = diaDistante();
    const criados: number[] = [];
    try {
      const page = await authedPage('coord_vidas');
      const nova = new SolicitacaoWizardPage(page);
      await nova.goto();

      await nova.preencherEvento(1, {
        projeto: 'TESTE E2E',
        municipio: 'Salvador',
        data: dia.tela,
        inicio: '08:00',
        fim: '10:00',
        formador: FORMADOR,
      });
      await nova.btnAdicionarEvento.click();
      await expect(page.getByRole('heading', { level: 3, name: 'Evento 2' })).toBeFocused();
      await nova.preencherEvento(2, {
        projeto: 'TESTE E2E NAO_SUPER',
        municipio: 'Salvador',
        data: dia.tela,
        inicio: '14:00',
        fim: '16:00',
        formador: FORMADOR,
      });

      const resposta = page.waitForResponse(
        (r) => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/solicitacoes/lote/'
      );
      await nova.btnCriarEventos(2).click();
      const lote = await resposta;
      expect(lote.status(), await lote.text()).toBe(201);
      const corpo = (await lote.json()) as { eventos: Array<{ indice: number; id: number; status: string }> };
      criados.push(...corpo.eventos.map((e) => e.id));
      expect(corpo.eventos.map((e) => e.status)).toEqual(['pendente', 'aprovado']);

      await expect(page).toHaveURL(/\/solicitacoes\/minhas$/);
      await expect(page.getByText('2 eventos criados (1 vai para aprovação)')).toBeVisible();
      // Minhas Solicitações ordena do mais distante para o mais próximo: os 2 estão na 1ª página.
      for (const id of criados) {
        await expect(page.locator(`tr[data-row-key="${id}"]`)).toBeVisible();
      }
    } finally {
      for (const id of criados) await api.delete(`/api/solicitacoes/${id}/`);
      await api.dispose();
    }
  });

  test('borda: a mesma pessoa no mesmo horário nos 2 eventos deixa os 2 vermelhos e não cria nada', async ({
    authedPage,
    baseURL,
  }) => {
    test.setTimeout(90_000);
    const api = await apiDoCoord(baseURL!);
    const dia = diaDistante();
    try {
      const antes = await eventosNoDia(api, dia.iso);
      const page = await authedPage('coord_vidas');
      // No celular desde o início (a barra lateral só recolhe ao abrir a página estreita).
      await page.setViewportSize({ width: 360, height: 800 });
      const nova = new SolicitacaoWizardPage(page);
      await nova.goto();

      const mesmoHorario = { municipio: 'Salvador', data: dia.tela, inicio: '09:00', fim: '11:00', formador: FORMADOR };
      await nova.preencherEvento(1, { projeto: 'TESTE E2E', ...mesmoHorario });
      await nova.btnAdicionarEvento.click();
      await nova.preencherEvento(2, { projeto: 'TESTE E2E NAO_SUPER', ...mesmoHorario });

      const resposta = page.waitForResponse(
        (r) => r.request().method() === 'POST' && new URL(r.url()).pathname === '/api/solicitacoes/lote/'
      );
      await nova.btnCriarEventos(2).click();
      expect((await resposta).status()).toBe(400);

      // Os 2 cartões dizem, em texto, que têm problema, e citam o outro evento da lista.
      await expect(nova.cartao(1)).toHaveAccessibleName('Evento 1 com problema');
      await expect(nova.cartao(2)).toHaveAccessibleName('Evento 2 com problema');
      await expect(nova.cartao(1)).toContainText('evento 2 desta lista');
      await expect(nova.cartao(2)).toContainText('evento 1 desta lista');
      await expect(nova.regiaoViva).toContainText('Nada foi criado.');
      await expect(page).toHaveURL(/\/solicitacoes\/nova$/);

      expect(await eventosNoDia(api, dia.iso)).toBe(antes);

      // Celular: os 2 cartões com erro, o "Remover" e o resumo cabem na largura.
      const medicao = await medirRolagemHorizontal(page);
      expect(temProblema(medicao), resumir(medicao)).toBe(false);
    } finally {
      await api.dispose();
    }
  });
});
