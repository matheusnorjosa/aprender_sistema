/**
 * Drawer de Detalhes de Eventos.
 *
 * Exibe métricas (ch_month, ch_year, position_month) e detalhes dos eventos.
 * Usa campos "inicio" e "fim" do backend.
 */

import type { JSX } from 'react';
import type { ID } from '../../types';

/** Person record from the monthly grid */
export interface PersonType {
  id: ID;
  name: string;
  email?: string;
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
        <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">
            Detalhes: {person.name} - Dia {day}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 text-sm text-gray-600 hover:text-gray-900 border rounded"
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
              <span className="text-gray-900">{person.name}</span>
            </div>
            {person.email && (
              <div>
                <span className="font-medium text-gray-700">Email: </span>
                <span className="text-gray-900">{person.email}</span>
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="p-2 border text-left font-medium text-gray-700">
                      Município
                    </th>
                    <th className="p-2 border text-left font-medium text-gray-700">
                      Tipo
                    </th>
                    <th className="p-2 border text-left font-medium text-gray-700">
                      Data
                    </th>
                    <th className="p-2 border text-left font-medium text-gray-700">
                      Início
                    </th>
                    <th className="p-2 border text-left font-medium text-gray-700">
                      Fim
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {details.map((d, idx) => (
                    <tr key={d.id || idx} className="hover:bg-gray-50">
                      <td className="p-2 border">{d.municipio ?? ''}</td>
                      <td className="p-2 border">{d.tipo ?? ''}</td>
                      <td className="p-2 border">{d.data ?? ''}</td>
                      <td className="p-2 border">{d.inicio ?? ''}</td>
                      <td className="p-2 border">{d.fim ?? ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
