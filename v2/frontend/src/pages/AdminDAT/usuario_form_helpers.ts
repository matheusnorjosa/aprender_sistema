/**
 * Helpers puros (sem React) para o formulário de Usuário (Bug 3 fix, 2026-04-27).
 *
 * O campo `cpf` é write-only por LGPD no serializer backend (`extra_kwargs` em
 * `UsuarioAdminSerializer`): a resposta traz `cpf_masked`. O login (`username`), que é o CPF, chega
 * inteiro ao DAT por decisão do dono (05/11/2026); a tela o mostra mascarado (`loginDeTela`).
 * Por isso no edit precisamos:
 * - Mostrar `cpf_masked` como visual (input disabled)
 * - Não exigir CPF como required
 * - Liberar nova entrada apenas após clique em "Alterar CPF"
 * - Omitir `cpf` do payload se user não optou por alterar (backend mantém atual)
 *
 * Esta lógica é extraída em função pura para ser testável sem render do form.
 */

import type { FormInstance } from 'antd';
import { computeCapabilities } from '../../hooks/useCapabilities';
import type { ID } from '../../types';

export interface UsuarioFormValues {
  // Só leitura: o login é o CPF (D14). O servidor o grava ao criar e o troca junto com o CPF; o payload não o leva.
  username?: string | undefined;
  email: string;
  // exactOptionalPropertyTypes: casam com UserFormValues (hidratado de um AntD Form
  // cujos campos são T | undefined). buildUsuarioPayload já trata undefined/vazio.
  first_name?: string | undefined;
  last_name?: string | undefined;
  cpf?: string | undefined;
  telefone?: string | undefined;
  cargo?: string | undefined;
  is_active: boolean;
  is_superuser: boolean;
  // Gerência específica (single-select). O backend deriva o papel da FUNÇÃO e
  // auto-atribui o grupo de setor — o FE só envia a Gerência + as Funções.
  gerencia_id?: ID | null | undefined;
  funcao_ids: ID[];
  // Papel EQUIPE ("Equipe administrativa") na gerência: não vem de função, tem caixa própria.
  // undefined = não hidratado, o payload não envia e o backend mantém como está.
  equipe_administrativa?: boolean | undefined;
  password?: string | undefined;
}

export interface BuildPayloadOptions {
  /** Se está em modo edit (true) ou create (false) */
  isEditing: boolean;
  /** Se o user clicou em "Alterar CPF" no edit (sempre true em create) */
  cpfEditUnlocked: boolean;
  /** Se o user logado é superuser (controla visibilidade de is_superuser no payload) */
  currentIsSuperuser: boolean;
  /**
   * 17/10/2026: o DAT (`manage_lotacao_comum`) lota esta conta nas gerências comuns (não é a própria nem
   * tem vínculo reservado). Envia a lotação como o superusuário; o backend aplica a regra.
   */
  lotaComum?: boolean;
  /**
   * #2071: se a lista de funções (RBAC meta + grupos) carregou. Sem ela, o form hidrata as funções
   * vazias; mandar `group_ids` tiraria todas as funções (e a aprovação) por falha de carga.
   */
  funcoesCarregadas?: boolean;
}

/**
 * Constrói payload para createUser/updateUser a partir dos valores do form.
 *
 * Regras LGPD-compliant para CPF:
 * - Create: sempre enviar `cpf` (required no schema)
 * - Edit + locked: omitir `cpf` do payload (backend mantém valor atual)
 * - Edit + unlocked + valor preenchido: enviar `cpf` novo
 * - Edit + unlocked + valor vazio: omitir (não substitui CPF existente por vazio)
 *
 * Login e e-mail (lote C, 06/11/2026): `username` nunca vai (o servidor o deriva do CPF). Na edição, e-mail
 * vazio não vai: o e-mail de reserva chega vazio do servidor (D15) e o salvar mantém o gravado.
 */
