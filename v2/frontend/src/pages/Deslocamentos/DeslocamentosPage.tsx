/**
 * Deslocamentos Page - Issue #188
 *
 * CRUD interface for managing travel records between municipalities.
 *
 * Features:
 * - List with filters (Usuario, Date Range, Origem/Destino)
 * - Create/Edit via modal
 * - Delete with confirmation
 * - Pagination (50 per page)
 * - RBAC: Only Controle/Coordenador can access
 *
 * API:
 * - GET /api/deslocamentos/ (list with filters)
 * - POST /api/deslocamentos/ (create)
 * - PUT /api/deslocamentos/{id}/ (update)
 * - DELETE /api/deslocamentos/{id}/ (delete)
 *
 * Sem rolagem horizontal (G30, padrão responsivo): ResponsiveTable. Sempre na linha o formador e
 * as ações (AcoesLinha; no celular, o menu "Mais ações"); Data Início sobe a partir de sm, Destino
 * e Data Fim de md, Origem de lg e a Observação (texto longo) só de xxl. O que some vai para a
 * linha expandida.
 */

import { useState, useEffect, useCallback, useRef, ChangeEvent, JSX } from 'react';
import {
  Button,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  message,
  Space,
  Row,
  Col,
  Card,
  Typography,
  Grid,
} from 'antd';
import type { TablePaginationConfig } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  CarOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  listDeslocamentos,
  listFormadoresDoSetor,
  listAlvosDeslocamento,
  createDeslocamento,
  updateDeslocamento,
  deleteDeslocamento,
  type DeslocamentoRecord,
  type DeslocamentoFilters as FiltersType,
  type FormadorOption as UsuarioOptionType,
} from '../../api/deslocamentos';
import { useAcesso } from '../../contexts/AcessoContext';
import { mensagemDoErro } from '../AdminDAT/usuario_form_helpers';
import DatImportsCentralizedBanner from '../../components/DatImportsCentralizedBanner';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';
import logger from '../../utils/logger';
import type { ID } from '../../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

/** Form values type */
/** Quem a linha representa: nomeia o expandir e as ações ("Editar: deslocamento de Maria em 10/11/2026"). */
function nomeDoDeslocamento(registro: DeslocamentoRecord): string {
  return `deslocamento de ${registro.usuario_nome} em ${dayjs(registro.start_date).format('DD/MM/YYYY')}`;
}

interface FormValuesType {
  usuario?: ID;
  origem: string;
  destino: string;
  start_date: Dayjs;
  end_date: Dayjs;
  observacao?: string;
}

