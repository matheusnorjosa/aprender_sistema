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
  assignGroups,
  autocompleteMunicipiosAdmin,
  createGroup,
  createUser,
  deleteGroup,
  getRBACMeta,
  listUsers,
  syncGroupMembers,
  updateGroup,
} from '../adminDAT';

describe('adminDAT API wrappers', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
    deleteMock.mockReset();
  });

  test('listUsers calls /usuarios-admin/ with params', async () => {
    getMock.mockResolvedValue({ data: { count: 0, results: [] } });

    await listUsers({ search: 'ana', is_active: true });

    expect(getMock).toHaveBeenCalledWith('/usuarios-admin/', {
      params: { search: 'ana', is_active: true },
    });
  });

  test('createUser sends full payload including telefone/cargo', async () => {
    const payload = {
      username: 'novo',
      email: 'novo@test.com',
      telefone: '85999990000',
      cargo: 'Coordenador',
    };
    postMock.mockResolvedValue({ data: { id: 1, ...payload, is_staff: false, is_superuser: false, groups: [] } });

    await createUser(payload);

    expect(postMock).toHaveBeenCalledWith('/usuarios-admin/', payload);
  });

  test('assignGroups uses /usuarios-admin/{id}/assign_groups/', async () => {
    postMock.mockResolvedValue({ data: { id: 10 } });

    await assignGroups(10, { group_ids: [1, 2, 3] });

    expect(postMock).toHaveBeenCalledWith('/usuarios-admin/10/assign_groups/', {
      group_ids: [1, 2, 3],
    });
  });

  test('createGroup accepts group_type_input payload for dynamic setor/funcao classification', async () => {
    postMock.mockResolvedValue({ data: { id: 21, name: 'Analista de Campo', group_type: 'funcao' } });

    await createGroup({ name: 'Analista de Campo', group_type_input: 'funcao' });

    expect(postMock).toHaveBeenCalledWith('/grupos/', {
      name: 'Analista de Campo',
      group_type_input: 'funcao',
    });
  });

  test('syncGroupMembers uses /grupos/{id}/sync-members/', async () => {
    postMock.mockResolvedValue({
      data: { group_id: 5, members_count: 2, member_ids: [11, 12], added: 1, removed: 0 },
    });

    await syncGroupMembers(5, { user_ids: [11, 12] });

    expect(postMock).toHaveBeenCalledWith('/grupos/5/sync-members/', { user_ids: [11, 12] });
  });

  test('updateGroup adds confirm_reserved query param when requested', async () => {
    patchMock.mockResolvedValue({ data: { id: 2, name: 'Grupo X' } });

    await updateGroup(2, { name: 'Grupo X' }, { confirmReserved: true });

    expect(patchMock).toHaveBeenCalledWith('/grupos/2/', { name: 'Grupo X' }, {
      params: { confirm_reserved: true },
    });
  });

  test('deleteGroup adds confirm_reserved query param when requested', async () => {
    deleteMock.mockResolvedValue({ data: undefined });

    await deleteGroup(2, { confirmReserved: true });

    expect(deleteMock).toHaveBeenCalledWith('/grupos/2/', {
      params: { confirm_reserved: true },
    });
  });

  test('getRBACMeta calls /rbac/meta/', async () => {
    getMock.mockResolvedValue({
      data: { setor_groups: ['DAT'], funcao_groups: ['Coordenador'], categories: ['admin_dat'] },
    });

    await getRBACMeta();

    expect(getMock).toHaveBeenCalledWith('/rbac/meta/');
  });

  test('autocompleteMunicipiosAdmin returns results list', async () => {
    getMock.mockResolvedValue({
      data: {
        results: [
          { nome: 'Fortaleza', uf: 'CE', ibge_code: '2304400', source: 'referencia', confidence: 'high' },
        ],
      },
    });

    const result = await autocompleteMunicipiosAdmin({ q: 'Fort', uf: 'CE' });

    expect(getMock).toHaveBeenCalledWith('/municipios/autocomplete/', {
      params: { q: 'Fort', uf: 'CE' },
    });
    expect(result).toEqual([
      { nome: 'Fortaleza', uf: 'CE', ibge_code: '2304400', source: 'referencia', confidence: 'high' },
    ]);
  });

  test('autocompleteMunicipiosAdmin returns empty list when API has no results key', async () => {
    getMock.mockResolvedValue({ data: {} });

    const result = await autocompleteMunicipiosAdmin({ q: 'X', uf: 'CE' });

    expect(result).toEqual([]);
  });

  test('apiRequest maps 403 to friendly permission error', async () => {
    getMock.mockRejectedValue({ response: { status: 403 } });

    await expect(listUsers()).rejects.toThrow('Você não tem permissão para realizar esta ação.');
  });

  test('apiRequest maps 404 to friendly not found error', async () => {
    getMock.mockRejectedValue({ response: { status: 404 } });

    await expect(getRBACMeta()).rejects.toThrow('Recurso não encontrado.');
  });

  test('apiRequest keeps backend detail when provided', async () => {
    postMock.mockRejectedValue({ response: { status: 400, data: { detail: 'Email já existe' } } });

    await expect(createUser({ username: 'dup' })).rejects.toThrow('Email já existe');
  });

  test('apiRequest exposes field-level validation errors when backend sends errors payload', async () => {
    postMock.mockRejectedValue({
      response: {
        status: 400,
        data: {
          code: 'INVALID',
          detail: 'Erro de validação.',
          errors: { cpf: ['Este campo é obrigatório.'] },
        },
      },
    });

    await expect(createUser({ username: 'sem-cpf' })).rejects.toThrow('Este campo é obrigatório.');
  });
});
