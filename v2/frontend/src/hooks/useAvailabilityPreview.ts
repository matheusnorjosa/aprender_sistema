/**
 * useAvailabilityPreview — aviso antecipado de conflito de disponibilidade (#1452).
 *
 * Checa, enquanto o coordenador monta a solicitação, se algum participante
 * (criador + formadores + coordenadores) já está alocado no intervalo escolhido.
 * O enforcement real é do backend (bloqueio duro no submit); este hook é a UX que
 * antecipa o "não é possível criar o evento" e permite bloquear o botão com honestidade.
 *
 * Correção central — status derivado DURANTE o render, não em effect:
 * o resultado guardado vale para uma `key` (intervalo + participantes). Se a `key` atual
 * difere da guardada, o status é 'checking' na hora, sem pintar um veredito velho contra
 * input novo, e sem precisar filtrar o resultado anterior quando um participante é removido.
 */

import { useEffect, useRef, useState } from 'react';

import { checkAvailabilityMany } from '../api/availability';
import { TIMING } from '../constants';
import logger from '../utils/logger';
import type { BlockedParticipant, ConflictDetail, ID } from '../types';

export interface PreviewParticipant {
  id: ID;
  nome: string;
  /** true para o criador da solicitação (não pode ser removido para resolver o conflito). */
  criador: boolean;
}

export interface AvailabilityPreviewInput {
  inicio: string | null;
  fim: string | null;
  municipioId: ID | null;
  participantes: PreviewParticipant[];
  /** Desliga a checagem (ex.: enquanto não se está no passo de participantes). */
  enabled?: boolean;
}

export type AvailabilityPreview =
  | { status: 'idle' }
  | { status: 'checking' }
  | { status: 'ok' }
  | { status: 'conflito'; bloqueados: BlockedParticipant[] }
  | { status: 'indisponivel'; motivo: 'throttled' | 'erro' };

interface StoredResult {
  key: string;
  preview: AvailabilityPreview;
}

/**
 * Monta a `key` estável da checagem. `null` quando não há o que checar
 * (intervalo/município incompletos ou nenhum participante além do criador).
 * Ordenar os ids garante que [1,2] e [2,1] não refaçam a checagem.
 */
function buildKey(input: AvailabilityPreviewInput): string | null {
  if (input.enabled === false) return null;
  if (!input.inicio || !input.fim || input.municipioId == null) return null;

  const temParticipante = input.participantes.some((p) => !p.criador);
  if (!temParticipante) return null;

  const ids = Array.from(new Set(input.participantes.map((p) => p.id))).sort((a, b) => Number(a) - Number(b));
  return `${input.inicio}|${input.fim}|${input.municipioId}|${ids.join(',')}`;
}

export function useAvailabilityPreview(input: AvailabilityPreviewInput): AvailabilityPreview {
  const key = buildKey(input);
  const [stored, setStored] = useState<StoredResult | null>(null);

  // Guarda de sequência: descarta resposta de uma checagem que não é mais a atual.
  const seqRef = useRef(0);

  // Nomes por id para preencher `usuario_nome` (o check-many devolve só usuario_id).
  const nomePorId = new Map<ID, PreviewParticipant>(input.participantes.map((p) => [p.id, p]));

  useEffect(() => {
    if (key === null) return;

    const seq = ++seqRef.current;
    const controller = new AbortController();
    const usuariosIds = Array.from(new Set(input.participantes.map((p) => p.id)));

    const timer = setTimeout(() => {
      void checkAvailabilityMany(
        {
          usuarios_ids: usuariosIds,
          inicio: input.inicio as string,
          fim: input.fim as string,
          municipio_id: input.municipioId as ID,
        },
        { signal: controller.signal }
      )
        .then((resp) => {
          if (seq !== seqRef.current) return; // chegou obsoleta
          if (resp.ok) {
            setStored({ key, preview: { status: 'ok' } });
            return;
          }
          const bloqueados: BlockedParticipant[] = resp.results
            .filter((r) => !r.ok)
            .map((r) => {
              const p = nomePorId.get(r.usuario_id);
              return {
                usuario_id: r.usuario_id,
                usuario_nome: p?.nome ?? `Participante #${r.usuario_id}`,
                conflicts: r.conflicts as ConflictDetail[],
              };
            });
          setStored({ key, preview: { status: 'conflito', bloqueados } });
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return; // cancelamento não é falha
          if (seq !== seqRef.current) return;
          const httpStatus = (err as { status?: number })?.status;
          const motivo = httpStatus === 429 ? 'throttled' : 'erro';
          // Fail-open: o backend é o gate real; não travar o usuário por uma
          // checagem que falhou. O status 'indisponivel' NÃO bloqueia o botão.
          logger.warn('Falha ao pré-checar disponibilidade (fail-open):', err);
          setStored({ key, preview: { status: 'indisponivel', motivo } });
        });
    }, TIMING.DEBOUNCE_AVAILABILITY_CHECK_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // nomePorId deriva de participantes; a key já cobre a identidade dos inputs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  // Derivação durante o render: só confia no resultado guardado se for da key atual.
  if (key === null) return { status: 'idle' };
  if (stored && stored.key === key) return stored.preview;
  return { status: 'checking' };
}
