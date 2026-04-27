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

import { useState, useEffect, useCallback, useMemo, useRef, ChangeEvent, Key, JSX } from 'react';
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
  Segmented,
  Empty,
  Spin,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { TableRowSelection } from 'antd/es/table/interface';
import type { Dayjs } from 'dayjs';
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
  UnorderedListOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { fetchAPI } from '../../api/config';
import {
  listSolicitacoes,
  previewSolicitacao,
  publishSolicitacao,
  resyncSolicitacao,
  cancelSolicitacao,
} from '../../api/solicitacoes';
import { getStatusSummary, reapplyBatch, resyncBatch, type GCalStatusSummary } from '../../api/gcal';
import { MeetLink } from '../../components/MeetLink';
import { getMe } from '../../api/availability';
import { computePermissions } from '../../hooks/usePermissions';
import useGoogleIntegration from '../../hooks/useGoogleIntegration';
import useGoogleGuard from '../../hooks/useGoogleGuard';
import GoogleIntegrationCard from '../../components/google/GoogleIntegrationCard';
import { TIMING } from '../../constants/timing';
import { usePolling } from '../../hooks/usePolling';
import { syncChannel } from '../../services/syncChannel';
import logger from '../../utils/logger';
import type { ID, Solicitacao, GCalStatus, CurrentUser, PaginatedResponse } from '../../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

/** GCAL status colors */
const GCAL_STATUS_COLORS: Record<string, string> = {
  NONE: 'default',
  PENDING: 'processing',
  PUBLISHED: 'success',
  ERROR: 'error',
};

/** Google Calendar event from API */
interface GoogleCalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  status: string;
  htmlLink: string;
  location: string;
  creator: string;
}

type ViewMode = 'preagenda' | 'gcal-events';

/** Preview data type */
interface PreviewDataType {
  preview: {
    payload?: {
      summary?: string;
      start?: { dateTime?: string };
      end?: { dateTime?: string };
      location?: string;
      description?: string;
      conferenceData?: unknown;
      attendees?: Array<{ email: string; responseStatus?: string }>;
    };
    event_id?: string;
    payload_hash?: string;
    meet_link?: string;
  };
}

