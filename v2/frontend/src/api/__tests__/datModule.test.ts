import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getMock, postMock, patchMock, deleteMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  patchMock: vi.fn(),
  deleteMock: vi.fn(),
}));

vi.mock('../../api', () => ({
  default: {
    get: getMock,
    post: postMock,
    patch: patchMock,
    delete: deleteMock,
  },
}));

import {
  createProdutoDAT,
  deleteProdutoDAT,
  getProdutoDAT,
  listProdutosDAT,
  updateCadastroEtapa,
  updateProdutoDAT,
} from '../datModule';

describe('datModule API', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
    deleteMock.mockReset();
  });

  test('updateCadastroEtapa uses POST on /dat/cadastros/{id}/etapa/', async () => {
    const payload = { id: 7, etapa: 'chaves', status: 'concluido' };
    postMock.mockResolvedValue({ data: payload });

    const response = await updateCadastroEtapa(7, 'chaves', 'concluido');

    expect(postMock).toHaveBeenCalledWith('/dat/cadastros/7/etapa/', {
      etapa: 'chaves',
      status: 'concluido',
    });
    expect(patchMock).not.toHaveBeenCalled();
    expect(response).toEqual(payload);
  });

  test('produto endpoints use /produtos/ base path', async () => {
    getMock.mockResolvedValueOnce({ data: { count: 0, results: [] } });
    getMock.mockResolvedValueOnce({ data: { id: 5, nome: 'Produto X' } });
    postMock.mockResolvedValueOnce({ data: { id: 6, nome: 'Produto Novo' } });
    patchMock.mockResolvedValueOnce({ data: { id: 5, nome: 'Produto Atualizado' } });
    deleteMock.mockResolvedValueOnce({ data: undefined });

    await listProdutosDAT({ search: 'abc' });
    await getProdutoDAT(5);
    await createProdutoDAT({ nome: 'Produto Novo' });
    await updateProdutoDAT(5, { nome: 'Produto Atualizado' });
    await deleteProdutoDAT(5);

    expect(getMock).toHaveBeenNthCalledWith(1, '/produtos/', { params: { search: 'abc' } });
    expect(getMock).toHaveBeenNthCalledWith(2, '/produtos/5/');
    expect(postMock).toHaveBeenCalledWith('/produtos/', { nome: 'Produto Novo' });
    expect(patchMock).toHaveBeenCalledWith('/produtos/5/', { nome: 'Produto Atualizado' });
    expect(deleteMock).toHaveBeenCalledWith('/produtos/5/');
  });
});
