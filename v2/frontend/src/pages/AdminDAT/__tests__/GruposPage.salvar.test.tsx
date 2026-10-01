/**
 * C2 (Programa C) — Grupos, Setores e Funções: o Salvar não mente e não apaga membros.
 *
 * - Os membros do modal vêm da lista de usuários, carregada à parte, e o Salvar os grava por
 *   full-replace (sync-members). Sem a lista carregada, o Editar abria com 0 membros e o
 *   Salvar mandava `user_ids: []`: tirava todos do grupo e ainda dizia sucesso. Agora, sem a
 *   lista, o Salvar não mexe nos membros e o modal diz por quê, com "Tentar de novo".
 * - Membros pelo nome (e e-mail), nunca pelo username, que é o CPF.
 * - A exclusão diz quantos usuários perdem o grupo; o erro de validação mostra o motivo.
 * - Falha ao carregar a lista mostra o motivo, não "Não há dados".
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { GRUPO, MARIA } = vi.hoisted(() => ({
  GRUPO: { id: 9741, name: 'Formação Continuada do Litoral Leste', group_type: 'setor', user_count: 2, permissoes_funcionais: [] },
  MARIA: {
    id: 51,
    username: '00011122233',
    email: 'maria@example.invalid',
    first_name: 'Maria',
    last_name: 'Fictícia',
    group_ids_display: [9741],
  },
}));

vi.mock('../../../api/auth', () => ({ checkAuth: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listGroups: vi.fn(),
  listUsers: vi.fn(),
  listPermissoesFuncionais: vi.fn().mockResolvedValue({ results: [] }),
  getRBACMeta: vi.fn().mockResolvedValue({ setor_groups: [], funcao_groups: [], categories: [], setores_produto: [] }),
  getGroup: vi.fn(),
  createGroup: vi.fn(),
  updateGroup: vi.fn(),
  deleteGroup: vi.fn(),
  syncGroupMembers: vi.fn(),
}));

import { checkAuth } from '../../../api/auth';
import { createGroup, getGroup, listGroups, listUsers, syncGroupMembers, updateGroup } from '../../../api/adminDAT';
import GruposPage from '../GruposPage';

function renderPage(forcedType: 'setor' | 'funcao' = 'setor'): void {
  render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <GruposPage forcedType={forcedType} />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function abrirEditar(user: ReturnType<typeof userEvent.setup>): Promise<HTMLElement> {
  const nome = await screen.findByText(GRUPO.name, {}, { timeout: 15000 });
  const linha = nome.closest<HTMLElement>('tr')!;
  await user.click(await within(linha).findByRole('button', { name: `Editar: ${GRUPO.name}` }));
  const titulo = await screen.findByText('Editar Setor', {}, { timeout: 10000 });
  return titulo.closest<HTMLElement>('[role="dialog"]')!;
}

describe('GruposPage: salvar sem apagar membros (C2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: true } } as never);
    vi.mocked(listGroups).mockResolvedValue({ results: [GRUPO], count: 1, next: null, previous: null } as never);
    vi.mocked(listUsers).mockResolvedValue({ results: [MARIA], count: 1, next: null, previous: null } as never);
    vi.mocked(getGroup).mockResolvedValue(GRUPO as never);
    vi.mocked(updateGroup).mockResolvedValue(GRUPO as never);
    vi.mocked(syncGroupMembers).mockResolvedValue({ added: 0, removed: 0, members_count: 1 } as never);
  });

  test('lista de usuários não carregou: o Salvar não manda user_ids=[] (não esvazia o grupo)', async () => {
    vi.mocked(listUsers).mockRejectedValue(new Error('Você não tem permissão para realizar esta ação.'));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(updateGroup).toHaveBeenCalledTimes(1));
    expect(syncGroupMembers).not.toHaveBeenCalled();
  }, 40000);

  test('lista de usuários não carregou: o modal diz que os membros não serão alterados, com "Tentar de novo"', async () => {
    vi.mocked(listUsers).mockRejectedValue(new Error('Você não tem permissão para realizar esta ação.'));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    const aviso = await within(modal).findByRole('alert');
    expect(aviso).toHaveTextContent('Os membros deste grupo não serão alterados');
    expect(aviso).toHaveTextContent('Você não tem permissão para realizar esta ação.');
    expect(within(aviso).getByRole('button', { name: 'Tentar de novo' })).toBeInTheDocument();
  }, 40000);

  test('"Tentar de novo" recarrega os usuários, o campo ganha os membros atuais e o Salvar os mantém', async () => {
    vi.mocked(listUsers).mockRejectedValueOnce(new Error('Falha de rede'));
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(within(modal).getByRole('alert')).getByRole('button', { name: 'Tentar de novo' }));
    await waitFor(() => expect(within(modal).queryByRole('alert')).not.toBeInTheDocument());
    expect(await within(modal).findByText('Maria Fictícia (maria@example.invalid)')).toBeInTheDocument();

    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(syncGroupMembers).toHaveBeenCalledWith(GRUPO.id, { user_ids: [MARIA.id] }));
  }, 40000);

  test('membros pelo nome e e-mail, nunca pelo username (CPF)', async () => {
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);

    expect(within(modal).getByText('Maria Fictícia (maria@example.invalid)')).toBeInTheDocument();
    expect(modal.textContent).not.toContain(MARIA.username);
  }, 40000);

  test('erro de validação: mostra o motivo do backend, não "Erro de validação."', async () => {
    const erro = vi.spyOn(message, 'error').mockImplementation(() => (() => undefined) as never);
    vi.mocked(updateGroup).mockRejectedValue(
      Object.assign(new Error('Erro de validação.'), {
        response: { status: 400, data: { detail: 'Erro de validação.', errors: { name: ['grupo com este nome já existe.'] } } },
      }),
    );
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(erro).toHaveBeenCalledWith('Erro ao salvar grupo: grupo com este nome já existe.'));
    expect(await within(modal).findByText('grupo com este nome já existe.')).toBeInTheDocument();
    erro.mockRestore();
  }, 40000);

  test('a exclusão diz quantos usuários perdem o setor', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const linha = (await screen.findByText(GRUPO.name, {}, { timeout: 15000 })).closest<HTMLElement>('tr')!;

    await user.click(await within(linha).findByRole('button', { name: `Excluir: ${GRUPO.name}` }));

    expect(String(confirmar.mock.calls[0]![0].content)).toContain('2 usuário(s) deixarão de ter este setor');
    confirmar.mockRestore();
  }, 30000);

  test('falha ao carregar a lista: o motivo e "Tentar de novo", não "Não há dados"', async () => {
    vi.mocked(listGroups).mockRejectedValue(new Error('Você não tem permissão para realizar esta ação.'));
    renderPage();

    const alerta = await screen.findByText('Não foi possível carregar a lista.', {}, { timeout: 15000 });
    expect(alerta.closest('[role="alert"]')).toHaveTextContent('Você não tem permissão para realizar esta ação.');
    expect(screen.queryByText('Não há dados')).not.toBeInTheDocument();
    // Sem número no título: "(0)" diria que não há setor.
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent(/^Setores$/);
  }, 30000);

  test('enquanto a lista de usuários carrega: o resumo diz que está carregando, sem "não carregou" nem 0 membros', async () => {
    vi.mocked(listUsers).mockReturnValue(new Promise(() => undefined));
    const aviso = vi.spyOn(message, 'warning').mockImplementation(() => (() => undefined) as never);
    const sucesso = vi.spyOn(message, 'success').mockImplementation(() => (() => undefined) as never);
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    expect(within(modal).getByText('Membros: aguardando a lista de usuários…')).toBeInTheDocument();
    expect(within(modal).queryByText(/não carregou/)).not.toBeInTheDocument();
    expect(within(modal).queryByText(/Membros selecionados/)).not.toBeInTheDocument();

    // Salvar nesse intervalo grava o resto, e o toast diz que os membros ficaram de fora (não é sucesso pleno).
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));
    await waitFor(() =>
      expect(aviso).toHaveBeenCalledWith(
        'Grupo atualizado, mas os membros não foram alterados: a lista de usuários ainda estava carregando.',
      ),
    );
    expect(sucesso).not.toHaveBeenCalled();
    expect(syncGroupMembers).not.toHaveBeenCalled();
    aviso.mockRestore();
    sucesso.mockRestore();
  }, 40000);

  test('lista de usuários falhou: o resumo diz "não carregou" e o toast avisa que os membros não mudaram', async () => {
    vi.mocked(listUsers).mockRejectedValue(new Error('Falha de rede'));
    const aviso = vi.spyOn(message, 'warning').mockImplementation(() => (() => undefined) as never);
    const user = userEvent.setup();
    renderPage();

    const modal = await abrirEditar(user);
    expect(within(modal).getByText('Membros: não serão alterados (a lista de usuários não carregou).')).toBeInTheDocument();
    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));

    await waitFor(() =>
      expect(aviso).toHaveBeenCalledWith('Grupo atualizado, mas os membros não foram alterados: a lista de usuários não carregou.'),
    );
    aviso.mockRestore();
  }, 40000);

  test('Funções: vazio e confirmação no feminino ("Nenhuma função", "esta função")', async () => {
    const FUNCAO = { ...GRUPO, id: 9800, name: 'Formadora Regional', group_type: 'funcao' };
    vi.mocked(listGroups).mockResolvedValueOnce({ results: [], count: 0, next: null, previous: null });
    const { unmount } = render(
      <ConfigProvider locale={ptBR}>
        <MemoryRouter>
          <GruposPage forcedType="funcao" />
        </MemoryRouter>
      </ConfigProvider>,
    );
    expect(
      await screen.findByText('Nenhuma função cadastrada. Use "Nova Função" para criar.', {}, { timeout: 15000 }),
    ).toBeInTheDocument();
    unmount();

    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    vi.mocked(listGroups).mockResolvedValue({ results: [FUNCAO], count: 1, next: null, previous: null } as never);
    const user = userEvent.setup();
    renderPage('funcao');
    const linha = (await screen.findByText(FUNCAO.name, {}, { timeout: 15000 })).closest<HTMLElement>('tr')!;
    await user.click(await within(linha).findByRole('button', { name: `Excluir: ${FUNCAO.name}` }));
    expect(String(confirmar.mock.calls[0]![0].content)).toContain('2 usuário(s) deixarão de ter esta função.');
    confirmar.mockRestore();

    await user.click(screen.getByRole('button', { name: /Nova Função/ }));
    expect(await screen.findByLabelText('Nome da Função')).toBeInTheDocument();
  }, 40000);

  test('a busca tem nome acessível', async () => {
    renderPage();
    expect(await screen.findByRole('searchbox', { name: 'Buscar setores por nome' })).toBeInTheDocument();
  }, 30000);
});

/**
 * Os caminhos da lista de usuários: o Salvar de um grupo que já existe nunca manda `user_ids: []`
 * nem menos membros do que o grupo tem, se ninguém mexeu no campo. O modal não é destruído ao
 * fechar, então cada caminho é testado também na 2ª, 3ª abertura (rodada 3: o recarregamento da
 * lista "velha" deixava o campo vazio a partir do 2º Editar e o Salvar esvaziava o grupo).
 */
