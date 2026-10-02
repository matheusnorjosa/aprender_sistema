/**
 * C1 (Programa C) — Usuários sem rolagem horizontal: lista enxuta + detalhe por assunto.
 *
 * Nunca na grade: ID, CPF, username (em produção o username É o CPF), telefone e cargo.
 * Eles ficam no detalhe (Drawer com Dados pessoais · Lotação · Acesso), aberto pelo nome.
 * O login (CPF) aparece mascarado com a regra do `cpf_masked` do backend (decisão 4 do
 * dono): o CPF cru não aparece em texto, aria-label, title nem valor de campo, no detalhe
 * nem nos modais. O form de edição guarda o valor real, que o Salvar manda como antes.
 * A 360 px a linha mostra identidade, situação e o menu de ações; o resto vai para a
 * linha expandida do ResponsiveTable.
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

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
      is_staff: false,
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

import { listUsers, updateUser } from '../../../api/adminDAT';
import { checkAuth } from '../../../api/auth';
import UsuariosPage from '../UsuariosPage';

const NOME = 'Maria Aparecida da Conceição';
const CPF = '12345678901'; // o username da fixture
/** Mesma regra do `cpf_masked` do backend (UsuarioAdminSerializer): só os 6 últimos. */
const LOGIN_MASCARADO = '***.***.678901';
/** O que nunca pode aparecer na grade (o CPF cru, nem no detalhe). */
const SO_NO_DETALHE = [LOGIN_MASCARADO, '***.***.678-01', '85988887777', 'Coordenadora Pedagógica Regional'];

/** O CPF cru não aparece em texto, aria-label, title nem valor de campo. */
function semCpfCru(el: HTMLElement): void {
  expect(el.textContent).not.toContain(CPF);
  for (const no of Array.from(el.querySelectorAll('*'))) {
    for (const atributo of ['aria-label', 'title', 'value']) {
      expect(no.getAttribute(atributo) ?? '', `${atributo} de <${no.tagName.toLowerCase()}>`).not.toContain(CPF);
    }
    if (no instanceof HTMLInputElement) expect(no.value).not.toContain(CPF);
  }
}

