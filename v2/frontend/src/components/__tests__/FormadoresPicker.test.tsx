/**
 * FormadoresPicker → UsuarioPicker → lookupUsuarios: o projeto do evento chega ao lookup
 * (`/lookup/usuarios/?projeto_id=`), que oferece só pessoas da gerência dele (PR 9, P9-5).
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { lookupUsuariosMock } = vi.hoisted(() => ({ lookupUsuariosMock: vi.fn() }));
vi.mock('../../api/lookup', () => ({ lookupUsuarios: lookupUsuariosMock }));

import FormadoresPicker from '../FormadoresPicker';

describe('FormadoresPicker — projeto do evento no lookup (PR 9)', () => {
  beforeEach(() => {
    lookupUsuariosMock.mockReset();
    lookupUsuariosMock.mockResolvedValue([]);
  });

  test('ao focar e ao buscar, o lookup recebe o projeto escolhido', async () => {
    render(<FormadoresPicker value={[]} onChange={vi.fn()} projetoId={123} />);
    const campo = screen.getByRole('combobox');
    fireEvent.focus(campo);
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('', 'Formador,Coordenador', 123));
    fireEvent.change(campo, { target: { value: 'an' } });
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('an', 'Formador,Coordenador', 123));
  });

  test('cada formador escolhido tem um botão "Remover" que o teclado alcança', () => {
    const onChange = vi.fn();
    render(
      <FormadoresPicker
        value={[{ id: 1, label: 'Bruno Formador' }, { id: 2, label: 'Gil Formador' }]}
        onChange={onChange}
      />
    );
    const remover = screen.getByRole('button', { name: 'Remover Bruno Formador' });
    remover.focus();
    expect(remover).toHaveFocus();
    fireEvent.click(remover);
    expect(onChange).toHaveBeenCalledWith([{ id: 2, label: 'Gil Formador' }]);
  });

  test('o id e os aria-* do Form.Item chegam ao campo de busca', () => {
    render(<FormadoresPicker value={[]} onChange={vi.fn()} id="formadores" aria-invalid="true" aria-describedby="formadores_help" />);
    const campo = screen.getByRole('combobox');
    expect(campo).toHaveAttribute('id', 'formadores');
    expect(campo).toHaveAttribute('aria-invalid', 'true');
    expect(campo).toHaveAttribute('aria-describedby', 'formadores_help');
  });

  test('falha ao carregar mostra o motivo e "Tentar de novo"', async () => {
    lookupUsuariosMock.mockRejectedValueOnce(new Error('Servidor indisponível.'));
    render(<FormadoresPicker value={[]} onChange={vi.fn()} projetoId={123} />);
    fireEvent.focus(screen.getByRole('combobox'));
    expect(await screen.findByText('Não foi possível carregar os formadores.')).toBeInTheDocument();
    expect(screen.getByText('Servidor indisponível.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo: carregar os formadores' }));
    await waitFor(() => expect(screen.queryByText('Não foi possível carregar os formadores.')).not.toBeInTheDocument());
  });
});
