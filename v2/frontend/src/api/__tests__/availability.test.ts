import { beforeEach, describe, expect, test, vi } from 'vitest'

const { fetchAPIMock, buildUrlMock } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
  buildUrlMock: vi.fn(),
}))

vi.mock('../config', () => ({
  fetchAPI: fetchAPIMock,
  buildUrl: buildUrlMock,
}))

import { getMe } from '../availability'

const validCurrentUserPayload = {
  id: 1,
  username: 'admin',
  email: 'admin@test.com',
  first_name: 'Admin',
  last_name: 'User',
  name: 'Admin User',
  groups: ['DAT'],
  setores: ['DAT'],
  funcoes: ['Coordenador'],
  is_superuser: true,
  is_superintendencia: false,
  can_approve_super: true,
}

describe('availability API - current user contract', () => {
  beforeEach(() => {
    fetchAPIMock.mockReset()
    buildUrlMock.mockReset()
    buildUrlMock.mockImplementation((path: string) => path)
  })

  test('getMe returns data when /api/me payload matches contract', async () => {
    fetchAPIMock.mockResolvedValue(validCurrentUserPayload)

    const user = await getMe()

    expect(fetchAPIMock).toHaveBeenCalledWith('/me/')
    expect(user).toEqual(validCurrentUserPayload)
  })

  test('getMe throws when /api/me payload drifts from expected shape', async () => {
    fetchAPIMock.mockResolvedValue({
      id: 1,
      username: 'admin',
      // missing mandatory contract fields
    })

    await expect(getMe()).rejects.toThrow('Invalid /api/me payload shape')
  })
})
