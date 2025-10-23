/**
 * Barra de filtros compartilhados.
 *
 * Filtros: ano, mês, setor, busca (q).
 * Sem "role" (controlado pela página principal).
 */

export default function FiltersBar({ year, month, sector, q, onChange }) {
  /**
   * Incrementa/decrementa mês.
   *
   * @param {number} delta - Delta de meses (-1 ou +1)
   */
  const bump = (delta) => {
    const dt = new Date(year, month - 1, 1);
    dt.setMonth(dt.getMonth() + delta);
    onChange({ year: dt.getFullYear(), month: dt.getMonth() + 1 });
  };

  return (
    <div className="flex flex-wrap items-end gap-3 p-4 bg-white rounded-lg shadow-sm">
      {/* Navegação mês/ano */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => bump(-1)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
        >
          ←
        </button>
        <div className="px-3 py-2 font-semibold text-gray-900">
          {String(month).padStart(2, '0')}/{year}
        </div>
        <button
          type="button"
          onClick={() => bump(1)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
        >
          →
        </button>
      </div>

      {/* Filtro de setor */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Setor
        </label>
        <input
          type="text"
          value={sector}
          onChange={(e) => onChange({ sector: e.target.value })}
          placeholder="Filtrar por setor"
          className="w-52 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Filtro de busca */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Buscar
        </label>
        <input
          type="text"
          value={q}
          onChange={(e) => onChange({ q: e.target.value })}
          placeholder="Buscar nome/email"
          className="w-56 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    </div>
  );
}
