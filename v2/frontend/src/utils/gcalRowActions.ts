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
 *
 * Evento de formação (`tipo_evento_de_formacao`, CON-08) no Google ganha `cancelar` ("Cancelar evento": o
 * título lá ganha "(CANCELADO) "), ao lado de `remover`. A linha já cancelada na agenda só mostra o estado
 * ("Cancelado na agenda", "Cancelando…" ou "Erro ao cancelar"); no erro com id, oferece cancelar de novo.
 */
import type { GCalStatus, Solicitacao } from '../types';
import { formatFortaleza } from './datetime';

export type GcalRowAction = 'publicar' | 'tentar' | 'atualizar' | 'remover' | 'cancelar';

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

/** Estado da linha cancelada na agenda: a etiqueta só diz "Cancelado" quando o Google confirmou. */
const TAGS_CANCELADO: Record<GCalStatus, GcalRowTag> = {
  NONE: { label: 'Cancelado na agenda', color: 'default' },
  PENDING: { label: 'Cancelando…', color: 'processing' },
  PUBLISHED: { label: 'Cancelado na agenda', color: 'default' },
  ERROR: { label: 'Erro ao cancelar', color: 'error' },
};

export function gcalRowActions(
  row: Pick<Solicitacao, 'gcal_status' | 'external_event_id'> &
    Partial<Pick<Solicitacao, 'publicado_fora_do_sistema' | 'tipo_evento_de_formacao' | 'cancelado_na_agenda'>>,
  { ready }: { ready: boolean },
): GcalRowActionsResult {
  if (row.publicado_fora_do_sistema) {
    return { tag: TAG_FORA_DO_SISTEMA, actions: [], disabled: !ready };
  }
  if (row.cancelado_na_agenda) {
    const refazer = row.gcal_status === 'ERROR' && !!row.external_event_id;
    return { tag: TAGS_CANCELADO[row.gcal_status], actions: refazer ? ['cancelar'] : [], disabled: !ready };
  }
  const actions = actionsFor(row.gcal_status, !!row.external_event_id);
  // Cancelar só onde há Tirar (com o id de lá), como na Pré-agenda: sem id, um Cancelar que falhasse deixaria a
  // linha em ERROR sem id, que o servidor não deixa refazer.
  if (row.tipo_evento_de_formacao && actions.includes('remover')) actions.push('cancelar');
  return { tag: TAGS[row.gcal_status], actions, disabled: !ready };
}

/** Códigos do `motivo_nao_publicavel` do backend (services/solicitacao_publish.py). */
export type MotivoNaoPublicavel =
  | 'cancelado_na_agenda'
  | 'publicado_fora_do_sistema'
  | 'evento_passado'
  | 'ja_publicado'
  | 'nao_publicado'
  | 'sem_numero_da_formacao';

/** Por que a linha cancelada na agenda não se edita (o mesmo texto do 400 do servidor, CON-08). */
export const MSG_CANCELADO_NA_AGENDA = 'Este evento foi cancelado na agenda: não se edita nem se publica de novo.';

/** Motivo curto, para completar o nome acessível do botão ou da caixa de seleção. */
export const MOTIVO_NAO_PUBLICAVEL: Record<MotivoNaoPublicavel, string> = {
  cancelado_na_agenda: 'foi cancelado na agenda',
  publicado_fora_do_sistema: 'já está no Google Agenda pela planilha',
  evento_passado: 'o evento já terminou',
  ja_publicado: 'já publicado',
  nao_publicado: 'ainda não publicado',
  sem_numero_da_formacao: 'falta o Nº da formação',
};

/**
 * Espelho do `motivo_nao_publicavel` do backend: por que a linha não pode ser publicada
 * (`reenvio=false`) ou reaplicada/reenviada (`reenvio=true`), ou null se pode.
 * "Passado" compara instantes (o ISO traz o fuso), então vale em qualquer fuso do navegador.
 * O Nº da formação (CON-09) não é conferido aqui: a linha traz a resposta do servidor
 * (`falta_numero_da_formacao`); sem ela, o servidor recusa e diz o motivo.
 */
export function motivoNaoPublicavel(
  row: Pick<Solicitacao, 'gcal_status'> &
    Partial<
      Pick<Solicitacao, 'fim' | 'publicado_fora_do_sistema' | 'falta_numero_da_formacao' | 'cancelado_na_agenda'>
    >,
  { reenvio = false, agora = Date.now() }: { reenvio?: boolean; agora?: number } = {},
): MotivoNaoPublicavel | null {
  if (row.cancelado_na_agenda) return 'cancelado_na_agenda';
  if (row.publicado_fora_do_sistema) return 'publicado_fora_do_sistema';
  if (row.fim && Date.parse(row.fim) < agora) return 'evento_passado';
  if (reenvio) {
    if (row.gcal_status === 'NONE') return 'nao_publicado';
  } else if (row.gcal_status === 'PUBLISHED' || row.gcal_status === 'PENDING') {
    return 'ja_publicado';
  }
  return row.falta_numero_da_formacao ? 'sem_numero_da_formacao' : null;
}

/**
 * Evento que o sistema pôs (ou pode ter posto) no Google: publicado, com o id de lá, ou em ERROR
 * (a publicação que falhou pode ter criado o evento sem gravar o id). Mesmo critério do backend
 * (`esta_no_google`): excluir um desses o tira do Google também.
 */
export function estaNoGoogle(row: Pick<Solicitacao, 'gcal_status' | 'external_event_id'>): boolean {
  return row.gcal_status === 'PUBLISHED' || row.gcal_status === 'ERROR' || Boolean(row.external_event_id);
}

/**
 * Espelho do `excluir_marca_cancelado` do backend: o Excluir de um evento que está no Google marca o título
 * com "(CANCELADO) " em vez de tirá-lo de lá (evento de formação ou linha já cancelada na agenda).
 */
export function excluirMarcaCancelado(
  row: Partial<Pick<Solicitacao, 'tipo_evento_de_formacao' | 'cancelado_na_agenda'>>,
): boolean {
  return Boolean(row.cancelado_na_agenda || row.tipo_evento_de_formacao);
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
 * Meet só é citado quando existe. Evento de formação (CON-08, decisão do dono de 23/11) não sai do
 * Google: o título lá ganha "(CANCELADO) ". Em ERROR sem id ele pode nunca ter chegado lá, e o texto
 * não promete que está.
 */
export function confirmacaoDeExcluirNoGoogle(
  row: EventoDaExclusao &
    Pick<Solicitacao, 'gcal_status' | 'meet_link'> &
    Partial<Pick<Solicitacao, 'tipo_evento_de_formacao' | 'cancelado_na_agenda' | 'external_event_id'>>,
): { title: string; content: string } {
  if (excluirMarcaCancelado(row)) {
    const fica =
      row.gcal_status === 'ERROR' && !row.external_event_id
        ? 'e, se chegou ao Google Agenda, fica lá com (CANCELADO) no título'
        : 'e fica no Google Agenda com (CANCELADO) no título';
    return {
      title: 'Excluir evento?',
      content: `${resumoDoEvento(row)}. Ele sai do sistema ${fica}. Não dá para desfazer.`,
    };
  }
  const doGoogle = row.gcal_status === 'ERROR' ? 'do Google Agenda, se estiver lá' : 'do Google Agenda';
  const meet = row.meet_link ? ', junto com o link do Meet' : '';
  return {
    title: 'Excluir evento?',
    content: `${resumoDoEvento(row)}. Ele sai do sistema e ${doGoogle}${meet}. Não dá para desfazer.`,
  };
}
