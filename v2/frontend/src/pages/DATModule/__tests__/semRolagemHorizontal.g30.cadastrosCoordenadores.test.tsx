/**
 * G30 (Programa C) — Gestão de Cadastros e Gestão de Coordenadores sem rolagem horizontal.
 *
 * As duas tabelas tinham `scroll.x` (1200/1100 e 1200) e colunas fixas. Agora são o ResponsiveTable:
 * a identidade, o estado e as ações (AcoesLinha, menu no celular) ficam sempre na linha; o resto sobe
 * por largura e o que some vai para a linha expandida, onde as etapas continuam clicáveis. Em
 * Coordenadores, o cartão e a vista "Por área" quebram a área longa em vez de cortá-la, e os
 * cabeçalhos e a barra de botões dos filtros quebram linha a 360 px.
 */
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

import { definirLarguraTela } from '../../../test/larguraTela';
import { ComAcesso } from '../../../test/comAcesso';
import { atorRbac } from '../../../test/atoresRbac';

const { cadastroRow, coordRow, updateEtapa } = vi.hoisted(() => ({
  cadastroRow: {
    id: 5,
    plataforma: 'FORMAR',
    municipio: 1,
    municipio_nome: 'Fortaleza',
    uf: 'CE',
    projeto_geral: 2,
    projeto_geral_nome: 'Coleção X',
    quantidade_alunos: 120,
    quantidade_professores: 8,
    quantidade_codigos: 3,
    status_criacao_curso: 'concluido',
    status_chaves: 'pendente',
    status_instrucoes: 'pendente',
    status_envio: 'pendente',
  },
  coordRow: {
    id: 11,
    nome: 'Ana Maria',
    email: 'ana@example.invalid',
    telefone: '(85) 99999-0000',
    area: 'Formação Continuada e Acompanhamento Pedagógico',
    cargo: 'Coordenadora',
    data_admissao: '2026-01-10',
    ativo: true,
    foto_url: null,
    total_municipios: 1,
    total_projetos: 2,
  },
  updateEtapa: vi.fn().mockResolvedValue({}),
}));

vi.mock('../../../api/datModule', () => ({
  listCadastros: vi.fn().mockResolvedValue({ results: [cadastroRow], count: 1, next: null, previous: null }),
  getCadastro: vi.fn().mockResolvedValue(cadastroRow),
  createCadastro: vi.fn(),
  updateCadastro: vi.fn(),
  deleteCadastro: vi.fn(),
  updateCadastroEtapa: updateEtapa,
  getCadastrosStats: vi.fn().mockResolvedValue({ total: 1, por_plataforma: { FORMAR: 1, AVALIAR: 0 } }),
  listCoordenadoresDAT: vi.fn().mockResolvedValue({ results: [coordRow], count: 1, next: null, previous: null }),
  getCoordenadorDAT: vi.fn().mockResolvedValue({ ...coordRow, observacoes: '' }),
  createCoordenadorDAT: vi.fn(),
  updateCoordenadorDAT: vi.fn().mockResolvedValue({}),
  deleteCoordenadorDAT: vi.fn(),
  getCoordenadorAlocacoes: vi.fn().mockResolvedValue([]),
  getAreasOptions: vi.fn().mockResolvedValue([]),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getProjetosGeraisOptions: vi.fn().mockResolvedValue([]),
}));

import CadastrosPage from '../CadastrosPage';
import CoordenadoresPage from '../CoordenadoresPage';

vi.setConfig({ testTimeout: 30_000 });

const CADASTRO = 'Fortaleza - CE · Coleção X';
const COORD = 'Ana Maria';

function renderCadastros(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <CadastrosPage />
    </MemoryRouter>,
  );
}

function renderCoordenadores(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <ComAcesso policies={atorRbac('DAT').policies}>
        <CoordenadoresPage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

async function linhaPelaAcao(nome: string): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: nome }, { timeout: 15000 });
  const linha = botao.closest('tr');
  if (!linha) throw new Error('o botão não está numa linha da tabela');
  return linha;
}

function semLarguraForcada(container: HTMLElement): void {
  expect(container.querySelector('.ant-table-cell-fix-right, .ant-table-cell-fix-left')).toBeNull();
  expect(container.querySelector('.ant-table-content')?.getAttribute('style') ?? '').not.toMatch(/overflow/);
  expect(container.querySelector('table')?.style.width ?? '').toBe('');
}

function expandida(): ReturnType<typeof within> {
  return within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
}

