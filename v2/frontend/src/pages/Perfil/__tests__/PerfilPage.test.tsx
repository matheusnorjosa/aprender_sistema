import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { message } from 'antd';

const { changeMyPasswordMock } = vi.hoisted(() => ({
  changeMyPasswordMock: vi.fn(),
}));

vi.mock('../../../api/me', () => ({
  changeMyPassword: changeMyPasswordMock,
}));

import PerfilPage from '../PerfilPage';
import type { CurrentUser } from '../../../types/usuario';

function makeUser(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: 1,
    username: '04944374305',
    email: 'coord@aprendereditora.com.br',
    first_name: 'Amanda',
    last_name: 'Rodrigues',
    name: 'Amanda Rodrigues',
    groups: ['Coordenador'],
    setores: ['Vidas'],
    funcoes: ['Coordenador'],
    is_superuser: false,
    is_superintendencia: false,
    can_approve_super: false,
    permissions: [],
    ...overrides,
  };
}

function renderPage(user: CurrentUser = makeUser()) {
  return render(
    <MemoryRouter>
      <PerfilPage user={user} />
    </MemoryRouter>
  );
}

function fill(placeholder: string, value: string) {
  fireEvent.change(screen.getByPlaceholderText(placeholder), { target: { value } });
}

describe('PerfilPage', () => {
  beforeEach(() => {
    changeMyPasswordMock.mockReset();
    vi.restoreAllMocks();
  });

  test('mostra os dados do usuário com CPF mascarado', async () => {
    renderPage();
    expect(await screen.findByText('Amanda Rodrigues')).toBeInTheDocument();
    // CPF mascarado (LGPD): 3 primeiros + 2 últimos.
    expect(screen.getByText('049.***.***-05')).toBeInTheDocument();
    expect(screen.getByText('coord@aprendereditora.com.br')).toBeInTheDocument();
  });

  test('submit válido chama changeMyPassword e avisa sucesso', async () => {
    changeMyPasswordMock.mockResolvedValueOnce({ detail: 'Senha alterada com sucesso.' });
    const successSpy = vi.spyOn(message, 'success');
    renderPage();

    fill('Senha atual', 'SenhaAtual123!');
    fill('Nova senha', 'N0vaSenh@Forte');
    fill('Confirmar nova senha', 'N0vaSenh@Forte');
    fireEvent.click(screen.getByRole('button', { name: /alterar senha/i }));

    await waitFor(() =>
      expect(changeMyPasswordMock).toHaveBeenCalledWith({
        old_password: 'SenhaAtual123!',
        new_password: 'N0vaSenh@Forte',
      })
    );
    await waitFor(() => expect(successSpy).toHaveBeenCalled());
  });

  test('confirmação divergente bloqueia o submit (não chama a API)', async () => {
    renderPage();

    fill('Senha atual', 'SenhaAtual123!');
    fill('Nova senha', 'N0vaSenh@Forte');
    fill('Confirmar nova senha', 'Diferente123!');
    fireEvent.click(screen.getByRole('button', { name: /alterar senha/i }));

    expect(await screen.findByText('As senhas não conferem.')).toBeInTheDocument();
    expect(changeMyPasswordMock).not.toHaveBeenCalled();
  });

  test('erro do backend exibe message.error', async () => {
    changeMyPasswordMock.mockRejectedValueOnce(new Error('Senha atual incorreta.'));
    const errorSpy = vi.spyOn(message, 'error');
    renderPage();

    fill('Senha atual', 'errada');
    fill('Nova senha', 'N0vaSenh@Forte');
    fill('Confirmar nova senha', 'N0vaSenh@Forte');
    fireEvent.click(screen.getByRole('button', { name: /alterar senha/i }));

    await waitFor(() => expect(changeMyPasswordMock).toHaveBeenCalled());
    await waitFor(() => expect(errorSpy).toHaveBeenCalled());
  });
});