async function abrirModal(titulo: string): Promise<HTMLElement> {
  // (no jsdom o AntD dá o mesmo id "test-id" a todo diálogo: o nome acessível não distingue)
  const modal = (await screen.findByText(titulo, {}, { timeout: 10000 })).closest<HTMLElement>('[role="dialog"]');
  if (!modal) throw new Error(`o modal "${titulo}" não abriu`);
  return modal;
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

async function linhaDoUsuario(): Promise<HTMLElement> {
  const nome = await screen.findByRole('button', { name: `Ver detalhes de ${NOME}` }, { timeout: 15000 });
  const linha = nome.closest('tr');
  if (!linha) throw new Error('o nome não está numa linha da tabela');
  return linha;
}

/** Títulos das colunas de dados (sem a do botão de expandir, cujo título é só para leitor de tela). */
function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

// Teste que troca a lista (CPF formatado, total para paginar) não vaza para os outros.
afterEach(() => {
  vi.mocked(listUsers).mockResolvedValue({ results: USUARIOS, count: 1, next: null, previous: null });
});

describe('UsuariosPage responsiva (C1)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a 1280 px: lista enxuta, sem ID, username, CPF, telefone nem cargo', async () => {
    renderPage();
    const linha = await linhaDoUsuario();

    expect(cabecalhos()).toEqual(['Nome', 'E-mail', 'Setor', 'Função', 'Situação', 'Ações']);
    for (const texto of [CPF, ...SO_NO_DETALHE]) expect(within(linha).queryByText(texto)).not.toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Editar: ${NOME}` })).toBeInTheDocument();
  }, 20000);

  test('a 360 px: só nome, situação e o menu de ações; e-mail, setor e função na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoUsuario();

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
    for (const texto of [CPF, ...SO_NO_DETALHE]) expect(within(linha).queryByText(texto)).not.toBeInTheDocument();
    expect(within(linha).queryByRole('button', { name: `Editar: ${NOME}` })).not.toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Mais ações: ${NOME}` })).toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${NOME}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('maria.aparecida@example.invalid')).toBeInTheDocument();
    expect(expandida.getByText('Superativar')).toBeInTheDocument();
    for (const texto of [CPF, ...SO_NO_DETALHE]) expect(expandida.queryByText(texto)).not.toBeInTheDocument();
  }, 20000);

  test('a 360 px o detalhe, aberto pelo nome, mostra login mascarado, CPF, telefone e cargo por assunto', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    await linhaDoUsuario();

    await user.click(screen.getByRole('button', { name: `Ver detalhes de ${NOME}` }));
    const drawer = await screen.findByRole('dialog', { name: NOME }, { timeout: 10000 });
    const detalhe = within(drawer);

    for (const secao of ['Dados pessoais', 'Lotação', 'Acesso']) {
      expect(detalhe.getByText(secao)).toBeInTheDocument();
    }
    for (const texto of SO_NO_DETALHE) expect(detalhe.getByText(texto)).toBeInTheDocument();
    semCpfCru(drawer);
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

  test('Editar: o username (o CPF) aparece mascarado, e o Salvar manda o valor real', async () => {
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoUsuario();

    await user.click(within(linha).getByRole('button', { name: `Editar: ${NOME}` }));
    const modal = await abrirModal('Editar Usuário');

    expect(within(modal).getByLabelText('Username')).toHaveValue(LOGIN_MASCARADO);
    semCpfCru(modal);

    await user.click(within(modal).getByRole('button', { name: 'Salvar' }));
    // a máscara nunca vira o login: o form guarda o valor real (o PATCH manda o que mandava)
    await vi.waitFor(() => expect(updateUser).toHaveBeenCalledTimes(1), { timeout: 10000 });
    expect(vi.mocked(updateUser).mock.calls[0]![1]).toEqual(expect.objectContaining({ username: CPF }));
  }, 30000);

  test('login com o CPF formatado (000.000.000-00) também sai mascarado, no detalhe e no Editar', async () => {
    const formatado = '123.456.789-01'; // o mesmo CPF fictício, com pontuação
    vi.mocked(listUsers).mockResolvedValue({
      results: [{ ...USUARIOS[0]!, username: formatado }], count: 1, next: null, previous: null,
    });
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoUsuario();

    await user.click(within(linha).getByRole('button', { name: `Ver detalhes de ${NOME}` }));
    const drawer = await screen.findByRole('dialog', { name: NOME }, { timeout: 10000 });
    expect(within(drawer).getByText(LOGIN_MASCARADO)).toBeInTheDocument();
    expect(drawer.textContent).not.toContain(formatado);

    await user.click(within(drawer).getByRole('button', { name: /Editar/ }));
    const modal = await abrirModal('Editar Usuário');
    expect(within(modal).getByLabelText('Username')).toHaveValue(LOGIN_MASCARADO);
  }, 30000);

  test('Redefinir senha e Excluir não mostram o CPF cru', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoUsuario();

    await user.click(within(linha).getByRole('button', { name: `Redefinir senha: ${NOME}` }));
    semCpfCru(await abrirModal(`Redefinir senha — ${NOME}`));

    // Modal.confirm não monta de forma confiável sob React 19 no jsdom: confere o que ele recebe.
    await user.click(within(linha).getByRole('button', { name: `Excluir: ${NOME}` }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(confirmar.mock.calls[0]![0])).not.toContain(CPF);
    confirmar.mockRestore();
  }, 30000);

  test('Excluir: a confirmação começa no Cancelar (Enter repetido não apaga)', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoUsuario();

    await user.click(within(linha).getByRole('button', { name: `Excluir: ${NOME}` }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(confirmar.mock.calls[0]![0]).toMatchObject({ autoFocusButton: 'cancel' });
    confirmar.mockRestore();
  }, 30000);

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await linhaDoUsuario();
    expect(cabecalhos()).toContain('E-mail');

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
  }, 20000);
});

