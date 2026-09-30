/**
 * ResponsiveTable (Programa C, C1): a tabela sem rolagem horizontal.
 *
 * - cada coluna declara a partir de que largura aparece (`responsive` do AntD, via
 *   VISIVEL_A_PARTIR); sem `responsive`, aparece sempre;
 * - o que está escondido na largura atual vai para a linha expandida, com o título da
 *   coluna como rótulo e o `render` da própria coluna: nada some da tela;
 * - o tipo não aceita `scroll` nem coluna `fixed`. Os `@ts-expect-error` abaixo são
 *   conferidos por `npx tsc --noEmit -p tsconfig.eslint.json` (o tsconfig do build exclui
 *   os testes): se o tipo passar a aceitar `scroll`, a diretiva fica sem uso e o tsc reprova.
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Tag } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { describe, expect, test } from 'vitest';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../ResponsiveTable';
import { definirLarguraTela } from '../../test/larguraTela';

interface Pessoa {
  id: number;
  nome: string;
  email: string;
  setor: string;
  funcao: string;
  ativo: boolean;
}

const PESSOAS: Pessoa[] = [
  {
    id: 1,
    nome: 'Maria Aparecida',
    email: 'maria@example.invalid',
    setor: 'Gerência de Formação Continuada',
    funcao: 'Coordenadora',
    ativo: true,
  },
  {
    id: 2,
    nome: 'José Ribamar',
    email: 'jose@example.invalid',
    setor: 'Gerência de Logística',
    funcao: 'Formador',
    ativo: false,
  },
];

const COLUNAS: ColunaResponsiva<Pessoa>[] = [
  { title: 'Nome', dataIndex: 'nome', key: 'nome', ellipsis: true },
  { title: 'E-mail', dataIndex: 'email', key: 'email', ellipsis: true, responsive: VISIVEL_A_PARTIR.md },
  {
    title: 'Setor',
    dataIndex: 'setor',
    key: 'setor',
    responsive: VISIVEL_A_PARTIR.lg,
    render: (setor: string) => <Tag>{setor}</Tag>,
  },
  { title: 'Função', dataIndex: 'funcao', key: 'funcao', responsive: VISIVEL_A_PARTIR.xl },
  { title: 'Situação', dataIndex: 'ativo', key: 'ativo', width: 96, render: (ativo: boolean) => (ativo ? 'Ativo' : 'Inativo') },
  {
    title: 'Ações',
    key: 'acoes',
    width: 64,
    render: (_: unknown, pessoa: Pessoa) => (
      <button type="button" aria-label={`Editar: ${pessoa.nome}`}>
        E
      </button>
    ),
  },
];

/** Com o locale do app (App.tsx), como no uso real. */
function renderTabela() {
  return render(
    <ConfigProvider locale={ptBR}>
      <ResponsiveTable<Pessoa>
        columns={COLUNAS}
        dataSource={PESSOAS}
        rowKey="id"
        pagination={false}
        nomeDaLinha={(pessoa) => pessoa.nome}
      />
    </ConfigProvider>,
  );
}

/** Títulos das colunas de dados (sem a do botão de expandir, cujo título é só para leitor de tela). */
function cabecalhos(): string[] {
  return screen
    .getAllByRole('columnheader')
    .filter((th) => !th.classList.contains('ant-table-row-expand-icon-cell'))
    .map((th) => th.textContent?.trim() ?? '')
    .filter(Boolean);
}

function botaoExpandir(nome = 'Maria Aparecida'): HTMLElement | null {
  // "Expandir linha", e não "detalhes": na mesma linha, o nome abre "Ver detalhes de ..." (Usuários).
  return screen.queryByRole('button', { name: `Expandir linha de ${nome}` });
}

