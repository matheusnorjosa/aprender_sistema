/**
 * Admin DAT - Projetos
 *
 * CRUD de projetos com fluxo (SUPER/NAO_SUPER) e status ativo.
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect, useMemo, type JSX } from 'react';
import { Button, Input, Tag, Typography, Card, message, Modal, Form, Radio, Checkbox, Select, Alert, Switch, Grid } from 'antd';
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
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';
import { DEFAULT_PAGE_SIZE } from '../../constants';
import type { ID } from '../../types';
import { aposConfirmacaoFechar, dialogoDeExclusaoEmUso } from './excluirEmUso';

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
  // Família do projeto (ProjetoGeral), só leitura; null sem família.
  projeto_geral_nome?: string | null;
  // Série/variante: fora da Nova Solicitação; no Plano Anual só entra se já tiver plano.
  eh_serie?: boolean;
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
  eh_serie: boolean;
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

  // Celular (< 576 px): as ações da linha vão todas para o menu "Mais ações".
  const acoesCompactas = !Grid.useBreakpoint().sm;

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
      eh_serie: projeto.eh_serie ?? false,
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
    // 409 (em uso): o diálogo "Não é possível excluir" abre quando este terminar de fechar, ou na hora,
    // se a pessoa já o fechou com o DELETE em andamento (excluirEmUso.ts).
    const aposFechar = aposConfirmacaoFechar();
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
          const emUso = dialogoDeExclusaoEmUso({
            erro: error,
            registro: `o projeto "${projeto.nome}"`,
            ativo: projeto.ativo,
            desativar: () => updateProjeto(projeto.id, { ativo: false }),
            desativado: 'Projeto desativado',
            // Esta tela mostra a coluna "Ativo" com Sim/Não, não "Situação".
            aoDesativar: 'a coluna Ativo passa a "Não"',
            recarregar: () => void fetchProjetos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE),
          });
          if (emUso) aposFechar.abrir(emUso);
          else message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
      afterClose: aposFechar.afterClose,
    });
  };

  // Sem rolagem horizontal: colunas por prioridade de largura (VISIVEL_A_PARTIR). Sempre na linha:
  // o nome (com a etiqueta de série), a situação e as ações. O que some da linha vai para a linha
  // expandida (ResponsiveTable). O ID interno não vai para a grade.
  const columns: ColunaResponsiva<ProjetoRecord>[] = [
    {
      title: 'Nome',
      dataIndex: 'nome',
      key: 'nome',
      // Identidade: quebra linha em vez de cortar. A etiqueta fica junto do nome, sem coluna nova.
      render: (_, record) => (
        <div className="min-w-0">
          <Text className="max-w-full break-words">{record.nome}</Text>
          {record.eh_serie ? (
            <div>
              <Tag color="purple" style={{ marginInlineEnd: 0 }}>Série</Tag>
            </div>
          ) : null}
        </div>
      ),
    },
    { title: 'Código', dataIndex: 'codigo', key: 'codigo', width: 136, ellipsis: true, responsive: VISIVEL_A_PARTIR.sm },
    {
      // PR A: "Setor" = rótulo da gerência (nome de tela). O setor do catálogo (`setor_efetivo`,
      // derivado, read-only; o form de conferência grava no raw) fica na mesma célula quando
      // difere — sem coluna nova, para não alargar a tabela (regra: sem rolagem horizontal).
      title: 'Setor',
      key: 'setor',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_, record) => (
        <div className="min-w-0">
          {record.gerencia_nome ? (
            // Rótulo longo quebra linha dentro da etiqueta (a do AntD não quebra e estouraria a coluna).
            <Tag color="geekblue" className="whitespace-normal break-words" style={{ marginInlineEnd: 0, maxWidth: '100%' }}>
              {record.gerencia_nome}
            </Tag>
          ) : (
            <Tag style={{ marginInlineEnd: 0 }}>não definido</Tag>
          )}
          {record.setor_efetivo && record.setor_efetivo !== record.gerencia_nome ? (
            <Text type="secondary" className="block max-w-full break-words">
              catálogo: {record.setor_efetivo}
            </Text>
          ) : null}
        </div>
      ),
    },
    {
      // Família (ProjetoGeral) do projeto: só leitura; a ligação vem do import ou de correção de dados.
      title: 'Família',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto_geral_nome',
      ellipsis: true,
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_, record) => record.projeto_geral_nome || '-',
    },
    {
      title: 'Fluxo',
      dataIndex: 'fluxo',
      key: 'fluxo',
      width: 150,
      responsive: VISIVEL_A_PARTIR.xl,
      render: (_, record) => {
        const cor = record.fluxo === 'SUPER' ? 'gold' : 'blue';
        return (
          <Tag color={cor} style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG[cor] }}>
            {record.fluxo === 'SUPER' ? 'SUPER (Manual)' : 'NAO_SUPER (Auto)'}
          </Tag>
        );
      },
    },
    {
      title: 'Situação',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 88,
      render: (_, record) => {
        const cor = record.ativo ? 'green' : 'red';
        return (
          <Tag color={cor} style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG[cor] }}>
            {record.ativo ? 'Ativo' : 'Inativo'}
          </Tag>
        );
      },
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: larguraAcoesLinha(2, acoesCompactas),
      render: (_, record) => (
        <AcoesLinha
          compacto={acoesCompactas}
          alvo={record.nome}
          acoes={[
            { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: () => handleEdit(record) },
            {
              chave: 'excluir',
              rotulo: 'Excluir',
              icone: <DeleteOutlined />,
              onClick: () => handleDelete(record),
              perigo: true,
            },
          ]}
        />
      ),
    },
  ];

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="projetos-title">
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Title level={3} className="m-0" id="projetos-title">
            Projetos ({pagination.total || 0})
          </Title>
          <div className="flex flex-wrap items-center gap-2">
            <Search
              placeholder="Buscar por nome ou código"
              aria-label="Buscar projetos por nome ou código"
              allowClear
              style={{ width: 250, maxWidth: '100%' }}
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
          </div>
        </header>

        <ResponsiveTable<ProjetoRecord>
          columns={columns}
          dataSource={projetos}
          rowKey="id"
          nomeDaLinha={(projeto) => projeto.nome}
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            pageSizeOptions: ['15', '30', '50', '100'],
            showTotal: (total) => `Total: ${total}`,
          }}
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

          <Form.Item
            name="eh_serie"
            label="É série"
            valuePropName="checked"
            initialValue={false}
            extra="Série ou variante de um projeto (ex.: A COR DA GENTE 3). Marcada, não aparece na Nova Solicitação; no Plano Anual só aparece se já tiver plano. Continua em Compras e no DAT."
          >
            <Switch checkedChildren="Sim" unCheckedChildren="Não" />
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Projeto ativo</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
