/**
 * Helpers puros (sem React) para o formulário de Usuário (Bug 3 fix, 2026-04-27).
 *
 * CPF é write-only por LGPD no serializer backend (`extra_kwargs` em
 * `UsuarioAdminSerializer`). API nunca retorna CPF raw — apenas `cpf_masked`.
 * Por isso no edit precisamos:
 * - Mostrar `cpf_masked` como visual (input disabled)
 * - Não exigir CPF como required
 * - Liberar nova entrada apenas após clique em "Alterar CPF"
 * - Omitir `cpf` do payload se user não optou por alterar (backend mantém atual)
 *
 * Esta lógica é extraída em função pura para ser testável sem render do form.
 */

import type { FormInstance } from 'antd';
import type { ID } from '../../types';

export interface UsuarioFormValues {
  username: string;
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
 */
export function buildUsuarioPayload(
  values: UsuarioFormValues,
  options: BuildPayloadOptions,
): Record<string, unknown> {
  const { funcao_ids = [], gerencia_id, equipe_administrativa, is_superuser, cpf, ...rest } = values;
  const { isEditing, cpfEditUnlocked, currentIsSuperuser, funcoesCarregadas = true } = options;
  const editaLotacao = currentIsSuperuser && funcoesCarregadas;

  // CPF: incluir se create OU se edit+unlocked com valor preenchido
  const includeCpf = !isEditing || cpfEditUnlocked;
  const cpfPayload = includeCpf && cpf ? { cpf } : {};

  // is_superuser: incluir apenas se quem está editando é superuser
  const superuserPayload = currentIsSuperuser ? { is_superuser } : {};

  // group_ids (memberships): P0-1 Tier-0 (D-1=2a) — gestão de grupo é
  // superuser-only. Editor não-superuser NÃO envia group_ids (co-deploy: para
  // de enviar antes de o backend rejeitar). DAT segue editando conta comum
  // (cadastral/senha/ativo) sem tocar em memberships. Agora só as FUNÇÕES — o
  // grupo de setor é auto-atribuído pelo backend a partir da Gerência.
  const groupsPayload = editaLotacao ? { group_ids: [...funcao_ids] } : {};

  // gerencia_id (lotação): mesmo gate superuser-only. O backend cria/sincroniza
  // o vínculo EquipeGerencia; null = não altera o vínculo existente.
  const gerenciaPayload = editaLotacao ? { gerencia_id: gerencia_id ?? null } : {};
  // Papel EQUIPE: mesmo gate; reenvia o valor hidratado (salvar sem mudar mantém o vínculo).
  const equipePayload =
    editaLotacao && typeof equipe_administrativa === 'boolean' ? { equipe_administrativa } : {};

  return {
    ...rest,
    ...cpfPayload,
    ...superuserPayload,
    ...groupsPayload,
    ...gerenciaPayload,
    ...equipePayload,
  };
}

/** Setores que compõem um par aprovador; espelha `APPROVER_COMPOSITES` (`apps/core/rbac/helpers.py`). */
const SETORES_DE_PAR_APROVADOR = new Set(['Superintendência', 'Controle']);

interface GrupoLike {
  id: ID;
  name: string;
}

interface GerenciaLike {
  id: ID;
  nome: string;
  setor_canonico?: string | null | undefined;
}

/**
 * #2071: o que é obrigatório no form (só para superuser, o único que edita lotação). Ao criar,
 * gerência e função. Na edição, a função é opcional (o DAT não tem) e a gerência só é obrigatória
 * para quem já tem lotação: o Controle não tem, e limpar a gerência não pode ser um jeito de salvar
 * uma aprovadora sem revogar. Com "Equipe administrativa" marcada, a gerência é obrigatória (o vínculo
 * é nela) e a função não (a equipe do DAT e do Controle não tem função).
 */
export function lotacaoObrigatoria(opts: {
  currentIsSuperuser: boolean;
  isEditing: boolean;
  temLotacao: boolean;
  equipeAdministrativa?: boolean | undefined;
}): { gerencia: boolean; funcao: boolean } {
  const { currentIsSuperuser, isEditing, temLotacao, equipeAdministrativa = false } = opts;
  return {
    gerencia: currentIsSuperuser && (!isEditing || temLotacao || equipeAdministrativa),
    funcao: currentIsSuperuser && !isEditing && !equipeAdministrativa,
  };
}

function setorDaGerencia<G extends GrupoLike>(grupos: G[], gerencia: GerenciaLike | undefined): G | undefined {
  const setor = (gerencia?.setor_canonico ?? '').trim();
  if (!setor || SETORES_DE_PAR_APROVADOR.has(setor)) return undefined;
  return grupos.find((g) => g.name === setor);
}

/** Funções que viram papel no vínculo; espelha `PAPEL_POR_FUNCAO` (`services/equipe_gerencia.py`). */
const FUNCOES_COM_PAPEL = new Set(['Formador', 'Coordenador', 'Gerente', 'Apoio de Coordenação']);

/**
 * #2071: grupos da pessoa depois do Salvar, espelhando `_apply_lotacao` do backend. Os grupos
 * atuais que não são FUNÇÃO ficam; as funções vêm do form; o grupo de setor da gerência entra e
 * sai só quando a gerência muda e só com função que tem papel (a Equipe administrativa nunca dá
 * grupo); setor de par aprovador (Superintendência, Controle) não vira grupo.
 */
export function gruposAposSalvar<G extends GrupoLike>(args: {
  grupos: G[];
  idsAtuais: ID[];
  funcoes: Set<string>;
  funcaoIds: ID[];
  gerencia: GerenciaLike | undefined;
  gerenciaAnterior: GerenciaLike | undefined;
}): G[] {
  const { grupos, idsAtuais, funcoes, funcaoIds, gerencia, gerenciaAnterior } = args;
  let final = grupos.filter((g) => idsAtuais.includes(g.id) && !funcoes.has(g.name));
  final.push(...grupos.filter((g) => funcaoIds.includes(g.id) && !final.includes(g)));
  const temFuncaoComPapel = final.some((g) => FUNCOES_COM_PAPEL.has(g.name));
  if (gerencia && gerencia.id !== gerenciaAnterior?.id && temFuncaoComPapel) {
    const antigo = setorDaGerencia(grupos, gerenciaAnterior);
    const novo = setorDaGerencia(grupos, gerencia);
    if (antigo && antigo !== novo) final = final.filter((g) => g !== antigo);
    if (novo && !final.includes(novo)) final.push(novo);
  }
  return final;
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

/** Nome de tela da pessoa; sem nome cadastrado, o e-mail (nunca o username, que é o CPF). */
export function nomeDe(user: { first_name?: string; last_name?: string; email?: string }): string {
  return `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email || 'Sem nome';
}
