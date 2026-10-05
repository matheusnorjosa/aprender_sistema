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
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

const { loginMock } = vi.hoisted(() => ({ loginMock: vi.fn() }));

vi.mock('../../../api/auth', () => ({
  login: loginMock,
}));

import LoginPage from '../LoginPage';
import { guardarAvisoDoLogin, lerAvisoDoLogin, apagarAvisoDoLogin } from '../../../utils/storage';

async function tentarEntrar(): Promise<void> {
  fireEvent.change(screen.getByPlaceholderText('CPF'), { target: { value: '52998224725' } });
  fireEvent.change(screen.getByPlaceholderText('Sua senha'), { target: { value: 'qualquer-senha' } });
  await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));
}

const erroHttp = (status: number, extra: object = {}): Error =>
  Object.assign(new Error('falhou'), { status, response: { status, data: {} }, ...extra });

describe('LoginPage', () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
    apagarAvisoDoLogin();
  });

  // Auditoria UX 30/09, rodada 2 (MÉDIA): a sessão expirada caía no login sem dizer por quê
  // (o "Logout realizado com sucesso" sumia no reload). O App guarda o motivo; o login mostra.
  test('mostra o motivo guardado (sessão expirada) e o consome', () => {
    guardarAvisoDoLogin('Sua sessão expirou por inatividade. Entre de novo.');

    render(<LoginPage />);

    expect(screen.getByRole('alert')).toHaveTextContent('Sua sessão expirou por inatividade. Entre de novo.');
    expect(lerAvisoDoLogin()).toBeNull();
  });

  test('sem motivo guardado, não mostra aviso', () => {
    render(<LoginPage />);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
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

  // P10: a tela dizia "Usuário ou senha incorretos." para QUALQUER falha (limite de tentativas
  // da rede, servidor fora, sem internet) — a pessoa redigitava a senha certa até se bloquear.
  describe('erro ao entrar: cada causa com a sua frase', () => {
    test('senha errada (400): uma frase só, com a dica do bloqueio', async () => {
      loginMock.mockRejectedValue(erroHttp(400));
      render(<LoginPage />);

      await tentarEntrar();

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'CPF ou senha incorretos. Depois de 10 erros o acesso fica bloqueado por alguns minutos.',
      );
    });

    test('muitas tentativas da rede (429): diz quanto esperar e que a senha não foi recusada', async () => {
      loginMock.mockRejectedValue(erroHttp(429, { retryAfter: 37 }));
      render(<LoginPage />);

      await tentarEntrar();

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Muitas tentativas de entrada vindas desta rede. Aguarde 37 segundos e tente de novo. Sua senha não foi recusada.',
      );
    });

    test('429 com espera longa (limite do /api/csrf/): fala em minutos', async () => {
      loginMock.mockRejectedValue(erroHttp(429, { retryAfter: 1790 }));
      render(<LoginPage />);

      await tentarEntrar();

      expect(await screen.findByRole('alert')).toHaveTextContent('Aguarde cerca de 30 minutos e tente de novo.');
    });

    test('429 sem tempo de espera: "cerca de um minuto"', async () => {
      loginMock.mockRejectedValue(erroHttp(429));
      render(<LoginPage />);

      await tentarEntrar();

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Aguarde cerca de um minuto e tente de novo. Sua senha não foi recusada.',
      );
    });

    test('sem conexão (TypeError): não culpa a senha', async () => {
      loginMock.mockRejectedValue(new TypeError('Sem conexão com o servidor.'));
      render(<LoginPage />);

      await tentarEntrar();

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Sem conexão com o servidor. Confira a internet e tente de novo. Sua senha não foi recusada.',
      );
    });

    test.each([
      ['erro do servidor (500)', erroHttp(500)],
      ['403 de CSRF', erroHttp(403)],
      ['erro sem status', new Error('CSRF token ausente. Faça login novamente.')],
    ])('%s: problema é no sistema, não na senha', async (_caso, erro) => {
      loginMock.mockRejectedValue(erro);
      render(<LoginPage />);

      await tentarEntrar();

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Não foi possível entrar agora. O problema é no sistema, não na sua senha. Tente de novo em alguns minutos.',
      );
    });

    test('o erro substitui o aviso de sessão expirada: um alerta só na tela', async () => {
      guardarAvisoDoLogin('Sua sessão expirou. Entre de novo.');
      loginMock.mockRejectedValue(erroHttp(400));
      render(<LoginPage />);
      expect(screen.getByRole('alert')).toHaveTextContent('Sua sessão expirou. Entre de novo.');

      await tentarEntrar();

      await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('CPF ou senha incorretos.'));
      expect(screen.getAllByRole('alert')).toHaveLength(1);
      expect(screen.queryByText('Sua sessão expirou. Entre de novo.')).not.toBeInTheDocument();
    });

    test('nova tentativa com sucesso apaga o erro e avisa o App', async () => {
      loginMock.mockRejectedValueOnce(erroHttp(400)).mockResolvedValueOnce({});
      const onLoginSuccess = vi.fn();
      render(<LoginPage onLoginSuccess={onLoginSuccess} />);

      await tentarEntrar();
      await screen.findByRole('alert');
      await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));

      await waitFor(() => expect(onLoginSuccess).toHaveBeenCalledTimes(1));
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
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
