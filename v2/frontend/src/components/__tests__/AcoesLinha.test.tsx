/**
 * AcoesLinha (Programa C, C1): as ações de uma linha de tabela sem ocupar largura.
 *
 * - botões só de ícone, com nome acessível (rótulo + alvo da linha) e Tooltip com o rótulo;
 * - até 3 ícones; do 4º em diante, o menu "Mais ações";
 * - `compacto` (celular): todas as ações no menu, um botão só.
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DeleteOutlined, EditOutlined, EyeOutlined, KeyOutlined } from '@ant-design/icons';
import { describe, expect, test, vi } from 'vitest';

import { AcoesLinha, larguraAcoesLinha, type AcaoDaLinha } from '../AcoesLinha';

function quatroAcoes(excluir = vi.fn()): AcaoDaLinha[] {
  return [
    { chave: 'detalhes', rotulo: 'Ver detalhes', icone: <EyeOutlined />, onClick: vi.fn() },
    { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: vi.fn() },
    { chave: 'senha', rotulo: 'Redefinir senha', icone: <KeyOutlined />, onClick: vi.fn() },
    { chave: 'excluir', rotulo: 'Excluir', icone: <DeleteOutlined />, onClick: excluir, perigo: true },
  ];
}

describe('AcoesLinha', () => {
  test('até 3 ações: só ícones, cada um com nome acessível, e sem menu', async () => {
    const acoes = quatroAcoes().slice(0, 3);
    const user = userEvent.setup();
    render(<AcoesLinha acoes={acoes} alvo="Maria Aparecida" />);

    const botoes = screen.getAllByRole('button');
    expect(botoes.map((b) => b.getAttribute('aria-label'))).toEqual([
      'Ver detalhes: Maria Aparecida',
      'Editar: Maria Aparecida',
      'Redefinir senha: Maria Aparecida',
    ]);
    expect(botoes.every((b) => (b.textContent ?? '').trim() === '')).toBe(true);
    expect(screen.queryByRole('button', { name: /mais ações/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Editar: Maria Aparecida' }));
    expect(acoes[1]!.onClick).toHaveBeenCalledTimes(1);
  });

  test('4 ações: 3 ícones e a 4ª no menu "Mais ações"', async () => {
    const excluir = vi.fn();
    const user = userEvent.setup();
    render(<AcoesLinha acoes={quatroAcoes(excluir)} alvo="Maria Aparecida" />);

    expect(screen.getByRole('button', { name: 'Ver detalhes: Maria Aparecida' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Editar: Maria Aparecida' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Redefinir senha: Maria Aparecida' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Excluir: Maria Aparecida' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Mais ações: Maria Aparecida' }));
    const item = await screen.findByRole('menuitem', { name: /Excluir/ });
    await user.click(item);
    expect(excluir).toHaveBeenCalledTimes(1);
  });

  test('o Tooltip mostra o rótulo do ícone', async () => {
    const user = userEvent.setup();
    render(<AcoesLinha acoes={quatroAcoes()} alvo="Maria Aparecida" />);

    await user.hover(screen.getByRole('button', { name: 'Editar: Maria Aparecida' }));
    await waitFor(() => expect(screen.getByRole('tooltip')).toHaveTextContent('Editar'));
  });

  test('o Tooltip também abre no foco por teclado (ícone e "Mais ações")', async () => {
    const user = userEvent.setup();
    render(<AcoesLinha acoes={quatroAcoes()} alvo="Maria Aparecida" />);

    await user.tab(); // Ver detalhes
    await user.tab(); // Editar
    expect(screen.getByRole('button', { name: 'Editar: Maria Aparecida' })).toHaveFocus();
    await waitFor(() => expect(screen.getByRole('tooltip')).toHaveTextContent('Editar'));

    await user.tab(); // Redefinir senha
    await user.tab(); // Mais ações
    expect(screen.getByRole('button', { name: 'Mais ações: Maria Aparecida' })).toHaveFocus();
    await waitFor(() =>
      expect(screen.getAllByRole('tooltip').some((dica) => dica.textContent === 'Mais ações')).toBe(true),
    );
  });

  test('Esc fecha o Tooltip aberto pelo foco, sem tirar o foco do ícone (WCAG 1.4.13)', async () => {
    const user = userEvent.setup();
    render(<AcoesLinha acoes={quatroAcoes()} alvo="Maria Aparecida" />);
    const editar = screen.getByRole('button', { name: 'Editar: Maria Aparecida' });

    act(() => editar.focus()); // como um modal que, ao fechar, devolve o foco ao ícone
    await waitFor(() => expect(screen.getByRole('tooltip')).toHaveTextContent('Editar'));
    await user.keyboard('{Escape}');

    await waitFor(() => expect(screen.queryByRole('tooltip')).not.toBeInTheDocument());
    expect(editar).toHaveFocus();
  });

  test('escolher uma ação no menu devolve o foco ao "Mais ações" (e o modal que ela abre o devolve ali)', async () => {
    const acoes = quatroAcoes();
    const user = userEvent.setup();
    render(<AcoesLinha acoes={acoes} alvo="Maria Aparecida" compacto />);
    const botao = screen.getByRole('button', { name: 'Mais ações: Maria Aparecida' });

    await user.click(botao);
    await user.click(await screen.findByRole('menuitem', { name: /Editar/ }));

    expect(acoes[1]!.onClick).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(botao).toHaveFocus());
    expect(botao).toHaveAttribute('aria-expanded', 'false');
  });

  test('"Mais ações" anuncia o menu, leva o foco a ele e o Esc devolve o foco ao botão', async () => {
    const user = userEvent.setup();
    render(<AcoesLinha acoes={quatroAcoes()} alvo="Maria Aparecida" compacto />);
    const botao = screen.getByRole('button', { name: 'Mais ações: Maria Aparecida' });

    expect(botao).toHaveAttribute('aria-haspopup', 'menu');
    expect(botao).toHaveAttribute('aria-expanded', 'false');

    await user.tab();
    expect(botao).toHaveFocus();
    await user.keyboard('{Enter}');

    expect(botao).toHaveAttribute('aria-expanded', 'true');
    const menu = await screen.findByRole('menu');
    await waitFor(() => expect(menu).toContainElement(document.activeElement as HTMLElement));
    expect(document.activeElement).toHaveAttribute('role', 'menuitem');

    // O rc-dropdown lê `keyCode` (o navegador manda 27); o user-event v14 manda 0.
    fireEvent.keyDown(document.activeElement as HTMLElement, { key: 'Escape', code: 'Escape', keyCode: 27, which: 27 });

    await waitFor(() => expect(botao).toHaveFocus());
    expect(botao).toHaveAttribute('aria-expanded', 'false');
  });

  test('compacto (celular): um botão só, com todas as ações no menu', async () => {
    const user = userEvent.setup();
    render(<AcoesLinha acoes={quatroAcoes()} alvo="Maria Aparecida" compacto />);

    expect(screen.getAllByRole('button')).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: 'Mais ações: Maria Aparecida' }));
    const itens = await screen.findAllByRole('menuitem');
    expect(itens.map((i) => i.textContent)).toEqual(['Ver detalhes', 'Editar', 'Redefinir senha', 'Excluir']);
  });

  test('o item do menu tem só o rótulo como nome, sem o nome do ícone em inglês ("delete Excluir")', async () => {
    const user = userEvent.setup();
    render(<AcoesLinha acoes={quatroAcoes()} alvo="Maria Aparecida" compacto />);

    await user.click(screen.getByRole('button', { name: 'Mais ações: Maria Aparecida' }));

    expect(await screen.findByRole('menuitem', { name: 'Excluir' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Editar' })).toBeInTheDocument();
  });

  test('larguraAcoesLinha cobre os botões que aparecem', () => {
    expect(larguraAcoesLinha(1)).toBeLessThan(larguraAcoesLinha(3));
    expect(larguraAcoesLinha(4)).toBeGreaterThan(larguraAcoesLinha(3));
    expect(larguraAcoesLinha(6)).toBe(larguraAcoesLinha(4)); // 3 ícones + o menu, sempre
    expect(larguraAcoesLinha(4, true)).toBe(larguraAcoesLinha(1));
  });
});
