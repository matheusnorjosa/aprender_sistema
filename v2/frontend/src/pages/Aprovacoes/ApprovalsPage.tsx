/**
 * ApprovalsPage - Página de aprovação/reprovação de solicitações (Superintendência)
 *
 * Features:
 * - Filtra solicitações pendentes do fluxo SUPER
 * - Botões para preview, aprovar e reprovar
 * - Modal para preview de payload JSON
 * - Confirmação simples para reprovação (sem justificativa obrigatória)
 *
 * PA-06 (Política de Aprovação Manual):
 * - Botões de aprovar/reprovar aparecem para: Superintendência, DAT, e Superusuários
 * - Verifica: is_superuser || is_superintendencia || groups.includes('Superintendência') || groups.includes('DAT')
 * - Conformidade ISO 9241-110: Controle explícito (usuário vê apenas ações permitidas)
 */

import { useState, useEffect, useCallback, useMemo, useRef, ChangeEvent, Key, JSX } from 'react';
import {
  Table,
  Card,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Typography,
  message,
  Modal,
  Descriptions,
  Divider,
  List,
  Avatar,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { TableRowSelection } from 'antd/es/table/interface';
import {
  CalendarOutlined,
  EnvironmentOutlined,
  TeamOutlined,
  MailOutlined,
  LinkOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import {
  listSolicitacoes,
  approveSolicitacao,
  rejectSolicitacao,
  previewSolicitacao,
  approveSolicitacoesBatch,
  rejectSolicitacoesBatch,
} from '../../api/solicitacoes';
import { getMyPolicies } from '../../api/me';
import { computeAccess } from '../../hooks/useCanAccess';
import { TIMING } from '../../constants/timing';
import { usePolling } from '../../hooks/usePolling';
import { syncChannel } from '../../services/syncChannel';
import logger from '../../utils/logger';
import type { ID, Solicitacao, SolicitacaoStatus, PaginatedResponse, Participation, BatchOperationResult } from '../../types';

const { Title, Paragraph, Text } = Typography;

/** Status colors */
const STATUS_COLORS: Record<SolicitacaoStatus, string> = {
  pendente: 'orange',
  aprovado: 'green',
  reprovado: 'red',
};

/** Status labels */
const STATUS_LABELS: Record<SolicitacaoStatus, string> = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
};

/** Preview data type */
interface PreviewDataType {
  preview: {
    payload?: {
      summary?: string;
      start?: { dateTime?: string };
      end?: { dateTime?: string };
      location?: string;
      description?: string;
      attendees?: Array<{ email: string }>;
    };
    event_id?: string;
    payload_hash?: string;
    meet_link?: string;
  };
}

export default function ApprovalsPage(): JSX.Element {
  const [loading, setLoading] = useState<boolean>(false);
  const [rows, setRows] = useState<Solicitacao[]>([]);
  const [total, setTotal] = useState<number>(0);

  const [statusFilter, setStatusFilter] = useState<SolicitacaoStatus | string>('pendente');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const [previewVisible, setPreviewVisible] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<PreviewDataType | null>(null);

  // PA-06: Estado para verificar permissão do usuário (Superintendência, DAT, Superusuários)
  const [canApprove, setCanApprove] = useState<boolean>(false);

  // Estados para seleção em lote
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [batchLoading, setBatchLoading] = useState<boolean>(false);

  const loadData = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      const filters = { flow: 'SUPER' as const, status: statusFilter || 'pendente', q: searchTerm };

      const data = await listSolicitacoes(filters as unknown as Record<string, string>) as PaginatedResponse<Solicitacao> | Solicitacao[];
      const results = 'results' in data ? data.results : data;
      const count = 'count' in data ? data.count : (data as Solicitacao[]).length;
      setRows(results || []);
      setTotal(count || 0);
    } catch (error) {
      message.error('Erro ao carregar solicitações: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // RT-02: Polling 5s for cross-device sync (#1032)
  const loadDataRef = useRef(loadData);
  loadDataRef.current = loadData;
  usePolling(() => loadDataRef.current(), {
    enabled: true,
    intervalMs: TIMING.SYNC_POLL_INTERVAL_MS,
    events: ['solicitacoes:refresh', 'aprovacoes:refresh'],
  });

  // RT-02: BroadcastChannel for instant cross-tab sync
  useEffect(() => {
    const unsub1 = syncChannel.subscribe('solicitacoes', () => { loadData(); });
    const unsub2 = syncChannel.subscribe('aprovacoes', () => { loadData(); });
    return () => { unsub1(); unsub2(); };
  }, [loadData]);

  // PA-06 + PR 3 hardening RBAC (#1308) + PR 10 hardening RBAC (2026-04-30):
  // a fonte exclusiva de autorização passou a ser a policy pública
  // `access_solicitation_approvals` (Gerente da Superintendência OU
  // Assistente Administrativo do Controle). Legacy `can_approve_super`
  // deixou de ser consultado pelo frontend.
  useEffect(() => {
    const loadAccess = async (): Promise<void> => {
      try {
        const policies = await getMyPolicies().catch(() => [] as string[]);
        const access = computeAccess(policies);
        setCanApprove(access.canAccessApprovals);
      } catch (error) {
        logger.error('Erro ao carregar policies:', error);
        setCanApprove(false);
      }
    };
    loadAccess();
  }, []);

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

  const handleApprove = useCallback((id: ID): void => {
    Modal.confirm({
      title: 'Confirmar Aprovação',
      content: 'Deseja aprovar esta solicitação?',
      okText: 'Aprovar',
      okType: 'primary',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await approveSolicitacao(id);
          message.success('Solicitação aprovada com sucesso!');
          loadData();
        } catch (error) {
          message.error('Erro ao aprovar: ' + (error as Error).message);
        }
      },
    });
  }, [loadData]);

  const handleReject = useCallback((id: ID): void => {
    Modal.confirm({
      title: 'Confirmar Reprovação',
      content: 'Deseja reprovar esta solicitação?',
      okText: 'Reprovar',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await rejectSolicitacao(id);
          message.success('Solicitação reprovada.');
          loadData();
        } catch (error) {
          message.error('Erro ao reprovar: ' + (error as Error).message);
        }
      },
    });
  }, [loadData]);

  // Handlers de operações em lote
  const handleBatchApprove = (): void => {
    Modal.confirm({
      title: `Aprovar ${selectedRowKeys.length} solicitação(ões)?`,
      content: 'Esta ação não pode ser desfeita.',
      okText: 'Aprovar Todas',
      okType: 'primary',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const result = await approveSolicitacoesBatch(selectedRowKeys as ID[]) as BatchOperationResult;

          if (result.approved && result.approved > 0) {
            message.success(`${result.approved} solicitação(ões) aprovada(s)!`);
          }
          if (result.errors?.length > 0) {
            message.warning(`${result.errors.length} erro(s) encontrado(s)`);
          }

          setSelectedRowKeys([]);
          loadData();
        } catch (error) {
          message.error('Erro ao aprovar em lote: ' + (error as Error).message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  const handleBatchReject = (): void => {
    Modal.confirm({
      title: `Reprovar ${selectedRowKeys.length} solicitação(ões)?`,
      content: 'Esta ação não pode ser desfeita.',
      okText: 'Reprovar Todas',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const result = await rejectSolicitacoesBatch(selectedRowKeys as ID[]) as BatchOperationResult;

          if (result.rejected && result.rejected > 0) {
            message.success(`${result.rejected} solicitação(ões) reprovada(s)!`);
          }
          if (result.errors?.length > 0) {
            message.warning(`${result.errors.length} erro(s) encontrado(s)`);
          }

          setSelectedRowKeys([]);
          loadData();
        } catch (error) {
          message.error('Erro ao reprovar em lote: ' + (error as Error).message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // Configuração de seleção de linhas
  const rowSelection: TableRowSelection<Solicitacao> | undefined = canApprove ? {
    selectedRowKeys,
    onChange: (keys: Key[]) => setSelectedRowKeys(keys),
    getCheckboxProps: (record: Solicitacao) => ({
      disabled: record.status !== 'pendente', // Só permite selecionar pendentes
    }),
    selections: [
      Table.SELECTION_ALL,
      Table.SELECTION_INVERT,
      Table.SELECTION_NONE,
    ],
  } : undefined;

  // Issue #260: Memoizar columns para evitar re-renderização desnecessária da tabela
  const columns: ColumnsType<Solicitacao> = useMemo(() => [
    {
      title: 'Data/Horário',
      key: 'data_horario',
      width: 140,
      render: (_, record) => (
        <div>
          <div>{dayjs(record.inicio).format('DD/MM/YYYY')}</div>
          <small className="text-gray-500">
            {dayjs(record.inicio).format('HH:mm')} - {dayjs(record.fim).format('HH:mm')}
          </small>
        </div>
      ),
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio_nome',
      render: (nome: string | null) => nome || '-',
      width: 130,
      ellipsis: true,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto_nome',
      render: (nome: string | null) => nome || '-',
      width: 130,
      ellipsis: true,
    },
    {
      title: 'Tipo/Enc./Seg.',
      key: 'tipo_encontro_segmento',
      width: 100,
      render: (_, record) => (
        <div style={{ lineHeight: 1.3 }}>
          {record.tipo && <div>{record.tipo}</div>}
          {record.encontro && <small className="text-gray-500">{record.encontro}</small>}
          {record.segmento && <div><small className="text-gray-400">{record.segmento}</small></div>}
          {!record.tipo && !record.encontro && !record.segmento && '-'}
        </div>
      ),
    },
    {
      title: 'Coordenador',
      dataIndex: 'coordenador_nome',
      key: 'coordenador_nome',
      render: (nome: string | null) => nome || '-',
      width: 130,
      ellipsis: true,
    },
    {
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      render: (participations: Participation[] | undefined) => {
        if (!participations || participations.length === 0) return '-';
        const formadores = participations
          .filter((p: Participation) => p.role === 'FORMADOR')
          .map((p: Participation) => p.usuario?.first_name || p.usuario?.last_name || p.email || 'N/A')
          .filter((name: string) => name !== 'N/A')
          .join(', ');
        return formadores || '-';
      },
      width: 150,
      ellipsis: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: SolicitacaoStatus) => (
        <Tag color={STATUS_COLORS[status]}>{STATUS_LABELS[status] || status}</Tag>
      ),
      width: 90,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record.id)}
            aria-label="Visualizar preview do evento"
          />
          {/* PA-06: Botões de aprovar/reprovar para Superintendência, DAT e Superusuários */}
          {record.status === 'pendente' && canApprove ? (
            <>
              <Button
                size="small"
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record.id)}
              >
                Aprovar
              </Button>
              <Button
                size="small"
                danger
                icon={<CloseOutlined />}
                onClick={() => handleReject(record.id)}
              >
                Reprovar
              </Button>
            </>
          ) : null}
        </Space>
      ),
    },
  ], [handlePreview, handleApprove, handleReject, canApprove]);

  return (
    <section className="p-6" aria-labelledby="aprovacoes-title">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Header semantico */}
          <header>
            <Title level={2} id="aprovacoes-title">Aprovações</Title>
          </header>

          {/* Filtros */}
          <nav aria-label="Filtros de busca">
            <Space>
              <Select
                value={statusFilter}
                onChange={setStatusFilter}
                style={{ width: '100%', maxWidth: 200 }}
                placeholder="Status"
                aria-label="Filtrar por status"
              >
                <Select.Option value="pendente">Pendentes</Select.Option>
                <Select.Option value="aprovado">Aprovadas</Select.Option>
                <Select.Option value="reprovado">Reprovadas</Select.Option>
              </Select>

              <Input.Search
                placeholder="Buscar por município, projeto, autor..."
                value={searchTerm}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
                onSearch={loadData}
                style={{ width: '100%', maxWidth: 400 }}
                allowClear
                aria-label="Buscar solicitacoes"
              />
            </Space>
          </nav>

          {/* Contagem de pendentes */}
          {statusFilter === 'pendente' && total > 0 && (
            <aside aria-label="Contador de pendentes">
              <Paragraph>
                <Tag color="orange">{total}</Tag> solicitações aguardando aprovação
              </Paragraph>
            </aside>
          )}

          {/* Toolbar de ações em lote (PA-06: apenas para usuários com permissão) */}
          {selectedRowKeys.length > 0 && canApprove && (
            <nav aria-label="Acoes em lote" className="mb-4 p-3 bg-blue-50 rounded border border-blue-200">
              <Space>
                <Text strong aria-live="polite">
                  {selectedRowKeys.length} solicitação(ões) selecionada(s)
                </Text>
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  onClick={handleBatchApprove}
                  loading={batchLoading}
                >
                  Aprovar Selecionadas
                </Button>
                <Button
                  danger
                  icon={<CloseOutlined />}
                  onClick={handleBatchReject}
                  loading={batchLoading}
                >
                  Reprovar Selecionadas
                </Button>
                <Button type="link" onClick={() => setSelectedRowKeys([])}>
                  Limpar Seleção
                </Button>
              </Space>
            </nav>
          )}

          {/* Tabela */}
          <section aria-label="Lista de solicitacoes para aprovacao">
            <Table
              rowSelection={rowSelection}
              columns={columns}
              dataSource={rows}
              loading={loading}
              rowKey="id"
              scroll={{ x: 1090 }}
              pagination={{
                total,
                pageSize: 20,
                showTotal: (total) => `Total: ${total} solicitações`,
              }}
            />
          </section>
        </Space>
      </Card>

      {/* Modal Preview - Visualização Amigável */}
      <Modal
        title={
          <Space>
            <CalendarOutlined />
            <span>Preview do Evento no Google Calendar</span>
          </Space>
        }
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Fechar
          </Button>,
        ]}
        width={700}
      >
        {previewData?.preview?.payload && (() => {
          const payload = previewData.preview.payload;
          const start = payload.start?.dateTime ? dayjs(payload.start.dateTime) : null;
          const end = payload.end?.dateTime ? dayjs(payload.end.dateTime) : null;

          return (
            <div style={{ maxHeight: 500, overflow: 'auto' }}>
              {/* Título do Evento */}
              <Card size="small" className="mb-4" style={{ background: '#f0f5ff' }}>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {payload.summary}
                </Typography.Title>
              </Card>

              {/* Informações Principais */}
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item
                  label={<><CalendarOutlined /> Data/Horário</>}
                >
                  {start && end ? (
                    <>
                      <Tag color="blue">{start.format('DD/MM/YYYY')}</Tag>
                      <span style={{ marginLeft: 8 }}>
                        {start.format('HH:mm')} às {end.format('HH:mm')}
                      </span>
                    </>
                  ) : '-'}
                </Descriptions.Item>

                <Descriptions.Item
                  label={<><EnvironmentOutlined /> Local</>}
                >
                  {payload.location || '-'}
                </Descriptions.Item>

                {previewData.preview.meet_link && (
                  <Descriptions.Item
                    label={<><VideoCameraOutlined /> Google Meet</>}
                  >
                    <a href={previewData.preview.meet_link} target="_blank" rel="noopener noreferrer">
                      <LinkOutlined /> {previewData.preview.meet_link}
                    </a>
                  </Descriptions.Item>
                )}
              </Descriptions>

              {/* Descrição */}
              {payload.description && (
                <>
                  <Divider orientation="left" className="mt-4">Descrição</Divider>
                  <Card size="small" className="bg-gray-50">
                    <pre style={{
                      whiteSpace: 'pre-wrap',
                      margin: 0,
                      fontFamily: 'inherit',
                      fontSize: 13
                    }}>
                      {payload.description}
                    </pre>
                  </Card>
                </>
              )}

              {/* Participantes */}
              {payload.attendees && payload.attendees.length > 0 && (
                <>
                  <Divider orientation="left" className="mt-4">
                    <TeamOutlined /> Participantes ({payload.attendees.length})
                  </Divider>
                  <List
                    size="small"
                    dataSource={payload.attendees}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={<Avatar size="small" icon={<MailOutlined />} />}
                          title={item.email}
                        />
                      </List.Item>
                    )}
                  />
                </>
              )}

              {/* Metadados (colapsável) */}
              <Divider orientation="left" className="mt-4">Metadados</Divider>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="ID Evento">
                  <Tag>{previewData.preview.event_id}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Hash Payload">
                  <Tag color="default" style={{ fontSize: 10 }}>
                    {previewData.preview.payload_hash?.substring(0, 12)}...
                  </Tag>
                </Descriptions.Item>
              </Descriptions>
            </div>
          );
        })()}

        {/* Fallback para JSON se não tiver payload */}
        {!previewData?.preview?.payload && (
          <pre style={{ maxHeight: 500, overflow: 'auto', backgroundColor: '#f5f5f5', padding: 12 }}>
            {JSON.stringify(previewData, null, 2)}
          </pre>
        )}
      </Modal>

    </section>
  );
}
