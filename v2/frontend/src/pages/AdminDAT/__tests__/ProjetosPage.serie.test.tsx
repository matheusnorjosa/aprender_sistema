/**
 * Marca de série (`Projeto.eh_serie`) e família na tela Projetos.
 *
 * - Grade: a etiqueta "Série" junto do nome (sempre na linha) e a coluna "Coleção", que é a família
 *   (`projeto_geral_nome`, só leitura; decisão do dono, 06/10/2026), e sobe a partir de `lg`.
 * - Modal: o interruptor "É série", com o texto que diz o efeito; o valor vai no PATCH/POST.
 * - Sem rolagem horizontal: lista no ResponsiveTable. Sempre na linha: nome, situação e ações;
 *   o resto sobe por largura e, escondido, aparece na linha expandida. O ID não vai para a grade.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

const { PROJETOS } = vi.hoisted(() => ({
  PROJETOS: [
    {
      id: 501,
      nome: 'A COR DA GENTE 3',
      codigo: 'ACG3',
      fluxo: 'NAO_SUPER',
      ativo: true,
      setor: 'Vidas',
      setor_efetivo: 'Vidas',
      gerencia: 4,
      gerencia_nome: 'Vidas',
      projeto_geral: 7,
      projeto_geral_nome: 'A COR DA GENTE',
      eh_serie: true,
    },
    {
      id: 502,
      nome: 'Trânsito Legal',
      codigo: 'TL',
      fluxo: 'NAO_SUPER',
      ativo: true,
      setor: 'Vidas',
      setor_efetivo: 'Vidas',
      gerencia: 4,
      gerencia_nome: 'Vidas',
      projeto_geral: null,
      projeto_geral_nome: null,
      eh_serie: false,
    },
  ],
}));

vi.mock('../../../api/adminDAT', () => ({
  listProjetos: vi.fn().mockResolvedValue({ results: PROJETOS, count: 2, next: null, previous: null }),
  createProjeto: vi.fn().mockResolvedValue({}),
  updateProjeto: vi.fn().mockResolvedValue({}),
  deleteProjeto: vi.fn().mockResolvedValue({}),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: ['Vidas'] }),
  listGerencias: vi.fn().mockResolvedValue({
    results: [{ id: 4, nome: 'GERENCIA 4', nome_setor: 'Vidas', nome_exibicao: '', rotulo: 'Vidas', ativo: true }],
    count: 1,
    next: null,
    previous: null,
  }),
}));

import ProjetosPage from '../ProjetosPage';
import { createProjeto, updateProjeto } from '../../../api/adminDAT';

const SERIE = 'A COR DA GENTE 3';
const FAMILIA_SEM = 'Trânsito Legal';

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjetosPage />
    </MemoryRouter>,
  );
}

async function linhaDe(nome: string): Promise<HTMLElement> {
  const celula = await screen.findByText(nome, { selector: 'td, td *' }, { timeout: 15000 });
  const linha = celula.closest('tr');
  if (!linha) throw new Error('o nome não está numa linha da tabela');
  return linha;
}

/** Títulos das colunas de dados (sem a do botão de expandir). */
function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

async function abrirEdicao(user: ReturnType<typeof userEvent.setup>, nome: string): Promise<HTMLElement> {
  const linha = await linhaDe(nome);
  await user.click(within(linha).getByRole('button', { name: `Editar: ${nome}` }));
  return screen.findByRole('dialog', {}, { timeout: 10000 });
}

describe('ProjetosPage — série e família', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a grade mostra a etiqueta "Série" e a família do projeto', async () => {
    renderPage();
    const serie = await linhaDe(SERIE);
    const semFamilia = await linhaDe(FAMILIA_SEM);

    expect(cabecalhos()).toEqual(['Nome', 'Código', 'Setor', 'Coleção', 'Fluxo', 'Situação', 'Ações']);
    expect(within(serie).getByText('Série')).toBeInTheDocument();
    expect(within(serie).getByText('A COR DA GENTE', { exact: true })).toBeInTheDocument();
    expect(within(semFamilia).queryByText('Série')).not.toBeInTheDocument();
    // o ID interno não vai para a grade
    expect(within(serie).queryByText('501')).not.toBeInTheDocument();
  }, 20000);

  test('a 360 px: só nome (com a etiqueta), situação e o menu de ações; a família na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDe(SERIE);

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
    expect(within(linha).getByText('Série')).toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Mais ações: ${SERIE}` })).toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${SERIE}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('Coleção')).toBeInTheDocument();
    expect(expandida.getByText('A COR DA GENTE', { exact: true })).toBeInTheDocument();
    expect(expandida.getByText('ACG3')).toBeInTheDocument();
  }, 20000);

  test('o interruptor "É série" abre com a marca do projeto e diz o efeito', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await abrirEdicao(user, SERIE);

    expect(within(dialog).getByRole('switch', { name: 'É série' })).toBeChecked();
    expect(within(dialog).getByText(/não aparece na Nova Solicitação; no Plano Anual só aparece se já tiver plano/)).toBeInTheDocument();
  }, 30000);

  test('desligar o interruptor envia eh_serie=false no salvar', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await abrirEdicao(user, SERIE);

    await user.click(within(dialog).getByRole('switch', { name: 'É série' }));
    await user.click(within(dialog).getByRole('button', { name: /salvar/i }));

    await waitFor(
      () => expect(updateProjeto).toHaveBeenCalledWith(501, expect.objectContaining({ eh_serie: false })),
      { timeout: 10000 },
    );
  }, 30000);

  test('ligar o interruptor envia eh_serie=true no salvar', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await abrirEdicao(user, FAMILIA_SEM);

    const interruptor = within(dialog).getByRole('switch', { name: 'É série' });
    expect(interruptor).not.toBeChecked();
    await user.click(interruptor);
    await user.click(within(dialog).getByRole('button', { name: /salvar/i }));

    await waitFor(
      () => expect(updateProjeto).toHaveBeenCalledWith(502, expect.objectContaining({ eh_serie: true })),
      { timeout: 10000 },
    );
  }, 30000);

  test('projeto novo nasce sem a marca', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /novo projeto/i }, { timeout: 15000 }));
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    expect(within(dialog).getByRole('switch', { name: 'É série' })).not.toBeChecked();
    await user.type(within(dialog).getByLabelText('Nome do Projeto'), 'Projeto Novo');
    await user.type(within(dialog).getByLabelText('Código'), 'PN');
    await user.click(within(dialog).getByRole('combobox', { name: 'Gerência' }));
    await user.click(await screen.findByText('Vidas', { selector: '.ant-select-item-option-content' }, { timeout: 10000 }));
    await user.click(within(dialog).getByRole('button', { name: /salvar/i }));

    await waitFor(
      () => expect(createProjeto).toHaveBeenCalledWith(expect.objectContaining({ nome: 'Projeto Novo', eh_serie: false })),
      { timeout: 10000 },
    );
  }, 40000);
});
