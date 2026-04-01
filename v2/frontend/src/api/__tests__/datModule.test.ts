import { beforeEach, describe, expect, test, vi } from 'vitest';

const fetchAPIMock = vi.hoisted(() => vi.fn());
const fetchWithErrorMappingMock = vi.hoisted(() => vi.fn());

vi.mock('../config', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../config')>();
  return {
    ...actual,
    fetchAPI: fetchAPIMock,
    fetchWithErrorMapping: fetchWithErrorMappingMock,
  };
});

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
    fetchAPIMock.mockReset();
    fetchWithErrorMappingMock.mockReset();
  });

  test('updateCadastroEtapa uses POST on /dat/cadastros/{id}/etapa/', async () => {
    const payload = { id: 7, etapa: 'chaves', status: 'concluido' };
    fetchWithErrorMappingMock.mockResolvedValue(payload);

    const response = await updateCadastroEtapa(7, 'chaves', 'concluido');

    expect(fetchWithErrorMappingMock).toHaveBeenCalledWith(
      '/dat/cadastros/7/etapa/',
      expect.objectContaining({ method: 'POST' }),
      expect.any(Object),
    );
    expect(response).toEqual(payload);
  });

  test('produto endpoints use /produtos/ base path', async () => {
    fetchAPIMock
      .mockResolvedValueOnce({ count: 0, results: [] })
      .mockResolvedValueOnce({ id: 5, nome: 'Produto X' })
      .mockResolvedValueOnce({ id: 6, nome: 'Produto Novo' })
      .mockResolvedValueOnce({ id: 5, nome: 'Produto Atualizado' })
      .mockResolvedValueOnce(undefined);

    await listProdutosDAT({ search: 'abc' });
    await getProdutoDAT(5);
    await createProdutoDAT({ nome: 'Produto Novo' });
    await updateProdutoDAT(5, { nome: 'Produto Atualizado' });
    await deleteProdutoDAT(5);

    expect(fetchAPIMock).toHaveBeenNthCalledWith(1, expect.stringContaining('/produtos/'));
    expect(fetchAPIMock).toHaveBeenNthCalledWith(2, '/produtos/5/');
    expect(fetchAPIMock).toHaveBeenNthCalledWith(3, '/produtos/', expect.objectContaining({ method: 'POST' }));
    expect(fetchAPIMock).toHaveBeenNthCalledWith(4, '/produtos/5/', expect.objectContaining({ method: 'PATCH' }));
    expect(fetchAPIMock).toHaveBeenNthCalledWith(5, '/produtos/5/', expect.objectContaining({ method: 'DELETE' }));
  });
});
