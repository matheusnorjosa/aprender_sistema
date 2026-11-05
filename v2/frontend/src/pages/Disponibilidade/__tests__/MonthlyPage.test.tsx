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

import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, test, expect, vi, afterEach, beforeEach } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

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

// Na CI a tela roda cerca de 4x mais lenta que local: os 5 s padrão por teste e o 1 s padrão
// de findBy/waitFor não bastam. Só o limite de tempo muda, nenhuma asserção.
vi.setConfig({ testTimeout: 20_000 });
const ESPERA = { timeout: 5000 };

/**
 * Aguarda o fetch mockado resolver: cada Grid renderiza um cabeçalho "Nome".
 * Duas grades = dois cabeçalhos. Serve como ponto de sincronização estável.
 */
async function renderEDeixarResolver(): Promise<void> {
  render(<MonthlyPage />);
  await waitFor(() => {
    expect(screen.getAllByText('Nome')).toHaveLength(2);
  }, ESPERA);
}

describe('MonthlyPage — grade mensal', () => {
  afterEach(() => {
    vi.clearAllMocks();
    // clearAllMocks não desfaz mockRejectedValue/mockReturnValue. Restaurar aqui, e não no fim
    // do teste, garante que um teste que falha (e o retry dele) não deixe a grade quebrada para o próximo.
    vi.mocked(getMonthlyAvailability).mockResolvedValue(GRADE_VAZIA);
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

    const cabecalhosNome = await screen.findAllByText('Nome', undefined, ESPERA);
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
  });

  test('429 na atualização: UM aviso discreto (role=status), grades na tela, sem erro', async () => {
    await renderEDeixarResolver();

    vi.mocked(getMonthlyAvailability).mockRejectedValue(
      Object.assign(new Error('Limite excedido.'), { status: 429, retryAfter: 30 }),
    );
    await act(async () => { window.dispatchEvent(new Event('availability:refresh')); });

    const avisos = await screen.findAllByText('Atualização automática pausada por alguns instantes.', undefined, ESPERA);
    expect(avisos).toHaveLength(1);
    expect(avisos[0]?.closest('[role="status"]')).not.toBeNull();
    expect(screen.getAllByText('Nome')).toHaveLength(2);
    expect(screen.queryByText(/Erro ao carregar/)).not.toBeInTheDocument();
  });

  test('falha ao atualizar com a grade na tela: avisa (role=alert) e mantém as grades', async () => {
    await renderEDeixarResolver();

    vi.mocked(getMonthlyAvailability).mockRejectedValue(new Error('Sem conexão com o servidor.'));
    await act(async () => { window.dispatchEvent(new Event('availability:refresh')); });

    const avisos = await screen.findAllByText(/Não foi possível atualizar a grade/, undefined, ESPERA);
    expect(avisos).toHaveLength(1);
    expect(avisos[0]?.closest('[role="alert"]')).not.toBeNull();
    expect(avisos[0]?.textContent).toContain('Sem conexão com o servidor.');
    expect(screen.getAllByText('Nome')).toHaveLength(2);
  });

  // B#19: o erro da carga mostrava a todos uma dica de desenvolvedor (porta 8002), até junto do 403.
  test('falha na primeira carga: a mensagem do servidor e "Tentar de novo" em cada grade, sem dica de desenvolvedor', async () => {
    vi.mocked(getMonthlyAvailability).mockRejectedValue(new Error('Você não tem acesso a este setor.'));
    render(<MonthlyPage />);

    expect(await screen.findAllByText('Você não tem acesso a este setor.', undefined, ESPERA)).toHaveLength(2);
    expect(screen.queryByText(/porta 8002|backend/i)).not.toBeInTheDocument();

    vi.mocked(getMonthlyAvailability).mockResolvedValue(GRADE_VAZIA);
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo: carregar os formadores' }));
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo: carregar os coordenadores' }));

    await waitFor(() => expect(screen.getAllByText('Nome')).toHaveLength(2), ESPERA);
    expect(screen.queryByText(/Erro ao carregar/)).not.toBeInTheDocument();
  });

  test('botão de atualizar: o ícone gira enquanto busca e as grades continuam na tela', async () => {
    const { container } = render(<MonthlyPage />);
    await waitFor(() => expect(screen.getAllByText('Nome')).toHaveLength(2), ESPERA);
    expect(container.querySelector('.anticon-spin')).toBeNull();

    vi.mocked(getMonthlyAvailability).mockReturnValue(new Promise(() => undefined));
    const botao = container.querySelector('.anticon-sync');
    expect(botao).not.toBeNull();
    await act(async () => { fireEvent.click(botao as Element); });

    expect(container.querySelector('.anticon-spin')).not.toBeNull();
    expect(screen.queryByText('Carregando...')).not.toBeInTheDocument();
    expect(screen.getAllByText('Nome')).toHaveLength(2);
  });
});