export function buildUsuarioPayload(
  values: UsuarioFormValues,
  options: BuildPayloadOptions,
): Record<string, unknown> {
  const { funcao_ids = [], gerencia_id, equipe_administrativa, is_superuser, cpf, username: _login, email, ...rest } =
    values;
  const { isEditing, cpfEditUnlocked, currentIsSuperuser, lotaComum = false, funcoesCarregadas = true } = options;
  const editaLotacao = (currentIsSuperuser || lotaComum) && funcoesCarregadas;

  // CPF: incluir se create OU se edit+unlocked com valor preenchido
  const includeCpf = !isEditing || cpfEditUnlocked;
  const cpfPayload = includeCpf && cpf ? { cpf } : {};

  // is_superuser: incluir apenas se quem está editando é superuser
  const superuserPayload = currentIsSuperuser ? { is_superuser } : {};

  // group_ids (memberships): P0-1 Tier-0 (D-1=2a) — gestão de grupo é do
  // superuser e, desde 17/10/2026, do DAT que lota nas gerências comuns (`lotaComum`).
  // Fora disso o editor não-superuser NÃO envia group_ids (cadastral/senha/ativo só).
  // Só as FUNÇÕES — o grupo de setor é auto-atribuído pelo backend a partir da Gerência.
  const groupsPayload = editaLotacao ? { group_ids: [...funcao_ids] } : {};

  // gerencia_id (lotação): mesmo gate. O backend cria/sincroniza
  // o vínculo EquipeGerencia; null = não altera o vínculo existente.
  const gerenciaPayload = editaLotacao ? { gerencia_id: gerencia_id ?? null } : {};
  // Papel EQUIPE: mesmo gate; reenvia o valor hidratado (salvar sem mudar mantém o vínculo).
  const equipePayload =
    editaLotacao && typeof equipe_administrativa === 'boolean' ? { equipe_administrativa } : {};

  const emailPayload = !isEditing || email ? { email } : {};

  return {
    ...rest,
    ...emailPayload,
    ...cpfPayload,
    ...superuserPayload,
    ...groupsPayload,
    ...gerenciaPayload,
    ...equipePayload,
  };
}

interface GerenciaLike {
  id: ID;
  nome: string;
  setor_canonico?: string | null | undefined;
}

/**
 * O que o pacote da gerência dá a quem é Equipe ou Gerente nela; espelha `PERFIL_PERMITIDO` e `PACOTE`
 * (`apps/core/services/rbac_pacotes.py`). PR 11: DAT e Controle aprovam; a Diretoria (D20) supervisiona e
 * vê os painéis, sem aprovar.
 */
const AVISO_DO_PACOTE: Record<string, string> = {
  'GERENCIA DAT': 'Nesta gerência, Equipe e Gerente recebem o pacote do setor, inclusive aprovar solicitações.',
  CONTROLE: 'Nesta gerência, Equipe e Gerente recebem o pacote do setor, inclusive aprovar solicitações.',
  DIRETORIA: 'Nesta gerência, Equipe e Gerente recebem o pacote da Diretoria: supervisão e painéis, sem aprovar solicitações.',
};

/** O aviso do pacote que a gerência dá a quem é Equipe ou Gerente nela; null se ela não dá pacote. */
export function avisoDoPacote(gerencia: Pick<GerenciaLike, 'nome'> | undefined): string | null {
  return (gerencia && AVISO_DO_PACOTE[gerencia.nome]) ?? null;
}

/**
 * #2071: o que é obrigatório no form (para quem edita lotação: o superuser e o DAT com `lotaComum`). Ao criar,
 * gerência e função. Na edição, a função é opcional (o DAT não tem) e a gerência só é obrigatória
 * para quem já tem lotação: o Controle não tem, e limpar a gerência não pode ser um jeito de salvar
 * uma aprovadora sem revogar. Com "Equipe administrativa" marcada, a gerência é obrigatória (o vínculo
 * é nela) e a função não (a equipe do DAT e do Controle não tem função).
 */
export function lotacaoObrigatoria(opts: {
  currentIsSuperuser: boolean;
  lotaComum?: boolean;
  isEditing: boolean;
  temLotacao: boolean;
  equipeAdministrativa?: boolean | undefined;
}): { gerencia: boolean; funcao: boolean } {
  const { currentIsSuperuser, lotaComum = false, isEditing, temLotacao, equipeAdministrativa = false } = opts;
  const edita = currentIsSuperuser || lotaComum;
  return {
    gerencia: edita && (!isEditing || temLotacao || equipeAdministrativa),
    funcao: edita && !isEditing && !equipeAdministrativa,
  };
}

/**
 * 17/10/2026: por que o DAT (`manage_lotacao_comum`) não edita a lotação desta conta; null = edita (ou não é o
 * caso: superusuário edita tudo, sem a policy ninguém edita). Espelha `_valida_lotacao_comum` do backend.
 */
export function motivoDaLotacaoTravada(opts: {
  currentIsSuperuser: boolean;
  podeLotarComum: boolean;
  propria: boolean;
  reservada: boolean;
}): string | null {
  if (opts.currentIsSuperuser || !opts.podeLotarComum) return null;
  if (opts.propria) return 'Sua própria lotação só o superusuário altera.';
  if (opts.reservada) {
    return 'Esta pessoa trabalha no DAT, no Controle ou na Diretoria, ou é Gerente da Superintendência: a lotação dela só o superusuário altera.';
  }
  return null;
}

/** Funções que viram papel no vínculo; espelha `PAPEL_POR_FUNCAO` (`services/equipe_gerencia.py`). */
const FUNCOES_COM_PAPEL = new Set(['Formador', 'Coordenador', 'Gerente', 'Apoio de Coordenação']);

/**
 * D10: só o superusuário dá ou tira função sem papel no vínculo (ex.: Assistente Administrativo); o servidor
 * recusa o DAT (`_valida_lotacao_comum`). Para ele a opção fica bloqueada, não escondida.
 */
