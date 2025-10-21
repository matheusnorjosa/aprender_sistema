/**
 * Componente de Legenda.
 *
 * Consome legend do backend com fallback para CODE_LABEL.
 * Usa CODE_CLASS para estilização.
 */

import { CODE_LABEL, CODE_CLASS } from './codes';

export default function Legend({ legend }) {
  // Usar legend do backend ou fallback local
  const map = legend ?? CODE_LABEL;

  return (
    <div className="flex flex-wrap gap-2 bg-white/80 rounded p-2 shadow-sm">
      {Object.entries(map).map(([k, v]) => {
        // Pular código vazio
        if (!k) return null;

        return (
          <span
            key={k}
            className={`inline-flex items-center gap-1 px-2 py-1 rounded ${CODE_CLASS[k] || CODE_CLASS['']}`}
          >
            <b>{k}</b>
            <span className="text-sm">{v}</span>
          </span>
        );
      })}
    </div>
  );
}
