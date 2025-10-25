/**
 * Página de Mapa do Brasil Interativo
 *
 * Design: paginamapadobrasil/screen.png
 * - Mapa do Brasil com visualização de eventos por município
 * - Filtros por projeto e intervalo de datas
 * - Estatísticas: Projetos por Município e Eventos + Coordenadores
 * - Toggle Map/List view
 */

import { useState, useEffect } from 'react';
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
  PlusOutlined,
  MinusOutlined,
  AimOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Panel } = Collapse;

// Mock data - Substituir por chamadas API reais
const mockProjetos = [
  { id: 1, nome: 'Todos os Projetos' },
  { id: 2, nome: 'Formação Continuada' },
  { id: 3, nome: 'Educação Infantil' },
  { id: 4, nome: 'BNCC Implementação' },
];

const mockProjetosPorMunicipio = [
  { municipio: 'São Paulo', uf: 'SP', projetos: 12 },
  { municipio: 'Rio de Janeiro', uf: 'RJ', projetos: 8 },
  { municipio: 'Belo Horizonte', uf: 'MG', projetos: 7 },
  { municipio: 'Salvador', uf: 'BA', projetos: 5 },
  { municipio: 'Fortaleza', uf: 'CE', projetos: 6 },
];

const mockEventosPorMunicipio = [
  { municipio: 'São Paulo', eventos: 128, coordenadores: 15 },
  { municipio: 'Rio de Janeiro', eventos: 95, coordenadores: 12 },
  { municipio: 'Belo Horizonte', eventos: 72, coordenadores: 8 },
  { municipio: 'Salvador', eventos: 54, coordenadores: 7 },
  { municipio: 'Fortaleza', eventos: 63, coordenadores: 9 },
];

export default function MapaBrasilPage() {
  const [viewMode, setViewMode] = useState('map'); // 'map' ou 'list'
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProjeto, setSelectedProjeto] = useState(1);
  const [dateRange, setDateRange] = useState(null);
  const [zoom, setZoom] = useState(1);
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

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 0.2, 3));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - 0.2, 0.5));
  };

  const handleResetZoom = () => {
    setZoom(1);
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
          <Text type="secondary">Visualização geral do Brasil</Text>
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
            <Card style={{ marginBottom: 16, position: 'relative' }}>
              {/* Controles de Zoom */}
              <div style={{ position: 'absolute', top: 16, right: 16, zIndex: 10 }}>
                <Space direction="vertical">
                  <Button icon={<PlusOutlined />} onClick={handleZoomIn} />
                  <Button icon={<MinusOutlined />} onClick={handleZoomOut} />
                  <Button icon={<AimOutlined />} onClick={handleResetZoom} />
                </Space>
              </div>

              {/* Mapa do Brasil (Simplified SVG) */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  minHeight: '500px',
                  overflow: 'hidden',
                  background: '#f8f9fa',
                  borderRadius: '8px',
                }}
              >
                <div style={{ transform: `scale(${zoom})`, transition: 'transform 0.3s' }}>
                  {/* Simplified Brazil Map SVG */}
                  <svg
                    width="400"
                    height="500"
                    viewBox="0 0 400 500"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    {/* Simplified outline of Brazil */}
                    <path
                      d="M150,50 L250,30 L320,60 L350,120 L360,180 L350,240 L330,300 L300,360 L260,420 L200,460 L150,480 L100,460 L70,420 L50,360 L40,300 L45,240 L60,180 L80,120 L100,80 Z"
                      fill="#e3f2fd"
                      stroke="#1890ff"
                      strokeWidth="2"
                    />
                    {/* Marker points for major cities */}
                    <circle cx="120" cy="380" r="8" fill="#52c41a" opacity="0.8" />
                    <text x="120" y="405" fontSize="10" textAnchor="middle" fill="#333">SP</text>

                    <circle cx="180" cy="400" r="6" fill="#1890ff" opacity="0.8" />
                    <text x="180" y="420" fontSize="10" textAnchor="middle" fill="#333">RJ</text>

                    <circle cx="140" cy="350" r="6" fill="#faad14" opacity="0.8" />
                    <text x="140" y="370" fontSize="10" textAnchor="middle" fill="#333">MG</text>

                    <circle cx="110" cy="280" r="5" fill="#f5222d" opacity="0.8" />
                    <text x="110" y="298" fontSize="10" textAnchor="middle" fill="#333">BA</text>

                    <circle cx="90" cy="200" r="5" fill="#722ed1" opacity="0.8" />
                    <text x="90" y="218" fontSize="10" textAnchor="middle" fill="#333">CE</text>
                  </svg>
                </div>
              </div>
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Text type="secondary">
                  Use os controles de zoom para navegar pelo mapa. Clique nos marcadores para ver detalhes.
                </Text>
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
