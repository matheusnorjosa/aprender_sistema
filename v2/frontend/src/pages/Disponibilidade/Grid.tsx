/**
 * Componente de Grade Mensal - Layout Horizontal (como planilha).
 *
 * Layout:
 * - Header: dias do mês (1, 2, 3...31)
 * - Cada linha: uma pessoa
 * - Primeira coluna: nome da pessoa
 * - Células: barras coloridas mostrando eventos/bloqueios
 */

import type { JSX } from 'react';
import { CODE_LABEL } from './codes';
import type { ID } from '../../types';

/** Code type for grid cells */
type CellCode = 'E' | '2' | 'P' | 'T' | 'X' | 'D' | 'D1' | '';

/** Person type in the grid */
export interface GridPersonType {
  id: ID;
  name: string;
  ch_month?: number;
}

/** Selected cell type */
export interface SelectedCellType {
  rowIdx: number;
  dayIdx: number;
}

/** Details index type */
export type DetailsIndexType = Record<string, unknown[]>;

interface GridProps {
  year: number;
  month: number;
  title: string;
  days: number[];
  people: GridPersonType[];
  cells: CellCode[][];
  detailsIndex: DetailsIndexType;
  onSelect: (rowIdx: number, dayIdx: number) => void;
  selected: SelectedCellType | null;
}

/**
 * Mapeamento de códigos para cores (barras horizontais).
 */
const CODE_COLOR: Record<CellCode, string> = {
  E: 'bg-green-500',      // 1 evento - verde
  '2': 'bg-green-600',    // >=2 eventos - verde escuro
  P: 'bg-cyan-500',       // Bloqueio parcial - ciano
  T: 'bg-purple-600',     // Bloqueio total - roxo
  X: 'bg-red-500',        // Evento + bloqueio - vermelho (conflito)
  D: 'bg-yellow-500',     // Deslocamento - amarelo
  D1: 'bg-blue-500',      // Evento + deslocamento - azul
  '': '',                  // Vazio
};

/**
 * Verifica se um dia é hoje.
 */
const isToday = (year: number, month: number, day: number): boolean => {
  const t = new Date();
  return (
    t.getFullYear() === year &&
    t.getMonth() + 1 === month &&
    t.getDate() === day
  );
};

export default function Grid({
  year,
  month,
  title,
  days,
  people,
  cells,
  detailsIndex,
  onSelect,
  selected,
}: GridProps): JSX.Element {
  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      {/* Título da grade */}
      <div className="px-4 py-3 border-b bg-gray-50">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      </div>

      {/* Tabela horizontal com scroll */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b">
              {/* Coluna de nomes */}
              <th className="sticky left-0 z-10 bg-gray-50 px-3 py-2 text-left text-xs font-semibold text-gray-900 border-r min-w-[180px] max-w-[200px]">
                Nome
              </th>
              {/* Colunas dos dias */}
              {days.map((day) => {
                const today = isToday(year, month, day);
                return (
                  <th
                    key={day}
                    className={`px-1.5 py-2 text-center text-xs font-semibold w-12 ${
                      today ? 'bg-blue-100 text-blue-700' : 'text-gray-700'
                    }`}
                  >
                    {day}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {people.map((person, rowIdx) => (
              <tr key={person.id} className="border-b hover:bg-gray-50">
                {/* Nome da pessoa */}
                <td className="sticky left-0 z-10 bg-white px-3 py-1.5 text-xs font-medium text-gray-900 border-r whitespace-nowrap">
                  <div className="flex flex-col">
                    <span className="truncate max-w-[170px]" title={person.name}>{person.name}</span>
                    {person.ch_month !== undefined && (
                      <span className="text-[10px] text-gray-500">
                        {person.ch_month}h
                      </span>
                    )}
                  </div>
                </td>
                {/* Células dos dias */}
                {days.map((day, dayIdx) => {
                  const code = cells[rowIdx][dayIdx];
                  const key = `${rowIdx}:${dayIdx}`;
                  const hasDetails = (detailsIndex[key] as unknown[] | undefined)?.length ?? 0 > 0;
                  const sel = selected?.rowIdx === rowIdx && selected?.dayIdx === dayIdx;
                  const today = isToday(year, month, day);
                  const conflict = code === 'X';

                  // Classes da célula
                  let cellClass = 'border-l border-gray-100';
                  if (today) cellClass += ' bg-blue-50';
                  if (sel) cellClass += ' bg-blue-100';
                  if (conflict) cellClass += ' bg-red-50';

                  return (
                    <td
                      key={dayIdx}
                      className={`px-1 py-1.5 text-center relative ${cellClass}`}
                    >
                      {code && (
                        <button
                          type="button"
                          title={CODE_LABEL[code as keyof typeof CODE_LABEL] || code}
                          onClick={() => hasDetails && onSelect(rowIdx, dayIdx)}
                          className={`
                            w-10 h-7 rounded flex items-center justify-center
                            transition-all hover:scale-110
                            ${CODE_COLOR[code]}
                            ${hasDetails ? 'cursor-pointer' : 'cursor-default opacity-70'}
                          `}
                        >
                          <span className="text-white text-xs font-bold">
                            {code}
                          </span>
                        </button>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