describe('GruposPage: nenhum caminho da lista de usuários esvazia o grupo (C2)', () => {
  const MARIA_ROTULO = 'Maria Fictícia (maria@example.invalid)';
  const JOAO = { ...MARIA, id: 52, username: '00011122244', email: 'joao@example.invalid', first_name: 'João', group_ids_display: [] as number[] };
  const JOAO_ROTULO = 'João Fictícia (joao@example.invalid)';
  const OUTRO = { ...GRUPO, id: 9742, name: 'Apoio Pedagógico do Sertão Central', user_count: 1 };
  const pagina = (results: unknown[]) => ({ results, count: results.length, next: null, previous: null }) as never;

  function adiada<T>(): { promessa: Promise<T>; resolver: (valor: T) => void } {
    let resolver!: (valor: T) => void;
    const promessa = new Promise<T>((r) => {
      resolver = r;
    });
    return { promessa, resolver };
  }

  function oModal(): HTMLElement {
    return document.querySelector<HTMLElement>('.ant-modal[role="dialog"]')!;
  }

  async function editar(user: ReturnType<typeof userEvent.setup>, grupo: { name: string } = GRUPO): Promise<HTMLElement> {
    const linha = (await screen.findByText(grupo.name, {}, { timeout: 15000 })).closest<HTMLElement>('tr')!;
    await user.click(await within(linha).findByRole('button', { name: `Editar: ${grupo.name}` }));
    await waitFor(() => expect(oModal()).toHaveTextContent('Editar Setor'), { timeout: 10000 });
    return oModal();
  }

  async function cancelar(user: ReturnType<typeof userEvent.setup>): Promise<void> {
    await user.click(within(oModal()).getByRole('button', { name: 'Cancelar' }));
  }

  async function salvar(user: ReturnType<typeof userEvent.setup>): Promise<void> {
    await user.click(within(oModal()).getByRole('button', { name: 'Salvar' }));
  }

  /** O Salvar manda exatamente estes membros para o grupo e nunca `[]` para grupo que já existe. */
  async function esperarSync(id: number, ids: number[]): Promise<void> {
    await waitFor(() => expect(syncGroupMembers).toHaveBeenCalledWith(id, { user_ids: ids }));
    expect(syncGroupMembers).not.toHaveBeenCalledWith(expect.anything(), { user_ids: [] });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: true } } as never);
    vi.mocked(listGroups).mockResolvedValue(pagina([GRUPO]));
    vi.mocked(listUsers).mockResolvedValue(pagina([MARIA]));
    vi.mocked(getGroup).mockImplementation(async (id) => (id === OUTRO.id ? OUTRO : GRUPO) as never);
    vi.mocked(updateGroup).mockResolvedValue(GRUPO as never);
    vi.mocked(syncGroupMembers).mockResolvedValue({ added: 0, removed: 0, members_count: 1 } as never);
  });

  test('carregou: Editar de novo minutos depois (lista "velha") e Salvar sem mexer mantém os membros', async () => {
    const agora = vi.spyOn(Date, 'now').mockReturnValue(1_000_000_000);
    const user = userEvent.setup();
    renderPage();

    expect(await within(await editar(user)).findByText(MARIA_ROTULO)).toBeInTheDocument();
    await cancelar(user);
    agora.mockReturnValue(1_000_000_000 + 10 * 60 * 1000);
    const modal = await editar(user);
    await waitFor(() => expect(within(modal).queryByText('Membros: aguardando a lista de usuários…')).not.toBeInTheDocument());
    agora.mockRestore();
    await salvar(user);

    await esperarSync(GRUPO.id, [MARIA.id]);
  }, 60000);

  test('carregou: reabrir o Editar várias vezes e Salvar sem mexer mantém os membros', async () => {
    const user = userEvent.setup();
    renderPage();

    for (let vez = 1; vez <= 3; vez += 1) {
      expect(await within(await editar(user)).findByText(MARIA_ROTULO)).toBeInTheDocument();
      if (vez < 3) await cancelar(user);
    }
    await salvar(user);

    await esperarSync(GRUPO.id, [MARIA.id]);
  }, 60000);

  test('carregando: a lista chega com o Editar aberto (reaberto), o campo ganha os membros e o Salvar os mantém', async () => {
    const lista = adiada<never>();
    vi.mocked(listUsers).mockReturnValueOnce(lista.promessa);
    const user = userEvent.setup();
    renderPage();

    await editar(user);
    await cancelar(user);
    const modal = await editar(user);
    expect(within(modal).getByText('Membros: aguardando a lista de usuários…')).toBeInTheDocument();
    lista.resolver(pagina([MARIA]));

    expect(await within(modal).findByText(MARIA_ROTULO)).toBeInTheDocument();
    await salvar(user);
    await esperarSync(GRUPO.id, [MARIA.id]);
  }, 60000);

  test('falhou: com o modal já aberto antes (Editar, Novo), "Tentar de novo" preenche os membros e o Salvar os mantém', async () => {
    vi.mocked(listUsers).mockRejectedValueOnce(new Error('Falha de rede'));
    const user = userEvent.setup();
    renderPage();

    await editar(user);
    await cancelar(user);
    await user.click(screen.getByRole('button', { name: /Novo Setor/ }));
    await cancelar(user);
    const modal = await editar(user);
    await user.click(within(within(modal).getByRole('alert')).getByRole('button', { name: 'Tentar de novo' }));

    expect(await within(modal).findByText(MARIA_ROTULO)).toBeInTheDocument();
    await salvar(user);
    await esperarSync(GRUPO.id, [MARIA.id]);
  }, 60000);

  test('falhou e nunca carregou: o Salvar não chama o sync em nenhuma abertura', async () => {
    vi.mocked(listUsers).mockRejectedValue(new Error('Falha de rede'));
    const aviso = vi.spyOn(message, 'warning').mockImplementation(() => (() => undefined) as never);
    const user = userEvent.setup();
    renderPage();

    await editar(user);
    await cancelar(user);
    await editar(user);
    await salvar(user);

    await waitFor(() => expect(updateGroup).toHaveBeenCalledTimes(1));
    expect(syncGroupMembers).not.toHaveBeenCalled();
    expect(aviso).toHaveBeenCalledWith('Grupo atualizado, mas os membros não foram alterados: a lista de usuários não carregou.');
    aviso.mockRestore();
  }, 60000);

  test('Editar logo depois de salvar, com a lista recarregando: quando ela chega, o campo tem os membros de agora', async () => {
    const recarga = adiada<never>();
    vi.mocked(listUsers)
      .mockResolvedValueOnce(pagina([MARIA, JOAO]))
      // Enquanto isso, em outra aba, o João entrou no setor.
      .mockReturnValueOnce(recarga.promessa);
    const user = userEvent.setup();
    renderPage();

    expect(await within(await editar(user)).findByText(MARIA_ROTULO)).toBeInTheDocument();
    await salvar(user);
    await waitFor(() => expect(listUsers).toHaveBeenCalledTimes(2));
    vi.mocked(syncGroupMembers).mockClear();

    const modal = await editar(user);
    recarga.resolver(pagina([MARIA, { ...JOAO, group_ids_display: [GRUPO.id] }]));
    expect(await within(modal).findByText(JOAO_ROTULO)).toBeInTheDocument();
    await salvar(user);

    await esperarSync(GRUPO.id, [MARIA.id, JOAO.id]);
  }, 60000);

  test('criar grupo novo depois de um Editar: o campo começa vazio e o Editar seguinte mantém os membros', async () => {
    const NOVO = { ...GRUPO, id: 9900, name: 'Setor Novo Fictício', user_count: 0 };
    vi.mocked(createGroup).mockResolvedValue(NOVO as never);
    const user = userEvent.setup();
    renderPage();

    await editar(user);
    await cancelar(user);
    await user.click(screen.getByRole('button', { name: /Novo Setor/ }));
    await waitFor(() => expect(oModal()).toHaveTextContent('Novo Setor'));
    expect(within(oModal()).queryByText(MARIA_ROTULO)).not.toBeInTheDocument();
    await user.type(within(oModal()).getByLabelText('Nome do Setor'), NOVO.name);
    await salvar(user);
    await waitFor(() => expect(syncGroupMembers).toHaveBeenCalledWith(NOVO.id, { user_ids: [] }));
    expect(syncGroupMembers).not.toHaveBeenCalledWith(GRUPO.id, expect.anything());

    expect(await within(await editar(user)).findByText(MARIA_ROTULO)).toBeInTheDocument();
    await salvar(user);
    await waitFor(() => expect(syncGroupMembers).toHaveBeenCalledWith(GRUPO.id, { user_ids: [MARIA.id] }));
  }, 60000);

  test('criar grupo novo sem a lista de usuários: cria sem membros, sem sync, com aviso', async () => {
    vi.mocked(listUsers).mockRejectedValue(new Error('Falha de rede'));
    vi.mocked(createGroup).mockResolvedValue({ ...GRUPO, id: 9901 } as never);
    const aviso = vi.spyOn(message, 'warning').mockImplementation(() => (() => undefined) as never);
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(GRUPO.name, {}, { timeout: 15000 });

    await user.click(screen.getByRole('button', { name: /Novo Setor/ }));
    await user.type(await screen.findByLabelText('Nome do Setor'), 'Setor Sem Lista');
    await salvar(user);

    await waitFor(() => expect(aviso).toHaveBeenCalledWith('Grupo criado sem membros: a lista de usuários não carregou.'));
    expect(syncGroupMembers).not.toHaveBeenCalled();
    aviso.mockRestore();
  }, 60000);

  test('trocar de grupo com o modal aberto: o campo e o Salvar são do grupo novo', async () => {
    vi.mocked(listGroups).mockResolvedValue(pagina([GRUPO, OUTRO]));
    vi.mocked(listUsers).mockResolvedValue(pagina([MARIA, { ...JOAO, group_ids_display: [OUTRO.id] }]));
    const user = userEvent.setup();
    renderPage();

    expect(await within(await editar(user)).findByText(MARIA_ROTULO)).toBeInTheDocument();
    const modal = await editar(user, OUTRO);
    expect(await within(modal).findByText(JOAO_ROTULO)).toBeInTheDocument();
    expect(within(modal).queryByText(MARIA_ROTULO)).not.toBeInTheDocument();
    await salvar(user);

    await esperarSync(OUTRO.id, [JOAO.id]);
    expect(syncGroupMembers).not.toHaveBeenCalledWith(GRUPO.id, expect.anything());
  }, 60000);

  test('trocar de grupo com o modal aberto enquanto a lista carrega: quando ela chega, os membros são do grupo novo', async () => {
    const lista = adiada<never>();
    vi.mocked(listGroups).mockResolvedValue(pagina([GRUPO, OUTRO]));
    vi.mocked(listUsers).mockReturnValueOnce(lista.promessa);
    const user = userEvent.setup();
    renderPage();

    await editar(user);
    const modal = await editar(user, OUTRO);
    lista.resolver(pagina([MARIA, { ...JOAO, group_ids_display: [OUTRO.id] }]));
    expect(await within(modal).findByText(JOAO_ROTULO)).toBeInTheDocument();
    expect(within(modal).queryByText(MARIA_ROTULO)).not.toBeInTheDocument();
    await salvar(user);

    await esperarSync(OUTRO.id, [JOAO.id]);
  }, 60000);
});