export function funcaoSoDoSuperusuario(nome: string): boolean {
  return !FUNCOES_COM_PAPEL.has(nome);
}

/**
 * #2071: se o salvar pode mandar funções e gerência. Na edição, só se as funções estavam carregadas
 * quando o Editar abriu (senão o form foi preenchido com funções vazias) ou se a pessoa mexeu nelas
 * depois. Ao criar, basta estarem carregadas agora.
 */
export function funcoesProntasParaSalvar(opts: {
  isEditing: boolean;
  hidratouComFuncoes: boolean;
  funcoesTocadas: boolean;
  carregadasAgora: boolean;
}): boolean {
  if (!opts.isEditing) return opts.carregadasAgora;
  return opts.hidratouComFuncoes || opts.funcoesTocadas;
}

/**
 * #2071: texto do erro de API para o usuário. A validação do backend chega como
 * `{detail: "Erro de validação.", errors: {campo: [...]}}`; o motivo está em `errors`.
 */
export function mensagemDoErro(error: unknown): string {
  const err = error as Error & { response?: { data?: { errors?: Record<string, unknown> } } };
  const errors = err.response?.data?.errors;
  if (errors && typeof errors === 'object') {
    const textos = Object.values(errors).flatMap((v) => (Array.isArray(v) ? v.map(String) : [String(v)]));
    if (textos.length > 0) return textos.join(' ');
  }
  return err.message;
}

/**
 * C2: os erros de validação do backend (`errors: {campo: [...]}`) no formato do `form.setFields`,
 * para a mensagem aparecer no campo a corrigir (ex.: código repetido), e não só num toast.
 */
export function errosDosCampos<Valores>(error: unknown): Parameters<FormInstance<Valores>['setFields']>[0] {
  const errors = (error as { response?: { data?: { errors?: unknown } } }).response?.data?.errors;
  if (!errors || typeof errors !== 'object') return [];
  // O nome vem do backend: um campo que o formulário não tem só não aparece.
  return Object.entries(errors).map(([name, v]) => ({
    name: name as Parameters<FormInstance<Valores>['setFields']>[0][number]['name'],
    errors: Array.isArray(v) ? v.map(String) : [String(v)],
  }));
}

/** E-mail de reserva `<cpf>@placeholder.local` da conta importada sem e-mail (D15); espelha `pii.email_de_reserva`. */
function emailDeReserva(email: string): boolean {
  return email.trim().toLowerCase().endsWith('@placeholder.local');
}

/** Nome de tela da pessoa; sem nome cadastrado, o e-mail (nunca o username, que é o CPF, nem o e-mail de reserva). */
export function nomeDe(user: { first_name?: string; last_name?: string; email?: string }): string {
  const email = user.email && !emailDeReserva(user.email) ? user.email : '';
  return `${user.first_name || ''} ${user.last_name || ''}`.trim() || email || 'Sem nome';
}

/**
 * O que a pessoa vê no menu, pelas policies dela no servidor (`GET /usuarios-admin/{id}/policies/`,
 * a mesma regra de `/me/policies/`). Os itens e a ordem são os do `AppSidebar`, com os submenus
 * pelo nome do grupo (Controle, Dashboards, DAT, Solicitações); a Página Inicial fica de fora.
 * Só o básico vira uma frase simples, para quem não é técnico (ensaio r3, 28/10/2026).
 */
export function resumoDoMenu(policies: readonly string[]): { itens: string[]; frase: string | null } {
  const caps = computeCapabilities(policies);
  const itens = ['Meus Eventos'];
  if (caps.canAccessApprovals) itens.push('Aprovações');
  if (caps.canAccessAvailabilityBlocks) itens.push('Bloqueios');
  if (caps.canAccessControleSection) itens.push('Controle');
  if (caps.canManageInternalActions) itens.push('Ações Internas');
  if (caps.canAccessTravel) itens.push('Deslocamentos');
  if (
    caps.canViewOverviewDashboard ||
    caps.canViewComprasDashboard ||
    caps.canViewTeamDashboard ||
    caps.canViewGcalDashboard ||
    caps.canViewMapMetrics
  ) {
    itens.push('Dashboards');
  }
  if (caps.canManageAdminRegistries) itens.push('DAT');
  if (caps.canAccessMonthlyAvailability) itens.push('Grade Mensal');
  if (caps.canCreateSolicitation) itens.push('Solicitações');
  if (caps.canPublishSetorSolicitacao) itens.push('Publicar na agenda');
  const basico = itens.join('|');
  const frase =
    basico === 'Meus Eventos'
      ? 'Vê só os próprios eventos.'
      : basico === 'Meus Eventos|Bloqueios'
        ? 'Vê os próprios eventos e registra bloqueios.'
        : null;
  return { itens, frase };
}
