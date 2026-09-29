/**
 * PR A — gestor só por vínculo (sem grupo de FUNÇÃO) usa Deslocamentos.
 *
 * A rota e o menu já liberam `isGestorPorVinculo` (AppRoutes/AppSidebar), e o backend
 * escopa por vínculo. O gate local da página (defesa em camadas) precisa concordar,
 * senão a pessoa entra pela rota e cai em "Sem permissão" sem nunca listar.
 * Usa o `computePermissions` real (sem mock) para provar a regra de ponta a ponta.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

const { getMeMock, listDeslocamentosMock, listFormadoresMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  listDeslocamentosMock: vi.fn(),
  listFormadoresMock: vi.fn(),
}));

vi.mock('../../../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../../../api/deslocamentos', () => ({
  listDeslocamentos: listDeslocamentosMock,
  listFormadoresDoSetor: listFormadoresMock,
  createDeslocamento: vi.fn(),
  updateDeslocamento: vi.fn(),
  deleteDeslocamento: vi.fn(),
}));
vi.mock('../../../components/DatImportsCentralizedBanner', () => ({ default: () => null }));

import DeslocamentosPage from '../DeslocamentosPage';

function meComVinculo(papel: string) {
  return {
    id: 1,
    username: 'gestor',
    email: 'gestor@example.invalid',
    first_name: 'Gestor',
    last_name: 'Teste',
    name: 'Gestor Teste',
    groups: [],
    setores: [],
    funcoes: [],
    gerencias: [{ id: 4, rotulo: 'Superativar', papeis: [papel] }],
    is_superuser: false,
    is_superintendencia: false,
    can_approve_super: false,
    permissions: [],
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <DeslocamentosPage />
    </MemoryRouter>,
  );
}

describe('DeslocamentosPage — gestor só por vínculo (PR A)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDeslocamentosMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    listFormadoresMock.mockResolvedValue([]);
  });

  test('vínculo COORDENADOR sem grupo: abre a página e lista', async () => {
    getMeMock.mockResolvedValue(meComVinculo('COORDENADOR'));
    renderPage();

    await waitFor(() => expect(listDeslocamentosMock).toHaveBeenCalled(), { timeout: 3000 });
    expect(screen.queryByText('Sem permissão')).not.toBeInTheDocument();
  });

  test('vínculo FORMADOR sem grupo: continua negado', async () => {
    getMeMock.mockResolvedValue(meComVinculo('FORMADOR'));
    renderPage();

    expect(await screen.findByText('Sem permissão', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(listDeslocamentosMock).not.toHaveBeenCalled();
  });
});
