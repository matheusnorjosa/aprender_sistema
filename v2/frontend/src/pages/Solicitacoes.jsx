/**
 * Página de Solicitações (Superintendência)
 *
 * Permite que usuários do grupo Superintendência:
 * - Visualizem solicitações de eventos (filtros por status)
 * - Aprovem ou reprovem solicitações pendentes
 * - Vejam detalhes completos de cada solicitação
 */

import { useState, useEffect, useCallback } from 'react';
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
  DatePicker,
  Row,
  Col,
  Timeline,
  Typography,
} from 'antd';
import {
  CheckOutlined,
  CloseOutlined,
  EyeOutlined,
  SearchOutlined,
  VideoCameraOutlined,
  FilterOutlined,
  ClearOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  listSolicitacoes,
  getSolicitacao,
  approveSolicitacao,
  rejectSolicitacao,
} from '../api/solicitacoes';
import { getMe } from '../api/availability';
import { lookupMunicipios, lookupProjetos } from '../api/lookup';

const { TextArea } = Input;
const { Title: AntTitle, Text } = Typography;

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
  const [dataInicio, setDataInicio] = useState(null);
  const [dataFim, setDataFim] = useState(null);
  const [municipioFilter, setMunicipioFilter] = useState(null);
  const [projetoFilter, setProjetoFilter] = useState(null);
  const [fluxoFilter, setFluxoFilter] = useState('');

  // Options para filtros
  const [municipios, setMunicipios] = useState([]);
  const [projetos, setProjetos] = useState([]);

  // Drawer de detalhes
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedSolicitacao, setSelectedSolicitacao] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Modal de reprovação
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [rejectForm] = Form.useForm();
  const [processingAction, setProcessingAction] = useState(false);

  // Usuário atual
  const [isSuperintendencia, setIsSuperintendencia] = useState(false);
  const [loadingUser, setLoadingUser] = useState(true);

  /**
   * Busca informações do usuário atual e verifica permissão PA-06
   */
  useEffect(() => {
    async function fetchCurrentUser() {
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
        console.error('Erro ao buscar usuário:', error);
        setIsSuperintendencia(false);
      } finally {
        setLoadingUser(false);
      }
    }
    fetchCurrentUser();

    // Carregar opções de filtros
    const loadFilterOptions = async () => {
      try {
        const [municData, projData] = await Promise.all([
          lookupMunicipios(''),
          lookupProjetos(''),
        ]);
        setMunicipios(municData);
        setProjetos(projData);
      } catch (error) {
        console.error('Erro ao carregar opções de filtros:', error);
      }
    };
    loadFilterOptions();
  }, []);

  /**
   * Carrega solicitações com filtros e paginação
   */
  const fetchSolicitacoes = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params = {
        status: statusFilter,
        page,
        search: searchTerm,
      };

      // Adicionar filtros opcionais
      if (dataInicio) {
        params.data_inicio = dayjs(dataInicio).format('YYYY-MM-DD');
      }
      if (dataFim) {
        params.data_fim = dayjs(dataFim).format('YYYY-MM-DD');
      }
      if (municipioFilter) {
        params.municipio_id = municipioFilter;
      }
      if (projetoFilter) {
        params.projeto_id = projetoFilter;
      }
      if (fluxoFilter) {
        params.fluxo = fluxoFilter;
      }

      const data = await listSolicitacoes(params);

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
  }, [statusFilter, searchTerm, dataInicio, dataFim, municipioFilter, projetoFilter, fluxoFilter]);

  /**
   * Recarrega quando filtros mudam
   */
  useEffect(() => {
    fetchSolicitacoes(1);
  }, [fetchSolicitacoes]);

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
   * Reprova solicitação com justificativa (opcional)
   */
  const handleReject = async (values) => {
    setProcessingAction(true);
    try {
      await rejectSolicitacao(selectedSolicitacao.id, {
        justificativa: values.justificativa || '',
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
      title: 'Projeto',
      dataIndex: ['projeto', 'nome'],
      key: 'projeto',
      render: (text, record) => record.projeto?.nome || record.projeto || '-',
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
      title: 'Fluxo',
      dataIndex: 'fluxo',
      key: 'fluxo',
      render: (fluxo) => {
        if (!fluxo) return '-';
        const color = fluxo === 'SUPER' ? 'blue' : 'green';
        const label = fluxo === 'SUPER' ? 'SUPER' : 'NÃO SUPER';
        return <Tag color={color}>{label}</Tag>;
      },
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
        <Card title={<Space><FilterOutlined /> Filtros</Space>} style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8}>
              <label style={{ display: 'block', marginBottom: 4 }}>Data Inicial</label>
              <DatePicker
                style={{ width: '100%' }}
                placeholder="DD/MM/AAAA"
                format="DD/MM/YYYY"
                value={dataInicio}
                onChange={setDataInicio}
                allowClear
              />
            </Col>

            <Col xs={24} sm={12} md={8}>
              <label style={{ display: 'block', marginBottom: 4 }}>Data Final</label>
              <DatePicker
                style={{ width: '100%' }}
                placeholder="DD/MM/AAAA"
                format="DD/MM/YYYY"
                value={dataFim}
                onChange={setDataFim}
                allowClear
              />
            </Col>

            <Col xs={24} sm={12} md={8}>
              <label style={{ display: 'block', marginBottom: 4 }}>Município</label>
              <Select
                style={{ width: '100%' }}
                placeholder="Selecione"
                value={municipioFilter}
                onChange={setMunicipioFilter}
                allowClear
                showSearch
                optionFilterProp="label"
                options={municipios.map(m => ({ label: m.label, value: m.id }))}
              />
            </Col>

            <Col xs={24} sm={12} md={8}>
              <label style={{ display: 'block', marginBottom: 4 }}>Projeto</label>
              <Select
                style={{ width: '100%' }}
                placeholder="Selecione"
                value={projetoFilter}
                onChange={setProjetoFilter}
                allowClear
                showSearch
                optionFilterProp="label"
                options={projetos.map(p => ({ label: p.label, value: p.id }))}
              />
            </Col>

            <Col xs={24} sm={12} md={8}>
              <label style={{ display: 'block', marginBottom: 4 }}>Status</label>
              <Select
                style={{ width: '100%' }}
                value={statusFilter}
                onChange={setStatusFilter}
                options={[
                  { label: 'Pendente', value: 'pendente' },
                  { label: 'Aprovado', value: 'aprovado' },
                  { label: 'Reprovado', value: 'reprovado' },
                  { label: 'Todos', value: '' },
                ]}
              />
            </Col>

            <Col xs={24} sm={12} md={8}>
              <label style={{ display: 'block', marginBottom: 4 }}>Fluxo</label>
              <Select
                style={{ width: '100%' }}
                placeholder="Selecione"
                value={fluxoFilter}
                onChange={setFluxoFilter}
                allowClear
                options={[
                  { label: 'SUPER (Superintendência)', value: 'SUPER' },
                  { label: 'NAO_SUPER (Outros)', value: 'NAO_SUPER' },
                ]}
              />
            </Col>
          </Row>

          <Row style={{ marginTop: 16 }}>
            <Col span={24}>
              <Space>
                <Button
                  icon={<ClearOutlined />}
                  onClick={() => {
                    setStatusFilter('pendente');
                    setSearchTerm('');
                    setDataInicio(null);
                    setDataFim(null);
                    setMunicipioFilter(null);
                    setProjetoFilter(null);
                    setFluxoFilter('');
                  }}
                >
                  Limpar Filtros
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>

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
          <>
            <AntTitle level={5}>Linha do Tempo</AntTitle>
            <Timeline
              style={{ marginBottom: 24 }}
              items={[
                {
                  color: 'blue',
                  dot: <ClockCircleOutlined />,
                  children: (
                    <>
                      <Text strong>Solicitação Criada</Text>
                      <br />
                      <Text type="secondary">
                        {formatDateTime(selectedSolicitacao.created_at)}
                      </Text>
                    </>
                  ),
                },
                selectedSolicitacao.status === 'aprovado' && {
                  color: 'green',
                  dot: <CheckOutlined />,
                  children: (
                    <>
                      <Text strong>Solicitação Aprovada</Text>
                      <br />
                      <Text type="secondary">Aguardando aprovação</Text>
                    </>
                  ),
                },
                selectedSolicitacao.status === 'reprovado' && {
                  color: 'red',
                  dot: <CloseOutlined />,
                  children: (
                    <>
                      <Text strong>Solicitação Reprovada</Text>
                      <br />
                      <Text type="secondary">Aguardando aprovação</Text>
                    </>
                  ),
                },
                selectedSolicitacao.status === 'pendente' && {
                  color: 'gray',
                  children: (
                    <>
                      <Text type="secondary">Aguardando aprovação</Text>
                    </>
                  ),
                },
                selectedSolicitacao.gcal_status === 'PUBLISHED' && {
                  color: 'green',
                  dot: <SyncOutlined />,
                  children: (
                    <>
                      <Text strong>Sincronização Concluída</Text>
                      <br />
                      <Text type="secondary">
                        Evento publicado no Google Calendar
                        {selectedSolicitacao.gcal_last_sync_at &&
                          ` em ${formatDateTime(selectedSolicitacao.gcal_last_sync_at)}`
                        }
                      </Text>
                    </>
                  ),
                },
              ].filter(Boolean)}
            />

            <AntTitle level={5}>Detalhes da Solicitação</AntTitle>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="ID">{selectedSolicitacao.id}</Descriptions.Item>
              <Descriptions.Item label="Solicitante">
                {selectedSolicitacao.usuario?.username || selectedSolicitacao.usuario || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Município">
                {selectedSolicitacao.municipio?.nome || selectedSolicitacao.municipio || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Projeto">
                {selectedSolicitacao.projeto?.nome || selectedSolicitacao.projeto || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Tipo de Evento">
                {selectedSolicitacao.tipo_evento?.nome || selectedSolicitacao.tipo_evento || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Período">
                {formatDateTime(selectedSolicitacao.inicio)} - {formatDateTime(selectedSolicitacao.fim)}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={STATUS_COLORS[selectedSolicitacao.status]}>
                  {selectedSolicitacao.status?.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              {selectedSolicitacao.fluxo && (
                <Descriptions.Item label="Fluxo">
                  <Tag color={selectedSolicitacao.fluxo === 'SUPER' ? 'blue' : 'green'}>
                    {selectedSolicitacao.fluxo === 'SUPER' ? 'SUPER' : 'NÃO SUPER'}
                  </Tag>
                </Descriptions.Item>
              )}
              {selectedSolicitacao.observacoes && (
                <Descriptions.Item label="Observações">
                  {selectedSolicitacao.observacoes}
                </Descriptions.Item>
              )}
              {selectedSolicitacao.meet_link && (
                <Descriptions.Item label="Reunião Online">
                  <Button
                    type="primary"
                    icon={<VideoCameraOutlined />}
                    href={selectedSolicitacao.meet_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    size="small"
                  >
                    Entrar na reunião
                  </Button>
                </Descriptions.Item>
              )}
            </Descriptions>

            {selectedSolicitacao.participations && selectedSolicitacao.participations.length > 0 && (
              <>
                <AntTitle level={5} style={{ marginTop: 16 }}>Participantes</AntTitle>
                <Descriptions column={1} bordered size="small">
                  {selectedSolicitacao.participations.map((p, idx) => (
                    <Descriptions.Item key={idx} label={p.role}>
                      {p.usuario?.first_name && p.usuario?.last_name
                        ? `${p.usuario.first_name} ${p.usuario.last_name}`
                        : p.email || p.guest_email || '-'}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </>
            )}
          </>
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
