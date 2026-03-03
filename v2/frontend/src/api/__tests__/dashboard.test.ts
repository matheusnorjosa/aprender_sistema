import { beforeEach, describe, expect, test, vi } from 'vitest'

const { fetchAPIMock } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
}))

vi.mock('../config', () => ({
  fetchAPI: fetchAPIMock,
}))

import { getDashboardOverview } from '../dashboard'

describe('dashboard API wrappers', () => {
  beforeEach(() => {
    fetchAPIMock.mockReset()
  })

  test('getDashboardOverview uses /dashboard/overview/', async () => {
    const response = {
      kpis: {
        eventos_futuros: 1,
        eventos_aprovados: 2,
        total_formadores: 3,
        aprovacoes_pendentes: 4,
      },
      por_fluxo: [],
      por_gerencia: [],
      top_coordenadores: [],
    }
    fetchAPIMock.mockResolvedValue(response)

    const result = await getDashboardOverview()

    expect(fetchAPIMock).toHaveBeenCalledWith('/dashboard/overview/')
    expect(result).toEqual(response)
  })
})
