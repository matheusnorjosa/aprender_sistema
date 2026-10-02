/**
 * Tests: TrocaSenhaObrigatoriaPage — tela bloqueante do primeiro acesso.
 *
 * A pessoa entrou com a senha que recebeu; o servidor só aceita a troca. A tela mostra as
 * regras ANTES do erro, põe o foco no primeiro campo, devolve o erro do servidor no campo
 * certo e oferece "Sair".
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { changeMyPasswordMock } = vi.hoisted(() => ({ changeMyPasswordMock: vi.fn() }));

vi.mock('../../../api/me', () => ({ changeMyPassword: changeMyPasswordMock }));

import TrocaSenhaObrigatoriaPage from '../TrocaSenhaObrigatoriaPage';

const RECEBIDA = 'Provisoria#2026';
const NOVA = 'Girassol#Azul77';

function montar() {
  const onConcluida = vi.fn();
  const onSair = vi.fn();
  const onSessaoEncerrada = vi.fn();
  render(
    <TrocaSenhaObrigatoriaPage onConcluida={onConcluida} onSair={onSair} onSessaoEncerrada={onSessaoEncerrada} />,
  );
  return { onConcluida, onSair, onSessaoEncerrada };
}

async function preencher(recebida: string, nova: string, repetida: string = nova): Promise<void> {
  if (recebida) await userEvent.type(screen.getByLabelText('Senha que você recebeu'), recebida);
  if (nova) await userEvent.type(screen.getByLabelText('Nova senha'), nova);
  if (repetida) await userEvent.type(screen.getByLabelText('Repita a nova senha'), repetida);
}

const salvar = (): Promise<void> => userEvent.click(screen.getByRole('button', { name: 'Salvar e continuar' }));

const erroHttp = (status: number, data: unknown, extra: object = {}): Error =>
  Object.assign(new Error('falhou'), { status, response: { status, data }, ...extra });

describe('TrocaSenhaObrigatoriaPage', () => {
  beforeEach(() => {
    changeMyPasswordMock.mockReset();
  });

  test('diz o que está acontecendo e mostra as cinco regras antes de qualquer digitação', () => {
    montar();

    expect(screen.getByRole('heading', { level: 1, name: 'Defina sua senha' })).toBeInTheDocument();
    expect(screen.getByText(/Você entrou com uma senha provisória/)).toBeInTheDocument();
    const regras = screen.getByRole('list', { name: 'Regras da nova senha' });
    expect(regras).toHaveTextContent('Pelo menos 8 caracteres');
    expect(regras).toHaveTextContent('Não pode ser só números');
    expect(regras).toHaveTextContent('Não pode ser uma senha muito comum');
    expect(regras).toHaveTextContent('Não pode parecer com seu nome, CPF ou e-mail');
    expect(regras).toHaveTextContent('Tem de ser diferente da senha que você recebeu');
    expect(regras.querySelectorAll('li')).toHaveLength(5);
  });

  test('campos têm rótulo, autocomplete certo, regras ligadas à nova senha e foco no primeiro', () => {
    montar();

    const recebida = screen.getByLabelText('Senha que você recebeu');
    const nova = screen.getByLabelText('Nova senha');
    const repetida = screen.getByLabelText('Repita a nova senha');
    expect(recebida).toHaveAttribute('autocomplete', 'current-password');
    expect(nova).toHaveAttribute('autocomplete', 'new-password');
    expect(repetida).toHaveAttribute('autocomplete', 'new-password');
    expect(recebida).toHaveAttribute('type', 'password');
    expect(recebida).toHaveFocus();

    const regras = screen.getByRole('list', { name: 'Regras da nova senha' });
    expect(nova.getAttribute('aria-describedby')?.split(' ')).toContain(regras.id);
  });

  test('não há menu nem link para o resto do sistema: só salvar e sair', () => {
    montar();

    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Salvar e continuar' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sair' })).toBeInTheDocument();
  });

  test('submeter vazio mostra o erro em cada campo e não chama a API', async () => {
    montar();

    await salvar();

    expect(await screen.findByText('Digite a senha que você recebeu.')).toBeInTheDocument();
    expect(await screen.findByText('Digite a nova senha.')).toBeInTheDocument();
    expect(await screen.findByText('Digite a nova senha outra vez.')).toBeInTheDocument();
    expect(changeMyPasswordMock).not.toHaveBeenCalled();
  });

  test('confirmação diferente: "As senhas não conferem." e não chama a API', async () => {
    montar();

    await preencher(RECEBIDA, NOVA, 'Outra#Coisa99');
    await salvar();

    expect(await screen.findByText('As senhas não conferem.')).toBeInTheDocument();
    expect(changeMyPasswordMock).not.toHaveBeenCalled();
  });

  test('nova igual à recebida é recusada na tela, sem chamar a API', async () => {
    montar();

    await preencher(RECEBIDA, RECEBIDA);
    await salvar();

    expect(await screen.findByText('A nova senha tem de ser diferente da que você recebeu.')).toBeInTheDocument();
    expect(changeMyPasswordMock).not.toHaveBeenCalled();
  });

  test('sucesso: chama a troca com as duas senhas e avisa que concluiu', async () => {
    changeMyPasswordMock.mockResolvedValue({ detail: 'Senha alterada com sucesso.' });
    const { onConcluida } = montar();

    await preencher(RECEBIDA, NOVA);
    await salvar();

    await waitFor(() => expect(onConcluida).toHaveBeenCalledTimes(1));
    expect(changeMyPasswordMock).toHaveBeenCalledWith({ old_password: RECEBIDA, new_password: NOVA });
  });

  test('erro do servidor na senha nova aparece no campo "Nova senha", que recebe o foco', async () => {
    changeMyPasswordMock.mockRejectedValue(
      erroHttp(400, { code: 'INVALID', errors: { new_password: ['Esta senha é muito comum.'] } }),
    );
    const { onConcluida } = montar();

    await preencher(RECEBIDA, NOVA);
    await salvar();

    expect(await screen.findByText('Esta senha é muito comum.')).toBeInTheDocument();
    const nova = screen.getByLabelText('Nova senha');
    expect(nova).toHaveAttribute('aria-invalid', 'true');
    await waitFor(() => expect(nova).toHaveFocus());
    expect(onConcluida).not.toHaveBeenCalled();
  });

  test('senha recebida errada aparece no campo "Senha que você recebeu"', async () => {
    changeMyPasswordMock.mockRejectedValue(
      erroHttp(400, { code: 'INVALID', errors: { old_password: 'Senha atual incorreta.' } }),
    );
    montar();

    await preencher('errada-de-proposito', NOVA);
    await salvar();

    expect(await screen.findByText('Esta não é a senha que você recebeu. Confira e digite de novo.')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText('Senha que você recebeu')).toHaveFocus());
  });

  test('sessão encerrada no servidor (403 NOT_AUTHENTICATED): avisa o App, sem erro na tela', async () => {
    changeMyPasswordMock.mockRejectedValue(erroHttp(403, { code: 'NOT_AUTHENTICATED' }));
    const { onSessaoEncerrada, onConcluida } = montar();

    await preencher(RECEBIDA, NOVA);
    await salvar();

    await waitFor(() => expect(onSessaoEncerrada).toHaveBeenCalledTimes(1));
    expect(onConcluida).not.toHaveBeenCalled();
  });

  test('sem conexão: diz que a senha não foi alterada', async () => {
    changeMyPasswordMock.mockRejectedValue(new TypeError('Sem conexão com o servidor.'));
    montar();

    await preencher(RECEBIDA, NOVA);
    await salvar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Sem conexão com o servidor. Sua senha não foi alterada. Confira a internet e tente de novo.',
    );
  });

  test('muitas tentativas (429): diz quanto esperar', async () => {
    changeMyPasswordMock.mockRejectedValue(erroHttp(429, { code: 'THROTTLED' }, { retryAfter: 42 }));
    montar();

    await preencher(RECEBIDA, NOVA);
    await salvar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Muitas tentativas. Aguarde 42 segundos e tente de novo. Sua senha não foi alterada.',
    );
  });

  test('erro do servidor (500): mensagem geral, sem culpar a senha', async () => {
    changeMyPasswordMock.mockRejectedValue(erroHttp(500, { detail: 'boom' }));
    montar();

    await preencher(RECEBIDA, NOVA);
    await salvar();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Não foi possível salvar a senha agora. O problema é no sistema, não na sua senha. Tente de novo em alguns minutos.',
    );
  });

  test('"Sair" chama onSair', async () => {
    const { onSair } = montar();

    await userEvent.click(screen.getByRole('button', { name: 'Sair' }));

    expect(onSair).toHaveBeenCalledTimes(1);
    expect(changeMyPasswordMock).not.toHaveBeenCalled();
  });
});
