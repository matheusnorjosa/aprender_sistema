/**
 * D4 do ADR-020 (PR A da arquitetura de permissões): o que um grupo pode muda só por PR.
 *
 * O modal de Grupos mostra as permissões do grupo só para leitura, com o aviso "Definido no
 * sistema", e o Salvar (criar ou editar) não manda mais `permissao_funcional_ids`.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { clicarNaLinha } from '../../../test/clicarNaLinha';

const { GRUPO, CAPACIDADE, OUTRA } = vi.hoisted(() => {
  const capacidade = {
    id: 701,
    codename: 'operate_preagenda',
    label: 'Operar pré-agenda e relatórios',
    description: 'Pré-agenda, relatórios gerenciais e publicações operacionais.',
    category: 'operacao',
    is_system: true,
  };
  return {
    CAPACIDADE: capacidade,
    OUTRA: {
      id: 702,
      codename: 'approve_solicitation',
      label: 'Aprovar solicitações',
      description: 'Aprovar ou reprovar solicitações pendentes.',
      category: 'solicitacao',
      is_system: true,
    },
    GRUPO: {
      id: 9742,
      name: 'Setor Fictício do Sertão',
      group_type: 'setor',
      user_count: 0,
      permissoes_funcionais: [
        { id: capacidade.id, codename: capacidade.codename, label: capacidade.label, category: capacidade.category },
      ],
    },
  };
});

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
import {
  createGroup,
  getGroup,
  listGroups,
  listPermissoesFuncionais,
  listUsers,
  syncGroupMembers,
  updateGroup,
} from '../../../api/adminDAT';
import GruposPage from '../GruposPage';

function renderPage(): void {
  render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <GruposPage forcedType="setor" />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

describe('GruposPage: permissões do grupo só leitura (D4)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: true } } as never);
    vi.mocked(listGroups).mockReset().mockResolvedValue({ results: [GRUPO], count: 1, next: null, previous: null } as never);
    vi.mocked(listUsers).mockReset().mockResolvedValue({ results: [], count: 0, next: null, previous: null });
    vi.mocked(listPermissoesFuncionais).mockResolvedValue({ results: [CAPACIDADE, OUTRA] } as never);
    vi.mocked(getGroup).mockResolvedValue(GRUPO as never);
    vi.mocked(updateGroup).mockResolvedValue(GRUPO as never);
    vi.mocked(createGroup).mockResolvedValue({ ...GRUPO, id: 9743 } as never);
    vi.mocked(syncGroupMembers).mockResolvedValue({ added: 0, removed: 0, members_count: 0 } as never);
  });

  test('editar mostra as permissões do grupo sem caixa de marcar e diz que vêm do sistema', async () => {
    const user = userEvent.setup();
    renderPage();

    await clicarNaLinha(user, GRUPO.name, `Editar: ${GRUPO.name}`);
    const modal = (await screen.findByText('Editar Setor', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]')!;

    expect(await within(modal).findByText(CAPACIDADE.label)).toBeInTheDocument();
    expect(within(modal).queryByText(OUTRA.label)).not.toBeInTheDocument();
    expect(within(modal).queryAllByRole('checkbox')).toHaveLength(0);
    expect(within(modal).getByText(/Definido no sistema/)).toBeInTheDocument();
  }, 40000);

  test('o Salvar da edição não manda permissao_funcional_ids', async () => {
    const user = userEvent.setup();
    renderPage();

    await clicarNaLinha(user, GRUPO.name, `Editar: ${GRUPO.name}`);
    const modal = (await screen.findByText('Editar Setor', {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]')!;
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(updateGroup).toHaveBeenCalledTimes(1));
    expect(vi.mocked(updateGroup).mock.calls[0][1]).not.toHaveProperty('permissao_funcional_ids');
  }, 40000);

  test('o Salvar da criação não manda permissao_funcional_ids', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole('button', { name: /Novo Setor/ }, { timeout: 10000 }));
    const modal = (await screen.findByText('Novo Setor', { selector: '.ant-modal-title' })).closest<HTMLElement>(
      '[role="dialog"]',
    )!;
    await user.type(within(modal).getByRole('textbox', { name: /Nome/ }), 'Setor Novo Fictício');
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(createGroup).toHaveBeenCalledTimes(1));
    expect(vi.mocked(createGroup).mock.calls[0][0]).not.toHaveProperty('permissao_funcional_ids');
  }, 40000);
});
