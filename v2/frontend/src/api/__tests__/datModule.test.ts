import { beforeEach, describe, expect, test, vi } from 'vitest';

const { postMock, patchMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
  patchMock: vi.fn(),
}));

vi.mock('../../api', () => ({
  default: {
    get: vi.fn(),
    post: postMock,
    patch: patchMock,
    delete: vi.fn(),
  },
}));

import { updateCadastroEtapa } from '../datModule';

describe('datModule API', () => {
  beforeEach(() => {
    postMock.mockReset();
    patchMock.mockReset();
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
});
