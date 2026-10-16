/**
 * Troca obrigatória de senha no primeiro acesso: com `deve_trocar_senha` ligado no /api/me/,
 * o App mostra só a tela "Defina sua senha" — sem menu, sem rotas e sem pedir nada que o
 * servidor recusaria (policies, polling). Depois da troca, abre o endereço que a pessoa pediu.
 *
 * Estratégia: mesma do App.boot-error — filhos pesados stubados; getMe controlado.
 */
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import type { CurrentUser } from '../types';

const { getMeMock, getMyPoliciesMock, logoutMock } = vi.hoisted(() => ({
  getMeMock: vi.fn(),
  getMyPoliciesMock: vi.fn(),
  logoutMock: vi.fn(),
}));

vi.mock('../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../api/me', () => ({ getMyPolicies: getMyPoliciesMock }));
vi.mock('../api/auth', () => ({ logout: logoutMock }));

vi.mock('../components/AppSidebar', () => ({ AppSidebar: () => <nav>SIDEBAR</nav> }));
vi.mock('../components/AppHeader', () => ({ AppHeader: () => <div>HEADER</div> }));
vi.mock('../components/AppRoutes', () => ({
  AppRoutes: () => <div data-testid="app-routes">ROUTES</div>,
}));
vi.mock('../pages/Auth/LoginPage', () => ({ default: () => <div>LOGIN_PAGE</div> }));
interface RedefinicaoStub {
  por: string;
  em: string;
}

// O stub mostra o que o App passa em `aviso` e `redefinicoes` (F1): o teste cobre a ligação
// /api/me/ → App → tela; o texto da tela real é coberto em TrocaSenhaObrigatoriaPage.test.tsx.
vi.mock('../pages/Auth/TrocaSenhaObrigatoriaPage', () => ({
  default: ({
    aviso,
    redefinicoes,
    onConcluida,
    onSair,
  }: {
    aviso?: RedefinicaoStub | null;
    redefinicoes?: readonly RedefinicaoStub[];
    onConcluida: () => void;
    onSair: () => void;
  }) => (
    <div>
      <h1>Defina sua senha</h1>
      {aviso && <p role="status">{`Sua senha foi redefinida por ${aviso.por} em ${aviso.em}.`}</p>}
      {redefinicoes && redefinicoes.length > 0 && (
        <ul aria-label="REDEFINICOES">
          {redefinicoes.map((r) => (
            <li key={`${r.por}-${r.em}`}>{`${r.por} em ${r.em}`}</li>
          ))}
        </ul>
      )}
      <button type="button" onClick={onConcluida}>CONCLUIR</button>
      <button type="button" onClick={onSair}>SAIR</button>
    </div>
  ),
}));

