/**
 * Menu lateral por cima do conteúdo (Programa C, C1; revisão adversarial, lentes C e D).
 *
 * Abaixo de 1280 px o ☰ abre a navegação POR CIMA do conteúdo (sobreposta < 992 px;
 * recolhida 992 a 1279 px). Enquanto ela está aberta, quem usa teclado ou leitor de tela
 * precisa: ter o foco levado ao 1º item do menu; fechar com Esc e voltar ao ☰; não
 * alcançar cabeçalho nem conteúdo atrás do fundo escuro (inert). O ☰ tem rótulo estável,
 * `aria-expanded` e `aria-controls`. Com a sobreposta fechada, a navegação escondida sai
 * do Tab e do leitor de tela. Trocar de rota por fora do menu (voltar do navegador) fecha.
 *
 * O jsdom não implementa `inert` (nem o layout): o teste confere o atributo, que o
 * navegador aplica. Sidebar, cabeçalho e `useResponsive` são os de verdade; só as rotas,
 * as APIs e os pollings são stubs.
 */

import { render, screen, fireEvent, act, waitFor, within } from '@testing-library/react';
import { describe, test, expect, vi, beforeEach } from 'vitest';
import type { CurrentUser } from '../types';
import { definirLarguraTela } from '../test/larguraTela';

const getMeMock = vi.hoisted(() => vi.fn());

vi.mock('../api/availability', () => ({ getMe: getMeMock }));
vi.mock('../api/me', () => ({ getMyPolicies: vi.fn().mockResolvedValue(['manage_admin_registries']) }));
vi.mock('../api/auth', () => ({ logout: vi.fn().mockResolvedValue(undefined) }));
vi.mock('../components/AppRoutes', () => ({
  AppRoutes: () => (
    <div data-testid="app-routes">
      <a href="#conteudo">Conteúdo da página</a>
    </div>
  ),
}));
vi.mock('../pages/Auth/LoginPage', () => ({ default: () => <div>LOGIN_PAGE</div> }));
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

import App from '../App';

// Dados fictícios.
const usuario: CurrentUser = {
  id: 7,
  username: 'teste.dat',
  email: 'teste.dat@example.invalid',
  first_name: 'Pessoa',
  last_name: 'Teste',
  name: 'Pessoa Teste',
  groups: [],
  setores: [],
  funcoes: [],
  gerencias: [],
  is_superuser: false,
  is_superintendencia: false,
  can_approve_super: false,
  permissions: [],
};

async function montar(largura: number): Promise<void> {
  definirLarguraTela(largura);
  getMeMock.mockResolvedValue(usuario);
  render(<App />);
  await screen.findByTestId('app-routes');
}

const botaoMenu = (): HTMLElement => screen.getByRole('button', { name: 'Menu principal' });
const navegacao = (): HTMLElement => screen.getByRole('navigation', { name: 'Navegacao principal' });
const inerte = (el: Element): boolean => el.closest('[inert]') !== null;

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState({}, '', '/dat/admin/usuarios');
});

