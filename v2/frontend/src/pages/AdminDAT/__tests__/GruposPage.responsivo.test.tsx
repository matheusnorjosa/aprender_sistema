/**
 * C2 (Programa C) — Grupos, Setores e Funções sem rolagem horizontal: lista enxuta.
 *
 * O ID nunca vai para a grade. A linha mostra o nome (com a etiqueta "Reservado") e as
 * ações; Tipo, Usuários e Permissões sobem por largura (sm, md, lg) e, abaixo delas, ficam
 * na linha expandida do ResponsiveTable. As ações são o AcoesLinha: ícones com nome
 * acessível "Editar: <grupo>", e no celular todas no menu "Mais ações".
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal, message } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

const { GRUPOS } = vi.hoisted(() => {
  const permissao = (id: number, label: string) => ({
    id, codename: `perm_${id}`, label, description: '', category: 'operacao', is_system: false,
  });
  return {
    GRUPOS: [
      {
        id: 9731,
        name: 'Formação Continuada do Litoral Leste',
        group_type: 'setor',
        user_count: 2,
        permissoes_funcionais: [
          permissao(1, 'Aprovar solicitações'),
          permissao(2, 'Ver agenda da equipe'),
          permissao(3, 'Importar planilhas'),
          permissao(4, 'Publicar no Google Agenda'),
        ],
      },
      { id: 9732, name: 'DAT', group_type: 'setor', user_count: 5, permissoes_funcionais: [] },
    ],
  };
});

vi.mock('../../../api/auth', () => ({ checkAuth: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listGroups: vi.fn().mockResolvedValue({ results: GRUPOS, count: 2, next: null, previous: null }),
  listUsers: vi.fn().mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
  listPermissoesFuncionais: vi.fn().mockResolvedValue({ results: [] }),
  getRBACMeta: vi.fn().mockResolvedValue({
    setor_groups: ['DAT'], funcao_groups: [], categories: [], setores_produto: [],
  }),
  getGroup: vi.fn(),
  createGroup: vi.fn(),
  updateGroup: vi.fn(),
  deleteGroup: vi.fn(),
  syncGroupMembers: vi.fn(),
}));

import { checkAuth } from '../../../api/auth';
import GruposPage from '../GruposPage';

const NOME = 'Formação Continuada do Litoral Leste';
const RESERVADO = 'DAT';

function renderPage(): void {
  render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <GruposPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function linhaDo(nome: string): Promise<HTMLElement> {
  const linha = (await screen.findByText(nome, {}, { timeout: 15000 })).closest<HTMLElement>('tr');
  if (!linha) throw new Error(`"${nome}" não está numa linha da tabela`);
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

describe('GruposPage responsiva (C2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(checkAuth).mockResolvedValue({ authenticated: true, user: { is_superuser: true } } as never);
  });

  test('a 1280 px: nome, tipo, usuários, permissões e ações; sem a coluna ID', async () => {
    renderPage();
    const linha = await linhaDo(NOME);
    await within(linha).findByRole('button', { name: `Editar: ${NOME}` });

    expect(cabecalhos()).toEqual(['Nome', 'Tipo', 'Usuários', 'Permissões funcionais', 'Ações']);
    expect(linha.textContent).not.toContain('9731');
    expect(within(linha).getByText('Aprovar solicitações')).toBeInTheDocument();
    expect(within(linha).getByText('+1')).toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Excluir: ${NOME}` })).toBeInTheDocument();
    // etiqueta green com texto green-8 (5,44:1); a cor do preset dava 3,37:1
    expect(within(linha).getByText('Setor')).toHaveStyle({ color: '#237804' });
  }, 20000);

  test('a 768 px: as permissões vão para a linha expandida', async () => {
    definirLarguraTela(768);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDo(NOME);
    await within(linha).findByRole('button', { name: `Editar: ${NOME}` });

    expect(cabecalhos()).toEqual(['Nome', 'Tipo', 'Usuários', 'Ações']);
    expect(within(linha).queryByText('Aprovar solicitações')).not.toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${NOME}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('Permissões funcionais')).toBeInTheDocument();
    expect(expandida.getByText('Aprovar solicitações')).toBeInTheDocument();
  }, 20000);

  test('a 360 px: só o nome e o menu de ações; tipo, usuários e permissões na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDo(NOME);
    await within(linha).findByRole('button', { name: `Mais ações: ${NOME}` });

    expect(cabecalhos()).toEqual(['Nome', 'Ações']);
    expect(within(linha).queryByRole('button', { name: `Editar: ${NOME}` })).not.toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${NOME}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('Setor')).toBeInTheDocument();
    expect(expandida.getByText('2 usuário(s)')).toBeInTheDocument();
    expect(expandida.getByText('Aprovar solicitações')).toBeInTheDocument();
    expect(expandida.queryByText('9731')).not.toBeInTheDocument();
  }, 20000);

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await within(await linhaDo(NOME)).findByRole('button', { name: `Editar: ${NOME}` });
    expect(cabecalhos()).toContain('Permissões funcionais');

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Nome', 'Ações']);
  }, 20000);

  test('Excluir: a confirmação cita o grupo e começa no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDo(NOME);

    await user.click(await within(linha).findByRole('button', { name: `Excluir: ${NOME}` }));

    // Modal.confirm não monta de forma confiável sob React 19 no jsdom: confere o que ele recebe.
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(confirmar.mock.calls[0]![0]).toMatchObject({ autoFocusButton: 'cancel' });
    expect(String(confirmar.mock.calls[0]![0].content)).toContain(NOME);
    confirmar.mockRestore();
  }, 20000);

  test('grupo reservado: a etiqueta tem contraste AA e o Excluir só avisa, sem abrir a confirmação', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const aviso = vi.spyOn(message, 'warning').mockImplementation(() => (() => undefined) as never);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDo(RESERVADO);

    const etiqueta = (await within(linha).findByText('Reservado')).closest<HTMLElement>('.ant-tag');
    expect(etiqueta).toHaveStyle({ color: '#874d00' }); // gold-9: 6,53:1

    await user.click(await within(linha).findByRole('button', { name: `Excluir (reservado): ${RESERVADO}` }));
    expect(aviso).toHaveBeenCalledWith('Grupo reservado: exclusão bloqueada na interface.');
    // O toast do AntD não é região viva: o aviso também vai para o leitor de tela (WCAG 4.1.3).
    expect(screen.getByRole('status')).toHaveTextContent('Grupo reservado: exclusão bloqueada na interface.');
    expect(confirmar).not.toHaveBeenCalled();
    confirmar.mockRestore();
    aviso.mockRestore();
  }, 20000);
});
