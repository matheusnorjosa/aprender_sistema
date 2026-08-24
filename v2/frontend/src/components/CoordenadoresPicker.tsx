/**
 * CoordenadoresPicker - Seleção de Coordenadores Acompanhantes.
 *
 * Wrapper fino de UsuarioPicker (implementação compartilhada): papel
 * 'Coordenador', Tag verde.
 */

import { type JSX } from 'react';
import UsuarioPicker, { type UsuarioItem, type UsuarioPickerProps } from './UsuarioPicker';

/** Coordenador selecionado (mesmo shape de UsuarioItem). */
export type CoordenadorItem = UsuarioItem;

export type CoordenadoresPickerProps = Pick<UsuarioPickerProps, 'value' | 'onChange'>;

export default function CoordenadoresPicker(props: CoordenadoresPickerProps): JSX.Element {
  return (
    <UsuarioPicker {...props} role="Coordenador" tagColor="green" ariaLabel="Coordenadores selecionados" />
  );
}
