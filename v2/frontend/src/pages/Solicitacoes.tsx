/**
 * Página de Solicitações (Superintendência)
 *
 * Permite que usuários do grupo Superintendência:
 * - Visualizem solicitações de eventos (filtros por status)
 * - Aprovem ou reprovem solicitações pendentes
 * - Vejam detalhes completos de cada solicitação
 */

import { useState, useEffect, useCallback, ChangeEvent, JSX } from 'react';
import {
  Table,
  Tag,
  Button,
  Input,
  Select,
  Drawer,
  Space,
  message,
  Modal,
  Form,
  Spin,
  Card,
  Descriptions,
  Alert,
} from 'antd';
import type { ColumnsType, TablePaginationConfig, FilterValue, SorterResult } from 'antd/es/table/interface';
import {
  CheckOutlined,
  CloseOutlined,
  EyeOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  listSolicitacoes,
  getSolicitacao,
  approveSolicitacao,
  rejectSolicitacao,
} from '../api/solicitacoes';
import { getMe } from '../api/availability';
import { MeetLink } from '../components/MeetLink';
import logger from '../utils/logger';
import type { ID, Solicitacao, SolicitacaoStatus, PaginatedResponse } from '../types';

const { TextArea } = Input;

/** Status colors mapping */
const STATUS_COLORS: Record<SolicitacaoStatus, string> = {
  pendente: 'gold',
  aprovado: 'green',
  reprovado: 'red',
};

/** Form values for rejection */
interface RejectFormValues {
  justificativa?: string;
}

/**
 * Formata data/hora para exibição
 */
function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) return '-';
  return dayjs(dateString).format('DD/MM/YYYY HH:mm');
}

