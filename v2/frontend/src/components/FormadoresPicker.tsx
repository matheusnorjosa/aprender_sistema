/**
 * FormadoresPicker - Seleção de Formadores para Nova Solicitação.
 *
 * Wrapper fino de UsuarioPicker (implementação compartilhada): papéis 'Formador' e
 * 'Coordenador', Tag azul. Decisão do dono (05/10/2026): coordenador que atua no evento
 * entra na lista de formadores (a lista de acompanhantes saiu). Com `projetoId`, só pessoas da
 * gerência do projeto (PR 9, P9-5); o backend aplica a mesma regra.
 */

import { type JSX } from 'react';
import UsuarioPicker, { type UsuarioItem, type UsuarioPickerProps } from './UsuarioPicker';

/** Formador selecionado (mesmo shape de UsuarioItem). */
export type FormadorItem = UsuarioItem;

export type FormadoresPickerProps = Pick<UsuarioPickerProps, 'value' | 'onChange' | 'projetoId'>;

export default function FormadoresPicker(props: FormadoresPickerProps): JSX.Element {
  return (
    <UsuarioPicker {...props} role="Formador,Coordenador" tagColor="blue" ariaLabel="Formadores selecionados" />
  );
}
