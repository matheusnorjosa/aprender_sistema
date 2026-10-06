/**
 * Admin DAT - Usuários
 *
 * Gestão de usuários: listagem, busca, criação/edição e atribuição de CPF.
 * Substitui uso cotidiano do Django Admin para usuários.
 *
 * Piloto do padrão responsivo (Programa C, C1): lista enxuta no ResponsiveTable (nome,
 * e-mail, setor, função, situação e ações, por prioridade de largura) e detalhe por
 * assunto num Drawer aberto pelo nome. Nunca na grade: ID, CPF, username (em produção
 * é o CPF), telefone e cargo.
 *
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 * GAP-001 (resolvido): Endpoint /api/usuarios-admin/ reativado
 */

import { useEffect, useMemo, useRef, useState, type JSX } from 'react';
import {
  Button,
  Input,
  Space,
  Tag,
  Typography,
  Card,
  message,
  Modal,
  Form,
  Select,
  Divider,
  Radio,
  Checkbox,
  Alert,
  Descriptions,
  Drawer,
  Grid,
  theme,
} from 'antd';
import type { TablePaginationConfig } from 'antd/es/table';
import type { FilterValue, SorterResult, SortOrder, TableCurrentDataSource } from 'antd/es/table/interface';
import type { RadioChangeEvent } from 'antd/es/radio';
import { ReloadOutlined, EditOutlined, PlusOutlined, DeleteOutlined, LockOutlined } from '@ant-design/icons';
import { Link } from 'react-router';
import { checkAuth } from '../../api/auth';
import { listUsers, createUser, updateUser, deleteUser, resetUserPassword, listGroups, getRBACMeta, listGerencias } from '../../api/adminDAT';
import {
  buildUsuarioPayload,
  funcoesProntasParaSalvar,
  gruposAposSalvar,
  lotacaoObrigatoria,
  mensagemDoErro,
  nomeDe,
} from './usuario_form_helpers';
import type { PermissaoFuncional, RBACMetaPayload, GerenciaRecord } from '../../api/adminDAT';
import { importUsuarios } from '../../api/ops';
import type { ImportResult } from '../../api/ops';
import ImportUploader from '../../components/ImportUploader';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';
import { formatFortaleza } from '../../utils/datetime';
import type { ValidationResult, ApplyResult } from '../../components/ImportUploader';
import logger from '../../utils/logger';
import { PAGE_SIZES } from '../../constants';
import type { ID } from '../../types';

/** View mode type */
type ViewMode = 'lista' | 'importar';

/**
 * Helper to convert ImportResult to ValidationResult format
 */
function toValidationResult(result: ImportResult): ValidationResult {
  return {
    stats: {
      created: result.created,
      updated: result.updated,
      unchanged: result.skipped,
    },
    errors: result.errors.map((e) => `Linha ${e.row}: ${e.message}`),
    // Avisos não-bloqueantes (ex.: coluna `grupos` ignorada por falta de
    // privilégio) vão para o alerta de Pendências, que não gateia o Aplicar.
    ...(result.warnings.length > 0 ? { pendencias: { avisos: result.warnings } } : {}),
  };
}

/**
 * Helper to convert ImportResult to ApplyResult format
 */
function toApplyResult(result: ImportResult): ApplyResult {
  return {
    stats: {
      created: result.created,
      updated: result.updated,
      unchanged: result.skipped,
    },
  };
}

const { Title, Text } = Typography;
const { Search } = Input;

/**
 * User record interface
 */
interface UserRecord {
  id: ID;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  cpf?: string;
  cpf_masked?: string;
  telefone?: string;
  cargo?: string;
  is_active: boolean;
  is_superuser: boolean;
  groups?: string[];
  group_ids_display?: ID[];
  // Lotação vigente (EquipeGerencia) — hidrata a gerência no EDIT. null se não há vínculo.
  gerencia_atual?: { gerencia_id: number; rotulo: string; nome_setor: string; setor_canonico: string; papel: string } | null;
  // Tem vínculo vigente de papel EQUIPE ("Equipe administrativa").
  equipe_administrativa?: boolean;
  date_joined?: string;
  last_login?: string | null;
}

/**
 * Login de tela: em produção o username é o CPF. CPF (só dígitos ou 000.000.000-00) sai com a
 * regra do `cpf_masked` do backend (UsuarioAdminSerializer: só os 6 últimos dígitos), para login
 * e CPF mascarados não se completarem; username que não é CPF aparece como está.
 */
function loginDeTela(username: string): string {
  return /^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$/.test(username)
    ? `***.***.${username.replace(/\D/g, '').slice(-6)}`
    : username;
}

