/**
 * AdminDAT — CRUD de Projetos Gerais (#1914)
 *
 * ProjetoGeral é a FAMÍLIA de projeto (nome-base, ex.: "PROJETO AMMA"), com a política de
 * cálculo de códigos (por aluno / por professor) e o flag de AVALIAR. O ViewSet já existia
 * (/api/projetos-gerais/); esta tela dá o CRUD que faltava.
 *
 * Fora de escopo (costura backend #1914-BE): a conferência de `setor_canonico` — esse campo
 * é do model Gerencia/Projeto e não é serializado, então não entra aqui.
 *
 * Padrão responsivo (Programa C, C2): lista enxuta no ResponsiveTable. Sempre na linha o
 * nome, Situação e as ações; as demais colunas sobem por largura e o que some vai para a linha
 * expandida. Nunca na grade: ID e descrição (no formulário).
 */
import { useState, useEffect, type JSX } from 'react';
import { Button, Input, Tag, Typography, Card, message, Modal, Form, Select, Checkbox, InputNumber, Grid } from 'antd';
import type { TablePaginationConfig } from 'antd/es/table';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { Link } from 'react-router';
import {
  listProjetosGerais,
  createProjetoGeral,
  updateProjetoGeral,
  deleteProjetoGeral,
  type ProjetoGeralRecord,
  type ProjetoGeralPayload,
} from '../../api/adminDAT';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';
import { DEFAULT_PAGE_SIZE } from '../../constants';
import { aposConfirmacaoFechar, dialogoDeExclusaoEmUso } from './excluirEmUso';
import { errosDosCampos, mensagemDoErro } from './usuario_form_helpers';

const { Title, Text } = Typography;
const { Search } = Input;

function SimNao({ valor, corDoNao }: { valor: boolean; corDoNao: string }): JSX.Element {
  const cor = valor ? 'green' : corDoNao;
  return (
    <Tag color={cor} style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG[cor] }}>
      {valor ? 'Sim' : 'Não'}
    </Tag>
  );
}

/** Rótulo curto no Select (com a fórmula, cortava a 360 px); a fórmula vai abaixo do campo e na coluna. */
const TIPO_CALCULO_OPTIONS = [
  { label: 'Por aluno', value: 'por_aluno', formula: 'alunos ÷ divisor' },
  { label: 'Por professor', value: 'por_professor', formula: 'professores × multiplicador' },
  { label: 'Não se aplica', value: 'nao_aplicavel', formula: 'não gera códigos' },
];

interface ProjetoGeralFormValues {
  nome: string;
  usa_avaliar?: boolean;
  tipo_calculo_codigos?: 'por_aluno' | 'por_professor' | 'nao_aplicavel';
  divisor_aluno?: number;
  multiplicador_professor?: number | string;
  ativo?: boolean;
  descricao?: string;
}

