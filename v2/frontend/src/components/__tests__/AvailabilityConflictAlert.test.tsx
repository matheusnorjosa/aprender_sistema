import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import AvailabilityConflictAlert from '../AvailabilityConflictAlert';
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
    expect(screen.getByText('X')).toBeInTheDocument();
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
