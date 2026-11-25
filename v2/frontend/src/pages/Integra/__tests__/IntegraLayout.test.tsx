/**
 * Integra (protótipo para a validação de 07/12/2026): moldura, página com os 5 cartões e rotas.
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
import { QUEM_VE, type ChaveTela } from '../quemVe';

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
    for (const rota of ['/integra', '/integra/ica', '/integra/semaforo', '/integra/deslocamento', '/integra/para-validar']) {
      const { unmount } = render(
        <MemoryRouter initialEntries={[rota]}>
          <Routes>
            <Route path="/integra/*" element={<IntegraLayout />} />
          </Routes>
        </MemoryRouter>,
      );
      // As telas do Semáforo e do Deslocamento têm outra nota (quem vê na versão real): acha a faixa pelo texto.
      const nota = (await screen.findByText('DADOS SIMULADOS')).closest('[role="note"]');
      expect(nota).not.toBeNull();
      expect(nota).toHaveTextContent(/nada é gravado/i);
      // Os municípios e os tempos de deslocamento vêm do relatório real: a faixa não os chama de gerados, e não
      // chama de reais os tempos que o relatório diz que são estimativas.
      expect(nota).toHaveTextContent(/municípios reais; tempos estimados pelo relatório/);
      expect(nota).not.toHaveTextContent(/tempos de deslocamento são reais/);
      // A faixa fica presa no topo e a folga do `scroll-padding-top` (integra.css) foi medida para um texto deste
      // tamanho: 3 linhas a 360 px e 1 a partir de 768 px. Texto mais longo faz a faixa cobrir o título de destino
      // e o campo focado (WCAG 2.4.11). A explicação longa fica no parágrafo da página da Integra.
      expect(nota?.textContent?.length ?? 0).toBeLessThanOrEqual(100);
      unmount();
    }
  });

  test('a página da Integra diz o que é simulado e o que é real', async () => {
    renderIntegra('/integra');
    expect(
      await screen.findByText(
        'As ferramentas do gestor pedagógico num lugar só. As pessoas e os números destas telas são simulados; os municípios são reais, e os tempos de deslocamento são as estimativas do relatório da Coordenação Pedagógica.',
      ),
    ).toBeInTheDocument();
  });

  test('os 5 cartões: ICA, Semáforo, Deslocamento, DFF e Avaliação do Coordenador', async () => {
    renderIntegra('/integra');
    expect(await screen.findByText('ICA')).toBeInTheDocument();
    const ica = screen.getByRole('link', { name: /ICA/ });
    expect(ica).toHaveAttribute('href', '/integra/ica');
    expect(screen.getByRole('link', { name: /Semáforo/ })).toHaveAttribute('href', '/integra/semaforo');
    expect(screen.getByRole('link', { name: /Deslocamento/ })).toHaveAttribute('href', '/integra/deslocamento');
    // O Deslocamento soma o tempo de referência de ida e volta; "viagens" são as registradas na tela de viagens.
    expect(screen.getByRole('link', { name: /Deslocamento/ })).toHaveTextContent(/ida e volta/);
    expect(screen.getByRole('link', { name: /Deslocamento/ })).not.toHaveTextContent(/viagens/);
    expect(screen.getByRole('link', { name: /DFF/ })).toBeInTheDocument();
    expect(screen.getByText('Avaliação do Coordenador')).toBeInTheDocument();
    expect(screen.queryByText(/chega na próxima entrega/i)).not.toBeInTheDocument();
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

  test('Semáforo: abre o índice das telas, com o caminho de volta para a Integra', async () => {
    renderIntegra('/integra/semaforo');
    expect(await screen.findByRole('heading', { level: 1, name: 'Semáforo de Risco Municipal' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Telas do Semáforo' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Integra' })).toHaveAttribute('href', '/integra');
  });

  test('Deslocamento: abre os tempos por município, com o caminho de volta para a Integra', async () => {
    renderIntegra('/integra/deslocamento');
    expect(await screen.findByRole('heading', { level: 1, name: 'Tempos de deslocamento' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Telas do Deslocamento' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Integra' })).toHaveAttribute('href', '/integra');
  });

  test('endereço desconhecido dentro da Integra volta para a página da Integra', async () => {
    renderIntegra('/integra/nao-existe');
    expect(await screen.findByText('Avaliação do Coordenador')).toBeInTheDocument();
  });
});

describe('Integra — telas do ICA', { timeout: 20000 }, () => {
  /** [rota, título, chave do aviso de quem vê na versão real]. */
  const TELAS: readonly (readonly [string, string, ChaveTela])[] = [
    ['/integra/ica', 'Painel do ICA', 'painel'],
    ['/integra/ica/coordenador/101', 'Ficha do coordenador', 'coordenador'],
    ['/integra/ica/simulador', 'Simulador de remanejamento', 'simulador'],
    ['/integra/ica/pesos', 'Pesos e faixas', 'pesos'],
    ['/integra/ica/gerencias', 'Visão por gerência', 'gerencias'],
    ['/integra/ica/comparativo', 'Comparativo de pesos', 'comparativo'],
    ['/integra/ica/historico', 'Histórico semestral', 'historico'],
    ['/integra/ica/alertas', 'Alertas', 'alertas'],
  ];

  test.each(TELAS)('%s mostra "%s" e o aviso de quem vê', async (rota, titulo, chave) => {
    renderIntegra(rota);
    expect(await screen.findByRole('heading', { level: 1, name: titulo })).toBeInTheDocument();
    const aviso = screen.getByText(QUEM_VE[chave].aviso);
    expect(aviso.closest('[role="note"]')).not.toBeNull();
    // Um aviso só por tela.
    expect(screen.getAllByText(/^Na versão real, quem vê esta tela: /)).toHaveLength(1);
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

describe('Integra — telas do Semáforo e do Deslocamento', { timeout: 20000 }, () => {
  /** [rota, título, chave do aviso de quem vê]. O índice do Semáforo não tem aviso: só lista as telas. */
  const TELAS: readonly (readonly [string, string, ChaveTela | null])[] = [
    ['/integra/semaforo', 'Semáforo de Risco Municipal', null],
    ['/integra/semaforo/comite', 'Comitê de Satisfação', 'comite'],
    ['/integra/semaforo/municipio/5', 'Ficha do município', 'municipio'],
    ['/integra/semaforo/gestora', 'Painel da gestora de referência', 'gestora'],
    ['/integra/semaforo/pesquisa', 'Pesquisa do articulador', 'pesquisa'],
    ['/integra/semaforo/lider', 'Indicadores da Líder do NFP', 'lider'],
    ['/integra/semaforo/relatorio-mensal', 'Relatório mensal e formulários', 'relatorio-mensal'],
    ['/integra/deslocamento', 'Tempos de deslocamento', 'deslocamento'],
    ['/integra/deslocamento/regras', 'Como o tempo é calculado', 'deslocamento'],
    ['/integra/deslocamento/coordenadores', 'Soma por coordenador', 'deslocamento'],
  ];

  test.each(TELAS)('%s mostra "%s", a faixa e o aviso de quem vê', async (rota, titulo, chave) => {
    renderIntegra(rota);
    expect(await screen.findByRole('heading', { level: 1, name: titulo })).toBeInTheDocument();
    expect(screen.getByText('DADOS SIMULADOS')).toBeInTheDocument();
    if (chave) expect(screen.getByText(QUEM_VE[chave].aviso)).toBeInTheDocument();
  });

  test('menu local do Deslocamento leva às 3 telas', async () => {
    renderIntegra('/integra/deslocamento/regras');
    const nav = await screen.findByRole('navigation', { name: 'Telas do Deslocamento' });
    expect(within(nav).getAllByRole('link').map((l) => l.getAttribute('href'))).toEqual([
      '/integra/deslocamento',
      '/integra/deslocamento/regras',
      '/integra/deslocamento/coordenadores',
    ]);
  });

  test('endereço desconhecido dentro do Deslocamento volta para os tempos por município', async () => {
    renderIntegra('/integra/deslocamento/nao-existe');
    expect(await screen.findByRole('heading', { level: 1, name: 'Tempos de deslocamento' })).toBeInTheDocument();
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
