/**
 * Integra (protótipo para a validação de 07/12/2026): moldura, página com os 4 cartões e rotas.
 *
 * A rota `/integra/*` é aberta pelo AppRoutes só com a policy `access_integra` (o gate está em
 * `AppRoutes.access-by-profile.test.tsx`); aqui a moldura é montada direto.
 */
import { MemoryRouter, Route, Routes } from 'react-router';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { EXTERNAL_URLS } from '../../../constants/urls';
import IntegraLayout from '../IntegraLayout';

function renderIntegra(rota: string): void {
  render(
    <MemoryRouter initialEntries={[rota]}>
      <Routes>
        <Route path="/integra/*" element={<IntegraLayout />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Integra — moldura e página', { timeout: 20000 }, () => {
  test('a faixa DADOS SIMULADOS aparece como nota em toda tela da Integra', async () => {
    for (const rota of ['/integra', '/integra/ica', '/integra/semaforo', '/integra/para-validar']) {
      const { unmount } = render(
        <MemoryRouter initialEntries={[rota]}>
          <Routes>
            <Route path="/integra/*" element={<IntegraLayout />} />
          </Routes>
        </MemoryRouter>,
      );
      const nota = await screen.findByRole('note');
      expect(nota).toHaveTextContent(/DADOS SIMULADOS/);
      expect(nota).toHaveTextContent(/nada é gravado/i);
      unmount();
    }
  });

  test('os 4 cartões: ICA, Semáforo, DFF e Avaliação do Coordenador', async () => {
    renderIntegra('/integra');
    expect(await screen.findByText('ICA')).toBeInTheDocument();
    const ica = screen.getByRole('link', { name: /ICA/ });
    expect(ica).toHaveAttribute('href', '/integra/ica');
    expect(screen.getByRole('link', { name: /Semáforo/ })).toHaveAttribute('href', '/integra/semaforo');
  });

  test('DFF abre em outra aba, com aviso no nome do link e sem passar a janela de origem', async () => {
    renderIntegra('/integra');
    const dff = await screen.findByRole('link', { name: /DFF.*abre em outra aba/i });
    expect(dff).toHaveAttribute('href', EXTERNAL_URLS.DFF_PLATFORM);
    expect(dff).toHaveAttribute('target', '_blank');
    expect(dff.getAttribute('rel')?.split(' ').sort()).toEqual(['noopener', 'noreferrer']);
  });

  test('Avaliação do Coordenador está desativada e avisa "em breve"', async () => {
    renderIntegra('/integra');
    const titulo = await screen.findByText('Avaliação do Coordenador');
    const cartao = titulo.closest('[aria-disabled]');
    expect(cartao).not.toBeNull();
    expect(cartao).toHaveAttribute('aria-disabled', 'true');
    expect(within(cartao as HTMLElement).getByText(/em breve/i)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Avaliação do Coordenador/ })).not.toBeInTheDocument();
  });

  test('link para a tela "Para validar no dia 7"', async () => {
    renderIntegra('/integra');
    const link = await screen.findByRole('link', { name: /Para validar no dia 7/i });
    expect(link).toHaveAttribute('href', '/integra/para-validar');
  });

  test('Semáforo: tela "em construção" com volta para a Integra', async () => {
    renderIntegra('/integra/semaforo');
    expect(await screen.findByText(/chega na próxima entrega/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Voltar para a Integra/i })).toHaveAttribute('href', '/integra');
  });

  test('endereço desconhecido dentro da Integra volta para a página da Integra', async () => {
    renderIntegra('/integra/nao-existe');
    expect(await screen.findByText('Avaliação do Coordenador')).toBeInTheDocument();
  });
});

