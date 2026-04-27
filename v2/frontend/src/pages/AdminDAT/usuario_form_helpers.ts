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

import type { ID } from '../../types';

export interface UsuarioFormValues {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  cpf?: string;
  telefone?: string;
  cargo?: string;
  is_active: boolean;
  is_superuser: boolean;
  setor_ids: ID[];
  funcao_ids: ID[];
  password?: string;
}

export interface BuildPayloadOptions {
  /** Se está em modo edit (true) ou create (false) */
  isEditing: boolean;
  /** Se o user clicou em "Alterar CPF" no edit (sempre true em create) */
  cpfEditUnlocked: boolean;
  /** Se o user logado é superuser (controla visibilidade de is_superuser no payload) */
  currentIsSuperuser: boolean;
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
  const { setor_ids = [], funcao_ids = [], is_superuser, cpf, ...rest } = values;
  const { isEditing, cpfEditUnlocked, currentIsSuperuser } = options;

  // CPF: incluir se create OU se edit+unlocked com valor preenchido
  const includeCpf = !isEditing || cpfEditUnlocked;
  const cpfPayload = includeCpf && cpf ? { cpf } : {};

  // is_superuser: incluir apenas se quem está editando é superuser
  const superuserPayload = currentIsSuperuser ? { is_superuser } : {};

  return {
    ...rest,
    ...cpfPayload,
    ...superuserPayload,
    group_ids: [...setor_ids, ...funcao_ids],
  };
}