describe('UsuariosPage: lista ordenada pelo nome (decisão 5 do dono)', () => {
  beforeEach(() => vi.clearAllMocks());

  /** `ordering` de cada GET da lista, em ordem. */
  const ordenacoes = (): unknown[] => vi.mocked(listUsers).mock.calls.map(([params]) => params?.['ordering']);
  const cabecalho = (nome: RegExp): HTMLElement => screen.getByRole('columnheader', { name: nome });
  /** Clica no cabeçalho e espera o GET que o clique dispara. */
  async function ordenarPor(user: ReturnType<typeof userEvent.setup>, nome: RegExp): Promise<void> {
    const antes = ordenacoes().length;
    await user.click(cabecalho(nome));
    await vi.waitFor(() => expect(ordenacoes()).toHaveLength(antes + 1));
  }

  test('abre pelo nome (desempate pelo id), não pelo username (o CPF), e o cabeçalho Nome diz isso', async () => {
    renderPage();
    await linhaDoUsuario();
    expect(ordenacoes()).toEqual(['first_name,last_name,id']);
    expect(cabecalho(/^Nome/)).toHaveAttribute('aria-sort', 'ascending');
    expect(cabecalho(/^E-mail/)).not.toHaveAttribute('aria-sort');
  }, 20000);

  test('Nome inverte e volta; E-mail ordena com o id desempatando; seta e aria-sort seguem a lista', async () => {
    const user = userEvent.setup();
    renderPage();
    await linhaDoUsuario();

    await ordenarPor(user, /^Nome/);
    expect(cabecalho(/^Nome/)).toHaveAttribute('aria-sort', 'descending');
    await ordenarPor(user, /^Nome/); // limpar a ordenação volta ao padrão: Nome crescente
    expect(cabecalho(/^Nome/)).toHaveAttribute('aria-sort', 'ascending');
    await ordenarPor(user, /^E-mail/);
    expect(cabecalho(/^E-mail/)).toHaveAttribute('aria-sort', 'ascending');
    expect(cabecalho(/^Nome/)).not.toHaveAttribute('aria-sort');
    await ordenarPor(user, /^E-mail/);
    expect(cabecalho(/^E-mail/)).toHaveAttribute('aria-sort', 'descending');

    expect(ordenacoes().slice(1)).toEqual([
      '-first_name,-last_name,-id',
      'first_name,last_name,id',
      'email,id',
      '-email,-id',
    ]);
  }, 30000);

  test('a ordem escolhida vale na busca, no Atualizar e na paginação', async () => {
    vi.mocked(listUsers).mockResolvedValue({ results: USUARIOS, count: 25, next: null, previous: null });
    const user = userEvent.setup();
    renderPage();
    await linhaDoUsuario();
    await ordenarPor(user, /^Nome/);
    const decrescente = '-first_name,-last_name,-id';

    await user.type(screen.getByRole('searchbox', { name: /Buscar usuários/ }), 'Maria{Enter}');
    await vi.waitFor(() => expect(vi.mocked(listUsers).mock.calls.at(-1)?.[0]?.['search']).toBe('Maria'));
    expect(ordenacoes().at(-1)).toBe(decrescente);

    await user.click(screen.getByRole('button', { name: /Atualizar/ }));
    await vi.waitFor(() => expect(ordenacoes()).toHaveLength(4));
    expect(ordenacoes().at(-1)).toBe(decrescente);

    await user.click(await screen.findByTitle('2'));
    await vi.waitFor(() => expect(vi.mocked(listUsers).mock.calls.at(-1)?.[0]?.['page']).toBe(2));
    expect(ordenacoes().at(-1)).toBe(decrescente);
    expect(cabecalho(/^Nome/)).toHaveAttribute('aria-sort', 'descending');
  }, 30000);
});

describe('UsuariosPage: importar pela tela é só do superusuário (decisão do dono, 02/10/2026)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('superusuário vê a opção Importar', async () => {
    renderPage();
    await linhaDoUsuario();

    expect(await screen.findByRole('radio', { name: 'Importar' })).toBeInTheDocument();
  }, 20000);

  test('quem não é superusuário (DAT) não vê a opção Importar', async () => {
    vi.mocked(checkAuth).mockResolvedValueOnce({ authenticated: true, user: { is_superuser: false } } as never);
    renderPage();
    await linhaDoUsuario();
    await vi.waitFor(() => expect(checkAuth).toHaveBeenCalled());

    expect(screen.queryByRole('radio', { name: 'Importar' })).not.toBeInTheDocument();
    expect(screen.queryByRole('radio', { name: 'Lista' })).not.toBeInTheDocument();
  }, 20000);
});
