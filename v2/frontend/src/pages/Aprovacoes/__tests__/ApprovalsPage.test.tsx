/**
 * Tests: ApprovalsPage (fila de aprovações — fluxo SUPER, PA-06)
 *
 * Cobertura (presença/estado, sem dirigir fluxo assíncrono nem Modal.confirm):
 * - Título "Aprovações" + filtros renderizam; polling é o mock (não roda de verdade).
 * - Estado vazio: tabela renderiza sem linhas de ação de aprovar.
 * - Sem permissão (policies = []): botão "Aprovar" ausente mesmo com pendente.
 * - Com permissão (`access_solicitation_approvals`): botão "Aprovar" presente.
 * - PR B1 (PA-02 segregação): a linha da PRÓPRIA solicitação sai sem checkbox e sem
 *   Aprovar/Reprovar, com a Tag "Sua solicitação" (a de outra pessoa segue normal).
 *
 * GOTCHA: todo cliente de API que a página dispara no useEffect de mount é
 * mockado (listSolicitacoes, getMyPolicies, getMe) resolvendo com dados vazios/mínimos.
 * Sem isso, o fetch rejeita no jsdom e loga async no teardown do worker →
 * EnvironmentTeardownError, reprovando o CI mesmo com asserts verdes.
 * `usePolling` também é mockado (no-op) para não disparar polling real.
 * `computeAccess` (useCanAccess) fica REAL — a permissão é dirigida via as
 * policies mockadas, exercitando a tradução policy → canApprove de verdade.
 */

import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal } from 'antd';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { MemoryRouter } from 'react-router';
import type { CurrentUser, PaginatedResponse, Solicitacao, SolicitacaoFilters } from '../../../types';

vi.mock('../../../api/solicitacoes', () => ({
  listSolicitacoes: vi.fn(),
  approveSolicitacao: vi.fn(),
  rejectSolicitacao: vi.fn(),
  previewSolicitacao: vi.fn(),
  approveSolicitacoesBatch: vi.fn(),
  rejectSolicitacoesBatch: vi.fn(),
}));

vi.mock('../../../api/me', () => ({
  getMyPolicies: vi.fn(),
}));

vi.mock('../../../api/availability', () => ({
  getMe: vi.fn(),
}));

vi.mock('../../../hooks/usePolling', () => ({
  usePolling: vi.fn(),
}));

// Espião sobre a função real: conta quantas vezes a coluna "Formadores" é desenhada.
vi.mock('../../../utils/participants', async (importOriginal) => {
  const real = await importOriginal<typeof import('../../../utils/participants')>();
  return { ...real, formadoresLabel: vi.fn(real.formadoresLabel) };
});

import ApprovalsPage from '../ApprovalsPage';
import { approveSolicitacao, approveSolicitacoesBatch, listSolicitacoes } from '../../../api/solicitacoes';
import { getMyPolicies } from '../../../api/me';
import { getMe } from '../../../api/availability';
import { usePolling } from '../../../hooks/usePolling';
import { formadoresLabel } from '../../../utils/participants';

const pausarPolling = vi.fn();

/** Página vazia (nenhuma solicitação). */
function emptyPage(): PaginatedResponse<Solicitacao> {
  return { count: 0, next: null, previous: null, results: [] };
}

/** Constrói uma solicitação pendente mínima com os campos que a tabela lê. */
function pendingRow(overrides: Partial<Solicitacao> = {}): Solicitacao {
  return {
    id: 1,
    municipio_nome: 'MunicipioTesteAlfa',
    projeto_nome: 'ProjetoTeste',
    coordenador_nome: 'Coordenador Teste',
    tipo: 'FORMACAO',
    encontro: null,
    segmento: null,
    inicio: '2026-08-25T13:00:00Z',
    fim: '2026-08-25T15:00:00Z',
    status: 'pendente',
    participations: [],
    ...overrides,
  } as unknown as Solicitacao;
}

