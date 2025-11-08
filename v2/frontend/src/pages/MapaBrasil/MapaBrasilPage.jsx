/**
 * Página de Mapa do Brasil Interativo
 *
 * Design: paginamapadobrasil/screen.png
 * - Mapa do Brasil com visualização de eventos por município (usando Leaflet + GeoJSON)
 * - Filtros por projeto e intervalo de datas
 * - Estatísticas: Projetos por Município e Eventos + Coordenadores
 * - Toggle Map/List view
 */

import { useState } from 'react';
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
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import { MapContainer, TileLayer, Marker, Popup, GeoJSON } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import brazilGeoJSON from '../../data/brazil-states.json';

const { Title, Text } = Typography;
const { Panel } = Collapse;

// Fix Leaflet default icon issue in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom marker icons by activity level
const createCustomIcon = (count) => {
  const color = count > 100 ? '#52c41a' : count > 50 ? '#1890ff' : count > 20 ? '#faad14' : '#f5222d';
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="background-color: ${color}; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; border: 2px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">${count}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
};

// Mock data - Substituir por chamadas API reais
const mockProjetos = [
  { id: 1, nome: 'Todos os Projetos' },
  { id: 2, nome: 'Formação Continuada' },
  { id: 3, nome: 'Educação Infantil' },
  { id: 4, nome: 'BNCC Implementação' },
];

const mockProjetosPorMunicipio = [
  { municipio: 'São Paulo', uf: 'SP', projetos: 12, coords: [-23.5505, -46.6333] },
  { municipio: 'Rio de Janeiro', uf: 'RJ', projetos: 8, coords: [-22.9068, -43.1729] },
  { municipio: 'Belo Horizonte', uf: 'MG', projetos: 7, coords: [-19.9167, -43.9378] },
  { municipio: 'Salvador', uf: 'BA', projetos: 5, coords: [-12.9714, -38.5108] },
  { municipio: 'Fortaleza', uf: 'CE', projetos: 6, coords: [-3.7172, -38.5434] },
];

const mockEventosPorMunicipio = [
  { municipio: 'São Paulo', eventos: 128, coordenadores: 15, coords: [-23.5505, -46.6333] },
  { municipio: 'Rio de Janeiro', eventos: 95, coordenadores: 12, coords: [-22.9068, -43.1729] },
  { municipio: 'Belo Horizonte', eventos: 72, coordenadores: 8, coords: [-19.9167, -43.9378] },
  { municipio: 'Salvador', eventos: 54, coordenadores: 7, coords: [-12.9714, -38.5108] },
  { municipio: 'Fortaleza', eventos: 63, coordenadores: 9, coords: [-3.7172, -38.5434] },
];

export default function MapaBrasilPage() {
  const [viewMode, setViewMode] = useState('map'); // 'map' ou 'list'
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProjeto, setSelectedProjeto] = useState(1);
  const [dateRange, setDateRange] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleApplyFilters = () => {
    setLoading(true);
    // TODO: Chamar API com filtros
    console.log('Aplicando filtros:', { selectedProjeto, dateRange, searchTerm });
    setTimeout(() => setLoading(false), 500);
  };

  const handleClearFilters = () => {
    setSelectedProjeto(1);
    setDateRange(null);
    setSearchTerm('');
  };

  const onEachFeature = (feature, layer) => {
    if (feature.properties && feature.properties.name) {
      layer.bindPopup(
        `<strong>${feature.properties.name}</strong><br/>
         Sigla: ${feature.properties.sigla}<br/>
         Região: ${feature.properties.regiao}`
      );
    }
  };

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
                    options={mockProjetos.map((p) => ({ label: p.nome, value: p.id }))}
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
          {viewMode === 'map' ? (
            <Card style={{ marginBottom: 16 }}>
              {/* Mapa Leaflet com GeoJSON */}
              <div style={{ height: '600px', borderRadius: '8px', overflow: 'hidden' }}>
                <MapContainer
                  center={[-14.235, -51.9253]}
                  zoom={4}
                  style={{ height: '100%', width: '100%' }}
                  scrollWheelZoom={true}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  {/* GeoJSON layer for states */}
                  <GeoJSON data={brazilGeoJSON} onEachFeature={onEachFeature} />

                  {/* Markers para eventos por município */}
                  {mockEventosPorMunicipio.map((item) => (
                    <Marker
                      key={item.municipio}
                      position={item.coords}
                      icon={createCustomIcon(item.eventos)}
                    >
                      <Popup>
                        <div style={{ minWidth: '200px' }}>
                          <Text strong style={{ fontSize: 16 }}>{item.municipio}</Text>
                          <br />
                          <br />
                          <Space direction="vertical" size="small" style={{ width: '100%' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Text>Eventos:</Text>
                              <Tag color="blue">{item.eventos}</Tag>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <Text>Coordenadores:</Text>
                              <Tag color="green">{item.coordenadores}</Tag>
                            </div>
                          </Space>
                        </div>
                      </Popup>
                    </Marker>
                  ))}
                </MapContainer>
              </div>
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Space split="|">
                  <Text type="secondary">
                    <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#52c41a', marginRight: 4 }}></span>
                    &gt;100 eventos
                  </Text>
                  <Text type="secondary">
                    <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#1890ff', marginRight: 4 }}></span>
                    50-100 eventos
                  </Text>
                  <Text type="secondary">
                    <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#faad14', marginRight: 4 }}></span>
                    20-50 eventos
                  </Text>
                  <Text type="secondary">
                    <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#f5222d', marginRight: 4 }}></span>
                    &lt;20 eventos
                  </Text>
                </Space>
              </div>
            </Card>
          ) : (
            <Card title="Lista de Municípios" style={{ marginBottom: 16 }}>
              <List
                dataSource={mockProjetosPorMunicipio}
                renderItem={(item) => (
                  <List.Item
                    extra={<Tag color="blue">{item.projetos} projetos</Tag>}
                  >
                    <List.Item.Meta
                      avatar={<EnvironmentOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                      title={item.municipio}
                      description={item.uf}
                    />
                  </List.Item>
                )}
              />
            </Card>
          )}

          {/* Estatísticas */}
          <Row gutter={[16, 16]}>
            {/* Projetos por Município */}
            <Col xs={24} lg={12}>
              <Card title="Projetos por Município" bordered={false}>
                <List
                  dataSource={mockProjetosPorMunicipio}
                  renderItem={(item) => (
                    <List.Item>
                      <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between' }}>
                        <div>
                          <Text strong>{item.municipio}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: 12 }}>{item.uf}</Text>
                        </div>
                        <Text strong style={{ fontSize: 16 }}>{item.projetos} Projetos</Text>
                      </div>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>

            {/* Eventos + Coordenadores por Município */}
            <Col xs={24} lg={12}>
              <Card title="Eventos + Coordenadores por Município" bordered={false}>
                <Table
                  dataSource={mockEventosPorMunicipio}
                  rowKey="municipio"
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: 'Município',
                      dataIndex: 'municipio',
                      key: 'municipio',
                      render: (text) => <Text strong>{text}</Text>,
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
