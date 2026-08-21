import type { ID } from '../../types'

export interface MapMunicipioMetric {
  municipio: string
  uf: string
  projetos: number
  eventos: number
  coordenadores: number
  compras?: number
  latitude: number
  longitude: number
}

export interface MapUfMetric {
  uf: string
  eventos: number
  projetos: number
  coordenadores: number
  municipios: number
  compras?: number
}

export interface MapMetricsResponse {
  by_municipio: MapMunicipioMetric[]
  by_uf?: MapUfMetric[]
}

export interface MunicipioDataType {
  municipio: string
  uf: string
  projetos: number
  eventos: number
  coordenadores: number
  compras: number
  coords: [number, number]
}

export interface EstadoAgregadoType {
  uf: string
  eventos: number
  projetos: number
  coordenadores: number
  compras: number
  municipios: string[]
  municipiosTotal: number
}

export type EstadosDataType = Record<string, EstadoAgregadoType>

export interface MapQueryParams {
  projeto_id?: ID
  data_inicio?: string
  data_fim?: string
}

export function normalizeMapMetricsResponse(response: MapMetricsResponse): {
  municipios: MunicipioDataType[]
  estados: EstadosDataType
} {
  const municipios: MunicipioDataType[] = (response.by_municipio || []).map((item) => ({
    municipio: item.municipio,
    uf: item.uf,
    projetos: item.projetos,
    eventos: item.eventos,
    coordenadores: item.coordenadores,
    compras: item.compras || 0,
    coords: [item.latitude, item.longitude] as [number, number],
  }))

  const municipiosPorUf = new Map<string, Set<string>>()
  municipios.forEach((item) => {
    const key = item.uf
    if (!municipiosPorUf.has(key)) {
      municipiosPorUf.set(key, new Set())
    }
    municipiosPorUf.get(key)!.add(item.municipio)
  })

  const estados: EstadosDataType = {}
  if (response.by_uf && response.by_uf.length > 0) {
    response.by_uf.forEach((item) => {
      const municipiosNomes = Array.from(municipiosPorUf.get(item.uf) || []).sort((a, b) => a.localeCompare(b))
      estados[item.uf] = {
        uf: item.uf,
        eventos: item.eventos,
        projetos: item.projetos,
        coordenadores: item.coordenadores,
        compras: item.compras || 0,
        municipios: municipiosNomes,
        municipiosTotal: item.municipios,
      }
    })
    return { municipios, estados }
  }

  // Fallback para contratos antigos sem by_uf.
  municipios.forEach((item) => {
    let estado = estados[item.uf]
    if (!estado) {
      estado = {
        uf: item.uf,
        eventos: 0,
        projetos: 0,
        coordenadores: 0,
        compras: 0,
        municipios: [],
        municipiosTotal: 0,
      }
      estados[item.uf] = estado
    }
    estado.eventos += item.eventos
    estado.projetos += item.projetos
    estado.coordenadores += item.coordenadores
    estado.compras += item.compras
    if (!estado.municipios.includes(item.municipio)) {
      estado.municipios.push(item.municipio)
      estado.municipiosTotal = estado.municipios.length
    }
  })

  return { municipios, estados }
}
