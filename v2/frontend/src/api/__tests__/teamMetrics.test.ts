import { beforeEach, describe, expect, test, vi } from 'vitest'

const { fetchAPIMock, buildUrlMock } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
  buildUrlMock: vi.fn(),
}))

vi.mock('../config', () => ({
  fetchAPI: fetchAPIMock,
  buildUrl: buildUrlMock,
}))

import { getTeamProductivity, getTeamFormadores, getTeamQuality } from '../teamMetrics'

describe('teamMetrics API wrappers', () => {
  beforeEach(() => {
    fetchAPIMock.mockReset()
    buildUrlMock.mockReset()
    buildUrlMock.mockImplementation((path: string) => path)
  })

  test('getTeamProductivity builds URL and fetches data', async () => {
    fetchAPIMock.mockResolvedValue({ period: '7d', events_created: 10 })

    await getTeamProductivity(7)

    expect(buildUrlMock).toHaveBeenCalledWith('/metrics/team/productivity/', { days: 7 })
    expect(fetchAPIMock).toHaveBeenCalledWith('/metrics/team/productivity/')
  })

  test('getTeamFormadores builds URL and fetches data', async () => {
    fetchAPIMock.mockResolvedValue({ period: '7d', formadores: [] })

    await getTeamFormadores(7)

    expect(buildUrlMock).toHaveBeenCalledWith('/metrics/team/formadores/', { days: 7 })
    expect(fetchAPIMock).toHaveBeenCalledWith('/metrics/team/formadores/')
  })

  test('getTeamQuality builds URL and fetches data', async () => {
    fetchAPIMock.mockResolvedValue({ period: '7d', rejection_rate: 0 })

    await getTeamQuality(7)

    expect(buildUrlMock).toHaveBeenCalledWith('/metrics/team/quality/', { days: 7 })
    expect(fetchAPIMock).toHaveBeenCalledWith('/metrics/team/quality/')
  })
})
