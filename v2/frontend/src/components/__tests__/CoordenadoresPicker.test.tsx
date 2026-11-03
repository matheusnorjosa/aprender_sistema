/**
 * CoordenadoresPicker → UsuarioPicker → lookupUsuarios: a caixa "Coordenador(es)" busca só o papel
 * Coordenador da gerência do projeto (PR 9, P9-5). O 1º escolhido é o responsável e a tag dele diz isso
 * (decisão do dono, 03/11/2026).
 */
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const { lookupUsuariosMock } = vi.hoisted(() => ({ lookupUsuariosMock: vi.fn() }));
vi.mock('../../api/lookup', () => ({ lookupUsuarios: lookupUsuariosMock }));

import CoordenadoresPicker from '../CoordenadoresPicker';

const CARLA = { id: 7, label: 'Carla Coordenadora' };
const DORA = { id: 8, label: 'Dora Coordenadora' };

describe('CoordenadoresPicker', () => {
  beforeEach(() => {
    lookupUsuariosMock.mockReset();
    lookupUsuariosMock.mockResolvedValue([]);
  });

  test('ao focar e ao buscar, o lookup pede só o papel Coordenador do projeto escolhido', async () => {
    render(<CoordenadoresPicker value={[]} onChange={vi.fn()} projetoId={123} />);
    const campo = screen.getByRole('combobox');
    fireEvent.focus(campo);
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('', 'Coordenador', 123));
    fireEvent.change(campo, { target: { value: 'an' } });
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('an', 'Coordenador', 123));
  });

  test('a 1ª tag diz que é o responsável, no texto e no botão de remover', () => {
    render(<CoordenadoresPicker value={[CARLA, DORA]} onChange={vi.fn()} />);
    expect(screen.getByText('Carla Coordenadora (responsável)')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Remover Carla Coordenadora (responsável) dos coordenadores' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remover Dora Coordenadora dos coordenadores' })).toBeInTheDocument();
    expect(screen.queryByText('Dora Coordenadora (responsável)')).not.toBeInTheDocument();
  });

  test('trocar o projeto refaz a busca com o projeto novo (as opções do anterior não valem)', async () => {
    lookupUsuariosMock.mockResolvedValue([{ id: 7, label: 'Carla Coordenadora' }]);
    const { rerender } = render(<CoordenadoresPicker value={[]} onChange={vi.fn()} projetoId={123} />);
    fireEvent.focus(screen.getByRole('combobox'));
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('', 'Coordenador', 123));
    fireEvent.blur(screen.getByRole('combobox'));
    // O rc-select só solta o foco depois de um instante: sem esperar, o 2º focus não conta.
    await act(async () => {
      await new Promise((fim) => setTimeout(fim, 50));
    });

    rerender(<CoordenadoresPicker value={[]} onChange={vi.fn()} projetoId={456} />);
    fireEvent.focus(screen.getByRole('combobox'));
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('', 'Coordenador', 456));
  });

  test('a resposta atrasada da busca do projeto anterior é descartada', async () => {
    let responderAntiga: (itens: unknown[]) => void = () => {};
    lookupUsuariosMock.mockImplementationOnce(
      () => new Promise((resolver) => {
        responderAntiga = resolver;
      }),
    );
    const { rerender } = render(<CoordenadoresPicker value={[]} onChange={vi.fn()} projetoId={123} />);
    fireEvent.focus(screen.getByRole('combobox'));
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('', 'Coordenador', 123));
    fireEvent.blur(screen.getByRole('combobox'));
    await act(async () => {
      await new Promise((fim) => setTimeout(fim, 50));
    });

    rerender(<CoordenadoresPicker value={[]} onChange={vi.fn()} projetoId={456} />);
    await act(async () => {
      responderAntiga([{ id: 1, label: 'Coordenadora do Projeto Antigo' }]);
    });
    // Sem descartar, as opções do projeto 123 voltariam e o foco não buscaria o 456.
    fireEvent.focus(screen.getByRole('combobox'));
    await waitFor(() => expect(lookupUsuariosMock).toHaveBeenCalledWith('', 'Coordenador', 456));
    expect(screen.queryByText('Coordenadora do Projeto Antigo')).not.toBeInTheDocument();
  });

  test('nome longo quebra dentro da tag em vez de passar da largura', () => {
    const longo = { id: 9, label: 'Maria Aparecida Conceição dos Santos Albuquerque de Vasconcelos Ficticia' };
    render(<CoordenadoresPicker value={[longo]} onChange={vi.fn()} />);
    const tag = screen.getByText(`${longo.label} (responsável)`).closest('.ant-tag');
    expect(tag).toHaveClass('max-w-full', 'whitespace-normal', 'break-words');
  });
});
