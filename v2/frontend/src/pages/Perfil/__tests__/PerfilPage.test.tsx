import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { message } from 'antd';

const { changeMyPasswordMock, updateMyContactMock, exportMyDataMock } = vi.hoisted(() => ({
  changeMyPasswordMock: vi.fn(),
  updateMyContactMock: vi.fn(),
  exportMyDataMock: vi.fn(),
}));

vi.mock('../../../api/me', () => ({
  changeMyPassword: changeMyPasswordMock,
  updateMyContact: updateMyContactMock,
  exportMyData: exportMyDataMock,
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
    updateMyContactMock.mockReset();
    exportMyDataMock.mockReset();
    vi.restoreAllMocks();
  });

  test('exportar meus dados chama exportMyData e dispara o download (art. 18-V)', async () => {
    const blob = new Blob(['{"personal_data":{}}'], { type: 'application/json' });
    exportMyDataMock.mockResolvedValueOnce(blob);
    const createObjectURL = vi.fn(() => 'blob:fake');
    const revokeObjectURL = vi.fn();
    (URL as unknown as { createObjectURL: unknown }).createObjectURL = createObjectURL;
    (URL as unknown as { revokeObjectURL: unknown }).revokeObjectURL = revokeObjectURL;
    const successSpy = vi.spyOn(message, 'success');
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: /exportar meus dados/i }));

    await waitFor(() => expect(exportMyDataMock).toHaveBeenCalled());
    await waitFor(() => expect(successSpy).toHaveBeenCalled());
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(revokeObjectURL).toHaveBeenCalled();
  });

  test('mostra os dados do usuário com CPF mascarado', async () => {
    renderPage();
    expect(await screen.findByText('Amanda Rodrigues')).toBeInTheDocument();
    // CPF mascarado (LGPD): 3 primeiros + 2 últimos.
    expect(screen.getByText('049.***.***-05')).toBeInTheDocument();
    expect(screen.getByText('coord@aprendereditora.com.br')).toBeInTheDocument();
  });

  test('mascara o CPF do campo cpf (não do username) e mostra telefone/cargo', async () => {
    renderPage(
      makeUser({
        username: 'amanda.rodrigues', // username != cpf
        cpf: '11144477735',
        telefone: '(85) 98888-1111',
        cargo: 'Coordenadora',
      })
    );
    // Mascara o CPF real, não o username.
    expect(await screen.findByText('111.***.***-35')).toBeInTheDocument();
    expect(screen.getByText('(85) 98888-1111')).toBeInTheDocument();
    expect(screen.getByText('Coordenadora')).toBeInTheDocument();
  });

  test('salvar telefone chama updateMyContact e avisa sucesso (art. 18-III)', async () => {
    updateMyContactMock.mockResolvedValueOnce(makeUser({ telefone: '(85) 97777-2222' }));
    const successSpy = vi.spyOn(message, 'success');
    renderPage();

    fill('(85) 99999-0000', '(85) 97777-2222');
    fireEvent.click(screen.getByRole('button', { name: /salvar telefone/i }));

    await waitFor(() =>
      expect(updateMyContactMock).toHaveBeenCalledWith({ telefone: '(85) 97777-2222' })
    );
    await waitFor(() => expect(successSpy).toHaveBeenCalled());
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