describe('Integra — telas do ICA', { timeout: 20000 }, () => {
  const TELAS = [
    ['/integra/ica', 'Painel do ICA'],
    ['/integra/ica/coordenador/101', 'Ficha do coordenador'],
    ['/integra/ica/simulador', 'Simulador de remanejamento'],
    ['/integra/ica/pesos', 'Pesos e faixas'],
    ['/integra/ica/gerencias', 'Visão por gerência'],
    ['/integra/ica/comparativo', 'Comparativo de pesos'],
    ['/integra/ica/historico', 'Histórico semestral'],
    ['/integra/ica/alertas', 'Alertas'],
  ] as const;

  test.each(TELAS)('%s mostra "%s"', async (rota, titulo) => {
    renderIntegra(rota);
    expect(await screen.findByRole('heading', { level: 1, name: titulo })).toBeInTheDocument();
  });

  test('a ficha do smoke é de verdade (id que existe), não o "não encontrado"', async () => {
    renderIntegra('/integra/ica/coordenador/101');
    expect(await screen.findByRole('heading', { level: 2, name: 'Lucinéia Barreto' })).toBeInTheDocument();
    expect(screen.queryByText('Coordenador não encontrado.')).not.toBeInTheDocument();
  });

  test('menu local do ICA: um link por tela (a ficha abre pelo painel) e a atual marcada', async () => {
    renderIntegra('/integra/ica/pesos');
    const nav = await screen.findByRole('navigation', { name: 'Telas do ICA' });
    const links = within(nav).getAllByRole('link');
    expect(links.map((l) => l.getAttribute('href'))).toEqual([
      '/integra/ica',
      '/integra/ica/simulador',
      '/integra/ica/pesos',
      '/integra/ica/gerencias',
      '/integra/ica/comparativo',
      '/integra/ica/historico',
      '/integra/ica/alertas',
    ]);
    expect(within(nav).getByRole('link', { name: 'Pesos e faixas' })).toHaveAttribute('aria-current', 'page');
    expect(within(nav).getByRole('link', { name: 'Painel' })).not.toHaveAttribute('aria-current');
  });

  test('endereço desconhecido dentro do ICA volta para o painel', async () => {
    renderIntegra('/integra/ica/nao-existe');
    expect(await screen.findByRole('heading', { level: 1, name: 'Painel do ICA' })).toBeInTheDocument();
  });
});

describe('Integra — troca de tela', { timeout: 20000 }, () => {
  const scrollToOriginal = window.scrollTo;
  afterEach(() => {
    window.scrollTo = scrollToOriginal;
  });

  test('o nome no Painel abre a Ficha no topo, com o foco no título; "Voltar ao painel" também', async () => {
    const rolar = vi.fn();
    window.scrollTo = rolar;
    const user = userEvent.setup();
    renderIntegra('/integra/ica');
    const lista = await screen.findByRole('list', { name: 'ICA por coordenador' });
    // Ao abrir a tela pela primeira vez, o foco não é tirado de onde está.
    expect(screen.getByRole('heading', { level: 1, name: 'Painel do ICA' })).not.toHaveFocus();
    expect(rolar).not.toHaveBeenCalled();

    await user.click(within(lista).getAllByRole('link')[0] as HTMLElement);
    const ficha = await screen.findByRole('heading', { level: 1, name: 'Ficha do coordenador' });
    await waitFor(() => expect(ficha).toHaveFocus());
    expect(rolar).toHaveBeenCalledWith(0, 0);

    rolar.mockClear();
    await user.click(screen.getByRole('link', { name: 'Voltar ao painel' }));
    const painel = await screen.findByRole('heading', { level: 1, name: 'Painel do ICA' });
    await waitFor(() => expect(painel).toHaveFocus());
    expect(rolar).toHaveBeenCalledWith(0, 0);
  });
});

describe('Integra — Para validar no dia 7', { timeout: 20000 }, () => {
  test('a tela abre com o título', async () => {
    renderIntegra('/integra/para-validar');
    expect(await screen.findByRole('heading', { level: 1, name: /Para validar no dia 7/i })).toBeInTheDocument();
  });
});