/**
 * Sem rolagem horizontal (C4, decisão do dono): abaixo de 1280 px, uma semana por vez com
 * ‹ › dentro do mês; a partir de 1280 px (a sidebar aberta, `useResponsive`), o mês inteiro,
 * com a coluna do dia sem largura fixa. Vale nas duas grades.
 */
describe('MonthlyPage — semana abaixo de 1280 px, mês inteiro a partir de 1280', { timeout: 20000 }, () => {
  const CODIGOS = ['E', '2', 'P', 'T', 'X', 'D', 'D1'] as const;

  /** Grade densa do mês pedido: uma pessoa, código em todo dia, detalhe só no dia 21. */
  function gradeDoMes({ year, month }: { year: number; month: number }) {
    const days = Array.from({ length: new Date(year, month, 0).getDate() }, (_, i) => i + 1);
    return {
      days,
      legend: {},
      people: [{ id: 1, name: 'Ana Formadora' }],
      cells: [days.map((_, i) => CODIGOS[i % CODIGOS.length] ?? 'E')],
      details_index: {
        '0:20': [{ id: 9, municipio: 'Crato', tipo: 'Formação', data: `${year}-01-21`, inicio: '08:00', fim: '12:00' }],
      },
    };
  }

  const grades = (): HTMLElement[] => [
    screen.getByRole('article', { name: 'Formadores' }),
    screen.getByRole('article', { name: 'Coordenadores' }),
  ];
  const diasNaGrade = (grade: HTMLElement): string[] =>
    within(grade)
      .getAllByRole('columnheader')
      .map((th) => th.textContent ?? '')
      .filter((t) => t !== 'Nome');
  const diasDe = (de: number, ate: number): string[] =>
    Array.from({ length: ate - de + 1 }, (_, i) => String(de + i));

  async function abrirEm(largura: number): Promise<ReturnType<typeof render>> {
    definirLarguraTela(largura);
    const tela = render(<MonthlyPage />);
    expect(await screen.findAllByText('Ana Formadora', undefined, ESPERA)).toHaveLength(2);
    return tela;
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-01-15T12:00:00-03:00'));
    vi.mocked(getMonthlyAvailability).mockImplementation(async (params) => gradeDoMes(params));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.mocked(getMonthlyAvailability).mockResolvedValue(GRADE_VAZIA);
  });

  test.each([1024, 768, 360])('a %i px, as duas grades mostram só a semana de hoje, com o rótulo à vista', async (largura) => {
    await abrirEm(largura);

    for (const grade of grades()) expect(diasNaGrade(grade)).toEqual(diasDe(12, 18));
    expect(screen.getByText('Semana: 12 a 18/01')).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Semana mostrada' })).toBeInTheDocument();
  });

  test('"hoje" é o de Fortaleza: 31/01 às 23h30 em Fortaleza (já 01/02 em UTC) abre janeiro na última semana', async () => {
    vi.setSystemTime(new Date('2026-02-01T02:30:00Z'));
    await abrirEm(1024);

    expect(screen.getByText('01/2026')).toBeInTheDocument();
    expect(screen.getByText('Semana: 26 a 31/01')).toBeInTheDocument();
  });

  test('as setas trocam a semana nas duas grades sem sair do mês e ficam indisponíveis nas pontas', async () => {
    await abrirEm(1024);
    const anterior = screen.getByRole('button', { name: 'Semana anterior' });
    const proxima = screen.getByRole('button', { name: 'Próxima semana' });

    fireEvent.click(proxima);
    expect(screen.getByText('Semana: 19 a 25/01')).toBeInTheDocument();
    for (const grade of grades()) expect(diasNaGrade(grade)).toEqual(diasDe(19, 25));

    fireEvent.click(proxima);
    expect(diasNaGrade(grades()[0] as HTMLElement)).toEqual(diasDe(26, 31));
    expect(proxima).toHaveAttribute('aria-disabled', 'true');
    fireEvent.click(proxima);
    expect(screen.getByText('Semana: 26 a 31/01')).toBeInTheDocument();
    expect(screen.getByText('01/2026')).toBeInTheDocument();

    for (let i = 0; i < 4; i += 1) fireEvent.click(anterior);
    expect(screen.getByText('Semana: 01 a 04/01')).toBeInTheDocument();
    for (const grade of grades()) expect(diasNaGrade(grade)).toEqual(diasDe(1, 4));
    expect(anterior).toHaveAttribute('aria-disabled', 'true');
    expect(proxima).toHaveAttribute('aria-disabled', 'false');
  });

  test('a seta indisponível continua focável: o foco não se perde na ponta', async () => {
    await abrirEm(1024);
    const proxima = screen.getByRole('button', { name: 'Próxima semana' });
    proxima.focus();
    fireEvent.click(proxima);
    fireEvent.click(proxima);
    expect(proxima).toHaveAttribute('aria-disabled', 'true');
    expect(proxima).not.toBeDisabled();
    expect(proxima).toHaveFocus();
  });

  test('a 1280 px, as duas grades mostram os 31 dias, sem setas de semana e sem largura fixa por dia', async () => {
    const { container } = await abrirEm(1280);

    for (const grade of grades()) {
      expect(diasNaGrade(grade)).toEqual(diasDe(1, 31));
      expect(grade.querySelector('table')).toHaveClass('table-fixed');
      expect(grade.querySelector('.overflow-x-auto, .w-10, .w-12, [class*="min-w-["]')).toBeNull();
    }
    expect(screen.queryByRole('button', { name: 'Próxima semana' })).not.toBeInTheDocument();
    expect(screen.queryByText(/^Semana:/)).not.toBeInTheDocument();
    expect(container.querySelector('.overflow-x-auto')).toBeNull();
  });

  test('mudar a largura com a tela aberta troca entre semana e mês', async () => {
    await abrirEm(1280);

    act(() => definirLarguraTela(1024));
    expect(diasNaGrade(grades()[1] as HTMLElement)).toEqual(diasDe(12, 18));

    act(() => definirLarguraTela(1280));
    expect(diasNaGrade(grades()[1] as HTMLElement)).toEqual(diasDe(1, 31));
  });

  test('trocar de mês volta para a primeira semana do mês novo', async () => {
    await abrirEm(1024);

    fireEvent.click(screen.getByRole('button', { name: 'Próximo mês' }));

    expect(await screen.findByText('Semana: 01/02', undefined, ESPERA)).toBeInTheDocument();
    await waitFor(() => expect(diasNaGrade(grades()[0] as HTMLElement)).toEqual(['1']), ESPERA);
    expect(screen.getByRole('button', { name: 'Semana anterior' })).toHaveAttribute('aria-disabled', 'true');
  });

  test('o detalhe abre na célula certa fora da 1ª semana (o índice do dia é o do mês)', async () => {
    await abrirEm(1024);
    fireEvent.click(screen.getByRole('button', { name: 'Próxima semana' }));

    const formadores = grades()[0] as HTMLElement;
    const linha = within(formadores).getByText('Ana Formadora').closest('tr') as HTMLElement;
    // Semana de 19 a 25: o 3º dia é o 21, o único com detalhe.
    fireEvent.click(within(linha).getAllByRole('button')[2] as HTMLElement);

    expect(screen.getByRole('heading', { name: 'Detalhes: Ana Formadora - Dia 21' })).toBeInTheDocument();
    expect(screen.getByText('Crato')).toBeInTheDocument();
  });
});