describe('Gestão de Cadastros sem rolagem horizontal (G30)', () => {
  test('a 1280 px: identidade, etapas, link e ações na linha; sem coluna fixa nem largura forçada', async () => {
    const { container } = renderCadastros();
    const linha = await linhaPelaAcao(`Editar: ${CADASTRO}`);

    expect(cabecalhos()).toEqual([
      'Município - UF',
      'Coleção',
      'Criação Curso',
      'Chaves',
      'Instruções',
      'Envio',
      'Link',
      'Ações',
    ]);
    expect(within(linha).getByRole('button', { name: `Excluir: ${CADASTRO}` })).toBeInTheDocument();
    semLarguraForcada(container);
    // Alunos, Profs. e Códs. só entram na linha de xxl: até lá, na linha expandida.
    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${CADASTRO}` }));
    for (const texto of ['Alunos', 'Profs.', 'Códs', '120']) expect(expandida().getByText(texto)).toBeInTheDocument();
  });

  test('a 360 px: só o município e o menu de ações; as etapas na linha expandida continuam clicáveis', async () => {
    definirLarguraTela(360);
    const { container } = renderCadastros();
    const linha = await linhaPelaAcao(`Mais ações: ${CADASTRO}`);

    expect(cabecalhos()).toEqual(['Município - UF', 'Ações']);
    semLarguraForcada(container);

    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${CADASTRO}` }));
    for (const texto of ['Coleção X', 'Criação Curso', 'Envio']) expect(expandida().getByText(texto)).toBeInTheDocument();
    const etapas = expandida().getAllByRole('button', { name: /alterar status/i });
    expect(etapas).toHaveLength(4);
    fireEvent.click(etapas[0]);
    expect(updateEtapa).toHaveBeenCalledWith(5, 'criacao_curso', 'pendente');
  });

  test('a 360 px: o cabeçalho e a barra de botões dos filtros quebram linha', async () => {
    definirLarguraTela(360);
    renderCadastros();
    await linhaPelaAcao(`Mais ações: ${CADASTRO}`);

    expect(screen.getByRole('button', { name: /Novo Cadastro/ }).closest('.flex')).toHaveClass('flex-wrap');
    expect(screen.getByRole('button', { name: /Limpar/ }).closest('.flex')).toHaveClass('flex-wrap');
  });
});

describe('Gestão de Coordenadores sem rolagem horizontal (G30)', () => {
  async function abrirLista(): Promise<HTMLElement> {
    fireEvent.click(await screen.findByLabelText('Visualizar como lista', {}, { timeout: 15000 }));
    return linhaPelaAcao(`Editar: ${COORD}`);
  }

  test('lista a 1280 px: colunas por prioridade e ações pelo nome; sem coluna fixa', async () => {
    const { container } = renderCoordenadores();
    const linha = await abrirLista();

    expect(cabecalhos()).toEqual(['Foto', 'Nome', 'Área', 'Email', 'Municípios', 'Projetos', 'Status', 'Ações']);
    for (const acao of ['Ver detalhes', 'Editar', 'Excluir']) {
      expect(within(linha).getByRole('button', { name: `${acao}: ${COORD}` })).toBeInTheDocument();
    }
    semLarguraForcada(container);
    // O telefone só entra na linha de xxl.
    expect(within(linha).queryByText(coordRow.telefone)).not.toBeInTheDocument();
  });

  test('lista a 360 px: nome, status e o menu de ações; o resto na linha expandida', async () => {
    definirLarguraTela(360);
    renderCoordenadores();
    fireEvent.click(await screen.findByLabelText('Visualizar como lista', {}, { timeout: 15000 }));
    const linha = await linhaPelaAcao(`Mais ações: ${COORD}`);

    expect(cabecalhos()).toEqual(['Nome', 'Status', 'Ações']);
    expect(within(linha).getByRole('switch')).toBeInTheDocument();
    fireEvent.click(within(linha).getByRole('button', { name: `Expandir linha de ${COORD}` }));
    for (const texto of [coordRow.area, 'ana@example.invalid', coordRow.telefone]) {
      expect(expandida().getByText(texto, { exact: false })).toBeInTheDocument();
    }
  });

  test('mudar a largura com a lista aberta reorganiza as colunas', async () => {
    renderCoordenadores();
    await abrirLista();

    act(() => definirLarguraTela(768));
    expect(cabecalhos()).toEqual(['Nome', 'Área', 'Status', 'Ações']);
  });

  test('cartão e "Por área": a área longa quebra linha em vez de ser cortada', async () => {
    renderCoordenadores();
    const tagDoCartao = await screen.findByText(coordRow.area, {}, { timeout: 15000 });
    expect(tagDoCartao).toHaveStyle({ whiteSpace: 'normal' });

    fireEvent.click(screen.getByLabelText('Visualizar por área'));
    const tags = await screen.findAllByText(coordRow.area);
    for (const tag of tags) expect(tag).toHaveStyle({ whiteSpace: 'normal' });
  });

  test('a 360 px: o cabeçalho e a barra de botões dos filtros quebram linha', async () => {
    definirLarguraTela(360);
    renderCoordenadores();
    await screen.findByText(COORD, {}, { timeout: 15000 });

    expect(screen.getByRole('button', { name: /Novo Coordenador/ }).closest('header > .flex')).toHaveClass('flex-wrap');
    expect(screen.getByRole('button', { name: /Limpar/ }).closest('.flex')).toHaveClass('flex-wrap');
  });
});
