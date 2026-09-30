/**
 * C1 (Programa C) — Usuários: os achados de acessibilidade e identificação da revisão
 * adversarial (relatorios/revisao_adversarial_c1_2026-09-30.md).
 *
 * - Tags com contraste AA: o AntD pinta o preset com a cor 7 sobre a cor 1 e reprova 4,5:1
 *   em green, gold e orange; o texto vai para green-8, gold-9 e orange-8.
 * - As seções do detalhe são cabeçalhos (h3), não <div>.
 * - Excluir e Redefinir senha identificam a pessoa pelo nome, não pelo username (= CPF).
 * - Drawer > Editar: ao fechar o modal, o foco volta ao nome da linha, e não se perde.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { USUARIOS } = vi.hoisted(() => ({
  USUARIOS: [
    {
      id: 42,
      username: '12345678901', // em produção o login é o CPF
      email: 'maria.aparecida@example.invalid',
      first_name: 'Maria Aparecida',
      last_name: 'da Conceição',
      // sem cpf_masked: o detalhe mostra a tag "Sem CPF"
      is_active: true,
      is_superuser: true,
      groups: ['Vidas', 'Coordenador'],
      group_ids_display: [1, 2],
      gerencia_atual: null,
      date_joined: '2026-03-02T12:00:00Z',
      last_login: null,
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
  resetUserPassword: vi.fn().mockResolvedValue(undefined),
  listGroups: vi.fn().mockResolvedValue({
    results: [{ id: 1, name: 'Vidas' }, { id: 2, name: 'Coordenador' }], count: 2, next: null, previous: null,
  }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: ['Vidas'], funcao_groups: ['Coordenador'], categories: [], setores_produto: [],
  }),
  listGerencias: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

import { listUsers } from '../../../api/adminDAT';
import UsuariosPage from '../UsuariosPage';

const NOME = 'Maria Aparecida da Conceição';
const USERNAME = '12345678901';

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

async function abrirDetalhe(): Promise<HTMLElement> {
  const user = userEvent.setup();
  await linhaDoUsuario();
  await user.click(screen.getByRole('button', { name: `Ver detalhes de ${NOME}` }));
  return screen.findByRole('dialog', { name: NOME }, { timeout: 10000 });
}

describe('UsuariosPage: acessibilidade e identificação (revisão do C1)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  test('tags com contraste AA: Ativo em green-8, Superusuário em gold-9, Sem CPF em orange-8', async () => {
    renderPage();
    const linha = within(await linhaDoUsuario());

    expect(linha.getByText('Ativo')).toHaveStyle({ color: '#237804' });
    expect(linha.getByText('Superusuário')).toHaveStyle({ color: '#874d00' });

    const detalhe = within(await abrirDetalhe());
    expect(detalhe.getByText('Sem CPF')).toHaveStyle({ color: '#ad4e00' });
  }, 30000);

  test('resumo do Editar: a gerência selecionada em green-8', async () => {
    const lotado = {
      ...USUARIOS[0]!,
      is_staff: false,
      gerencia_atual: { gerencia_id: 4, rotulo: 'Superativar', nome_setor: 'ACerta', setor_canonico: 'Superativar', papel: 'COORDENADOR' },
    };
    vi.mocked(listUsers).mockResolvedValueOnce({ results: [lotado], count: 1, next: null, previous: null });
    const user = userEvent.setup();
    renderPage();
    const linha = within(await linhaDoUsuario());

    await user.click(linha.getByRole('button', { name: `Editar: ${NOME}` }));

    const rotulo = await screen.findByText('Gerência selecionada:', {}, { timeout: 10000 });
    expect(await within(rotulo.closest('div')!).findByText('Superativar')).toHaveStyle({ color: '#237804' });
  }, 30000);

  test('as seções do detalhe são cabeçalhos', async () => {
    renderPage();
    const detalhe = within(await abrirDetalhe());

    for (const secao of ['Dados pessoais', 'Lotação', 'Acesso']) {
      expect(detalhe.getByRole('heading', { level: 3, name: secao })).toBeInTheDocument();
    }
  }, 30000);

  test('a confirmação de exclusão cita o nome, não o username (CPF)', async () => {
    // Modal.confirm (API estática do antd v5) não monta de forma confiável sob React 19 no
    // jsdom (ver GerenciasPage.rotulo.test.tsx): espia a chamada em vez de renderizar.
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const linha = within(await linhaDoUsuario());

    await user.click(linha.getByRole('button', { name: `Excluir: ${NOME}` }));

    expect(confirmar).toHaveBeenCalledTimes(1);
    const { content } = confirmar.mock.calls[0]![0];
    expect(content).toEqual(expect.stringContaining(`"${NOME}"`));
    expect(content).not.toEqual(expect.stringContaining(USERNAME));
  }, 30000);

  test('Redefinir senha: o título e o aviso de sucesso citam o nome, não o username (CPF)', async () => {
    const sucesso = vi.spyOn(message, 'success').mockImplementation(vi.fn());
    const user = userEvent.setup();
    renderPage();
    const linha = within(await linhaDoUsuario());

    await user.click(linha.getByRole('button', { name: `Redefinir senha: ${NOME}` }));

    const titulo = await screen.findByText(`Redefinir senha — ${NOME}`, {}, { timeout: 10000 });
    const modal = within(titulo.closest<HTMLElement>('[role="dialog"]')!);
    expect(modal.queryByText(new RegExp(USERNAME))).not.toBeInTheDocument();

    // paste (1 evento) em vez de type (1 render do form por tecla): o teste levava ~13 s e estourava sob carga.
    await user.click(modal.getByLabelText('Nova senha'));
    await user.paste('SenhaFicticia#2026');
    await user.click(modal.getByLabelText('Confirmar nova senha'));
    await user.paste('SenhaFicticia#2026');
    await user.click(modal.getByRole('button', { name: 'Redefinir senha' }));

    await waitFor(() => expect(sucesso).toHaveBeenCalledTimes(1), { timeout: 10000 });
    const aviso = String(sucesso.mock.calls[0]![0]);
    expect(aviso).toContain(NOME);
    expect(aviso).not.toContain(USERNAME);
  }, 30000);

  test('Drawer > Editar: ao fechar o modal, o foco volta ao nome da linha', async () => {
    const user = userEvent.setup();
    renderPage();
    await linhaDoUsuario();
    const nome = screen.getByRole('button', { name: `Ver detalhes de ${NOME}` });

    await user.click(nome);
    const detalhe = await screen.findByRole('dialog', { name: NOME }, { timeout: 10000 });
    await user.click(within(detalhe).getByRole('button', { name: /Editar/ }));

    const modal = (await screen.findByText('Editar Usuário', {}, { timeout: 10000 })).closest<HTMLElement>(
      '[role="dialog"]',
    );
    await user.click(within(modal!).getByRole('button', { name: 'Cancelar' }));

    await waitFor(() => expect(nome).toHaveFocus(), { timeout: 10000 });
  }, 30000);
});
