/**
 * Tela de Usuários, lote C do alinhamento (06/11/2026).
 *
 * - O login é o CPF (D14): criar não pede login (o servidor grava o CPF) e o Salvar não manda `username`;
 *   na edição, "Usuário (login)" aparece travado.
 * - E-mail de reserva (D15): chega vazio do servidor; a tela diz "Sem e-mail", o form vem vazio e o Salvar
 *   sem e-mail não o manda (o servidor mantém o gravado). `nomeDe` ignora o e-mail de reserva.
 * - Sem lotação vigente, a coluna Setor e o detalhe dizem "Sem lotação": grupo de setor não dá poder (D03).
 * - Sai a soma "Permissões efetivas" (grupos não dão poder desde o PR 12).
 * - Para quem não é superusuário, as funções sem papel na gerência ficam bloqueadas (D10).
 * - O aviso do pacote cobre a Diretoria (supervisão e painéis, sem aprovar).
 * - Textos: Função é o cargo; "E-mail"; o Redefinir senha diz o que acontece no próximo acesso.
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { message } from 'antd';

import { ComAcesso } from '../../../test/comAcesso';
import { avisoDoPacote, buildUsuarioPayload, nomeDe, type UsuarioFormValues } from '../usuario_form_helpers';

const { USUARIOS, GERENCIAS, auth } = vi.hoisted(() => ({
  auth: { superusuario: true },
  USUARIOS: [
    {
      id: 41, username: '10000012120', email: '', first_name: 'Reserva', last_name: 'Teste',
      cpf_masked: '***.***.012-120', is_active: true, is_superuser: false,
      // Só o grupo DAT, sem vínculo: não tem poder nenhum.
      groups: ['DAT'], group_ids_display: [1], gerencia_atual: null, equipe_administrativa: false,
      lotacao_reservada: false,
    },
  ],
  GERENCIAS: [
    {
      id: 9, nome: 'DIRETORIA', nome_setor: 'Diretoria', nome_exibicao: 'Diretoria', rotulo: 'Diretoria',
      setor_canonico: '', setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true,
      descricao: '', projetos_count: 0, created_at: '', updated_at: '', lotacao_reservada: true,
    },
    {
      id: 7, nome: 'GERENCIA VIDAS', nome_setor: 'Vidas', nome_exibicao: 'Vidas', rotulo: 'Vidas',
      setor_canonico: 'Vidas', setor_canonico_confianca: '', gerente: null, gerente_nome: '', ativo: true,
      descricao: '', projetos_count: 0, created_at: '', updated_at: '', lotacao_reservada: false,
    },
  ],
}));

vi.mock('../../../api/auth', () => ({
  checkAuth: vi.fn(async () => ({ authenticated: true, user: { id: 1, is_superuser: auth.superusuario } })),
}));
vi.mock('../../../api/ops', () => ({ importUsuarios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listUsers: vi.fn().mockResolvedValue({ results: USUARIOS, count: 1, next: null, previous: null }),
  getUserPolicies: vi.fn().mockResolvedValue([]),
  createUser: vi.fn().mockResolvedValue({}),
  updateUser: vi.fn().mockResolvedValue({}),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  listGroups: vi.fn().mockResolvedValue({
    results: [
      { id: 1, name: 'DAT', permissoes_funcionais: [{ id: 1, codename: 'x', label: 'Gerenciar cadastros', category: 'c' }] },
      { id: 2, name: 'Formador' },
      { id: 3, name: 'Assistente Administrativo' },
    ],
    count: 3, next: null, previous: null,
  }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: ['DAT'], funcao_groups: ['Formador', 'Assistente Administrativo'], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: GERENCIAS, count: 2, next: null, previous: null }),
}));

import { createUser, getRBACMeta, updateUser } from '../../../api/adminDAT';
import UsuariosPage from '../UsuariosPage';

function renderPage(policies: readonly string[] = ['manage_admin_registries']) {
  return render(
    <ComAcesso policies={policies}>
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    </ComAcesso>,
  );
}

async function editar(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  await user.click(await screen.findByRole('button', { name: 'Editar: Reserva Teste' }, { timeout: 15000 }));
  return screen.findByRole('dialog', {}, { timeout: 10000 });
}

const BASE: UsuarioFormValues = {
  username: '10000012120',
  email: '',
  is_active: true,
  is_superuser: false,
  funcao_ids: [],
};

describe('helpers — login e e-mail de reserva', () => {
  test('o Salvar nunca manda o login: ele nasce e muda com o CPF', () => {
    const criar = buildUsuarioPayload({ ...BASE, email: 'a@example.invalid', cpf: '10000012120' }, {
      isEditing: false, cpfEditUnlocked: true, currentIsSuperuser: true,
    });
    const editar = buildUsuarioPayload(BASE, { isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: true });
    expect(criar).not.toHaveProperty('username');
    expect(editar).not.toHaveProperty('username');
  });

  test('na edição, e-mail vazio não vai (o servidor mantém o gravado); preenchido vai', () => {
    const opcoes = { isEditing: true, cpfEditUnlocked: false, currentIsSuperuser: true };
    expect(buildUsuarioPayload(BASE, opcoes)).not.toHaveProperty('email');
    expect(buildUsuarioPayload({ ...BASE, email: 'novo@example.invalid' }, opcoes)).toMatchObject({
      email: 'novo@example.invalid',
    });
  });

  test('nomeDe ignora o e-mail de reserva', () => {
    expect(nomeDe({ email: '10000012120@placeholder.local' })).toBe('Sem nome');
    expect(nomeDe({ email: 'ana@example.invalid' })).toBe('ana@example.invalid');
  });

  test('aviso do pacote: DAT e Controle aprovam; a Diretoria supervisiona sem aprovar; as demais nada', () => {
    expect(avisoDoPacote({ nome: 'GERENCIA DAT' })).toMatch(/inclusive aprovar solicitações/);
    expect(avisoDoPacote({ nome: 'CONTROLE' })).toMatch(/inclusive aprovar solicitações/);
    expect(avisoDoPacote({ nome: 'DIRETORIA' })).toMatch(/supervisão e painéis, sem aprovar/);
    expect(avisoDoPacote({ nome: 'GERENCIA 2' })).toBeNull();
    expect(avisoDoPacote(undefined)).toBeNull();
  });
});

describe('UsuariosPage — alinhamento (lote C)', { timeout: 45000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.superusuario = true;
  });

  test('lista: sem lotação diz "Sem lotação" (o grupo DAT não aparece) e sem e-mail diz "Sem e-mail"', async () => {
    renderPage();
    const linha = (await screen.findByText('Reserva Teste', {}, { timeout: 15000 })).closest('tr') as HTMLElement;

    expect(within(linha).getByText('Sem lotação')).toBeInTheDocument();
    expect(within(linha).getByText('Sem e-mail')).toBeInTheDocument();
    expect(within(linha).queryByText('DAT')).not.toBeInTheDocument();
  });

  test('detalhe: "Sem lotação" e "Sem e-mail"', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Ver detalhes de Reserva Teste' }, { timeout: 15000 }));
    const drawer = await screen.findByRole('dialog', {}, { timeout: 10000 });

    expect(within(drawer).getByText('Sem lotação')).toBeInTheDocument();
    expect(within(drawer).getByText('Sem e-mail')).toBeInTheDocument();
  });

  test('criar não pede o login e o Salvar não o manda', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: /novo usuário/i }, { timeout: 15000 }));
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    expect(within(dialog).queryByLabelText(/usuário \(login\)/i)).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Username')).not.toBeInTheDocument();
    await user.click(within(dialog).getByLabelText('E-mail'));
    await user.paste('nova@example.invalid');
    await user.click(within(dialog).getByLabelText('CPF'));
    await user.paste('10000012120');
    await user.click(within(dialog).getByRole('combobox', { name: /gerência \(onde trabalha\)/i }));
    await user.click(await screen.findByTitle('Vidas'));
    await user.click(within(dialog).getByRole('combobox', { name: /função \(cargo\)/i }));
    await user.click(await screen.findByTitle('Formador'));
    await user.click(within(dialog).getByLabelText('Senha'));
    await user.paste('Senha-Forte-2026!');
    await user.click(within(dialog).getByRole('button', { name: /^salvar$/i }));

    await waitFor(() => expect(createUser).toHaveBeenCalled(), { timeout: 10000 });
    expect(vi.mocked(createUser).mock.calls[0]![0]).not.toHaveProperty('username');
  }, 90000); // preenche o form inteiro: na CI passa de 45 s

  test('editar: login travado, e-mail vazio sem obrigar, sem "Permissões efetivas", textos novos', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user);

    expect(within(dialog).getByLabelText('Usuário (login)')).toBeDisabled();
    expect(within(dialog).getByLabelText('E-mail')).toHaveValue('');
    expect(
      within(dialog).getByText('Gerência e papel na gerência definem o que a pessoa pode fazer. Função é só o cargo.', {
        exact: false,
      }),
    ).toBeInTheDocument();
    expect(within(dialog).queryByText(/permissões efetivas/i)).not.toBeInTheDocument();
    expect(within(dialog).queryByText('Gerenciar cadastros')).not.toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: /^salvar$/i }));
    await waitFor(() => expect(updateUser).toHaveBeenCalled(), { timeout: 10000 });
    expect(vi.mocked(updateUser).mock.calls[0]![1]).not.toHaveProperty('email');
    expect(vi.mocked(updateUser).mock.calls[0]![1]).not.toHaveProperty('username');
  });

  test('o DAT vê as funções sem papel na gerência bloqueadas (não escondidas)', async () => {
    auth.superusuario = false;
    const user = userEvent.setup();
    renderPage(['manage_admin_registries', 'manage_lotacao_comum']);
    const dialog = await editar(user);

    await user.click(within(dialog).getByRole('combobox', { name: /função \(cargo\)/i }));
    const assistente = await screen.findByTitle(/Assistente Administrativo/);
    expect(assistente.closest('.ant-select-item-option')).toHaveClass('ant-select-item-option-disabled');
    const formador = await screen.findByTitle('Formador');
    expect(formador.closest('.ant-select-item-option')).not.toHaveClass('ant-select-item-option-disabled');
  });

  test('o superusuário escolhe qualquer função', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user);

    await user.click(within(dialog).getByRole('combobox', { name: /função \(cargo\)/i }));
    const assistente = await screen.findByTitle('Assistente Administrativo');
    expect(assistente.closest('.ant-select-item-option')).not.toHaveClass('ant-select-item-option-disabled');
  });

  test('escolher a Diretoria mostra o aviso da supervisão sem aprovar', async () => {
    const user = userEvent.setup();
    renderPage();
    const dialog = await editar(user);

    await user.click(within(dialog).getByRole('combobox', { name: /gerência \(onde trabalha\)/i }));
    await user.click(await screen.findByTitle('Diretoria'));

    expect(await within(dialog).findByText(/pacote da Diretoria: supervisão e painéis, sem aprovar/)).toBeInTheDocument();
  });

  test('Redefinir senha diz que a pessoa terá de escolher a senha e verá quem redefiniu', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Redefinir senha: Reserva Teste' }, { timeout: 15000 }));
    const dialog = await screen.findByRole('dialog', {}, { timeout: 10000 });

    expect(
      within(dialog).getByText(
        'A senha nova vale na hora e destrava o login. No próximo acesso a pessoa terá de escolher a própria senha e verá que você a redefiniu.',
      ),
    ).toBeInTheDocument();
  });

  test('falha ao carregar funções e setores: mensagem clara', async () => {
    const erro = vi.spyOn(message, 'error');
    vi.mocked(getRBACMeta).mockRejectedValueOnce(new Error('500'));
    renderPage();

    await waitFor(() => expect(erro).toHaveBeenCalledWith('Não foi possível carregar as funções e setores'), {
      timeout: 15000,
    });
    erro.mockRestore();
  });
});