describe('ResponsiveTable', () => {
  test('a 1280 px todas as colunas aparecem e não há linha expandida', () => {
    renderTabela();

    expect(cabecalhos()).toEqual(['Nome', 'E-mail', 'Setor', 'Função', 'Situação', 'Ações']);
    expect(botaoExpandir()).not.toBeInTheDocument();
  });

  test('a 360 px só identidade, estado e ações; o resto aparece na linha expandida, com rótulo', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderTabela();

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
    expect(screen.getByRole('button', { name: 'Editar: Maria Aparecida' })).toBeInTheDocument();
    expect(screen.queryByText('maria@example.invalid')).not.toBeInTheDocument();

    await user.click(botaoExpandir()!);

    const detalhe = document.querySelector<HTMLElement>('.ant-table-expanded-row');
    expect(detalhe).not.toBeNull();
    const itens = within(detalhe!);
    expect(itens.getByText('E-mail')).toBeInTheDocument();
    expect(itens.getByText('maria@example.invalid')).toBeInTheDocument();
    expect(itens.getByText('Setor')).toBeInTheDocument();
    // o render da coluna é reaproveitado (a Tag), não só o valor cru
    expect(itens.getByText('Gerência de Formação Continuada').closest('.ant-tag')).not.toBeNull();
    expect(itens.getByText('Função')).toBeInTheDocument();
    expect(itens.getByText('Coordenadora')).toBeInTheDocument();
    // o que já está na linha não se repete no detalhe
    expect(itens.queryByText('Situação')).not.toBeInTheDocument();
  });

  test('a 1024 px o detalhe leva só o que não coube (Função, que é a partir de xl)', async () => {
    definirLarguraTela(1024);
    const user = userEvent.setup();
    renderTabela();

    expect(cabecalhos()).toEqual(['Nome', 'E-mail', 'Setor', 'Situação', 'Ações']);
    await user.click(botaoExpandir()!);
    const itens = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(itens.getByText('Função')).toBeInTheDocument();
    expect(itens.queryByText('E-mail')).not.toBeInTheDocument();
  });

  test('acompanha a mudança de largura depois de montada', () => {
    renderTabela();
    expect(cabecalhos()).toContain('Função');

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
    expect(botaoExpandir()).toBeInTheDocument();
  });

  test('o botão de expandir diz de que linha é, e a coluna dele tem título para leitor de tela', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderTabela();

    const maria = botaoExpandir('Maria Aparecida')!;
    const jose = botaoExpandir('José Ribamar')!;
    expect(maria).toBeInTheDocument();
    expect(jose).toBeInTheDocument();
    // a classe do AntD fica: é ela que desenha o +/- e que o Playwright procura
    expect(maria).toHaveClass('ant-table-row-expand-icon');
    expect(maria).toHaveAttribute('aria-expanded', 'false');

    await user.click(maria);
    expect(maria).toHaveAttribute('aria-expanded', 'true');
    expect(jose).toHaveAttribute('aria-expanded', 'false');

    const cabecalho = document.querySelector<HTMLElement>('th.ant-table-row-expand-icon-cell');
    expect(cabecalho).toHaveTextContent('Detalhes');
    expect(within(cabecalho!).getByText('Detalhes')).toHaveClass('sr-only');
  });

  test('layout fixo: as colunas cabem na largura da tabela', () => {
    const { container } = renderTabela();
    expect(container.querySelector('table')).toHaveStyle({ tableLayout: 'fixed' });
  });

  test('o tipo não aceita scroll nem coluna fixed (conferido pelo tsc -p tsconfig.eslint.json)', () => {
    const comScroll = (
      <ResponsiveTable<Pessoa>
        columns={COLUNAS}
        dataSource={PESSOAS}
        rowKey="id"
        // @ts-expect-error: scroll.x é a rolagem horizontal que o padrão proíbe
        scroll={{ x: 1200 }}
      />
    );
    const colunaFixa: ColunaResponsiva<Pessoa> = {
      title: 'Nome',
      key: 'nome',
      // @ts-expect-error: coluna fixed só existe com scroll.x
      fixed: 'left',
    };
    expect(comScroll).toBeTruthy();
    expect(colunaFixa).toBeTruthy();
  });
});
