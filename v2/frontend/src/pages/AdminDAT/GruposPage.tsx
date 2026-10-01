/**
 * Admin DAT - Grupos
 *
 * CRUD de grupos Django com gestão de membros e permissões funcionais.
 * Fase 4a - RBAC funcional (Issue #830)
 *
 * Padrão responsivo (Programa C, C2): lista enxuta no ResponsiveTable (nome e ações sempre;
 * Tipo, Usuários e Permissões sobem por largura), ações no AcoesLinha. O ID não vai para a
 * grade. Padrão: v2/docs/specs/frontend/pages.spec.md, "Padrão responsivo".
 */

import { useEffect, useMemo, useState, type JSX } from 'react';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Empty,
  Form,
  Grid,
  Input,
  Modal,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  DeleteOutlined,
  EditOutlined,
  LockOutlined,
  PlusOutlined,
  ReloadOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router';
import {
  createGroup,
  deleteGroup,
  getGroup,
  getRBACMeta,
  listGroups,
  listPermissoesFuncionais,
  listUsers,
  syncGroupMembers,
  updateGroup,
} from '../../api/adminDAT';
import type { PermissaoFuncional, RBACMetaPayload } from '../../api/adminDAT';
import { checkAuth } from '../../api/auth';
import { errosDosCampos, mensagemDoErro, nomeDe } from './usuario_form_helpers';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';
import { PAGE_SIZES } from '../../constants';
import type { ID } from '../../types';

const { Title, Text } = Typography;
const { Search } = Input;

interface GroupRecord {
  id: ID;
  name: string;
  group_type?: string | null;
  user_count?: number;
  permissions?: string[];
  permissoes_funcionais?: PermissaoFuncional[];
}

interface UserRecord {
  id: ID;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  groups?: string[];
  group_ids_display?: ID[];
}

interface GroupFormValues {
  name: string;
  group_type_input: 'setor' | 'funcao';
  permissao_funcional_ids: ID[];
  member_ids: ID[];
}

interface GruposPageProps {
  forcedType?: 'setor' | 'funcao';
}

// Epic 1 RBAC Refactor (2026-04-23): categorias capability-oriented.
// `admin_dat` → `cadastros_administrativos`; `gerencia` → `supervisao`.
// Ver v2/docs/plans/rbac-refactor/epic-1-labels.md.
const CATEGORY_LABELS: Record<string, { title: string; help: string }> = {
  cadastros_administrativos: {
    title: 'Cadastros administrativos',
    help: 'Permissões para gerenciar cadastros e configurações administrativas.',
  },
  dashboard: {
    title: 'Dashboards',
    help: 'Permissões para visualizar indicadores e painéis analíticos.',
  },
  supervisao: {
    title: 'Supervisão',
    help: 'Permissões de supervisão gerencial e atuação de liderança.',
  },
  importacao: {
    title: 'Importações',
    help: 'Permissões para importar dados de planilhas e arquivos.',
  },
  operacao: {
    title: 'Operações',
    help: 'Permissões de operação do dia a dia no sistema.',
  },
  solicitacao: {
    title: 'Solicitações',
    help: 'Permissões sobre o fluxo de aprovação de solicitações.',
  },
};

// `feminino`: a concordância das frases ("Nenhuma função", "esta função", "Nome da Função").
const TYPE_UI: Record<'setor' | 'funcao', { title: string; create: string; singular: string; feminino: boolean }> = {
  setor: { title: 'Setores', create: 'Novo Setor', singular: 'Setor', feminino: false },
  funcao: { title: 'Funções', create: 'Nova Função', singular: 'Função', feminino: true },
};

