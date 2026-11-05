/**
 * Gestão de Ações e Gestão de Coordenadores (Controle e DAT, alinhamento das telas, 05/11/2026).
 *
 * - Excluir aparecia para o Controle na linha, no cartão e no rodapé do modal, mas o `destroy`
 *   das duas exige `execute_restricted_operations` (só o DAT e o superusuário): o Controle
 *   confirmava e recebia "Erro ao excluir: Acesso restrito ao setor DAT.". Como em Compras
 *   (item 38), Excluir só aparece para quem pode.
 * - "Exportar" não fazia nada (botão sem ação): saiu.
 * - Erro ao abrir a edição da ação sem acento ("acao", "edicao").
 *
 * Atores: CONTROLE e DAT de `test/atoresRbac.ts` (as policies medidas no backend).
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { message } from 'antd';

import { ComAcesso } from '../../../test/comAcesso';
import { atorRbac } from '../../../test/atoresRbac';

const { acaoRow, coordRow } = vi.hoisted(() => ({
  acaoRow: {
    id: 7,
    municipio: 1,
    municipio_nome: 'Fortaleza',
    municipio_uf: 'CE',
    projeto: 2,
    projeto_nome: 'Sub X',
    projeto_geral_nome: 'Coleção X',
    coordenador: 3,
    coordenador_nome: 'Josefa Coordenadora',
    status_carta: 'concluido',
    status_contato: 'pendente',
    status_reuniao: 'pendente',
    status_entrega: 'pendente',
  },
  coordRow: {
    id: 11, nome: 'Ana', email: 'a@example.invalid', telefone: '', area: 'DAT', cargo: '',
    data_admissao: '2026-01-10', ativo: true, foto_url: null, total_municipios: 1, total_projetos: 2,
  },
}));

vi.mock('../../../api/datModule', () => ({
  listAcoes: vi.fn().mockResolvedValue({ results: [acaoRow], count: 1, next: null, previous: null }),
  getAcao: vi.fn().mockResolvedValue(acaoRow),
  createAcao: vi.fn(),
  updateAcao: vi.fn(),
  deleteAcao: vi.fn(),
  getAcoesStats: vi.fn().mockResolvedValue({}),
  listCoordenadoresDAT: vi.fn().mockResolvedValue({ results: [coordRow], count: 1, next: null, previous: null }),
  getCoordenadorDAT: vi.fn().mockResolvedValue({ ...coordRow, observacoes: '' }),
  createCoordenadorDAT: vi.fn(),
  updateCoordenadorDAT: vi.fn().mockResolvedValue({}),
  deleteCoordenadorDAT: vi.fn(),
  getCoordenadorAlocacoes: vi.fn().mockResolvedValue([]),
  getAreasOptions: vi.fn().mockResolvedValue([]),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

import AcoesPage from '../AcoesPage';
import CoordenadoresPage from '../CoordenadoresPage';
import { getAcao } from '../../../api/datModule';

const CONTROLE = atorRbac('Controle').policies;
const DAT = atorRbac('DAT').policies;
const ACAO = 'Fortaleza - CE · Sub X';

function renderAcoes(policies: readonly string[]): void {
  render(
    <MemoryRouter>
      <ComAcesso policies={policies}>
        <AcoesPage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

function renderCoordenadores(policies: readonly string[]): void {
  render(
    <MemoryRouter>
      <ComAcesso policies={policies}>
        <CoordenadoresPage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

async function linhaPelaAcao(nome: string): Promise<HTMLElement> {
  const botao = await screen.findByRole('button', { name: nome }, { timeout: 15000 });
  const linha = botao.closest('tr');
  if (!linha) throw new Error('o botão não está numa linha da tabela');
  return linha;
}

beforeEach(() => vi.clearAllMocks());

describe('Gestão de Ações', { timeout: 20000 }, () => {
  test('o Controle não vê Excluir, nem na linha nem no modal', async () => {
    renderAcoes(CONTROLE);
    const linha = await linhaPelaAcao(`Editar: ${ACAO}`);
    expect(within(linha).queryByRole('button', { name: /Excluir/ })).not.toBeInTheDocument();

    fireEvent.click(within(linha).getByRole('button', { name: `Editar: ${ACAO}` }));
    await screen.findByText('Editar Ação');
    expect(screen.queryByRole('button', { name: /Excluir/ })).not.toBeInTheDocument();
  });

  test('o DAT vê Excluir na linha e no modal', async () => {
    renderAcoes(DAT);
    const linha = await linhaPelaAcao(`Editar: ${ACAO}`);
    expect(within(linha).getByRole('button', { name: `Excluir: ${ACAO}` })).toBeInTheDocument();

    fireEvent.click(within(linha).getByRole('button', { name: `Editar: ${ACAO}` }));
    await screen.findByText('Editar Ação');
    expect(screen.getByRole('button', { name: /Excluir$/ })).toBeInTheDocument();
  });

  test('não há botão Exportar (não faz nada)', async () => {
    renderAcoes(DAT);
    await linhaPelaAcao(`Editar: ${ACAO}`);
    expect(screen.queryByRole('button', { name: /Exportar/ })).not.toBeInTheDocument();
  });

  test('o erro ao abrir a edição sai com acento', async () => {
    const erro = vi.spyOn(message, 'error').mockImplementation(() => Promise.resolve(true) as never);
    vi.mocked(getAcao).mockRejectedValueOnce(new Error('Sem conexão com o servidor.'));
    renderAcoes(CONTROLE);
    const linha = await linhaPelaAcao(`Editar: ${ACAO}`);

    fireEvent.click(within(linha).getByRole('button', { name: `Editar: ${ACAO}` }));

    await waitFor(() =>
      expect(erro).toHaveBeenCalledWith('Erro ao carregar a ação para edição: Sem conexão com o servidor.'),
    );
    erro.mockRestore();
  });
});

describe('Gestão de Coordenadores', { timeout: 20000 }, () => {
  test('o Controle não vê Excluir no cartão, na lista nem no modal', async () => {
    renderCoordenadores(CONTROLE);
    await screen.findByText('Ana', {}, { timeout: 15000 });
    // Cartões (vista padrão): os ícones das ações são ícones do AntD (role img, nome do ícone).
    expect(screen.getByRole('img', { name: 'edit' })).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'delete' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Visualizar como lista'));
    const editar = await screen.findByLabelText('Editar coordenador', {}, { timeout: 15000 });
    expect(screen.queryByLabelText('Excluir coordenador')).not.toBeInTheDocument();

    fireEvent.click(editar);
    await screen.findByText('Editar Coordenador');
    expect(screen.queryByRole('button', { name: /Excluir/ })).not.toBeInTheDocument();
  });

  test('o DAT vê Excluir no cartão, na lista e no modal', async () => {
    renderCoordenadores(DAT);
    await screen.findByText('Ana', {}, { timeout: 15000 });
    expect(screen.getByRole('img', { name: 'delete' })).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Visualizar como lista'));
    const editar = await screen.findByLabelText('Editar coordenador', {}, { timeout: 15000 });
    expect(screen.getByLabelText('Excluir coordenador')).toBeInTheDocument();

    fireEvent.click(editar);
    await screen.findByText('Editar Coordenador');
    expect(screen.getByRole('button', { name: /Excluir$/ })).toBeInTheDocument();
  });

  test('não há botão Exportar (não faz nada)', async () => {
    renderCoordenadores(DAT);
    await screen.findByText('Ana', {}, { timeout: 15000 });
    expect(screen.queryByRole('button', { name: /Exportar/ })).not.toBeInTheDocument();
  });
});
