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
 * 2x) e getGerencias/getMe (via FiltersBar), todos de '../../api/availability',
 * e getMyPolicies (FiltersBar, '../../api/me'). Sem mock, esses fetch REJEITAM no
 * jsdom e logam async DEPOIS do teste -> EnvironmentTeardownError, reprovando o CI
 * mesmo com asserts passando. Mockar os módulos resolvendo com dados vazios
 * elimina o fetch pendente.
 */

import { act, render, screen, waitFor } from '@testing-library/react';
import { describe, test, expect, vi, afterEach } from 'vitest';

vi.mock('../../../api/me', () => ({
  getMyPolicies: vi.fn().mockResolvedValue([]),
}));

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
    gerencias: [{ id: 4, rotulo: 'Superativar', papeis: ['COORDENADOR'] }],
  }),
}));

import MonthlyPage from '../MonthlyPage';
import { getMonthlyAvailability } from '../../../api/availability';

const GRADE_VAZIA = { days: [], legend: {}, people: [], cells: [], details_index: {} };

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
    expect(screen.getByLabelText('Projeto')).toBeInTheDocument();
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

  // Liberação 2026-10: a atualização automática não desmonta as grades nem pisca.
  test('atualização em segundo plano mantém as duas grades na tela, sem "Carregando..."', async () => {
    await renderEDeixarResolver();
    const cabecalhos = screen.getAllByText('Nome');
    const cargasAntes = vi.mocked(getMonthlyAvailability).mock.calls.length;

    // Mesma via do polling (usePolling): o evento dispara a busca; a resposta fica em voo.
    vi.mocked(getMonthlyAvailability).mockReturnValue(new Promise(() => undefined));
    await act(async () => { window.dispatchEvent(new Event('availability:refresh')); });

    expect(vi.mocked(getMonthlyAvailability).mock.calls.length).toBe(cargasAntes + 2);
    expect(screen.queryByText('Carregando...')).not.toBeInTheDocument();
    // Os mesmos nós: as grades não foram desmontadas e remontadas.
    expect(screen.getAllByText('Nome')).toEqual(cabecalhos);
    cabecalhos.forEach((no) => expect(no).toBeInTheDocument());

    vi.mocked(getMonthlyAvailability).mockResolvedValue(GRADE_VAZIA);
  });

  test('429 na atualização: UM aviso discreto (role=status), grades na tela, sem erro', async () => {
    await renderEDeixarResolver();

    vi.mocked(getMonthlyAvailability).mockRejectedValue(
      Object.assign(new Error('Limite excedido.'), { status: 429, retryAfter: 30 }),
    );
    await act(async () => { window.dispatchEvent(new Event('availability:refresh')); });

    const avisos = await screen.findAllByText('Atualização automática pausada por alguns instantes.');
    expect(avisos).toHaveLength(1);
    expect(avisos[0]?.closest('[role="status"]')).not.toBeNull();
    expect(screen.getAllByText('Nome')).toHaveLength(2);
    expect(screen.queryByText(/Erro ao carregar/)).not.toBeInTheDocument();

    vi.mocked(getMonthlyAvailability).mockResolvedValue(GRADE_VAZIA);
  });
});
