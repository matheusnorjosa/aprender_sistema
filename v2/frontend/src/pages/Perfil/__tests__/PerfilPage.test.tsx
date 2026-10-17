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
    username: '12345678900',
    email: 'pessoa.teste@example.invalid',
    first_name: 'Pessoa',
    last_name: 'Teste',
    name: 'Pessoa Teste',
    groups: ['Coordenador'],
    setores: ['Vidas'],
    funcoes: ['Coordenador'],
    gerencias: [],
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

describe('PerfilPage — redefinições da senha por outra pessoa (F1)', () => {
  test('lista as redefinições dos últimos 30 dias', () => {
    renderPage(
      makeUser({
        redefinicoes_senha: [
          { por: 'Outra Pessoa', em: '16/10/2026' },
          { por: 'Pessoa Do Dat', em: '15/10/2026' },
        ],
      }),
    );

    const lista = screen.getByRole('list', { name: 'Redefinições da sua senha nos últimos 30 dias' });
    expect(lista).toHaveTextContent('Outra Pessoa em 16/10/2026');
    expect(lista).toHaveTextContent('Pessoa Do Dat em 15/10/2026');
  });

  test('sem redefinições, não mostra a seção', () => {
    renderPage(makeUser({ redefinicoes_senha: [] }));

    expect(screen.queryByRole('list', { name: /Redefinições da sua senha/ })).not.toBeInTheDocument();
  });
});

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
    expect(await screen.findByText('Pessoa Teste')).toBeInTheDocument();
    // CPF mascarado (LGPD): 3 primeiros + 2 últimos.
    expect(screen.getByText('123.***.***-00')).toBeInTheDocument();
    expect(screen.getByText('pessoa.teste@example.invalid')).toBeInTheDocument();
  });

  test('PR A: o setor vem do vínculo (me.gerencias, nome de tela), não do grupo', async () => {
    renderPage(
      makeUser({ setores: ['Vidas'], gerencias: [{ id: 4, rotulo: 'Superativar', papeis: ['COORDENADOR'] }] })
    );
    expect(await screen.findByText('Superativar')).toBeInTheDocument();
    expect(screen.queryByText('Vidas')).not.toBeInTheDocument();
  });

  test('PR A: sem vínculo (Controle opera por grupo), o setor cai para os grupos de setor', async () => {
    renderPage(makeUser({ setores: ['Controle'], gerencias: [] }));
    expect(await screen.findByText('Controle')).toBeInTheDocument();
  });

  test('mascara o CPF do campo cpf (não do username) e mostra telefone/cargo', async () => {
    renderPage(
      makeUser({
        username: 'pessoa.teste', // username != cpf
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
