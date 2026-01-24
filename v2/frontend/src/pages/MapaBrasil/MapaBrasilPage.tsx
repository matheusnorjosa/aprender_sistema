/**
 * Página de Mapa do Brasil Interativo
 *
 * Design: paginamapadobrasil/screen.png
 * - Mapa do Brasil com visualização de eventos por município (usando Leaflet + GeoJSON)
 * - Filtros por projeto e intervalo de datas
 * - Estatísticas: Projetos por Município e Eventos + Coordenadores
 * - Toggle Map/List view
 */

import { useState, useEffect, useRef, useCallback, MutableRefObject, ChangeEvent, JSX } from 'react';
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
import type { Map as LeafletMap, Layer, GeoJSON as LeafletGeoJSON, PathOptions } from 'leaflet';
import type { Feature, Geometry, FeatureCollection } from 'geojson';
import 'leaflet/dist/leaflet.css';
import api from '../../api';
import logger from '../../utils/logger';
import type { ID } from '../../types';

const { Title, Text } = Typography;
const { Panel } = Collapse;

/** View mode type */
type ViewMode = 'map' | 'list';

/** Projeto type */
interface ProjetoType {
  id: ID | null;
  nome: string;
}

/** Municipio data type */
interface MunicipioDataType {
  municipio: string;
  uf: string;
  projetos: number;
  eventos: number;
  coordenadores: number;
  coords: [number, number];
}

/** Estado agregado type */
interface EstadoAgregadoType {
  uf: string;
  eventos: number;
  projetos: number;
  coordenadores: number;
  municipios: string[];
}

/** Estados data type */
type EstadosDataType = Record<string, EstadoAgregadoType>;

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

/** Layer with path */
interface LayerWithPath {
  feature?: Feature<Geometry, StateFeatureProperties>;
  _path?: HTMLElement & { classList: DOMTokenList };
  setStyle: (style: PathOptions) => void;
  bringToFront: () => void;
  bindTooltip: (content: string, options?: Record<string, unknown>) => void;
  on: (events: Record<string, (e: { target: LayerWithPath }) => void>) => void;
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


export default function MapaBrasilPage(): JSX.Element {
  const [viewMode, setViewMode] = useState<ViewMode>('map');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedProjeto, setSelectedProjeto] = useState<ID | null>(null);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [brazilGeoJSON, setBrazilGeoJSON] = useState<FeatureCollection<Geometry, StateFeatureProperties> | null>(null);
  const [geoJsonLoading, setGeoJsonLoading] = useState<boolean>(true);

  // Estados para dados da API
  const [municipiosData, setMunicipiosData] = useState<MunicipioDataType[]>([]);
  const [estadosData, setEstadosData] = useState<EstadosDataType>({});
  const [projetos, setProjetos] = useState<ProjetoType[]>([]);
  const [coordenadoresData, setCoordenadoresData] = useState<CoordenadorDataType[]>([]);
  const [loadingCoordinators, setLoadingCoordinators] = useState<boolean>(false);

  // Refs para usar em event handlers (evita stale closure)
  const selectedStateRef = useRef<string | null>(null);
  const estadosDataRef = useRef<EstadosDataType>({});
  const mapRef = useRef<LeafletMap | null>(null);
  const geoJsonRef = useRef<GeoJSONRefType | null>(null);
  const mapContainerRef = useRef<HTMLDivElement | null>(null);

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

  // Manter refs sincronizados com state
  useEffect(() => {
    selectedStateRef.current = selectedState;
  }, [selectedState]);

  useEffect(() => {
    estadosDataRef.current = estadosData;
  }, [estadosData]);

