/** Moldura do Deslocamento: caminho, aviso de quem vê na versão real, de onde vêm os dados e o menu. */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { QUEM_VE } from '../../quemVe';
import { renderTelaDeslocamento } from './telaDeslocamento';

describe('Deslocamento — moldura e menu', { timeout: 20000 }, () => {
  test('caminho de volta à Integra e o aviso de quem vê esta tela na versão real', async () => {
    renderTelaDeslocamento('/integra/deslocamento');
    await screen.findByRole('heading', { level: 1, name: 'Tempos de deslocamento' });
    expect(screen.getByRole('link', { name: 'Integra' })).toHaveAttribute('href', '/integra');
    expect(QUEM_VE.deslocamento.aviso).toMatch(/^Na versão real, quem vê esta tela: /);
    expect(screen.getByText(QUEM_VE.deslocamento.aviso)).toBeInTheDocument();
  });

  test('diz o que é real e o que é simulado', async () => {
    renderTelaDeslocamento('/integra/deslocamento');
    const origem = await screen.findByText(/Os tempos não são simulados/);
    expect(origem).toHaveTextContent(/são as estimativas do relatório da Coordenação Pedagógica \(novembro de 2026\)/);
    expect(origem).toHaveTextContent(/coordenadores e as carteiras são fictícios/);
  });

  test('a tela das regras não chama os tempos de reais logo acima de "São estimativas, não horários reais"', async () => {
    renderTelaDeslocamento('/integra/deslocamento/regras');
    await screen.findAllByText(/São estimativas, não horários reais/);
    expect(document.body).not.toHaveTextContent(/tempos[^.]*reais/i);
  });

  test('menu local com as três telas; a atual fica marcada', async () => {
    const user = userEvent.setup();
    renderTelaDeslocamento('/integra/deslocamento');
    const menu = await screen.findByRole('navigation', { name: 'Telas do Deslocamento' });
    const links = within(menu).getAllByRole('link');
    expect(links.map((l) => l.textContent)).toEqual(['Tempos por município', 'Como o tempo é calculado', 'Soma por coordenador']);
    expect(links[0]).toHaveAttribute('aria-current', 'page');

    await user.click(links[1]!);
    expect(await screen.findByRole('heading', { level: 1, name: 'Como o tempo é calculado' })).toBeInTheDocument();
    expect(within(menu).getByRole('link', { name: 'Como o tempo é calculado' })).toHaveAttribute('aria-current', 'page');

    await user.click(within(menu).getByRole('link', { name: 'Soma por coordenador' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Soma por coordenador' })).toBeInTheDocument();
  });

  test('endereço desconhecido volta para os tempos por município', async () => {
    renderTelaDeslocamento('/integra/deslocamento/nao-existe');
    expect(await screen.findByRole('heading', { level: 1, name: 'Tempos de deslocamento' })).toBeInTheDocument();
  });
});
