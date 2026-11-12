/**
 * G17 — Compras (tela): não apagar a observação, filtro de status, UF e campos da carga.
 *
 * - P#27/P#29: a edição semeia o modal com a linha da lista; sem `observacoes` na linha, a compra
 *   abria com Observações vazia e quem escrevia ali apagava o texto anterior.
 * - P#26/P#30: o filtro mandava `?status=` (o servidor só conhece `status_uso`) e oferecia
 *   "Reservado", que não existe; faltava "Devolvido".
 * - P#31: editar travava em "Selecione a UF" (a linha traz `municipio_uf`, não `uf`).
 * - P#32: a edição exigia Produto, Tipo de Compra e Ano de Uso, que a compra importada não tem.
 * - B#32: `ordering=-updated_at` não é aceito pelo servidor.
 * - B#34: "Baixo Estoque" nunca aparece (o status sempre vem preenchido).
 */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';

import { ComAcesso } from '../../../test/comAcesso';
import { listCompras, updateCompra, createCompra } from '../../../api/datModule';

const { comObservacao, importada } = vi.hoisted(() => ({
  comObservacao: {
    id: 1, projeto: 10, projeto_nome: 'NOVO LENDO 1', projeto_geral_nome: 'NOVO LENDO',
    produto: 100, produto_nome: 'Livro do Aluno', codigo_produto: 'LA1', descricao_produto: '',
    municipio: 20, municipio_nome: 'Fortaleza', municipio_uf: 'CE',
    quantidade: 100, quantidade_utilizada: 40, valor_unitario: '5.00', data_compra: '2026-03-01',
    ano_uso: 2026, tipo_compra: 'primeira', tipo: null, status_uso: 'em_uso', ativo: true,
    observacoes: 'Entrega parcial combinada com a secretaria',
  },
  // Carga importada: sem produto cadastrado (só a descrição), sem tipo de compra e sem ano.
  importada: {
    id: 2, projeto: 11, projeto_nome: 'ACERTA 2', projeto_geral_nome: 'ACERTA',
    produto: null, produto_nome: null, codigo_produto: null, descricao_produto: 'Kit importado',
    municipio: 21, municipio_nome: 'Crato', municipio_uf: 'CE',
    quantidade: 50, quantidade_utilizada: 0, valor_unitario: '0.00', data_compra: null,
    ano_uso: null, tipo_compra: null, tipo: null, status_uso: 'devolvido', ativo: true,
    observacoes: '',
  },
}));

vi.mock('../../../api/datModule', () => ({
  listCompras: vi.fn().mockResolvedValue({ results: [comObservacao, importada], count: 2, next: null, previous: null }),
  createCompra: vi.fn().mockResolvedValue({}),
  updateCompra: vi.fn().mockResolvedValue({}),
  deleteCompra: vi.fn(),
  getMunicipiosOptions: vi.fn().mockResolvedValue([]),
  getProjetosOptions: vi.fn().mockResolvedValue([]),
  getProdutosOptions: vi.fn().mockResolvedValue([]),
}));

import ComprasPage from '../ComprasPage';

// Tela pesada (AntD + filtros + tabela + modal): na CI passa dos 5 s padrão.
vi.setConfig({ testTimeout: 60_000 }); // FER-53: estourava 30 s no CI com cobertura

const DAT = ['view_compras_stats', 'access_controle_section', 'run_daily_operations', 'execute_restricted_operations'];

function renderPagina(): ReturnType<typeof render> {
  return render(
    <MemoryRouter>
      <ComAcesso policies={DAT}>
        <ComprasPage />
      </ComAcesso>
    </MemoryRouter>,
  );
}

async function abrirEdicao(nome: string): Promise<HTMLElement> {
  fireEvent.click(await screen.findByRole('button', { name: `Editar: ${nome}` }, { timeout: 15000 }));
  return screen.findByRole('dialog');
}

function ultimoPayload(): Record<string, unknown> {
  const chamadas = vi.mocked(updateCompra).mock.calls;
  return chamadas[chamadas.length - 1][1];
}

beforeEach(() => vi.clearAllMocks());

describe('Compras: editar não apaga a observação', () => {
  test('o modal mostra a observação da compra e o PATCH preserva o resto', async () => {
    renderPagina();
    const dialogo = await abrirEdicao('Livro do Aluno · Fortaleza - CE');
    expect(within(dialogo).getByLabelText('Observações')).toHaveValue('Entrega parcial combinada com a secretaria');

    fireEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }));
    await waitFor(() => expect(updateCompra).toHaveBeenCalledTimes(1));
    expect(updateCompra).toHaveBeenCalledWith(1, expect.objectContaining({
      observacoes: 'Entrega parcial combinada com a secretaria',
      projeto: 10,
      produto: 100,
      municipio: 20,
      quantidade: 100,
      quantidade_utilizada: 40,
      ano_uso: 2026,
      tipo_compra: 'primeira',
      data_compra: '2026-03-01',
    }));
  });
});

