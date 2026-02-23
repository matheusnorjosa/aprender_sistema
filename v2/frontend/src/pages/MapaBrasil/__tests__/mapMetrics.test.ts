import { describe, expect, test } from 'vitest'

import { normalizeMapMetricsResponse } from '../mapMetrics'

describe('normalizeMapMetricsResponse', () => {
  test('deve priorizar by_uf para evitar dupla agregacao no frontend', () => {
    const payload = {
      by_municipio: [
        {
          municipio: 'Fortaleza',
          uf: 'CE',
          projetos: 2,
          eventos: 5,
          coordenadores: 1,
          compras: 2,
          latitude: -3.71,
          longitude: -38.54,
        },
        {
          municipio: 'Sobral',
          uf: 'CE',
          projetos: 1,
          eventos: 3,
          coordenadores: 1,
          compras: 1,
          latitude: -3.69,
          longitude: -40.34,
        },
      ],
      by_uf: [
        {
          uf: 'CE',
          eventos: 8,
          projetos: 2,
          coordenadores: 1,
          municipios: 2,
          compras: 3,
        },
      ],
    }

    const normalized = normalizeMapMetricsResponse(payload)

    expect(normalized.estados.CE.eventos).toBe(8)
    expect(normalized.estados.CE.projetos).toBe(2)
    expect(normalized.estados.CE.coordenadores).toBe(1)
    expect(normalized.estados.CE.compras).toBe(3)
    expect(normalized.estados.CE.municipiosTotal).toBe(2)
    expect(normalized.estados.CE.municipios).toEqual(['Fortaleza', 'Sobral'])
  })

  test('deve manter fallback para payload legado sem by_uf', () => {
    const payload = {
      by_municipio: [
        {
          municipio: 'Fortaleza',
          uf: 'CE',
          projetos: 2,
          eventos: 5,
          coordenadores: 1,
          compras: 2,
          latitude: -3.71,
          longitude: -38.54,
        },
        {
          municipio: 'São Paulo',
          uf: 'SP',
          projetos: 1,
          eventos: 4,
          coordenadores: 2,
          compras: 7,
          latitude: -23.55,
          longitude: -46.63,
        },
      ],
    }

    const normalized = normalizeMapMetricsResponse(payload)

    expect(normalized.estados.CE.eventos).toBe(5)
    expect(normalized.estados.CE.compras).toBe(2)
    expect(normalized.estados.CE.municipiosTotal).toBe(1)
    expect(normalized.estados.SP.eventos).toBe(4)
    expect(normalized.estados.SP.compras).toBe(7)
    expect(normalized.estados.SP.municipiosTotal).toBe(1)
  })
})