function humanizeCategory(category: string): string {
  return category
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function GruposPage({ forcedType }: GruposPageProps = {}): JSX.Element {
  const [grupos, setGrupos] = useState<GroupRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupRecord | null>(null);
  const [savingGroup, setSavingGroup] = useState(false);
  // Celular (< 576 px): as ações da linha vão todas para o menu "Mais ações".
  const acoesCompactas = !Grid.useBreakpoint().sm;
  // P0-1 Tier-0 (D-1=2a): gestão de grupo/matriz/membership é superuser-only.
  // Não-superuser vê a lista, mas sem ações de escrita (co-deploy: UI para de
  // oferecer escrita antes de o backend rejeitar).
  const [currentIsSuperuser, setCurrentIsSuperuser] = useState(false);

  const [usuarios, setUsuarios] = useState<UserRecord[]>([]);
  // Os membros do modal saem desta lista e o Salvar os grava por full-replace: sem ela
  // carregada inteira, o Salvar não mexe nos membros (senão mandaria `user_ids: []`).
  const [usuariosProntos, setUsuariosProntos] = useState(false);
  const [erroUsuarios, setErroUsuarios] = useState<string | null>(null);
  const [erroLista, setErroLista] = useState<string | null>(null);
  // O toast do AntD não é região viva: o aviso do grupo reservado vai também para o leitor de tela.
  const [avisoLeitor, setAvisoLeitor] = useState('');

  const [permissoesDisponiveis, setPermissoesDisponiveis] = useState<PermissaoFuncional[]>([]);
  const [rbacMeta, setRbacMeta] = useState<RBACMetaPayload | null>(null);

  const [form] = Form.useForm<GroupFormValues>();
  const selectedPermissionIds = Form.useWatch('permissao_funcional_ids', form) || [];
  const selectedMemberIds = Form.useWatch('member_ids', form) || [];
  const selectedGroupType = Form.useWatch('group_type_input', form) || forcedType || 'setor';
  const pageTypeMeta = forcedType ? TYPE_UI[forcedType] : null;

  const reservedGroupNames = useMemo(
    () => new Set([...(rbacMeta?.setor_groups || []), ...(rbacMeta?.funcao_groups || [])]),
    [rbacMeta]
  );

  const currentMemberIds = useMemo(() => {
    if (!editingGroup) {
      return [];
    }
    return usuarios
      .filter((usuario) => (usuario.group_ids_display || []).includes(editingGroup.id))
      .map((usuario) => usuario.id);
  }, [editingGroup, usuarios]);

  const membershipDelta = useMemo(() => {
    const current = new Set(currentMemberIds);
    const selected = new Set(selectedMemberIds);
    const added = selectedMemberIds.filter((id) => !current.has(id)).length;
    const removed = currentMemberIds.filter((id) => !selected.has(id)).length;
    return { added, removed };
  }, [currentMemberIds, selectedMemberIds]);

  const permissionsByCategory = useMemo(() => {
    const grouped = new Map<string, PermissaoFuncional[]>();
    permissoesDisponiveis.forEach((permissao) => {
      const key = permissao.category || 'geral';
      const current = grouped.get(key) || [];
      current.push(permissao);
      grouped.set(key, current);
    });

    return Array.from(grouped.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([category, perms]) => ({
        category,
        categoryTitle: CATEGORY_LABELS[category]?.title || humanizeCategory(category),
        categoryHelp: CATEGORY_LABELS[category]?.help || 'Permissões relacionadas a este módulo.',
        permissions: perms.sort((a, b) => a.label.localeCompare(b.label)),
      }));
  }, [permissoesDisponiveis]);

  const isReservedGroup = (groupName: string): boolean => reservedGroupNames.has(groupName);

  // Membros pelo nome, com o e-mail para distinguir homônimos; nunca o username (é o CPF).
  const opcoesDeMembros = usuarios
    .map((usuario) => {
      const nome = nomeDe(usuario);
      return { label: nome === usuario.email ? nome : `${nome} (${usuario.email})`, value: usuario.id };
    })
    .sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'));

  // Vazio que diz o que fazer: a busca, ou o "Novo" de quem pode criar.
  const rotuloDoTipo = pageTypeMeta ? pageTypeMeta.singular.toLowerCase() : 'grupo';
  const feminino = pageTypeMeta?.feminino ?? false;
  const artigo = feminino ? 'a' : 'o';
  const nenhum = feminino ? 'Nenhuma' : 'Nenhum';
  const vazio = searchText
    ? `${nenhum} ${rotuloDoTipo} encontrad${artigo} para "${searchText}".`
    : `${nenhum} ${rotuloDoTipo} cadastrad${artigo}.` +
      (currentIsSuperuser ? ` Use "${pageTypeMeta ? pageTypeMeta.create : 'Novo Grupo'}" para criar.` : '');

  const inferGroupType = (group: GroupRecord): 'setor' | 'funcao' | undefined => {
    if (group.group_type === 'setor' || group.group_type === 'funcao') {
      return group.group_type;
    }
    if (rbacMeta?.setor_groups.includes(group.name)) {
      return 'setor';
    }
    if (rbacMeta?.funcao_groups.includes(group.name)) {
      return 'funcao';
    }
    return undefined;
  };

  const fetchGrupos = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await listGroups({
        search: searchText,
        ordering: 'name',
        page_size: PAGE_SIZES.ALL,
      });
      const loaded = data.results as GroupRecord[];
      setErroLista(null);
      if (!forcedType) {
        setGrupos(loaded);
        return;
      }

      const fallbackTypes = new Set(
        forcedType === 'setor' ? (rbacMeta?.setor_groups || []) : (rbacMeta?.funcao_groups || [])
      );
      const filtered = loaded.filter((group) => {
        if (group.group_type) {
          return group.group_type === forcedType;
        }
        return fallbackTypes.has(group.name);
      });
      setGrupos(filtered);
    } catch (error) {
      setErroLista(mensagemDoErro(error));
    } finally {
      setLoading(false);
    }
  };

  const fetchUsuarios = async (): Promise<void> => {
    setUsuariosProntos(false);
    setErroUsuarios(null);
    try {
      // M01-07 (#1612): a membership do grupo é DERIVADA desta lista e salva por
      // full-replace (sync-members). Carregar só a 1ª página revogava membros além
      // do teto do paginador ao salvar. Seguimos `next` até esgotar para garantir o
      // conjunto COMPLETO de usuários (robusto mesmo acima do max_page_size).
      const all: UserRecord[] = [];
      let page = 1;
      for (;;) {
        const data = await listUsers({ ordering: 'username', page_size: PAGE_SIZES.ALL, page });
        all.push(...(data.results as UserRecord[]));
        if (!data.next) {
          break;
        }
        page += 1;
      }
      setUsuarios(all);
      setUsuariosProntos(true);
    } catch (error) {
      setErroUsuarios(mensagemDoErro(error));
    }
  };

  const fetchPermissoesAndMeta = async (): Promise<void> => {
    try {
      const [permissionsResponse, metaResponse] = await Promise.all([
        listPermissoesFuncionais({ ordering: 'category,label', page_size: PAGE_SIZES.ALL }),
        getRBACMeta(),
      ]);
      setPermissoesDisponiveis(permissionsResponse.results);
      setRbacMeta(metaResponse);
    } catch (error) {
      message.error(`Erro ao carregar metadados RBAC: ${(error as Error).message}`);
    }
  };

  useEffect(() => {
    void fetchGrupos();
  }, [searchText, forcedType, rbacMeta]);

  // Usuários que carregam com o Editar já aberto ("Tentar de novo", ou a recarga depois de
  // salvar): os membros atuais entram no campo, que ficou desabilitado enquanto a lista não vinha.
  useEffect(() => {
    if (editingGroup && usuariosProntos && !form.isFieldTouched('member_ids')) {
      form.setFieldValue('member_ids', currentMemberIds);
    }
  }, [currentMemberIds, usuariosProntos, editingGroup, form]);

  useEffect(() => {
    void fetchUsuarios();
    void fetchPermissoesAndMeta();
    void (async () => {
      try {
        const auth = await checkAuth();
        setCurrentIsSuperuser(Boolean(auth.user?.is_superuser));
      } catch {
        setCurrentIsSuperuser(false);
      }
    })();
  }, []);

  const handleCreate = (): void => {
    setEditingGroup(null);
    form.resetFields();
    form.setFieldsValue({
      name: '',
      group_type_input: 'setor',
      permissao_funcional_ids: [],
      member_ids: [],
    });
    setModalVisible(true);
  };

  const handleEdit = async (group: GroupRecord): Promise<void> => {
    try {
      const groupDetail = (await getGroup(group.id)) as GroupRecord;
      setEditingGroup(groupDetail);
      const memberIds = usuarios
        .filter((usuario) => (usuario.group_ids_display || []).includes(group.id))
        .map((usuario) => usuario.id);
      const groupType = inferGroupType(groupDetail);
      form.setFieldsValue({
        name: groupDetail.name,
        group_type_input: groupType || 'setor',
        permissao_funcional_ids: (groupDetail.permissoes_funcionais || []).map((permissao) => permissao.id),
      });
      // Não tocado: o setFieldsValue marca o campo como tocado quando o valor muda (o modal não é
      // destruído, e o valor anterior é o do Editar ou do Novo de antes), e aí o efeito acima não
      // punha a lista que chega depois. O Salvar mandava o campo vazio ou velho por full-replace.
      form.setFields([{ name: 'member_ids', value: memberIds, touched: false }]);
      setModalVisible(true);
    } catch (error) {
      message.error(`Erro ao carregar grupo para edição: ${(error as Error).message}`);
    }
  };

  const persistGroup = async (
    values: GroupFormValues,
    options: { confirmReserved?: boolean } = {}
  ): Promise<void> => {
    setSavingGroup(true);
    try {
      const { member_ids = [], ...groupPayload } = values;
      let groupId: ID;

      if (editingGroup) {
        await updateGroup(editingGroup.id, groupPayload, options);
        groupId = editingGroup.id;
      } else {
        const createdGroup = await createGroup(groupPayload);
        groupId = createdGroup.id;
      }

      if (!usuariosProntos) {
        // Salvamento parcial não é sucesso pleno: aviso, com o motivo certo (carregando × falhou).
        const motivo = erroUsuarios ? 'a lista de usuários não carregou' : 'a lista de usuários ainda estava carregando';
        message.warning(
          editingGroup
            ? `Grupo atualizado, mas os membros não foram alterados: ${motivo}.`
            : `Grupo criado sem membros: ${motivo}.`
        );
      } else {
        const syncResult = await syncGroupMembers(groupId, { user_ids: member_ids });
        if (editingGroup) {
          message.success(
            `Grupo atualizado com sucesso (+${syncResult.added}/-${syncResult.removed} membros)`
          );
        } else {
          message.success(`Grupo criado com sucesso (${syncResult.members_count} membros vinculados)`);
        }
      }
      setModalVisible(false);
      form.resetFields();
      await Promise.all([fetchGrupos(), fetchUsuarios()]);
    } catch (error) {
      form.setFields(errosDosCampos(error));
      message.error(`Erro ao salvar grupo: ${mensagemDoErro(error)}`);
    } finally {
      setSavingGroup(false);
    }
  };

  const handleSave = async (values: GroupFormValues): Promise<void> => {
    const payload = forcedType ? { ...values, group_type_input: forcedType } : values;
    if (editingGroup && isReservedGroup(editingGroup.name) && payload.name !== editingGroup.name) {
      Modal.confirm({
        title: 'Grupo reservado',
        content:
          'Você está renomeando um grupo reservado. Confirma que deseja continuar com essa alteração?',
        okText: 'Confirmar renomeação',
        cancelText: 'Cancelar',
        onOk: () => persistGroup(payload, { confirmReserved: true }),
      });
      return;
    }

    await persistGroup(payload);
  };

  const handleDelete = (group: GroupRecord): void => {
    if (isReservedGroup(group.name)) {
      const aviso = 'Grupo reservado: exclusão bloqueada na interface.';
      message.warning(aviso);
      setAvisoLeitor(aviso);
      return;
    }

    const quantos = group.user_count ?? 0;
    Modal.confirm({
      title: 'Confirmar exclusão',
      content:
        `Tem certeza que deseja excluir o grupo "${group.name}"?` +
        (quantos > 0 ? ` ${quantos} usuário(s) deixarão de ter ${feminino ? 'esta' : 'este'} ${rotuloDoTipo}.` : ''),
      okText: 'Excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      // Ação destrutiva: o foco começa no Cancelar (senão um Enter repetido exclui sem confirmar).
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await deleteGroup(group.id);
          message.success('Grupo excluído com sucesso');
          await fetchGrupos();
        } catch (error) {
          message.error(`Erro ao excluir grupo: ${mensagemDoErro(error)}`);
        }
      },
    });
  };

  // C2: lista enxuta, por prioridade de largura (VISIVEL_A_PARTIR). O que some da linha vai
  // para a linha expandida (ResponsiveTable). O ID não vai para a grade.
  const columns: ColunaResponsiva<GroupRecord>[] = [
    {
      title: 'Nome',
      key: 'name',
      // Sem detalhe para mostrar o nome inteiro, ele quebra linha em vez de cortar.
      render: (_, record) => (
        <div className="flex min-w-0 flex-wrap items-center gap-1">
          <Text className="min-w-0 max-w-full break-words">{record.name}</Text>
          {isReservedGroup(record.name) ? (
            <Tag
              color="gold"
              icon={<LockOutlined />}
              style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG['gold'] }}
            >
              Reservado
            </Tag>
          ) : null}
        </div>
      ),
    },
    {
      title: 'Tipo',
      key: 'group_type',
      width: 96,
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_, record) => {
        const type = inferGroupType(record);
        if (type === 'funcao') {
          return <Tag color="geekblue" style={{ marginInlineEnd: 0 }}>Função</Tag>;
        }
        if (type === 'setor') {
          return <Tag color="green" style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG['green'] }}>Setor</Tag>;
        }
        return <Text type="secondary">-</Text>;
      },
    },
    {
      title: 'Usuários',
      key: 'user_count',
      width: 128,
      responsive: VISIVEL_A_PARTIR.md,
      render: (_, record) => (
        <Tag color="blue" style={{ marginInlineEnd: 0 }}>{record.user_count || 0} usuário(s)</Tag>
      ),
    },
    {
      title: 'Permissões funcionais',
      key: 'permissoes_funcionais',
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_, record) => {
        const permissoes = record.permissoes_funcionais;
        if (!permissoes || permissoes.length === 0) {
          return <Text type="secondary">Sem permissões funcionais</Text>;
        }

        const displayed = permissoes.slice(0, 3);
        const remaining = permissoes.length - displayed.length;

        // Tags que quebram linha e cortam com reticências em vez de estourar a coluna.
        return (
          <div className="flex min-w-0 flex-wrap gap-1">
            {displayed.map((permissao) => (
              <Tag
                key={permissao.id}
                color="purple"
                title={permissao.label}
                className="truncate"
                style={{ marginInlineEnd: 0, maxWidth: '100%' }}
              >
                {permissao.label}
              </Tag>
            ))}
            {remaining > 0 ? <Tag style={{ marginInlineEnd: 0 }}>+{remaining}</Tag> : null}
          </div>
        );
      },
    },
    // P0-1 Tier-0: sem escrita para não-superuser, a coluna nem aparece (o aviso fica no topo).
    ...(currentIsSuperuser
      ? [
          {
            title: 'Ações',
            key: 'acoes',
            width: larguraAcoesLinha(2, acoesCompactas),
            render: (_: unknown, record: GroupRecord) => {
              const reserved = isReservedGroup(record.name);
              return (
                <AcoesLinha
                  compacto={acoesCompactas}
                  alvo={record.name}
                  acoes={[
                    { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: () => void handleEdit(record) },
                    // Reservado: o Excluir só avisa que a exclusão está bloqueada (handleDelete).
                    reserved
                      ? { chave: 'excluir', rotulo: 'Excluir (reservado)', icone: <LockOutlined />, onClick: () => handleDelete(record) }
                      : {
                          chave: 'excluir',
                          rotulo: 'Excluir',
                          icone: <DeleteOutlined />,
                          onClick: () => handleDelete(record),
                          perigo: true,
                        },
                  ]}
                />
              );
            },
          },
        ]
      : []),
  ];

  return (
    <section
      className="p-6 bg-gray-100"
      style={{ minHeight: 'calc(100vh - 64px)' }}
      aria-labelledby="grupos-title"
    >
      <nav className="mb-4" aria-label="Navegação">
        <Link to="/dat/admin">← Voltar para Admin DAT</Link>
      </nav>

      <Card>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Title level={3} className="m-0" id="grupos-title">
            {/* Lista que falhou não tem total: "(0)" diria que não há grupo. */}
            <TeamOutlined aria-hidden="true" /> {pageTypeMeta ? pageTypeMeta.title : 'Grupos RBAC'}
            {erroLista ? '' : ` (${grupos.length})`}
          </Title>
          <div className="flex flex-wrap items-center gap-2">
            <Search
              placeholder={pageTypeMeta ? `Buscar ${pageTypeMeta.singular.toLowerCase()} por nome` : 'Buscar por nome'}
              aria-label={`Buscar ${pageTypeMeta ? pageTypeMeta.title.toLowerCase() : 'grupos'} por nome`}
              allowClear
              style={{ width: 250, maxWidth: '100%' }}
              onSearch={setSearchText}
              onChange={(event) => !event.target.value && setSearchText('')}
            />
            <Button icon={<ReloadOutlined />} onClick={() => void fetchGrupos()} loading={loading}>
              Atualizar
            </Button>
            {currentIsSuperuser ? (
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                {pageTypeMeta ? pageTypeMeta.create : 'Novo Grupo'}
              </Button>
            ) : null}
          </div>
        </header>

        {!currentIsSuperuser ? (
          <Text type="secondary" className="mb-4 block">
            <LockOutlined aria-hidden="true" /> Somente superusuário cria, edita ou exclui.
          </Text>
        ) : null}

        <span role="status" className="sr-only">{avisoLeitor}</span>

        <ResponsiveTable<GroupRecord>
          columns={columns}
          dataSource={grupos}
          rowKey="id"
          nomeDaLinha={(grupo) => grupo.name}
          loading={loading}
          erro={erroLista}
          onTentarDeNovo={() => void fetchGrupos()}
          locale={{ emptyText: vazio }}
          pagination={{ pageSize: 15, showTotal: (total) => `Total: ${total}` }}
        />
      </Card>

      <Modal
        title={
          editingGroup
            ? `Editar ${pageTypeMeta ? pageTypeMeta.singular : 'Grupo'}`
            : (pageTypeMeta ? pageTypeMeta.create : 'Novo Grupo')
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={savingGroup}
        width={820}
      >
        <Form form={form} layout="vertical" autoComplete="off" onFinish={(values) => void handleSave(values)}>
          <Form.Item
            name="name"
            label={`Nome d${artigo} ${pageTypeMeta ? pageTypeMeta.singular : 'Grupo'}`}
            rules={[{ required: true, message: 'Nome é obrigatório' }]}
          >
            <Input placeholder={pageTypeMeta ? `Ex: ${pageTypeMeta.singular} Pedagógic${artigo}` : 'Ex: DAT, Superintendência, Coordenador'} />
          </Form.Item>

          {!forcedType ? (
            <Form.Item
              name="group_type_input"
              label="Tipo do Grupo"
              rules={[{ required: true, message: 'Tipo do grupo é obrigatório' }]}
            >
              <Select
                options={[
                  { label: 'Setor (onde o usuário trabalha)', value: 'setor' },
                  { label: 'Função (o que o usuário pode fazer)', value: 'funcao' },
                ]}
              />
            </Form.Item>
          ) : null}

          <Form.Item
            name="permissao_funcional_ids"
            label={selectedGroupType === 'funcao' ? 'Permissões de acesso da Função' : 'Permissões de acesso'}
            extra="Use termos de negócio: selecione apenas o necessário para este perfil."
          >
            {permissionsByCategory.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Nenhuma permissão funcional disponível"
              />
            ) : (
              <Checkbox.Group className="w-full">
                <Space direction="vertical" className="w-full" size="middle">
                  {permissionsByCategory.map(({ category, categoryTitle, categoryHelp, permissions }) => (
                    <Card
                      key={category}
                      size="small"
                      title={
                        <Space direction="vertical" size={0}>
                          <Text strong>{categoryTitle}</Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>{categoryHelp}</Text>
                        </Space>
                      }
                    >
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {permissions.map((permissao) => (
                          <Checkbox key={permissao.id} value={permissao.id}>
                            <Space direction="vertical" size={0}>
                              <Text>{permissao.label}</Text>
                              {permissao.description ? (
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                  {permissao.description}
                                </Text>
                              ) : null}
                            </Space>
                          </Checkbox>
                        ))}
                      </div>
                    </Card>
                  ))}
                </Space>
              </Checkbox.Group>
            )}
          </Form.Item>

          {!usuariosProntos ? (
            <Alert
              className="mb-4"
              type={erroUsuarios ? 'error' : 'info'}
              showIcon
              message={erroUsuarios ? 'Não foi possível carregar os usuários.' : 'Carregando os usuários…'}
              description={
                (erroUsuarios ? `${erroUsuarios} ` : '') +
                (editingGroup
                  ? 'Os membros deste grupo não serão alterados ao salvar.'
                  : 'O grupo será criado sem membros.')
              }
              action={
                erroUsuarios ? (
                  <Button size="small" onClick={() => void fetchUsuarios()}>
                    Tentar de novo
                  </Button>
                ) : undefined
              }
            />
          ) : null}

          <Form.Item
            name="member_ids"
            label="Membros do grupo"
            tooltip="Selecione os usuários que devem pertencer a este grupo"
          >
            <Select
              mode="multiple"
              allowClear
              showSearch
              disabled={!usuariosProntos}
              placeholder="Selecione os membros"
              optionFilterProp="label"
              options={opcoesDeMembros}
            />
          </Form.Item>

          <Card size="small" title="Resumo antes de salvar" className="mb-2">
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Text>
                Permissões selecionadas: <Tag color="purple">{selectedPermissionIds.length}</Tag>
              </Text>
              {/* Sem a lista, a contagem seria 0 (o campo está vazio): mostra o estado da lista, não um número. */}
              {usuariosProntos ? (
                <Text>
                  Membros selecionados: <Tag color="blue">{selectedMemberIds.length}</Tag>
                </Text>
              ) : null}
              {!usuariosProntos ? (
                <Text type="secondary">
                  {!erroUsuarios
                    ? 'Membros: aguardando a lista de usuários…'
                    : editingGroup
                      ? 'Membros: não serão alterados (a lista de usuários não carregou).'
                      : 'Membros: nenhum (a lista de usuários não carregou).'}
                </Text>
              ) : editingGroup ? (
                <Text type="secondary">
                  Alterações de membros: +{membershipDelta.added} / -{membershipDelta.removed}
                </Text>
              ) : (
                <Text type="secondary">Novo grupo: os membros serão vinculados no mesmo salvamento.</Text>
              )}
            </Space>
          </Card>
        </Form>
      </Modal>
    </section>
  );
}