describe('Compras: editar a carga importada', () => {
  test('mudar só a quantidade salva sem pedir UF, produto, tipo ou ano', async () => {
    renderPagina();
    const dialogo = await abrirEdicao('ACERTA 2 · Crato - CE');
    expect(within(dialogo).queryByText('Selecione a UF')).not.toBeInTheDocument();

    fireEvent.change(within(dialogo).getByRole('spinbutton', { name: 'Quantidade' }), { target: { value: '70' } });
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(updateCompra).toHaveBeenCalledTimes(1));
    const payload = ultimoPayload();
    expect(payload.quantidade).toBe(70);
    // Nada inventado: o que estava vazio continua vazio.
    expect(payload.produto ?? null).toBeNull();
    expect(payload.descricao_produto).toBe('Kit importado');
    expect(payload.tipo_compra ?? null).toBeNull();
    expect(payload.ano_uso ?? null).toBeNull();
    expect(within(dialogo).queryByText(/Selecione o (produto|tipo de compra|ano de uso)/)).not.toBeInTheDocument();
  });

  test('limpar o Produto e escrever a Descrição manda produto: null no PATCH', async () => {
    renderPagina();
    const dialogo = await abrirEdicao('Livro do Aluno · Fortaleza - CE');

    const campoProduto = within(dialogo).getByLabelText('Produto').closest('.ant-select') as HTMLElement;
    const limpar = campoProduto.querySelector('.ant-select-clear') as HTMLElement;
    fireEvent.mouseDown(limpar);
    fireEvent.mouseUp(limpar);
    fireEvent.change(within(dialogo).getByLabelText('Descrição'), { target: { value: 'Kit avulso' } });
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(updateCompra).toHaveBeenCalledTimes(1));
    const payload = ultimoPayload();
    // undefined some no JSON.stringify do PATCH e o servidor manteria o produto antigo.
    expect(payload).toHaveProperty('produto', null);
    expect(payload.descricao_produto).toBe('Kit avulso');
  });

  test('na criação, tipo de compra e ano de uso continuam obrigatórios', async () => {
    renderPagina();
    fireEvent.click(await screen.findByRole('button', { name: /Nova Compra/ }, { timeout: 15000 }));
    const dialogo = await screen.findByRole('dialog');
    fireEvent.click(within(dialogo).getByRole('button', { name: 'Salvar' }));

    expect(await within(dialogo).findByText('Selecione o tipo de compra', {}, { timeout: 10000 })).toBeInTheDocument();
    expect(within(dialogo).getByText('Selecione o ano de uso')).toBeInTheDocument();
    expect(within(dialogo).getByText('Selecione o produto ou preencha a descrição')).toBeInTheDocument();
    expect(createCompra).not.toHaveBeenCalled();
  });
});

describe('Compras: filtro de status e ordenação', () => {
  test('o filtro oferece Devolvido (não Reservado) e manda status_uso', async () => {
    renderPagina();
    await screen.findByRole('button', { name: 'Editar: Livro do Aluno · Fortaleza - CE' }, { timeout: 15000 });

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Status' }));
    await screen.findByTitle('Devolvido');
    expect(screen.queryByTitle('Reservado')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTitle('Esgotado'));
    fireEvent.click(screen.getByRole('button', { name: /Filtrar/ }));

    await waitFor(() => {
      const chamadas = vi.mocked(listCompras).mock.calls;
      const params = chamadas[chamadas.length - 1][0] as Record<string, unknown>;
      expect(params).toMatchObject({ status_uso: 'esgotado' });
      expect(params).not.toHaveProperty('status');
    });
  });

  test('a lista pede uma ordenação que o servidor aceita', async () => {
    renderPagina();
    await waitFor(() => expect(listCompras).toHaveBeenCalled());
    expect(vi.mocked(listCompras).mock.calls[0][0]).toMatchObject({ ordering: '-created_at' });
  });
});

describe('Compras: etiqueta e legenda de status', () => {
  test('a compra devolvida mostra Devolvido e a legenda não promete Baixo Estoque', async () => {
    renderPagina();
    await screen.findByRole('button', { name: 'Editar: ACERTA 2 · Crato - CE' }, { timeout: 15000 });
    const legenda = screen.getByRole('complementary', { name: 'Legenda de status' });
    expect(within(legenda).queryByText('Baixo Estoque')).not.toBeInTheDocument();
    expect(within(legenda).getByText('Devolvido')).toBeInTheDocument();
    expect(screen.queryByText('Baixo Estoque')).not.toBeInTheDocument();
  });
});
