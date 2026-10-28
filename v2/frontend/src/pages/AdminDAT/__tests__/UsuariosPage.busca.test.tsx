/**
 * Usuários — a busca filtra enquanto se digita (ensaio r3, 28/10/2026), como Minhas Solicitações:
 * espera a pessoa parar de digitar (350 ms), Enter ou a lupa buscam na hora, e só a resposta da
 * carga mais recente entra na lista. Antes, só Enter ou a lupa filtravam.
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

vi.setConfig({ testTimeout: 20_000 });

vi.mock('../../../api/auth', () => ({
  checkAuth: vi.fn().mockResolvedValue({ authenticated: true, user: { is_superuser: true } }),
}));
vi.mock('../../../api/ops', () => ({ importUsuarios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  listGroups: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: [], funcao_groups: [], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

import { listUsers } from '../../../api/adminDAT';
import UsuariosPage from '../UsuariosPage';

function usuario(id: number, first_name: string, last_name: string) {
  return {
    id,
    username: `user${id}`,
    email: `user${id}@example.invalid`,
    first_name,
    last_name,
    cpf_masked: null,
    is_active: true,
    is_staff: false,
    is_superuser: false,
    groups: [],
    group_ids_display: [],
    gerencia_atual: null,
    date_joined: '2026-03-02T12:00:00Z',
    last_login: null,
  };
}

function pagina(itens: ReturnType<typeof usuario>[]) {
  return { results: itens, count: itens.length, next: null, previous: null };
}

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

function campoDeBusca(): HTMLElement {
  return screen.getByRole('searchbox', { name: 'Buscar usuários por nome, e-mail ou CPF' });
}

/** Enter inteiro (o input do AntD ignora um segundo Enter até a tecla subir). */
function pressionarEnter(): void {
  fireEvent.keyDown(campoDeBusca(), { key: 'Enter', code: 'Enter', keyCode: 13 });
  fireEvent.keyUp(campoDeBusca(), { key: 'Enter', code: 'Enter', keyCode: 13 });
}

function buscasFeitas(): unknown[] {
  return vi.mocked(listUsers).mock.calls.map(([params]) => (params as Record<string, unknown>)['search']);
}

describe('UsuariosPage — busca enquanto se digita', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listUsers).mockResolvedValue(pagina([usuario(1, 'Maria', 'Nova')]));
  });

  test('filtra depois que a pessoa para de digitar, sem Enter, e volta à página 1', async () => {
    renderPage();
    await screen.findByRole('button', { name: 'Ver detalhes de Maria Nova' }, { timeout: 15000 });

    fireEvent.change(campoDeBusca(), { target: { value: 'mar' } });
    // Ainda digitando: nada vai ao servidor a cada tecla.
    expect(buscasFeitas()).not.toContain('mar');

    await waitFor(() =>
      expect(listUsers).toHaveBeenLastCalledWith(expect.objectContaining({ search: 'mar', page: 1 })),
    );
  });

  test('Enter busca na hora, sem esperar', async () => {
    renderPage();
    await screen.findByRole('button', { name: 'Ver detalhes de Maria Nova' }, { timeout: 15000 });

    fireEvent.change(campoDeBusca(), { target: { value: 'maria' } });
    pressionarEnter();

    expect(listUsers).toHaveBeenLastCalledWith(expect.objectContaining({ search: 'maria', page: 1 }));
  });

  test('só a resposta da busca mais recente entra na lista', async () => {
    let responderAntiga: (valor: ReturnType<typeof pagina>) => void = () => undefined;
    renderPage();
    await screen.findByRole('button', { name: 'Ver detalhes de Maria Nova' }, { timeout: 15000 });

    // A busca "an" demora; a "maria" responde antes.
    vi.mocked(listUsers).mockImplementation(((params: Record<string, unknown>) => {
      if (params['search'] === 'an') return new Promise((resolver) => { responderAntiga = resolver; });
      if (params['search'] === 'maria') return Promise.resolve(pagina([usuario(2, 'Maria', 'Recente')]));
      return Promise.resolve(pagina([usuario(1, 'Maria', 'Nova')]));
    }) as never);
    fireEvent.change(campoDeBusca(), { target: { value: 'an' } });
    pressionarEnter();

    fireEvent.change(campoDeBusca(), { target: { value: 'maria' } });
    pressionarEnter();
    expect(await screen.findByRole('button', { name: 'Ver detalhes de Maria Recente' })).toBeInTheDocument();

    await act(async () => {
      responderAntiga(pagina([usuario(3, 'Ana', 'Antiga')]));
    });
    expect(screen.queryByRole('button', { name: 'Ver detalhes de Ana Antiga' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ver detalhes de Maria Recente' })).toBeInTheDocument();
  });
});
