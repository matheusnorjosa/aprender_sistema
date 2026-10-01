/**
 * C2 (Programa C) — Municípios sem rolagem horizontal: lista enxuta no ResponsiveTable.
 *
 * Sempre na linha: o nome, a situação e as ações (AcoesLinha, com o nome e a UF no nome
 * acessível: há municípios de mesmo nome em UFs diferentes). UF sobe a partir de `sm` e o
 * código IBGE a partir de `md`; abaixo disso, vão para a linha expandida. O ID interno
 * não vai para a grade. A 360 px as ações ficam no menu "Mais ações".
 */
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigProvider, Modal } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, test, vi } from 'vitest';

import { definirLarguraTela } from '../../../test/larguraTela';

const { MUNICIPIOS } = vi.hoisted(() => ({
  MUNICIPIOS: [
    { id: 917, nome: 'São Sebastião dos Campos Gerais', uf: 'BA', ibge_code: '2927408', ativo: true },
  ],
}));

vi.mock('../../../api/ops', () => ({ importMunicipios: vi.fn() }));
vi.mock('../../../api/adminDAT', () => ({
  listMunicipios: vi.fn().mockResolvedValue({ results: MUNICIPIOS, count: 1, next: null, previous: null }),
  createMunicipio: vi.fn(),
  updateMunicipio: vi.fn(),
  deleteMunicipio: vi.fn(),
  autocompleteMunicipiosAdmin: vi.fn().mockResolvedValue([]),
}));

import MunicipiosPage from '../MunicipiosPage';

const NOME = 'São Sebastião dos Campos Gerais';
/** Quem a linha representa: o nome com a UF. */
const ALVO = `${NOME} - BA`;

function renderPage() {
  return render(
    <ConfigProvider locale={ptBR}>
      <MemoryRouter>
        <MunicipiosPage />
      </MemoryRouter>
    </ConfigProvider>,
  );
}

async function linhaDoMunicipio(): Promise<HTMLElement> {
  const nome = await screen.findByText(NOME, { selector: 'td, td *' }, { timeout: 15000 });
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

describe('MunicipiosPage responsiva (C2)', () => {
  beforeEach(() => vi.clearAllMocks());

  test('a 1280 px: nome, UF, IBGE, situação e ações por ícone, sem o ID', async () => {
    renderPage();
    const linha = await linhaDoMunicipio();

    expect(cabecalhos()).toEqual(['Nome', 'UF', 'IBGE', 'Situação', 'Ações']);
    // O nome (identidade) quebra linha em vez de cortar com reticências: não há detalhe que o mostre.
    expect(within(linha).getByText(NOME).closest('td')).not.toHaveClass('ant-table-cell-ellipsis');
    expect(within(linha).queryByText('917')).not.toBeInTheDocument();
    expect(within(linha).getByText('2927408')).toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Editar: ${ALVO}` })).toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Excluir: ${ALVO}` })).toBeInTheDocument();
  }, 20000);

  test('a 360 px: só nome, situação e o menu de ações; UF e IBGE na linha expandida', async () => {
    definirLarguraTela(360);
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoMunicipio();

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
    // Sem a coluna UF, a UF fica junto do nome: homônimos de UFs diferentes não ficam iguais.
    expect(within(linha).getByText(NOME).closest('td')).toHaveTextContent(ALVO);
    expect(within(linha).queryByText('2927408')).not.toBeInTheDocument();
    expect(within(linha).queryByRole('button', { name: `Editar: ${ALVO}` })).not.toBeInTheDocument();
    expect(within(linha).getByRole('button', { name: `Mais ações: ${ALVO}` })).toBeInTheDocument();

    await user.click(within(linha).getByRole('button', { name: `Expandir linha de ${ALVO}` }));
    const expandida = within(document.querySelector<HTMLElement>('.ant-table-expanded-row')!);
    expect(expandida.getByText('BA')).toBeInTheDocument();
    expect(expandida.getByText('2927408')).toBeInTheDocument();
  }, 20000);

  test('mudar a largura com a página aberta reorganiza as colunas', async () => {
    renderPage();
    await linhaDoMunicipio();
    expect(cabecalhos()).toContain('IBGE');

    act(() => definirLarguraTela(360));

    expect(cabecalhos()).toEqual(['Nome', 'Situação', 'Ações']);
  }, 20000);

  test('a etiqueta de situação tem contraste AA (texto green-8)', async () => {
    renderPage();
    const linha = await linhaDoMunicipio();

    expect(within(linha).getByText('Ativo')).toHaveStyle({ color: '#237804' });
  }, 20000);

  test('Editar abre o modal de sempre com o município', async () => {
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoMunicipio();

    await user.click(within(linha).getByRole('button', { name: `Editar: ${ALVO}` }));
    // (no jsdom o AntD dá o mesmo id "test-id" a todo diálogo: o nome acessível não distingue)
    const modal = (await screen.findByText('Editar Município', {}, { timeout: 10000 })).closest<HTMLElement>(
      '[role="dialog"]',
    );
    expect(modal).not.toBeNull();
    expect(within(modal!).getByLabelText('Código IBGE')).toHaveValue('2927408');
  }, 30000);

  test('Excluir: a confirmação cita o município e começa no Cancelar', async () => {
    const confirmar = vi.spyOn(Modal, 'confirm').mockImplementation(() => ({ destroy: vi.fn(), update: vi.fn() }));
    const user = userEvent.setup();
    renderPage();
    const linha = await linhaDoMunicipio();

    // Modal.confirm não monta de forma confiável sob React 19 no jsdom: confere o que ele recebe.
    await user.click(within(linha).getByRole('button', { name: `Excluir: ${ALVO}` }));
    expect(confirmar).toHaveBeenCalledTimes(1);
    expect(confirmar.mock.calls[0]![0]).toMatchObject({ autoFocusButton: 'cancel' });
    expect(String(confirmar.mock.calls[0]![0].content)).toContain(ALVO);
    confirmar.mockRestore();
  }, 30000);
});
