/**
 * PR2 (#1830): a página de Formações expõe o `ano` do plano.
 * O plano é anual (NK (municipio, projeto, ano)); a coluna "Ano" mostra o ano do registro.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

vi.mock('../../../api/datModule', () => ({
  listPlanoFormacoes: vi.fn().mockResolvedValue({
    results: [
      {
        id: 1,
        municipio: 1,
        municipio_nome: 'Municipio Teste',
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
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../../api/availability', () => ({
  getMe: vi.fn().mockResolvedValue({
    is_superuser: true,
    is_superintendencia: true,
    setores: [],
    funcoes: [],
  }),
}));

import PlanoFormacoesPage from '../PlanoFormacoesPage';

describe('#1830: página de Formações expõe o ano', () => {
  beforeEach(() => vi.clearAllMocks());

  test(
    'renderiza o ano do plano (2026) na tabela',
    async () => {
      render(
        <MemoryRouter>
          <PlanoFormacoesPage />
        </MemoryRouter>,
      );
      // A coluna "Ano" mostra o valor do registro (findByText p/ conteúdo de tabela AntD).
      expect(await screen.findByText('2026', {}, { timeout: 15000 })).toBeTruthy();
    },
    20000,
  );
});
