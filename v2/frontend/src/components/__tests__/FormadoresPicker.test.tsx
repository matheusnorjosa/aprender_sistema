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
});
