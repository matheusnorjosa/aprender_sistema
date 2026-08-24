/**
 * Tests: MonthlyPage — Grade Mensal de Disponibilidade (RD).
 *
 * Cobertura (presença + estado, sem fluxo assíncrono frágil):
 * - Título/heading da grade
 * - Barra de filtros (nav + campos)
 * - Legenda
 * - As duas grades (Formadores / Coordenadores)
 * - Estado com dados após o fetch mockado resolver
 *
 * GOTCHA: no mount a página dispara getMonthlyAvailability (via useMonthlyQuery,
 * 2x) e getGerencias/getMe (via FiltersBar), todos de '../../api/availability'.
 * Sem mock, esses fetch REJEITAM no jsdom e logam async DEPOIS do teste
 * -> EnvironmentTeardownError, reprovando o CI mesmo com asserts passando.
 * Mockar o módulo inteiro resolvendo com dados vazios elimina o fetch pendente.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { describe, test, expect, vi, afterEach } from 'vitest';

vi.mock('../../../api/availability', () => ({
  getMonthlyAvailability: vi.fn().mockResolvedValue({
    days: [],
    legend: {},
    people: [],
    cells: [],
    details_index: {},
  }),
  getGerencias: vi.fn().mockResolvedValue([]),
  getMe: vi.fn().mockResolvedValue({
    id: 1,
    username: 'tester',
    is_superuser: false,
    is_superintendencia: false,
    can_approve_super: false,
    setores: [],
    funcoes: [],
  }),
}));

import MonthlyPage from '../MonthlyPage';

/**
 * Aguarda o fetch mockado resolver: cada Grid renderiza um cabeçalho "Nome".
 * Duas grades = dois cabeçalhos. Serve como ponto de sincronização estável.
 */
async function renderEDeixarResolver(): Promise<void> {
  render(<MonthlyPage />);
  await waitFor(() => {
    expect(screen.getAllByText('Nome')).toHaveLength(2);
  });
}

describe('MonthlyPage — grade mensal', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  test('renderiza o título da grade', async () => {
    await renderEDeixarResolver();

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: /Grade Mensal de Disponibilidade/i,
      }),
    ).toBeInTheDocument();
  });

  test('renderiza a barra de filtros com os campos', async () => {
    await renderEDeixarResolver();

    expect(
      screen.getByRole('navigation', { name: /Filtros da grade/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Gerência')).toBeInTheDocument();
    expect(screen.getByLabelText('Setor')).toBeInTheDocument();
    expect(screen.getByLabelText('Buscar')).toBeInTheDocument();
  });

  test('renderiza a legenda', async () => {
    await renderEDeixarResolver();

    expect(
      screen.getByRole('complementary', { name: /Legenda de cores/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Legenda' }),
    ).toBeInTheDocument();
  });

  test('renderiza as duas grades (Formadores e Coordenadores)', async () => {
    await renderEDeixarResolver();

    expect(
      screen.getByRole('heading', { level: 2, name: 'Formadores' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: 'Coordenadores' }),
    ).toBeInTheDocument();
  });

  test('exibe as grades após o fetch mockado resolver', async () => {
    render(<MonthlyPage />);

    const cabecalhosNome = await screen.findAllByText('Nome');
    expect(cabecalhosNome).toHaveLength(2);
  });
});
