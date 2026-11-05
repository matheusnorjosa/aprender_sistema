import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

const { listSolicitacoesMock, deleteSolicitacaoMock } = vi.hoisted(() => ({
  listSolicitacoesMock: vi.fn(),
  deleteSolicitacaoMock: vi.fn(),
}));

vi.mock('../../../api/solicitacoes', () => ({
  listSolicitacoes: listSolicitacoesMock,
  deleteSolicitacao: deleteSolicitacaoMock,
}));

vi.mock('../../../components/MeetLink', () => ({
  MeetLink: ({ href }: { href: string | null }) =>
    href ? <a href={href}>Entrar na reunião</a> : null,
}));

import MySolicitacoesPage from '../MySolicitacoesPage';
import type { Solicitacao } from '../../../types';

function renderPage() {
  return render(
    <MemoryRouter>
      <MySolicitacoesPage />
    </MemoryRouter>
  );
}

/**
 * Linha no formato REAL do SolicitacaoSerializer: `municipio`/`projeto`/`tipo_evento`
 * são FK inteiros e o nome vem nos campos planos `*_nome`. É esse contrato que a
 * tabela precisa ler (bug: as colunas liam o objeto aninhado e mostravam "-").
 */
function makeSolic(overrides: Partial<Solicitacao> = {}): Solicitacao {
  return {
    id: 1,
    usuario: 1,
    municipio: 5,
    municipio_nome: 'Juazeiro do Norte',
    projeto: 10,
    projeto_nome: 'Vidas',
    tipo_evento: 2,
    tipo_evento_nome: 'Formação',
    tipo: null,
    encontro: null,
    segmento: null,
    coordenador_acompanha: false,
    coordenador: null,
    coordenador_nome: null,
    inicio: '2026-05-10T13:00:00Z',
    fim: '2026-05-10T17:00:00Z',
    status: 'aprovado',
    observacoes: null,
    local: null,
    is_online: false,
    external_event_id: null,
    created_at: '2026-05-01T12:00:00Z',
    updated_at: '2026-05-01T12:00:00Z',
    participations: [],
    fluxo: 'NAO_SUPER',
    gcal_status: 'PENDING',
    gcal_last_sync_at: null,
    gcal_last_error: null,
    meet_link: null,
    ...overrides,
  };
}

describe('MySolicitacoesPage', () => {
  beforeEach(() => {
    listSolicitacoesMock.mockReset();
    deleteSolicitacaoMock.mockReset();
  });

  test('renderiza o título da página', async () => {
    listSolicitacoesMock.mockResolvedValueOnce({ count: 0, next: null, previous: null, results: [] });
    renderPage();
    expect(
      await screen.findByRole('heading', { name: /minhas solicitações/i })
    ).toBeInTheDocument();
  });

  // Contrato FE↔BE: as colunas Município/Projeto/Tipo exibem os campos planos
  // `municipio_nome`/`projeto_nome`/`tipo_evento_nome` do serializer, não o objeto aninhado.
  test('exibe município, projeto e tipo a partir dos campos *_nome do serializer', async () => {
    listSolicitacoesMock.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [
        makeSolic({
          id: 10,
          municipio: 5,
          municipio_nome: 'Juazeiro do Norte',
          projeto: 10,
          projeto_nome: 'Vidas',
          tipo_evento: 2,
          tipo_evento_nome: 'Formação',
        }),
      ],
    });
    renderPage();

    expect(await screen.findByText('Juazeiro do Norte')).toBeInTheDocument();
    expect(await screen.findByText('Vidas')).toBeInTheDocument();
    expect(await screen.findByText('Formação')).toBeInTheDocument();
  });

  // Seam 3 (import v15): a coluna Formadores mostra o NOME, e inclui convidados "que saíram"
  // (sem FK, nome em guest_nome). Antes o filtro `&& p.usuario` descartava esse convidado.
  test('coluna Formadores inclui convidado por guest_nome (antes descartado por não ter FK)', async () => {
    listSolicitacoesMock.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [
        makeSolic({
          id: 11,
          participations: [
            { usuario: { id: 1, username: 'jsilva', first_name: 'João', last_name: 'Silva', email: 'j@x.com' }, guest_email: null, guest_nome: null, email: 'j@x.com', role: 'FORMADOR', ch_horas: null, observacao: null },
            { usuario: null, guest_email: 'maria@x.com', guest_nome: 'Maria Ex', email: 'maria@x.com', role: 'FORMADOR', ch_horas: null, observacao: null },
          ],
        }),
      ],
    });
    renderPage();
    expect(await screen.findByText(/João Silva, Maria Ex/)).toBeInTheDocument();
  });

  // Vários coordenadores (03/11/2026): coluna Coordenador(es) = responsável + extras (COORD_ACOMPANHA).
  // A participação COORDENADOR é quem criou, não entra.
  test('coluna Coordenador(es) mostra o responsável e os extras', async () => {
    const extra = { usuario: { id: 7, username: 'beto', first_name: 'Beto', last_name: 'Extra', email: '' }, guest_email: null, guest_nome: null, email: null, role: 'COORD_ACOMPANHA' as const, ch_horas: null, observacao: null };
    const criador = { ...extra, usuario: { ...extra.usuario, id: 8, first_name: 'Quem', last_name: 'Criou' }, role: 'COORDENADOR' as const };
    listSolicitacoesMock.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [makeSolic({ id: 12, coordenador_nome: 'Rita Resp', participations: [criador, extra] })],
    });
    renderPage();
    expect(await screen.findByRole('columnheader', { name: 'Coordenador(es)' })).toBeInTheDocument();
    expect(await screen.findByText('Rita Resp, Beto Extra')).toBeInTheDocument();
    expect(screen.queryByText(/Quem Criou/)).not.toBeInTheDocument();
  });

  test('coluna Coordenador(es) sem extra mostra só o responsável', async () => {
    listSolicitacoesMock.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [makeSolic({ id: 13, coordenador_nome: 'Sol Sozinha' })],
    });
    renderPage();
    expect(await screen.findByText('Sol Sozinha')).toBeInTheDocument();
  });
});

// Teste E2E de 28/09 (#2069): o rodapé dizia "Total: 1 solicitações".
describe('MySolicitacoesPage — total da lista', { timeout: 20000 }, () => {
  beforeEach(() => {
    listSolicitacoesMock.mockReset();
  });

  test.each([
    [1, 'Total: 1 solicitação'],
    [2, 'Total: 2 solicitações'],
  ])('o total concorda com o número (%i)', async (quantos, texto) => {
    listSolicitacoesMock.mockResolvedValue({
      count: quantos,
      next: null,
      previous: null,
      results: Array.from({ length: quantos }, (_, i) => makeSolic({ id: 40 + i })),
    });
    renderPage();
    expect(await screen.findByText(texto)).toBeInTheDocument();
  });
});