describe.each([
  [360, 'sobreposta'],
  [1024, 'recolhida'],
])('a %i px (%s), o ☰ abre a navegação por cima do conteúdo', (largura) => {
  test('☰: rótulo estável, aria-expanded e aria-controls apontando para a navegação', async () => {
    await montar(largura);
    expect(botaoMenu()).toHaveAttribute('aria-expanded', 'false');
    expect(botaoMenu()).toHaveAttribute('aria-controls', navegacao().id);
    expect(navegacao().id).not.toBe('');

    fireEvent.click(botaoMenu());

    expect(botaoMenu()).toHaveAttribute('aria-expanded', 'true');
    expect(botaoMenu()).toHaveAttribute('aria-controls', navegacao().id);
  });

  test('abrir leva o foco ao 1º item e tira cabeçalho e conteúdo do Tab e do leitor', async () => {
    await montar(largura);
    fireEvent.click(botaoMenu());

    expect(screen.getByRole('link', { name: 'Página Inicial' })).toHaveFocus();
    expect(inerte(screen.getByRole('main'))).toBe(true);
    expect(inerte(screen.getByRole('button', { name: /Sair/ }))).toBe(true);
    expect(inerte(botaoMenu())).toBe(true);
    expect(inerte(navegacao())).toBe(false);
  });

  test('Esc fecha, devolve o foco ao ☰ e o conteúdo volta a ser operável', async () => {
    await montar(largura);
    fireEvent.click(botaoMenu());
    fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' });

    expect(botaoMenu()).toHaveAttribute('aria-expanded', 'false');
    expect(botaoMenu()).toHaveFocus();
    expect(document.querySelector('.mobile-sidebar-overlay')).toBeNull();
    expect(inerte(screen.getByRole('main'))).toBe(false);
  });

  test('"Fechar menu", dentro da navegação e fora do inert, fecha e devolve o foco ao ☰', async () => {
    // Com o ☰ inerte e o fundo aria-hidden, é a saída de quem usa leitor de tela no toque (sem Esc).
    await montar(largura);
    fireEvent.click(botaoMenu());

    const fechar = within(navegacao()).getByRole('button', { name: 'Fechar menu' });
    expect(inerte(fechar)).toBe(false);
    fireEvent.click(fechar);

    expect(botaoMenu()).toHaveAttribute('aria-expanded', 'false');
    expect(botaoMenu()).toHaveFocus();
    expect(screen.queryByRole('button', { name: 'Fechar menu' })).toBeNull();
  });

  test('rota que muda por fora do menu (voltar do navegador) fecha a navegação', async () => {
    await montar(largura);
    fireEvent.click(botaoMenu());
    expect(botaoMenu()).toHaveAttribute('aria-expanded', 'true');

    act(() => {
      window.history.pushState({}, '', '/home');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });

    await waitFor(() => expect(botaoMenu()).toHaveAttribute('aria-expanded', 'false'));
    expect(document.querySelector('.mobile-sidebar-overlay')).toBeNull();
  });
});

describe('navegação fechada', () => {
  test('a 360 px (sobreposta fechada): a navegação escondida não recebe Tab nem é lida', async () => {
    await montar(360);
    expect(inerte(navegacao())).toBe(true);
    expect(inerte(screen.getByRole('main'))).toBe(false);
  });

  test('a 1024 px (recolhida, só ícones): a faixa de ícones continua operável', async () => {
    await montar(1024);
    expect(inerte(navegacao())).toBe(false);
    expect(inerte(screen.getByRole('main'))).toBe(false);
    expect(screen.queryByRole('button', { name: 'Fechar menu' })).toBeNull();
  });

  test('a 1280 px (aberta): sem ☰ visível, nada inerte, e Esc não mexe no menu', async () => {
    await montar(1280);
    // display:none: fora da árvore de acessibilidade (e o nome some junto).
    expect(screen.queryByRole('button', { name: 'Menu principal' })).toBeNull();
    expect(document.querySelector('.mobile-menu-toggle')).not.toBeVisible();
    expect(document.querySelector('[inert]')).toBeNull();

    expect(screen.queryByRole('button', { name: 'Fechar menu' })).toBeNull();
    const toggle = document.querySelector('.mobile-menu-toggle');
    expect(toggle).toHaveAttribute('aria-expanded', 'true');

    fireEvent.keyDown(document.body, { key: 'Escape' });

    // Se o Esc recolhesse a sidebar aberta, ela viraria a faixa de ícones (sem inert nem fundo):
    // só o estado do ☰ e a classe do Sider mostram a diferença.
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(navegacao()).not.toHaveClass('ant-layout-sider-collapsed');
    expect(document.querySelector('[inert]')).toBeNull();
    expect(document.querySelector('.mobile-sidebar-overlay')).toBeNull();
  });
});
