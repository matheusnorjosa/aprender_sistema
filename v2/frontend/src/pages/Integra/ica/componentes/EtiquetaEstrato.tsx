/**
 * Etiqueta do estrato: a cor sempre com o número e o nome ("170 · Sobrecarga").
 * Quem está sem municípios ganha "0 · Sem municípios", em cinza (fora da média da equipe).
 */
import type { JSX } from 'react';

import { nomeDoEstrato, type Estrato } from '../calculo';
import { COR_ESTRATO } from './estilos';

interface EtiquetaEstratoProps {
  estrato: Estrato;
  /** ICA exibido (inteiro). Sem ele, só o nome do estrato. */
  ica?: number;
  semMunicipios?: boolean;
}

const SEM_MUNICIPIOS = { fundo: '#F0F0F0', texto: '#3D3D3D' } as const;

// Função pura usada junto com o componente pelas telas (o Fast Refresh só recarrega a página inteira).
// eslint-disable-next-line react-refresh/only-export-components
export function textoDoEstrato(estrato: Estrato, ica?: number, semMunicipios = false): string {
  const nome = semMunicipios ? 'Sem municípios' : nomeDoEstrato(estrato);
  return ica === undefined ? nome : `${ica} · ${nome}`;
}

export function EtiquetaEstrato({ estrato, ica, semMunicipios = false }: EtiquetaEstratoProps): JSX.Element {
  const cor = semMunicipios ? SEM_MUNICIPIOS : COR_ESTRATO[estrato];
  return (
    <span
      className="inline-block max-w-full rounded px-2 py-0.5 text-sm font-semibold"
      style={{ background: cor.fundo, color: cor.texto }}
    >
      {textoDoEstrato(estrato, ica, semMunicipios)}
    </span>
  );
}
