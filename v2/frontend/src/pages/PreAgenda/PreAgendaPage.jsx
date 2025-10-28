/**
 * PreAgendaPage - Página de pré-agenda (Controle)
 *
 * Features:
 * - Lista solicitações aprovadas de ambos os fluxos (SUPER + NAO_SUPER)
 * - Filtros por data, setor, busca textual
 * - Exibe resumo de status GCal no topo
 * - Botões para preview e publish individual
 *
 * Nota: Publicação no Google Calendar ocorre exclusivamente via botão "Publicar"
 * nesta página. Não há operações em lote de publicação.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Card,
  Input,
  DatePicker,
  Button,
  Space,
  Tag,
  Typography,
  message,
  Modal,
  Statistic,
  Row,
  Col,
  Alert,
} from 'antd';
import {
  EyeOutlined,
  CloudUploadOutlined,
  CalendarOutlined,
  VideoCameraOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { listSolicitacoes, previewSolicitacao, publishSolicitacao } from '../../api/solicitacoes';
import { getStatusSummary } from '../../api/gcal';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const GCAL_STATUS_COLORS = {
  NONE: 'default',
  PENDING: 'processing',
  PUBLISHED: 'success',
  ERROR: 'error',
};

export default function PreAgendaPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);

  const [summary, setSummary] = useState({ counts: {}, total: 0 });

  const [searchTerm, setSearchTerm] = useState('');
  const [sectorFilter, setSectorFilter] = useState('');
  const [dateRange, setDateRange] = useState([null, null]);

  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);

      const filters = { status: 'aprovado' };
      if (searchTerm) filters.q = searchTerm;
      if (sectorFilter) filters.sector = sectorFilter;
      if (dateRange[0]) filters.date_from = dateRange[0].format('YYYY-MM-DD');
      if (dateRange[1]) filters.date_to = dateRange[1].format('YYYY-MM-DD');

      // Carregar ambos os fluxos e resumo
      const [superData, naoSuperData, summaryData] = await Promise.all([
        listSolicitacoes({ ...filters, flow: 'SUPER' }),
        listSolicitacoes({ ...filters, flow: 'NAO_SUPER' }),
        getStatusSummary(filters),
      ]);

      const superRows = superData.results || superData;
      const naoRows = naoSuperData.results || naoSuperData;

      setRows([...superRows, ...naoRows]);
      setTotal((superData.count || superRows.length) + (naoSuperData.count || naoRows.length));
      setSummary(summaryData);
    } catch (error) {
      message.error('Erro ao carregar pré-agenda: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, sectorFilter, dateRange]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handlePreview = async (id) => {
    try {
      const data = await previewSolicitacao(id);
      setPreviewData(data);
      setPreviewVisible(true);
    } catch (error) {
      message.error('Erro ao visualizar payload: ' + error.message);
    }
  };

  const handlePublish = (id) => {
    Modal.confirm({
      title: 'Confirmar Publicação',
      content: 'Deseja publicar este evento no Google Calendar?',
      okText: 'Publicar',
      okType: 'primary',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await publishSolicitacao(id, { dry_run: false });
          message.success('Evento publicado com sucesso!');
          loadData();
        } catch (error) {
          message.error('Erro ao publicar: ' + error.message);
        }
      },
    });
  };

  const columns = [
    {
      title: 'Data/Hora',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (inicio) => dayjs(inicio).format('DD/MM/YYYY HH:mm'),
      width: 150,
    },
    {
      title: 'Município',
      dataIndex: 'municipio',
      key: 'municipio',
      render: (municipio) => municipio?.nome || '-',
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto',
      key: 'projeto',
      render: (projeto) => projeto?.nome || '-',
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_evento',
      key: 'tipo_evento',
      render: (tipo) => tipo?.nome || '-',
    },
    {
      title: 'GCal Status',
      dataIndex: 'gcal_status',
      key: 'gcal_status',
      render: (gcal_status) => (
        <Tag color={GCAL_STATUS_COLORS[gcal_status] || 'default'}>{gcal_status || 'NONE'}</Tag>
      ),
      width: 120,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record.id)}
            title="Preview"
          />
          <Button
            size="small"
            type="primary"
            icon={<CloudUploadOutlined />}
            onClick={() => handlePublish(record.id)}
            title="Publicar"
            disabled={record.gcal_status === 'PUBLISHED'}
          />
          {record.meet_link && (
            <Button
              size="small"
              type="link"
              icon={<VideoCameraOutlined />}
              href={record.meet_link}
              target="_blank"
              rel="noopener noreferrer"
              title="Entrar na reunião"
            />
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <Card>
          <Title level={2} style={{ margin: 0 }}>
            Pré-agenda (Controle)
          </Title>
        </Card>

        {/* Resumo GCal */}
        <Card title="Resumo de Status GCal" size="small">
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="Não Publicados" value={summary.counts?.NONE || 0} />
            </Col>
            <Col span={6}>
              <Statistic
                title="Pendentes"
                value={summary.counts?.PENDING || 0}
                valueStyle={{ color: '#faad14' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Publicados"
                value={summary.counts?.PUBLISHED || 0}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="Erros"
                value={summary.counts?.ERROR || 0}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Col>
          </Row>
        </Card>

        {/* Filtros */}
        <Card size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <Input.Search
                placeholder="Buscar por município, projeto..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onSearch={loadData}
                style={{ width: 300 }}
                allowClear
              />
              <Input
                placeholder="Filtrar por setor/projeto"
                value={sectorFilter}
                onChange={(e) => setSectorFilter(e.target.value)}
                onPressEnter={loadData}
                style={{ width: 200 }}
                allowClear
              />
              <RangePicker
                value={dateRange}
                onChange={setDateRange}
                format="DD/MM/YYYY"
                placeholder={['Data inicial', 'Data final']}
              />
            </Space>
          </Space>
        </Card>

        {/* Tabela */}
        <Card>
          <Table
            columns={columns}
            dataSource={rows}
            loading={loading}
            rowKey="id"
            pagination={{
              total,
              pageSize: 20,
              showTotal: (total) => `Total: ${total} eventos aprovados`,
            }}
          />
        </Card>
      </Space>

      {/* Modal Preview */}
      <Modal
        title="Preview do Payload GCal"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Fechar
          </Button>,
        ]}
        width={700}
      >
        <pre style={{ maxHeight: 500, overflow: 'auto', backgroundColor: '#f5f5f5', padding: 12 }}>
          {JSON.stringify(previewData, null, 2)}
        </pre>
      </Modal>
    </div>
  );
}