/**
 * Ordem da lista no servidor (decisão 5 do dono): pelo nome, com o id desempatando, e não pelo
 * username (o CPF). Por coluna com `sorter`: os campos da ordem crescente (o id desempata, para
 * a paginação não repetir nem pular ninguém). A ordem é controlada: a seta e o `aria-sort`
 * mostram a que a lista tem, e ela vale na busca, na paginação, no Atualizar, no salvar e no
 * excluir. Limpar a ordenação volta ao padrão.
 */
const ORDEM_DA_COLUNA = {
  nome: ['first_name', 'last_name', 'id'],
  email: ['email', 'id'],
} as const;
type ColunaOrdenavel = keyof typeof ORDEM_DA_COLUNA;
interface Ordem {
  coluna: ColunaOrdenavel;
  sentido: NonNullable<SortOrder>;
}
const ORDEM_PADRAO: Ordem = { coluna: 'nome', sentido: 'ascend' };

function colunaOrdenavel(chave: unknown): chave is ColunaOrdenavel {
  return typeof chave === 'string' && chave in ORDEM_DA_COLUNA;
}

/** Parâmetro `ordering` da API: '-' em cada campo na decrescente. */
function ordering({ coluna, sentido }: Ordem): string {
  return ORDEM_DA_COLUNA[coluna].map((campo) => (sentido === 'descend' ? `-${campo}` : campo)).join(',');
}

/** Papel no vínculo EquipeGerencia (PAPEL_CHOICES do backend). */
const PAPEL: Record<string, string> = {
  GERENTE: 'Gerente',
  COORDENADOR: 'Coordenador',
  APOIO: 'Apoio de Coordenação',
  FORMADOR: 'Formador',
  EQUIPE: 'Equipe administrativa',
};

/** Tags que quebram linha e cortam com reticências em vez de estourar a coluna. */
function Etiquetas({ nomes, cor }: { nomes: string[]; cor: (nome: string) => string }): JSX.Element {
  if (nomes.length === 0) return <Text type="secondary">-</Text>;
  return (
    <div className="flex min-w-0 flex-wrap gap-1">
      {nomes.map((nome) => (
        <Tag
          key={nome}
          color={cor(nome)}
          title={nome}
          className="truncate"
          style={{ marginInlineEnd: 0, maxWidth: '100%', color: TEXTO_DA_TAG[cor(nome)] }}
        >
          {nome}
        </Tag>
      ))}
    </div>
  );
}

function Situacao({ ativo }: { ativo: boolean }): JSX.Element {
  const cor = ativo ? 'green' : 'red';
  return (
    <Tag color={cor} style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG[cor] }}>
      {ativo ? 'Ativo' : 'Inativo'}
    </Tag>
  );
}

const corDoSetor = (): string => 'purple';
const corDaFuncao = (nome: string): string => (nome === 'Superusuário' || nome === 'Gerente' ? 'gold' : 'blue');

interface DetalheUsuarioProps {
  usuario: UserRecord;
  setores: string[];
  funcoes: string[];
}

/** Detalhe por assunto (Drawer): o que não cabe na grade, inteiro e sem corte. */
function DetalheUsuario({ usuario, setores, funcoes }: DetalheUsuarioProps): JSX.Element {
  const lotacao = usuario.gerencia_atual;
  return (
    <div className="flex flex-col gap-6">
      <Descriptions
        title={<h3>Dados pessoais</h3>}
        size="small"
        column={1}
        items={[
          { key: 'nome', label: 'Nome', children: nomeDe(usuario) },
          { key: 'email', label: 'E-mail', children: usuario.email || '-' },
          {
            key: 'cpf',
            label: 'CPF',
            children: usuario.cpf_masked || (
              <Tag color="orange" style={{ color: TEXTO_DA_TAG['orange'] }}>
                Sem CPF
              </Tag>
            ),
          },
          { key: 'telefone', label: 'Telefone', children: usuario.telefone || '-' },
          { key: 'cargo', label: 'Cargo', children: usuario.cargo || '-' },
        ]}
      />
      <Descriptions
        title={<h3>Lotação</h3>}
        size="small"
        column={1}
        items={
          lotacao
            ? [
                { key: 'setor', label: 'Setor', children: lotacao.rotulo },
                { key: 'papel', label: 'Papel', children: PAPEL[lotacao.papel] ?? lotacao.papel },
              ]
            : [{ key: 'setor', label: 'Setor', children: <Etiquetas nomes={setores} cor={corDoSetor} /> }]
        }
      />
      <Descriptions
        title={<h3>Acesso</h3>}
        size="small"
        column={1}
        items={[
          { key: 'login', label: 'Usuário (login)', children: loginDeTela(usuario.username) },
          { key: 'situacao', label: 'Situação', children: <Situacao ativo={usuario.is_active} /> },
          { key: 'superusuario', label: 'Superusuário', children: usuario.is_superuser ? 'Sim' : 'Não' },
          { key: 'funcoes', label: 'Funções', children: <Etiquetas nomes={funcoes} cor={corDaFuncao} /> },
          {
            key: 'ultimo-acesso',
            label: 'Último acesso',
            children: usuario.last_login ? formatFortaleza(usuario.last_login) : 'Nunca',
          },
          {
            key: 'cadastro',
            label: 'Cadastrado em',
            children: usuario.date_joined ? formatFortaleza(usuario.date_joined, 'DD/MM/YYYY') : '-',
          },
        ]}
      />
    </div>
  );
}

