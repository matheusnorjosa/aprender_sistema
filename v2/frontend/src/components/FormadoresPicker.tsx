/**
 * FormadoresPicker - Seleção de Formadores para Nova Solicitação.
 *
 * Wrapper fino de UsuarioPicker (implementação compartilhada): papel 'Formador',
 * Tag azul.
 */

import { type JSX } from 'react';
import UsuarioPicker, { type UsuarioItem, type UsuarioPickerProps } from './UsuarioPicker';

/** Formador selecionado (mesmo shape de UsuarioItem). */
export type FormadorItem = UsuarioItem;

export type FormadoresPickerProps = Pick<UsuarioPickerProps, 'value' | 'onChange'>;

export default function FormadoresPicker(props: FormadoresPickerProps): JSX.Element {
  return (
    <UsuarioPicker {...props} role="Formador" tagColor="blue" ariaLabel="Formadores selecionados" />
  );
}