export default function ProjetosGeraisPage(): JSX.Element {
  const [projetos, setProjetos] = useState<ProjetoGeralRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchText, setSearchText] = useState<string>('');
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [editing, setEditing] = useState<ProjetoGeralRecord | null>(null);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });
  const [form] = Form.useForm<ProjetoGeralFormValues>();
  // Só o parâmetro do cálculo escolhido aparece (o outro continua no formulário, escondido).
  const tipoCalculo = Form.useWatch('tipo_calculo_codigos', form);
  const formulaDoCalculo = TIPO_CALCULO_OPTIONS.find((o) => o.value === tipoCalculo)?.formula;
  const [salvando, setSalvando] = useState(false);
  const [erroLista, setErroLista] = useState<string | null>(null);
  // Celular (< 576 px): as ações da linha vão todas para o menu "Mais ações".
  const acoesCompactas = !Grid.useBreakpoint().sm;

  const fetchProjetos = async (page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<void> => {
    try {
      setLoading(true);
      const data = await listProjetosGerais({
        ...(searchText && { search: searchText }),
        ordering: 'nome',
        page,
        page_size: pageSize,
      });
      setProjetos(data.results ?? []);
      setErroLista(null);
      setPagination((prev) => ({ ...prev, current: page, pageSize, total: data.count ?? 0 }));
    } catch (error) {
      setErroLista(mensagemDoErro(error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchProjetos(1, pagination.pageSize ?? DEFAULT_PAGE_SIZE);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText]);

  const handleTableChange = (p: TablePaginationConfig): void => {
    void fetchProjetos(p.current ?? 1, p.pageSize ?? DEFAULT_PAGE_SIZE);
  };

  const handleCreate = (): void => {
    setEditing(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: ProjetoGeralRecord): void => {
    setEditing(record);
    form.setFieldsValue({
      nome: record.nome,
      usa_avaliar: record.usa_avaliar,
      tipo_calculo_codigos: record.tipo_calculo_codigos,
      divisor_aluno: record.divisor_aluno,
      multiplicador_professor: record.multiplicador_professor,
      ativo: record.ativo,
      descricao: record.descricao,
    });
    setModalVisible(true);
  };

  const handleSave = async (values: ProjetoGeralFormValues): Promise<void> => {
    setSalvando(true);
    try {
      // Monta o payload só com campos definidos (exactOptionalPropertyTypes) e converte
      // multiplicador_professor para string (DecimalField no backend).
      const payload: ProjetoGeralPayload = {
        nome: values.nome,
        ...(values.usa_avaliar !== undefined && { usa_avaliar: values.usa_avaliar }),
        ...(values.tipo_calculo_codigos !== undefined && { tipo_calculo_codigos: values.tipo_calculo_codigos }),
        ...(values.divisor_aluno !== undefined && { divisor_aluno: values.divisor_aluno }),
        ...(values.multiplicador_professor != null && {
          multiplicador_professor: String(values.multiplicador_professor),
        }),
        ...(values.ativo !== undefined && { ativo: values.ativo }),
        ...(values.descricao !== undefined && { descricao: values.descricao }),
      };
      if (editing) {
        await updateProjetoGeral(editing.id, payload);
        message.success('Projeto geral atualizado');
      } else {
        await createProjetoGeral(payload);
        message.success('Projeto geral criado');
      }
      setModalVisible(false);
      void fetchProjetos(pagination.current ?? 1, pagination.pageSize ?? DEFAULT_PAGE_SIZE);
    } catch (error) {
      form.setFields(errosDosCampos(error));
      message.error(`Erro ao salvar: ${mensagemDoErro(error)}`);
    } finally {
      setSalvando(false);
    }
  };

  const handleDelete = (record: ProjetoGeralRecord): void => {
    const projetos = record.projetos_count ?? 0;
    // 409 (em uso): o diálogo "Não é possível excluir" abre quando este terminar de fechar, ou na hora,
    // se a pessoa já o fechou com o DELETE em andamento (excluirEmUso.ts).
    const aposFechar = aposConfirmacaoFechar();
    Modal.confirm({
      title: 'Excluir projeto geral',
      // Os projetos da família não somem: ficam sem projeto geral (SET_NULL no backend), inclusive os
      // inativos, que a contagem (só de ativos) não inclui.
      content:
        `Tem certeza que deseja excluir "${record.nome}"?` +
        (projetos > 0
          ? ` Os projetos desta família (${projetos} ativo(s) e os inativos) ficarão sem projeto geral.`
          : ' Não há projetos ativos nesta família; os inativos, se houver, ficarão sem projeto geral.'),
      okText: 'Sim, excluir',
      cancelText: 'Cancelar',
      okButtonProps: { danger: true },
      // Ação destrutiva: o foco começa no Cancelar (senão um Enter repetido exclui sem confirmar).
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await deleteProjetoGeral(record.id);
          message.success('Projeto geral excluído');
          void fetchProjetos(pagination.current ?? 1, pagination.pageSize ?? DEFAULT_PAGE_SIZE);
        } catch (error) {
          const emUso = dialogoDeExclusaoEmUso({
            erro: error,
            registro: `o projeto geral "${record.nome}"`,
            ativo: record.ativo,
            desativar: () => updateProjetoGeral(record.id, { ativo: false }),
            desativado: 'Projeto geral desativado',
            recarregar: () => void fetchProjetos(pagination.current ?? 1, pagination.pageSize ?? DEFAULT_PAGE_SIZE),
          });
          if (emUso) aposFechar.abrir(emUso);
          else message.error(`Erro ao excluir: ${mensagemDoErro(error)}`);
        }
      },
      afterClose: aposFechar.afterClose,
    });
  };

  // C2: lista enxuta, por prioridade de largura (VISIVEL_A_PARTIR). O que some da linha vai
  // para a linha expandida (ResponsiveTable).
  const columns: ColunaResponsiva<ProjetoGeralRecord>[] = [
    {
      title: 'Nome',
      dataIndex: 'nome',
      key: 'nome',
      // Sem detalhe que mostre o nome inteiro, ele quebra linha em vez de cortar.
      render: (_, p) => <Text className="min-w-0 max-w-full break-words">{p.nome}</Text>,
    },
    {
      title: 'Usa AVALIAR',
      dataIndex: 'usa_avaliar',
      key: 'usa_avaliar',
      width: 112,
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_, p) => <SimNao valor={p.usa_avaliar} corDoNao="default" />,
    },
    {
      title: 'Cálculo de códigos',
      dataIndex: 'tipo_calculo_codigos',
      key: 'tipo_calculo_codigos',
      ellipsis: true,
      responsive: VISIVEL_A_PARTIR.md,
      render: (_, p) => {
        const tipo = TIPO_CALCULO_OPTIONS.find((o) => o.value === p.tipo_calculo_codigos);
        return tipo ? `${tipo.label} (${tipo.formula})` : p.tipo_calculo_codigos;
      },
    },
    {
      title: 'Projetos',
      dataIndex: 'projetos_count',
      key: 'projetos_count',
      width: 88,
      responsive: VISIVEL_A_PARTIR.lg,
    },
    {
      title: 'Situação',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 88,
      render: (_, p) => {
        const cor = p.ativo ? 'green' : 'red';
        return (
          <Tag color={cor} style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG[cor] }}>
            {p.ativo ? 'Ativo' : 'Inativo'}
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
    <section
      className="p-6 bg-gray-100"
      style={{ minHeight: 'calc(100vh - 64px)' }}
      aria-labelledby="projetos-gerais-title"
    >
      <nav aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>
      <Card style={{ marginTop: 16 }}>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Title level={2} id="projetos-gerais-title" className="m-0">
            Projetos Gerais
          </Title>
          <div className="flex flex-wrap items-center gap-2">
            <Search
              placeholder="Buscar por nome..."
              aria-label="Buscar projetos gerais por nome"
              allowClear
              onSearch={(v) => setSearchText(v)}
              style={{ width: 240, maxWidth: '100%' }}
            />
            <Button
              icon={<ReloadOutlined />}
              loading={loading}
              onClick={() => fetchProjetos(pagination.current ?? 1, pagination.pageSize ?? DEFAULT_PAGE_SIZE)}
            >
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Novo Projeto Geral
            </Button>
          </div>
        </header>
        <ResponsiveTable<ProjetoGeralRecord>
          columns={columns}
          dataSource={projetos}
          rowKey="id"
          nomeDaLinha={(p) => p.nome}
          loading={loading}
          erro={erroLista}
          onTentarDeNovo={() => void fetchProjetos(pagination.current ?? 1, pagination.pageSize ?? DEFAULT_PAGE_SIZE)}
          onChange={handleTableChange}
          pagination={pagination}
        />
      </Card>

      <Modal
        title={editing ? 'Editar Projeto Geral' : 'Novo Projeto Geral'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={salvando}
        width={600}
      >
        <Form form={form} layout="vertical" autoComplete="off" onFinish={handleSave}>
          <Form.Item name="nome" label="Nome" rules={[{ required: true, message: 'Nome é obrigatório' }]}>
            <Input placeholder="Ex: PROJETO AMMA" />
          </Form.Item>
          <Form.Item
            name="tipo_calculo_codigos"
            label="Cálculo de códigos"
            initialValue="por_professor"
            extra={formulaDoCalculo ? `Cálculo: ${formulaDoCalculo}.` : undefined}
          >
            <Select options={TIPO_CALCULO_OPTIONS.map(({ label, value }) => ({ label, value }))} />
          </Form.Item>
          <Form.Item
            name="divisor_aluno"
            label="Divisor (por aluno)"
            initialValue={20}
            hidden={tipoCalculo !== 'por_aluno'}
          >
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="multiplicador_professor"
            label="Multiplicador (por professor)"
            initialValue={1.1}
            hidden={tipoCalculo !== 'por_professor'}
          >
            <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="usa_avaliar" valuePropName="checked" initialValue={false}>
            <Checkbox>Usa AVALIAR</Checkbox>
          </Form.Item>
          <Form.Item name="ativo" valuePropName="checked" initialValue={true}>
            <Checkbox>Projeto ativo</Checkbox>
          </Form.Item>
          <Form.Item name="descricao" label="Descrição">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