export default function PreAgendaPage(): JSX.Element {
  const [loading, setLoading] = useState<boolean>(false);
  const [rows, setRows] = useState<Solicitacao[]>([]);
  const [total, setTotal] = useState<number>(0);

  const [summary, setSummary] = useState<GCalStatusSummary>({
    counts: { NONE: 0, PENDING: 0, PUBLISHED: 0, ERROR: 0 },
    total: 0,
  });

  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sectorFilter, setSectorFilter] = useState<string>('');
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);

  const [previewVisible, setPreviewVisible] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<PreviewDataType | null>(null);

  // Issue #95: Batch operations - Row selection
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [batchLoading, setBatchLoading] = useState<boolean>(false);

  // View mode: pré-agenda (solicitações) ou eventos Google Calendar
  const [viewMode, setViewMode] = useState<ViewMode>('preagenda');
  const [gcalEvents, setGcalEvents] = useState<GoogleCalendarEvent[]>([]);
  const [loadingGcalEvents, setLoadingGcalEvents] = useState(false);

  // OAuth Phase 5: Estado do usuário e integração Google
  const [user, setUser] = useState<CurrentUser | null>(null);
  const { status: googleStatus, disconnect: googleDisconnect } = useGoogleIntegration();

  // Section 4 Epic #459: Consolidated Google OAuth guard
  const { requireGoogleConnection, handleGoogleError } = useGoogleGuard({
    googleStatus,
    returnTo: '/pre-agenda',
  });

  // Carregar dados do usuário
  useEffect(() => {
    const loadUser = async (): Promise<void> => {
      try {
        const userData = await getMe();
        setUser(userData);
      } catch (error) {
        logger.error('Erro ao carregar usuário:', error);
      }
    };
    loadUser();
  }, []);

  const loadData = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);

      const filters: Record<string, string> = { status: 'approved' };
      if (searchTerm) filters.q = searchTerm;
      if (sectorFilter) filters.sector = sectorFilter;
      if (dateRange[0]) filters.date_from = dateRange[0].format('YYYY-MM-DD');
      if (dateRange[1]) filters.date_to = dateRange[1].format('YYYY-MM-DD');

      // Carregar ambos os fluxos e resumo
      const [superData, naoSuperData, summaryData] = await Promise.all([
        listSolicitacoes({ ...filters, flow: 'SUPER' }) as Promise<PaginatedResponse<Solicitacao> | Solicitacao[]>,
        listSolicitacoes({ ...filters, flow: 'NAO_SUPER' }) as Promise<PaginatedResponse<Solicitacao> | Solicitacao[]>,
        getStatusSummary(filters),
      ]);

      const superRows = 'results' in superData ? superData.results : superData;
      const naoRows = 'results' in naoSuperData ? naoSuperData.results : naoSuperData;
      const superCount = 'count' in superData ? superData.count : (superData as Solicitacao[]).length;
      const naoCount = 'count' in naoSuperData ? naoSuperData.count : (naoSuperData as Solicitacao[]).length;

      setRows([...superRows, ...naoRows]);
      setTotal(superCount + naoCount);
      setSummary(summaryData);
    } catch (error) {
      message.error('Erro ao carregar pré-agenda: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, sectorFilter, dateRange]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // RT-02: Polling 5s for cross-device sync (#1032)
  const loadDataRef = useRef(loadData);
  loadDataRef.current = loadData;
  usePolling(() => loadDataRef.current(), {
    enabled: true,
    intervalMs: TIMING.SYNC_POLL_INTERVAL_MS,
    events: ['preagenda:refresh', 'solicitacoes:refresh'],
  });

  // RT-02: BroadcastChannel for instant cross-tab sync
  useEffect(() => {
    const unsub1 = syncChannel.subscribe('preagenda', () => { loadData(); });
    const unsub2 = syncChannel.subscribe('solicitacoes', () => { loadData(); });
    return () => { unsub1(); unsub2(); };
  }, [loadData]);

  // Issue #260: Memoizar handlers para evitar re-renderização desnecessária
  const handlePreview = useCallback(async (id: ID): Promise<void> => {
    try {
      const data = await previewSolicitacao(id) as unknown as PreviewDataType;
      setPreviewData(data);
      setPreviewVisible(true);
    } catch (error) {
      message.error('Erro ao visualizar payload: ' + (error as Error).message);
    }
  }, []);

  const handlePublish = useCallback((id: ID): void => {
    // Section 4 Epic #459: Use consolidated Google guard
    if (!requireGoogleConnection('publicar eventos')) return;

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
          // Section 4 Epic #459: Use consolidated error handler
          if (handleGoogleError(error)) return;
          message.error('Erro ao publicar: ' + (error as Error).message);
        }
      },
    });
  }, [requireGoogleConnection, handleGoogleError, loadData]);

  const handleResync = useCallback((id: ID): void => {
    // Section 4 Epic #459: Use consolidated Google guard
    if (!requireGoogleConnection('reenviar eventos')) return;

    Modal.confirm({
      title: 'Confirmar Reenvio',
      icon: <SyncOutlined className="text-yellow-500" />,
      content: (
        <div>
          <p>Deseja reenviar (forçar UPDATE) este evento no Google Calendar?</p>
          <p className="text-gray-500 text-xs">
            Esta ação irá sobrescrever o evento existente com os dados atualizados.
          </p>
        </div>
      ),
      okText: 'Reenviar',
      okType: 'default',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await resyncSolicitacao(id);
          message.success('Reenvio solicitado! O evento será atualizado em instantes.');
          loadData();
        } catch (error) {
          // Section 4 Epic #459: Use consolidated error handler
          if (handleGoogleError(error)) return;
          message.error('Erro ao reenviar: ' + (error as Error).message);
        }
      },
    });
  }, [requireGoogleConnection, handleGoogleError, loadData]);

  const handleCancel = useCallback((id: ID): void => {
    Modal.confirm({
      title: 'Confirmar Cancelamento',
      icon: <StopOutlined className="text-red-500" />,
      content: (
        <div>
          <p>Deseja cancelar este evento no Google Calendar?</p>
          <p className="text-red-500 font-bold text-xs">
            Atenção: Esta ação irá deletar permanentemente o evento do Calendar e limpar todos os campos relacionados (event_id, meet_link, etc.).
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
          message.error('Erro ao cancelar: ' + (error as Error).message);
        }
      },
    });
  }, [loadData]);

  // Issue #95: Batch Reapply
  const handleBatchReapply = (): void => {
    // Section 4 Epic #459: Use consolidated Google guard
    if (!requireGoogleConnection('realizar ações em massa')) return;

    if (selectedRowKeys.length === 0) {
      message.warning('Selecione ao menos um evento para reaplica');
      return;
    }

    Modal.confirm({
      title: `Confirmar Reapply em Massa (${selectedRowKeys.length} eventos)`,
      icon: <SyncOutlined className="text-yellow-500" />,
      content: (
        <div>
          <p>Deseja reenviar (forçar UPDATE) estes {selectedRowKeys.length} eventos no Google Calendar?</p>
          <p className="text-gray-500 text-xs">
            Esta ação irá sobrescrever os eventos existentes com os dados atualizados.
          </p>
        </div>
      ),
      okText: 'Reenviar',
      okType: 'default',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const data = await reapplyBatch({
            ids: selectedRowKeys as ID[],
            dry_run: false,
            apply_blocked: true,
          });

          message.success(`${data.queued} eventos enfileirados para reapply!`);
          if (data.errors && data.errors.length > 0) {
            message.warning(
              `${data.errors.length} erros: ${data.errors.map((e) => e.detail || e.error || 'erro').join(', ')}`
            );
          }
          setSelectedRowKeys([]);
          loadData();
        } catch (error) {
          if (handleGoogleError(error)) return;
          message.error('Erro ao reenviar em massa: ' + (error as Error).message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // Issue #95: Batch Resync
  const handleBatchResync = (): void => {
    // Section 4 Epic #459: Use consolidated Google guard
    if (!requireGoogleConnection('realizar ações em massa')) return;

    if (selectedRowKeys.length === 0) {
      message.warning('Selecione ao menos um evento para resync');
      return;
    }

    Modal.confirm({
      title: `Confirmar Resync em Massa (${selectedRowKeys.length} eventos)`,
      icon: <SyncOutlined className="text-red-500" />,
      content: (
        <div>
          <p>Deseja forçar resync (resetar hash + PENDING) destes {selectedRowKeys.length} eventos?</p>
          <p className="text-gray-500 text-xs">
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
          const data = await resyncBatch({
            ids: selectedRowKeys as ID[],
            dry_run: false,
            apply_blocked: true,
          });

          message.success(`${data.queued} eventos enfileirados para resync!`);
          if (data.errors && data.errors.length > 0) {
            message.warning(
              `${data.errors.length} erros: ${data.errors.map((e) => e.detail || e.error || 'erro').join(', ')}`
            );
          }
          setSelectedRowKeys([]);
          loadData();
        } catch (error) {
          if (handleGoogleError(error)) return;
          message.error('Erro ao resync em massa: ' + (error as Error).message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // Issue #260: Memoizar columns para evitar re-renderização desnecessária da tabela
  const columns: ColumnsType<Solicitacao> = useMemo(() => [
    {
      title: 'Data/Hora',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (inicio: string) => dayjs(inicio).format('DD/MM/YYYY HH:mm'),
      width: 150,
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio_nome',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto_nome',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      render: (tipo: string | null) => tipo || '-',
    },
    {
      title: 'GCal Status',
      dataIndex: 'gcal_status',
      key: 'gcal_status',
      render: (gcal_status: GCalStatus) => (
        <Tag color={GCAL_STATUS_COLORS[gcal_status] || 'default'}>{gcal_status || 'NONE'}</Tag>
      ),
      width: 120,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 200,
      render: (_, record) => {
        const isPublished = record.gcal_status === ('PUBLISHED' as GCalStatus);
        const hasError = record.gcal_status === ('ERROR' as GCalStatus);
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
              aria-label="Visualizar preview do evento"
            />
            <Button
              size="small"
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={() => handlePublish(record.id)}
              aria-label="Publicar evento no Google Calendar"
              disabled={isPublished}
            />
            {showResync && (
              <Button
                size="small"
                type="default"
                icon={<SyncOutlined />}
                onClick={() => handleResync(record.id)}
                aria-label="Reenviar evento (forçar atualização)"
                style={{ color: '#faad14', borderColor: '#faad14' }}
              />
            )}
            {showCancel && (
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => handleCancel(record.id)}
                aria-label="Cancelar evento no Google Calendar"
              />
            )}
            <MeetLink href={record.meet_link} />
          </Space>
        );
      },
    },
  ], [handlePreview, handlePublish, handleResync, handleCancel]);

  // Google Calendar events loader
  const loadGcalEvents = useCallback(async (): Promise<void> => {
    try {
      setLoadingGcalEvents(true);
      const params = new URLSearchParams();
      if (dateRange[0]) params.set('time_min', dateRange[0].format('YYYY-MM-DD'));
      if (dateRange[1]) params.set('time_max', dateRange[1].format('YYYY-MM-DD'));
      params.set('max_results', '250');

      const data = await fetchAPI<{ events: GoogleCalendarEvent[]; count: number }>(
        `/integrations/google/events/?${params.toString()}`
      );
      setGcalEvents(data.events || []);
    } catch (error) {
      message.error('Erro ao carregar eventos do Google Calendar');
      logger.error('Erro ao carregar eventos GCal:', error);
    } finally {
      setLoadingGcalEvents(false);
    }
  }, [dateRange]);

  // Carregar eventos GCal quando mudar para a aba
  useEffect(() => {
    if (viewMode === 'gcal-events' && googleStatus?.connected) {
      loadGcalEvents();
    }
  }, [viewMode, googleStatus?.connected, loadGcalEvents]);

  const formatGcalDate = (dateStr: string): string => {
    if (!dateStr) return '-';
    try {
      return dayjs(dateStr).format('DD/MM/YYYY HH:mm');
    } catch {
      return dateStr;
    }
  };

  const gcalEventsColumns: ColumnsType<GoogleCalendarEvent> = [
    {
      title: 'Evento',
      dataIndex: 'summary',
      key: 'summary',
      ellipsis: true,
      filterSearch: true,
    },
    {
      title: 'Início',
      dataIndex: 'start',
      key: 'start',
      width: 160,
      render: (val: string) => formatGcalDate(val),
      sorter: (a: GoogleCalendarEvent, b: GoogleCalendarEvent) => a.start.localeCompare(b.start),
      defaultSortOrder: 'ascend',
    },
    {
      title: 'Fim',
      dataIndex: 'end',
      key: 'end',
      width: 160,
      render: (val: string) => formatGcalDate(val),
    },
    {
      title: 'Local',
      dataIndex: 'location',
      key: 'location',
      ellipsis: true,
      render: (val: string) => val || '-',
    },
    {
      title: 'Criador',
      dataIndex: 'creator',
      key: 'creator',
      ellipsis: true,
      width: 200,
    },
    {
      title: 'Link',
      dataIndex: 'htmlLink',
      key: 'htmlLink',
      width: 70,
      render: (val: string) =>
        val ? (
          <a href={val} target="_blank" rel="noopener noreferrer">
            <LinkOutlined />
          </a>
        ) : '-',
    },
  ];

  // OAuth Phase 5: RBAC — verificar se é Controle ou Super.
  // Epic 3.3 cleanup: usa flags derivadas do usePermissions (SSOT).
  const userPerms = user ? computePermissions(user) : null;
  const showGoogleCard = !!(userPerms?.canControle || userPerms?.canSeeAllSectors);

  // Handlers para o card Google
  const handleGoogleConnect = (): void => {
    window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
  };

  const handleGoogleDisconnect = async (): Promise<void> => {
    try {
      const result = await googleDisconnect() as { success: boolean; error?: string };

      if (result.success) {
        message.success('Conta Google desconectada com sucesso');
      } else {
        message.error(result.error || 'Erro ao desconectar conta Google');
      }
    } catch (error) {
      message.error('Erro ao desconectar: ' + (error as Error).message);
    }
  };

  // Row selection config
  const rowSelection: TableRowSelection<Solicitacao> = {
    selectedRowKeys,
    onChange: (keys: Key[]) => setSelectedRowKeys(keys),
    selections: [
      Table.SELECTION_ALL,
      Table.SELECTION_INVERT,
      Table.SELECTION_NONE,
    ],
  };

  return (
    <div className="p-6">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={2} className="m-0">
              Pré-agenda
            </Title>
            {googleStatus?.connected && (
              <Segmented
                value={viewMode}
                onChange={(val) => setViewMode(val as ViewMode)}
                options={[
                  { label: 'Solicitações', value: 'preagenda', icon: <UnorderedListOutlined /> },
                  { label: 'Eventos Google Calendar', value: 'gcal-events', icon: <CalendarOutlined /> },
                ]}
              />
            )}
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

        {/* View: Solicitações (Pré-agenda) */}
        {viewMode === 'preagenda' && (
          <>
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
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
                    onSearch={loadData}
                    style={{ width: '100%', maxWidth: 300 }}
                    allowClear
                  />
                  <Input
                    placeholder="Filtrar por setor/projeto"
                    value={sectorFilter}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setSectorFilter(e.target.value)}
                    onPressEnter={loadData}
                    style={{ width: '100%', maxWidth: 200 }}
                    allowClear
                  />
                  <RangePicker
                    value={dateRange}
                    onChange={(dates) => setDateRange(dates || [null, null])}
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
                <div className="mb-4 p-3 bg-blue-50 rounded">
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
                scroll={{ x: "max-content" }}
                columns={columns}
                dataSource={rows}
                loading={loading}
                rowKey="id"
                rowSelection={rowSelection}
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
          </>
        )}

        {/* View: Eventos Google Calendar */}
        {viewMode === 'gcal-events' && (
          <>
            <Card size="small">
              <Space>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => setDateRange(dates || [null, null])}
                  format="DD/MM/YYYY"
                  placeholder={['Data inicial', 'Data final']}
                />
                <Button
                  type="primary"
                  icon={<SyncOutlined />}
                  onClick={loadGcalEvents}
                  loading={loadingGcalEvents}
                >
                  Atualizar
                </Button>
                <Tag color="blue">{gcalEvents.length} eventos</Tag>
              </Space>
            </Card>

            <Card>
              {loadingGcalEvents ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 16 }}>
                    <Text type="secondary">Carregando eventos do Google Calendar...</Text>
                  </div>
                </div>
              ) : gcalEvents.length === 0 ? (
                <Empty
                  description="Nenhum evento encontrado neste calendário"
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
              ) : (
                <Table
                  scroll={{ x: "max-content" }}
                  columns={gcalEventsColumns}
                  dataSource={gcalEvents}
                  rowKey="id"
                  size="small"
                  pagination={{
                    pageSize: 20,
                    showSizeChanger: true,
                    showTotal: (total) => `${total} eventos`,
                  }}
                />
              )}
            </Card>
          </>
        )}
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
              <Title level={4} className="m-0">
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
            {previewData.preview.payload?.attendees && previewData.preview.payload.attendees.length > 0 && (
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

            {/* Informações Técnicas (Colapsável) — apenas superuser (debug widget). Epic 3.3: usa flag isAdmin (SSOT). */}
            {userPerms?.isAdmin && (
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
