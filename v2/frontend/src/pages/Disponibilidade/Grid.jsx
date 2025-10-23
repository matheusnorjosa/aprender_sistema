/**
 * Componente de Grade Mensal.
 *
 * Renderiza matriz 2D com códigos de disponibilidade.
 * Usa chave "row:col" para details_index.
 * Destaques: fins de semana, hoje, células selecionadas.
 */

import { CODE_LABEL, CODE_CLASS } from './codes';

/**
 * Verifica se um dia é fim de semana.
 */
const isWeekend = (year, month, day) => {
  return [0, 6].includes(new Date(year, month - 1, day).getDay());
};

/**
 * Verifica se um dia é hoje.
 */
const isToday = (year, month, day) => {
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
}) {
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header fixo */}
      <div
        className="grid sticky top-0 z-10"
        style={{
          gridTemplateColumns: `240px repeat(${days.length}, 28px)`,
        }}
      >
        {/* Coluna de título */}
        <div className="px-2 py-2 font-semibold border-r bg-gray-50">
          {title}
        </div>

        {/* Cabeçalhos de dias */}
        {days.map((d) => (
          <div
            key={d}
            className={`text-center text-[10px] py-1 border-r ${
              isWeekend(year, month, d)
                ? 'bg-gray-100 text-gray-600'
                : 'bg-gray-50'
            } ${
              isToday(year, month, d)
                ? 'ring-2 ring-blue-400 ring-offset-1'
                : ''
            }`}
          >
            {d}
          </div>
        ))}
      </div>

      {/* Linhas de pessoas */}
      {people.map((person, rowIdx) => (
        <div
          key={person.id}
          className="grid border-b hover:bg-gray-50"
          style={{
            gridTemplateColumns: `240px repeat(${days.length}, 28px)`,
          }}
        >
          {/* Coluna de pessoa */}
          <div className="px-2 py-2 text-sm border-r flex flex-col justify-center">
            <div className="font-medium text-gray-900">{person.name}</div>
            {person.ch_month !== undefined && (
              <div className="text-[10px] text-gray-500">
                CH mês: {person.ch_month}h
              </div>
            )}
          </div>

          {/* Células de dias */}
          {days.map((day, dayIdx) => {
            const code = cells[rowIdx][dayIdx];
            const key = `${rowIdx}:${dayIdx}`;
            const hasDetails = detailsIndex[key]?.length > 0;
            const sel =
              selected?.rowIdx === rowIdx && selected?.dayIdx === dayIdx;

            return (
              <button
                key={dayIdx}
                type="button"
                title={code ? CODE_LABEL[code] || code : ''}
                onClick={() => onSelect(rowIdx, dayIdx)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && hasDetails) {
                    onSelect(rowIdx, dayIdx);
                  }
                }}
                className={`text-[11px] border-t border-r flex items-center justify-center ${
                  CODE_CLASS[code] || CODE_CLASS['']
                } ${sel ? 'ring-2 ring-blue-500 ring-offset-1' : ''}`}
                aria-label={`${code || ''} dia ${days[dayIdx]}`}
              >
                {code}
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
