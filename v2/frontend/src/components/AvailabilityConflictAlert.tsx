/**
 * AvailabilityConflictAlert — mostra os participantes bloqueados e o motivo de cada um (#1452).
 *
 * Apresentacional puro (sem fetch). Serve três pontos: o aviso antecipado no wizard
 * (a partir de `useAvailabilityPreview`), o erro 400 do submit (`blocked_participants`
 * do backend) e, pela `ListaDeBloqueados`, o erro ao aprovar na tela de Aprovações. O texto
 * do conflito (`title`/`detail`) vem verbatim do backend — o `code` só define a cor da tag,
 * para não criar uma segunda fonte de verdade das regras RD.
 */

import { JSX } from 'react';
import Alert from 'antd/es/alert';
import Tag from 'antd/es/tag';

import type { BlockedParticipant, ConflictDetail } from '../types';
import type { AvisoDeAgenda } from '../types/availability';

/** Cor da tag por código de conflito (RD-01..08). Só estética. */
const COR_POR_CODIGO: Record<ConflictDetail['code'], string> = {
  X: 'red', // sobreposição de evento
  T: 'volcano', // bloqueio total
  P: 'orange', // bloqueio parcial
  D: 'gold', // deslocamento
  M: 'geekblue', // limite diário: só aviso, nunca vem como bloqueio (ver AvisosDeAgenda)
};

const ORIENTACAO_PADRAO =
  'Remova o participante em conflito ou volte ao passo anterior e escolha outra data/horário.';

export interface ListaDeBloqueadosProps {
  bloqueados: BlockedParticipant[];
  /** O que a pessoa pode fazer agora. O padrão é o do wizard de criação. */
  orientacao?: string;
}

/**
 * Quem está bloqueado e por quê: a tag traz o motivo por extenso (`title`) e, ao lado, o
 * detalhe quando o backend manda. Sem moldura: quem usa decide o contêiner (Alert, Modal).
 */
export function ListaDeBloqueados({
  bloqueados,
  orientacao = ORIENTACAO_PADRAO,
}: ListaDeBloqueadosProps): JSX.Element {
  return (
    <ul className="list-none pl-0 m-0">
      {bloqueados.map((p) => (
        <li key={p.usuario_id} className="mb-2">
          <strong>{p.usuario_nome}</strong>
          <div className="mt-1">
            {p.conflicts.map((c, i) => (
              <div key={`${p.usuario_id}-${i}`} className="text-sm">
                <Tag color={COR_POR_CODIGO[c.code] ?? 'default'}>{c.title || c.code}</Tag>
                {c.detail ? <span>{c.detail}</span> : null}
              </div>
            ))}
          </div>
        </li>
      ))}
      <li className="text-sm text-gray-500">{orientacao}</li>
    </ul>
  );
}

export interface AvailabilityConflictAlertProps {
  bloqueados: BlockedParticipant[];
  /** id do bloco, para `aria-describedby` do botão desabilitado. */
  id?: string;
}

export default function AvailabilityConflictAlert({
  bloqueados,
  id,
}: AvailabilityConflictAlertProps): JSX.Element | null {
  if (bloqueados.length === 0) return null;

  return (
    <Alert
      {...(id !== undefined && { id })}
      type="error"
      showIcon
      role="alert"
      className="mb-4"
      message="Não é possível criar o evento"
      description={<ListaDeBloqueados bloqueados={bloqueados} />}
    />
  );
}

export interface AvisosDeAgendaProps {
  avisos: AvisoDeAgenda[];
}

/**
 * Aviso que NÃO impede o evento (limite diário, RD-05 — decisão do dono em 02/10/2026).
 *
 * Diferente do bloqueio em tudo o que a pessoa percebe: é informação (azul, `role="status"`,
 * lido sem interromper), diz no título que não impede e não manda remover ninguém. O texto
 * de cada aviso (`title`/`detail`) vem pronto do backend.
 */
export function AvisosDeAgenda({ avisos }: AvisosDeAgendaProps): JSX.Element | null {
  if (avisos.length === 0) return null;

  return (
    <Alert
      type="info"
      showIcon
      role="status"
      className="mb-4"
      message="Aviso de agenda: isso não impede o evento"
      description={
        <ul className="list-none pl-0 m-0">
          {avisos.map((p) => (
            <li key={p.usuario_id} className="mb-2">
              <strong>{p.usuario_nome}</strong>
              {p.warnings.map((w, i) => (
                <div key={`${p.usuario_id}-${i}`} className="text-sm">
                  {w.title}
                  {w.detail ? `. ${w.detail}` : null}
                </div>
              ))}
            </li>
          ))}
        </ul>
      }
    />
  );
}
