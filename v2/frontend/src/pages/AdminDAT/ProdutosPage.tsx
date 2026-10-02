/**
 * Admin DAT - Produtos
 *
 * CRUD de produtos por projeto com codigo e status ativo.
 */

import { useState, useEffect, useRef, type JSX } from 'react';
import { flushSync } from 'react-dom';
import { Button, Input, Tag, Typography, Card, message, Modal, Form, Checkbox, Select, Grid, Space } from 'antd';
import type { InputRef, RefSelectProps } from 'antd';
import type { TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router';
import {
  listProdutos,
  createProduto,
  updateProduto,
  deleteProduto,
  listProjetos,
  listColecoesOptions,
} from '../../api/adminDAT';
import type { ProdutoRecord, ProdutoPayload, ColecaoOption } from '../../api/adminDAT';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';
import { FalhaAoCarregar } from '../../components/FalhaAoCarregar';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';
import { DEFAULT_PAGE_SIZE } from '../../constants';
import type { ID, Projeto } from '../../types';
import { aposConfirmacaoFechar, dialogoDeExclusaoEmUso } from './excluirEmUso';
import { errosDosCampos, mensagemDoErro } from './usuario_form_helpers';

const { Title, Text } = Typography;
const { Search } = Input;

/** Texto opcional: vazio vira '-' (o cinza #bfbfbf de antes dava 1,9:1 no branco). */
const ouTraco = (texto: string | null | undefined): string => (texto && texto.trim() ? texto : '-');

/**
 * Produto form values interface
 */
interface ProdutoFormValues {
  codigo: string;
  nome: string;
  descricao: string;
  projeto: ID;
  colecao?: ID | null;
  ativo: boolean;
}

export default function ProdutosPage(): JSX.Element {
  const [produtos, setProdutos] = useState<ProdutoRecord[]>([]);
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [colecoes, setColecoes] = useState<ColecaoOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  // O texto no campo de busca (a busca só vale no Enter): controlado para o "Limpar" do vazio o apagar.
  const [busca, setBusca] = useState('');
  const buscaRef = useRef<InputRef>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProduto, setEditingProduto] = useState<ProdutoRecord | null>(null);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });

  const [projetoFiltro, setProjetoFiltro] = useState<ID | undefined>(undefined);
  const [erroLista, setErroLista] = useState<string | null>(null);
  const [erroProjetos, setErroProjetos] = useState<string | null>(null);
  const [erroColecoes, setErroColecoes] = useState<string | null>(null);
  // O "Tentar de novo" que carregou põe o foco no campo que ele recarregou.
  const filtroProjetoRef = useRef<RefSelectProps>(null);
  const projetoRef = useRef<RefSelectProps>(null);
  const colecaoRef = useRef<RefSelectProps>(null);
  const [salvando, setSalvando] = useState(false);

  // Celular (< 576 px): as ações da linha vão todas para o menu "Mais ações", e o Código sai
  // da grade (fica junto do nome: o nome pode repetir, o código não).
  const acoesCompactas = !Grid.useBreakpoint().sm;

  const [form] = Form.useForm<ProdutoFormValues>();
  const selectedProjeto = Form.useWatch('projeto', form);
  const colecoesDoProjeto = colecoes.filter((c) => selectedProjeto == null || c.projeto === selectedProjeto);

  const fetchProdutos = async (
    current = pagination.current || 1,
    pageSize = pagination.pageSize || DEFAULT_PAGE_SIZE,
  ): Promise<void> => {
    setLoading(true);
    try {
      const data = await listProdutos({
        search: searchText,
        projeto: projetoFiltro,
        ordering: 'nome',
        page: current,
        page_size: pageSize,
      });
      setProdutos(data.results);
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

  // Opções: o erro fica até a resposta (o "Tentar de novo" não some com o foco nele) e, no
  // sucesso, a tela atualiza na hora (flushSync), para o Select já estar habilitado quando recebe
  // o foco. Devolvem se carregou.
  const fetchProjetos = async (): Promise<boolean> => {
    try {
      const data = await listProjetos({ page_size: 200 });
      flushSync(() => {
        setProjetos(data.results);
        setErroProjetos(null);
      });
      return true;
    } catch (error) {
      setErroProjetos(mensagemDoErro(error));
      return false;
    }
  };

  const fetchColecoes = async (): Promise<boolean> => {
    try {
      const data = await listColecoesOptions();
      flushSync(() => {
        setColecoes(data);
        setErroColecoes(null);
      });
      return true;
    } catch (error) {
      setErroColecoes(mensagemDoErro(error));
      return false;
    }
  };

  useEffect(() => {
    void fetchProdutos(1, pagination.pageSize || DEFAULT_PAGE_SIZE);
  }, [searchText, projetoFiltro]);

  const handleTableChange = (newPagination: TablePaginationConfig): void => {
    void fetchProdutos(
      newPagination.current || 1,
      newPagination.pageSize || pagination.pageSize || DEFAULT_PAGE_SIZE,
    );
  };

  useEffect(() => {
    void fetchProjetos();
    void fetchColecoes();
  }, []);

  const handleCreate = (): void => {
    setEditingProduto(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (produto: ProdutoRecord): void => {
    setEditingProduto(produto);
    form.setFieldsValue({
      codigo: produto.codigo,
      nome: produto.nome,
      descricao: produto.descricao,
      projeto: produto.projeto,
      colecao: produto.colecao,
      ativo: produto.ativo,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: ProdutoFormValues): Promise<void> => {
    setSalvando(true);
    try {
      const payload: ProdutoPayload = {
        codigo: values.codigo,
        nome: values.nome,
        descricao: values.descricao,
        projeto: values.projeto,
        colecao: values.colecao ?? null,
        ativo: values.ativo,
      };
      if (editingProduto) {
        await updateProduto(editingProduto.id, payload);
        message.success('Produto atualizado com sucesso');
      } else {
        await createProduto(payload);
        message.success('Produto criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      void fetchProdutos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
    } catch (error) {
      form.setFields(errosDosCampos(error));
      message.error(`Erro: ${mensagemDoErro(error)}`);
    } finally {
      setSalvando(false);
    }
  };

  const handleDelete = (produto: ProdutoRecord): void => {
    // 409 (em uso): o diálogo "Não é possível excluir" abre quando este terminar de fechar, ou na hora,
    // se a pessoa já o fechou com o DELETE em andamento (excluirEmUso.ts).
    const aposFechar = aposConfirmacaoFechar();
    Modal.confirm({
      title: 'Confirmar exclusão',
      // O nome pode repetir; o código, não.
      content: `Tem certeza que deseja excluir o produto "${produto.nome}" (código ${produto.codigo})?`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      // Ação destrutiva: o foco começa no Cancelar (senão um Enter repetido exclui sem confirmar).
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await deleteProduto(produto.id);
          message.success('Produto excluido com sucesso');
          void fetchProdutos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
        } catch (error) {
          const emUso = dialogoDeExclusaoEmUso({
            erro: error,
            registro: `o produto "${produto.nome}" (código ${produto.codigo})`,
            ativo: produto.ativo,
            desativar: () => updateProduto(produto.id, { ativo: false }),
            desativado: 'Produto desativado',
            recarregar: () => void fetchProdutos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE),
          });
          if (emUso) aposFechar.abrir(emUso);
          else message.error(`Erro ao excluir: ${mensagemDoErro(error)}`);
        }
      },
      afterClose: aposFechar.afterClose,
    });
  };

  // Vazio que diz o que fazer: com o filtro de projeto, o jeito de limpá-lo (como a UF em Municípios).
  // Com a busca também, cita as duas e limpa as duas: o projeto pode ter produtos que só não batem
  // com a busca.
  const nomeDoProjetoFiltro = projetos.find((p) => p.id === projetoFiltro)?.nome ?? projetoFiltro;
  const vazio = projetoFiltro ? (
    <Space direction="vertical" size={4}>
      <span>
        {searchText
          ? `Nenhum produto para "${searchText}" no projeto ${nomeDoProjetoFiltro}.`
          : `Nenhum produto para o projeto ${nomeDoProjetoFiltro}.`}
      </span>
      <Button
        size="small"
        onClick={() => {
          setProjetoFiltro(undefined);
          setSearchText('');
          setBusca('');
          // O botão some com o clique (o vazio sai): o foco vai para a busca, não para o body.
          buscaRef.current?.focus();
        }}
      >
        {searchText ? 'Limpar busca e filtro de projeto' : 'Limpar filtro de projeto'}
      </Button>
    </Space>
  ) : null;

  // C2: lista enxuta, por prioridade de largura (VISIVEL_A_PARTIR). O que some da linha vai
  // para a linha expandida (ResponsiveTable). O ID interno não vai para a grade, e a
  // Descrição (texto longo) só entra nela a partir de xxl (1600 px).
  const columns: ColunaResponsiva<ProdutoRecord>[] = [
    {
      title: 'Nome',
      dataIndex: 'nome',
      key: 'nome',
      // Sem detalhe que mostre o nome inteiro, ele quebra linha em vez de cortar. No celular, o
      // código (fora da grade) vai junto: é a chave única, o nome pode repetir.
      render: (_, record) => (
        <div className="min-w-0">
          <Text className="max-w-full break-words">{record.nome}</Text>
          {acoesCompactas ? (
            <Text type="secondary" className="block max-w-full break-words">
              {record.codigo}
            </Text>
          ) : null}
        </div>
      ),
    },
    { title: 'Código', dataIndex: 'codigo', key: 'codigo', width: 136, ellipsis: true, responsive: VISIVEL_A_PARTIR.sm },
    { title: 'Projeto', dataIndex: 'projeto_nome', key: 'projeto_nome', ellipsis: true, responsive: VISIVEL_A_PARTIR.md },
    {
      title: 'Coleção',
      dataIndex: 'colecao_nome',
      key: 'colecao_nome',
      ellipsis: true,
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_, record) => ouTraco(record.colecao_nome),
    },
    {
      title: 'Descrição',
      dataIndex: 'descricao',
      key: 'descricao',
      ellipsis: true,
      responsive: VISIVEL_A_PARTIR.xxl,
      render: (_, record) => ouTraco(record.descricao),
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="produtos-title">
      <nav className="mb-4" aria-label="Navegacao">
        <Link to="/dat/admin">&larr; Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Title level={3} className="m-0" id="produtos-title">
            {/* Lista que falhou não tem total: "(0)" diria que não há produto. */}
            Produtos{erroLista ? '' : ` (${pagination.total || 0})`}
          </Title>
          <div className="flex flex-wrap items-center gap-2">
            <Search
              ref={buscaRef}
              placeholder="Buscar por nome ou codigo..."
              aria-label="Buscar produtos por nome ou código"
              allowClear
              style={{ width: 250, maxWidth: '100%' }}
              value={busca}
              onSearch={setSearchText}
              onChange={(e) => {
                setBusca(e.target.value);
                if (!e.target.value) setSearchText('');
              }}
            />
            <Select
              ref={filtroProjetoRef}
              placeholder="Filtrar por projeto"
              aria-label="Filtrar por projeto"
              allowClear
              showSearch
              optionFilterProp="label"
              style={{ width: 220, maxWidth: '100%' }}
              disabled={!!erroProjetos && projetos.length === 0}
              value={projetoFiltro}
              onChange={setProjetoFiltro}
              options={projetos.map((p) => ({ value: p.id, label: p.nome }))}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchProdutos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
              loading={loading}
            >
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Produto
            </Button>
          </div>
        </header>

        {/* Projetos que não carregaram: o filtro fica desabilitado e o motivo aparece aqui, não "Não há dados". */}
        {erroProjetos ? (
          <FalhaAoCarregar
            oque="os projetos"
            erro={erroProjetos}
            onTentarDeNovo={fetchProjetos}
            campo={filtroProjetoRef}
            className="mb-4"
          />
        ) : null}

        <ResponsiveTable<ProdutoRecord>
          columns={columns}
          dataSource={produtos}
          rowKey="id"
          nomeDaLinha={(produto) => produto.nome}
          loading={loading}
          erro={erroLista}
          onTentarDeNovo={() => void fetchProdutos(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE)}
          {...(vazio && { locale: { emptyText: vazio } })}
          onChange={handleTableChange}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            pageSizeOptions: ['15', '30', '50', '100'],
            showTotal: (total) => `Total: ${total}`,
          }}
        />
      </Card>

      {/* Modal Criar/Editar Produto */}
      <Modal
        title={editingProduto ? 'Editar Produto' : 'Novo Produto'}
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
            name="codigo"
            label="Codigo"
            rules={[{ required: true, message: 'Codigo e obrigatorio' }]}
          >
            <Input placeholder="Ex: PROD-001" />
          </Form.Item>

          <Form.Item
            name="nome"
            label="Nome do Produto"
            rules={[{ required: true, message: 'Nome e obrigatorio' }]}
          >
            <Input placeholder="Ex: Material Didatico" />
          </Form.Item>

          <Form.Item
            name="descricao"
            label="Descricao"
          >
            <Input.TextArea rows={3} placeholder="Descricao do produto" />
          </Form.Item>

          <Form.Item
            name="projeto"
            label="Projeto"
            rules={[{ required: true, message: 'Projeto e obrigatorio' }]}
            extra={
              erroProjetos ? (
                <FalhaAoCarregar oque="os projetos" erro={erroProjetos} onTentarDeNovo={fetchProjetos} campo={projetoRef} />
              ) : undefined
            }
          >
            <Select
              ref={projetoRef}
              placeholder="Selecione um projeto"
              showSearch
              disabled={!!erroProjetos && projetos.length === 0}
              optionFilterProp="children"
              filterOption={(input, option) =>
                (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
              }
              // A coleção é do projeto: trocar o projeto a limpa (senão gravava a de outro projeto).
              onChange={() => form.setFieldValue('colecao', undefined)}
            >
              {projetos.map((p) => (
                <Select.Option key={p.id} value={p.id}>
                  {p.nome}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="colecao"
            label="Coleção"
            help={selectedProjeto == null ? 'Selecione um projeto para listar as coleções' : undefined}
            extra={
              erroColecoes ? (
                <FalhaAoCarregar oque="as coleções" erro={erroColecoes} onTentarDeNovo={fetchColecoes} campo={colecaoRef} />
              ) : undefined
            }
          >
            <Select
              ref={colecaoRef}
              placeholder="Selecione uma coleção (opcional)"
              allowClear
              showSearch
              disabled={!!erroColecoes && colecoes.length === 0}
              optionFilterProp="children"
              filterOption={(input, option) =>
                (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
              }
            >
              {colecoesDoProjeto.map((c) => (
                <Select.Option key={c.id} value={c.id}>
                  {c.nome}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Produto ativo</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
