/**
 * Admin DAT - Projetos
 *
 * CRUD de projetos com fluxo (SUPER/NAO_SUPER) e status ativo.
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect, useMemo, type JSX } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Modal, Form, Radio, Checkbox, Select, Alert } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router';
import {
  listProjetos,
  createProjeto,
  updateProjeto,
  deleteProjeto,
  getRBACMeta,
  listGerencias,
  type GerenciaRecord,
} from '../../api/adminDAT';
import { DEFAULT_PAGE_SIZE } from '../../constants';
import type { ID } from '../../types';

const { Title, Text } = Typography;
const { Search } = Input;

/**
 * Projeto record interface
 */
interface ProjetoRecord {
  id: ID;
  nome: string;
  codigo: string;
  fluxo: 'SUPER' | 'NAO_SUPER';
  ativo: boolean;
  // Conferência #1914: setor = raw gravável; setor_efetivo = derivado (setor || gerencia.nome_setor), read-only.
  setor: string;
  setor_efetivo: string;
  // Gerência do projeto (id); null sem gerência. Pré-preenche o campo Gerência na edição.
  gerencia: ID | null;
  // PR A: rótulo (nome de tela) da gerência do projeto; null sem gerência.
  gerencia_nome: string | null;
}

/**
 * Projeto form values interface
 */
interface ProjetoFormValues {
  nome: string;
  codigo: string;
  fluxo: 'SUPER' | 'NAO_SUPER';
  ativo: boolean;
  setor?: string;
  gerencia?: ID | undefined;
}

