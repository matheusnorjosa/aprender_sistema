/**
 * FormadoresPicker - Seleção de Formadores para Nova Solicitação.
 *
 * Wrapper fino de UsuarioPicker (implementação compartilhada): papéis 'Formador',
 * 'Coordenador' e 'Gerente', Tag azul. Coordenador ou gerente que atua no evento entra aqui (gerente:
 * decisão do dono, 11/11/2026); os coordenadores
 * do evento ficam na caixa "Coordenador(es)" (CoordenadoresPicker, 03/11/2026). Com `projetoId`, só
 * pessoas da gerência do projeto (PR 9, P9-5); o backend aplica a mesma regra.
 */

import { type JSX } from 'react';
import UsuarioPicker, { type UsuarioItem, type UsuarioPickerProps } from './UsuarioPicker';

/** Formador selecionado (mesmo shape de UsuarioItem). */
export type FormadorItem = UsuarioItem;

export type FormadoresPickerProps = Pick<
  UsuarioPickerProps,
  'value' | 'onChange' | 'projetoId' | 'id' | 'aria-describedby' | 'aria-invalid'
>;

export default function FormadoresPicker(props: FormadoresPickerProps): JSX.Element {
  return (
    <UsuarioPicker
      {...props}
      role="Formador,Coordenador,Gerente"
      tagColor="blue"
      ariaLabel="Formadores selecionados"
      oQueCarrega="os formadores"
      daLista="dos formadores"
    />
  );
}
