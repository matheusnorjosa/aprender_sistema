/**
 * Semáforo — rotas, menu local e índice das 6 telas (DADOS SIMULADOS).
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { MemoryRouter, Route, Routes } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import IntegraLayout from '../../IntegraLayout';
import { renderTelaSemaforo } from './telaSemaforo';

const TELAS: readonly [string, string][] = [
  ['Comitê de Satisfação', '/integra/semaforo/comite'],
  ['Ficha do município', '/integra/semaforo/municipio/'],
  ['Painel da gestora de referência', '/integra/semaforo/gestora'],
  ['Pesquisa do articulador', '/integra/semaforo/pesquisa'],
  ['Indicadores da Líder', '/integra/semaforo/lider'],
  ['Relatório mensal e formulários', '/integra/semaforo/relatorio-mensal'],
];

/** A moldura da Integra só leva ao Semáforo depois que `IntegraRoutes` monta `semaforo/*` com estas rotas. */
const SEMAFORO_NA_MOLDURA = readFileSync(join(__dirname, '../../IntegraRoutes.tsx'), 'utf-8').includes('SemaforoRoutes');

describe('Semáforo — rotas e índice', { timeout: 20000 }, () => {
  test('o índice lista as 6 telas, cada uma com o link', async () => {
    renderTelaSemaforo('/integra/semaforo');
    await screen.findByText('Semáforo de Risco Municipal');
    const lista = screen.getByRole('list', { name: 'As 6 telas do Semáforo' });
    const links = within(lista).getAllByRole('link');
    expect(links).toHaveLength(6);
    TELAS.forEach(([nome, para], i) => {
      expect(links[i]).toHaveTextContent(nome);
      expect(links[i]!.getAttribute('href')).toMatch(new RegExp(`^${para}`));
    });
  });

  test('o índice diz as regras novas: o vermelho muda na hora, os projetos e a pesquisa por projeto (decisões 38, 46 e 51)', async () => {
    renderTelaSemaforo('/integra/semaforo');
    await screen.findByText('Semáforo de Risco Municipal');
    const lista = screen.getByRole('list', { name: 'As 6 telas do Semáforo' });
    expect(lista).toHaveTextContent(/o vermelho muda a cor em vigor na hora, e o Comitê confirma ou desfaz/);
    expect(lista).toHaveTextContent(/Os projetos, os 5 indicadores/);
    expect(lista).toHaveTextContent(/uma resposta por projeto/);
  });

  test('decisões 38 e 39: a abertura do Semáforo diz que um vermelho ou três amarelos mudam a cor na hora', async () => {
    renderTelaSemaforo('/integra/semaforo');
    const abertura = await screen.findByText(/Cada município ganha uma cor a cada dois meses/);
    expect(abertura).toHaveTextContent(
      'Um indicador em vermelho, ou três amarelos, muda a cor para vermelho na hora, e o Comitê confirma ou desfaz depois.',
    );
  });

  test('menu local do Semáforo, com a tela atual marcada', async () => {
    renderTelaSemaforo('/integra/semaforo/comite');
    await screen.findByText('Comitê de Satisfação');
    const menu = screen.getByRole('navigation', { name: 'Telas do Semáforo' });
    expect(within(menu).getByRole('link', { name: 'Comitê' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Integra' })).toHaveAttribute('href', '/integra');
  });

  test('o índice cita os 4 formulários da tela do relatório mensal e a observação de formação lida da DFF (decisão 94)', async () => {
    renderTelaSemaforo('/integra/semaforo');
    const lista = await screen.findByRole('list', { name: 'As 6 telas do Semáforo' });
    const item = within(lista).getByRole('link', { name: 'Relatório mensal e formulários' }).closest('li')!;
    expect(item).toHaveTextContent(
      'O relatório mensal do coordenador, os registros de ocorrência e de reunião de escuta, e a observação de formação lida da DFF.',
    );
  });

  test('em todas as telas, a moldura avisa que sair do Semáforo desfaz o que foi registrado ou publicado', async () => {
    for (const rota of ['/integra/semaforo', '/integra/semaforo/comite', '/integra/semaforo/pesquisa', '/integra/semaforo/gestora']) {
      const { unmount } = renderTelaSemaforo(rota);
      await screen.findByRole('heading', { level: 1 });
      expect(
        screen.getByText(
          'O que você registrar ou publicar no Semáforo vale só enquanto estiver nele: ir para outra parte da Integra ou recarregar a página volta tudo ao original.',
        ),
      ).toBeInTheDocument();
      unmount();
    }
  });

  test('endereço desconhecido dentro do Semáforo volta ao índice', async () => {
    renderTelaSemaforo('/integra/semaforo/nao-existe');
    expect(await screen.findByRole('list', { name: 'As 6 telas do Semáforo' })).toBeInTheDocument();
  });

  test.skipIf(!SEMAFORO_NA_MOLDURA)('na moldura da Integra, cada tela tem a faixa DADOS SIMULADOS', async () => {
    for (const rota of ['/integra/semaforo', '/integra/semaforo/comite', '/integra/semaforo/municipio/5', '/integra/semaforo/gestora']) {
      const { unmount } = render(
        <MemoryRouter initialEntries={[rota]}>
          <Routes>
            <Route path="/integra/*" element={<IntegraLayout />} />
          </Routes>
        </MemoryRouter>,
      );
      const faixa = await screen.findByText('DADOS SIMULADOS');
      expect(faixa.closest('[role="note"]')).toHaveTextContent(/nada é gravado/i);
      expect(await screen.findByRole('heading', { level: 1 })).toBeInTheDocument();
      unmount();
    }
  });
});