/**
 * Group record interface
 */
interface GroupRecord {
  id: ID;
  name: string;
  permissions?: string[];
  permissoes_funcionais?: PermissaoFuncional[];
}

/**
 * User form values interface
 */
interface UserFormValues {
  username: string;
  email: string;
  first_name?: string | undefined;
  last_name?: string | undefined;
  cpf?: string;
  telefone?: string | undefined;
  cargo?: string | undefined;
  is_active: boolean;
  is_superuser: boolean;
  gerencia_id?: ID | null | undefined;
  funcao_ids: ID[];
  equipe_administrativa?: boolean | undefined;
  password?: string;
}

/**
 * Pagination state interface
 */
interface PaginationState {
  current: number;
  pageSize: number;
  total: number;
}

/**
 * Fetch params interface
 */
interface FetchParams {
  current?: number | undefined;
  pageSize?: number | undefined;
  ordem?: Ordem;
}

export default function UsuariosPage(): JSX.Element {
  const [usuarios, setUsuarios] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: PAGE_SIZES.SMALL,
    total: 0,
  });
  const [ordem, setOrdem] = useState<Ordem>(ORDEM_PADRAO);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  // #2071: as funções estavam carregadas quando o Editar abriu (e hidratou o form)?
  const [hidratouComFuncoes, setHidratouComFuncoes] = useState(false);
  // #1675 follow-up: redefinição de senha de OUTRO usuário (ação de admin).
  // Modal dedicado, separado do form de edição — intenção explícita e a
  // auditoria RESET_PASSWORD (#1672) dispara só aqui.
  const [resetPasswordUser, setResetPasswordUser] = useState<UserRecord | null>(null);
  const [resetSaving, setResetSaving] = useState(false);
  // C1: detalhe por assunto (Drawer), aberto pelo nome na lista. O usuário fica no estado
  // depois de fechar, para o conteúdo não sumir durante a animação de saída.
  const [detalheUser, setDetalheUser] = useState<UserRecord | null>(null);
  const [detalheAberto, setDetalheAberto] = useState(false);
  const abrirDetalhe = (user: UserRecord): void => {
    setDetalheUser(user);
    setDetalheAberto(true);
  };
  // Editar pelo detalhe: o modal só abre quando o Drawer acaba de fechar. Aí o Drawer já
  // devolveu o foco ao nome da linha, e é para lá que o modal o devolve ao fechar. Abrindo
  // junto, o modal guardava o Editar do Drawer (escondido) e o foco caía no <body>.
  const editarAoFecharDetalhe = useRef(false);
  // Celular (< 576 px): as ações da linha vão todas para o menu "Mais ações".
  const acoesCompactas = !Grid.useBreakpoint().sm;
  // Nome como link na cor da marca: o azul padrão do link do AntD dá 4,1:1 no branco (WCAG
  // pede 4,5:1); colorPrimary troca sozinho para o verde claro no tema escuro.
  const { token } = theme.useToken();
  // Bug 3 fix (2026-04-27): CPF é write-only por LGPD (serializer), então API
  // nunca retorna o CPF raw — apenas `cpf_masked`. No modo edit, manter o
  // campo disabled mostrando o mascarado, e exigir clique em "Alterar CPF"
  // para liberar nova entrada. Submit omite `cpf` do payload se locked.
  const [cpfEditUnlocked, setCpfEditUnlocked] = useState(false);
  const [grupos, setGrupos] = useState<GroupRecord[]>([]);
  const [gerencias, setGerencias] = useState<GerenciaRecord[]>([]);
  const [rbacMeta, setRbacMeta] = useState<RBACMetaPayload | null>(null);
  const [currentIsSuperuser, setCurrentIsSuperuser] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('lista');

  const [form] = Form.useForm<UserFormValues>();
  const [resetForm] = Form.useForm<{ nova_senha: string; confirmar_nova_senha: string }>();
  const selectedGerenciaId = Form.useWatch('gerencia_id', form);
  const equipeMarcada = Form.useWatch('equipe_administrativa', form);
  const obrigatorio = lotacaoObrigatoria({
    currentIsSuperuser,
    isEditing: !!editingUser,
    temLotacao: !!editingUser?.gerencia_atual,
    equipeAdministrativa: equipeMarcada,
  });
  const selectedFuncaoIds = Form.useWatch('funcao_ids', form) || [];

  const setorGroupsSet = useMemo(
    () => new Set(rbacMeta?.setor_groups || []),
    [rbacMeta]
  );
  const funcaoGroupsSet = useMemo(
    () => new Set(rbacMeta?.funcao_groups || []),
    [rbacMeta]
  );

  // Gerência específica (single-select). Label = rotulo (nome de tela, PR A). Só
  // gerências ATIVAS entram (carregadas no fetch de contexto já filtradas por `ativo: true`),
  // mais a lotação atual de quem está em edição quando ela foi desativada — o form a
  // reenvia e o backend aceita (sem ela o Select mostraria o id cru).
  const gerenciaOptions = useMemo(() => {
    const options = gerencias
      .slice()
      .sort((a, b) => a.rotulo.localeCompare(b.rotulo, 'pt-BR'))
      .map((g) => ({ label: g.rotulo, value: g.id }));
    const atual = editingUser?.gerencia_atual;
    if (atual && !options.some((o) => o.value === atual.gerencia_id)) {
      options.push({ label: atual.rotulo, value: atual.gerencia_id });
    }
    return options;
  }, [gerencias, editingUser]);

  const funcaoOptions = useMemo(
    () => grupos
      .filter((g) => funcaoGroupsSet.has(g.name))
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((g) => ({ label: g.name, value: g.id })),
    [grupos, funcaoGroupsSet]
  );

  /**
   * Fetch users from API
   */
  const fetchUsuarios = async (params: FetchParams = {}): Promise<void> => {
    setLoading(true);
    try {
      const apiParams: Record<string, unknown> = {};

      // Only add non-empty search
      if (searchText) {
        apiParams['search'] = searchText;
      }

      // Add pagination params
      apiParams['page'] = params.current || pagination.current;
      apiParams['page_size'] = params.pageSize || pagination.pageSize;

      // A ordem escolhida na tabela (a nova vem em params: o estado só muda no próximo render)
      apiParams['ordering'] = ordering(params.ordem ?? ordem);

      const data = await listUsers(apiParams);

      // DRF pagination response structure
      // Note: API returns AdminUser with Group[], component uses string[]
      // This is acceptable during migration - will be unified in strict mode phase
      setUsuarios(data.results);
      setPagination({
        current: params.current || pagination.current,
        pageSize: params.pageSize || pagination.pageSize,
        total: data.count || data.results.length,
      });
    } catch (error) {
      message.error(`Erro ao carregar usuários: ${(error as Error).message}`);
      logger.error('Erro ao carregar usuários:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch RBAC metadata and groups for dynamic classification
  const fetchRbacContext = async (): Promise<void> => {
    try {
      const [groupsData, meta, gerenciasData] = await Promise.all([
        listGroups({ ordering: 'name', page_size: PAGE_SIZES.ALL }),
        getRBACMeta(),
        listGerencias({ ativo: true, page_size: 1000 }),
      ]);
      setGrupos(groupsData.results);
      setRbacMeta(meta);
      setGerencias(gerenciasData.results);
    } catch (error) {
      logger.error('Erro ao carregar contexto RBAC:', error);
      message.error('Erro ao carregar metadados RBAC');
    }
  };

  // Load RBAC context and current auth profile on mount
  useEffect(() => {
    void fetchRbacContext();
    void (async () => {
      // #1741: checkAuth agora relança erros não-auth (5xx/rede). Fail-closed para
      // read-only (espelha GruposPage) em vez de deixar uma unhandled rejection.
      try {
        const auth = await checkAuth();
        setCurrentIsSuperuser(Boolean(auth.user?.is_superuser));
      } catch {
        setCurrentIsSuperuser(false);
      }
    })();
  }, []);

  // Load users on mount and search change (reset to page 1)
  useEffect(() => {
    void fetchUsuarios({ current: 1 });
  }, [searchText]);

  const handleTableChange = (
    newPagination: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    sorter: SorterResult<UserRecord> | SorterResult<UserRecord>[],
    extra: TableCurrentDataSource<UserRecord>
  ): void => {
    const params: FetchParams = {
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    };

    // Só o clique no cabeçalho muda a ordem; a paginação segue a atual (o E-mail some da
    // tabela abaixo de md, e aí o sorter da paginação viria sem ele).
    if (extra.action === 'sort') {
      const singleSorter = Array.isArray(sorter) ? sorter[0] : sorter;
      const nova =
        singleSorter?.order && colunaOrdenavel(singleSorter.columnKey)
          ? { coluna: singleSorter.columnKey, sentido: singleSorter.order }
          : ORDEM_PADRAO;
      setOrdem(nova);
      params.ordem = nova;
    }

    void fetchUsuarios(params);
  };

  const handleCreate = (): void => {
    setEditingUser(null);
    setCpfEditUnlocked(true);  // Create: campo CPF sempre liberado
    form.resetFields();
    form.setFieldsValue({
      is_active: true,
      is_superuser: false,
      gerencia_id: undefined,
      funcao_ids: [],
      equipe_administrativa: false,
    });
    setModalVisible(true);
  };

  const handleEdit = (user: UserRecord): void => {
    setEditingUser(user);
    setCpfEditUnlocked(false);  // Edit: CPF locked até user clicar "Alterar"
    // Separar IDs de grupos por tipo (só FUNÇÕES agora; o setor vem via Gerência)
    const userGroupIds = user.group_ids_display || [];
    const funcaoIds = grupos
      .filter((g) => funcaoGroupsSet.has(g.name) && userGroupIds.includes(g.id))
      .map(g => g.id);
    setHidratouComFuncoes(funcaoGroupsSet.size > 0 && grupos.length > 0);

    form.setFieldsValue({
      username: user.username,
      email: user.email,
      first_name: user.first_name,
      last_name: user.last_name,
      // CPF não é populado no modo edit — write-only por LGPD; o input mostra
      // `cpf_masked` como placeholder/valor visual via prop, não via setFieldsValue.
      telefone: user.telefone,
      cargo: user.cargo,
      is_active: user.is_active,
      is_superuser: user.is_superuser,
      gerencia_id: user.gerencia_atual?.gerencia_id ?? undefined,
      funcao_ids: funcaoIds,
      equipe_administrativa: user.equipe_administrativa,
    });
    setModalVisible(true);
  };

  const handleDelete = (user: UserRecord): void => {
    Modal.confirm({
      title: 'Confirmar exclusão',
      content: `Tem certeza que deseja excluir o usuário "${nomeDe(user)}"? Esta ação não pode ser desfeita.`,
      okText: 'Excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      // Ação destrutiva: o foco começa no Cancelar (senão um Enter repetido exclui sem confirmar).
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await deleteUser(user.id);
          message.success('Usuário excluído com sucesso');
          void fetchUsuarios();
        } catch (error) {
          message.error(`Erro ao excluir: ${(error as Error).message}`);
        }
      },
    });
  };

  const handleSave = async (values: UserFormValues): Promise<void> => {
    try {
      // Bug 3 fix (2026-04-27): payload construído via helper puro testável.
      // Regras LGPD para CPF: omitir do payload se edit+locked (mantém atual).
      const payload = buildUsuarioPayload(values, {
        isEditing: !!editingUser,
        cpfEditUnlocked,
        currentIsSuperuser,
        funcoesCarregadas: funcoesProntasParaSalvar({
          isEditing: !!editingUser,
          hidratouComFuncoes,
          funcoesTocadas: form.isFieldTouched('funcao_ids'),
          carregadasAgora: funcaoGroupsSet.size > 0 && grupos.length > 0,
        }),
      });

      if (editingUser) {
        await updateUser(editingUser.id, payload);
        message.success('Usuário atualizado com sucesso');
      } else {
        await createUser(payload);
        message.success('Usuário criado com sucesso');
      }
      setModalVisible(false);
      form.resetFields();
      void fetchUsuarios();
    } catch (error) {
      message.error(`Erro: ${mensagemDoErro(error)}`);
    }
  };

  const handleOpenResetPassword = (user: UserRecord): void => {
    setResetPasswordUser(user);
    resetForm.resetFields();
  };

  const handleResetPassword = async (values: { nova_senha: string }): Promise<void> => {
    if (!resetPasswordUser) return;
    setResetSaving(true);
    try {
      await resetUserPassword(resetPasswordUser.id, values.nova_senha);
      message.success(`Senha de "${nomeDe(resetPasswordUser)}" redefinida com sucesso`);
      setResetPasswordUser(null);
      resetForm.resetFields();
    } catch (error) {
      message.error(`Erro ao redefinir senha: ${mensagemDoErro(error)}`);
    } finally {
      setResetSaving(false);
    }
  };

  const setoresDe = (record: UserRecord): string[] =>
    record.gerencia_atual
      ? [record.gerencia_atual.rotulo]
      : (record.groups || []).filter((g) => setorGroupsSet.has(g));
  const funcoesDe = (record: UserRecord): string[] => (record.groups || []).filter((g) => funcaoGroupsSet.has(g));

  // C1: lista enxuta, por prioridade de largura (VISIVEL_A_PARTIR). O que some da linha vai
  // para a linha expandida (ResponsiveTable) e tudo está no detalhe, aberto pelo nome.
  const columns: ColunaResponsiva<UserRecord>[] = [
    {
      title: 'Nome',
      key: 'nome',
      ellipsis: true,
      sorter: true,
      sortOrder: ordem.coluna === 'nome' ? ordem.sentido : null,
      render: (_, record) => (
        <Button
          type="link"
          onClick={() => abrirDetalhe(record)}
          aria-label={`Ver detalhes de ${nomeDe(record)}`}
          title={nomeDe(record)}
          style={{ padding: 0, height: 'auto', maxWidth: '100%', color: token.colorPrimary }}
        >
          <span className="min-w-0 truncate hover:underline">{nomeDe(record)}</span>
        </Button>
      ),
    },
    {
      title: 'E-mail',
      dataIndex: 'email',
      key: 'email',
      ellipsis: true,
      sorter: true,
      sortOrder: ordem.coluna === 'email' ? ordem.sentido : null,
      responsive: VISIVEL_A_PARTIR.md,
    },
    {
      // PR A: setor = gerência da lotação vigente (EquipeGerencia), pelo nome de tela.
      // Sem vínculo (Controle, DAT, Diretoria operam por grupo), cai para os grupos de setor.
      title: 'Setor',
      key: 'setor',
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_, record) => <Etiquetas nomes={setoresDe(record)} cor={corDoSetor} />,
    },
    {
      title: 'Função',
      key: 'funcao',
      responsive: VISIVEL_A_PARTIR.xl,
      render: (_, record) => (
        <Etiquetas nomes={[...(record.is_superuser ? ['Superusuário'] : []), ...funcoesDe(record)]} cor={corDaFuncao} />
      ),
    },
    {
      title: 'Situação',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 88,
      render: (_, record) => <Situacao ativo={record.is_active} />,
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: larguraAcoesLinha(3, acoesCompactas),
      render: (_, record) => (
        <AcoesLinha
          compacto={acoesCompactas}
          alvo={nomeDe(record)}
          acoes={[
            { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: () => handleEdit(record) },
            {
              chave: 'senha',
              rotulo: 'Redefinir senha',
              icone: <LockOutlined />,
              onClick: () => handleOpenResetPassword(record),
            },
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
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="usuarios-title">
      {/* Header */}
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Title level={3} className="m-0" id="usuarios-title">
            {viewMode === 'lista'
              ? `Usuários (${pagination.total})`
              : 'Importar Usuários'}
          </Title>
          {/* Importação pela tela: só superusuário (decisão do dono, 02/10/2026). */}
          {currentIsSuperuser && (
            <Radio.Group
              value={viewMode}
              onChange={(e: RadioChangeEvent) => setViewMode(e.target.value as ViewMode)}
              buttonStyle="solid"
            >
              <Radio.Button value="lista">Lista</Radio.Button>
              <Radio.Button value="importar">Importar</Radio.Button>
            </Radio.Group>
          )}
          {viewMode === 'lista' && (
            <div className="flex flex-wrap items-center gap-2">
              <Search
                placeholder="Buscar por nome, e-mail ou CPF"
                aria-label="Buscar usuários por nome, e-mail ou CPF"
                allowClear
                style={{ width: 300, maxWidth: '100%' }}
                onSearch={(value) => setSearchText(value)}
                onChange={(e) => {
                  if (!e.target.value) setSearchText('');
                }}
              />
              <Button icon={<ReloadOutlined />} onClick={() => fetchUsuarios()} loading={loading}>
                Atualizar
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                Novo Usuário
              </Button>
            </div>
          )}
        </header>

        {viewMode === 'lista' ? (
          /* Tabela */
          (<ResponsiveTable<UserRecord>
            columns={columns}
            dataSource={usuarios}
            rowKey="id"
            nomeDaLinha={nomeDe}
            loading={loading}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showTotal: (total) => `Total: ${total} usuários`,
            }}
            onChange={handleTableChange}
          />)
        ) : (
          /* Importação */
          (<ImportUploader
            label="Importar Usuários de CSV/XLSX"
            description="Colunas obrigatórias: cpf, nome. Opcionais: email, telefone, cargo, grupos (separados por vírgula). O CPF é a chave de idempotência."
            onDryRun={async (file: File) => toValidationResult(await importUsuarios(file, true))}
            onApply={async (file: File) => {
              const result = await importUsuarios(file, false);
              // Recarregar lista após importação
              void fetchUsuarios();
              return toApplyResult(result);
            }}
          />)
        )}
      </Card>

      {/* C1: detalhe por assunto. A edição continua no modal de sempre. */}
      <Drawer
        title={detalheUser ? nomeDe(detalheUser) : 'Usuário'}
        open={detalheAberto}
        onClose={() => setDetalheAberto(false)}
        afterOpenChange={(aberto) => {
          if (!aberto && editarAoFecharDetalhe.current && detalheUser) {
            editarAoFecharDetalhe.current = false;
            handleEdit(detalheUser);
          }
        }}
        width={480}
        extra={
          detalheUser ? (
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => {
                editarAoFecharDetalhe.current = true;
                setDetalheAberto(false);
              }}
            >
              Editar
            </Button>
          ) : null
        }
      >
        {detalheUser ? (
          <DetalheUsuario usuario={detalheUser} setores={setoresDe(detalheUser)} funcoes={funcoesDe(detalheUser)} />
        ) : null}
      </Drawer>

      {/* Modal Criar/Editar Usuário */}
      <Modal
        title={editingUser ? 'Editar Usuário' : 'Novo Usuário'}
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
          <Form.Item
            name="username"
            label="Username"
            rules={[{ required: true, message: 'Username é obrigatório' }]}
            // Na edição (campo travado) o login, que é o CPF, aparece mascarado; o form guarda
            // o valor real, e o Salvar manda o que sempre mandou.
            getValueProps={(valor?: string) => ({ value: editingUser && valor ? loginDeTela(valor) : valor })}
          >
            <Input placeholder="Ex: joao.silva" disabled={!!editingUser} />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Email é obrigatório' },
              { type: 'email', message: 'Email inválido' },
            ]}
          >
            <Input placeholder="usuario@example.com" />
          </Form.Item>

          <Form.Item name="first_name" label="Nome">
            <Input placeholder="João" />
          </Form.Item>

          <Form.Item name="last_name" label="Sobrenome">
            <Input placeholder="Silva" />
          </Form.Item>

          <Form.Item
            name="cpf"
            label="CPF"
            // Bug 3 fix (2026-04-27): no edit, CPF não é required (write-only
            // por LGPD; backend mantém valor existente se omitido). No create
            // segue obrigatório.
            rules={
              !editingUser || cpfEditUnlocked
                ? [
                    { required: !editingUser, message: 'CPF é obrigatório' },
                    {
                      pattern: /^[0-9]{11}$/,
                      message: 'CPF deve conter exatamente 11 dígitos numéricos',
                    },
                  ]
                : []
            }
            // Em edit + locked, mostra cpf_masked como valor visual; o form
            // não captura porque o input fica disabled.
            help={
              editingUser && !cpfEditUnlocked
                ? 'CPF protegido por LGPD. Clique em "Alterar CPF" para editar.'
                : undefined
            }
          >
            {editingUser && !cpfEditUnlocked ? (
              <Input
                value={editingUser.cpf_masked || ''}
                disabled
                addonAfter={
                  <Button
                    type="link"
                    size="small"
                    onClick={() => setCpfEditUnlocked(true)}
                    data-testid="alterar-cpf-button"
                    style={{ padding: 0, height: 'auto' }}
                  >
                    Alterar CPF
                  </Button>
                }
              />
            ) : (
              <Input placeholder="12345678901 (apenas números)" maxLength={11} />
            )}
          </Form.Item>

          <Form.Item name="telefone" label="Telefone">
            <Input placeholder="Ex: 85999990000" maxLength={20} />
          </Form.Item>

          <Form.Item name="cargo" label="Cargo">
            <Input placeholder="Ex: Coordenador Pedagógico" maxLength={100} />
          </Form.Item>

          <Space size={24} className="mb-4">
            <Form.Item name="is_active" valuePropName="checked" style={{ marginBottom: 0 }}>
              <Checkbox>Usuário ativo</Checkbox>
            </Form.Item>

            {currentIsSuperuser ? (
              <Form.Item name="is_superuser" valuePropName="checked" style={{ marginBottom: 0 }}>
                <Checkbox>Superusuário</Checkbox>
              </Form.Item>
            ) : null}
          </Space>

          {!currentIsSuperuser ? (
            <Alert
              type="info"
              showIcon
              className="mb-4"
              message="Somente superusuários podem alterar privilégio de superusuário."
            />
          ) : null}

          <Divider orientation="left">Perfil de Acesso</Divider>

          <Alert
            type="info"
            showIcon
            className="mb-4"
            message="Como configurar"
            description="Gerência define onde a pessoa atua (o setor é atribuído automaticamente). Função define o que a pessoa pode fazer no sistema."
          />

          <Form.Item
            name="gerencia_id"
            label="Gerência (onde trabalha)"
            tooltip="Gerência específica de lotação da pessoa. O setor é derivado da gerência."
            // P0-1 Tier-0 (D-1=2a): lotação é superuser-only. Não-superuser vê o
            // valor atual, mas não edita (e o helper não envia gerencia_id). Relaxa
            // o required p/ não travar o submit de conta comum com o Select disabled.
            // #2071: obrigatória ao criar e para quem já tem lotação (o Controle não tem).
            rules={
              obrigatorio.gerencia ? [{ required: true, message: 'Selecione uma gerência' }] : []
            }
          >
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Selecione uma gerência"
              options={gerenciaOptions}
              disabled={!currentIsSuperuser}
            />
          </Form.Item>

          <Form.Item
            name="funcao_ids"
            label="Função (o que pode fazer)"
            tooltip="Papel da pessoa no processo"
            // P0-1 Tier-0 (D-1=2a): membership é superuser-only (ver gerencia_id acima).
            // #2071: obrigatória só ao criar (na edição, o DAT não tem função).
            rules={obrigatorio.funcao ? [{ required: true, message: 'Selecione pelo menos uma função' }] : []}
          >
            <Select
              mode="multiple"
              allowClear
              showSearch
              optionFilterProp="label"
              maxTagCount="responsive"
              placeholder="Selecione uma ou mais funções"
              options={funcaoOptions}
              disabled={!currentIsSuperuser}
            />
          </Form.Item>

          <Form.Item
            name="equipe_administrativa"
            valuePropName="checked"
            extra="Só registra que a pessoa trabalha nesta gerência (ex.: suporte do DAT, Controle). Não dá função, grupo, permissão nem acesso a dados da gerência, e não a põe em nenhuma lista."
          >
            <Checkbox disabled={!currentIsSuperuser}>Equipe administrativa</Checkbox>
          </Form.Item>

          <Card size="small" title="Resumo do perfil de acesso" className="mb-4">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <div>
                <Text strong>Gerência selecionada: </Text>
                {(() => {
                  // Mesmas opções do Select (inclui a lotação atual inativa).
                  const gerencia = gerenciaOptions.find((opt) => opt.value === selectedGerenciaId);
                  if (!gerencia) {
                    return <Text type="secondary">nenhuma gerência selecionada</Text>;
                  }
                  return (
                    <Tag color="green" style={{ color: TEXTO_DA_TAG['green'] }}>
                      {gerencia.label}
                    </Tag>
                  );
                })()}
              </div>
              <div>
                <Text strong>Funções selecionadas: </Text>
                {selectedFuncaoIds.length > 0 ? (
                  grupos
                    .filter((group) => selectedFuncaoIds.includes(group.id))
                    .map((group) => (
                      <Tag key={group.id} color="blue">{group.name}</Tag>
                    ))
                ) : (
                  <Text type="secondary">nenhuma função selecionada</Text>
                )}
              </div>
              <div>
                <Text strong>Permissões efetivas: </Text>
                {(() => {
                  // #2071: espelha o Salvar do backend (grupos que ficam + funções + setor
                  // da gerência só quando ela muda).
                  const selectedGroups = gruposAposSalvar({
                    grupos,
                    idsAtuais: editingUser?.group_ids_display || [],
                    funcoes: funcaoGroupsSet,
                    funcaoIds: selectedFuncaoIds,
                    gerencia: gerencias.find((ger) => ger.id === selectedGerenciaId),
                    gerenciaAnterior: gerencias.find((ger) => ger.id === editingUser?.gerencia_atual?.gerencia_id),
                  });
                  const labels = new Set<string>();
                  selectedGroups.forEach((group) => {
                    (group.permissoes_funcionais || []).forEach((permissao) => labels.add(permissao.label));
                  });
                  if (labels.size === 0) {
                    return <Text type="secondary">sem permissões específicas definidas</Text>;
                  }
                  return (
                    <>
                      <Tag color="purple">{labels.size} permissão(ões)</Tag>
                      {Array.from(labels).sort().slice(0, 6).map((label) => (
                        <Tag key={label} color="purple">{label}</Tag>
                      ))}
                      {labels.size > 6 ? <Tag>+{labels.size - 6}</Tag> : null}
                    </>
                  );
                })()}
              </div>
            </Space>
          </Card>

          {!editingUser && (
            <Form.Item
              name="password"
              label="Senha"
              rules={[{ required: true, message: 'Senha é obrigatória para novo usuário' }]}
            >
              <Input.Password placeholder="Senha inicial" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* #1675: Modal dedicado de redefinição de senha (admin -> outro usuário).
          O backend audita como RESET_PASSWORD (#1672); a senha nunca é exibida. */}
      <Modal
        title={resetPasswordUser ? `Redefinir senha — ${nomeDe(resetPasswordUser)}` : 'Redefinir senha'}
        open={resetPasswordUser !== null}
        onCancel={() => { setResetPasswordUser(null); resetForm.resetFields(); }}
        onOk={() => resetForm.submit()}
        okText="Redefinir senha"
        cancelText="Cancelar"
        confirmLoading={resetSaving}
        width={480}
      >
        <Alert
          type="info"
          showIcon
          className="mb-4"
          message="A nova senha entra em vigor imediatamente."
        />
        <Form
          form={resetForm}
          layout="vertical"
          autoComplete="off"
          onFinish={handleResetPassword}
        >
          <Form.Item
            name="nova_senha"
            label="Nova senha"
            rules={[
              { required: true, message: 'Informe a nova senha.' },
              { min: 8, message: 'A senha deve ter no mínimo 8 caracteres.' },
            ]}
          >
            <Input.Password placeholder="Nova senha" autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="confirmar_nova_senha"
            label="Confirmar nova senha"
            dependencies={['nova_senha']}
            rules={[
              { required: true, message: 'Confirme a nova senha.' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('nova_senha') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('As senhas não coincidem.'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="Confirmar nova senha" autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
