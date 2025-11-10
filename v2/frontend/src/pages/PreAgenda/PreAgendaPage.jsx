/**
 * PreAgendaPage - Página de pré-agenda (Controle)
 *
 * Features:
 * - Lista solicitações aprovadas de ambos os fluxos (SUPER + NAO_SUPER)
 * - Filtros por data, setor, busca textual
 * - Exibe resumo de status GCal no topo
 * - Botões para preview e publish
 * - Link para painel /publicacao para operações em lote
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
  SyncOutlined,
  StopOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import {
  listSolicitacoes,
  previewSolicitacao,
  publishSolicitacao,
  resyncSolicitacao,
  cancelSolicitacao,
} from '../../api/solicitacoes';
import { getStatusSummary } from '../../api/gcal';
import { MeetLink } from '../../components/MeetLink';
import { getMe } from '../../api/availability';
import useGoogleIntegration from '../../hooks/useGoogleIntegration';
import GoogleIntegrationCard from '../../components/google/GoogleIntegrationCard';

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

  // Issue #95: Batch operations - Row selection
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [batchLoading, setBatchLoading] = useState(false);

  // OAuth Phase 5: Estado do usuário e integração Google
  const [user, setUser] = useState(null);
  const { status: googleStatus, loading: _googleLoading, fetchStatus: _fetchStatus } = useGoogleIntegration();

  // Carregar dados do usuário
  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await getMe();
        setUser(userData);
      } catch (error) {
        console.error('Erro ao carregar usuário:', error);
      }
    };
    loadUser();
  }, []);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);

      const filters = { status: 'approved' };
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
    // OAuth Phase 5: Guarda - verificar conexão Google
    if (googleStatus && !googleStatus.connected) {
      Modal.confirm({
        title: 'Conectar conta Google',
        content: (
          <div>
            <p>Para publicar eventos no Google Calendar, você precisa conectar sua conta corporativa do Google.</p>
          </div>
        ),
        okText: 'Conectar agora',
        okType: 'primary',
        cancelText: 'Cancelar',
        onOk: () => {
          window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
        },
      });
      return;
    }

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
          // OAuth Phase 5: Tratar erro 403 com code='google_not_connected'
          if (error.response?.data?.code === 'google_not_connected') {
            Modal.confirm({
              title: 'Conectar conta Google',
              content: (
                <div>
                  <p>{error.response?.data?.detail || 'Conecte sua conta Google para publicar eventos.'}</p>
                </div>
              ),
              okText: 'Conectar agora',
              okType: 'primary',
              cancelText: 'Cancelar',
              onOk: () => {
                window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
              },
            });
          } else {
            message.error('Erro ao publicar: ' + error.message);
          }
        }
      },
    });
  };

  const handleResync = (id) => {
    // OAuth Phase 5: Guarda - verificar conexão Google
    if (googleStatus && !googleStatus.connected) {
      Modal.confirm({
        title: 'Conectar conta Google',
        content: (
          <div>
            <p>Para reenviar eventos no Google Calendar, você precisa conectar sua conta corporativa do Google.</p>
          </div>
        ),
        okText: 'Conectar agora',
        okType: 'primary',
        cancelText: 'Cancelar',
        onOk: () => {
          window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
        },
      });
      return;
    }

    Modal.confirm({
      title: 'Confirmar Reenvio',
      icon: <SyncOutlined style={{ color: '#faad14' }} />,
      content: (
        <div>
          <p>Deseja reenviar (forçar UPDATE) este evento no Google Calendar?</p>
          <p style={{ color: '#888', fontSize: '12px' }}>
            Esta ação irá sobrescrever o evento existente com os dados atualizados.
          </p>
        </div>
      ),
      okText: 'Reenviar',
      okType: 'warning',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await resyncSolicitacao(id);
          message.success('Reenvio solicitado! O evento será atualizado em instantes.');
          loadData();
        } catch (error) {
          // OAuth Phase 5: Tratar erro 403 com code='google_not_connected'
          if (error.response?.data?.code === 'google_not_connected') {
            Modal.confirm({
              title: 'Conectar conta Google',
              content: (
                <div>
                  <p>{error.response?.data?.detail || 'Conecte sua conta Google para reenviar eventos.'}</p>
                </div>
              ),
              okText: 'Conectar agora',
              okType: 'primary',
              cancelText: 'Cancelar',
              onOk: () => {
                window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
              },
            });
          } else {
            message.error('Erro ao reenviar: ' + error.message);
          }
        }
      },
    });
  };

  const handleCancel = (id) => {
    Modal.confirm({
      title: 'Confirmar Cancelamento',
      icon: <StopOutlined style={{ color: '#ff4d4f' }} />,
      content: (
        <div>
          <p>Deseja cancelar este evento no Google Calendar?</p>
          <p style={{ color: '#ff4d4f', fontWeight: 'bold', fontSize: '12px' }}>
            ⚠️ ATENÇÃO: Esta ação irá deletar permanentemente o evento do Calendar e limpar todos os campos relacionados (event_id, meet_link, etc.).
          </p>
        </div>
      ),
      okText: 'Sim, Cancelar Evento',
      okType: 'danger',
      cancelText: 'Não',
      onOk: async () => {
        try {
          await cancelSolicitacao(id);
          message.success('Cancelamento solicitado! O evento será removido em instantes.');
          loadData();
        } catch (error) {
          message.error('Erro ao cancelar: ' + error.message);
        }
      },
    });
  };

  // Issue #95: Batch Reapply
  const handleBatchReapply = () => {
    // OAuth Phase 5: Guarda - verificar conexão Google
    if (googleStatus && !googleStatus.connected) {
      Modal.confirm({
        title: 'Conectar conta Google',
        content: (
          <div>
            <p>Para realizar ações em massa no Google Calendar, você precisa conectar sua conta corporativa do Google.</p>
          </div>
        ),
        okText: 'Conectar agora',
        okType: 'primary',
        cancelText: 'Cancelar',
        onOk: () => {
          window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
        },
      });
      return;
    }

    if (selectedRowKeys.length === 0) {
      message.warning('Selecione ao menos um evento para reaplica');
      return;
    }

    Modal.confirm({
      title: `Confirmar Reapply em Massa (${selectedRowKeys.length} eventos)`,
      icon: <SyncOutlined style={{ color: '#faad14' }} />,
      content: (
        <div>
          <p>Deseja reenviar (forçar UPDATE) estes {selectedRowKeys.length} eventos no Google Calendar?</p>
          <p style={{ color: '#888', fontSize: '12px' }}>
            Esta ação irá sobrescrever os eventos existentes com os dados atualizados.
          </p>
        </div>
      ),
      okText: 'Reenviar',
      okType: 'warning',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const response = await fetch('/api/gcal/dashboard/batch/reapply/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              ids: selectedRowKeys,
              dry_run: false,
              apply_blocked: true,
            }),
          });

          const data = await response.json();

          if (response.status === 403 && data.code === 'google_not_connected') {
            Modal.confirm({
              title: 'Conectar conta Google',
              content: (
                <div>
                  <p>{data.detail || 'Conecte sua conta Google para realizar ações em massa.'}</p>
                </div>
              ),
              okText: 'Conectar agora',
              okType: 'primary',
              cancelText: 'Cancelar',
              onOk: () => {
                window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
              },
            });
            return;
          }

          if (!response.ok) {
            throw new Error(data.detail || 'Erro ao reenviar eventos');
          }

          message.success(`${data.queued} eventos enfileirados para reapply!`);
          if (data.errors && data.errors.length > 0) {
            message.warning(`${data.errors.length} erros: ${data.errors.map(e => e.detail).join(', ')}`);
          }
          setSelectedRowKeys([]);
          loadData();
        } catch (error) {
          message.error('Erro ao reenviar em massa: ' + error.message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // Issue #95: Batch Resync
  const handleBatchResync = () => {
    // OAuth Phase 5: Guarda - verificar conexão Google
    if (googleStatus && !googleStatus.connected) {
      Modal.confirm({
        title: 'Conectar conta Google',
        content: (
          <div>
            <p>Para realizar ações em massa no Google Calendar, você precisa conectar sua conta corporativa do Google.</p>
          </div>
        ),
        okText: 'Conectar agora',
        okType: 'primary',
        cancelText: 'Cancelar',
        onOk: () => {
          window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
        },
      });
      return;
    }

    if (selectedRowKeys.length === 0) {
      message.warning('Selecione ao menos um evento para resync');
      return;
    }

    Modal.confirm({
      title: `Confirmar Resync em Massa (${selectedRowKeys.length} eventos)`,
      icon: <SyncOutlined style={{ color: '#ff4d4f' }} />,
      content: (
        <div>
          <p>Deseja forçar resync (resetar hash + PENDING) destes {selectedRowKeys.length} eventos?</p>
          <p style={{ color: '#888', fontSize: '12px' }}>
            Útil para corrigir drift ou reprocessar eventos com erros.
          </p>
        </div>
      ),
      okText: 'Resync',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const response = await fetch('/api/gcal/dashboard/batch/resync/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              ids: selectedRowKeys,
              dry_run: false,
              apply_blocked: true,
            }),
          });

          const data = await response.json();

          if (response.status === 403 && data.code === 'google_not_connected') {
            Modal.confirm({
              title: 'Conectar conta Google',
              content: (
                <div>
                  <p>{data.detail || 'Conecte sua conta Google para realizar ações em massa.'}</p>
                </div>
              ),
              okText: 'Conectar agora',
              okType: 'primary',
              cancelText: 'Cancelar',
              onOk: () => {
                window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
              },
            });
            return;
          }

          if (!response.ok) {
            throw new Error(data.detail || 'Erro ao fazer resync de eventos');
          }

          message.success(`${data.queued} eventos enfileirados para resync!`);
          if (data.errors && data.errors.length > 0) {
            message.warning(`${data.errors.length} erros: ${data.errors.map(e => e.detail).join(', ')}`);
          }
          setSelectedRowKeys([]);
          loadData();
        } catch (error) {
          message.error('Erro ao resync em massa: ' + error.message);
        } finally {
          setBatchLoading(false);
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
      width: 200,
      render: (_, record) => {
        const isPublished = record.gcal_status === 'PUBLISHED';
        const hasError = record.gcal_status === 'ERROR';
        const hasEventId = !!record.external_event_id;

        // Resync: mostrar quando PUBLISHED ou ERROR
        const showResync = isPublished || hasError;

        // Cancel: mostrar apenas quando PUBLISHED e tem event_id
        const showCancel = isPublished && hasEventId;

        return (
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
              disabled={isPublished}
            />
            {showResync && (
              <Button
                size="small"
                type="default"
                icon={<SyncOutlined />}
                onClick={() => handleResync(record.id)}
                title="Reenviar (forçar UPDATE)"
                style={{ color: '#faad14', borderColor: '#faad14' }}
              />
            )}
            {showCancel && (
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => handleCancel(record.id)}
                title="Cancelar evento no Calendar"
              />
            )}
            <MeetLink href={record.meet_link} />
          </Space>
        );
      },
    },
  ];

  // OAuth Phase 5: RBAC - verificar se é Controle ou Super
  const canControle = user?.is_superuser || user?.groups?.includes('Controle');
  const canSuper = user?.is_superuser || user?.is_superintendencia || user?.groups?.includes('Superintendência');
  const showGoogleCard = canControle || canSuper;

  // Handlers para o card Google
  const handleGoogleConnect = () => {
    window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
  };

  const handleGoogleDisconnect = async () => {
    // Implementação futura (Fase 6+)
    message.info('Desconexão será implementada em breve');
  };

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={2} style={{ margin: 0 }}>
              Pré-agenda (Controle)
            </Title>
            <Button
              icon={<CalendarOutlined />}
              onClick={() => navigate('/publicacao')}
              type="default"
            >
              Painel de Publicação
            </Button>
          </div>
        </Card>

        {/* OAuth Phase 5: Google Integration Card (Controle/Super apenas) */}
        {showGoogleCard && (
          <GoogleIntegrationCard
            status={googleStatus}
            onConnect={handleGoogleConnect}
            onDisconnect={handleGoogleDisconnect}
          />
        )}

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
          {/* Issue #95: Toolbar de Ações em Massa */}
          {selectedRowKeys.length > 0 && (
            <div style={{ marginBottom: 16, padding: '12px', background: '#e6f7ff', borderRadius: '4px' }}>
              <Space>
                <Text strong>{selectedRowKeys.length} evento(s) selecionado(s)</Text>
                <Button
                  type="default"
                  icon={<SyncOutlined />}
                  onClick={handleBatchReapply}
                  loading={batchLoading}
                  style={{ color: '#faad14', borderColor: '#faad14' }}
                >
                  Reapply Selecionados
                </Button>
                <Button
                  danger
                  icon={<SyncOutlined />}
                  onClick={handleBatchResync}
                  loading={batchLoading}
                >
                  Resync Selecionados
                </Button>
                <Button
                  type="link"
                  onClick={() => setSelectedRowKeys([])}
                >
                  Limpar Seleção
                </Button>
              </Space>
            </div>
          )}
          <Table
            columns={columns}
            dataSource={rows}
            loading={loading}
            rowKey="id"
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys),
              selections: [
                Table.SELECTION_ALL,
                Table.SELECTION_INVERT,
                Table.SELECTION_NONE,
              ],
            }}
            pagination={{
              total,
              pageSize: 20,
              showTotal: (total) => `Total: ${total} eventos aprovados`,
            }}
          />
        </Card>

        {/* Rodapé */}
        <Alert
          message="Publicação em Lote"
          description={
            <Text>
              Para gerenciar status operacional, detectar drift e realizar re-aplicações em lote,
              use o <a href="/publicacao">Painel de Publicação GCal</a>.
            </Text>
          }
          type="info"
          icon={<InfoCircleOutlined />}
          showIcon
        />
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
