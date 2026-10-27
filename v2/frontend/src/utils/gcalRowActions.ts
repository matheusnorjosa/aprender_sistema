/**
 * Ações de Google Agenda por linha da página "Publicar na agenda" (#1656).
 *
 * Função PURA. A lista já vem filtrada pelo backend (`?publishable=true`): toda
 * linha é um evento aprovado que o usuário pode publicar. O que sobra decidir
 * por linha é o ESTADO GCal, espelhado aqui para oferecer só ações que o
 * backend aceita (publish/resync exigem aprovado; cancel exige o evento no Google):
 *
 * | gcal_status | sem external_event_id | com external_event_id |
 * |-------------|-----------------------|-----------------------|
 * | NONE        | publicar              | publicar              |
 * | PENDING     | —                     | —                     |
 * | PUBLISHED   | atualizar             | atualizar, remover    |
 * | ERROR       | tentar (= publicar)   | atualizar, remover    |
 *
 * Sem `ready` (status.publishReady) as ações continuam listadas, mas desabilitadas.
 *
 * Evento no Google pela planilha e não adotado (`publicado_fora_do_sistema`, virada de 16/10/2026)
 * não oferece ação nenhuma: publicar criaria um segundo evento, e o backend recusa.
 */
import type { GCalStatus, Solicitacao } from '../types';
import { formatFortaleza } from './datetime';

export type GcalRowAction = 'publicar' | 'tentar' | 'atualizar' | 'remover';

export interface GcalRowTag {
  label: string;
  color: 'default' | 'processing' | 'success' | 'error';
}

export interface GcalRowActionsResult {
  tag: GcalRowTag;
  actions: GcalRowAction[];
  disabled: boolean;
}

const TAGS: Record<GCalStatus, GcalRowTag> = {
  NONE: { label: 'Não publicado', color: 'default' },
  PENDING: { label: 'Publicando…', color: 'processing' },
  PUBLISHED: { label: 'Publicado', color: 'success' },
  ERROR: { label: 'Erro', color: 'error' },
};

function actionsFor(status: GCalStatus, hasEventId: boolean): GcalRowAction[] {
  switch (status) {
    case 'NONE':
      return ['publicar'];
    case 'PENDING':
      return [];
    case 'PUBLISHED':
      return hasEventId ? ['atualizar', 'remover'] : ['atualizar'];
    case 'ERROR':
      return hasEventId ? ['atualizar', 'remover'] : ['tentar'];
  }
}

const TAG_FORA_DO_SISTEMA: GcalRowTag = { label: 'Na agenda pela planilha', color: 'default' };

export function gcalRowActions(
  row: Pick<Solicitacao, 'gcal_status' | 'external_event_id'> & Partial<Pick<Solicitacao, 'publicado_fora_do_sistema'>>,
  { ready }: { ready: boolean },
): GcalRowActionsResult {
  if (row.publicado_fora_do_sistema) {
    return { tag: TAG_FORA_DO_SISTEMA, actions: [], disabled: !ready };
  }
  return {
    tag: TAGS[row.gcal_status],
    actions: actionsFor(row.gcal_status, !!row.external_event_id),
    disabled: !ready,
  };
}

/** Códigos do `motivo_nao_publicavel` do backend (services/solicitacao_publish.py). */
export type MotivoNaoPublicavel = 'publicado_fora_do_sistema' | 'evento_passado' | 'ja_publicado' | 'nao_publicado';

/** Motivo curto, para completar o nome acessível do botão ou da caixa de seleção. */
export const MOTIVO_NAO_PUBLICAVEL: Record<MotivoNaoPublicavel, string> = {
  publicado_fora_do_sistema: 'já está no Google Agenda pela planilha',
  evento_passado: 'o evento já terminou',
  ja_publicado: 'já publicado',
  nao_publicado: 'ainda não publicado',
};

/**
 * Espelho do `motivo_nao_publicavel` do backend: por que a linha não pode ser publicada
 * (`reenvio=false`) ou reaplicada/reenviada (`reenvio=true`), ou null se pode.
 * "Passado" compara instantes (o ISO traz o fuso), então vale em qualquer fuso do navegador.
 */
export function motivoNaoPublicavel(
  row: Pick<Solicitacao, 'gcal_status'> & Partial<Pick<Solicitacao, 'fim' | 'publicado_fora_do_sistema'>>,
  { reenvio = false, agora = Date.now() }: { reenvio?: boolean; agora?: number } = {},
): MotivoNaoPublicavel | null {
  if (row.publicado_fora_do_sistema) return 'publicado_fora_do_sistema';
  if (row.fim && Date.parse(row.fim) < agora) return 'evento_passado';
  if (reenvio) return row.gcal_status === 'NONE' ? 'nao_publicado' : null;
  return row.gcal_status === 'PUBLISHED' || row.gcal_status === 'PENDING' ? 'ja_publicado' : null;
}

/**
 * Evento que o sistema pôs (ou pode ter posto) no Google: publicado, com o id de lá, ou em ERROR
 * (a publicação que falhou pode ter criado o evento sem gravar o id). Mesmo critério do backend
 * (`esta_no_google`): excluir um desses o tira do Google também.
 */
export function estaNoGoogle(row: Pick<Solicitacao, 'gcal_status' | 'external_event_id'>): boolean {
  return row.gcal_status === 'PUBLISHED' || row.gcal_status === 'ERROR' || Boolean(row.external_event_id);
}

type EventoDaExclusao = Pick<Solicitacao, 'inicio' | 'municipio_nome' | 'projeto_nome'>;

/** O evento nas confirmações de excluir: "10/05/2026 09:00 · Crato · Vidas Em Rede". */
export function resumoDoEvento(row: EventoDaExclusao): string {
  const quando = formatFortaleza(row.inicio, 'DD/MM/YYYY HH:mm');
  return `${quando} · ${row.municipio_nome || 'sem município'} · ${row.projeto_nome || 'sem projeto'}`;
}

/**
 * Confirmação de excluir evento que está no Google (`estaNoGoogle`): sai dos dois lados. A mesma em
 * Minhas Solicitações e em Publicar na agenda. Em ERROR o evento pode não ter chegado ao Google; o
 * Meet só é citado quando existe.
 */
export function confirmacaoDeExcluirNoGoogle(
  row: EventoDaExclusao & Pick<Solicitacao, 'gcal_status' | 'meet_link'>,
): { title: string; content: string } {
  const doGoogle = row.gcal_status === 'ERROR' ? 'do Google Agenda, se estiver lá' : 'do Google Agenda';
  const meet = row.meet_link ? ', junto com o link do Meet' : '';
  return {
    title: 'Excluir evento?',
    content: `${resumoDoEvento(row)}. Ele sai do sistema e ${doGoogle}${meet}. Não dá para desfazer.`,
  };
}
