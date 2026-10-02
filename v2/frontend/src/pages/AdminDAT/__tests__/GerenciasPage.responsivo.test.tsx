/**
 * C2 (Programa C) — Gerências sem rolagem horizontal: lista enxuta no ResponsiveTable.
 *
 * Sempre na linha: o setor (rótulo de tela), Situação e as ações (AcoesLinha, "Editar: <setor>").
 * As demais sobem por largura: Setor canônico a partir de md, Projetos de lg, Gerente de xl e
 * Rótulo nas planilhas só de xxl (quase sempre repete o setor). O que some da linha vai para a
 * linha expandida. Nunca na grade: ID, código interno e descrição. A Confiança do de-para não
 * aparece em lugar nenhum (C2b, decisão do dono, 01/10: vazia nas 21 gerências de produção).
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

const { GERENCIAS } = vi.hoisted(() => ({
  GERENCIAS: [
    {
      id: 7, nome: 'GERENCIA 7', nome_setor: 'Formação Planilha', nome_exibicao: 'Formação Continuada',
      rotulo: 'Formação Continuada', setor_canonico: 'Ler, Ouvir e Contar', setor_canonico_confianca: 'media',
      gerente: 3, gerente_nome: 'Joana Fictícia', ativo: true, descricao: 'Descrição longa da gerência de teste',
      projetos_count: 5, created_at: '', updated_at: '',
    },
    {
      id: 8, nome: 'GERENCIA 8', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas',
      setor_canonico: 'Vidas', setor_canonico_confianca: 'alta', gerente: null, gerente_nome: '', ativo: false,
      descricao: '', projetos_count: 0, created_at: '', updated_at: '',
    },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 2, next: null, previous: null }),
  createGerencia: vi.fn().mockResolvedValue({}),
  updateGerencia: vi.fn().mockResolvedValue({}),
  deleteGerencia: vi.fn().mockResolvedValue({}),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: [] }),
}));

import GerenciasPage from '../GerenciasPage';

const SETOR = 'Formação Continuada';
/** Texto com contraste AA na tag green (TEXTO_DA_TAG do padrão). */
const VERDE_AA = '#237804';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <GerenciasPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

/** A linha da gerência, achada pelo botão de ações que leva o nome dela. */
async function linhaDaGerencia(acao: 'Editar' | 'Mais ações' = 'Editar'): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: `${acao}: ${SETOR}` }, { timeout: 15000 });
  const linha = botao.closest('tr');
  if (!linha) throw new Error('o botão não está numa linha da tabela');
  return linha;
}

/** Títulos das colunas de dados (sem a do botão de expandir, cujo título é só para leitor de tela). */
function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

describe('GerenciasPage responsiva (C2)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a 1280 px: lista enxuta, sem ID; ações pelo nome do setor', async () => {
    renderPage();
    const linha = await linhaDaGerencia();

    expect(cabecalhos()).toEqual(['Setor', 'Setor canônico', 'Gerente', 'Projetos', 'Situação', 'Ações']);
    // O setor (identidade) quebra linha em vez de cortar com reticências: não há detalhe que o mostre.
    expect(within(linha).getByText(SETOR).closest('td')).not.toHaveClass('ant-table-cell-ellipsis');
    expect(within(linha).getByRole('button', { name: `Excluir: ${SETOR}` })).toBeInTheDocument();
    for (const oculto of ['GERENCIA 7', 'Descrição longa da gerência de teste', 'Formação Planilha']) {
      expect(within(linha).queryByText(oculto)).not.toBeInTheDocument();
    }
    // Rótulo nas planilhas (só de xxl) fica na linha expandida
    expect(within(linha).getByRole('button', { name: `Expandir linha de ${SETOR}` })).toBeInTheDocument();
  }, 20000);

  test.each([
    [768, ['Setor', 'Setor canônico', 'Situação', 'Ações']],
    [1024, ['Setor', 'Setor canônico', 'Projetos', 'Situação', 'Ações']],
  ])('a %i px: colunas por prioridade', async (largura, esperadas) => {
    definirLarguraTela(largura);
    renderPage();
    await linhaDaGerencia();

    expect(cabecalhos()).toEqual(esperadas);
  }, 20000);

  test('a 360 px: só setor, Situação e o menu de ações; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDaGerencia('Mais ações');

    expect(cabecalhos()).toEqual(['Setor', 'Situação', 'Ações']);
    expect(within(linha).queryByRole('button', { name: `Editar: ${SETOR}` })).not.toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${SETOR}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    for (const texto of ['Ler, Ouvir e Contar', 'Joana Fictícia', 'Formação Planilha', '5']) {
      expect(expandida.getByText(texto)).toBeInTheDocument();
    }
    // Nem o código interno nem a Confiança (C2b) vão para a linha expandida.
    for (const oculto of ['GERENCIA 7', 'Confiança', 'Média']) {
      expect(expandida.queryByText(oculto)).not.toBeInTheDocument();
    }
  }, 20000);

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await linhaDaGerencia();

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Setor', 'Situação', 'Ações']);
  }, 20000);

  test('tag verde com texto de contraste AA', async () => {
    renderPage();
    const linha = await linhaDaGerencia();

    expect(within(linha).getByText('Ativo')).toHaveStyle({ color: VERDE_AA });
  }, 20000);

  test('a Confiança do de-para fica fora da tela: sem coluna, sem valor e sem filtro (C2b)', async () => {
    renderPage();
    await linhaDaGerencia();

    expect(screen.queryByText('Confiança')).not.toBeInTheDocument();
    for (const rotulo of ['Média', 'Alta', 'Conferir']) {
      expect(screen.queryByText(rotulo)).not.toBeInTheDocument();
    }
    expect(screen.queryByRole('combobox', { name: /confiança/i })).not.toBeInTheDocument();
  }, 20000);

  test('a busca tem nome acessível', async () => {
    renderPage();
    await linhaDaGerencia();

    expect(screen.getByRole('searchbox', { name: /Buscar gerências/ })).toBeInTheDocument();
  }, 20000);

  test('Excluir: a confirmação cita o setor e começa no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    await linhaDaGerencia();

    // Sem projeto ativo; com projeto ativo é só o aviso (GerenciasPage.salvar.test.tsx).
    await user.click(screen.getByRole('button', { name: 'Excluir: Vidas' }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(confirmar.mock.calls[0]![0]).toMatchObject({ autoFocusButton: 'cancel' });
    expect(String(confirmar.mock.calls[0]![0].content)).toContain('"Vidas"');
    confirmar.mockRestore();
  }, 30000);

  test('Editar pela linha abre o modal de sempre com os dados da gerência', async () => {
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDaGerencia();

    await user.click(within(linha).getByRole('button', { name: `Editar: ${SETOR}` }));
    const modal = (await screen.findByText('Editar Gerencia', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]');
    expect(modal).not.toBeNull();
    expect(within(modal!).getByLabelText('Nome na tela')).toHaveValue(SETOR);
  }, 30000);
});
