/**
 * Plano Anual e a regra da compra (14/10/2026): a lista de projetos do modal esconde o projeto
 * "em espera" (`comCompra`; o servidor isenta quem é isento). O plano já gravado num projeto em
 * espera continua mostrando o nome dele no modal de edição. O filtro da listagem é consulta e fica
 * fora da regra: oferece todos os projetos.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

vi.mock('../../../api/datModule', () => ({
  listPlanoFormacoes: vi.fn().mockResolvedValue({
    results: [
      {
        id: 1,
        municipio: 1,
        municipio_nome: 'Municipio Teste',
        municipio_uf: 'CE',
        projeto: 9,
        projeto_nome: 'Projeto Em Espera',
        ano: 2026,
        coordenador: null,
        coordenador_nome: null,
        ch_estudo: 10,
        ch_anual: 20,
        observacoes: null,
        formacoes_list: [],
        acompanhamentos_list: [],
        provas_list: [],
      },
    ],
    count: 1,
    next: null,
    previous: null,
  }),
  createPlanoFormacoes: vi.fn().mockResolvedValue({}),
  updatePlanoFormacoes: vi.fn().mockResolvedValue({}),
  deletePlanoFormacoes: vi.fn().mockResolvedValue({}),
  getPlanoFormacoesStats: vi.fn().mockResolvedValue({
    total_planos: 1,
    total_formacoes: 0,
    total_realizadas: 0,
    taxa_realizacao: 0,
    ch_total: 20,
  }),
  updateFormacaoInline: vi.fn().mockResolvedValue({}),
  getMunicipiosOptions: vi.fn().mockResolvedValue([{ id: 1, nome: 'Municipio Teste' }]),
  getProjetosOptions: vi.fn((opts?: { comCompra?: boolean }) =>
    Promise.resolve(
      opts?.comCompra
        ? [{ id: 2, nome: 'Projeto Com Compra' }]
        : [
            { id: 2, nome: 'Projeto Com Compra' },
            { id: 9, nome: 'Projeto Em Espera' },
          ],
    ),
  ),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../../api/availability', () => ({
  getMe: vi.fn().mockResolvedValue({ is_superuser: false, setores: [], funcoes: [] }),
}));

import PlanoFormacoesPage from '../PlanoFormacoesPage';
import { getProjetosOptions } from '../../../api/datModule';

describe('Plano Anual — regra da compra', () => {
  beforeEach(() => vi.clearAllMocks());

  test('pede os projetos sem os "em espera"', async () => {
    render(
      <MemoryRouter>
        <PlanoFormacoesPage />
      </MemoryRouter>,
    );
    await screen.findByText('Projeto Em Espera', {}, { timeout: 15000 });
    expect(getProjetosOptions).toHaveBeenCalledWith({ excludeKits: true, comCompra: true });
  }, 20000);

  test('filtro Projeto da listagem (consulta) oferece o projeto em espera', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <PlanoFormacoesPage />
      </MemoryRouter>,
    );
    await screen.findByText('Projeto Em Espera', {}, { timeout: 15000 });
    expect(getProjetosOptions).toHaveBeenCalledWith({ excludeKits: true });
    const filtros = screen.getByRole('navigation', { name: 'Filtros de busca' });
    const [, filtroProjeto] = within(filtros).getAllByRole('combobox');
    await user.click(filtroProjeto);
    await waitFor(
      () => {
        const opcoes = screen.getAllByTitle('Projeto Em Espera');
        expect(opcoes.some((el) => el.classList.contains('ant-select-item-option'))).toBe(true);
      },
      { timeout: 5000 },
    );
  }, 30000);

  test('editar plano de projeto em espera mostra o nome do projeto no modal', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <PlanoFormacoesPage />
      </MemoryRouter>,
    );
    await user.click(await screen.findByRole('button', { name: /Editar plano/i }, { timeout: 15000 }));
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
    expect(within(dialog).getByText('Projeto Em Espera', { selector: '.ant-select-selection-item' })).toBeInTheDocument();
  }, 30000);
});
