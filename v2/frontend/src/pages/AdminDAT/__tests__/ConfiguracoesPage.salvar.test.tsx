/**
 * Auditoria UX 30/09 (ALTA): salvar Configurações sem abrir as outras abas não pode
 * mudar o que não foi tocado.
 *
 * As abas do AntD só montam na primeira visita: sem `forceRender`, o
 * `validateFields()` devolvia só os campos da aba aberta, o PUT ia sem Google
 * Calendar, Sessões e Experimental, e o backend completava com o padrão.
 *
 * Rodada 2 (BAIXA): o PUT leva só o que mudou (o backend mescla com o vigente), para o
 * AuditLog listar só o que mudou e duas pessoas editando não desfazerem uma à outra.
 * Falha de carga desabilita o Salvar e mostra o motivo.
 *
 * Rodada 4 (decisão do dono, 01/10): a tela mostra só os 2 campos que o sistema lê (Buffer de
 * deslocamento e Aviso de horas por dia). Os outros 13 não tinham efeito e saíram da tela; o
 * backend os guarda como estão (o PUT mescla), e o salvar não os manda.
 */

import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { message } from 'antd';

const { getSystemConfigMock, updateSystemConfigMock } = vi.hoisted(() => ({
  getSystemConfigMock: vi.fn(),
  updateSystemConfigMock: vi.fn(),
}));

vi.mock('../../../api/systemConfig', () => ({
  getSystemConfig: getSystemConfigMock,
  updateSystemConfig: updateSystemConfigMock,
}));

import ConfiguracoesPage from '../ConfiguracoesPage';

/** Valores do servidor, todos diferentes do padrão do backend. */
const CONFIG_DO_SERVIDOR = {
  TRAVEL_BUFFER_MINUTES: 90,
  AVAILABILITY_DAILY_LIMIT_HOURS: 10,
  ALLOW_ADJACENT_EVENTS: false,
  BLOCK_AUTO_APPROVE: false,
  BATCH_SIZE: 150,
  LOCK_TTL_SECONDS: 200,
  AUTO_RETRY_ON_ERROR: false,
  MAX_RETRIES: 2,
  SEND_UPDATES: 'all',
  SESSION_COOKIE_AGE: 3600,
  SESSION_WARNING_THRESHOLD: 600,
  AUTOCOMPLETE_DEBOUNCE_MS: 500,
  ENABLE_MULTI_CALENDAR: true,
  ENABLE_BATCH_ACTIONS: true,
  ENABLE_ADVANCED_FILTERS: true,
};

async function abrir(): Promise<HTMLElement> {
  render(<ConfiguracoesPage />);
  return screen.findByRole('button', { name: /Salvar Configurações/ });
}

/** As 13 chaves sem leitor no sistema: escondidas da tela em 01/10 (decisão do dono). */
const CHAVES_ESCONDIDAS = [
  'ALLOW_ADJACENT_EVENTS',
  'BLOCK_AUTO_APPROVE',
  'BATCH_SIZE',
  'LOCK_TTL_SECONDS',
  'AUTO_RETRY_ON_ERROR',
  'MAX_RETRIES',
  'SEND_UPDATES',
  'SESSION_COOKIE_AGE',
  'SESSION_WARNING_THRESHOLD',
  'AUTOCOMPLETE_DEBOUNCE_MS',
  'ENABLE_MULTI_CALENDAR',
  'ENABLE_BATCH_ACTIONS',
  'ENABLE_ADVANCED_FILTERS',
];

/** Pelo id do campo (o nome no Form). */
function mudarCampo(nome: string, valor: string): void {
  const campo = document.getElementById(nome);
  if (!campo) throw new Error(`campo ${nome} não encontrado`);
  fireEvent.change(campo, { target: { value: valor } });
  fireEvent.blur(campo);
}

async function abrirMudarBufferESalvar(): Promise<void> {
  const salvar = await abrir();
  mudarCampo('TRAVEL_BUFFER_MINUTES', '45');
  fireEvent.click(salvar);
}