export default function ProjetosPage(): JSX.Element {
  const [projetos, setProjetos] = useState<ProjetoRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProjeto, setEditingProjeto] = useState<ProjetoRecord | null>(null);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });

  // Vocabulário setor-de-produto (SSOT no backend), buscado do endpoint de options (/rbac/meta/) —
  // Select FECHADO da conferência, sem hardcode (evita drift do vocabulário). Mesmo padrão da GerenciasPage.
  const [setoresProduto, setSetoresProduto] = useState<string[]>([]);
  const [gerencias, setGerencias] = useState<GerenciaRecord[]>([]);
  // Motivo da falha ao carregar as gerências (null = carregou). Sem a lista não dá para criar projeto.
  const [erroGerencias, setErroGerencias] = useState<string | null>(null);

  const [form] = Form.useForm<ProjetoFormValues>();

  const fetchProjetos = async (
    current = pagination.current || 1,
    pageSize = pagination.pageSize || DEFAULT_PAGE_SIZE,
  ): Promise<void> => {
    setLoading(true);
    try {
      const data = await listProjetos({
        search: searchText,
        ordering: 'nome',
        page: current,
        page_size: pageSize,
      });
      // Note: API returns Projeto with is_active, but component uses ativo field name
      // This is acceptable during migration - will be unified in strict mode phase
      setProjetos(data.results as unknown as ProjetoRecord[]);
      setPagination((prev) => ({
        ...prev,
        current,
        pageSize,
        total: data.count,
      }));
    } catch (error) {
      message.error(`Erro ao carregar projetos: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchProjetos(1, pagination.pageSize || DEFAULT_PAGE_SIZE);
  }, [searchText]);

  // Carrega o vocabulário de setor-de-produto uma vez (Select fechado da conferência).
  useEffect(() => {
    void (async () => {
      try {
        const meta = await getRBACMeta();
        setSetoresProduto(meta.setores_produto);
      } catch {
        // meta indisponível: o Select fica sem options até um reload; não bloqueia a listagem.
      }
    })();
  }, []);

  // Regra do dono (30/09): fluxo SUPER só em projeto da gerência Superintendência — a tela precisa
  // escolher a gerência. Só as ATIVAS, pelo rótulo de tela (PR A).
  useEffect(() => {
    void (async () => {
      try {
        const data = await listGerencias({ ativo: true, page_size: 1000 });
        setGerencias(data.results);
      } catch (error) {
        // Sem a lista, o campo obrigatório trava o criar sem chamar a API: o modal mostra o motivo.
        setErroGerencias((error as Error).message);
      }
    })();
  }, []);

  // Mais a gerência atual do projeto em edição quando ela foi desativada (sem ela o Select
  // mostraria o id cru) — mesmo padrão da UsuariosPage.
  const gerenciaOptions = useMemo(() => {
    const options = gerencias
      .slice()
      .sort((a, b) => a.rotulo.localeCompare(b.rotulo, 'pt-BR'))
      .map((g) => ({ label: g.rotulo, value: g.id }));
    const atual = editingProjeto?.gerencia;
    if (atual != null && !options.some((o) => o.value === atual)) {
      options.push({ label: editingProjeto?.gerencia_nome ?? String(atual), value: atual });
    }
    return options;
  }, [gerencias, editingProjeto]);

  const handleTableChange = (newPagination: TablePaginationConfig): void => {
    void fetchProjetos(
      newPagination.current || 1,
      newPagination.pageSize || pagination.pageSize || DEFAULT_PAGE_SIZE,
    );
  };

  const handleCreate = (): void => {
    setEditingProjeto(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (projeto: ProjetoRecord): void => {
    setEditingProjeto(projeto);
    // Limpa o erro do último salvar: o setFieldsValue só limpa o de campo cujo valor muda.
    form.resetFields();
    form.setFieldsValue({
      nome: projeto.nome,
      codigo: projeto.codigo,
      fluxo: projeto.fluxo,
      ativo: projeto.ativo,
      // Semeia o RAW `setor` (não o derivado `setor_efetivo`): editar o derivado e salvar
      // gravaria a derivação no raw, contaminando-o (guarda anti-M17).
      setor: projeto.setor,
      gerencia: projeto.gerencia ?? undefined,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: ProjetoFormValues): Promise<void> => {
    try {
      if (editingProjeto) {
        await updateProjeto(editingProjeto.id, values);
        message.success('Projeto atualizado com sucesso');
      } else {
        await createProjeto(values);
        message.success('Projeto criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      void fetchProjetos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
    } catch (error) {
      // A trava "SUPER só na Superintendência" volta como erro sem campo (400): mostra junto do
      // campo Gerência, onde se corrige.
      const semCampo = (error as { response?: { data?: { errors?: { non_field_errors?: string[] } } } }).response
        ?.data?.errors?.non_field_errors;
      if (semCampo?.length) {
        form.setFields([{ name: 'gerencia', errors: semCampo }]);
        return;
      }
      message.error(`Erro: ${(error as Error).message}`);
    }
  };

  const handleDelete = (projeto: ProjetoRecord): void => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Tem certeza que deseja excluir o projeto "${projeto.nome}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await deleteProjeto(projeto.id);
          message.success('Projeto excluído com sucesso');
          void fetchProjetos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const columns: ColumnsType<ProjetoRecord> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 300 },
    { title: 'Código', dataIndex: 'codigo', key: 'codigo', width: 120 },
    {
      // PR A: "Setor" = rótulo da gerência (nome de tela). O setor do catálogo (`setor_efetivo`,
      // derivado, read-only; o form de conferência grava no raw) fica na mesma célula quando
      // difere — sem coluna nova, para não alargar a tabela (regra: sem rolagem horizontal).
      title: 'Setor',
      key: 'setor',
      width: 160,
      render: (_, record) => (
        <>
          {record.gerencia_nome ? <Tag color="geekblue">{record.gerencia_nome}</Tag> : <Tag>não definido</Tag>}
          {record.setor_efetivo && record.setor_efetivo !== record.gerencia_nome ? (
            <div><Text type="secondary">catálogo: {record.setor_efetivo}</Text></div>
          ) : null}
        </>
      ),
    },
    {
      title: 'Fluxo',
      dataIndex: 'fluxo',
      key: 'fluxo',
      width: 150,
      render: (fluxo: string) => (
        <Tag color={fluxo === 'SUPER' ? 'gold' : 'blue'}>
          {fluxo === 'SUPER' ? 'SUPER (Manual)' : 'NAO_SUPER (Auto)'}
        </Tag>
      ),
    },
    {
      title: 'Ativo',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 100,
      render: (ativo: boolean) => <Tag color={ativo ? 'green' : 'red'}>{ativo ? 'Sim' : 'Não'}</Tag>,
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Editar
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            Excluir
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="projetos-title">
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="flex justify-between items-center mb-4">
          <Title level={3} className="m-0" id="projetos-title">
            Projetos ({pagination.total || 0})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome ou código"
              allowClear
              style={{ width: '100%', maxWidth: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchProjetos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
              loading={loading}
            >
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Projeto
            </Button>
          </Space>
        </header>

        <Table
          columns={columns}
          dataSource={projetos}
          rowKey="id"
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            pageSizeOptions: ['15', '30', '50', '100'],
            showTotal: (total) => `Total: ${total}`,
          }}
          scroll={{ x: 900 }}
        />
      </Card>

      {/* Modal Criar/Editar Projeto */}
      <Modal
        title={editingProjeto ? 'Editar Projeto' : 'Novo Projeto'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          onFinish={handleSave}
        >
          {erroGerencias ? (
            <Alert
              type="error"
              showIcon
              className="mb-4"
              message="Não foi possível carregar as gerências"
              description={`${erroGerencias} Sem essa lista não dá para criar projeto nem trocar a gerência; recarregue a página.`}
            />
          ) : null}
          <Form.Item
            name="nome"
            label="Nome do Projeto"
            rules={[{ required: true, message: 'Nome é obrigatório' }]}
          >
            <Input placeholder="Ex: PROJETO AMMA" />
          </Form.Item>

          <Form.Item
            name="codigo"
            label="Código"
            rules={[{ required: true, message: 'Código é obrigatório' }]}
          >
            <Input placeholder="Ex: AMMA" />
          </Form.Item>

          <Form.Item
            name="gerencia"
            label="Gerência"
            rules={editingProjeto ? [] : [{ required: true, message: 'Gerência é obrigatória' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Selecione a gerência..."
              options={gerenciaOptions}
            />
          </Form.Item>

          <Form.Item
            name="setor"
            label="Setor canônico (vocabulário de setor-de-produto)"
          >
            <Select
              allowClear
              showSearch
              placeholder="Selecione o setor..."
              options={setoresProduto.map((s) => ({ label: s, value: s }))}
            />
          </Form.Item>

          <Form.Item
            name="fluxo"
            label="Fluxo de Aprovação"
            rules={[{ required: true, message: 'Fluxo é obrigatório' }]}
            initialValue="NAO_SUPER"
          >
            <Radio.Group>
              <Radio value="SUPER">Aprovação Manual</Radio>
              <Radio value="NAO_SUPER">Auto-aprovado</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Projeto ativo</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
