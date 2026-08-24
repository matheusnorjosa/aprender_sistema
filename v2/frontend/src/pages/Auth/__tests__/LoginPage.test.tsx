/**
 * Tests: LoginPage (página de login — AS v2)
 *
 * Cobertura (presença/estado, sem fluxo assíncrono real):
 * - Heading "Login"
 * - Campos de CPF (usuário) e senha renderizam
 * - Botão "Entrar" presente e habilitado
 * - Validação de campos obrigatórios ao submeter vazio (não chama login)
 *
 * GOTCHA: `login` (de ../../api/auth) só dispara no submit — não há fetch no
 * mount. Mesmo assim mockamos o módulo para não puxar `api/config` (fetchAPI)
 * na árvore de import e evitar qualquer promessa pendente no teardown do worker
 * (EnvironmentTeardownError, que reprova o CI mesmo com asserts verdes).
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, test, vi } from 'vitest';

const { loginMock } = vi.hoisted(() => ({ loginMock: vi.fn() }));

vi.mock('../../../api/auth', () => ({
  login: loginMock,
}));

import LoginPage from '../LoginPage';

describe('LoginPage', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  test('renderiza o heading "Login"', () => {
    render(<LoginPage />);
    expect(screen.getByRole('heading', { name: 'Login' })).toBeInTheDocument();
  });

  test('renderiza os campos de CPF e senha', () => {
    render(<LoginPage />);

    // Campo de usuário (CPF): label + input via placeholder
    expect(screen.getByText('CPF')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('CPF')).toBeInTheDocument();

    // Campo de senha: label + input do tipo password
    expect(screen.getByText('Senha')).toBeInTheDocument();
    const senha = screen.getByPlaceholderText('Sua senha');
    expect(senha).toBeInTheDocument();
    expect(senha).toHaveAttribute('type', 'password');
  });

  test('renderiza o botão "Entrar" habilitado', () => {
    render(<LoginPage />);

    const botao = screen.getByRole('button', { name: 'Entrar' });
    expect(botao).toBeInTheDocument();
    expect(botao).toHaveAttribute('type', 'submit');
    expect(botao).toBeEnabled();
  });

  test('renderiza a logo com alt acessível', () => {
    render(<LoginPage />);
    expect(screen.getByRole('img', { name: 'Aprender Sistema' })).toBeInTheDocument();
  });

  test('valida campos obrigatórios ao submeter vazio, sem chamar login', async () => {
    render(<LoginPage />);

    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }));

    expect(await screen.findByText('Por favor, insira seu CPF!')).toBeInTheDocument();
    expect(await screen.findByText('Por favor, insira sua senha!')).toBeInTheDocument();

    await waitFor(() => {
      expect(loginMock).not.toHaveBeenCalled();
    });
  });
});
