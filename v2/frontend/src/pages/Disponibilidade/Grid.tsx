/**
 * Componente de Grade Mensal - Layout Horizontal (como planilha).
 *
 * Layout:
 * - Header: dias do mês (1, 2, 3...31)
 * - Cada linha: uma pessoa
 * - Primeira coluna: nome da pessoa
 * - Células: barras coloridas mostrando eventos/bloqueios
 *
 * Sem rolagem horizontal (C4): só os dias de `diasVisiveis` (a semana abaixo de 1280 px, o mês
 * inteiro a partir dele) e `table-fixed`, com a coluna do dia sem largura fixa.
 *
 * Grade enxuta (27/11/2026): sem título (a página já tem o h2), quadradinho baixo, horas só
 * quando passam de zero, todo código abre o dia e o nome abre o mês da pessoa.
 */

import type { JSX } from 'react';
import dayjs from 'dayjs';
import { FORTALEZA_TZ } from '../../utils/datetime';
import { CODE_LABEL } from './codes';
import { formatarHoras } from './horas';
import type { ID } from '../../types';

/** Code type for grid cells */
type CellCode = 'E' | '2' | 'P' | 'T' | 'X' | 'D' | 'D1' | '';

/** Person type in the grid */
export interface GridPersonType {
  id: ID;
  name: string;
  ch_month?: number;
}

/** Selected cell type (`dayIdx` nulo: o mês da pessoa, pelo nome) */
export interface SelectedCellType {
  rowIdx: number;
  dayIdx: number | null;
}

interface GridProps {
  year: number;
  month: number;
  days: number[];
  /** Índices de `days` mostrados, na ordem. A chave da célula continua sendo o índice no mês. */
  diasVisiveis: readonly number[];
  people: GridPersonType[];
  cells: CellCode[][];
  onSelect: (rowIdx: number, dayIdx: number) => void;
  /** Clique no nome: o mês da pessoa. */
  onSelectPessoa: (rowIdx: number) => void;
  selected: SelectedCellType | null;
}

/**
 * Mapeamento de códigos para cores (barras horizontais).
 */
const FOCO = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-blue-600';

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
  // Hoje em Fortaleza, o mesmo "hoje" da semana inicial (semanas.ts) e do mês inicial.
  const t = dayjs().tz(FORTALEZA_TZ);
  return (
    t.year() === year &&
    t.month() + 1 === month &&
    t.date() === day
  );
};

/** Primeiro e último nome, como a planilha ("Adriana Pinheiro"). */
const nomeCurto = (nome: string): string => {
  const partes = nome.trim().split(/\s+/);
  return partes.length > 2 ? `${partes[0]} ${partes[partes.length - 1]}` : nome.trim();
};

export default function Grid({
  year,
  month,
  days,
  diasVisiveis,
  people,
  cells,
  onSelect,
  onSelectPessoa,
  selected,
}: GridProps): JSX.Element {
  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      {/* Tabela sem rolagem: colunas dos dias repartem o que sobra do Nome */}
      <div>
        <table className="w-full table-fixed border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b">
              {/* Coluna de nomes */}
              <th className="bg-gray-50 px-1.5 py-0.5 text-left text-[11px] font-semibold text-gray-900 border-r w-24 sm:w-40">
                Nome
              </th>
              {/* Colunas dos dias */}
              {diasVisiveis.map((dayIdx) => {
                const day = days[dayIdx] ?? 0;
                const today = isToday(year, month, day);
                return (
                  <th
                    key={dayIdx}
                    className={`px-0 py-0.5 text-center text-[11px] font-semibold ${
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
                <td className="bg-white px-1.5 py-0 text-[11px] font-medium text-gray-900 border-r">
                  {/* Como a planilha: nome curto numa linha e as horas ao lado; o nome inteiro fica no título e na gaveta. */}
                  <div className="flex items-baseline gap-1 min-w-0">
                    <button
                      type="button"
                      title={person.name}
                      aria-label={`Ver o mês de ${person.name}`}
                      onClick={() => onSelectPessoa(rowIdx)}
                      className={`min-w-0 truncate text-left hover:underline rounded ${FOCO}`}
                    >
                      {nomeCurto(person.name)}
                    </button>
                    {(person.ch_month ?? 0) > 0 && (
                      <span className="ml-auto shrink-0 text-[10px] text-gray-500">
                        {formatarHoras(person.ch_month ?? 0)}
                      </span>
                    )}
                  </div>
                </td>
                {/* Células dos dias */}
                {diasVisiveis.map((dayIdx) => {
                  const day = days[dayIdx] ?? 0;
                  const code = cells[rowIdx]?.[dayIdx];
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
                      className={`px-px py-px text-center relative ${cellClass}`}
                    >
                      {code && (
                        <button
                          type="button"
                          title={CODE_LABEL[code as keyof typeof CODE_LABEL] || code}
                          aria-label={`${code}, ${(CODE_LABEL[code as keyof typeof CODE_LABEL] || code).toLowerCase()}: ${person.name}, dia ${day}`}
                          onClick={() => onSelect(rowIdx, dayIdx)}
                          className={`
                            w-full max-w-10 mx-auto min-w-0 h-4 rounded-sm flex items-center justify-center
                            hover:opacity-80 cursor-pointer ${FOCO}
                            ${CODE_COLOR[code]}
                          `}
                        >
                          <span className="text-white text-[10px] leading-none font-bold">
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