describe('ConfiguracoesPage — salvar não desfaz o que não foi tocado', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSystemConfigMock.mockResolvedValue({ ...CONFIG_DO_SERVIDOR });
  });

  test('só os 2 campos que o sistema lê aparecem, sem abas', async () => {
    await abrir();

    expect(screen.getByLabelText('Buffer de deslocamento')).toHaveValue('90');
    expect(screen.getByLabelText('Aviso de horas por dia')).toHaveValue('10');
    // Rótulo honesto (02/10/2026): o limite avisa, não impede, e não promete contagem com teto.
    expect(screen.getByText(/O aviso não impede o evento\./)).toBeInTheDocument();
    expect(screen.queryByText(/Máximo de horas/)).not.toBeInTheDocument();
    const campos = [...document.querySelectorAll('input, [role="switch"], [role="combobox"]')].map((c) => c.id);
    expect(campos.sort()).toEqual(['AVAILABILITY_DAILY_LIMIT_HOURS', 'TRAVEL_BUFFER_MINUTES']);
    expect(screen.queryAllByRole('tab')).toHaveLength(0);
  }, 20000);

  test('salvar manda só o campo alterado e nenhuma das chaves escondidas', async () => {
    updateSystemConfigMock.mockImplementation((v: Record<string, unknown>) =>
      Promise.resolve({ ...CONFIG_DO_SERVIDOR, ...v }),
    );

    await abrirMudarBufferESalvar();

    await waitFor(() => expect(updateSystemConfigMock).toHaveBeenCalledTimes(1));
    const enviado = updateSystemConfigMock.mock.calls[0][0] as Record<string, unknown>;
    expect(enviado).toEqual({ TRAVEL_BUFFER_MINUTES: 45 });
    expect(Object.keys(enviado).filter((k) => CHAVES_ESCONDIDAS.includes(k))).toEqual([]);
  }, 20000);

  test('salvar sem alterar nada não chama o backend e avisa', async () => {
    const infoSpy = vi.spyOn(message, 'info');

    fireEvent.click(await abrir());

    await waitFor(() => expect(infoSpy).toHaveBeenCalledWith('Nenhuma alteração para salvar.'));
    expect(updateSystemConfigMock).not.toHaveBeenCalled();
  }, 20000);

  test('campo vazio: diz o erro no campo e não chama o backend', async () => {
    const salvar = await abrir();

    mudarCampo('TRAVEL_BUFFER_MINUTES', '');
    fireEvent.click(salvar);

    expect(await screen.findByText('Campo obrigatório')).toBeInTheDocument();
    expect(updateSystemConfigMock).not.toHaveBeenCalled();
  }, 20000);

  // O backend só aceita inteiro: um 90,5 voltava 400 com a chave técnica na mensagem.
  test('número não inteiro: diz o erro no campo e não chama o backend', async () => {
    const salvar = await abrir();

    mudarCampo('TRAVEL_BUFFER_MINUTES', '90.5');
    fireEvent.click(salvar);

    expect(await screen.findByText('Use um número inteiro maior ou igual a 0.')).toBeInTheDocument();
    expect(updateSystemConfigMock).not.toHaveBeenCalled();
  }, 20000);

  test('falha ao carregar: Salvar desabilitado e o motivo na tela', async () => {
    getSystemConfigMock.mockRejectedValue(new Error('HTTP 500: Internal Server Error'));

    const salvar = await abrir();

    expect(salvar.closest('button')).toBeDisabled();
    const titulo = await screen.findByText('Não foi possível carregar as configurações');
    const aviso = titulo.closest('[role="alert"]');
    expect(aviso).not.toBeNull();
    expect(aviso).toHaveTextContent('HTTP 500: Internal Server Error');
  }, 20000);

  test('sucesso só depois de o backend confirmar; erro do backend não mostra sucesso', async () => {
    const successSpy = vi.spyOn(message, 'success');
    const errorSpy = vi.spyOn(message, 'error');
    let rejeitar: (e: unknown) => void = () => {};
    updateSystemConfigMock.mockImplementation(
      () => new Promise((_resolve, reject) => { rejeitar = reject; }),
    );

    await abrirMudarBufferESalvar();

    await waitFor(() => expect(updateSystemConfigMock).toHaveBeenCalledTimes(1));
    expect(successSpy).not.toHaveBeenCalled();
    // Enquanto a API trabalha, o Salvar fica em loading.
    expect(screen.getByRole('button', { name: /Salvar Configurações/ })).toHaveClass('ant-btn-loading');

    rejeitar(new Error('HTTP 500'));
    await waitFor(() => expect(errorSpy).toHaveBeenCalled());
    expect(successSpy).not.toHaveBeenCalled();
  }, 20000);

  // O erro mostra o motivo real: antes, sem rede vinha só "Erro ao salvar configurações", e um
  // 500 ou 403 (corpo `{code, detail}`) virava "Erro de validação: code: ... detail: ...".
  test.each([
    { caso: 'sem rede', erro: new TypeError('Sem conexão com o servidor.'), motivo: 'Sem conexão com o servidor.' },
    {
      caso: '403 sem permissão',
      erro: Object.assign(new Error('Você não tem permissão para executar essa ação.'), {
        status: 403,
        response: { status: 403, data: { code: 'PERMISSION_DENIED', detail: 'Você não tem permissão para executar essa ação.' } },
      }),
      motivo: 'Você não tem permissão para executar essa ação.',
    },
  ])('erro ao salvar ($caso) diz o motivo', async ({ erro, motivo }) => {
    const errorSpy = vi.spyOn(message, 'error');
    updateSystemConfigMock.mockRejectedValueOnce(erro);

    await abrirMudarBufferESalvar();

    await waitFor(() => expect(errorSpy).toHaveBeenCalled());
    const texto = String(errorSpy.mock.calls[0][0]);
    expect(texto).toContain(motivo);
    expect(texto).not.toContain('Erro de validação');
  }, 20000);
});
