/**
 * Página de Solicitações (Superintendência)
 *
 * Permite que usuários do grupo Superintendência:
 * - Visualizem solicitações de eventos (filtros por status)
 * - Aprovem ou reprovem solicitações pendentes
 * - Vejam detalhes completos de cada solicitação
 */

import { useState, useEffect } from 'react';
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

const { TextArea } = Input;

/**
 * Mapeia status para cores de tags
 */
const STATUS_COLORS = {
  pendente: 'gold',
  aprovado: 'green',
  reprovado: 'red',
};

/**
 * Formata data/hora para exibição
 */
function formatDateTime(dateString) {
  if (!dateString) return '-';
  return dayjs(dateString).format('DD/MM/YYYY HH:mm');
}

function Solicitacoes() {
  // Estado da tabela
  const [solicitacoes, setSolicitacoes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  // Filtros
  const [statusFilter, setStatusFilter] = useState('pendente');
  const [searchTerm, setSearchTerm] = useState('');

  // Drawer de detalhes
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedSolicitacao, setSelectedSolicitacao] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Modal de reprovação
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [rejectForm] = Form.useForm();
  const [processingAction, setProcessingAction] = useState(false);

  // Usuário atual
  const [currentUser, setCurrentUser] = useState(null);
  const [isSuperintendencia, setIsSuperintendencia] = useState(false);
  const [loadingUser, setLoadingUser] = useState(true);

  /**
   * Busca informações do usuário atual e verifica permissão PA-06
   */
  useEffect(() => {
    async function fetchCurrentUser() {
      try {
        const user = await getMe();
        setCurrentUser(user);

        // PA-06: Verificar se usuário pertence ao grupo "Superintendência"
        const isSuper =
          user?.is_superintendencia ||
          user?.groups?.includes('Superintendência') ||
          false;
        setIsSuperintendencia(isSuper);
      } catch (error) {
        console.error('Erro ao buscar usuário:', error);
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
  const fetchSolicitacoes = async (page = 1) => {
    setLoading(true);
    try {
      const data = await listSolicitacoes({
        status: statusFilter,
        page,
        search: searchTerm,
      });

      setSolicitacoes(data.results || []);
      setPagination({
        current: page,
        pageSize: 10,
        total: data.count || 0,
      });
    } catch (error) {
      message.error(`Erro ao carregar solicitações: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Recarrega quando filtros mudam
   */
  useEffect(() => {
    fetchSolicitacoes(1);
  }, [statusFilter, searchTerm]);

  /**
   * Mudança de página
   */
  const handleTableChange = (newPagination) => {
    fetchSolicitacoes(newPagination.current);
  };

  /**
   * Abre drawer com detalhes da solicitação
   */
  const handleViewDetails = async (record) => {
    setDrawerVisible(true);
    setLoadingDetails(true);
    try {
      const details = await getSolicitacao(record.id);
      setSelectedSolicitacao(details);
    } catch (error) {
      message.error(`Erro ao carregar detalhes: ${error.message}`);
      setDrawerVisible(false);
    } finally {
      setLoadingDetails(false);
    }
  };

  /**
   * Aprova solicitação
   */
  const handleApprove = async (id) => {
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
          message.error(`Erro ao aprovar: ${error.message}`);
        } finally {
          setProcessingAction(false);
        }
      },
    });
  };

  /**
   * Abre modal de reprovação
   */
  const handleOpenRejectModal = (id) => {
    setSelectedSolicitacao({ ...selectedSolicitacao, id });
    setRejectModalVisible(true);
  };

  /**
   * Reprova solicitação com justificativa
   */
  const handleReject = async (values) => {
    if (!values.justificativa || values.justificativa.trim() === '') {
      message.error('Justificativa é obrigatória para reprovar.');
      return;
    }

    setProcessingAction(true);
    try {
      await rejectSolicitacao(selectedSolicitacao.id, {
        justificativa: values.justificativa,
      });
      message.success('Solicitação reprovada.');
      setRejectModalVisible(false);
      setDrawerVisible(false);
      rejectForm.resetFields();
      fetchSolicitacoes(pagination.current);
    } catch (error) {
      message.error(`Erro ao reprovar: ${error.message}`);
    } finally {
      setProcessingAction(false);
    }
  };

  /**
   * Colunas da tabela
   */
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      sorter: (a, b) => a.id - b.id,
    },
    {
      title: 'Usuário',
      dataIndex: ['usuario', 'username'],
      key: 'usuario',
      render: (text, record) => record.usuario?.username || record.usuario || '-',
    },
    {
      title: 'Município',
      dataIndex: ['municipio', 'nome'],
      key: 'municipio',
      render: (text, record) => record.municipio?.nome || record.municipio || '-',
    },
    {
      title: 'Tipo Evento',
      dataIndex: ['tipo_evento', 'nome'],
      key: 'tipo_evento',
      render: (text, record) => record.tipo_evento?.nome || record.tipo_evento || '-',
    },
    {
      title: 'Início',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (text) => formatDateTime(text),
    },
    {
      title: 'Fim',
      dataIndex: 'fim',
      key: 'fim',
      render: (text) => formatDateTime(text),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={STATUS_COLORS[status] || 'default'}>
          {status?.toUpperCase() || 'DESCONHECIDO'}
        </Tag>
      ),
      filters: [
        { text: 'Pendente', value: 'pendente' },
        { text: 'Aprovado', value: 'aprovado' },
        { text: 'Reprovado', value: 'reprovado' },
      ],
      filteredValue: [statusFilter],
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
            onChange={(e) => setSearchTerm(e.target.value)}
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
              {selectedSolicitacao.usuario?.username || selectedSolicitacao.usuario || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Município">
              {selectedSolicitacao.municipio?.nome || selectedSolicitacao.municipio || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Tipo de Evento">
              {selectedSolicitacao.tipo_evento?.nome || selectedSolicitacao.tipo_evento || '-'}
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
            label="Justificativa"
            rules={[
              { required: true, message: 'Justificativa é obrigatória' },
              { min: 10, message: 'Justificativa deve ter pelo menos 10 caracteres' },
            ]}
          >
            <TextArea
              rows={4}
              placeholder="Descreva o motivo da reprovação..."
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