/** Usuário logado mínimo (`/api/me/`). */
function meUser(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 99,
    username: 'aprovadora',
    email: '',
    first_name: 'Aprovadora',
    last_name: 'Teste',
    name: 'Aprovadora Teste',
    groups: [],
    setores: [],
    funcoes: [],
    gerencias: [],
    is_superuser: false,
    is_superintendencia: false,
    can_approve_super: true,
    permissions: [],
    ...overrides,
  };
}

function renderPage(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <ApprovalsPage />
    </MemoryRouter>,
  );
}

describe('ApprovalsPage', () => {
  beforeEach(() => {
    vi.mocked(listSolicitacoes).mockResolvedValue(emptyPage());
    vi.mocked(getMyPolicies).mockResolvedValue([]);
    vi.mocked(getMe).mockResolvedValue(meUser());
    vi.mocked(usePolling).mockReturnValue({ pausado: false, pausar: pausarPolling });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  test('renderiza título e filtros; polling não roda de verdade', async () => {
    renderPage();

    expect(
      screen.getByRole('heading', { level: 2, name: 'Aprovações' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('searchbox', { name: /Buscar solicitacoes/i }),
    ).toBeInTheDocument();

    // A carga inicial usa o cliente mockado (nenhum fetch real dispara).
    await waitFor(() => expect(listSolicitacoes).toHaveBeenCalled());
    // Polling é o mock no-op — wiring presente, sem intervalo real.
    expect(usePolling).toHaveBeenCalled();
  });

  test('estado vazio: tabela renderiza sem ações de aprovação', async () => {
    renderPage();

    await waitFor(() => expect(listSolicitacoes).toHaveBeenCalled());

    expect(screen.getByRole('table')).toBeInTheDocument();
    // Sem pendentes: nenhum botão de aprovar e nenhum contador de pendentes.
    // (o ícone AntD entra no nome acessível, ex.: "check Aprovar" — daí o regex.)
    expect(screen.queryByRole('button', { name: /Aprovar/i })).not.toBeInTheDocument();
    expect(
      screen.queryByText(/solicitações aguardando aprovação/i),
    ).not.toBeInTheDocument();
  });

  test('sem permissão: não exibe "Aprovar" mesmo com solicitação pendente', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [pendingRow()],
    });
    vi.mocked(getMyPolicies).mockResolvedValue([]);

    renderPage();

    // Linha renderizou (dado da solicitação visível).
    expect(await screen.findByText('MunicipioTesteAlfa')).toBeInTheDocument();
    // Ação de preview sempre presente; aprovar/reprovar não (sem permissão).
    expect(
      screen.getByRole('button', { name: /Visualizar preview do evento/i }),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Aprovar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Reprovar/i })).not.toBeInTheDocument();
  });

  test('com permissão: exibe "Aprovar"/"Reprovar" para solicitação pendente', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue({
      count: 1,
      next: null,
      previous: null,
      results: [pendingRow()],
    });
    vi.mocked(getMyPolicies).mockResolvedValue(['access_solicitation_approvals']);

    renderPage();

    // Espera a LINHA renderizar (query de texto, rápida) e então os botões de ação
    // DENTRO da tabela. canApprove vem de computeAccess(policies) real. `findByRole`
    // por nome acessível numa tabela AntD é lento no CI (recomputa o nome de todos os
    // botões a cada poll); escopar na tabela + timeout folgado evita estourar o
    // timeout do teste sob carga (o ícone entra no nome acessível, daí o regex).
    await screen.findByText('MunicipioTesteAlfa');
    const table = screen.getByRole('table');
    const approveBtn = await within(table).findByRole(
      'button',
      { name: /Aprovar/i },
      { timeout: 10000 },
    );
    expect(approveBtn).toBeInTheDocument();
    expect(
      within(table).getByRole('button', { name: /Reprovar/i }),
    ).toBeInTheDocument();
  }, 20000);

  test('linha própria: sem checkbox e sem Aprovar/Reprovar, com a Tag "Sua solicitação"', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: [
        pendingRow({ id: 1, usuario: 99, municipio_nome: 'MunicipioProprio' }),
        pendingRow({ id: 2, usuario: 5, municipio_nome: 'MunicipioAlheio' }),
      ],
    });
    vi.mocked(getMyPolicies).mockResolvedValue(['access_solicitation_approvals']);
    vi.mocked(getMe).mockResolvedValue(meUser({ id: 99 }));

    renderPage();

    const propria = (await screen.findByText('MunicipioProprio')).closest('tr');
    const alheia = screen.getByText('MunicipioAlheio').closest('tr');
    expect(propria).not.toBeNull();
    expect(alheia).not.toBeNull();

    // A alheia segue com checkbox e ações (espera o canApprove chegar).
    await within(alheia as HTMLElement).findByRole('button', { name: /Aprovar/i }, { timeout: 10000 });
    expect(within(alheia as HTMLElement).getByRole('checkbox')).toBeInTheDocument();

    const linha = within(propria as HTMLElement);
    expect(linha.getByText('Sua solicitação')).toBeInTheDocument();
    expect(linha.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(linha.queryByRole('button', { name: /Aprovar/i })).not.toBeInTheDocument();
    expect(linha.queryByRole('button', { name: /Reprovar/i })).not.toBeInTheDocument();
  }, 20000);
  // ------------------------------------------------------------------
  // Mapa de acesso 02/10 (P6): paginação de verdade no servidor e ordem
  // "de hoje em diante, do mais próximo ao mais distante".
  // ------------------------------------------------------------------

  /** `n` pendentes de outra pessoa, ids a partir de `primeiroId`. */
  function pagina(n: number, count: number, primeiroId = 1): PaginatedResponse<Solicitacao> {
    return {
      count,
      next: null,
      previous: null,
      results: Array.from({ length: n }, (_, i) =>
        pendingRow({ id: primeiroId + i, usuario: 5, municipio_nome: `Municipio${primeiroId + i}` })),
    };
  }

  /** Último filtro enviado ao servidor. */
  function ultimoFiltro(): SolicitacaoFilters {
    const calls = vi.mocked(listSolicitacoes).mock.calls;
    return calls[calls.length - 1]?.[0] ?? {};
  }

  test('pede a primeira página ao servidor, do evento mais próximo para o mais distante', async () => {
    renderPage();

    await waitFor(() => expect(listSolicitacoes).toHaveBeenCalled());
    expect(listSolicitacoes).toHaveBeenCalledWith(expect.objectContaining({
      flow: 'SUPER',
      status: 'pendente',
      ordering: 'proximidade',
      page: 1,
      page_size: 20,
    }));
  });

  test('trocar de página busca a página no servidor e limpa a seleção', async () => {
    vi.mocked(listSolicitacoes).mockImplementation((filters = {}) =>
      Promise.resolve(filters.page === 2 ? pagina(20, 45, 21) : pagina(20, 45)));
    vi.mocked(getMyPolicies).mockResolvedValue(['access_solicitation_approvals']);

    renderPage();

    const linha = (await screen.findByText('Municipio1')).closest('tr') as HTMLElement;
    fireEvent.click(await within(linha).findByRole('checkbox', {}, { timeout: 10000 }));
    expect(await screen.findByText(/1 solicitação\(ões\) selecionada\(s\)/)).toBeInTheDocument();

    fireEvent.click(screen.getByTitle('2'));

    await waitFor(() => expect(ultimoFiltro()).toEqual(expect.objectContaining({ page: 2, page_size: 20 })));
    expect(await screen.findByText('Municipio21')).toBeInTheDocument();
    expect(screen.queryByText(/selecionada\(s\)/)).not.toBeInTheDocument();
  }, 20000);

  test('buscar volta para a página 1 e manda a busca ao servidor', async () => {
    vi.mocked(listSolicitacoes).mockImplementation((filters = {}) =>
      Promise.resolve(filters.page === 2 ? pagina(20, 45, 21) : pagina(20, 45)));

    renderPage();

    await screen.findByText('Municipio1');
    fireEvent.click(screen.getByTitle('2'));
    await screen.findByText('Municipio21');

    fireEvent.change(screen.getByRole('searchbox', { name: /Buscar solicitacoes/i }), { target: { value: 'sobral' } });

    await waitFor(() => expect(ultimoFiltro()).toEqual(expect.objectContaining({ q: 'sobral', page: 1 })));
  }, 20000);

  test('oferece 20, 50 e 100 por página (o lote do servidor aceita até 100)', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(20, 45));

    renderPage();

    await screen.findByText('Municipio1');
    const seletor = document.querySelector('.ant-pagination-options .ant-select-selector');
    expect(seletor).not.toBeNull();
    fireEvent.mouseDown(seletor as Element);

    const opcoes = await waitFor(() => {
      const itens = Array.from(document.querySelectorAll('.ant-select-item-option'));
      expect(itens).toHaveLength(3);
      return itens;
    });
    expect(opcoes.map((o) => o.textContent?.replace(/\D/g, ''))).toEqual(['20', '50', '100']);

    fireEvent.click(opcoes[2] as Element);
    await waitFor(() => expect(ultimoFiltro()).toEqual(expect.objectContaining({ page: 1, page_size: 100 })));
  }, 20000);

  test('página que deixou de existir (404) volta para a anterior, sem mensagem de erro', async () => {
    const erro = vi.spyOn(message, 'error');
    let pagina2Existe = true;
    vi.mocked(listSolicitacoes).mockImplementation((filters = {}) => {
      if (filters.page === 2) {
        return pagina2Existe
          ? Promise.resolve(pagina(1, 21, 21))
          : Promise.reject(Object.assign(new Error('Página inválida.'), { status: 404 }));
      }
      return Promise.resolve(pagina(20, pagina2Existe ? 21 : 20));
    });

    renderPage();

    await screen.findByText('Municipio1');
    fireEvent.click(screen.getByTitle('2'));
    await screen.findByText('Municipio21');

    // Outra pessoa decide o último item da última página; o polling recarrega a página 2.
    pagina2Existe = false;
    const recarregar = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { await recarregar?.(); });

    await waitFor(() => expect(ultimoFiltro()).toEqual(expect.objectContaining({ page: 1 })));
    expect(await screen.findByText('Municipio1')).toBeInTheDocument();
    expect(erro).not.toHaveBeenCalled();
    erro.mockRestore();
  }, 20000);

  test('polling tira da seleção o item que saiu da lista (sem chave órfã)', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(2, 2));
    vi.mocked(getMyPolicies).mockResolvedValue(['access_solicitation_approvals']);

    renderPage();

    const linha = (await screen.findByText('Municipio2')).closest('tr') as HTMLElement;
    fireEvent.click(await within(linha).findByRole('checkbox', {}, { timeout: 10000 }));
    expect(await screen.findByText(/1 solicitação\(ões\) selecionada\(s\)/)).toBeInTheDocument();

    // Outra pessoa decidiu o item 2: a recarga não o traz mais.
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(1, 1));
    const recarregar = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { await recarregar?.(); });

    await waitFor(() => expect(screen.queryByText('Municipio2')).not.toBeInTheDocument());
    expect(screen.queryByText(/selecionada\(s\)/)).not.toBeInTheDocument();
  }, 20000);

  test('resposta mais lenta que o polling ainda aparece (o tick não descarta a carga em voo)', async () => {
    // Rede lenta: a carga do mount só responde depois do tick de 5 s.
    let responder: (dados: PaginatedResponse<Solicitacao>) => void = () => undefined;
    vi.mocked(listSolicitacoes)
      .mockReset()
      .mockReturnValueOnce(new Promise((resolve) => { responder = resolve; }))
      .mockReturnValue(new Promise(() => undefined));

    renderPage();
    await waitFor(() => expect(listSolicitacoes).toHaveBeenCalledTimes(1));

    const tick = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { void tick?.(); });
    await act(async () => { responder(pagina(1, 1)); });

    expect(await screen.findByText('Municipio1')).toBeInTheDocument();
    expect(listSolicitacoes).toHaveBeenCalledTimes(1);
  }, 20000);

  test('trocar de página com carga em voo busca a página nova (latest-wins continua valendo)', async () => {
    let responder: (dados: PaginatedResponse<Solicitacao>) => void = () => undefined;
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(20, 45));

    renderPage();
    await screen.findByText('Municipio1');

    // Um tick fica em voo; a troca de página não espera por ele e a resposta dele é descartada.
    vi.mocked(listSolicitacoes).mockReturnValueOnce(new Promise((resolve) => { responder = resolve; }));
    const tick = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { void tick?.(); });
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(20, 45, 21));
    fireEvent.click(await screen.findByTitle('2'));

    expect(await screen.findByText('Municipio21')).toBeInTheDocument();
    await act(async () => { responder(pagina(20, 45)); });
    expect(screen.getByText('Municipio21')).toBeInTheDocument();
    expect(screen.queryByText('Municipio1')).not.toBeInTheDocument();
  }, 20000);
  // ------------------------------------------------------------------
  // Liberação 2026-10: intervalo, atualização sem piscar e pausa por 429.
  // ------------------------------------------------------------------

  test('polling a cada 20 s e sem busca dupla no mount (a carga inicial é da página)', async () => {
    renderPage();
    await waitFor(() => expect(listSolicitacoes).toHaveBeenCalledTimes(1));

    expect(vi.mocked(usePolling).mock.calls[0]?.[1]).toEqual(
      expect.objectContaining({ intervalMs: 20_000, immediate: false }),
    );
  });

  test('atualização em segundo plano não mostra carregamento e mantém a lista na tela', async () => {
    let responder: (dados: PaginatedResponse<Solicitacao>) => void = () => undefined;
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(2, 2));

    const { container } = renderPage();
    await screen.findByText('Municipio1');
    await waitFor(() => expect(container.querySelector('.ant-spin-spinning')).toBeNull());

    vi.mocked(listSolicitacoes).mockReturnValueOnce(new Promise((resolve) => { responder = resolve; }));
    const tick = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { void tick?.(); });

    // O Spin do antd liga com um setTimeout: dá tempo de ele aparecer antes de conferir.
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 50)); });
    // Carga em voo: nada de spinner; os dados antigos continuam na tela.
    expect(container.querySelector('.ant-spin-spinning')).toBeNull();
    expect(screen.getByText('Municipio1')).toBeInTheDocument();

    await act(async () => { responder(pagina(3, 3)); });
    expect(await screen.findByText('Municipio3')).toBeInTheDocument();
  }, 20000);

  test('atualização em segundo plano com os mesmos dados não redesenha a tabela', async () => {
    vi.mocked(listSolicitacoes).mockImplementation(() => Promise.resolve(pagina(2, 2)));

    renderPage();
    await screen.findByText('Municipio2');
    await waitFor(() => expect(getMe).toHaveBeenCalled());
    await act(async () => { await Promise.resolve(); });
    const desenhosAntes = vi.mocked(formadoresLabel).mock.calls.length;

    const tick = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { await tick?.(); });

    expect(listSolicitacoes).toHaveBeenCalledTimes(2);
    expect(vi.mocked(formadoresLabel).mock.calls.length).toBe(desenhosAntes);
  }, 20000);

  test('429 na atualização: pausa o polling pelo Retry-After, sem mensagem de erro', async () => {
    const erro = vi.spyOn(message, 'error');
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(1, 1));

    renderPage();
    await screen.findByText('Municipio1');

    vi.mocked(listSolicitacoes).mockRejectedValue(
      Object.assign(new Error('Limite excedido.'), { status: 429, retryAfter: 30 }),
    );
    const tick = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { await tick?.(); });

    expect(pausarPolling).toHaveBeenCalledWith(30_000);
    expect(erro).not.toHaveBeenCalled();
    expect(screen.getByText('Municipio1')).toBeInTheDocument();
  }, 20000);

  test('polling pausado mostra UM aviso discreto (role=status)', async () => {
    vi.mocked(usePolling).mockReturnValue({ pausado: true, pausar: pausarPolling });

    renderPage();

    const avisos = await screen.findAllByText('Atualização automática pausada por alguns instantes.');
    expect(avisos).toHaveLength(1);
    expect(avisos[0]?.closest('[role="status"]')).not.toBeNull();
  });

  const LISTA_NAO_CARREGOU = /Não foi possível carregar agora/;
  const erro429 = (): Error => Object.assign(new Error('Limite excedido.'), { status: 429 });

  test('429 na primeira carga: diz que a lista não carregou (role=alert) e pausa o polling', async () => {
    vi.mocked(listSolicitacoes).mockRejectedValue(erro429());

    renderPage();

    const aviso = await screen.findByText(LISTA_NAO_CARREGOU);
    expect(aviso.closest('[role="alert"]')).not.toBeNull();
    expect(pausarPolling).toHaveBeenCalledWith(60_000);
  });

  test('429 em carga pedida pela pessoa (busca): avisa que a tela pode não corresponder; some quando carrega', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(1, 1));
    renderPage();
    await screen.findByText('Municipio1');
    expect(screen.queryByText(LISTA_NAO_CARREGOU)).not.toBeInTheDocument();

    vi.mocked(listSolicitacoes).mockRejectedValue(erro429());
    fireEvent.change(screen.getByRole('searchbox', { name: /Buscar solicitacoes/i }), { target: { value: 'sobral' } });
    expect(await screen.findByText(LISTA_NAO_CARREGOU)).toBeInTheDocument();

    // Fim da pausa: o polling busca de novo e a carga atende o filtro pedido.
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(1, 1));
    const tick = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { await tick?.(); });
    expect(screen.queryByText(LISTA_NAO_CARREGOU)).not.toBeInTheDocument();
  }, 20000);

  test('429 só na atualização em segundo plano não mostra o aviso de carga que falhou', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(1, 1));
    renderPage();
    await screen.findByText('Municipio1');

    vi.mocked(listSolicitacoes).mockRejectedValue(erro429());
    const tick = vi.mocked(usePolling).mock.calls[0]?.[0];
    await act(async () => { await tick?.(); });

    expect(pausarPolling).toHaveBeenCalledWith(60_000);
    expect(screen.queryByText(LISTA_NAO_CARREGOU)).not.toBeInTheDocument();
  }, 20000);

  // ------------------------------------------------------------------
  // Mapa de acesso 02/10 (P9): o erro ao aprovar diz quem e por quê.
  // ------------------------------------------------------------------

  /**
   * Modal.confirm/Modal.error são estáticos e não montam no jsdom deste projeto: o teste
   * espia a chamada (padrão das telas AdminDAT) e dispara o `onOk` à mão.
   */
  const semModal = (): { destroy: () => void; update: () => void } => ({ destroy: vi.fn(), update: vi.fn() });

  async function confirmar(spy: ReturnType<typeof vi.spyOn>): Promise<void> {
    await waitFor(() => expect(spy).toHaveBeenCalled());
    const config = spy.mock.calls[0]?.[0] as { onOk?: () => Promise<void> };
    await act(async () => { await config.onOk?.(); });
  }

  const DETALHE_CONFLITO = 'Não é possível aprovar a solicitação: Bruno Formador tem outro evento aprovado neste horário.';
  const BLOQUEADOS = [
    {
      usuario_id: 7,
      usuario_nome: 'Bruno Formador',
      conflicts: [{ code: 'X' as const, title: 'Sobreposição', detail: 'Conflita com evento aprovado #5 (15:00 10/03–17:00 10/03)', ref_id: 5 }],
    },
  ];

  test('lote com erros lista o evento e o motivo de cada um', async () => {
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(2, 2));
    vi.mocked(getMyPolicies).mockResolvedValue(['access_solicitation_approvals']);
    vi.mocked(approveSolicitacoesBatch).mockResolvedValue({
      approved: 1,
      errors: [
        { id: 2, code: 'availability_conflict', detail: DETALHE_CONFLITO, blocked_participants: BLOQUEADOS },
        { id: 77, detail: 'Solicitação não encontrada' },
      ],
    });

    renderPage();

    for (const municipio of ['Municipio1', 'Municipio2']) {
      const linha = (await screen.findByText(municipio)).closest('tr') as HTMLElement;
      fireEvent.click(await within(linha).findByRole('checkbox', {}, { timeout: 10000 }));
    }
    const confirmacao = vi.spyOn(Modal, 'confirm').mockImplementation(semModal);
    fireEvent.click(await screen.findByRole('button', { name: /Aprovar Selecionadas/ }));
    await confirmar(confirmacao);

    const aviso = await screen.findByRole('status');
    expect(within(aviso).getByText('2 solicitação(ões) não foram aprovadas')).toBeInTheDocument();
    // Evento (data · município · projeto) + motivo; o que não está na tela vai pelo número.
    expect(within(aviso).getByText(/25\/08\/2026 · Municipio2 · ProjetoTeste/)).toBeInTheDocument();
    expect(within(aviso).getByText(/tem outro evento aprovado neste horário/)).toBeInTheDocument();
    expect(within(aviso).getByText(/Solicitação #77/)).toBeInTheDocument();
    expect(within(aviso).getByText(/Solicitação não encontrada/)).toBeInTheDocument();
  }, 30000);

  test('aprovar um com conflito de agenda mostra quem e por quê', async () => {
    const erro = vi.spyOn(message, 'error');
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(1, 1));
    vi.mocked(getMyPolicies).mockResolvedValue(['access_solicitation_approvals']);
    vi.mocked(approveSolicitacao).mockRejectedValue(Object.assign(new Error(DETALHE_CONFLITO), {
      status: 400,
      response: {
        status: 400,
        data: { code: 'availability_conflict', detail: DETALHE_CONFLITO, errors: { blocked_participants: BLOQUEADOS } },
      },
    }));

    renderPage();

    const linha = (await screen.findByText('Municipio1')).closest('tr') as HTMLElement;
    const confirmacao = vi.spyOn(Modal, 'confirm').mockImplementation(semModal);
    const modalDeErro = vi.spyOn(Modal, 'error').mockImplementation(semModal);
    fireEvent.click(await within(linha).findByRole('button', { name: /Aprovar/ }, { timeout: 10000 }));
    await confirmar(confirmacao);

    expect(modalDeErro).toHaveBeenCalledTimes(1);
    const modal = modalDeErro.mock.calls[0]?.[0];
    expect(modal?.title).toBe('Não foi possível aprovar');
    render(<>{modal?.content}</>);
    expect(screen.getByText(DETALHE_CONFLITO)).toBeInTheDocument();
    expect(screen.getByText('Bruno Formador')).toBeInTheDocument();
    expect(screen.getByText('Sobreposição')).toBeInTheDocument();
    expect(screen.getByText(/Reprove a solicitação ou peça a quem criou/)).toBeInTheDocument();
    expect(erro).not.toHaveBeenCalled();
    erro.mockRestore();
  }, 30000);

  test('aprovar um com outro erro segue na mensagem curta', async () => {
    const erro = vi.spyOn(message, 'error');
    vi.mocked(listSolicitacoes).mockResolvedValue(pagina(1, 1));
    vi.mocked(getMyPolicies).mockResolvedValue(['access_solicitation_approvals']);
    vi.mocked(approveSolicitacao).mockRejectedValue(Object.assign(new Error('Solicitação já aprovada.'), {
      status: 400,
      response: { status: 400, data: { code: 'already_approved', detail: 'Solicitação já aprovada.' } },
    }));

    renderPage();

    const linha = (await screen.findByText('Municipio1')).closest('tr') as HTMLElement;
    const confirmacao = vi.spyOn(Modal, 'confirm').mockImplementation(semModal);
    const modalDeErro = vi.spyOn(Modal, 'error').mockImplementation(semModal);
    fireEvent.click(await within(linha).findByRole('button', { name: /Aprovar/ }, { timeout: 10000 }));
    await confirmar(confirmacao);

    expect(erro).toHaveBeenCalledWith('Erro ao aprovar: Solicitação já aprovada.');
    expect(modalDeErro).not.toHaveBeenCalled();
    erro.mockRestore();
  }, 30000);
});
