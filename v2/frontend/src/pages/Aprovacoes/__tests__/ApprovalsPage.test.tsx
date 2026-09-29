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

import { render, screen, waitFor, within } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { MemoryRouter } from 'react-router';
import type { CurrentUser, PaginatedResponse, Solicitacao } from '../../../types';

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

import ApprovalsPage from '../ApprovalsPage';
import { listSolicitacoes } from '../../../api/solicitacoes';
import { getMyPolicies } from '../../../api/me';
import { getMe } from '../../../api/availability';
import { usePolling } from '../../../hooks/usePolling';

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
  });

  afterEach(() => {
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
});
