/**
 * Admin DAT - Gerencias
 *
 * CRUD de gerencias organizacionais com setor e status ativo.
 *
 * Padrão responsivo (Programa C, C2): lista enxuta no ResponsiveTable. Sempre na linha o
 * setor (rótulo de tela), Situação e as ações; as demais colunas sobem por largura e o que some
 * vai para a linha expandida. Nunca na grade: ID, código interno e descrição (no formulário).
 */

import { useState, useEffect, useRef, type JSX } from 'react';
import { flushSync } from 'react-dom';
import { Button, Input, Tag, Typography, Card, message, Modal, Form, Checkbox, Select, Grid } from 'antd';
import type { RefSelectProps } from 'antd';
import type { TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router';
import { listGerencias, createGerencia, updateGerencia, deleteGerencia, getRBACMeta } from '../../api/adminDAT';
import type { GerenciaRecord, GerenciaPayload } from '../../api/adminDAT';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';
import { FalhaAoCarregar } from '../../components/FalhaAoCarregar';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';
import { DEFAULT_PAGE_SIZE } from '../../constants';
import { errosDosCampos, mensagemDoErro } from './usuario_form_helpers';

const { Title, Text } = Typography;
const { Search } = Input;

/** Confiança do de-para (vocabulário do importer) com o rótulo de tela e a cor da etiqueta. */
const CONFIANCA: Record<string, { rotulo: string; cor: string }> = {
  na: { rotulo: 'Conferir', cor: 'red' }, // não-aplicável: prioridade máxima da conferência
  media: { rotulo: 'Média', cor: 'orange' },
  alta: { rotulo: 'Alta', cor: 'green' },
};

/** Tag que corta com reticências em vez de estourar a coluna. */
function Etiqueta({ cor, texto }: { cor: string; texto: string }): JSX.Element {
  return (
    <Tag
      color={cor}
      title={texto}
      className="truncate"
      style={{ marginInlineEnd: 0, maxWidth: '100%', color: TEXTO_DA_TAG[cor] }}
    >
      {texto}
    </Tag>
  );
}

/**
 * Gerencia form values interface
 */
interface GerenciaFormValues {
  nome: string;
  nome_setor: string;
  nome_exibicao?: string;
  setor_canonico?: string;
  descricao: string;
  ativo: boolean;
}

export default function GerenciasPage(): JSX.Element {
  const [gerencias, setGerencias] = useState<GerenciaRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGerencia, setEditingGerencia] = useState<GerenciaRecord | null>(null);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });
  // Vocabulário setor-de-produto (SSOT = SETORES_PRODUTO no backend), buscado do endpoint de
  // options (/rbac/meta/) — Select FECHADO da conferência, sem hardcode (evita drift do vocabulário).
  const [setoresProduto, setSetoresProduto] = useState<string[]>([]);
  const [erroSetores, setErroSetores] = useState<string | null>(null);
  const setorRef = useRef<RefSelectProps>(null);
  const [erroLista, setErroLista] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  // Filtro de confiança no topo (vale em qualquer largura; no cabeçalho da coluna, sumia com ela).
  const [confiancaFiltro, setConfiancaFiltro] = useState<string | undefined>(undefined);
  // Celular (< 576 px): as ações da linha vão todas para o menu "Mais ações".
  const acoesCompactas = !Grid.useBreakpoint().sm;

  const [form] = Form.useForm<GerenciaFormValues>();

  const fetchGerencias = async (
    current = pagination.current || 1,
    pageSize = pagination.pageSize || DEFAULT_PAGE_SIZE,
  ): Promise<void> => {
    setLoading(true);
    try {
      const data = await listGerencias({
        search: searchText,
        // PR A: ordena pelo nome de tela (nome_exibicao || nome_setor), anotado no backend.
        ordering: 'rotulo_ordem',
        page: current,
        page_size: pageSize,
      });
      setGerencias(data.results);
      setErroLista(null);
      setPagination((prev) => ({
        ...prev,
        current,
        pageSize,
        total: data.count,
      }));
    } catch (error) {
      setErroLista(mensagemDoErro(error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchGerencias(1, pagination.pageSize || DEFAULT_PAGE_SIZE);
  }, [searchText]);

  // Vocabulário de setor-de-produto (Select fechado da conferência). Se não carregar, o campo
  // avisa e oferece "Tentar de novo"; a listagem não depende dele. O erro fica até a resposta
  // (o botão não some com o foco nele). Devolve se carregou.
  const fetchSetores = async (): Promise<boolean> => {
    try {
      const meta = await getRBACMeta();
      // Síncrono: quando o "Tentar de novo" põe o foco no Select, ele já está habilitado.
      flushSync(() => {
        setSetoresProduto(meta.setores_produto);
        setErroSetores(null);
      });
      return true;
    } catch (error) {
      setErroSetores(mensagemDoErro(error));
      return false;
    }
  };

  useEffect(() => {
    void fetchSetores();
  }, []);

  const handleTableChange = (newPagination: TablePaginationConfig): void => {
    void fetchGerencias(
      newPagination.current || 1,
      newPagination.pageSize || pagination.pageSize || DEFAULT_PAGE_SIZE,
    );
  };

  const handleCreate = (): void => {
    setEditingGerencia(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (gerencia: GerenciaRecord): void => {
    setEditingGerencia(gerencia);
    form.setFieldsValue({
      nome: gerencia.nome,
      nome_setor: gerencia.nome_setor,
      nome_exibicao: gerencia.nome_exibicao,
      setor_canonico: gerencia.setor_canonico,
      descricao: gerencia.descricao,
      ativo: gerencia.ativo,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: GerenciaFormValues): Promise<void> => {
    setSalvando(true);
    try {
      const payload: GerenciaPayload = {
        nome_setor: values.nome_setor,
        nome_exibicao: values.nome_exibicao ?? '',
        descricao: values.descricao,
        ativo: values.ativo,
        // setor_canonico é opcional (CharField allow_blank); envia string vazia se limpo.
        setor_canonico: values.setor_canonico ?? '',
      };
      // `nome` (código interno) só é definido na criação: é chave técnica (seed/aprovação).
      if (!editingGerencia) payload.nome = values.nome;
      if (editingGerencia) {
        await updateGerencia(editingGerencia.id, payload);
        message.success('Gerencia atualizada com sucesso');
      } else {
        await createGerencia(payload);
        message.success('Gerencia criada com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      void fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
    } catch (error) {
      form.setFields(errosDosCampos(error));
      message.error(`Erro: ${mensagemDoErro(error)}`);
    } finally {
      setSalvando(false);
    }
  };

  const handleDelete = (gerencia: GerenciaRecord): void => {
    const projetos = gerencia.projetos_count ?? 0;
    // Com projeto ativo, a exclusão já se sabe recusada (PROTECT, 409): só o aviso, sem "Sim, excluir".
    if (projetos > 0) {
      Modal.info({
        title: 'Não é possível excluir',
        content:
          `A gerência "${gerencia.rotulo}" tem ${projetos} projeto(s) ativo(s) vinculado(s).` +
          ' Gerência com projetos ou equipes vinculados, mesmo inativos, não pode ser excluída.',
        okText: 'Entendi',
      });
      return;
    }
    Modal.confirm({
      title: 'Confirmar exclusão',
      // A contagem é só dos ativos: projeto inativo ou equipe (EquipeGerencia) também barram, e o
      // backend diz qual no 409.
      content: `Tem certeza que deseja excluir a gerência "${gerencia.rotulo}"?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      // Ação destrutiva: o foco começa no Cancelar (senão um Enter repetido exclui sem confirmar).
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await deleteGerencia(gerencia.id);
          message.success('Gerencia excluida com sucesso');
          void fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
        } catch (error) {
          message.error(`Erro ao excluir: ${mensagemDoErro(error)}`);
        }
      },
    });
  };

  // C2: lista enxuta, por prioridade de largura (VISIVEL_A_PARTIR). O que some da linha vai
  // para a linha expandida (ResponsiveTable). O Rótulo nas planilhas só entra na linha a partir
  // de xxl: sem nome de tela, ele é o próprio setor.
  const columns: ColunaResponsiva<GerenciaRecord>[] = [
    // PR A: o setor aparece pelo nome de tela; o código interno (`nome`) fica só no formulário.
    // Sem detalhe que mostre o nome inteiro, ele quebra linha em vez de cortar.
    {
      title: 'Setor',
      dataIndex: 'rotulo',
      key: 'rotulo',
      render: (_, g) => <Text className="min-w-0 max-w-full break-words">{g.rotulo}</Text>,
    },
    {
      title: 'Rótulo nas planilhas',
      dataIndex: 'nome_setor',
      key: 'nome_setor',
      ellipsis: true,
      responsive: VISIVEL_A_PARTIR.xxl,
    },
    {
      title: 'Setor canônico',
      dataIndex: 'setor_canonico',
      key: 'setor_canonico',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_, g) => (g.setor_canonico ? <Etiqueta cor="geekblue" texto={g.setor_canonico} /> : <Tag>não definido</Tag>),
    },
    {
      // Sinal de qualidade do de-para v15 (read-only) — ajuda a priorizar a conferência de
      // baixa confiança (vocabulário definido pelo importer, RELAY 50), com rótulo de tela.
      title: 'Confiança',
      dataIndex: 'setor_canonico_confianca',
      key: 'setor_canonico_confianca',
      width: 120,
      responsive: VISIVEL_A_PARTIR.md,
      // Realça baixa qualidade p/ priorizar a conferência: Conferir (`na`) vermelho, Média
      // laranja, Alta verde. O filtro fica no topo da página (confiancaFiltro).
      render: (_, g) => {
        const v = g.setor_canonico_confianca;
        if (!v) return <Text type="secondary">—</Text>;
        const confianca = CONFIANCA[v];
        return <Etiqueta cor={confianca?.cor ?? 'green'} texto={confianca?.rotulo ?? v} />;
      },
    },
    {
      title: 'Gerente',
      dataIndex: 'gerente_nome',
      key: 'gerente_nome',
      ellipsis: true,
      responsive: VISIVEL_A_PARTIR.xl,
    },
    {
      title: 'Projetos',
      dataIndex: 'projetos_count',
      key: 'projetos_count',
      width: 88,
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_, g) => <Tag color="blue">{g.projetos_count}</Tag>,
    },
    {
      title: 'Situação',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 88,
      render: (_, g) => {
        const cor = g.ativo ? 'green' : 'red';
        return (
          <Tag color={cor} style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG[cor] }}>
            {g.ativo ? 'Ativo' : 'Inativo'}
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
          alvo={record.rotulo}
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="gerencias-title">
      <nav className="mb-4" aria-label="Navegacao">
        <Link to="/dat/admin">&larr; Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Title level={3} className="m-0" id="gerencias-title">
            {/* Lista que falhou não tem total: "(0)" diria que não há gerência. */}
            Gerencias{erroLista ? '' : ` (${pagination.total || 0})`}
          </Title>
          <div className="flex flex-wrap items-center gap-2">
            <Search
              placeholder="Buscar por nome ou setor..."
              aria-label="Buscar gerências por nome ou setor"
              allowClear
              style={{ width: 250, maxWidth: '100%' }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Select
              placeholder="Filtrar por confiança"
              aria-label="Filtrar por confiança"
              allowClear
              style={{ width: 180 }}
              value={confiancaFiltro}
              onChange={setConfiancaFiltro}
              options={Object.entries(CONFIANCA).map(([valor, { rotulo }]) => ({ value: valor, label: rotulo }))}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
              loading={loading}
            >
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Nova Gerencia
            </Button>
          </div>
        </header>

        <ResponsiveTable<GerenciaRecord>
          columns={columns}
          // O filtro de confiança vale sobre a página carregada (o backend ainda não filtra por ele).
          dataSource={
            confiancaFiltro ? gerencias.filter((g) => g.setor_canonico_confianca === confiancaFiltro) : gerencias
          }
          rowKey="id"
          nomeDaLinha={(g) => g.rotulo}
          loading={loading}
          erro={erroLista}
          onTentarDeNovo={() => void fetchGerencias(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
          {...(confiancaFiltro && {
            locale: { emptyText: `Nenhuma gerência com confiança ${CONFIANCA[confiancaFiltro]?.rotulo ?? confiancaFiltro} nesta página.` },
          })}
          onChange={handleTableChange}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            pageSizeOptions: ['15', '30', '50', '100'],
            showTotal: (total) => (confiancaFiltro ? `Total: ${total} (confiança filtrada nesta página)` : `Total: ${total}`),
          }}
        />
      </Card>

      {/* Modal Criar/Editar Gerencia */}
      <Modal
        title={editingGerencia ? 'Editar Gerencia' : 'Nova Gerencia'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={salvando}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          onFinish={handleSave}
        >
          <Form.Item
            name="nome_exibicao"
            label="Nome na tela"
            extra="Nome do setor que aparece nas telas. Vazio: usa o rótulo nas planilhas."
            rules={[{ max: 100, message: 'Máximo de 100 caracteres' }]}
          >
            <Input placeholder="Ex: Superativar" />
          </Form.Item>

          <Form.Item
            name="nome"
            label="Código interno"
            extra={editingGerencia ? 'Chave técnica do sistema; não é alterada pela tela.' : undefined}
            rules={[{ required: true, message: 'Código interno e obrigatorio' }]}
          >
            <Input placeholder="Ex: GERENCIA 4" disabled={!!editingGerencia} />
          </Form.Item>

          <Form.Item
            name="nome_setor"
            label="Rótulo nas planilhas"
            extra="Como o setor aparece nas planilhas importadas (usado para casar a importação)."
            rules={[{ required: true, message: 'Rótulo nas planilhas e obrigatorio' }]}
          >
            <Input placeholder="Ex: ACerta" />
          </Form.Item>

          <Form.Item
            name="setor_canonico"
            label="Setor canônico (vocabulário de setor-de-produto)"
            extra={
              erroSetores ? (
                <FalhaAoCarregar oque="os setores" erro={erroSetores} onTentarDeNovo={fetchSetores} campo={setorRef} />
              ) : undefined
            }
          >
            <Select
              ref={setorRef}
              allowClear
              showSearch
              placeholder="Selecione o setor canônico..."
              disabled={!!erroSetores && setoresProduto.length === 0}
              options={setoresProduto.map((s) => ({ label: s, value: s }))}
            />
          </Form.Item>

          <Form.Item
            name="descricao"
            label="Descricao"
          >
            <Input.TextArea rows={3} placeholder="Descricao da gerencia" />
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Gerencia ativa</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
