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

import { useState, useEffect, useCallback, useMemo } from 'react';
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
import { getMe } from '../../api/availability';
import logger from '../../utils/logger';

const { Title, Paragraph, Text } = Typography;

const STATUS_COLORS = {
  pendente: 'orange',
  aprovado: 'green',
  reprovado: 'red',
};

const STATUS_LABELS = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
};

export default function ApprovalsPage() {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);

  const [statusFilter, setStatusFilter] = useState('pendente');
  const [searchTerm, setSearchTerm] = useState('');

  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  // PA-06: Estado para verificar permissão do usuário (Superintendência, DAT, Superusuários)
  const [canApprove, setCanApprove] = useState(false);

  // Estados para seleção em lote
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [batchLoading, setBatchLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const filters = { flow: 'SUPER', status: statusFilter || 'pendente', q: searchTerm };

      const data = await listSolicitacoes(filters);
      setRows(data.results || data);
      setTotal(data.count || data.length);
    } catch (error) {
      message.error('Erro ao carregar solicitações: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // PA-06: Carregar dados do usuário e verificar permissão
  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await getMe();

        // Usar can_approve_super da API (Gerente + Superintendência)
        // A API já calcula: is_superuser || (Gerente in funcoes && Superintendência in setores)
        setCanApprove(userData?.can_approve_super || false);
      } catch (error) {
        logger.error('Erro ao carregar usuário:', error);
        setCanApprove(false);
      }
    };
    loadUser();
  }, []);

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

  const handleApprove = useCallback((id) => {
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
          message.error('Erro ao aprovar: ' + error.message);
        }
      },
    });
  }, [loadData]);

  const handleReject = useCallback((id) => {
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
          message.error('Erro ao reprovar: ' + error.message);
        }
      },
    });
  }, [loadData]);

  // Handlers de operações em lote
  const handleBatchApprove = () => {
    Modal.confirm({
      title: `Aprovar ${selectedRowKeys.length} solicitação(ões)?`,
      content: 'Esta ação não pode ser desfeita.',
      okText: 'Aprovar Todas',
      okType: 'primary',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const result = await approveSolicitacoesBatch(selectedRowKeys);

          if (result.approved > 0) {
            message.success(`${result.approved} solicitação(ões) aprovada(s)!`);
          }
          if (result.errors?.length > 0) {
            message.warning(`${result.errors.length} erro(s) encontrado(s)`);
          }

          setSelectedRowKeys([]);
          loadData();
        } catch (error) {
          message.error('Erro ao aprovar em lote: ' + error.message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  const handleBatchReject = () => {
    Modal.confirm({
      title: `Reprovar ${selectedRowKeys.length} solicitação(ões)?`,
      content: 'Esta ação não pode ser desfeita.',
      okText: 'Reprovar Todas',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const result = await rejectSolicitacoesBatch(selectedRowKeys);

          if (result.rejected > 0) {
            message.success(`${result.rejected} solicitação(ões) reprovada(s)!`);
          }
          if (result.errors?.length > 0) {
            message.warning(`${result.errors.length} erro(s) encontrado(s)`);
          }

          setSelectedRowKeys([]);
          loadData();
        } catch (error) {
          message.error('Erro ao reprovar em lote: ' + error.message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // Configuração de seleção de linhas
  const rowSelection = canApprove ? {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
    getCheckboxProps: (record) => ({
      disabled: record.status !== 'pendente', // Só permite selecionar pendentes
    }),
    selections: [
      Table.SELECTION_ALL,
      Table.SELECTION_INVERT,
      Table.SELECTION_NONE,
    ],
  } : undefined;

  // Issue #260: Memoizar columns para evitar re-renderização desnecessária da tabela
  const columns = useMemo(() => [
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
      render: (nome) => nome || '-',
      width: 130,
      ellipsis: true,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto_nome',
      render: (nome) => nome || '-',
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
      render: (nome) => nome || '-',
      width: 130,
      ellipsis: true,
    },
    {
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      render: (participations) => {
        if (!participations || participations.length === 0) return '-';
        const formadores = participations
          .filter(p => p.role === 'FORMADOR')
          .map(p => p.usuario?.first_name || p.usuario?.last_name || p.email || 'N/A')
          .filter(name => name !== 'N/A')
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
      render: (status) => (
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
    <div className="p-6">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Header */}
          <Title level={2}>Aprovações</Title>

          {/* Filtros */}
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 200 }}
              placeholder="Status"
            >
              <Select.Option value="pendente">Pendentes</Select.Option>
              <Select.Option value="aprovado">Aprovadas</Select.Option>
              <Select.Option value="reprovado">Reprovadas</Select.Option>
            </Select>

            <Input.Search
              placeholder="Buscar por município, projeto, autor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onSearch={loadData}
              style={{ width: 400 }}
              allowClear
            />
          </Space>

          {/* Contagem de pendentes */}
          {statusFilter === 'pendente' && total > 0 && (
            <Paragraph>
              <Tag color="orange">{total}</Tag> solicitações aguardando aprovação
            </Paragraph>
          )}

          {/* Toolbar de ações em lote (PA-06: apenas para usuários com permissão) */}
          {selectedRowKeys.length > 0 && canApprove && (
            <div className="mb-4 p-3 bg-blue-50 rounded border border-blue-200">
              <Space>
                <Text strong>
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
            </div>
          )}

          {/* Tabela */}
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
                  <Card size="small" style={{ background: '#fafafa' }}>
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

    </div>
  );
}
