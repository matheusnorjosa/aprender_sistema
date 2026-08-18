/**
 * #1740 (H2): o botao Excluir do Plano de Formacoes so pode aparecer para quem pode
 * executar a operacao restrita — o backend exige `execute_restricted_operations` no
 * destroy (superuser OU Superintendencia) e agora tambem bloqueia (409) a exclusao de
 * planos com formacoes concluidas. Antes o botao era renderizado incondicionalmente,
 * garantindo 403 para nao-Superintendencia.
 *
 * RED no codigo antigo: o botao Excluir aparecia para qualquer usuario.
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

vi.mock('../../../api/datModule', () => ({
  // Registro inline: a factory do vi.mock e' icada ao topo, entao nao pode referenciar
  // variaveis de nivel de modulo (TDZ).
  listPlanoFormacoes: vi.fn().mockResolvedValue({
    results: [
      {
        id: 1,
        municipio: 1,
        municipio_nome: 'Municipio Teste',
        municipio_uf: 'CE',
        projeto: 1,
        projeto_nome: 'Projeto Teste',
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
  getMunicipiosOptions: vi.fn().mockResolvedValue({ results: [] }),
  getProjetosOptions: vi.fn().mockResolvedValue({ results: [] }),
  getCoordenadoresOptions: vi.fn().mockResolvedValue({ results: [] }),
}));

vi.mock('../../../api/availability', () => ({ getMe: vi.fn() }));

import { getMe } from '../../../api/availability';
import PlanoFormacoesPage from '../PlanoFormacoesPage';

describe('#1740: botao Excluir do Plano so aparece para operacao restrita', () => {
  beforeEach(() => vi.clearAllMocks());

  // Timeouts folgados: renderizar a pagina inteira (Table + filtros + options) em jsdom
  // e lento; o comportamento testado (visibilidade do botao) e rapido.
  test(
    'Superintendencia ve o botao Excluir',
    async () => {
      vi.mocked(getMe).mockResolvedValue({
        is_superuser: false,
        is_superintendencia: true,
        setores: ['Superintendência'],
        funcoes: ['Gerente'],
      } as never);

      render(
        <MemoryRouter>
          <PlanoFormacoesPage />
        </MemoryRouter>,
      );

      const btn = await screen.findByRole('button', { name: /Excluir plano/i }, { timeout: 15000 });
      expect(btn).toBeTruthy();
    },
    20000,
  );

  test(
    'Coordenador (sem operacao restrita) NAO ve o botao Excluir',
    async () => {
      vi.mocked(getMe).mockResolvedValue({
        is_superuser: false,
        is_superintendencia: false,
        setores: ['DAT'],
        funcoes: ['Coordenador'],
      } as never);

      render(
        <MemoryRouter>
          <PlanoFormacoesPage />
        </MemoryRouter>,
      );

      // A linha renderiza (o botao Editar aparece sempre); o Excluir deve estar ausente.
      await screen.findByRole('button', { name: /Editar plano/i }, { timeout: 15000 });
      expect(screen.queryByRole('button', { name: /Excluir plano/i })).toBeNull();
    },
    20000,
  );
});
