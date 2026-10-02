import { render, screen } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import AvailabilityConflictAlert, { AvisosDeAgenda, ListaDeBloqueados } from '../AvailabilityConflictAlert';
import type { BlockedParticipant } from '../../types';
import type { AvisoDeAgenda } from '../../types/availability';

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
    // sobreposição saiu: o motivo pode ser bloqueio ou deslocamento.
    expect(screen.getByText('Sobreposição')).toBeInTheDocument();
    expect(screen.queryByText('X')).not.toBeInTheDocument();
    expect(screen.queryByText(/já está alocado neste horário/)).not.toBeInTheDocument();
    expect(screen.getByText(/Remova o participante em conflito/)).toBeInTheDocument();
  });

  test('conflito sem detalhe mostra o motivo uma vez só', () => {
    const bloqueados: BlockedParticipant[] = [
      { usuario_id: 7, usuario_nome: 'Dora Formadora', conflicts: [{ code: 'T', title: 'Bloqueio total', detail: '' }] },
    ];
    render(<AvailabilityConflictAlert bloqueados={bloqueados} />);

    expect(screen.getAllByText('Bloqueio total')).toHaveLength(1);
  });

  test('ListaDeBloqueados aceita a orientação de quem usa (aprovação)', () => {
    const bloqueados: BlockedParticipant[] = [
      { usuario_id: 7, usuario_nome: 'Dora Formadora', conflicts: [{ code: 'D', title: 'Buffer deslocamento insuficiente', detail: 'Apenas 60 min' }] },
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
      { usuario_id: 2, usuario_nome: 'Bruno', conflicts: [{ code: 'P', title: 'Bloqueio', detail: 'parcial' }] },
    ];
    render(<AvailabilityConflictAlert bloqueados={bloqueados} />);
    expect(screen.getByText('Ana')).toBeInTheDocument();
    expect(screen.getByText('Bruno')).toBeInTheDocument();
  });
});

describe('AvisosDeAgenda — limite diário avisa, não barra (decisão de 02/10/2026)', () => {
  const avisos: AvisoDeAgenda[] = [
    {
      usuario_id: 99,
      usuario_nome: 'Bruno Formador',
      warnings: [
        {
          code: 'M',
          title: 'Dia com mais de 8 horas de eventos',
          detail: 'No dia 10/03 a soma dos eventos chega a 10h. Isso não impede o evento.',
        },
      ],
    },
  ];

  test('sem avisos, a região viva já existe e está vazia', () => {
    render(<AvisosDeAgenda avisos={[]} />);

    // Leitor de tela só anuncia o que entra numa região que já estava na página.
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });

  test('o aviso entra na região que já estava montada', () => {
    const { rerender } = render(<AvisosDeAgenda avisos={[]} />);
    const regiao = screen.getByRole('status');

    rerender(<AvisosDeAgenda avisos={avisos} />);

    expect(screen.getByRole('status')).toBe(regiao);
    expect(regiao).toHaveTextContent('Dia com mais de 8 horas de eventos');
  });

  test('é informação (role status), nunca alerta de erro', () => {
    render(<AvisosDeAgenda avisos={avisos} />);

    const bloco = screen.getByRole('status');
    expect(bloco).toHaveTextContent('Aviso de agenda: isso não impede o evento');
    expect(bloco).toHaveTextContent('Bruno Formador');
    expect(bloco).toHaveTextContent('Dia com mais de 8 horas de eventos');
    expect(bloco).toHaveTextContent('No dia 10/03 a soma dos eventos chega a 10h.');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText('Não é possível criar o evento')).not.toBeInTheDocument();
    // Não manda remover ninguém nem trocar a data: nada está bloqueado.
    expect(screen.queryByText(/Remova o participante/)).not.toBeInTheDocument();
  });

  test('não promete contagem de horas com teto (ainda não existe)', () => {
    render(<AvisosDeAgenda avisos={avisos} />);
    expect(screen.getByRole('status').textContent ?? '').not.toMatch(/contagem|contadas|teto/i);
  });
});
