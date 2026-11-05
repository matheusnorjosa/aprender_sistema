/**
 * Grupo é etiqueta (PR 12, RBAC_FONTE=lotacao): pôr alguém num grupo não dá acesso.
 *
 * A tela de Setores, Funções e Grupos avisa isso no topo e não chama de "Permissões de acesso"
 * as capacidades guardadas no grupo: elas só valeriam na volta de emergência (modo `uniao`).
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { clicarNaLinha } from '../../../test/clicarNaLinha';

const { GRUPO } = vi.hoisted(() => ({
  GRUPO: {
    id: 9761,
    name: 'Setor Fictício da Serra',
    group_type: 'setor',
    user_count: 1,
    permissoes_funcionais: [{ id: 801, codename: 'operate_preagenda', label: 'Operar pré-agenda', category: 'operacao' }],
  },
}));

vi.mock('../../../api/auth', () => ({ checkAuth: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listGroups: vi.fn(),
  listUsers: vi.fn(),
  listPermissoesFuncionais: vi.fn(),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: [] }),
  getGroup: vi.fn(),
  createGroup: vi.fn(),
  updateGroup: vi.fn(),
  deleteGroup: vi.fn(),
  syncGroupMembers: vi.fn(),
}));

import { checkAuth } from '../../../api/auth';
import { getGroup, listGroups, listPermissoesFuncionais, listUsers } from '../../../api/adminDAT';
import GruposPage from '../GruposPage';

const AVISO = 'Grupo é etiqueta: colocar alguém num grupo não dá acesso. O acesso vem do vínculo com a gerência.';

function renderPage(forcedType?: 'setor' | 'funcao'): void {
  render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <GruposPage forcedType={forcedType} />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

describe('GruposPage: grupo é etiqueta, não poder', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: true } } as never);
    vi.mocked(listGroups).mockResolvedValue({ results: [GRUPO], count: 1, next: null, previous: null } as never);
    vi.mocked(listUsers).mockResolvedValue({ results: [], count: 0, next: null, previous: null });
    vi.mocked(listPermissoesFuncionais).mockResolvedValue({ results: [] } as never);
    vi.mocked(getGroup).mockResolvedValue(GRUPO as never);
  });

  test('o aviso fixo diz que grupo é etiqueta, também para quem não é superusuário', async () => {
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: false } } as never);
    renderPage('setor');

    expect(await screen.findByText(AVISO)).toBeInTheDocument();
  });

  test('a coluna mostra "Capacidades guardadas (não valem hoje)", não "Permissões funcionais"', async () => {
    renderPage('setor');
    await screen.findByText(GRUPO.name, {}, { timeout: 15000 });

    const cabecalhos = screen.getAllByRole('columnheader').map((th) => th.textContent?.trim() ?? '');
    expect(cabecalhos).toContain('Capacidades guardadas (não valem hoje)');
    expect(cabecalhos).not.toContain('Permissões funcionais');
  });

  test('setor: o modal de editar não tem "Permissões de acesso" e rotula as capacidades guardadas', async () => {
    const user = userEvent.setup();
    renderPage('setor');

    await clicarNaLinha(user, GRUPO.name, `Editar: ${GRUPO.name}`);
    const modal = (await screen.findByText('Editar Setor', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]')!;

    expect(await within(modal).findByText('Operar pré-agenda')).toBeInTheDocument();
    expect(within(modal).queryByText(/Permissões de acesso/)).not.toBeInTheDocument();
    expect(within(modal).queryByText(/Permissões do grupo/)).not.toBeInTheDocument();
    expect(
      within(modal).getByText('Capacidades guardadas (não valem hoje: o acesso vem da lotação)'),
    ).toBeInTheDocument();
  });

  test('função: o modal também não tem "Permissões de acesso da Função"', async () => {
    vi.mocked(listGroups).mockResolvedValue({
      results: [{ ...GRUPO, group_type: 'funcao' }],
      count: 1,
      next: null,
      previous: null,
    } as never);
    vi.mocked(getGroup).mockResolvedValue({ ...GRUPO, group_type: 'funcao' } as never);
    const user = userEvent.setup();
    renderPage('funcao');

    await clicarNaLinha(user, GRUPO.name, `Editar: ${GRUPO.name}`);
    const modal = (await screen.findByText('Editar Função', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]')!;

    expect(within(modal).queryByText(/Permissões de acesso/)).not.toBeInTheDocument();
  });

  test('Grupos: o tipo Função diz que é cargo e não dá acesso', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole('button', { name: /Novo Grupo/ }, { timeout: 10000 }));
    const modal = (await screen.findByText('Novo Grupo', { selector: '.ant-modal-title' })).closest<HTMLElement>(
      '[role="dialog"]',
    )!;
    await user.click(within(modal).getByRole('combobox', { name: /Tipo do Grupo/ }));

    expect(await screen.findByText('Função (cargo da pessoa; não dá acesso)')).toBeInTheDocument();
    expect(screen.queryByText('Função (o que o usuário pode fazer)')).not.toBeInTheDocument();
  });
});
