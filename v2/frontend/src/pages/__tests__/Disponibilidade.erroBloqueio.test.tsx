/**
 * Disponibilidade — motivo do erro ao criar bloqueio (B#20).
 *
 * O 400 de validação do servidor chega como `detail: "Erro de validação."` e o motivo real em
 * `errors.<campo>`. A tela mostrava só o genérico; agora mostra o motivo do campo.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { message } from 'antd';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { getBlocksMock, createBlockMock } = vi.hoisted(() => ({
  getBlocksMock: vi.fn(),
  createBlockMock: vi.fn(),
}));

vi.mock('../../api/availability', () => ({
  getBlocks: getBlocksMock,
  createBlock: createBlockMock,
  deleteBlock: vi.fn(),
}));

// O formulário real usa DatePicker (frágil em jsdom): aqui só dispara o onSubmit da página.
vi.mock('../../components/BlockForm', () => ({
  default: ({ onSubmit }: { onSubmit: (p: unknown) => Promise<void> }) => (
    <button
      type="button"
      onClick={() => {
        onSubmit({ inicio: '2026-11-10T12:00:00Z', fim: '2026-11-10T12:00:00Z', tipo: 'T', motivo: '' }).catch(
          () => undefined,
        );
      }}
    >
      enviar-bloqueio
    </button>
  ),
}));

import Disponibilidade from '../Disponibilidade';

function erroHttp(status: number, data: unknown, texto: string): Error {
  return Object.assign(new Error(texto), { status, response: { status, data } });
}

describe('Disponibilidade — erro ao criar bloqueio', { timeout: 20000 }, () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getBlocksMock.mockResolvedValue([]);
  });

  test('mostra o motivo do campo que o servidor recusou', async () => {
    const erroSpy = vi.spyOn(message, 'error');
    createBlockMock.mockRejectedValue(
      erroHttp(
        400,
        {
          detail: 'Erro de validação.',
          code: 'VALIDATION_ERROR',
          errors: { fim: ['O fim do bloqueio deve ser posterior ao início.'] },
        },
        'Erro de validação.',
      ),
    );

    render(<Disponibilidade />);
    fireEvent.click(await screen.findByText('enviar-bloqueio'));

    await waitFor(() => {
      expect(erroSpy).toHaveBeenCalledWith(
        'Erro ao criar bloqueio: O fim do bloqueio deve ser posterior ao início.',
      );
    });
  });

  test('sem erro de campo, mantém a mensagem do servidor', async () => {
    const erroSpy = vi.spyOn(message, 'error');
    createBlockMock.mockRejectedValue(
      erroHttp(403, { detail: 'Você não tem permissão.', code: 'PERMISSION_DENIED' }, 'Você não tem permissão.'),
    );

    render(<Disponibilidade />);
    fireEvent.click(await screen.findByText('enviar-bloqueio'));

    await waitFor(() => {
      expect(erroSpy).toHaveBeenCalledWith('Erro ao criar bloqueio: Você não tem permissão.');
    });
  });
});
