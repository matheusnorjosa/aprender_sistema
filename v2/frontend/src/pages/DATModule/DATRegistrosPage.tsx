/**
 * DAT Module - Registros de Turmas
 *
 * Issue #303: Refactored - extracted constants, columns, and helpers to ./DATRegistros/
 *
 * Interface de gestão de registros DAT com filtros avançados,
 * tabela com cabeçalhos agrupados e legenda de status.
 */

import { useState, useEffect, type JSX } from 'react';
import { useTableFilters, type TableFilterParams } from '../../hooks/useTableFilters';
import type { PaginatedResponse } from '../../types';
import {
  Table,
  Button,
  Input,
  Space,
  Typography,
  Card,
  message,
  Select,
  Modal,
  Form,
  InputNumber,
  DatePicker,
  Checkbox,
  Divider,
  Row,
  Col,
  Tag,
} from 'antd';
import {
  ReloadOutlined,
  PlusOutlined,
  DownloadOutlined,
  FilterOutlined,
  ClearOutlined,
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  MinusCircleFilled,
  CloseCircleFilled,
  DatabaseOutlined,
  BookOutlined,
  BarChartOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import {
  listDATRegistros,
  createDATRegistro,
  updateDATRegistro,
  deleteDATRegistro,
  exportDATRegistros,
  getProjetosGeraisOptions,
  getMunicipiosOptions,
  getProjetosOptions,
} from '../../api/datModule';
import dayjs, { type Dayjs } from 'dayjs';
import {
  TURMA_STATUS_OPTIONS,
  ETAPA_STATUS_OPTIONS,
  UF_OPTIONS,
  REGIAO_UFS,
  REGIAO_OPTIONS,
  DEFAULT_FILTERS,
} from './DATRegistros/constants';
import { getColumns, type DATRegistroRecord } from './DATRegistros/columns';

const { Title, Text } = Typography;

// ============================================================
// TYPE DEFINITIONS
// ============================================================

interface DATRegistrosFilters {
  regiao: string | undefined;
  uf: string | undefined;
  municipio: number | undefined;
  projeto_geral: number | undefined;
  usa_avaliar: string | undefined;
  status_formar: string | undefined;
}

interface DATRegistroFormValues {
  municipio: number;
  projeto_geral: number;
  projeto: number;
  aluno_qtde?: number | null;
  professor_qtde?: number | null;
  // FORMAR
  reuniao_dat?: Dayjs | null;
  turma_formar_id?: string | null;
  turma_formar_status?: string | null;
  nr_codigos?: number | null;
  chaves_inscricao_status?: string | null;
  chaves_inscricao_data?: Dayjs | null;
  instrucoes_status?: string | null;
  instrucoes_data?: Dayjs | null;
  envio_codigos_status?: string | null;
  envio_codigos_data?: Dayjs | null;
  obs_formar?: string | null;
  // AVALIAR: multivalorado (JSONField array). O nome do form já é o plural do serializer.
  usa_avaliar?: boolean;
  alunos_recebidos_status?: string | null;
  alunos_recebidos_datas?: Dayjs[] | null;
  alunos_validados_status?: string | null;
  alunos_validados_datas?: Dayjs[] | null;
  alunos_importados_status?: string | null;
  alunos_importados_datas?: Dayjs[] | null;
  obs_avaliar?: string | null;
}

const toISODate = (d?: Dayjs | null): string | null => (d ? d.format('YYYY-MM-DD') : null);
// M16-07: as datas AVALIAR são multivaloradas (JSONField array no serializer). Mapeia TODAS
// as datas do DatePicker `multiple`, sem truncar ao primeiro item (o resíduo do parcial 3954e208).
const toISODateArray = (ds?: Dayjs[] | null): string[] => (ds ?? []).map((d) => d.format('YYYY-MM-DD'));

/**
 * Converte os valores do formulário no payload que os serializers DRF aceitam (M16-07):
 * - datas FORMAR (DateField) viram `YYYY-MM-DD`; sem isso o Dayjs cru vira datetime ISO
 *   (`2026-07-20T03:00:00.000Z`) e o DateField rejeita com 400, perdendo o formulário inteiro;
 * - datas AVALIAR são multivaloradas (JSONField array): o nome do form já é o plural do
 *   serializer, então envia o array INTEIRO. Antes truncava ao primeiro item e perdia o
 *   histórico das demais datas em silêncio.
 */
export function buildDATRegistroPayload(values: DATRegistroFormValues): Record<string, unknown> {
  return {
    ...values,
    reuniao_dat: toISODate(values.reuniao_dat),
    chaves_inscricao_data: toISODate(values.chaves_inscricao_data),
    instrucoes_data: toISODate(values.instrucoes_data),
    envio_codigos_data: toISODate(values.envio_codigos_data),
    alunos_recebidos_datas: toISODateArray(values.alunos_recebidos_datas),
    alunos_validados_datas: toISODateArray(values.alunos_validados_datas),
    alunos_importados_datas: toISODateArray(values.alunos_importados_datas),
  };
}

interface ProjetoGeralOption {
  id: number;
  nome: string;
}

interface MunicipioOption {
  id: number;
  nome: string;
  uf: string;
}

interface ProjetoOption {
  id: number;
  nome: string;
  codigo: string;
}

interface UFOption {
  label: string;
  value: string;
}


const buildRegistrosParams = (f: DATRegistrosFilters): TableFilterParams => ({
  ...(f.regiao && { regiao: f.regiao }),
  ...(f.uf && { uf: f.uf }),
  ...(f.municipio !== undefined && { municipio: f.municipio }),
  ...(f.projeto_geral !== undefined && { projeto_geral: f.projeto_geral }),
  ...(f.usa_avaliar !== undefined && { usa_avaliar: f.usa_avaliar }),
  ...(f.status_formar && { status_formar: f.status_formar }),
});

export default function DATRegistrosPage(): JSX.Element {
  // Options for dropdowns
  const [projetosGerais, setProjetosGerais] = useState<ProjetoGeralOption[]>([]);
  const [municipios, setMunicipios] = useState<MunicipioOption[]>([]);
  const [projetos, setProjetos] = useState<ProjetoOption[]>([]);
  const [filteredUFs, setFilteredUFs] = useState<UFOption[]>(UF_OPTIONS as UFOption[]);

  // Modal states
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editingRegistro, setEditingRegistro] = useState<DATRegistroRecord | null>(null);

  const [form] = Form.useForm<DATRegistroFormValues>();

  const {
    data: registros,
    loading,
    filters,
    setFilters,
    pagination,
    fetchData,
    handleClearFilters: clearFilterState,
    handleTableChange,
    refresh,
  } = useTableFilters<DATRegistrosFilters, DATRegistroRecord>({
    defaultFilters: DEFAULT_FILTERS as unknown as DATRegistrosFilters,
    listFn: listDATRegistros as unknown as (params: TableFilterParams) => Promise<PaginatedResponse<DATRegistroRecord>>,
    buildParams: buildRegistrosParams,
    defaultOrdering: '-created_at',
    entityName: 'registros',
  });

  // Load options on mount
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [pgData, munData, projData] = await Promise.all([
          getProjetosGeraisOptions(),
          getMunicipiosOptions(),
          getProjetosOptions(),
        ]);
        setProjetosGerais((pgData as any).results || pgData || []);
        setMunicipios((munData as any).results || munData || []);
        setProjetos((projData as any).results || projData || []);
      } catch (error) {
        message.error(`Erro ao carregar opções: ${(error as Error).message}`);
      }
    };
    loadOptions();
  }, []);

  // Handle region filter change
  const handleRegiaoChange = (regiao: string | undefined) => {
    setFilters((prev) => ({ ...prev, regiao, uf: undefined }));
    if (regiao && REGIAO_UFS[regiao]) {
      setFilteredUFs((UF_OPTIONS as UFOption[]).filter((uf) => (REGIAO_UFS as any)[regiao as string]?.includes(uf.value)));
    } else {
      setFilteredUFs(UF_OPTIONS as UFOption[]);
    }
  };

  // Clear all filters (also resets cascading UF list)
  const handleClearFilters = () => {
    clearFilterState();
    setFilteredUFs(UF_OPTIONS as UFOption[]);
  };

  // Apply filters
  const handleApplyFilters = () => {
    fetchData(1);
  };

  // Export to CSV
  const handleExport = async () => {
    try {
      const blob = await exportDATRegistros(filters as any);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dat_registros.csv';
      a.click();
      window.URL.revokeObjectURL(url);
      message.success('Exportação realizada com sucesso');
    } catch (error) {
      message.error(`Erro ao exportar: ${(error as Error).message}`);
    }
  };

  // CRUD handlers
  const handleCreate = () => {
    setEditingRegistro(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: DATRegistroRecord) => {
    setEditingRegistro(record);
    // Reconstrução explícita (record é frouxo, `[key: string]: unknown`): hidrata os
    // DatePickers. As datas AVALIAR persistem como array (JSONField) e voltam INTEIRAS
    // ao DatePicker `multiple` — antes só o primeiro item era hidratado (M16-07).
    const r = record as Record<string, unknown>;
    const asDate = (v: unknown): Dayjs | null => (v ? dayjs(v as string) : null);
    const toDateArray = (v: unknown): Dayjs[] => ((v as string[] | undefined) ?? []).map((s) => dayjs(s));
    form.setFieldsValue({
      municipio: record.municipio,
      projeto_geral: record.projeto_geral,
      projeto: record.projeto,
      aluno_qtde: record.aluno_qtde,
      professor_qtde: record.professor_qtde,
      reuniao_dat: asDate(record.reuniao_dat),
      turma_formar_id: record.turma_formar_id,
      turma_formar_status: r.turma_formar_status as string | null | undefined,
      nr_codigos: record.nr_codigos,
      chaves_inscricao_status: record.chaves_inscricao_status,
      chaves_inscricao_data: asDate(r.chaves_inscricao_data),
      instrucoes_status: r.instrucoes_status as string | null | undefined,
      instrucoes_data: asDate(r.instrucoes_data),
      envio_codigos_status: record.envio_codigos_status,
      envio_codigos_data: asDate(r.envio_codigos_data),
      obs_formar: record.obs_formar,
      usa_avaliar: record.usa_avaliar,
      alunos_recebidos_status: record.alunos_recebidos_status,
      alunos_recebidos_datas: toDateArray(r.alunos_recebidos_datas),
      alunos_validados_status: record.alunos_validados_status,
      alunos_validados_datas: toDateArray(r.alunos_validados_datas),
      alunos_importados_status: record.alunos_importados_status,
      alunos_importados_datas: toDateArray(r.alunos_importados_datas),
      obs_avaliar: record.obs_avaliar,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: DATRegistroFormValues) => {
    try {
      const payload = buildDATRegistroPayload(values);

      if (editingRegistro) {
        await updateDATRegistro(editingRegistro.id, payload);
        message.success('Registro atualizado com sucesso');
      } else {
        await createDATRegistro(payload);
        message.success('Registro criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      void refresh();
    } catch (error) {
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = (record: DATRegistroRecord) => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Excluir registro de "${record.municipio_nome}"? Esta ação requer permissão de Superintendência.`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteDATRegistro(record.id);
          message.success('Registro excluído com sucesso');
          void refresh();
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  // Issue #303: Column definitions extracted to ./DATRegistros/columns.jsx
  const columns = getColumns({
    onEdit: handleEdit,
    onDelete: handleDelete,
  });

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="dat-registros-title">
      {/* Header */}
      <header className="mb-6">
        <div className="flex justify-between items-start mb-2">
          <div>
            <Title level={3} className="m-0" id="dat-registros-title">
              Listagem de Registros DAT
            </Title>
            <Text type="secondary">
              Gerenciamento e acompanhamento de dados de turmas por município e projeto.
            </Text>
          </div>
          <Space>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              Exportar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Registro
            </Button>
          </Space>
        </div>
      </header>

      {/* Filters Card */}
      <nav aria-label="Filtros de busca">
      <Card className="mb-4" bodyStyle={{ paddingBottom: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Região
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todas"
              allowClear
              value={filters.regiao || undefined}
              onChange={handleRegiaoChange}
              options={REGIAO_OPTIONS}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={3}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                UF
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.uf}
              onChange={(val) => setFilters((prev) => ({ ...prev, uf: val }))}
              options={filteredUFs}
              showSearch
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={5}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Município
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Buscar município..."
              allowClear
              showSearch
              optionFilterProp="label"
              value={filters.municipio}
              onChange={(val) => setFilters((prev) => ({ ...prev, municipio: val }))}
              options={municipios.map((m) => ({ label: `${m.nome} - ${m.uf}`, value: m.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Projeto Geral
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.projeto_geral}
              onChange={(val) => setFilters((prev) => ({ ...prev, projeto_geral: val }))}
              options={projetosGerais.map((pg) => ({ label: pg.nome, value: pg.id }))}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Usa AVALIAR
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.usa_avaliar}
              onChange={(val) => setFilters((prev) => ({ ...prev, usa_avaliar: val }))}
              options={[
                { label: 'Sim', value: 'true' },
                { label: 'Não', value: 'false' },
              ]}
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <div className="mb-1">
              <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>
                Status Geral
              </Text>
            </div>
            <Select
              style={{ width: '100%' }}
              placeholder="Todos"
              allowClear
              value={filters.status_formar}
              onChange={(val) => setFilters((prev) => ({ ...prev, status_formar: val }))}
              options={[
                { label: 'Completo', value: 'completo' },
                { label: 'Pendente', value: 'pendente' },
              ]}
            />
          </Col>
        </Row>
        <Divider className="my-4 mb-3" />
        <div className="flex justify-end gap-2">
          <Button icon={<ClearOutlined />} onClick={handleClearFilters}>
            Limpar
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => fetchData(1)} loading={loading}>
            Atualizar
          </Button>
          <Button type="primary" icon={<FilterOutlined />} onClick={handleApplyFilters}>
            Filtrar
          </Button>
        </div>
      </Card>
      </nav>

      {/* Table Card */}
      <section aria-label="Resultados da busca">
      <Card
        bodyStyle={{ padding: 0 }}
        title={
          <Space>
            <Text strong>Resultados:</Text>
            <Text type="danger" strong>{pagination.total}</Text>
            <Text>registros</Text>
          </Space>
        }
      >
        {/* Column Group Headers */}
        <div
          className="flex text-xs font-semibold uppercase bg-gray-50"
          style={{ borderBottom: '1px solid #f0f0f0' }}
        >
          <div
            className="flex items-center gap-1.5"
            style={{ flex: '0 0 640px', padding: '8px 16px', borderRight: '1px solid #f0f0f0' }}
          >
            <DatabaseOutlined /> Dados Básicos
          </div>
          <div
            className="flex items-center gap-1.5 text-blue-500"
            style={{ flex: '0 0 580px', padding: '8px 16px', borderRight: '1px solid #f0f0f0' }}
          >
            <BookOutlined /> Detalhes FORMAR
          </div>
          <div
            className="flex items-center gap-1.5 text-green-500"
            style={{ flex: 1, padding: '8px 16px' }}
          >
            <BarChartOutlined /> Detalhes AVALIAR
          </div>
        </div>

        <Table
          columns={columns as any}
          dataSource={registros}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1800 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total, range) => `Mostrando ${range[0]} a ${range[1]} de ${total} registros`,
            onChange: handleTableChange,
          }}
          size="middle"
        />
      </Card>
      </section>

      {/* Legend */}
      <aside aria-label="Legenda de icones">
      <Card className="mt-4" size="small">
        <Space size="large" wrap>
          <Text strong style={{ textTransform: 'uppercase', fontSize: 12 }}>
            Legenda de Ícones:
          </Text>
          <Space>
            <CheckCircleFilled className="text-green-500" />
            <Text type="secondary">Concluído</Text>
          </Space>
          <Space>
            <ClockCircleFilled className="text-yellow-500" />
            <Text type="secondary">Em Andamento</Text>
          </Space>
          <Space>
            <ExclamationCircleFilled className="text-red-500" />
            <Text type="secondary">Pendente</Text>
          </Space>
          <Space>
            <MinusCircleFilled className="text-gray-400" />
            <Text type="secondary">Não Aplicável</Text>
          </Space>
          <Space>
            <CloseCircleFilled className="text-red-600" />
            <Text type="secondary">Erro</Text>
          </Space>
          <Divider type="vertical" />
          <Space>
            <Tag color="green">Chaves Geradas</Tag>
          </Space>
          <Space>
            <Tag color="gold">Chaves Pendentes</Tag>
          </Space>
        </Space>
      </Card>
      </aside>

      {/* Create/Edit Modal */}
      <Modal
        title={
          <div>
            <Title level={4} className="m-0">
              {editingRegistro ? 'Editar Registro DAT' : 'Novo Registro DAT'}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Gerenciamento de dados de acompanhamento de turmas FORMAR e AVALIAR
            </Text>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={
          <div className="flex justify-between">
            <div>
              {editingRegistro && (
                <Button danger type="text" icon={<DeleteOutlined />} onClick={() => { setModalVisible(false); handleDelete(editingRegistro); }}>
                  Excluir Registro
                </Button>
              )}
            </div>
            <Space>
              <Button onClick={() => setModalVisible(false)}>Cancelar</Button>
              <Button type="primary" onClick={() => form.submit()}>
                Salvar
              </Button>
            </Space>
          </div>
        }
        width={1100}
        styles={{ body: { maxHeight: 'calc(100vh - 250px)', overflowY: 'auto' } }}
      >
        <Form form={form} layout="vertical" autoComplete="off" onFinish={handleSave}>
          {/* Dados Básicos */}
          <Card
            size="small"
            title={
              <Space>
                <DatabaseOutlined className="text-blue-500" />
                <span>Dados Básicos</span>
              </Space>
            }
            className="mb-4"
          >
            <Row gutter={16}>
              <Col xs={24} sm={12} md={8}>
                <Form.Item
                  name="municipio"
                  label="Município"
                  rules={[{ required: true, message: 'Selecione o município' }]}
                >
                  <Select
                    placeholder="Selecione o município..."
                    showSearch
                    optionFilterProp="label"
                    options={municipios.map((m) => ({ label: `${m.nome} - ${m.uf}`, value: m.id }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Form.Item
                  name="projeto_geral"
                  label="Projeto Geral"
                  rules={[{ required: true, message: 'Selecione o projeto geral' }]}
                >
                  <Select
                    placeholder="Selecione..."
                    options={projetosGerais.map((pg) => ({ label: pg.nome, value: pg.id }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12} md={8}>
                <Form.Item
                  name="projeto"
                  label="Projeto"
                  rules={[{ required: true, message: 'Selecione o projeto' }]}
                >
                  <Select
                    placeholder="Filtrado pelo geral..."
                    showSearch
                    optionFilterProp="label"
                    options={projetos.map((p) => ({ label: `${p.nome} (${p.codigo})`, value: p.id }))}
                  />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={12} sm={6}>
                <Form.Item
                  name="aluno_qtde"
                  label="Qtde Alunos"
                  rules={[{ required: true, message: 'Obrigatório' }]}
                >
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
              <Col xs={12} sm={6}>
                <Form.Item name="professor_qtde" label="Qtde Professores">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* Two Column Layout: FORMAR and AVALIAR */}
          <Row gutter={16}>
            {/* Plataforma FORMAR */}
            <Col xs={24} lg={12}>
              <Card
                size="small"
                title={
                  <Space>
                    <BookOutlined className="text-blue-500" />
                    <span>Plataforma FORMAR</span>
                    <Tag color="blue">Integração</Tag>
                  </Space>
                }
                className="mb-4 h-full"
              >
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="reuniao_dat" label="Data Reunião DAT">
                      <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="turma_formar_status" label="Status Turma (Criada / Pendente / Erro)">
                      <Select placeholder="Selecione..." options={TURMA_STATUS_OPTIONS} allowClear />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="turma_formar_id" label="ID Turma FORMAR">
                      <Input placeholder="Ex: 48291" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="nr_codigos" label="Nº Códigos">
                      <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                    </Form.Item>
                  </Col>
                </Row>

                <Divider className="my-3" dashed />

                <div className="flex flex-col gap-3">
                  <div className="flex justify-between items-center">
                    <Form.Item name="chaves_inscricao_status" noStyle>
                      <Select
                        placeholder="Status"
                        options={ETAPA_STATUS_OPTIONS}
                        style={{ width: '100%', maxWidth: 140 }}
                        allowClear
                      />
                    </Form.Item>
                    <Text>Chaves de Inscrição</Text>
                    <Form.Item name="chaves_inscricao_data" noStyle>
                      <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: '100%', maxWidth: 130 }} />
                    </Form.Item>
                  </div>

                  <div className="flex justify-between items-center">
                    <Form.Item name="instrucoes_status" noStyle>
                      <Select
                        placeholder="Status"
                        options={ETAPA_STATUS_OPTIONS}
                        style={{ width: '100%', maxWidth: 140 }}
                        allowClear
                      />
                    </Form.Item>
                    <Text>Instruções</Text>
                    <Form.Item name="instrucoes_data" noStyle>
                      <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: '100%', maxWidth: 130 }} />
                    </Form.Item>
                  </div>

                  <div className="flex justify-between items-center">
                    <Form.Item name="envio_codigos_status" noStyle>
                      <Select
                        placeholder="Status"
                        options={ETAPA_STATUS_OPTIONS}
                        style={{ width: '100%', maxWidth: 140 }}
                        allowClear
                      />
                    </Form.Item>
                    <Text>Envio de Códigos</Text>
                    <Form.Item name="envio_codigos_data" noStyle>
                      <DatePicker format="DD/MM/YYYY" placeholder="Data" style={{ width: '100%', maxWidth: 130 }} />
                    </Form.Item>
                  </div>
                </div>

                <Divider className="my-3" dashed />

                <Form.Item name="obs_formar" label="Observações FORMAR" className="mb-0">
                  <Input.TextArea rows={3} placeholder="Observações sobre a integração com FORMAR..." />
                </Form.Item>
              </Card>
            </Col>

            {/* Plataforma AVALIAR */}
            <Col xs={24} lg={12}>
              <Card
                size="small"
                title={
                  <div className="flex justify-between items-center w-full">
                    <Space>
                      <BarChartOutlined className="text-green-500" />
                      <span>Plataforma AVALIAR</span>
                    </Space>
                    <Form.Item name="usa_avaliar" valuePropName="checked" noStyle>
                      <Checkbox>Usa AVALIAR</Checkbox>
                    </Form.Item>
                  </div>
                }
                className="mb-4 h-full"
              >
                <div className="flex flex-col gap-3">
                  {/* Alunos Recebidos */}
                  <Card size="small" className="bg-gray-50">
                    <div className="flex justify-between items-center">
                      <Space>
                        <Form.Item name="alunos_recebidos_status" noStyle>
                          <Select
                            placeholder="Status"
                            options={ETAPA_STATUS_OPTIONS}
                            style={{ width: '100%', maxWidth: 140 }}
                            allowClear
                          />
                        </Form.Item>
                        <Text strong>Alunos Recebidos</Text>
                      </Space>
                      <Form.Item name="alunos_recebidos_datas" noStyle>
                        <DatePicker multiple format="DD/MM/YYYY" placeholder="Datas" style={{ width: '100%', minWidth: 130 }} />
                      </Form.Item>
                    </div>
                  </Card>

                  {/* Alunos Validados */}
                  <Card size="small" className="bg-gray-50">
                    <div className="flex justify-between items-center">
                      <Space>
                        <Form.Item name="alunos_validados_status" noStyle>
                          <Select
                            placeholder="Status"
                            options={ETAPA_STATUS_OPTIONS}
                            style={{ width: '100%', maxWidth: 140 }}
                            allowClear
                          />
                        </Form.Item>
                        <Text strong>Alunos Validados</Text>
                      </Space>
                      <Form.Item name="alunos_validados_datas" noStyle>
                        <DatePicker multiple format="DD/MM/YYYY" placeholder="Datas" style={{ width: '100%', minWidth: 130 }} />
                      </Form.Item>
                    </div>
                  </Card>

                  {/* Alunos Importados */}
                  <Card size="small" className="bg-gray-50">
                    <div className="flex justify-between items-center">
                      <Space>
                        <Form.Item name="alunos_importados_status" noStyle>
                          <Select
                            placeholder="Status"
                            options={ETAPA_STATUS_OPTIONS}
                            style={{ width: '100%', maxWidth: 140 }}
                            allowClear
                          />
                        </Form.Item>
                        <Text strong>Alunos Importados</Text>
                      </Space>
                      <Form.Item name="alunos_importados_datas" noStyle>
                        <DatePicker multiple format="DD/MM/YYYY" placeholder="Datas" style={{ width: '100%', minWidth: 130 }} />
                      </Form.Item>
                    </div>
                  </Card>
                </div>

                <Divider className="my-3" dashed />

                <Form.Item name="obs_avaliar" label="Observações AVALIAR" className="mb-0">
                  <Input.TextArea rows={3} placeholder="Detalhes sobre a importação no AVALIAR..." />
                </Form.Item>
              </Card>
            </Col>
          </Row>
        </Form>
      </Modal>
    </section>
  );
}
