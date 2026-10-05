/**
 * FormadoresPicker - Seleção de Formadores para Nova Solicitação.
 *
 * Wrapper fino de UsuarioPicker (implementação compartilhada): papéis 'Formador' e
 * 'Coordenador', Tag azul. Decisão do dono (05/10/2026): coordenador que atua no evento
 * entra na lista de formadores (a lista de acompanhantes saiu). O backend escopa por setor.
 */

import { type JSX } from 'react';
import UsuarioPicker, { type UsuarioItem, type UsuarioPickerProps } from './UsuarioPicker';

/** Formador selecionado (mesmo shape de UsuarioItem). */
export type FormadorItem = UsuarioItem;

export type FormadoresPickerProps = Pick<UsuarioPickerProps, 'value' | 'onChange'>;

export default function FormadoresPicker(props: FormadoresPickerProps): JSX.Element {
  return (
    <UsuarioPicker {...props} role="Formador,Coordenador" tagColor="blue" ariaLabel="Formadores selecionados" />
  );
}
