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
 */
import type { GCalStatus, Solicitacao } from '../types';

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

export function gcalRowActions(
  row: Pick<Solicitacao, 'gcal_status' | 'external_event_id'>,
  { ready }: { ready: boolean },
): GcalRowActionsResult {
  return {
    tag: TAGS[row.gcal_status],
    actions: actionsFor(row.gcal_status, !!row.external_event_id),
    disabled: !ready,
  };
}
