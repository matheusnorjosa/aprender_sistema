/**
 * Drawer de Detalhes de Eventos.
 *
 * Exibe métricas (ch_month, ch_year, position_month) e detalhes dos eventos.
 * Usa campos "inicio" e "fim" do backend.
 *
 * Sem rolagem horizontal (C4): cada evento é um cartão (lista), não uma tabela de 5 colunas, e
 * texto longo quebra linha. O painel rola na vertical, e por isso qualquer excesso na
 * horizontal viraria rolagem interna.
 */

import type { JSX } from 'react';
import dayjs from 'dayjs';
import type { ID } from '../../types';

/** Person record from the monthly grid */
export interface PersonType {
  id: ID;
  name: string;
  email?: string | null;
  ch_month?: number;
  ch_year?: number;
  position_month?: number | string;
}

/** Event detail record */
export interface EventDetailType {
  id?: ID;
  municipio?: string;
  tipo?: string;
  data?: string;
  inicio?: string;
  fim?: string;
}

interface DetailsDrawerProps {
  open: boolean;
  onClose: () => void;
  person: PersonType | null;
  day: number | null;
  details: EventDetailType[];
}

export default function DetailsDrawer({ open, onClose, person, day, details }: DetailsDrawerProps): JSX.Element | null {
  if (!open || !person) return null;

  return (
    <>
      {/* Overlay */}
      <div
        role="button"
        tabIndex={0}
        aria-label="Fechar detalhes"
        className="fixed inset-0 bg-black/30 z-40"
        onClick={onClose}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClose();
          }
        }}
      ></div>

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-white shadow-2xl z-50 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between gap-3">
          <h2 className="min-w-0 break-words text-xl font-bold text-gray-900">
            Detalhes: {person.name} - Dia {day}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 px-3 py-1 text-sm text-gray-600 hover:text-gray-900 border rounded"
          >
            Fechar
          </button>
        </div>

        {/* Métricas */}
        <div className="p-4 border-b bg-gray-50">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {person.ch_month ?? 0}h
              </div>
              <div className="text-xs text-gray-600">CH Mês</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {person.ch_year ?? 0}h
              </div>
              <div className="text-xs text-gray-600">CH Ano</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {person.position_month ?? '-'}
              </div>
              <div className="text-xs text-gray-600">Ranking Mês</div>
            </div>
          </div>
        </div>

        {/* Informações da pessoa */}
        <div className="p-4 border-b">
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-gray-700">Nome: </span>
              <span className="text-gray-900 break-words">{person.name}</span>
            </div>
            {person.email && (
              <div>
                <span className="font-medium text-gray-700">Email: </span>
                <span className="text-gray-900 [overflow-wrap:anywhere]">{person.email}</span>
              </div>
            )}
          </div>
        </div>

        {/* Lista de eventos */}
        <div className="p-4">
          <h3 className="font-semibold text-gray-900 mb-3">
            Eventos do Dia {day}
          </h3>

          {details.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">
              Nenhum evento encontrado para este dia.
            </p>
          ) : (
            <ul className="space-y-3">
              {details.map((d, idx) => (
                <li key={d.id || idx} className="border rounded p-3">
                  <p className="font-medium text-gray-900 break-words">{d.municipio ?? ''}</p>
                  <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                    <div className="min-w-0">
                      <dt className="text-xs text-gray-600">Tipo</dt>
                      <dd className="text-gray-900 break-words">{d.tipo ?? ''}</dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-xs text-gray-600">Data</dt>
                      {/* O servidor já manda o dia de Fortaleza (YYYY-MM-DD): só troca o formato. */}
                      <dd className="text-gray-900">{d.data ? dayjs(d.data).format('DD/MM/YYYY') : ''}</dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-xs text-gray-600">Início</dt>
                      <dd className="text-gray-900">{d.inicio ?? ''}</dd>
                    </div>
                    <div className="min-w-0">
                      <dt className="text-xs text-gray-600">Fim</dt>
                      <dd className="text-gray-900">{d.fim ?? ''}</dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  );
}