function Solicitacoes(): JSX.Element {
  // Estado da tabela
  const [solicitacoes, setSolicitacoes] = useState<Solicitacao[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  // Filtros
  const [statusFilter, setStatusFilter] = useState<SolicitacaoStatus | ''>('pendente');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Drawer de detalhes
  const [drawerVisible, setDrawerVisible] = useState<boolean>(false);
  const [selectedSolicitacao, setSelectedSolicitacao] = useState<Solicitacao | null>(null);
  const [loadingDetails, setLoadingDetails] = useState<boolean>(false);

  // Modal de reprovação
  const [rejectModalVisible, setRejectModalVisible] = useState<boolean>(false);
  const [rejectForm] = Form.useForm<RejectFormValues>();
  const [processingAction, setProcessingAction] = useState<boolean>(false);

  // Usuário atual
  const [isSuperintendencia, setIsSuperintendencia] = useState<boolean>(false);
  const [loadingUser, setLoadingUser] = useState<boolean>(true);

  /**
   * Busca informações do usuário atual e verifica permissão PA-06
   */
  useEffect(() => {
    async function fetchCurrentUser(): Promise<void> {
      try {
        const user = await getMe();

        // PA-06: Verificar se usuário pertence ao grupo "Superintendência" ou é superuser
        const isSuper =
          user?.is_superuser ||
          user?.is_superintendencia ||
          user?.groups?.includes('Superintendência') ||
          false;
        setIsSuperintendencia(isSuper);
      } catch (error) {
        logger.error('Erro ao buscar usuário:', error);
        setIsSuperintendencia(false);
      } finally {
        setLoadingUser(false);
      }
    }
    fetchCurrentUser();
  }, []);

  /**
   * Carrega solicitações com filtros e paginação
   */
  const fetchSolicitacoes = useCallback(async (page = 1): Promise<void> => {
    setLoading(true);
    try {
      const data = await listSolicitacoes({
        status: statusFilter || undefined,
        page,
        search: searchTerm,
      }) as PaginatedResponse<Solicitacao>;

      setSolicitacoes(data.results || []);
      setPagination({
        current: page,
        pageSize: 10,
        total: data.count || 0,
      });
    } catch (error) {
      message.error(`Erro ao carregar solicitações: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  /**
   * Recarrega quando filtros mudam
   */
  useEffect(() => {
    fetchSolicitacoes(1);
  }, [fetchSolicitacoes]);

  /**
   * Mudança de página
   */
  const handleTableChange = (
    newPagination: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    _sorter: SorterResult<Solicitacao> | SorterResult<Solicitacao>[]
  ): void => {
    fetchSolicitacoes(newPagination.current);
  };

  /**
   * Abre drawer com detalhes da solicitação
   */
  const handleViewDetails = async (record: Solicitacao): Promise<void> => {
    setDrawerVisible(true);
    setLoadingDetails(true);
    try {
      const details = await getSolicitacao(record.id) as Solicitacao;
      setSelectedSolicitacao(details);
    } catch (error) {
      message.error(`Erro ao carregar detalhes: ${(error as Error).message}`);
      setDrawerVisible(false);
    } finally {
      setLoadingDetails(false);
    }
  };

  /**
   * Aprova solicitação
   */
  const handleApprove = async (id: ID): Promise<void> => {
    Modal.confirm({
      title: 'Confirmar Aprovação',
      content: 'Tem certeza que deseja aprovar esta solicitação?',
      okText: 'Aprovar',
      cancelText: 'Cancelar',
      onOk: async () => {
        setProcessingAction(true);
        try {
          await approveSolicitacao(id);
          message.success('Solicitação aprovada com sucesso!');
          setDrawerVisible(false);
          fetchSolicitacoes(pagination.current);
        } catch (error) {
          message.error(`Erro ao aprovar: ${(error as Error).message}`);
        } finally {
          setProcessingAction(false);
        }
      },
    });
  };

  /**
   * Abre modal de reprovação
   */
  const handleOpenRejectModal = (id: ID): void => {
    setSelectedSolicitacao({ ...selectedSolicitacao!, id });
    setRejectModalVisible(true);
  };

  /**
   * Reprova solicitação com justificativa (opcional)
   */
  const handleReject = async (values: RejectFormValues): Promise<void> => {
    setProcessingAction(true);
    try {
      await rejectSolicitacao(selectedSolicitacao!.id, values.justificativa || '');
      message.success('Solicitação reprovada.');
      setRejectModalVisible(false);
      setDrawerVisible(false);
      rejectForm.resetFields();
      fetchSolicitacoes(pagination.current);
    } catch (error) {
      message.error(`Erro ao reprovar: ${(error as Error).message}`);
    } finally {
      setProcessingAction(false);
    }
  };

  /**
   * Colunas da tabela
   */
  const columns: ColumnsType<Solicitacao> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      sorter: (a, b) => a.id - b.id,
    },
    {
      title: 'Usuário',
      dataIndex: 'usuario_username',
      key: 'usuario_username',
      render: (username: string | null) => username || '-',
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio_nome',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Tipo Evento',
      dataIndex: 'tipo_evento_nome',
      key: 'tipo_evento_nome',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Início',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (text: string) => formatDateTime(text),
    },
    {
      title: 'Fim',
      dataIndex: 'fim',
      key: 'fim',
      render: (text: string) => formatDateTime(text),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: SolicitacaoStatus) => (
        <Tag color={STATUS_COLORS[status] || 'default'}>
          {status?.toUpperCase() || 'DESCONHECIDO'}
        </Tag>
      ),
      filters: [
        { text: 'Pendente', value: 'pendente' },
        { text: 'Aprovado', value: 'aprovado' },
        { text: 'Reprovado', value: 'reprovado' },
      ],
      filteredValue: statusFilter ? [statusFilter] : [],
    },
    {
      title: 'Ações',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            Ver
          </Button>
          {isSuperintendencia && record.status === 'pendente' && (
            <>
              <Button
                type="primary"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record.id)}
              >
                Aprovar
              </Button>
              <Button
                danger
                size="small"
                icon={<CloseOutlined />}
                onClick={() => {
                  setSelectedSolicitacao(record);
                  setRejectModalVisible(true);
                }}
              >
                Reprovar
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={<h1>Solicitações de Eventos</h1>}
        extra={
          isSuperintendencia && (
            <Tag color="blue">Superintendência</Tag>
          )
        }
      >
        {/* Aviso para usuários não-autorizados (PA-06) */}
        {!loadingUser && !isSuperintendencia && (
          <Alert
            type="warning"
            message="Acesso restrito à Superintendência"
            description="Você pode visualizar as solicitações, mas não tem permissão para aprovar ou reprovar. Apenas usuários do grupo Superintendência podem realizar estas ações."
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Filtros */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Input
            placeholder="Buscar por usuário, município, tipo..."
            prefix={<SearchOutlined />}
            value={searchTerm}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
            style={{ width: 300 }}
            allowClear
          />
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 150 }}
            options={[
              { label: 'Pendente', value: 'pendente' },
              { label: 'Aprovado', value: 'aprovado' },
              { label: 'Reprovado', value: 'reprovado' },
              { label: 'Todos', value: '' },
            ]}
          />
        </Space>

        {/* Tabela */}
        <Table
          columns={columns}
          dataSource={solicitacoes}
          rowKey="id"
          loading={loading}
          pagination={pagination}
          onChange={handleTableChange}
        />
      </Card>

      {/* Drawer de Detalhes */}
      <Drawer
        title="Detalhes da Solicitação"
        placement="right"
        width={600}
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        extra={
          isSuperintendencia &&
          selectedSolicitacao?.status === 'pendente' && (
            <Space>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(selectedSolicitacao.id)}
                loading={processingAction}
              >
                Aprovar
              </Button>
              <Button
                danger
                icon={<CloseOutlined />}
                onClick={() => handleOpenRejectModal(selectedSolicitacao.id)}
                loading={processingAction}
              >
                Reprovar
              </Button>
            </Space>
          )
        }
      >
        {loadingDetails ? (
          <Spin />
        ) : selectedSolicitacao ? (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="ID">{selectedSolicitacao.id}</Descriptions.Item>
            <Descriptions.Item label="Usuário">
              {selectedSolicitacao.usuario_username || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Município">
              {selectedSolicitacao.municipio_nome || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Tipo de Evento">
              {selectedSolicitacao.tipo_evento_nome || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Início">
              {formatDateTime(selectedSolicitacao.inicio)}
            </Descriptions.Item>
            <Descriptions.Item label="Fim">
              {formatDateTime(selectedSolicitacao.fim)}
            </Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={STATUS_COLORS[selectedSolicitacao.status]}>
                {selectedSolicitacao.status?.toUpperCase()}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Observações">
              {selectedSolicitacao.observacoes || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Criado em">
              {formatDateTime(selectedSolicitacao.created_at)}
            </Descriptions.Item>
            <Descriptions.Item label="Atualizado em">
              {formatDateTime(selectedSolicitacao.updated_at)}
            </Descriptions.Item>
            {selectedSolicitacao.meet_link && (
              <Descriptions.Item label="Reunião Online">
                <MeetLink href={selectedSolicitacao.meet_link} />
              </Descriptions.Item>
            )}
          </Descriptions>
        ) : null}
      </Drawer>

      {/* Modal de Reprovação */}
      <Modal
        title="Reprovar Solicitação"
        open={rejectModalVisible}
        onCancel={() => {
          setRejectModalVisible(false);
          rejectForm.resetFields();
        }}
        onOk={() => rejectForm.submit()}
        confirmLoading={processingAction}
        okText="Reprovar"
        cancelText="Cancelar"
        okButtonProps={{ danger: true }}
      >
        <Form form={rejectForm} onFinish={handleReject} layout="vertical">
          <Form.Item
            name="justificativa"
            label="Justificativa (opcional)"
          >
            <TextArea
              rows={4}
              placeholder="Descreva o motivo da reprovação (opcional)..."
              maxLength={500}
              showCount
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default Solicitacoes;
