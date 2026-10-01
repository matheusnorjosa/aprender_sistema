/**
 * Auditoria UX 30/09 (ALTA): no Plano Anual, lista e estatísticas saíam juntas e o erro
 * das estatísticas derrubava a lista (tabela vazia + toast). Agora a lista continua e as
 * estatísticas mostram um aviso com o motivo.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

const { getPlanoFormacoesStatsMock } = vi.hoisted(() => ({ getPlanoFormacoesStatsMock: vi.fn() }));

vi.mock('../../../api/datModule', () => ({
  listPlanoFormacoes: vi.fn().mockResolvedValue({
    results: [
      {
        id: 1,
        municipio: 1,
        municipio_nome: 'Municipio do Controle',
        municipio_uf: 'CE',
        projeto: 1,
        projeto_nome: 'Projeto Teste',
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
  createPlanoFormacoes: vi.fn(),
  updatePlanoFormacoes: vi.fn(),
  deletePlanoFormacoes: vi.fn(),
  getPlanoFormacoesStats: getPlanoFormacoesStatsMock,
  updateFormacaoInline: vi.fn(),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../../api/availability', () => ({
  getMe: vi.fn().mockResolvedValue({ is_superuser: false, is_superintendencia: false, setores: ['Controle'], funcoes: [] }),
}));

import PlanoFormacoesPage from '../PlanoFormacoesPage';

describe('Plano Anual: erro das estatísticas não derruba a lista', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getPlanoFormacoesStatsMock.mockRejectedValue(new Error('Você não tem permissão para executar essa ação.'));
  });

  test(
    'a lista aparece e as estatísticas mostram o motivo do erro',
    async () => {
      render(
        <MemoryRouter>
          <PlanoFormacoesPage />
        </MemoryRouter>,
      );

      expect(await screen.findByText('Municipio do Controle', {}, { timeout: 15000 })).toBeTruthy();
      const aviso = await screen.findByRole('alert');
      expect(aviso).toHaveTextContent('Não foi possível carregar as estatísticas');
      expect(aviso).toHaveTextContent('Você não tem permissão para executar essa ação.');
    },
    20000,
  );

  // Rodada 2 (BAIXA): o aviso oferece "Tentar de novo" ali mesmo.
  test(
    '"Tentar de novo" no aviso busca as estatísticas outra vez',
    async () => {
      render(
        <MemoryRouter>
          <PlanoFormacoesPage />
        </MemoryRouter>,
      );

      const titulo = await screen.findByText('Não foi possível carregar as estatísticas', {}, { timeout: 15000 });
      const aviso = titulo.closest<HTMLElement>('[role="alert"]');
      expect(aviso).not.toBeNull();
      const chamadasAntes = getPlanoFormacoesStatsMock.mock.calls.length;

      fireEvent.click(within(aviso as HTMLElement).getByRole('button', { name: 'Tentar de novo' }));

      await waitFor(() => expect(getPlanoFormacoesStatsMock.mock.calls.length).toBe(chamadasAntes + 1));
    },
    20000,
  );
});
