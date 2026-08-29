/**
 * #1655: Form.Items sem campo correspondente no model/serializer ("dangling") — o usuário
 * digita e o valor é descartado no save. Removidos:
 *  - AcoesPage: "Área" e "Observações" (DATAcao não tem `area` nem `observacoes` plano;
 *    tem observacao_carta/contato/reuniao/entrega por etapa).
 *  - CadastrosPage: "Link da Planilha" e "Link da Plataforma" (DATCadastro não tem link_*).
 * A "Observações" da CadastrosPage FICA (DATCadastro tem `observacoes`) — guardado abaixo.
 *
 * RED no código antigo (os Form.Items existem no modal de edição).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';

const { acaoRow, cadastroRow } = vi.hoisted(() => ({
  acaoRow: {
    id: 7, municipio_nome: 'Fortaleza', municipio_uf: 'CE',
    projeto_nome: 'Sub X', tipo_acao: 'carta', prioridade: 'alta',
    status: 'em_andamento', progresso: 50,
  },
  cadastroRow: {
    id: 9, municipio_nome: 'Sobral', municipio_uf: 'CE',
    projeto_geral_nome: 'Projeto Y', status: 'em_andamento', progresso: 40,
  },
}));

vi.mock('../../../api/datModule', () => ({
  listAcoes: vi.fn().mockResolvedValue({ results: [acaoRow], count: 1, next: null, previous: null }),
  getAcao: vi.fn().mockResolvedValue({ ...acaoRow, data_carta: '2026-03-10', data_contato: null, data_reuniao: null, data_entrega: null }),
  createAcao: vi.fn(),
  updateAcao: vi.fn().mockResolvedValue({}),
  deleteAcao: vi.fn(),
  getAcoesStats: vi.fn().mockResolvedValue({}),
  listCadastros: vi.fn().mockResolvedValue({ results: [cadastroRow], count: 1, next: null, previous: null }),
  getCadastro: vi.fn().mockResolvedValue({ ...cadastroRow, data_criacao_curso: '2026-03-10' }),
  createCadastro: vi.fn(),
  updateCadastro: vi.fn().mockResolvedValue({}),
  deleteCadastro: vi.fn(),
  updateCadastroEtapa: vi.fn(),
  getCadastrosStats: vi.fn().mockResolvedValue({}),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getProjetosGeraisOptions: vi.fn().mockResolvedValue([]),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

import AcoesPage from '../AcoesPage';
import CadastrosPage from '../CadastrosPage';

describe('#1655: Form.Items dangling foram removidos', () => {
  beforeEach(() => vi.clearAllMocks());

  test(
    'AcoesPage: modal de edição não tem "Área" nem "Observações"',
    async () => {
      const user = userEvent.setup();
      render(<MemoryRouter><AcoesPage /></MemoryRouter>);
      const btn = await screen.findByLabelText('Editar ação', {}, { timeout: 15000 });
      await user.click(btn);
      const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
      expect(within(dialog).queryByLabelText('Área')).toBeNull();
      expect(within(dialog).queryByLabelText('Observações')).toBeNull();
    },
    25000,
  );

  test(
    'CadastrosPage: modal não tem "Link da Planilha"/"Link da Plataforma" (mas mantém "Observações")',
    async () => {
      const user = userEvent.setup();
      render(<MemoryRouter><CadastrosPage /></MemoryRouter>);
      const btn = await screen.findByLabelText('Editar cadastro', {}, { timeout: 15000 });
      await user.click(btn);
      const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });
      expect(within(dialog).queryByLabelText('Link da Planilha')).toBeNull();
      expect(within(dialog).queryByLabelText('Link da Plataforma')).toBeNull();
      // guarda: a Observações válida NÃO pode ser removida
      expect(within(dialog).queryByLabelText('Observações')).not.toBeNull();
    },
    25000,
  );
});
