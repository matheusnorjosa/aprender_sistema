/**
 * #1912 (frontend): DATRegistro/DATCadastro/DATAcao têm `ano` no model, dentro de uma
 * UniqueConstraint com nulls_distinct=False. Sem o campo no form de create, o registro nasce
 * com ano=NULL e o 2o do mesmo município+projeto colide (400). O backend (#1925) expõe `ano`
 * gravável; este teste trava o lado frontend: o modal de criação tem um input "Ano" já
 * preenchido com o ano corrente (nunca NULL).
 *
 * RED no código antigo (sem input "Ano" no create).
 */
import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import type { ComponentType } from 'react';

const { empty } = vi.hoisted(() => ({
  empty: { results: [], count: 0, next: null, previous: null },
}));

vi.mock('../../../api/datModule', () => ({
  // DATRegistros
  listDATRegistros: vi.fn().mockResolvedValue(empty),
  createDATRegistro: vi.fn().mockResolvedValue({}),
  updateDATRegistro: vi.fn().mockResolvedValue({}),
  deleteDATRegistro: vi.fn().mockResolvedValue({}),
  exportDATRegistros: vi.fn(),
  // Cadastros
  listCadastros: vi.fn().mockResolvedValue(empty),
  getCadastro: vi.fn().mockResolvedValue({}),
  createCadastro: vi.fn().mockResolvedValue({}),
  updateCadastro: vi.fn().mockResolvedValue({}),
  deleteCadastro: vi.fn().mockResolvedValue({}),
  updateCadastroEtapa: vi.fn(),
  getCadastrosStats: vi.fn().mockResolvedValue({}),
  // Acoes
  listAcoes: vi.fn().mockResolvedValue(empty),
  getAcao: vi.fn().mockResolvedValue({}),
  createAcao: vi.fn().mockResolvedValue({}),
  updateAcao: vi.fn().mockResolvedValue({}),
  deleteAcao: vi.fn().mockResolvedValue({}),
  getAcoesStats: vi.fn().mockResolvedValue({}),
  // Options (compartilhados)
  getProjetosGeraisOptions: vi.fn().mockResolvedValue([]),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getCoordenadoresOptions: vi.fn().mockResolvedValue([]),
}));

import DATRegistrosPage from '../DATRegistrosPage';
import CadastrosPage from '../CadastrosPage';
import AcoesPage from '../AcoesPage';

const CURRENT_YEAR = new Date().getFullYear();

const CASES: Array<[string, ComponentType, RegExp]> = [
  ['DATRegistros', DATRegistrosPage, /novo registro/i],
  ['Cadastros', CadastrosPage, /novo cadastro/i],
  ['Acoes', AcoesPage, /nova ação/i],
];

describe('#1912-FE: form de criação tem input "Ano" (default = ano corrente)', () => {
  beforeEach(() => vi.clearAllMocks());

  test.each(CASES)(
    '%s: o modal de criação tem "Ano" preenchido com o ano corrente',
    async (_name, Page, btnName) => {
      const user = userEvent.setup();
      render(
        <MemoryRouter>
          <Page />
        </MemoryRouter>,
      );
      await user.click(await screen.findByRole('button', { name: btnName }, { timeout: 15000 }));
      const anoInput = await screen.findByLabelText('Ano', {}, { timeout: 10000 });
      expect(anoInput).toHaveValue(String(CURRENT_YEAR));
    },
    25000,
  );
});