  // Limpar seleção ao clicar fora do mapa
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent): void => {
      if (
        selectedStateRef.current &&
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
  }, []);

  // Fetch projetos no mount
  useEffect(() => {
    const fetchProjetos = async (): Promise<void> => {
      try {
        const response = await api.get('/projetos/', { params: { page_size: 100 } });
        setProjetos([{ id: null, nome: 'Todos os Projetos' }, ...(response.data.results || [])]);
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

  const fetchMapData = async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      // Construir query params
      const params: Record<string, string | number> = {};
      if (selectedProjeto) params.projeto_id = selectedProjeto;
      if (dateRange?.[0]) params.data_inicio = dateRange[0].format('YYYY-MM-DD');
      if (dateRange?.[1]) params.data_fim = dateRange[1].format('YYYY-MM-DD');

      // Chamada à API
      const response = await api.get('/metrics/map/', { params });

      // Mapear resposta para formato esperado pelos markers
      const municipios: MunicipioDataType[] = response.data.by_municipio.map((item: { municipio: string; uf: string; projetos: number; eventos: number; coordenadores: number; latitude: number; longitude: number }) => ({
        municipio: item.municipio,
        uf: item.uf,
        projetos: item.projetos,
        eventos: item.eventos,
        coordenadores: item.coordenadores,
        coords: [item.latitude, item.longitude] as [number, number],
      }));

      // Agregar dados por estado (UF)
      const estadosAgregados: EstadosDataType = {};
      municipios.forEach(item => {
        if (!estadosAgregados[item.uf]) {
          estadosAgregados[item.uf] = {
            uf: item.uf,
            eventos: 0,
            projetos: 0,
            coordenadores: 0,
            municipios: [],
          };
        }
        estadosAgregados[item.uf].eventos += item.eventos;
        estadosAgregados[item.uf].projetos += item.projetos;
        estadosAgregados[item.uf].coordenadores += item.coordenadores;
        estadosAgregados[item.uf].municipios.push(item.municipio);
      });

      setMunicipiosData(municipios);
      setEstadosData(estadosAgregados);

    } catch (err) {
      logger.error('Erro ao buscar dados do mapa:', err);
      setError('Erro ao carregar dados. Tente novamente.');
      message.error('Erro ao carregar dados do mapa');
      setMunicipiosData([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch coordenadores para um estado específico
  const fetchCoordinators = async (uf: string): Promise<void> => {
    if (!uf) {
      setCoordenadoresData([]);
      return;
    }

    setLoadingCoordinators(true);
    try {
      const response = await api.get('/metrics/map/coordinators/', { params: { uf } });
      setCoordenadoresData(response.data.coordenadores || []);
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
      fetchCoordinators(selectedState);
    } else {
      setCoordenadoresData([]);
    }
  }, [selectedState]);

  const handleApplyFilters = (): void => {
    fetchMapData();
  };

  const handleClearFilters = (): void => {
    setSelectedProjeto(null);
    setDateRange(null);
    setSearchTerm('');
    fetchMapData();
  };

  // Função para obter estilo baseado se o estado tem eventos
  const getStateStyle = (sigla: string): PathOptions => {
    const hasEvents = estadosData[sigla] && estadosData[sigla].eventos > 0;
    return {
      fillColor: hasEvents ? '#2e7d32' : '#81c784',
      fillOpacity: 1,
      color: '#ffffff',
      weight: 1,
    };
  };

  // Estilo quando hover
  const hoverStyle: PathOptions = {
    fillColor: '#1b5e20',
    fillOpacity: 1,
    color: '#ffffff',
    weight: 2,
  };

  // Estilo quando selecionado (destacado "acima" do mapa - efeito de extração)
  const selectedStyle: PathOptions = {
    fillColor: '#1565c0',
    fillOpacity: 1,
    color: '#ffffff',
    weight: 3,
  };

  // Estilo dos estados não selecionados (levemente escurecidos)
  const dimmedStyle: PathOptions = {
    fillColor: '#a5d6a7',
    fillOpacity: 0.6,
    color: '#ffffff',
    weight: 1,
  };

  // Função para resetar a seleção do estado
  const handleResetSelection = (): void => {
    setSelectedState(null);
    selectedStateRef.current = null;
    // Resetar estilos de todos os estados baseado em se têm eventos
    if (geoJsonRef.current) {
      geoJsonRef.current.eachLayer((layer: LayerWithPath) => {
        const sigla = layer.feature?.properties?.sigla;
        if (sigla) {
          layer.setStyle(getStateStyle(sigla));
          // Remover classes de seleção e dimmed
          if (layer._path) {
            layer._path.classList.remove('selected-state');
            layer._path.classList.remove('dimmed-state');
          }
        }
      });
    }
  };

  const onEachFeature = useCallback((feature: Feature<Geometry, StateFeatureProperties>, layer: Layer): void => {
    const typedLayer = layer as unknown as LayerWithPath;
    if (feature.properties && feature.properties.name) {
      const sigla = feature.properties.sigla;

      // Label permanente com a sigla do estado (em branco)
      typedLayer.bindTooltip(sigla, {
        permanent: true,
        direction: 'center',
        className: 'state-label',
      });

      // Eventos de hover e click
      typedLayer.on({
        mouseover: (e: { target: LayerWithPath }) => {
          const targetLayer = e.target;
          const currentSelected = selectedStateRef.current;
          const layerSigla = targetLayer.feature?.properties?.sigla;

          // Se há um estado selecionado, não aplicar hover nos outros estados
          if (currentSelected && layerSigla !== currentSelected) {
            return;
          }

          // Aplicar hover apenas quando não há seleção ou é o estado selecionado
          if (!currentSelected) {
            targetLayer.setStyle(hoverStyle);
            targetLayer.bringToFront();
          }
        },
        mouseout: (e: { target: LayerWithPath }) => {
          const targetLayer = e.target;
          const layerSigla = targetLayer.feature?.properties?.sigla;
          const currentSelected = selectedStateRef.current;

          // Se há um estado selecionado, manter estilos apropriados
          if (layerSigla === currentSelected) {
            targetLayer.setStyle(selectedStyle);
          } else if (currentSelected) {
            // Não fazer nada - manter estilo dimmed
            return;
          } else if (layerSigla) {
            // Usar estilo baseado em se tem eventos
            const hasEvents = estadosDataRef.current[layerSigla]?.eventos > 0;
            targetLayer.setStyle({
              fillColor: hasEvents ? '#2e7d32' : '#81c784',
              fillOpacity: 1,
              color: '#ffffff',
              weight: 1,
            });
          }
        },
        click: (e: { target: LayerWithPath }) => {
          const clickedSigla = e.target.feature?.properties?.sigla;
          const currentSelected = selectedStateRef.current;

          if (!clickedSigla) return;

          // Toggle seleção
          if (currentSelected === clickedSigla) {
            // Desselecionar
            selectedStateRef.current = null;
            setSelectedState(null);
            if (geoJsonRef.current) {
              geoJsonRef.current.eachLayer((l: LayerWithPath) => {
                const lSigla = l.feature?.properties?.sigla;
                if (lSigla) {
                  const hasEvents = estadosDataRef.current[lSigla]?.eventos > 0;
                  l.setStyle({
                    fillColor: hasEvents ? '#2e7d32' : '#81c784',
                    fillOpacity: 1,
                    color: '#ffffff',
                    weight: 1,
                  });
                  // Remover classes de seleção e dimmed
                  if (l._path) {
                    l._path.classList.remove('selected-state');
                    l._path.classList.remove('dimmed-state');
                  }
                }
              });
            }
          } else {
            // Selecionar novo estado
            selectedStateRef.current = clickedSigla;
            setSelectedState(clickedSigla);

            // Atualizar estilos de todos os estados
            if (geoJsonRef.current) {
              geoJsonRef.current.eachLayer((l: LayerWithPath) => {
                const lSigla = l.feature?.properties?.sigla;
                if (lSigla === clickedSigla) {
                  l.setStyle(selectedStyle);
                  l.bringToFront();
                  // Adicionar classe para efeito de elevação
                  if (l._path) {
                    l._path.classList.add('selected-state');
                    l._path.classList.remove('dimmed-state');
                  }
                } else if (lSigla) {
                  l.setStyle(dimmedStyle);
                  // Adicionar classe dimmed e remover selected
                  if (l._path) {
                    l._path.classList.remove('selected-state');
                    l._path.classList.add('dimmed-state');
                  }
                }
              });
            }
          }
        },
      });
    }
  }, []);

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
      dataIndex: 'municipios',
      key: 'municipios',
      align: 'center',
      render: (municipios: string[]) => municipios.length,
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
              {/* Mapa Leaflet com GeoJSON (sem tiles de fundo) */}
              <div
                ref={mapContainerRef}
                style={{ height: '550px', borderRadius: '8px', overflow: 'hidden', background: '#e8f5e9', position: 'relative' }}
              >
                {/* CSS para labels dos estados e efeito de seleção */}
                <style>{`
                  .state-label {
                    background: transparent !important;
                    border: none !important;
                    box-shadow: none !important;
                    color: white !important;
                    font-weight: bold !important;
                    font-size: 11px !important;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8) !important;
                  }
                  .state-label::before {
                    display: none !important;
                  }
                  /* Efeito de elevação/extração para estado selecionado */
                  .leaflet-interactive.selected-state {
                    filter: drop-shadow(0 8px 16px rgba(0,0,0,0.4)) drop-shadow(0 4px 8px rgba(0,0,0,0.3));
                    transform: scale(1.05);
                    transform-origin: center;
                    transition: all 0.3s ease-out;
                  }
                  /* Estados não selecionados ficam mais "afundados" */
                  .leaflet-interactive.dimmed-state {
                    filter: brightness(0.85);
                    transition: all 0.3s ease-out;
                  }
                  /* Animação suave para todos os estados */
                  .leaflet-interactive {
                    transition: filter 0.3s ease-out, transform 0.3s ease-out;
                  }
                `}</style>

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
                    }}
                  >
                    Limpar Seleção
                  </Button>
                )}
                <MapContainer
                  center={[-15.5, -54.0]}
                  zoom={4}
                  minZoom={4}
                  maxZoom={4}
                  style={{ height: '100%', width: '100%', background: '#e8f5e9' }}
                  scrollWheelZoom={false}
                  zoomControl={false}
                  dragging={false}
                  doubleClickZoom={false}
                  touchZoom={false}
                >
                  {/* Controller para capturar referência do mapa */}
                  <MapController mapRef={mapRef} />

                  {/* GeoJSON layer for states - cores baseadas em eventos */}
                  {brazilGeoJSON && (
                    <GeoJSON
                      key={`geojson-${Object.keys(estadosData).length}`}
                      ref={geoJsonRef as unknown as React.Ref<LeafletGeoJSON>}
                      data={brazilGeoJSON}
                      onEachFeature={onEachFeature}
                      style={(feature) => {
                        const sigla = (feature?.properties as StateFeatureProperties)?.sigla;
                        const hasEvents = estadosData[sigla]?.eventos > 0;
                        return {
                          fillColor: hasEvents ? '#2e7d32' : '#81c784',
                          fillOpacity: 1,
                          color: '#ffffff',
                          weight: 1,
                        };
                      }}
                    />
                  )}

                </MapContainer>
              </div>
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Space direction="vertical" size="small">
                  {/* Legenda do mapa */}
                  <Space split="|">
                    <Text type="secondary">
                      <span style={{ display: 'inline-block', width: 12, height: 12, background: '#2e7d32', marginRight: 4 }}></span>
                      Estados com eventos
                    </Text>
                    <Text type="secondary">
                      <span style={{ display: 'inline-block', width: 12, height: 12, background: '#81c784', marginRight: 4 }}></span>
                      Estados sem eventos
                    </Text>
                    <Text type="secondary">
                      <span style={{ display: 'inline-block', width: 12, height: 12, background: '#1565c0', marginRight: 4 }}></span>
                      Estado selecionado
                    </Text>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Clique em um estado para ver detalhes.
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
                style={{ marginBottom: 16 }}
                extra={
                  <Button size="small" onClick={handleResetSelection}>
                    Fechar
                  </Button>
                }
              >
                <Row gutter={[16, 16]}>
                  {/* Estatísticas em destaque */}
                  <Col xs={8}>
                    <Statistic
                      title="Total de Eventos"
                      value={estadosData[selectedState].eventos}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Col>
                  <Col xs={8}>
                    <Statistic
                      title="Total de Projetos"
                      value={estadosData[selectedState].projetos}
                      valueStyle={{ color: '#722ed1' }}
                    />
                  </Col>
                  <Col xs={8}>
                    <Statistic
                      title="Coordenadores"
                      value={coordenadoresData.length}
                      valueStyle={{ color: '#52c41a' }}
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
                    Municípios com eventos ({estadosData[selectedState].municipios.length})
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
            <Card title="Lista de Municípios" style={{ marginBottom: 16 }} loading={loading}>
              <List
                dataSource={municipiosData}
                renderItem={(item) => (
                  <List.Item
                    extra={
                      <Space>
                        <Tag color="purple">{item.projetos} projetos</Tag>
                        <Tag color="blue">{item.eventos} eventos</Tag>
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
              <Card title="Eventos por Estado" bordered={false} loading={loading}>
                <List
                  dataSource={Object.entries(estadosData).sort((a, b) => b[1].eventos - a[1].eventos)}
                  renderItem={([uf, data]) => (
                    <List.Item>
                      <div className="w-full flex justify-between">
                        <div>
                          <Text strong>{uf}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: 12 }}>{data.municipios.length} municípios</Text>
                        </div>
                        <Space>
                          <Tag color="blue">{data.eventos} Eventos</Tag>
                          <Tag color="purple">{data.projetos} Projetos</Tag>
                        </Space>
                      </div>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>

            {/* Detalhes por Estado */}
            <Col xs={24} lg={12}>
              <Card title="Detalhes por Estado" bordered={false} loading={loading}>
                <Table
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
