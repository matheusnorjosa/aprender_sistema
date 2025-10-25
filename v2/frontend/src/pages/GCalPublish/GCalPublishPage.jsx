/**
 * Página de Publicação no Google Calendar
 *
 * Design: paginacriareventonaagenda/screen.png
 * - Exibe eventos pendentes de sincronização
 * - Mostra ações: CRIAR, ATUALIZAR, ADOTAR, EXCLUIR, IGNORAR
 * - Permite preview e aplicação de mudanças
 * - Exclusivo para grupo Controle
 */

import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Statistic,
  Row,
  Col,
  message,
  Modal,
  Typography,
  Alert,
  Spin,
} from 'antd';
import {
  SyncOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// Mock data - Substituir por chamadas API reais
const mockEvents = [
  {
    id: 1,
    action: 'CRIAR',
    titulo: 'Formação Continuada - Encontro 1',
    data: '2025-10-28 14:00',
    municipio: 'Fortaleza',
    status: 'pending',
  },
  {
    id: 2,
    action: 'ATUALIZAR',
    titulo: 'Reunião de Planejamento',
    data: '2025-10-29 09:00',
    municipio: 'Caucaia',
    status: 'pending',
  },
  {
    id: 3,
    action: 'EXCLUIR',
    titulo: 'Evento Cancelado',
    data: '2025-10-30 15:00',
    municipio: 'Maracanaú',
    status: 'pending',
  },
];

const ACTION_CONFIG = {
  CRIAR: { color: 'green', icon: <PlusOutlined />, label: 'Criar' },
  ATUALIZAR: { color: 'blue', icon: <EditOutlined />, label: 'Atualizar' },
  ADOTAR: { color: 'cyan', icon: <CheckCircleOutlined />, label: 'Adotar' },
  EXCLUIR: { color: 'red', icon: <DeleteOutlined />, label: 'Excluir' },
  IGNORAR: { color: 'default', icon: <CloseCircleOutlined />, label: 'Ignorar' },
};

export default function GCalPublishPage() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [previewVisible, setPreviewVisible] = useState(false);

  // Stats
  const stats = {
    criar: events.filter(e => e.action === 'CRIAR').length,
    atualizar: events.filter(e => e.action === 'ATUALIZAR').length,
    adotar: events.filter(e => e.action === 'ADOTAR').length,
    excluir: events.filter(e => e.action === 'EXCLUIR').length,
    ignorar: events.filter(e => e.action === 'IGNORAR').length,
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    setLoading(true);
    try {
      // TODO: Substituir por chamada API real
      // const data = await fetchGCalPendingEvents();
      setTimeout(() => {
        setEvents(mockEvents);
        setLoading(false);
      }, 500);
    } catch (error) {
      console.error('Erro ao carregar eventos:', error);
      message.error('Erro ao carregar eventos pendentes');
      setLoading(false);
    }
  };

  const handlePreview = (record) => {
    setSelectedEvent(record);
    setPreviewVisible(true);
  };

  const handleApply = async (eventId) => {
    setSyncing(true);
    try {
      // TODO: Chamar API de aplicação
      // await applyGCalEvent(eventId);
      message.success('Evento sincronizado com sucesso!');
      loadEvents();
    } catch (error) {
      console.error('Erro ao sincronizar evento:', error);
      message.error('Erro ao sincronizar evento');
    } finally {
      setSyncing(false);
    }
  };

  const handleApplyAll = async () => {
    Modal.confirm({
      title: 'Confirmar Sincronização em Lote',
      content: `Tem certeza que deseja aplicar todas as ${events.length} ações pendentes?`,
      okText: 'Aplicar Todas',
      cancelText: 'Cancelar',
      onOk: async () => {
        setSyncing(true);
        try {
          // TODO: Chamar API de aplicação em lote
          // await applyAllGCalEvents();
          message.success(`${events.length} eventos sincronizados com sucesso!`);
          loadEvents();
        } catch (error) {
          console.error('Erro ao sincronizar eventos:', error);
          message.error('Erro ao sincronizar eventos');
        } finally {
          setSyncing(false);
        }
      },
    });
  };

  const columns = [
    {
      title: 'Ação',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (action) => {
        const config = ACTION_CONFIG[action] || ACTION_CONFIG.IGNORAR;
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.label}
          </Tag>
        );
      },
    },
    {
      title: 'Título',
      dataIndex: 'titulo',
      key: 'titulo',
    },
    {
      title: 'Data/Hora',
      dataIndex: 'data',
      key: 'data',
      render: (date) => dayjs(date).format('DD/MM/YYYY HH:mm'),
    },
    {
      title: 'Município',
      dataIndex: 'municipio',
      key: 'municipio',
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            Pré-visualizar
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<SyncOutlined />}
            onClick={() => handleApply(record.id)}
            loading={syncing}
          >
            Aplicar
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>Publicação no Google Calendar</Title>
      <Text type="secondary">
        Gerencie a sincronização de eventos com o Google Calendar
      </Text>

      {/* Stats */}
      <Row gutter={16} style={{ marginTop: 24, marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title="CRIAR"
              value={stats.criar}
              prefix={<PlusOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title="ATUALIZAR"
              value={stats.atualizar}
              prefix={<EditOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title="ADOTAR"
              value={stats.adotar}
              prefix={<CheckCircleOutlined style={{ color: '#13c2c2' }} />}
              valueStyle={{ color: '#13c2c2' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title="EXCLUIR"
              value={stats.excluir}
              prefix={<DeleteOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={4}>
          <Card>
            <Statistic
              title="IGNORAR"
              value={stats.ignorar}
              prefix={<CloseCircleOutlined style={{ color: '#d9d9d9' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Alert de aviso */}
      <Alert
        message="Atenção"
        description="As ações serão aplicadas imediatamente no Google Calendar. Revise cuidadosamente antes de aplicar."
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* Tabela */}
      <Card
        title="Eventos Pendentes de Sincronização"
        extra={
          <Button
            type="primary"
            icon={<SyncOutlined />}
            onClick={handleApplyAll}
            disabled={events.length === 0}
            loading={syncing}
          >
            Aplicar Todas ({events.length})
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={events}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Modal de Preview */}
      <Modal
        title="Pré-visualização do Evento"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Fechar
          </Button>,
          <Button
            key="apply"
            type="primary"
            icon={<SyncOutlined />}
            onClick={() => {
              handleApply(selectedEvent?.id);
              setPreviewVisible(false);
            }}
            loading={syncing}
          >
            Aplicar Agora
          </Button>,
        ]}
      >
        {selectedEvent ? (
          <div>
            <p><Text strong>Ação:</Text> <Tag color={ACTION_CONFIG[selectedEvent.action]?.color}>{selectedEvent.action}</Tag></p>
            <p><Text strong>Título:</Text> {selectedEvent.titulo}</p>
            <p><Text strong>Data/Hora:</Text> {dayjs(selectedEvent.data).format('DD/MM/YYYY HH:mm')}</p>
            <p><Text strong>Município:</Text> {selectedEvent.municipio}</p>
          </div>
        ) : (
          <Spin />
        )}
      </Modal>
    </div>
  );
}
