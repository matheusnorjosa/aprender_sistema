/**
 * C2 (Programa C) — Coleções (ProjetoGeral) sem rolagem horizontal: lista enxuta no ResponsiveTable.
 *
 * Sempre na linha: o nome, Situação e as ações (AcoesLinha, "Editar: <nome>"). As demais sobem
 * por largura: Cálculo de códigos a partir de md, Usa AVALIAR e Projetos de lg. O que some da
 * linha vai para a linha expandida. Nunca na grade: ID e descrição.
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

const { ITEMS } = vi.hoisted(() => ({
  ITEMS: [
    {
      id: 1, nome: 'PROJETO AMMA', usa_avaliar: true, tipo_calculo_codigos: 'por_aluno', divisor_aluno: 20,
      multiplicador_professor: '1.10', ativo: true, descricao: 'Descrição longa do projeto geral de teste',
      projetos_count: 3, created_at: '', updated_at: '',
    },
    {
      id: 2, nome: 'PROJETO VIDAS', usa_avaliar: false, tipo_calculo_codigos: 'por_professor', divisor_aluno: 20,
      multiplicador_professor: '1.10', ativo: false, descricao: '', projetos_count: 1, created_at: '', updated_at: '',
    },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetosGerais: vi.fn().mockResolvedValue({ results: ITEMS, count: 2, next: null, previous: null }),
  createProjetoGeral: vi.fn().mockResolvedValue({ id: 3 }),
  updateProjetoGeral: vi.fn().mockResolvedValue({}),
  deleteProjetoGeral: vi.fn().mockResolvedValue({}),
}));

import ProjetosGeraisPage from '../ProjetosGeraisPage';

const NOME = 'PROJETO AMMA';
const CALCULO = 'Por aluno (alunos ÷ divisor)';
/** Texto com contraste AA na tag green (TEXTO_DA_TAG do padrão). */
const VERDE_AA = '#237804';

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <ProjetosGeraisPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

/** A linha do projeto, achada pelo botão de ações que leva o nome dele. */
async function linhaDoProjeto(acao: 'Editar' | 'Mais ações' = 'Editar'): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: `${acao}: ${NOME}` }, { timeout: 15000 });
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

describe('ProjetosGeraisPage responsiva (C2)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a 1280 px: lista enxuta, sem ID nem linha expandida; ações pelo nome', async () => {
    renderPage();
    const linha = await linhaDoProjeto();

    expect(cabecalhos()).toEqual(['Nome', 'Usa AVALIAR', 'Cálculo de códigos', 'Projetos', 'Situação', 'Ações']);
    // O nome (identidade) quebra linha em vez de cortar com reticências: não há detalhe que o mostre.
    expect(within(linha).getByText(NOME).closest('td')).not.toHaveClass('ant-table-cell-ellipsis');
    expect(within(linha).getByRole('button', { name: `Excluir: ${NOME}` })).toBeInTheDocument();
    expect(within(linha).queryByText('Descrição longa do projeto geral de teste')).not.toBeInTheDocument();
    expect(within(linha).queryByRole('button', { name: /Expandir linha/ })).not.toBeInTheDocument();
  }, 20000);

  test('a 768 px: nome, cálculo, Situação e ações', async () => {
    definirLarguraTela(768);
    renderPage();
    await linhaDoProjeto();

    expect(cabecalhos()).toEqual(['Nome', 'Cálculo de códigos', 'Situação', 'Ações']);
  }, 20000);

  test('a 360 px: só nome, Situação e o menu de ações; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoProjeto('Mais ações');

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
    expect(within(linha).queryByRole('button', { name: `Editar: ${NOME}` })).not.toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${NOME}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText(CALCULO)).toBeInTheDocument();
    expect(expandida.getByText('Usa AVALIAR')).toBeInTheDocument();
    expect(expandida.getByText('3')).toBeInTheDocument();
  }, 20000);

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await linhaDoProjeto();

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
  }, 20000);

  test('tags verdes com texto de contraste AA', async () => {
    renderPage();
    const linha = await linhaDoProjeto();

    // Usa AVALIAR (Sim) e Situação (Ativo, como em Usuários, Municípios e Produtos).
    for (const tag of [within(linha).getByText('Sim'), within(linha).getByText('Ativo')]) {
      expect(tag).toHaveStyle({ color: VERDE_AA });
    }
  }, 20000);

  test('a busca tem nome acessível', async () => {
    renderPage();
    await linhaDoProjeto();

    expect(screen.getByRole('searchbox', { name: /Buscar coleções/ })).toBeInTheDocument();
  }, 20000);

  test('a tela se chama Coleções: a família do projeto é a coleção (decisão do dono, 06/10/2026)', async () => {
    renderPage();
    await linhaDoProjeto();

    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(/^Coleções$/);
    expect(screen.getByRole('button', { name: /Nova Coleção/ })).toBeInTheDocument();
  }, 20000);

  test('Excluir: a confirmação cita o nome e começa no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoProjeto();

    await user.click(within(linha).getByRole('button', { name: `Excluir: ${NOME}` }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(confirmar.mock.calls[0]![0]).toMatchObject({ autoFocusButton: 'cancel' });
    expect(String(confirmar.mock.calls[0]![0].content)).toContain(`"${NOME}"`);
    confirmar.mockRestore();
  }, 30000);

  test('Editar pela linha abre o modal de sempre com os dados do projeto', async () => {
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoProjeto();

    await user.click(within(linha).getByRole('button', { name: `Editar: ${NOME}` }));
    const modal = (await screen.findByText('Editar Coleção', {}, { timeout: 10000 })).closest<HTMLElement>(
      '[role="dialog"]',
    );
    expect(modal).not.toBeNull();
    expect(within(modal!).getByLabelText('Nome')).toHaveValue(NOME);
  }, 30000);
});
