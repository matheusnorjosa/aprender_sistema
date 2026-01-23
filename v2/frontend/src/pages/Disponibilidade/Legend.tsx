/**
 * Componente de Legenda com Design Visual.
 *
 * Exibe círculos coloridos para cada código de disponibilidade.
 * Baseado no design: paginadisponibilidade/screen.png
 */

import type { JSX } from 'react';
import { CODE_LABEL } from './codes';

/** Legend code type */
type LegendCode = 'T' | 'P' | 'D' | 'X' | 'E' | '2' | 'D1';

/** Legend map type */
type LegendMapType = Record<string, string>;

interface LegendProps {
  legend?: LegendMapType;
}

// Mapeamento de códigos para cores (círculos)
const CODE_COLOR: Record<LegendCode, string> = {
  T: '#9333ea',     // Bloqueio total - roxo (purple-600)
  P: '#06b6d4',     // Bloqueio parcial - ciano (cyan-500)
  D: '#eab308',     // Deslocamento - amarelo (yellow-500)
  X: '#ef4444',     // Conflito - vermelho (red-500)
  E: '#22c55e',     // Evento - verde (green-500)
  '2': '#16a34a',   // >=2 eventos - verde escuro (green-600)
  D1: '#3b82f6',    // Evento + deslocamento - azul (blue-500)
};

export default function Legend({ legend }: LegendProps): JSX.Element {
  // Usar legend do backend ou fallback local
  const map = legend ?? CODE_LABEL;

  // Filtrar apenas códigos que têm cor definida
  const entries = Object.entries(map).filter(([code]) => code in CODE_COLOR);

  return (
    <div className="bg-white rounded-lg shadow-sm p-4">
      <h3 className="font-bold mb-3 text-gray-900">Legenda</h3>
      <div className="flex flex-wrap gap-4">
        {entries.map(([code, label]) => (
          <div key={code} className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded-full flex-shrink-0"
              style={{ backgroundColor: CODE_COLOR[code as LegendCode] }}
            ></div>
            <span className="text-sm text-gray-700 whitespace-nowrap">
              <span className="font-semibold">{code}</span> - {label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
