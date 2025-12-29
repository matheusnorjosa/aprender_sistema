/**
 * Página de Mapa do Brasil Interativo
 *
 * Design: paginamapadobrasil/screen.png
 * - Mapa do Brasil com visualização de eventos por município (usando Leaflet + GeoJSON)
 * - Filtros por projeto e intervalo de datas
 * - Estatísticas: Projetos por Município e Eventos + Coordenadores
 * - Toggle Map/List view
 */

import { useState, useEffect, useRef, useCallback } from 'react';
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
  Descriptions,
  Divider,
  Statistic,
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  EnvironmentOutlined,
  FullscreenOutlined,
} from '@ant-design/icons';
import { MapContainer, GeoJSON, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import brazilGeoJSON from '../../data/brazil-states.json';
import api from '../../api';
import logger from '../../utils/logger';

const { Title, Text } = Typography;
const { Panel } = Collapse;

// Componente para capturar a instância do mapa
function MapController({ mapRef }) {
  const map = useMap();
  useEffect(() => {
    mapRef.current = map;
  }, [map, mapRef]);
  return null;
}


export default function MapaBrasilPage() {
  const [viewMode, setViewMode] = useState('map'); // 'map' ou 'list'
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProjeto, setSelectedProjeto] = useState(null); // null = todos
  const [dateRange, setDateRange] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedState, setSelectedState] = useState(null); // Estado selecionado (sigla)

  // Estados para dados da API
  const [municipiosData, setMunicipiosData] = useState([]);
  const [estadosData, setEstadosData] = useState({}); // Agregado por UF: { CE: { eventos: 100, projetos: 5, ... }, ... }
  const [projetos, setProjetos] = useState([]);
  const [coordenadoresData, setCoordenadoresData] = useState([]); // Coordenadores do estado selecionado
  const [loadingCoordinators, setLoadingCoordinators] = useState(false);

  // Refs para usar em event handlers (evita stale closure)
  const selectedStateRef = useRef(null);
  const estadosDataRef = useRef({});
  const mapRef = useRef(null);
  const geoJsonRef = useRef(null);
  const mapContainerRef = useRef(null);

  // Manter refs sincronizados com state
  useEffect(() => {
    selectedStateRef.current = selectedState;
  }, [selectedState]);

  useEffect(() => {
    estadosDataRef.current = estadosData;
  }, [estadosData]);

  // Limpar seleção ao clicar fora do mapa
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        selectedStateRef.current &&
        mapContainerRef.current &&
        !mapContainerRef.current.contains(event.target)
      ) {
        // Verificar se o clique não foi no card de detalhes
        const detailCard = document.querySelector('.state-detail-card');
        if (detailCard && detailCard.contains(event.target)) {
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
    const fetchProjetos = async () => {
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

  const fetchMapData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Construir query params
      const params = {};
      if (selectedProjeto) params.projeto_id = selectedProjeto;
      if (dateRange?.[0]) params.data_inicio = dateRange[0].format('YYYY-MM-DD');
      if (dateRange?.[1]) params.data_fim = dateRange[1].format('YYYY-MM-DD');

      // Chamada à API
      const response = await api.get('/metrics/map/', { params });

      // Mapear resposta para formato esperado pelos markers
      const municipios = response.data.by_municipio.map(item => ({
        municipio: item.municipio,
        uf: item.uf,
        projetos: item.projetos,
        eventos: item.eventos,
        coordenadores: item.coordenadores,
        coords: [item.latitude, item.longitude],
      }));

      // Agregar dados por estado (UF)
      const estadosAgregados = {};
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
  const fetchCoordinators = async (uf) => {
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

  const handleApplyFilters = () => {
    fetchMapData();
  };

  const handleClearFilters = () => {
    setSelectedProjeto(null);
    setDateRange(null);
    setSearchTerm('');
    fetchMapData();
  };

  // Função para obter estilo baseado se o estado tem eventos
  const getStateStyle = (sigla) => {
    const hasEvents = estadosData[sigla] && estadosData[sigla].eventos > 0;
    return {
      fillColor: hasEvents ? '#2e7d32' : '#81c784', // Verde escuro para estados com eventos, verde claro sem
      fillOpacity: 1,
      color: '#ffffff',
      weight: 1,
    };
  };

  // Estilo quando hover
  const hoverStyle = {
    fillColor: '#1b5e20', // Verde ainda mais escuro no hover
    fillOpacity: 1,
    color: '#ffffff',
    weight: 2,
  };

  // Estilo quando selecionado (destacado "acima" do mapa - efeito de extração)
  const selectedStyle = {
    fillColor: '#1565c0', // Azul escuro para contraste (como na imagem de referência)
    fillOpacity: 1,
    color: '#ffffff',
    weight: 3,
    // className será adicionada via CSS para shadow
  };

  // Estilo dos estados não selecionados (levemente escurecidos)
  const dimmedStyle = {
    fillColor: '#a5d6a7', // Verde mais claro/desbotado
    fillOpacity: 0.6,
    color: '#ffffff',
    weight: 1,
  };

  // Função para resetar a seleção do estado
  const handleResetSelection = () => {
    setSelectedState(null);
    selectedStateRef.current = null;
    // Resetar estilos de todos os estados baseado em se têm eventos
    if (geoJsonRef.current) {
      geoJsonRef.current.eachLayer((layer) => {
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

  const onEachFeature = useCallback((feature, layer) => {
    if (feature.properties && feature.properties.name) {
      const sigla = feature.properties.sigla;

      // Label permanente com a sigla do estado (em branco)
      layer.bindTooltip(sigla, {
        permanent: true,
        direction: 'center',
        className: 'state-label',
      });

      // Eventos de hover e click
      layer.on({
        mouseover: (e) => {
          const targetLayer = e.target;
          const currentSelected = selectedStateRef.current;
          const layerSigla = targetLayer.feature.properties.sigla;

          // Se há um estado selecionado, não aplicar hover nos outros estados
          if (currentSelected && layerSigla !== currentSelected) {
            return; // Não fazer nada - manter estilo dimmed
          }

          // Aplicar hover apenas quando não há seleção ou é o estado selecionado
          if (!currentSelected) {
            targetLayer.setStyle(hoverStyle);
            targetLayer.bringToFront();
          }
        },
        mouseout: (e) => {
          const targetLayer = e.target;
          const layerSigla = targetLayer.feature.properties.sigla;
          const currentSelected = selectedStateRef.current;

          // Se há um estado selecionado, manter estilos apropriados
          if (layerSigla === currentSelected) {
            targetLayer.setStyle(selectedStyle);
          } else if (currentSelected) {
            // Não fazer nada - manter estilo dimmed
            return;
          } else {
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
        click: (e) => {
          const clickedSigla = e.target.feature.properties.sigla;
          const currentSelected = selectedStateRef.current;

          // Toggle seleção
          if (currentSelected === clickedSigla) {
            // Desselecionar
            selectedStateRef.current = null;
            setSelectedState(null);
            if (geoJsonRef.current) {
              geoJsonRef.current.eachLayer((l) => {
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
              geoJsonRef.current.eachLayer((l) => {
                const lSigla = l.feature?.properties?.sigla;
                if (lSigla === clickedSigla) {
                  l.setStyle(selectedStyle);
                  l.bringToFront();
                  // Adicionar classe para efeito de elevação
                  if (l._path) {
                    l._path.classList.add('selected-state');
                    l._path.classList.remove('dimmed-state');
                  }
                } else {
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

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ marginBottom: 0 }}>
            <EnvironmentOutlined style={{ marginRight: 8 }} />
            Mapa de Eventos
          </Title>
          <Text type="secondary">Visualização geográfica do Brasil</Text>
        </div>
        <Radio.Group value={viewMode} onChange={(e) => setViewMode(e.target.value)} buttonStyle="solid">
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
          onChange={(e) => setSearchTerm(e.target.value)}
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
            <Card style={{ marginBottom: 16 }} loading={loading}>
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
                  <GeoJSON
                    key={`geojson-${Object.keys(estadosData).length}`}
                    ref={geoJsonRef}
                    data={brazilGeoJSON}
                    onEachFeature={onEachFeature}
                    style={(feature) => {
                      const sigla = feature.properties?.sigla;
                      const hasEvents = estadosData[sigla]?.eventos > 0;
                      return {
                        fillColor: hasEvents ? '#2e7d32' : '#81c784',
                        fillOpacity: 1,
                        color: '#ffffff',
                        weight: 1,
                      };
                    }}
                  />

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
                    columns={[
                      {
                        title: 'Coordenador',
                        dataIndex: 'nome',
                        key: 'nome',
                        render: (nome) => <Text strong>{nome}</Text>,
                      },
                      {
                        title: 'Eventos',
                        dataIndex: 'eventos',
                        key: 'eventos',
                        align: 'center',
                        sorter: (a, b) => a.eventos - b.eventos,
                        defaultSortOrder: 'descend',
                        render: (v) => <Tag color="blue">{v}</Tag>,
                      },
                      {
                        title: 'Projetos (eventos)',
                        dataIndex: 'projetos',
                        key: 'projetos',
                        render: (projetos) => (
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
                        render: (municipios) => (
                          <Space wrap size={[4, 4]}>
                            {municipios.map((m, idx) => (
                              <Tag key={idx} color="green" style={{ margin: 0 }}>
                                {m.nome}: <strong>{m.eventos}</strong>
                              </Tag>
                            ))}
                          </Space>
                        ),
                      },
                    ]}
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
                    columns={[
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
                        render: (v) => <Tag color="blue">{v}</Tag>,
                      },
                      {
                        title: 'Coordenadores',
                        dataIndex: 'coordenadores',
                        key: 'coordenadores',
                        align: 'center',
                        render: (v) => <Tag color="green">{v}</Tag>,
                      },
                      {
                        title: 'Projetos',
                        dataIndex: 'projetos',
                        key: 'projetos',
                        align: 'center',
                        render: (v) => <Tag color="purple">{v}</Tag>,
                      },
                    ]}
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
                      <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between' }}>
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
                  dataSource={Object.entries(estadosData).map(([uf, data]) => ({ uf, ...data }))}
                  rowKey="uf"
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: 'Estado',
                      dataIndex: 'uf',
                      key: 'uf',
                      render: (text) => <Text strong>{text}</Text>,
                    },
                    {
                      title: 'Municípios',
                      dataIndex: 'municipios',
                      key: 'municipios',
                      align: 'center',
                      render: (municipios) => municipios.length,
                    },
                    {
                      title: 'Eventos',
                      dataIndex: 'eventos',
                      key: 'eventos',
                      align: 'center',
                      render: (eventos) => <Tag color="blue">{eventos}</Tag>,
                    },
                    {
                      title: 'Coordenadores',
                      dataIndex: 'coordenadores',
                      key: 'coordenadores',
                      align: 'center',
                      render: (coord) => <Tag color="green">{coord}</Tag>,
                    },
                  ]}
                />
              </Card>
            </Col>
          </Row>
        </Col>
      </Row>
    </div>
  );
}
