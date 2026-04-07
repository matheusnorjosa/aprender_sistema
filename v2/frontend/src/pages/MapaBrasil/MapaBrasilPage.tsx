/**
 * Página de Mapa do Brasil Interativo
 *
 * Design: paginamapadobrasil/screen.png
 * - Mapa do Brasil com visualização de eventos por município (usando Leaflet + GeoJSON)
 * - Filtros por projeto e intervalo de datas
 * - Estatísticas: Projetos por Município e Eventos + Coordenadores
 * - Toggle Map/List view
 *
 * Estilo: SimpleMaps (flat, clean, hover escurece preenchimento, bordas fixas)
 */

import { useState, useEffect, useRef, useCallback, useMemo, MutableRefObject, ChangeEvent, JSX } from 'react';
import {
  Card,
  Row,
  Col,
  Input,
  Select,
  DatePicker,
  Button,
  Table,
  List,
  Typography,
  Space,
  Collapse,
  Radio,
  Tag,
  Alert,
  message,
  Statistic,
  Divider,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { RadioChangeEvent } from 'antd/es/radio';
import type { Dayjs } from 'dayjs';
import {
  SearchOutlined,
  FilterOutlined,
  EnvironmentOutlined,
  FullscreenOutlined,
} from '@ant-design/icons';
import { MapContainer, GeoJSON, useMap } from 'react-leaflet';
import type { Map as LeafletMap, Layer, GeoJSON as LeafletGeoJSON, PathOptions, LatLngBounds } from 'leaflet';
import type { Feature, Geometry, FeatureCollection } from 'geojson';
import 'leaflet/dist/leaflet.css';
import { fetchAPI, buildUrl, type QueryParams } from '../../api/config';
import logger from '../../utils/logger';
import type { ID } from '../../types';
import {
  normalizeMapMetricsResponse,
  type EstadoAgregadoType,
  type EstadosDataType,
  type MapMetricsResponse,
  type MapQueryParams,
  type MunicipioDataType,
} from './mapMetrics';

const { Title, Text } = Typography;
const { Panel } = Collapse;

/** View mode type */
type ViewMode = 'map' | 'list';

/** Projeto type */
interface ProjetoType {
  id: ID | null;
  nome: string;
}

/** Coordenador projeto type */
interface CoordenadorProjetoType {
  nome: string;
  eventos: number;
}

/** Coordenador municipio type */
interface CoordenadorMunicipioType {
  nome: string;
  eventos: number;
}

/** Coordenador data type */
interface CoordenadorDataType {
  id: ID;
  nome: string;
  eventos: number;
  projetos: CoordenadorProjetoType[];
  municipios: CoordenadorMunicipioType[];
}

/** Estado table row type */
interface EstadoTableRowType extends EstadoAgregadoType {
  uf: string;
}

/** GeoJSON feature properties */
interface StateFeatureProperties {
  name: string;
  sigla: string;
}

/** Layer event types */
interface LayerMouseEvent {
  target: LayerWithPath;
  originalEvent?: MouseEvent;
}

/** Layer with path */
interface LayerWithPath {
  feature?: Feature<Geometry, StateFeatureProperties>;
  _path?: HTMLElement & { classList: DOMTokenList; getBoundingClientRect: () => DOMRect };
  setStyle: (style: PathOptions) => void;
  bringToFront: () => void;
  bindTooltip: (content: string, options?: Record<string, unknown>) => void;
  getTooltip: () => { getElement: () => HTMLElement | null } | null;
  on: (events: Record<string, (e: LayerMouseEvent) => void>) => void;
  getBounds: () => LatLngBounds;
}

/** GeoJSON ref type */
interface GeoJSONRefType {
  eachLayer: (fn: (layer: LayerWithPath) => void) => void;
}

/** Map controller props */
interface MapControllerProps {
  mapRef: MutableRefObject<LeafletMap | null>;
}

// Componente para capturar a instância do mapa
function MapController({ mapRef }: MapControllerProps): null {
  const map = useMap();
  useEffect(() => {
    mapRef.current = map;
  }, [map, mapRef]);
  return null;
}

// Cores do mapa - Estilo SimpleMaps (flat, clean)
const COLORS = {
  withEvents: '#4CAF50',      // Verde médio - estados com eventos
  withoutEvents: '#A5D6A7',   // Verde claro - estados sem eventos
  hover: '#66BB6A',           // Verde hover (mais claro que withEvents)
  selected: '#2196F3',        // Azul - selecionado
  dimmed: '#E8F5E9',          // Verde muito claro - não selecionados
  border: '#ffffff',          // Branco - bordas
  borderHover: '#388E3C',     // Verde escuro - borda no hover
};

export default function MapaBrasilPage(): JSX.Element {
  const [viewMode, setViewMode] = useState<ViewMode>('map');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedProjeto, setSelectedProjeto] = useState<ID | null>(null);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedState, setSelectedState] = useState<string | null>(null);
  // Removido hoveredState - hover controlado apenas por CSS (estilo SimpleMaps)
  const [brazilGeoJSON, setBrazilGeoJSON] = useState<FeatureCollection<Geometry, StateFeatureProperties> | null>(null);
  const [geoJsonLoading, setGeoJsonLoading] = useState<boolean>(true);

  // Estados para dados da API
  const [municipiosData, setMunicipiosData] = useState<MunicipioDataType[]>([]);
  const [estadosData, setEstadosData] = useState<EstadosDataType>({});
  const [projetos, setProjetos] = useState<ProjetoType[]>([]);
  const [coordenadoresData, setCoordenadoresData] = useState<CoordenadorDataType[]>([]);
  const [loadingCoordinators, setLoadingCoordinators] = useState<boolean>(false);
  const [appliedMapFilters, setAppliedMapFilters] = useState<MapQueryParams>({});

  // Refs
  const mapRef = useRef<LeafletMap | null>(null);
  const geoJsonRef = useRef<GeoJSONRefType | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);

  // Tooltip state for hover popup (estilo SimpleMaps)
  const [hoverTooltip, setHoverTooltip] = useState<{
    visible: boolean;
    name: string;
    x: number;
    y: number;
  }>({ visible: false, name: '', x: 0, y: 0 });

  // Lazy load do GeoJSON para reduzir bundle size
  useEffect(() => {
    import('../../data/brazil-states.json')
      .then((module) => {
        setBrazilGeoJSON(module.default as FeatureCollection<Geometry, StateFeatureProperties>);
        setGeoJsonLoading(false);
      })
      .catch((err) => {
        logger.error('Erro ao carregar GeoJSON:', err);
        setGeoJsonLoading(false);
      });
  }, []);

  // Limpar seleção ao clicar fora do mapa
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent): void => {
      if (
        selectedState &&
        mapContainerRef.current &&
        !mapContainerRef.current.contains(event.target as Node)
      ) {
        // Verificar se o clique não foi no card de detalhes
        const detailCard = document.querySelector('.state-detail-card');
        if (detailCard && detailCard.contains(event.target as Node)) {
          return;
        }
        handleResetSelection();
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [selectedState]);

  // Fetch projetos no mount
  useEffect(() => {
    const fetchProjetos = async (): Promise<void> => {
      try {
        const data = await fetchAPI<{ results: Array<{ id: ID | null; nome: string }> }>(buildUrl('/projetos/', { page_size: 100 }));
        setProjetos([{ id: null, nome: 'Todos os Projetos' }, ...(data.results || [])]);
      } catch (err) {
        logger.error('Erro ao carregar projetos:', err);
      }
    };
    fetchProjetos();
  }, []);

  // Fetch dados do mapa no mount
  useEffect(() => {
    fetchMapData();
  }, []);

  const buildCurrentMapParams = (): MapQueryParams => {
    const params: MapQueryParams = {};
    if (selectedProjeto) params.projeto_id = selectedProjeto;
    if (dateRange?.[0]) params.data_inicio = dateRange[0].format('YYYY-MM-DD');
    if (dateRange?.[1]) params.data_fim = dateRange[1].format('YYYY-MM-DD');
    return params;
  };

  const fetchMapData = async (forcedParams?: MapQueryParams): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const params = forcedParams ?? buildCurrentMapParams();

      const data = await fetchAPI<MapMetricsResponse>(buildUrl('/metrics/map/', params as QueryParams));
      const normalized = normalizeMapMetricsResponse(data);

      setAppliedMapFilters(params);
      setMunicipiosData(normalized.municipios);
      setEstadosData(normalized.estados);

    } catch (err) {
      logger.error('Erro ao buscar dados do mapa:', err);
      setError('Erro ao carregar dados. Tente novamente.');
      message.error('Erro ao carregar dados do mapa');
      setMunicipiosData([]);
      setEstadosData({});
    } finally {
      setLoading(false);
    }
  };

  // Fetch coordenadores para um estado específico
  const fetchCoordinators = async (uf: string, filters: MapQueryParams): Promise<void> => {
    if (!uf) {
      setCoordenadoresData([]);
      return;
    }

    setLoadingCoordinators(true);
    try {
      const data = await fetchAPI<{ coordenadores: CoordenadorDataType[] }>(buildUrl('/metrics/map/coordinators/', { uf, ...filters } as QueryParams));
      setCoordenadoresData(data.coordenadores || []);
    } catch (err) {
      logger.error('Erro ao buscar coordenadores:', err);
      setCoordenadoresData([]);
    } finally {
      setLoadingCoordinators(false);
    }
  };

  // Quando selectedState muda, buscar coordenadores
  useEffect(() => {
    if (selectedState) {
      fetchCoordinators(selectedState, appliedMapFilters);
    } else {
      setCoordenadoresData([]);
    }
  }, [selectedState, appliedMapFilters]);

  const handleApplyFilters = (): void => {
    fetchMapData();
  };

  const handleClearFilters = (): void => {
    setSelectedProjeto(null);
    setDateRange(null);
    setSearchTerm('');
    fetchMapData({});
  };

  // Função para resetar a seleção do estado com zoom de volta
  const handleResetSelection = (): void => {
    setSelectedState(null);
    if (mapRef.current) {
      mapRef.current.flyTo([-15.5, -54.0], 4, {
        duration: 0.8,
      });
    }
  };

  // Calcular estilo do estado - estilo SimpleMaps (flat, clean)
  // Hover é controlado apenas por CSS, não por React state
  const getStateStyle = useCallback((sigla: string): PathOptions => {
    const hasEvents = estadosData[sigla]?.eventos > 0;

    // Estado selecionado - borda branca mantida, só cor de preenchimento muda
    if (selectedState === sigla) {
      return {
        fillColor: COLORS.selected,
        fillOpacity: 0.9,
        color: COLORS.border,  // Borda branca fixa
        weight: 2,
      };
    }

    // Quando há um estado selecionado, outros ficam dimmed
    if (selectedState && selectedState !== sigla) {
      return {
        fillColor: hasEvents ? COLORS.withEvents : COLORS.withoutEvents,
        fillOpacity: 0.5,
        color: COLORS.border,  // Borda branca fixa
        weight: 2,
      };
    }

    // Estado normal - hover será via CSS
    return {
      fillColor: hasEvents ? COLORS.withEvents : COLORS.withoutEvents,
      fillOpacity: 1,
      color: COLORS.border,
      weight: 2,  // Borda mais grossa para separação visual
    };
  }, [estadosData, selectedState]);

  // Atualizar estilos quando seleção muda (não no hover - hover é CSS puro)
  useEffect(() => {
    if (geoJsonRef.current) {
      geoJsonRef.current.eachLayer((layer: LayerWithPath) => {
        const sigla = layer.feature?.properties?.sigla;
        if (sigla) {
          layer.setStyle(getStateStyle(sigla));

          // Gerenciar classes CSS para animações
          if (layer._path) {
            if (selectedState === sigla) {
              layer._path.classList.add('selected-state');
              layer._path.classList.remove('dimmed-state');
              layer.bringToFront();
            } else if (selectedState) {
              layer._path.classList.remove('selected-state');
              layer._path.classList.add('dimmed-state');
            } else {
              layer._path.classList.remove('selected-state');
              layer._path.classList.remove('dimmed-state');
            }
          }
        }
      });
    }
  }, [selectedState, getStateStyle]);

  const onEachFeature = useCallback((feature: Feature<Geometry, StateFeatureProperties>, layer: Layer): void => {
    const typedLayer = layer as unknown as LayerWithPath;
    if (feature.properties && feature.properties.name) {
      const sigla = feature.properties.sigla;
      const stateName = feature.properties.name;

      // Label permanente com a sigla do estado
      typedLayer.bindTooltip(sigla, {
        permanent: true,
        direction: 'center',
        className: 'state-label',
      });

      // Eventos de interação (estilo SimpleMaps)
      typedLayer.on({
        // Hover: mostra tooltip com nome completo do estado
        mouseover: (e: { target: LayerWithPath }) => {
          const layerElement = e.target._path;
          if (layerElement) {
            const rect = layerElement.getBoundingClientRect();
            setHoverTooltip({
              visible: true,
              name: stateName,
              x: rect.left + rect.width / 2,
              y: rect.top - 10,
            });
          }
        },
        mousemove: (e: { originalEvent?: MouseEvent }) => {
          if (e.originalEvent) {
            setHoverTooltip(prev => ({
              ...prev,
              x: e.originalEvent!.clientX,
              y: e.originalEvent!.clientY - 35,
            }));
          }
        },
        mouseout: () => {
          setHoverTooltip(prev => ({ ...prev, visible: false }));
        },
        // Click: zoom animado para o estado
        click: () => {
          if (selectedState === sigla) {
            // Desselecionar e voltar para view inicial
            setSelectedState(null);
            if (mapRef.current) {
              mapRef.current.flyTo([-15.5, -54.0], 4, {
                duration: 0.8,
              });
            }
          } else {
            // Selecionar e fazer zoom para o estado
            setSelectedState(sigla);
            const bounds = typedLayer.getBounds();
            if (mapRef.current && bounds && bounds.isValid()) {
              mapRef.current.flyToBounds(bounds, {
                padding: [80, 80],
                maxZoom: 6,
                duration: 0.8,
              });
            }
          }
        },
      });
    }
  }, [selectedState]);

  // Key única para forçar re-render do GeoJSON quando dados mudam
  // NÃO incluir selectedState aqui - atualização de seleção é via setStyle(), não re-render
  const geoJsonKey = useMemo(() =>
    `geojson-${Object.keys(estadosData).length}`,
    [estadosData]
  );

  // Columns for coordenadores table
  const coordenadoresColumns: ColumnsType<CoordenadorDataType> = [
    {
      title: 'Coordenador',
      dataIndex: 'nome',
      key: 'nome',
      render: (nome: string) => <Text strong>{nome}</Text>,
    },
    {
      title: 'Eventos',
      dataIndex: 'eventos',
      key: 'eventos',
      align: 'center',
      sorter: (a, b) => a.eventos - b.eventos,
      defaultSortOrder: 'descend',
      render: (v: number) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: 'Projetos (eventos)',
      dataIndex: 'projetos',
      key: 'projetos',
      render: (projetos: CoordenadorProjetoType[]) => (
        <Space wrap size={[4, 4]}>
          {projetos.map((p, idx) => (
            <Tag key={idx} color="purple" style={{ margin: 0 }}>
              {p.nome}: <strong>{p.eventos}</strong>
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'Municípios (eventos)',
      dataIndex: 'municipios',
      key: 'municipios',
      render: (municipios: CoordenadorMunicipioType[]) => (
        <Space wrap size={[4, 4]}>
          {municipios.map((m, idx) => (
            <Tag key={idx} color="green" style={{ margin: 0 }}>
              {m.nome}: <strong>{m.eventos}</strong>
            </Tag>
          ))}
        </Space>
      ),
    },
  ];

  // Columns for municipios table
  const municipiosColumns: ColumnsType<MunicipioDataType> = [
    {
      title: 'Município',
      dataIndex: 'municipio',
      key: 'municipio',
    },
    {
      title: 'Eventos',
      dataIndex: 'eventos',
      key: 'eventos',
      align: 'center',
      render: (v: number) => <Tag color="blue">{v}</Tag>,
    },
    {
      title: 'Coordenadores',
      dataIndex: 'coordenadores',
      key: 'coordenadores',
      align: 'center',
      render: (v: number) => <Tag color="green">{v}</Tag>,
    },
    {
      title: 'Projetos',
      dataIndex: 'projetos',
      key: 'projetos',
      align: 'center',
      render: (v: number) => <Tag color="purple">{v}</Tag>,
    },
    {
      title: 'Compras',
      dataIndex: 'compras',
      key: 'compras',
      align: 'center',
      render: (v: number) => <Tag color="orange">{v}</Tag>,
    },
  ];

  // Columns for estados table
  const estadosColumns: ColumnsType<EstadoTableRowType> = [
    {
      title: 'Estado',
      dataIndex: 'uf',
      key: 'uf',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: 'Municípios',
      dataIndex: 'municipiosTotal',
      key: 'municipiosTotal',
      align: 'center',
      render: (total: number) => total,
    },
    {
      title: 'Eventos',
      dataIndex: 'eventos',
      key: 'eventos',
      align: 'center',
      render: (eventos: number) => <Tag color="blue">{eventos}</Tag>,
    },
    {
      title: 'Coordenadores',
      dataIndex: 'coordenadores',
      key: 'coordenadores',
      align: 'center',
      render: (coord: number) => <Tag color="green">{coord}</Tag>,
    },
    {
      title: 'Compras',
      dataIndex: 'compras',
      key: 'compras',
      align: 'center',
      render: (compras: number) => <Tag color="orange">{compras}</Tag>,
    },
  ];

  return (
    <div className="p-6 bg-gray-100" style={{ minHeight: '100vh' }}>
      {/* Header */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <Title level={2} style={{ marginBottom: 0 }}>
            <EnvironmentOutlined style={{ marginRight: 8 }} />
            Mapa de Eventos
          </Title>
          <Text type="secondary">Visualização geográfica do Brasil</Text>
        </div>
        <Radio.Group value={viewMode} onChange={(e: RadioChangeEvent) => setViewMode(e.target.value)} buttonStyle="solid">
          <Radio.Button value="map">Mapa</Radio.Button>
          <Radio.Button value="list">Lista</Radio.Button>
        </Radio.Group>
      </div>

      {/* Busca */}
      <Card style={{ marginBottom: 16 }}>
        <Input
          size="large"
          placeholder="Buscar por localização"
          prefix={<SearchOutlined />}
          value={searchTerm}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
          allowClear
        />
      </Card>

      <Row gutter={16}>
        {/* Filtros Laterais */}
        <Col xs={24} md={6}>
          <Card title={<Space><FilterOutlined />Filtros</Space>} style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* Filtro de Projeto */}
              <Collapse defaultActiveKey={['1', '2']} ghost>
                <Panel header="Projeto" key="1">
                  <Select
                    style={{ width: '100%' }}
                    value={selectedProjeto}
                    onChange={setSelectedProjeto}
                    options={projetos.map((p) => ({ label: p.nome, value: p.id }))}
                    loading={projetos.length === 0}
                  />
                </Panel>

                {/* Filtro de Data */}
                <Panel header="Intervalo de Datas" key="2">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>Data Inicial</Text>
                    <DatePicker
                      style={{ width: '100%' }}
                      placeholder="mm/dd/yyyy"
                      format="DD/MM/YYYY"
                      value={dateRange?.[0]}
                      onChange={(date) => setDateRange([date, dateRange?.[1] || null])}
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>Data Final</Text>
                    <DatePicker
                      style={{ width: '100%' }}
                      placeholder="mm/dd/yyyy"
                      format="DD/MM/YYYY"
                      value={dateRange?.[1]}
                      onChange={(date) => setDateRange([dateRange?.[0] || null, date])}
                    />
                  </Space>
                </Panel>
              </Collapse>

              {/* Botões de Ação */}
              <Button type="primary" block onClick={handleApplyFilters} loading={loading}>
                Aplicar Filtros
              </Button>
              <Button block onClick={handleClearFilters}>
                Limpar Filtros
              </Button>
            </Space>
          </Card>
        </Col>

        {/* Área Principal */}
        <Col xs={24} md={18}>
          {/* Alert de erro */}
          {error && (
            <Alert
              message="Erro"
              description={error}
              type="error"
              showIcon
              closable
              onClose={() => setError(null)}
              style={{ marginBottom: 16 }}
            />
          )}

          {viewMode === 'map' ? (
            <>
            <Card style={{ marginBottom: 16 }} loading={loading || geoJsonLoading}>
              {/* Mapa Leaflet com GeoJSON - Estilo SimpleMaps */}
              <div
                ref={mapContainerRef}
                style={{
                  height: '550px',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  background: '#f5f5f5',
                  position: 'relative',
                  border: '1px solid #e0e0e0',
                }}
              >
                {/* CSS estilo SimpleMaps - flat, clean, animações suaves */}
                <style>{`
                  /* Labels dos estados - estilo SimpleMaps */
                  .state-label {
                    background: transparent !important;
                    border: none !important;
                    box-shadow: none !important;
                    color: #444 !important;
                    font-weight: 600 !important;
                    font-size: 10px !important;
                    text-shadow:
                      1px 1px 0 #fff,
                      -1px -1px 0 #fff,
                      1px -1px 0 #fff,
                      -1px 1px 0 #fff !important;
                    letter-spacing: 0.5px !important;
                    pointer-events: none !important;
                  }
                  .state-label::before {
                    display: none !important;
                  }

                  /* Container do mapa */
                  .leaflet-container {
                    background: #f8f9fa !important;
                    border-radius: 8px;
                  }

                  /* Estados - estilo SimpleMaps com transição suave */
                  .leaflet-interactive {
                    transition: filter 0.3s ease, stroke 0.3s ease, stroke-width 0.3s ease !important;
                    cursor: pointer !important;
                    stroke-linecap: round !important;
                    stroke-linejoin: round !important;
                  }

                  /* Hover - apenas escurece o preenchimento, bordas ficam fixas (estilo SimpleMaps) */
                  .leaflet-interactive:hover:not(.selected-state):not(.dimmed-state) {
                    filter: brightness(0.85) !important;
                    /* Bordas NÃO mudam no hover - ficam brancas e fixas */
                  }

                  /* Estado selecionado - bordas brancas fixas */
                  .leaflet-interactive.selected-state {
                    filter: brightness(1) !important;
                    /* Bordas brancas mantidas - não mudam */
                  }

                  /* Estados não selecionados quando há seleção - ficam "apagados" */
                  .leaflet-interactive.dimmed-state {
                    filter: brightness(0.7) saturate(0.5) !important;
                  }

                  /* Tooltip de hover - estilo SimpleMaps */
                  .state-hover-tooltip {
                    position: fixed;
                    background: #333;
                    color: #fff;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: 500;
                    pointer-events: none;
                    z-index: 9999;
                    white-space: nowrap;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
                    transform: translateX(-50%);
                    opacity: 0;
                    transition: opacity 0.15s ease;
                  }
                  .state-hover-tooltip.visible {
                    opacity: 1;
                  }
                  .state-hover-tooltip::after {
                    content: '';
                    position: absolute;
                    top: 100%;
                    left: 50%;
                    transform: translateX(-50%);
                    border-width: 5px;
                    border-style: solid;
                    border-color: #333 transparent transparent transparent;
                  }
                `}</style>

                {/* Tooltip de hover com nome do estado - estilo SimpleMaps */}
                <div
                  className={`state-hover-tooltip ${hoverTooltip.visible ? 'visible' : ''}`}
                  style={{
                    left: hoverTooltip.x,
                    top: hoverTooltip.y,
                  }}
                >
                  {hoverTooltip.name}
                </div>

                {/* Botão para limpar seleção */}
                {selectedState && (
                  <Button
                    type="primary"
                    icon={<FullscreenOutlined />}
                    onClick={handleResetSelection}
                    style={{
                      position: 'absolute',
                      top: 10,
                      right: 10,
                      zIndex: 1000,
                      borderRadius: '8px',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    }}
                  >
                    Limpar Seleção
                  </Button>
                )}
                <MapContainer
                  center={[-15.5, -54.0]}
                  zoom={4}
                  minZoom={4}
                  maxZoom={7}
                  style={{ height: '100%', width: '100%', background: '#f8f9fa' }}
                  scrollWheelZoom={false}
                  zoomControl={false}
                  dragging={false}
                  doubleClickZoom={false}
                  touchZoom={false}
                >
                  {/* Controller para capturar referência do mapa */}
                  <MapController mapRef={mapRef} />

                  {/* GeoJSON layer for states */}
                  {brazilGeoJSON && (
                    <GeoJSON
                      key={geoJsonKey}
                      ref={geoJsonRef as unknown as React.Ref<LeafletGeoJSON>}
                      data={brazilGeoJSON}
                      onEachFeature={onEachFeature}
                      style={(feature) => {
                        const sigla = (feature?.properties as StateFeatureProperties)?.sigla;
                        return getStateStyle(sigla);
                      }}
                    />
                  )}

                </MapContainer>
              </div>
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Space direction="vertical" size="small">
                  {/* Legenda do mapa - estilo SimpleMaps */}
                  <Space split="|" size="middle">
                    <Text type="secondary">
                      <span style={{
                        display: 'inline-block',
                        width: 14,
                        height: 14,
                        background: COLORS.withEvents,
                        marginRight: 6,
                        borderRadius: '2px',
                        border: '1px solid #388E3C',
                        verticalAlign: 'middle',
                      }}></span>
                      Com eventos
                    </Text>
                    <Text type="secondary">
                      <span style={{
                        display: 'inline-block',
                        width: 14,
                        height: 14,
                        background: COLORS.withoutEvents,
                        marginRight: 6,
                        borderRadius: '2px',
                        border: '1px solid #81C784',
                        verticalAlign: 'middle',
                      }}></span>
                      Sem eventos
                    </Text>
                    <Text type="secondary">
                      <span style={{
                        display: 'inline-block',
                        width: 14,
                        height: 14,
                        background: COLORS.selected,
                        marginRight: 6,
                        borderRadius: '2px',
                        border: '1px solid #1565C0',
                        verticalAlign: 'middle',
                      }}></span>
                      Selecionado
                    </Text>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Clique em um estado para ver detalhes
                  </Text>
                </Space>
              </div>
            </Card>

            {/* Card de detalhes do estado selecionado */}
            {selectedState && estadosData[selectedState] && (
              <Card
                className="state-detail-card"
                title={
                  <Space>
                    <EnvironmentOutlined />
                    <span>Detalhes: {selectedState}</span>
                  </Space>
                }
                style={{ marginBottom: 16, borderRadius: '12px' }}
                extra={
                  <Button size="small" onClick={handleResetSelection}>
                    Fechar
                  </Button>
                }
              >
                <Row gutter={[16, 16]}>
                  {/* Estatísticas em destaque */}
                  <Col xs={12} md={6}>
                    <Statistic
                      title="Total de Eventos"
                      value={estadosData[selectedState].eventos}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic
                      title="Total de Projetos"
                      value={estadosData[selectedState].projetos}
                      valueStyle={{ color: '#722ed1' }}
                    />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic
                      title="Coordenadores"
                      value={estadosData[selectedState].coordenadores}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic
                      title="Compras"
                      value={estadosData[selectedState].compras}
                      valueStyle={{ color: '#fa8c16' }}
                    />
                  </Col>
                </Row>

                <Divider />

                {/* Detalhes por Coordenador */}
                <div style={{ marginBottom: 16 }}>
                  <Title level={5} style={{ marginBottom: 12 }}>
                    Eventos por Coordenador
                  </Title>
                  <Table
                    scroll={{ x: "max-content" }}
                    size="small"
                    loading={loadingCoordinators}
                    pagination={false}
                    dataSource={coordenadoresData}
                    rowKey="id"
                    columns={coordenadoresColumns}
                  />
                </div>

                <Divider />

                {/* Lista de municípios com eventos */}
                <div style={{ marginBottom: 16 }}>
                  <Title level={5} style={{ marginBottom: 12 }}>
                    Municípios com eventos ({estadosData[selectedState].municipiosTotal})
                  </Title>
                  <Space wrap>
                    {estadosData[selectedState].municipios.map((municipio, idx) => (
                      <Tag key={idx} color="green">{municipio}</Tag>
                    ))}
                  </Space>
                </div>

                <Divider />

                {/* Detalhes por município */}
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>
                    Detalhes por Município
                  </Title>
                  <Table
                    scroll={{ x: "max-content" }}
                    size="small"
                    pagination={false}
                    dataSource={municipiosData.filter(m => m.uf === selectedState)}
                    rowKey={(record) => `${record.municipio}-${record.uf}`}
                    columns={municipiosColumns}
                  />
                </div>
              </Card>
            )}
            </>
          ) : (
            <Card title="Lista de Municípios" style={{ marginBottom: 16, borderRadius: '12px' }} loading={loading}>
              <List
                dataSource={municipiosData}
                renderItem={(item) => (
                  <List.Item
                    extra={
                      <Space>
                        <Tag color="purple">{item.projetos} projetos</Tag>
                        <Tag color="blue">{item.eventos} eventos</Tag>
                        <Tag color="orange">{item.compras} compras</Tag>
                      </Space>
                    }
                  >
                    <List.Item.Meta
                      avatar={<EnvironmentOutlined className="text-2xl text-blue-500" />}
                      title={`${item.municipio}-${item.uf}`}
                      description={`${item.coordenadores} coordenadores`}
                    />
                  </List.Item>
                )}
              />
            </Card>
          )}

          {/* Estatísticas por Estado */}
          <Row gutter={[16, 16]}>
            {/* Eventos por Estado */}
            <Col xs={24} lg={12}>
              <Card title="Eventos por Estado" bordered={false} loading={loading} style={{ borderRadius: '12px' }}>
                <List
                  dataSource={Object.entries(estadosData).sort((a, b) => b[1].eventos - a[1].eventos)}
                  renderItem={([uf, data]) => (
                    <List.Item>
                      <div className="w-full flex justify-between">
                        <div>
                          <Text strong>{uf}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: 12 }}>{data.municipiosTotal} municípios</Text>
                        </div>
                        <Space>
                          <Tag color="blue">{data.eventos} Eventos</Tag>
                          <Tag color="purple">{data.projetos} Projetos</Tag>
                          <Tag color="orange">{data.compras} Compras</Tag>
                        </Space>
                      </div>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>

            {/* Detalhes por Estado */}
            <Col xs={24} lg={12}>
              <Card title="Detalhes por Estado" bordered={false} loading={loading} style={{ borderRadius: '12px' }}>
                <Table
                  scroll={{ x: "max-content" }}
                  dataSource={Object.values(estadosData)}
                  rowKey="uf"
                  pagination={false}
                  size="small"
                  columns={estadosColumns}
                />
              </Card>
            </Col>
          </Row>
        </Col>
      </Row>
    </div>
  );
}
