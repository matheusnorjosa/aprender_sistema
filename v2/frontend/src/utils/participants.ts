/**
 * Rótulo humano de participantes/convidados de um evento.
 *
 * Convidados importados (import v15) podem não ter FK de usuário — pessoas "que saíram"
 * têm o nome preservado em `guest_nome`, sem FK. A exibição segue a cadeia:
 * usuario (nome) → guest_nome → guest_email → email.
 */
import type { Participation } from '../types/solicitacao';

/** Rótulo de um único participante (nome do usuário FK, ou nome/email do convidado). */
export function participantLabel(p: Participation): string {
  if (p.usuario) {
    const nomeCompleto = [p.usuario.first_name, p.usuario.last_name].filter(Boolean).join(' ').trim();
    return nomeCompleto || p.usuario.username || p.usuario.email || '';
  }
  return p.guest_nome || p.guest_email || p.email || '';
}

/** Nomes dos FORMADORES de uma lista de participações, unidos por ", " (vazios descartados). */
export function formadoresLabel(participations: Participation[] | undefined | null): string {
  if (!Array.isArray(participations)) return '';
  return participations
    .filter((p) => p.role === 'FORMADOR')
    .map(participantLabel)
    .filter((nome) => nome.length > 0)
    .join(', ');
}

/** Participante já com `nome` resolvido (shape [{role, nome}] do MeEventSerializer, #1945). */
export interface ParticipanteSlim {
  role: string;
  nome: string;
}

/**
 * Nomes dos FORMADORES a partir da lista pré-resolvida [{role, nome}] (MeusEventos).
 * O `nome` já vem na cascata usuario → guest_nome → guest_email pelo backend — aqui só filtra
 * o papel FORMADOR (inclui quem saiu, ao contrário do campo `formadores` legado).
 */
export function formadoresNomes(participantes: ParticipanteSlim[] | undefined | null): string {
  if (!Array.isArray(participantes)) return '';
  return participantes
    .filter((p) => p.role === 'FORMADOR')
    .map((p) => p.nome)
    .filter((nome) => nome.length > 0)
    .join(', ');
}