vi.mock('../hooks/useSessionMonitor', () => ({
  default: () => ({ showWarning: false, timeLeft: 7200, sessionAge: 7200, renewSession: vi.fn() }),
}));
vi.mock('../components/SessionExpiryWarning', () => ({ default: () => null }));
vi.mock('../hooks/useGCalAlertsPolling', () => ({
  useGCalAlertsPolling: () => ({ alerts: { errors: 0, warnings: 0 } }),
}));
vi.mock('../hooks/useUnreadNotificationsPolling', () => ({
  useUnreadNotificationsPolling: () => ({ unreadNotifications: 0 }),
}));
vi.mock('../services/preloadSearchData', () => ({
  preloadSearchData: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('../services/swCache', () => ({ clearApiCaches: vi.fn().mockResolvedValue(undefined) }));

import App from '../App';
import { TROCA_DE_SENHA_OBRIGATORIA } from '../api/config';

const pessoa: CurrentUser = {
  id: 7,
  username: 'conta.ficticia',
  email: 'pessoa.ficticia@example.invalid',
  first_name: 'Pessoa',
  last_name: 'Fictícia',
  name: 'Pessoa Fictícia',
  groups: [],
  setores: [],
  funcoes: [],
  gerencias: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

describe('App — troca obrigatória de senha no primeiro acesso', () => {
  const enderecoInicial = window.location.pathname;

  beforeEach(() => {
    vi.clearAllMocks();
    getMyPoliciesMock.mockResolvedValue([]);
    logoutMock.mockResolvedValue(undefined);
    window.history.pushState({}, '', '/minhas-solicitacoes');
  });

  afterEach(() => {
    window.history.pushState({}, '', enderecoInicial);
  });

  test('marca ligada: só a tela de troca — sem menu, sem rotas, sem buscar policies', async () => {
    getMeMock.mockResolvedValue({ ...pessoa, deve_trocar_senha: true });

    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Defina sua senha' })).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByTestId('app-routes')).not.toBeInTheDocument();
    expect(screen.queryByText('LOGIN_PAGE')).not.toBeInTheDocument();
    expect(getMyPoliciesMock).not.toHaveBeenCalled();
  });

  test('F1: o aviso e o histórico do /api/me/ chegam à tela de troca', async () => {
    getMeMock.mockResolvedValue({
      ...pessoa,
      deve_trocar_senha: true,
      aviso_senha_redefinida: { por: 'Pessoa Do Dat', em: '16/10/2026' },
      redefinicoes_senha: [
        { por: 'Pessoa Do Dat', em: '16/10/2026' },
        { por: 'Outra Pessoa', em: '15/10/2026' },
      ],
    });

    render(<App />);

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Sua senha foi redefinida por Pessoa Do Dat em 16/10/2026.',
    );
    const lista = screen.getByRole('list', { name: 'REDEFINICOES' });
    expect(lista).toHaveTextContent('Pessoa Do Dat em 16/10/2026');
    expect(lista).toHaveTextContent('Outra Pessoa em 15/10/2026');
  });

  test('F1: sem aviso no /api/me/, a tela de troca não mostra o status', async () => {
    getMeMock.mockResolvedValue({ ...pessoa, deve_trocar_senha: true, aviso_senha_redefinida: null });

    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Defina sua senha' })).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'REDEFINICOES' })).not.toBeInTheDocument();
  });

  test('depois da troca: abre o sistema no endereço que a pessoa tinha pedido', async () => {
    // Contador local (não `mockXOnce`): o retry do vitest re-executa o corpo do teste.
    let trocou = false;
    getMeMock.mockImplementation(() => Promise.resolve({ ...pessoa, deve_trocar_senha: !trocou }));

    render(<App />);
    const concluir = await screen.findByRole('button', { name: 'CONCLUIR' });
    trocou = true;
    await userEvent.click(concluir);

    expect(await screen.findByTestId('app-routes')).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Defina sua senha' })).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/minhas-solicitacoes');
    expect(getMyPoliciesMock).toHaveBeenCalledTimes(1);
  });

  test('marca desligada (ou payload antigo sem o campo): sistema normal', async () => {
    getMeMock.mockResolvedValue(pessoa);

    render(<App />);

    expect(await screen.findByTestId('app-routes')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Defina sua senha' })).not.toBeInTheDocument();
  });

  test('marca ligada com a pessoa já dentro: o aviso do servidor leva à tela de troca', async () => {
    let marcada = false;
    getMeMock.mockImplementation(() => Promise.resolve({ ...pessoa, deve_trocar_senha: marcada }));

    render(<App />);
    await screen.findByTestId('app-routes');

    marcada = true;
    act(() => {
      window.dispatchEvent(new Event(TROCA_DE_SENHA_OBRIGATORIA));
    });

    expect(await screen.findByRole('heading', { name: 'Defina sua senha' })).toBeInTheDocument();
    expect(screen.queryByTestId('app-routes')).not.toBeInTheDocument();
    expect(window.location.pathname).toBe('/minhas-solicitacoes');
  });

  test('"Sair" na tela de troca encerra a sessão no servidor', async () => {
    getMeMock.mockResolvedValue({ ...pessoa, deve_trocar_senha: true });

    render(<App />);
    await userEvent.click(await screen.findByRole('button', { name: 'SAIR' }));

    await waitFor(() => expect(logoutMock).toHaveBeenCalledTimes(1));
  });
});
