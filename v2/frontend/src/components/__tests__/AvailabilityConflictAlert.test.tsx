import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import AvailabilityConflictAlert, { ListaDeBloqueados } from '../AvailabilityConflictAlert';
import type { BlockedParticipant } from '../../types';

describe('AvailabilityConflictAlert', () => {
  test('não renderiza nada quando não há bloqueados', () => {
    const { container } = render(<AvailabilityConflictAlert bloqueados={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  test('nomeia o participante e mostra o texto do conflito verbatim do backend', () => {
    const bloqueados: BlockedParticipant[] = [
      {
        usuario_id: 99,
        usuario_nome: 'Bruno Formador',
        conflicts: [{ code: 'X', title: 'Sobreposição', detail: 'Conflita com evento aprovado #5', ref_id: 5 }],
      },
    ];
    render(<AvailabilityConflictAlert bloqueados={bloqueados} id="x" />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Não é possível criar o evento')).toBeInTheDocument();
    expect(screen.getByText('Bruno Formador')).toBeInTheDocument();
    expect(screen.getByText('Conflita com evento aprovado #5')).toBeInTheDocument();
    // A tag diz o motivo por extenso (não a letra do código), e a frase fixa de
    // sobreposição saiu: o motivo pode ser limite diário, bloqueio ou deslocamento.
    expect(screen.getByText('Sobreposição')).toBeInTheDocument();
    expect(screen.queryByText('X')).not.toBeInTheDocument();
    expect(screen.queryByText(/já está alocado neste horário/)).not.toBeInTheDocument();
    expect(screen.getByText(/Remova o participante em conflito/)).toBeInTheDocument();
  });

  test('conflito sem detalhe mostra o motivo uma vez só', () => {
    const bloqueados: BlockedParticipant[] = [
      { usuario_id: 7, usuario_nome: 'Dora Formadora', conflicts: [{ code: 'M', title: 'Capacidade diária excedida', detail: '' }] },
    ];
    render(<AvailabilityConflictAlert bloqueados={bloqueados} />);

    expect(screen.getAllByText('Capacidade diária excedida')).toHaveLength(1);
  });

  test('ListaDeBloqueados aceita a orientação de quem usa (aprovação)', () => {
    const bloqueados: BlockedParticipant[] = [
      { usuario_id: 7, usuario_nome: 'Dora Formadora', conflicts: [{ code: 'M', title: 'Capacidade diária excedida', detail: 'Total do dia' }] },
    ];
    render(<ListaDeBloqueados bloqueados={bloqueados} orientacao="Reprove ou peça o ajuste a quem criou." />);

    expect(screen.getByText('Dora Formadora')).toBeInTheDocument();
    expect(screen.getByText('Reprove ou peça o ajuste a quem criou.')).toBeInTheDocument();
    expect(screen.queryByText(/Remova o participante em conflito/)).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  test('lista múltiplos participantes bloqueados', () => {
    const bloqueados: BlockedParticipant[] = [
      { usuario_id: 1, usuario_nome: 'Ana', conflicts: [{ code: 'T', title: 'Bloqueio', detail: 'total' }] },
      { usuario_id: 2, usuario_nome: 'Bruno', conflicts: [{ code: 'M', title: 'Capacidade', detail: 'diária' }] },
    ];
    render(<AvailabilityConflictAlert bloqueados={bloqueados} />);
    expect(screen.getByText('Ana')).toBeInTheDocument();
    expect(screen.getByText('Bruno')).toBeInTheDocument();
  });
});
