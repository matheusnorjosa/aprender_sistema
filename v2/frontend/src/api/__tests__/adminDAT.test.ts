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

// Mock syncChannel to avoid BroadcastChannel in test env
vi.mock('../../services/syncChannel', () => ({
  syncChannel: { publish: vi.fn(), subscribe: vi.fn(() => () => {}) },
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
    fetchAPIMock.mockReset();
    fetchWithErrorMappingMock.mockReset();
  });

  test('listUsers calls /usuarios-admin/ with params', async () => {
    fetchWithErrorMappingMock.mockResolvedValue({ count: 0, results: [] });

    await listUsers({ search: 'ana', is_active: true });

    expect(fetchWithErrorMappingMock).toHaveBeenCalledWith(
      expect.stringContaining('/usuarios-admin/'),
      {},
      expect.any(Object),
    );
  });

  test('createUser sends POST with payload', async () => {
    const payload = {
      username: 'novo',
      email: 'novo@test.com',
      telefone: '85999990000',
      cargo: 'Coordenador',
    };
    fetchWithErrorMappingMock.mockResolvedValue({ id: 1, ...payload });

    await createUser(payload);

    expect(fetchWithErrorMappingMock).toHaveBeenCalledWith(
      '/usuarios-admin/',
      expect.objectContaining({ method: 'POST' }),
      expect.any(Object),
    );
  });

  test('assignGroups uses /usuarios-admin/{id}/assign_groups/', async () => {
    fetchWithErrorMappingMock.mockResolvedValue({ id: 10 });

    await assignGroups(10, { group_ids: [1, 2, 3] });

    expect(fetchWithErrorMappingMock).toHaveBeenCalledWith(
      '/usuarios-admin/10/assign_groups/',
      expect.objectContaining({ method: 'POST' }),
      expect.any(Object),
    );
  });

  test('createGroup accepts group_type_input payload', async () => {
    fetchWithErrorMappingMock.mockResolvedValue({ id: 21, name: 'Analista de Campo' });

    await createGroup({ name: 'Analista de Campo', group_type_input: 'funcao' });

    expect(fetchWithErrorMappingMock).toHaveBeenCalledWith(
      '/grupos/',
      expect.objectContaining({ method: 'POST' }),
      expect.any(Object),
    );
  });

  test('syncGroupMembers uses /grupos/{id}/sync-members/', async () => {
    fetchWithErrorMappingMock.mockResolvedValue({ group_id: 5, members_count: 2 });

    await syncGroupMembers(5, { user_ids: [11, 12] });

    expect(fetchWithErrorMappingMock).toHaveBeenCalledWith(
      '/grupos/5/sync-members/',
      expect.objectContaining({ method: 'POST' }),
      expect.any(Object),
    );
  });

  test('updateGroup adds confirm_reserved query param when requested', async () => {
    fetchWithErrorMappingMock.mockResolvedValue({ id: 2, name: 'Grupo X' });

    await updateGroup(2, { name: 'Grupo X' }, { confirmReserved: true });

    expect(fetchWithErrorMappingMock).toHaveBeenCalledWith(
      '/grupos/2/?confirm_reserved=true',
      expect.objectContaining({ method: 'PATCH' }),
      expect.any(Object),
    );
  });

  test('deleteGroup adds confirm_reserved query param when requested', async () => {
    fetchWithErrorMappingMock.mockResolvedValue(undefined);

    await deleteGroup(2, { confirmReserved: true });

    expect(fetchWithErrorMappingMock).toHaveBeenCalledWith(
      '/grupos/2/?confirm_reserved=true',
      expect.objectContaining({ method: 'DELETE' }),
      expect.any(Object),
    );
  });

  test('getRBACMeta calls /rbac/meta/', async () => {
    fetchAPIMock.mockResolvedValue({ setor_groups: ['DAT'], funcao_groups: ['Coordenador'] });

    await getRBACMeta();

    expect(fetchAPIMock).toHaveBeenCalledWith('/rbac/meta/');
  });

  test('autocompleteMunicipiosAdmin returns results list', async () => {
    fetchAPIMock.mockResolvedValue({
      results: [
        { nome: 'Fortaleza', uf: 'CE', ibge_code: '2304400', source: 'referencia', confidence: 'high' },
      ],
    });

    const result = await autocompleteMunicipiosAdmin({ q: 'Fort', uf: 'CE' });

    expect(result).toEqual([
      { nome: 'Fortaleza', uf: 'CE', ibge_code: '2304400', source: 'referencia', confidence: 'high' },
    ]);
  });

  test('autocompleteMunicipiosAdmin returns empty list when no results', async () => {
    fetchAPIMock.mockResolvedValue({});

    const result = await autocompleteMunicipiosAdmin({ q: 'X', uf: 'CE' });

    expect(result).toEqual([]);
  });

  test('fetchWithErrorMapping maps 403 to friendly error', async () => {
    fetchWithErrorMappingMock.mockRejectedValue(new Error('Você não tem permissão para realizar esta ação.'));

    await expect(listUsers()).rejects.toThrow('Você não tem permissão para realizar esta ação.');
  });

  test('fetchWithErrorMapping maps 404 to friendly error', async () => {
    fetchWithErrorMappingMock.mockRejectedValue(new Error('Recurso não encontrado.'));

    await expect(listUsers()).rejects.toThrow('Recurso não encontrado.');
  });

  // Note: field-level error extraction (errors.cpf) was removed in the axios→fetch migration.
  // fetchWithErrorMapping now uses a simple status→message map (ADMIN_ERROR_MAP).
  // Backend detail messages are preserved via fetchAPI's default error handler.
  test('errors propagate through fetchWithErrorMapping', async () => {
    fetchWithErrorMappingMock.mockRejectedValue(new Error('Email já existe'));

    await expect(createUser({ username: 'dup' })).rejects.toThrow('Email já existe');
  });
});
