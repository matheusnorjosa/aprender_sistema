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
    usuario_username: 'formador1',
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
    coordenador_username: null,
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
});
