import { render, screen, waitFor } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import ControlePage from '../Controle/ControlePage';
import ComprasPage from '../DATModule/ComprasPage';
import Disponibilidade from '../Disponibilidade';
import DeslocamentosPage from '../Deslocamentos/DeslocamentosPage';
import { getMe, getBlocks } from '../../api/availability';
import { listCompras as listControleCompras } from '../../api/ops';
import {
  getMunicipiosOptions,
  getProdutosOptions,
  getProjetosOptions,
  listCompras as listDatCompras,
} from '../../api/datModule';
import { DAT_IMPORTS_CENTRALIZED_MESSAGE } from '../../components/DatImportsCentralizedBanner';
import type { CurrentUser } from '../../types';

vi.mock('../../components/BlockForm', () => ({
  default: () => <div>Criar Bloqueio Form</div>,
}));

vi.mock('../../components/MyBlocksTable', () => ({
  default: () => <div>Meus Bloqueios Table</div>,
}));

vi.mock('../../api/availability', () => ({
  getMe: vi.fn(),
  getBlocks: vi.fn(),
  createBlock: vi.fn(),
  deleteBlock: vi.fn(),
}));

vi.mock('../../api/ops', () => ({
  listCompras: vi.fn(),
}));

vi.mock('../../api/datModule', () => ({
  listCompras: vi.fn(),
  createCompra: vi.fn(),
  updateCompra: vi.fn(),
  deleteCompra: vi.fn(),
  getMunicipiosOptions: vi.fn(),
  getProjetosOptions: vi.fn(),
  getProdutosOptions: vi.fn(),
}));

const controleUser: CurrentUser = {
  id: 1,
  username: 'controle',
  email: 'controle@example.com',
  first_name: 'Controle',
  last_name: 'User',
  name: 'Controle User',
  groups: ['Controle'],
  setores: ['Controle'],
  funcoes: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

function renderPage(ui: ReactElement): void {
  render(<MemoryRouter>{ui}</MemoryRouter>);
}

function expectLegacyImportsRemoved(): void {
  expect(screen.queryByText(/Importar COMPRAS/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Importar AÇÕES/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Importar EVENTOS/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Importar PRODUTOS/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Importar Bloqueios/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Importar Deslocamentos/i)).not.toBeInTheDocument();
}

describe('DAT Imports PR-D — remoção de entrypoints legados', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(getMe).mockResolvedValue(controleUser);
    vi.mocked(getBlocks).mockResolvedValue([]);
    vi.mocked(listControleCompras).mockResolvedValue([]);
    vi.mocked(listDatCompras).mockResolvedValue({ results: [], count: 0 });
    vi.mocked(getMunicipiosOptions).mockResolvedValue([]);
    vi.mocked(getProjetosOptions).mockResolvedValue([]);
    vi.mocked(getProdutosOptions).mockResolvedValue([]);

    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.startsWith('/api/deslocamentos/')) {
        return {
          ok: true,
          json: async () => ({ results: [], count: 0 }),
        };
      }

      if (url.startsWith('/api/options/formadores-do-setor/')) {
        return {
          ok: true,
          json: async () => [],
        };
      }

      return {
        ok: false,
        statusText: 'Not mocked',
        json: async () => ({}),
      };
    }));
  });

  test('ControlePage remove cards de importação, exibe banner e mantém filtros/listagem', async () => {
    renderPage(<ControlePage />);

    expect(screen.getByRole('heading', { level: 1, name: 'Controle' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Filtros de COMPRAS/i })).toBeInTheDocument();
    expect(await screen.findByLabelText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).toBeInTheDocument();
    expectLegacyImportsRemoved();
    expect(screen.queryByRole('link', { name: 'DAT > Importações' })).not.toBeInTheDocument();
  });

  test('ComprasPage remove modo Importar e mantém fluxo principal de compras', async () => {
    renderPage(<ComprasPage />);

    expect(screen.getByRole('heading', { name: /Gestão de Compras\/Materiais/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Nova Compra/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Exportar/i })).toBeInTheDocument();
    expect(await screen.findByLabelText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).toBeInTheDocument();
    expectLegacyImportsRemoved();
    expect(screen.queryByRole('button', { name: /^Importar$/i })).not.toBeInTheDocument();
  });

  test('Disponibilidade remove Importar bloqueios e mantém criação/listagem', async () => {
    renderPage(<Disponibilidade />);

    expect(screen.getByRole('heading', { name: /Gerenciar Disponibilidade/i })).toBeInTheDocument();
    expect(screen.getByText('Criar Bloqueio')).toBeInTheDocument();
    expect(screen.getByText('Meus Bloqueios')).toBeInTheDocument();
    expect(await screen.findByLabelText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).toBeInTheDocument();
    expectLegacyImportsRemoved();
    expect(screen.queryByRole('button', { name: /^Importar$/i })).not.toBeInTheDocument();
  });

  test('DeslocamentosPage remove Importar deslocamentos e mantém filtros/tabela', async () => {
    renderPage(<DeslocamentosPage />);

    expect(await screen.findByRole('heading', { name: /Deslocamentos/i })).toBeInTheDocument();
    expect(screen.getByText('Filtros')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Novo Deslocamento/i })).toBeInTheDocument();
    expect(await screen.findByLabelText(DAT_IMPORTS_CENTRALIZED_MESSAGE)).toBeInTheDocument();
    expectLegacyImportsRemoved();
    expect(screen.queryByRole('button', { name: /^Importar$/i })).not.toBeInTheDocument();

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        expect.stringMatching(/^\/api\/deslocamentos\/\?/),
        expect.objectContaining({ credentials: 'include' }),
      );
    });
  });
});
