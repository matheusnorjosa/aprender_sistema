/**
 * PreAgendaPage - Página de pré-agenda (Controle)
 *
 * Features:
 * - Lista solicitações aprovadas de ambos os fluxos (SUPER + NAO_SUPER)
 * - Filtros por data, setor, busca textual
 * - Exibe resumo de status GCal no topo
 * - Botões para preview e publish
 * - Operações em lote (Reapply/Resync) via seleção múltipla
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
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
  Descriptions,
  Collapse,
  Divider,
  List,
  Avatar,
} from 'antd';
import {
  EyeOutlined,
  CloudUploadOutlined,
  CalendarOutlined,
  VideoCameraOutlined,
  InfoCircleOutlined,
  SyncOutlined,
  StopOutlined,
  EnvironmentOutlined,
  TeamOutlined,
  LinkOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  GlobalOutlined,
  UserOutlined,
  CodeOutlined,
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
  const { status: googleStatus, loading: _googleLoading, fetchStatus: _fetchStatus, disconnect: googleDisconnect } = useGoogleIntegration();

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

  // Issue #260: Memoizar handlers para evitar re-renderização desnecessária
  const handlePreview = useCallback(async (id) => {
    try {
      const data = await previewSolicitacao(id);
      setPreviewData(data);
      setPreviewVisible(true);
    } catch (error) {
      message.error('Erro ao visualizar payload: ' + error.message);
    }
  }, []);

  const handlePublish = useCallback((id) => {
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
  }, [googleStatus, loadData]);

  const handleResync = useCallback((id) => {
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
  }, [googleStatus, loadData]);

  const handleCancel = useCallback((id) => {
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
  }, [loadData]);

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

  // Issue #260: Memoizar columns para evitar re-renderização desnecessária da tabela
  const columns = useMemo(() => [
    {
      title: 'Data/Hora',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (inicio) => dayjs(inicio).format('DD/MM/YYYY HH:mm'),
      width: 150,
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio_nome',
      render: (nome) => nome || '-',
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto_nome',
      render: (nome) => nome || '-',
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      render: (tipo) => tipo || '-',
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
  ], [handlePreview, handlePublish, handleResync, handleCancel]);

  // OAuth Phase 5: RBAC - verificar se é Controle ou Super
  const canControle = user?.is_superuser || user?.groups?.includes('Controle');
  const canSuper = user?.is_superuser || user?.is_superintendencia || user?.groups?.includes('Superintendência');
  const showGoogleCard = canControle || canSuper;

  // Handlers para o card Google
  const handleGoogleConnect = () => {
    window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
  };

  const handleGoogleDisconnect = async () => {
    try {
      const result = await googleDisconnect();

      if (result.success) {
        message.success('Conta Google desconectada com sucesso');
      } else {
        message.error(result.error || 'Erro ao desconectar conta Google');
      }
    } catch (error) {
      message.error('Erro ao desconectar: ' + error.message);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <Card>
          <Title level={2} style={{ margin: 0 }}>
            Pré-agenda
          </Title>
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
          message="Operações em Lote"
          description={
            <Text>
              Selecione múltiplos eventos na tabela para atualizar ou republicar no Google Calendar.
            </Text>
          }
          type="info"
          icon={<InfoCircleOutlined />}
          showIcon
        />
      </Space>

      {/* Modal Preview */}
      <Modal
        title={
          <Space>
            <CalendarOutlined />
            <span>Preview do Evento Google Calendar</span>
          </Space>
        }
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Fechar
          </Button>,
        ]}
        width={800}
      >
        {previewData?.preview && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* Título do Evento */}
            <Card size="small">
              <Title level={4} style={{ margin: 0 }}>
                {previewData.preview.payload?.summary || 'Sem título'}
              </Title>
            </Card>

            {/* Informações Principais */}
            <Descriptions bordered size="small" column={2}>
              {/* Data e Hora */}
              <Descriptions.Item
                label={<><ClockCircleOutlined /> Data/Hora</>}
                span={2}
              >
                {previewData.preview.payload?.start?.dateTime && (
                  <Space>
                    <Tag color="blue">
                      {dayjs(previewData.preview.payload.start.dateTime).format('DD/MM/YYYY')}
                    </Tag>
                    <Text>
                      {dayjs(previewData.preview.payload.start.dateTime).format('HH:mm')}
                      {' - '}
                      {previewData.preview.payload?.end?.dateTime &&
                        dayjs(previewData.preview.payload.end.dateTime).format('HH:mm')}
                    </Text>
                  </Space>
                )}
              </Descriptions.Item>

              {/* Localização */}
              <Descriptions.Item
                label={<><EnvironmentOutlined /> Local</>}
              >
                {previewData.preview.payload?.location || <Text type="secondary">Não informado</Text>}
              </Descriptions.Item>

              {/* Modalidade */}
              <Descriptions.Item
                label={<><GlobalOutlined /> Modalidade</>}
              >
                {previewData.preview.payload?.conferenceData ? (
                  <Tag color="green" icon={<VideoCameraOutlined />}>Online</Tag>
                ) : (
                  <Tag color="orange">Presencial</Tag>
                )}
              </Descriptions.Item>

              {/* Event ID */}
              <Descriptions.Item
                label={<><LinkOutlined /> Event ID</>}
              >
                <Text code copyable>{previewData.preview.event_id}</Text>
              </Descriptions.Item>

              {/* Meet Link */}
              <Descriptions.Item
                label={<><VideoCameraOutlined /> Meet Link</>}
              >
                {previewData.preview.meet_link ? (
                  <Text copyable={{ text: previewData.preview.meet_link }}>
                    <a href={previewData.preview.meet_link} target="_blank" rel="noopener noreferrer">
                      {previewData.preview.meet_link}
                    </a>
                  </Text>
                ) : (
                  <Text type="secondary">Não aplicável (presencial)</Text>
                )}
              </Descriptions.Item>
            </Descriptions>

            {/* Participantes */}
            {previewData.preview.payload?.attendees?.length > 0 && (
              <Card
                size="small"
                title={<><TeamOutlined /> Participantes ({previewData.preview.payload.attendees.length})</>}
              >
                <List
                  size="small"
                  dataSource={previewData.preview.payload.attendees}
                  renderItem={(attendee) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<Avatar size="small" icon={<UserOutlined />} />}
                        title={attendee.email}
                        description={attendee.responseStatus === 'needsAction' ? 'Aguardando resposta' : attendee.responseStatus}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {/* Descrição */}
            {previewData.preview.payload?.description && (
              <Card
                size="small"
                title={<><FileTextOutlined /> Descrição</>}
              >
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  margin: 0,
                  fontSize: '13px',
                  fontFamily: 'inherit',
                  maxHeight: '200px',
                  overflow: 'auto'
                }}>
                  {previewData.preview.payload.description}
                </pre>
              </Card>
            )}

            {/* Informações Técnicas (Colapsável) - Apenas superuser */}
            {user?.is_superuser && (
              <Collapse
                size="small"
                items={[
                  {
                    key: 'technical',
                    label: (
                      <Space>
                        <CodeOutlined />
                        <span>Informações Técnicas (JSON)</span>
                      </Space>
                    ),
                    children: (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Descriptions size="small" column={1}>
                          <Descriptions.Item label="Payload Hash">
                            <Text code copyable style={{ fontSize: '11px' }}>
                              {previewData.preview.payload_hash}
                            </Text>
                          </Descriptions.Item>
                        </Descriptions>
                        <Divider style={{ margin: '8px 0' }} />
                        <pre style={{
                          maxHeight: 300,
                          overflow: 'auto',
                          backgroundColor: '#f5f5f5',
                          padding: 12,
                          fontSize: '11px',
                          borderRadius: '4px'
                        }}>
                          {JSON.stringify(previewData, null, 2)}
                        </pre>
                      </Space>
                    ),
                  },
                ]}
              />
            )}
          </Space>
        )}
      </Modal>
    </div>
  );
}
