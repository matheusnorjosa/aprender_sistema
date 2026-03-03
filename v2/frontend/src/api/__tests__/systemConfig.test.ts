import { beforeEach, describe, expect, test, vi } from 'vitest'

const { fetchAPIMock } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
}))

vi.mock('../config', () => ({
  fetchAPI: fetchAPIMock,
}))

import { getSystemConfig, updateSystemConfig } from '../systemConfig'

describe('systemConfig API wrappers', () => {
  beforeEach(() => {
    fetchAPIMock.mockReset()
  })

  test('getSystemConfig calls /config/', async () => {
    fetchAPIMock.mockResolvedValue({ TRAVEL_BUFFER_MINUTES: 120 })

    const result = await getSystemConfig()

    expect(fetchAPIMock).toHaveBeenCalledWith('/config/')
    expect(result).toEqual({ TRAVEL_BUFFER_MINUTES: 120 })
  })

  test('updateSystemConfig sends PUT /config/ with JSON body', async () => {
    const payload = { TRAVEL_BUFFER_MINUTES: 90 }
    fetchAPIMock.mockResolvedValue(payload)

    const result = await updateSystemConfig(payload)

    expect(fetchAPIMock).toHaveBeenCalledWith('/config/', {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
    expect(result).toEqual(payload)
  })
})