export default function DeslocamentosPage(): JSX.Element {
  // PR 7 das permissões: a mesma policy da rota e do menu (access_travel). A rota já protege
  // (<RequirePolicy>); este check é defesa em camadas.
  // #1622: dois loadings separados. `pageLoading` gateia a página inteira (só o acesso
  // da pessoa); `tableLoading` gateia SÓ a tabela. Antes um `loading` único fazia o fetch
  // de filtro desmontar a página (input perdia foco/valor).
  const { caps, loading: pageLoading } = useAcesso();
  const canAccess = caps.canAccessTravel;
  const [tableLoading, setTableLoading] = useState<boolean>(false);
  const [deslocamentos, setDeslocamentos] = useState<DeslocamentoRecord[]>([]);
  const [usuarios, setUsuarios] = useState<UsuarioOptionType[]>([]);
  // P16 (PR 8): quem a pessoa pode pôr no campo "Formador". Vazio = o campo some e ela registra o próprio.
  const [alvos, setAlvos] = useState<UsuarioOptionType[]>([]);
  const [pagination, setPagination] = useState<TablePaginationConfig>({ current: 1, pageSize: 50, total: 0 });
  const [filters, setFilters] = useState<FiltersType>({});
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [currentRecord, setCurrentRecord] = useState<DeslocamentoRecord | null>(null);
  const [form] = Form.useForm<FormValuesType>();
  const acoesCompactas = !Grid.useBreakpoint().sm;

  // M09-06 (#1622): guarda de sequência (latest-wins). O debounce reduz mas não
  // elimina a corrida — se um request antigo (filtro obsoleto) resolver DEPOIS do
  // atual, ele sobrescreveria a tabela com o resultado errado. Espelha o idioma
  // canônico de useAvailabilityPreview.ts (seqRef + AbortController).
  const seqRef = useRef(0);

  // Load deslocamentos
  const loadDeslocamentos = useCallback(async (page = 1, signal?: AbortSignal): Promise<void> => {
    const seq = ++seqRef.current;
    setTableLoading(true);
    try {
      const data = await listDeslocamentos({ ...filters, page }, { signal });
      if (seq !== seqRef.current) return; // resposta obsoleta: um filtro/página mais novo venceu
      setDeslocamentos(data.results || []);
      setPagination({
        current: page,
        pageSize: 50,
        total: data.count || 0,
      });
    } catch (error) {
      if (signal?.aborted) return; // cancelamento no cleanup não é falha
      if (seq !== seqRef.current) return; // erro de request obsoleto: não polui a UI atual
      message.error((error as Error).message);
    } finally {
      if (seq === seqRef.current) setTableLoading(false);
    }
  }, [filters]);

  // Load formadores do setor do usuário logado (filtro) e quem ele pode registrar (formulário)
  const loadFormadores = useCallback(async (): Promise<void> => {
    const [doSetor, delegaveis] = await Promise.allSettled([listFormadoresDoSetor(), listAlvosDeslocamento()]);
    if (doSetor.status === 'fulfilled') setUsuarios(doSetor.value);
    else logger.error('Erro ao carregar formadores:', doSetor.reason);
    if (delegaveis.status === 'fulfilled') setAlvos(delegaveis.value);
    else logger.error('Erro ao carregar formadores do deslocamento:', delegaveis.reason);
  }, []);

  // Opções de formador carregam UMA vez (não dependem dos filtros).
  useEffect(() => {
    if (canAccess) {
      void loadFormadores();
    }
  }, [canAccess, loadFormadores]);

  // Lista recarrega ao mudar filtros, com debounce (evita 1 request por tecla).
  // O AbortController cancela o request em voo quando o filtro muda de novo (o
  // seqRef já descarta a resposta obsoleta; o abort evita o trabalho de rede).
  useEffect(() => {
    if (!canAccess) {
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      void loadDeslocamentos(1, controller.signal);
    }, 350);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [canAccess, filters, loadDeslocamentos]);

  // Handle table change (pagination)
  const handleTableChange = (paginationConfig: TablePaginationConfig): void => {
    void loadDeslocamentos(paginationConfig.current);
  };

  // Handle filter change
  const handleFilterChange = (key: keyof FiltersType, value: string | ID | undefined): void => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  // Handle date range change
  const handleDateRangeChange = (dates: [Dayjs | null, Dayjs | null] | null): void => {
    if (dates && dates.length === 2 && dates[0] && dates[1]) {
      setFilters((prev) => ({
        ...prev,
        data_inicio: dates[0]!.format('YYYY-MM-DD'),
        data_fim: dates[1]!.format('YYYY-MM-DD'),
      }));
    } else {
      setFilters((prev) => {
        const { data_inicio: _data_inicio, data_fim: _data_fim, ...rest } = prev;
        return rest;
      });
    }
  };

  // Open modal for create
  const handleCreate = (): void => {
    setModalMode('create');
    setCurrentRecord(null);
    form.resetFields();
    setModalVisible(true);
  };

  // Open modal for edit
  const handleEdit = (record: DeslocamentoRecord): void => {
    setModalMode('edit');
    setCurrentRecord(record);
    form.setFieldsValue({
      usuario: record.usuario,
      origem: record.origem,
      destino: record.destino,
      start_date: dayjs(record.start_date),
      end_date: dayjs(record.end_date),
      observacao: record.observacao || '',
    });
    setModalVisible(true);
  };

  // Handle modal submit
  const handleModalSubmit = async (): Promise<void> => {
    try {
      const values = await form.validateFields();

      // Format data. Sem `usuario` (campo vazio ou oculto), o backend grava para quem está logado.
      const data = {
        ...(values.usuario !== undefined ? { usuario: values.usuario } : {}),
        origem: values.origem,
        destino: values.destino,
        start_date: values.start_date.format('YYYY-MM-DD'),
        end_date: values.end_date.format('YYYY-MM-DD'),
        observacao: values.observacao || '',
      };

      if (modalMode === 'create') {
        await createDeslocamento(data);
        message.success('Deslocamento criado com sucesso!');
      } else {
        await updateDeslocamento(currentRecord!.id, data);
        message.success('Deslocamento atualizado com sucesso!');
      }

      setModalVisible(false);
      form.resetFields();
      void loadDeslocamentos(pagination.current);
    } catch (error) {
      // Campo vazio no formulário: o antd já marca o campo; não há resposta do servidor.
      if ((error as { errorFields?: unknown }).errorFields) return;
      // G07 (P#13): o motivo do servidor (validação em `errors`, 403 no `detail`).
      message.error(mensagemDoErro(error) || 'Não foi possível salvar o deslocamento.');
    }
  };

  // Ação destrutiva: começa no Cancelar e cita o deslocamento (quem, de onde, para onde).
  const confirmarExclusao = (record: DeslocamentoRecord): void => {
    Modal.confirm({
      title: 'Excluir este deslocamento?',
      content: `${record.usuario_nome}, de ${record.origem} a ${record.destino}, ${dayjs(record.start_date).format('DD/MM/YYYY')}.`,
      okText: 'Excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: () => handleDelete(record.id),
    });
  };

  // Handle delete
  const handleDelete = async (id: ID): Promise<void> => {
    try {
      await deleteDeslocamento(id);
      message.success('Deslocamento excluído.');
      void loadDeslocamentos(pagination.current);
    } catch (error) {
      message.error(mensagemDoErro(error) || 'Não foi possível excluir o deslocamento.');
    }
  };

  // Columns for table (G30: por prioridade de largura; o que some vai para a linha expandida)
  const columns: ColunaResponsiva<DeslocamentoRecord>[] = [
    {
      title: 'Formador',
      dataIndex: 'usuario_nome',
      key: 'usuario_nome',
    },
    {
      title: 'Origem',
      dataIndex: 'origem',
      key: 'origem',
      responsive: VISIVEL_A_PARTIR.lg,
      ellipsis: true,
    },
    {
      title: 'Destino',
      dataIndex: 'destino',
      key: 'destino',
      responsive: VISIVEL_A_PARTIR.md,
      ellipsis: true,
    },
    {
      title: 'Data Início',
      dataIndex: 'start_date',
      key: 'start_date',
      responsive: VISIVEL_A_PARTIR.sm,
      width: 112,
      render: (_, record) => dayjs(record.start_date).format('DD/MM/YYYY'),
    },
    {
      title: 'Data Fim',
      dataIndex: 'end_date',
      key: 'end_date',
      responsive: VISIVEL_A_PARTIR.md,
      width: 112,
      render: (_, record) => dayjs(record.end_date).format('DD/MM/YYYY'),
    },
    {
      title: 'Observação',
      dataIndex: 'observacao',
      key: 'observacao',
      responsive: VISIVEL_A_PARTIR.xxl,
      ellipsis: true,
      render: (_, record) => record.observacao || '-',
    },
    {
      title: 'Ações',
      key: 'actions',
      width: larguraAcoesLinha(2, acoesCompactas),
      // G07 (P#12): só onde o servidor deixa (dono ou quem delega); nas outras linhas o clique dava 403.
      render: (_, record) => record.pode_editar && (
        <AcoesLinha
          compacto={acoesCompactas}
          alvo={nomeDoDeslocamento(record)}
          acoes={[
            { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: () => handleEdit(record) },
            {
              chave: 'excluir',
              rotulo: 'Excluir',
              icone: <DeleteOutlined />,
              onClick: () => confirmarExclusao(record),
              perigo: true,
            },
          ]}
        />
      ),
    },
  ];

  // Opções do campo "Formador": os alvos; na edição, também o dono do registro (para mostrar o nome).
  const opcoesFormador: UsuarioOptionType[] =
    currentRecord && !alvos.some((u) => u.id === currentRecord.usuario)
      ? [...alvos, { id: currentRecord.usuario, first_name: currentRecord.usuario_nome, last_name: '' }]
      : alvos;

  // Permission check
  if (pageLoading) {
    return <div className="p-6">Carregando...</div>;
  }

  if (!canAccess) {
    return (
      <div className="p-6">
        <Card>
          <Title level={3}>Sem permissão</Title>
          <Text>Você não tem permissão para acessar esta página.</Text>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <Title level={2}>
            <CarOutlined /> Deslocamentos
          </Title>
          <Text type="secondary">
            Gestão de deslocamentos entre municípios
          </Text>
        </div>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            Novo Deslocamento
          </Button>
        </Space>
      </div>

      <DatImportsCentralizedBanner />

      {/* Filters */}
      <Card title="Filtros" size="small">
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Select
              placeholder="Selecione um formador"
              allowClear
              showSearch
              optionFilterProp="children"
              style={{ width: '100%' }}
              onChange={(value: ID | undefined) => handleFilterChange('usuario_id', value)}
            >
              {usuarios.map((u) => (
                <Select.Option key={u.id} value={u.id}>
                  {u.first_name} {u.last_name}
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <RangePicker
              placeholder={['Data Início', 'Data Fim']}
              format="DD/MM/YYYY"
              style={{ width: '100%' }}
              onChange={handleDateRangeChange}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Input
              placeholder="Origem"
              prefix={<SearchOutlined />}
              value={filters.origem ?? ''}
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('origem', e.target.value)}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Input
              placeholder="Destino"
              prefix={<SearchOutlined />}
              value={filters.destino ?? ''}
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleFilterChange('destino', e.target.value)}
            />
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card>
        <ResponsiveTable<DeslocamentoRecord>
          columns={columns}
          dataSource={deslocamentos}
          rowKey="id"
          loading={tableLoading}
          pagination={pagination}
          onChange={handleTableChange}
          nomeDaLinha={nomeDoDeslocamento}
        />
      </Card>

      {/* Modal */}
      <Modal
        title={modalMode === 'create' ? 'Novo Deslocamento' : 'Editar Deslocamento'}
        open={modalVisible}
        onOk={handleModalSubmit}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        okText="Salvar"
        cancelText="Cancelar"
        width={600}
      >
        <Form form={form} layout="vertical" autoComplete="off" className="mt-4">
          {alvos.length > 0 && (
            <Form.Item
              name="usuario"
              label="Formador"
              extra="Deixe em branco para registrar o seu próprio deslocamento."
            >
              <Select
                placeholder="Você"
                allowClear
                showSearch
                optionFilterProp="children"
              >
                {opcoesFormador.map((u) => (
                  <Select.Option key={u.id} value={u.id}>
                    {u.first_name} {u.last_name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="origem"
                label="Origem"
                rules={[
                  { required: true, message: 'Informe a origem' },
                  { max: 200, message: 'Máximo 200 caracteres' },
                ]}
              >
                <Input placeholder="Ex: Fortaleza" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="destino"
                label="Destino"
                rules={[
                  { required: true, message: 'Informe o destino' },
                  { max: 200, message: 'Máximo 200 caracteres' },
                ]}
              >
                <Input placeholder="Ex: Sobral" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="start_date"
                label="Data Início"
                rules={[{ required: true, message: 'Selecione a data de início' }]}
              >
                <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="end_date"
                label="Data Fim"
                rules={[{ required: true, message: 'Selecione a data de fim' }]}
              >
                <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="observacao"
            label="Observação"
            rules={[{ max: 500, message: 'Máximo 500 caracteres' }]}
          >
            <TextArea rows={3} placeholder="Observações sobre o deslocamento" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
