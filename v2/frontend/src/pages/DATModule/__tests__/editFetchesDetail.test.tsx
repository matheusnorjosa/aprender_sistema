/**
 * M17-02: editar pelo modal apagava as datas em silêncio, porque o form era alimentado com
 * a LINHA DA LISTA (serializer de lista não expõe as datas) e o PATCH reenviava `data_*: null`.
 *
 * O fix: `handleEdit` busca o DETAIL (getAcao/getCadastro) antes de abrir o modal. Este teste
 * trava exatamente isso — clicar em Editar dispara a busca do detail. RED no código antigo
 * (handleEdit usava o record da lista e nunca chamava getAcao/getCadastro).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

// vi.hoisted: o factory do vi.mock é içado pro topo; as fixtures precisam ser içadas junto.
const { acaoRow, cadastroRow } = vi.hoisted(() => ({
  acaoRow: {
    id: 7,
    municipio_nome: 'Fortaleza',
    municipio_uf: 'CE',
    projeto_geral_nome: 'Projeto X',
    projeto_nome: 'Sub X',
    tipo_acao: 'carta',
    prioridade: 'alta',
    status: 'em_andamento',
    progresso: 50,
    observacoes: 'obs',
  },
  cadastroRow: {
    id: 9,
    municipio_nome: 'Sobral',
    municipio_uf: 'CE',
    projeto_geral_nome: 'Projeto Y',
    status: 'em_andamento',
    progresso: 40,
  },
}));

vi.mock('../../../api/datModule', () => ({
  listAcoes: vi.fn().mockResolvedValue({ results: [acaoRow], count: 1, next: null, previous: null }),
  getAcao: vi.fn().mockResolvedValue({
    ...acaoRow,
    data_carta: '2026-03-10',
    data_contato: null,
    data_reuniao: null,
    data_entrega: null,
  }),
  createAcao: vi.fn(),
  updateAcao: vi.fn().mockResolvedValue({}),
  deleteAcao: vi.fn(),
  getAcoesStats: vi.fn().mockResolvedValue({}),
  listCadastros: vi.fn().mockResolvedValue({ results: [cadastroRow], count: 1, next: null, previous: null }),
  getCadastro: vi.fn().mockResolvedValue({
    ...cadastroRow,
    data_criacao_curso: '2026-03-10',
    data_chaves: null,
    data_instrucoes: null,
    data_envio: null,
    data_recebidos: null,
    data_validados: null,
    data_importados: null,
  }),
  createCadastro: vi.fn(),
  updateCadastro: vi.fn().mockResolvedValue({}),
  deleteCadastro: vi.fn(),
  updateCadastroEtapa: vi.fn(),
  getCadastrosStats: vi.fn().mockResolvedValue({}),
  getMunicipiosOptions: vi.fn().mockResolvedValue({ results: [] }),
  getProjetosOptions: vi.fn().mockResolvedValue({ results: [] }),
  getProjetosGeraisOptions: vi.fn().mockResolvedValue({ results: [] }),
  getCoordenadoresOptions: vi.fn().mockResolvedValue({ results: [] }),
}));

import AcoesPage from '../AcoesPage';
import CadastrosPage from '../CadastrosPage';
import { getAcao, getCadastro } from '../../../api/datModule';

describe('M17-02: editar busca o DETAIL antes de abrir o modal', () => {
  beforeEach(() => vi.clearAllMocks());

  // Timeouts folgados: renderizar a pagina inteira (Table + useTableFilters + options) em
  // jsdom sob carga do CI passa dos 5s default e estoura flaky. O comportamento testado
  // (handleEdit busca o detail) e' rapido; o que e' lento e' o render — dai a margem.
  test(
    'AcoesPage: clicar em Editar dispara getAcao(id) (não usa a linha da lista)',
    async () => {
      render(
        <MemoryRouter>
          <AcoesPage />
        </MemoryRouter>,
      );
      const btn = await screen.findByLabelText('Editar ação', {}, { timeout: 15000 });
      await userEvent.click(btn);
      await waitFor(() => expect(getAcao).toHaveBeenCalledWith(7), { timeout: 10000 });
    },
    20000,
  );

  test(
    'CadastrosPage: clicar em Editar dispara getCadastro(id)',
    async () => {
      render(
        <MemoryRouter>
          <CadastrosPage />
        </MemoryRouter>,
      );
      const btn = await screen.findByLabelText('Editar cadastro', {}, { timeout: 15000 });
      await userEvent.click(btn);
      await waitFor(() => expect(getCadastro).toHaveBeenCalledWith(9), { timeout: 10000 });
    },
    20000,
  );
});
