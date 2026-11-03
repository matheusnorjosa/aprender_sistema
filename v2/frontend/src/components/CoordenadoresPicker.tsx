/**
 * CoordenadoresPicker - a caixa "Coordenador(es)" de cada horário da Nova Solicitação.
 *
 * Wrapper fino de UsuarioPicker: papel 'Coordenador', Tag roxa. Decisão do dono (03/11/2026): a
 * caixa aceita mais de um; a ordem é a de escolha e o 1º é o responsável (a tag dele diz "(responsável)"). Com `projetoId`, só quem
 * é coordenador na gerência do projeto (PR 9, P9-5); o backend aplica a mesma regra.
 */

import { type JSX } from 'react';
import UsuarioPicker, { type UsuarioItem, type UsuarioPickerProps } from './UsuarioPicker';

/** Coordenador selecionado (mesmo shape de UsuarioItem). */
export type CoordenadorItem = UsuarioItem;

export type CoordenadoresPickerProps = Pick<
  UsuarioPickerProps,
  'value' | 'onChange' | 'projetoId' | 'id' | 'aria-describedby' | 'aria-invalid'
>;

export default function CoordenadoresPicker(props: CoordenadoresPickerProps): JSX.Element {
  return (
    <UsuarioPicker
      {...props}
      role="Coordenador"
      tagColor="purple"
      ariaLabel="Coordenadores selecionados"
      oQueCarrega="os coordenadores"
      marcaDoPrimeiro="responsável"
      daLista="dos coordenadores"
    />
  );
}
