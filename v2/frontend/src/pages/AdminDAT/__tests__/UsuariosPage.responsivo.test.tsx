/**
 * C1 (Programa C) — Usuários sem rolagem horizontal: lista enxuta + detalhe por assunto.
 *
 * Nunca na grade: ID, CPF, username (em produção o username É o CPF), telefone e cargo.
 * Eles ficam no detalhe (Drawer com Dados pessoais · Lotação · Acesso), aberto pelo nome.
 * A 360 px a linha mostra identidade, situação e o menu de ações; o resto vai para a
 * linha expandida do ResponsiveTable.
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

const { USUARIOS } = vi.hoisted(() => ({
  USUARIOS: [
    {
      id: 42,
      username: '12345678901', // em produção o login é o CPF
      email: 'maria.aparecida@example.invalid',
      first_name: 'Maria Aparecida',
      last_name: 'da Conceição',
      cpf_masked: '***.***.678-01',
      telefone: '85988887777',
      cargo: 'Coordenadora Pedagógica Regional',
      is_active: true,
      is_superuser: false,
      groups: ['Vidas', 'Coordenador'],
      group_ids_display: [1, 2],
      gerencia_atual: { gerencia_id: 4, rotulo: 'Superativar', nome_setor: 'ACerta', setor_canonico: 'Superativar', papel: 'COORDENADOR' },
      date_joined: '2026-03-02T12:00:00Z',
      last_login: '2026-09-29T13:30:00Z',
    },
  ],
}));

vi.mock('../../../api/auth', () => ({
  checkAuth: vi.fn().mockResolvedValue({ authenticated: true, user: { is_superuser: true } }),
}));
vi.mock('../../../api/ops', () => ({ importUsuarios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listUsers: vi.fn().mockResolvedValue({ results: USUARIOS, count: 1, next: null, previous: null }),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  listGroups: vi.fn().mockResolvedValue({
    results: [{ id: 1, name: 'Vidas' }, { id: 2, name: 'Coordenador' }], count: 2, next: null, previous: null,
  }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: ['Vidas'], funcao_groups: ['Coordenador'], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

import UsuariosPage from '../UsuariosPage';

const NOME = 'Maria Aparecida da Conceição';
/** O que nunca pode aparecer na grade. */
const SO_NO_DETALHE = ['12345678901', '***.***.678-01', '85988887777', 'Coordenadora Pedagógica Regional'];

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <UsuariosPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function linhaDoUsuario(): Promise<HTMLElement> {
  const nome = await screen.findByRole('button', { name: `Ver detalhes de ${NOME}` }, { timeout: 15000 });
  const linha = nome.closest('tr');
  if (!linha) throw new Error('o nome não está numa linha da tabela');
  return linha;
}

function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

describe('UsuariosPage responsiva (C1)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a 1280 px: lista enxuta, sem ID, username, CPF, telefone nem cargo', async () => {
    renderPage();
    const linha = await linhaDoUsuario();

    expect(cabecalhos()).toEqual(['Nome', 'E-mail', 'Setor', 'Função', 'Situação', 'Ações']);
    for (const texto of SO_NO_DETALHE) expect(within(linha).queryByText(texto)).not.toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Editar: ${NOME}` })).toBeInTheDocument();
  }, 20000);

  test('a 360 px: só nome, situação e o menu de ações; e-mail, setor e função na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoUsuario();

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
    for (const texto of SO_NO_DETALHE) expect(within(linha).queryByText(texto)).not.toBeInTheDocument();
    expect(within(linha).queryByRole('button', { name: `Editar: ${NOME}` })).not.toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Mais ações: ${NOME}` })).toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: /expandir linha/i }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('maria.aparecida@example.invalid')).toBeInTheDocument();
    expect(expandida.getByText('Superativar')).toBeInTheDocument();
    for (const texto of SO_NO_DETALHE) expect(expandida.queryByText(texto)).not.toBeInTheDocument();
  }, 20000);

  test('a 360 px o detalhe, aberto pelo nome, mostra username, CPF, telefone e cargo por assunto', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    await linhaDoUsuario();

    await user.click(screen.getByRole('button', { name: `Ver detalhes de ${NOME}` }));
    const detalhe = within(await screen.findByRole('dialog', { name: NOME }, { timeout: 10000 }));

    for (const secao of ['Dados pessoais', 'Lotação', 'Acesso']) {
      expect(detalhe.getByText(secao)).toBeInTheDocument();
    }
    for (const texto of SO_NO_DETALHE) expect(detalhe.getByText(texto)).toBeInTheDocument();
    expect(detalhe.getByText('Superativar')).toBeInTheDocument();
    // papel na gerência (Lotação) e função (Acesso)
    expect(detalhe.getAllByText('Coordenador')).toHaveLength(2);
  }, 30000);

  test('o detalhe leva à edição no modal de sempre', async () => {
    const user = userEvent.setup();
    renderPage();
    await linhaDoUsuario();

    await user.click(screen.getByRole('button', { name: `Ver detalhes de ${NOME}` }));
    const detalhe = await screen.findByRole('dialog', { name: NOME }, { timeout: 10000 });
    await user.click(within(detalhe).getByRole('button', { name: /Editar/ }));

    // (no jsdom o AntD dá o mesmo id "test-id" a todo diálogo: o nome acessível não distingue)
    const modal = (await screen.findByText('Editar Usuário', {}, { timeout: 10000 })).closest('[role="dialog"]');
    expect(modal).not.toBeNull();
    expect(within(modal as HTMLElement).getByLabelText('Email')).toHaveValue('maria.aparecida@example.invalid');
  }, 30000);

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await linhaDoUsuario();
    expect(cabecalhos()).toContain('E-mail');

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
  }, 20000);
});
