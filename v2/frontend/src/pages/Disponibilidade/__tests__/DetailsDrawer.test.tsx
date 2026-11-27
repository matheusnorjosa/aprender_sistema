/**
 * Detalhe da célula da Grade Mensal (ensaio r3, 28/10/2026): a data do evento aparece como
 * dd/mm/aaaa, como no resto do sistema, e não no formato do servidor (2026-12-07). O servidor já
 * manda o dia de Fortaleza; a tela só troca o formato, sem converter fuso.
 */
import { useState } from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';

import DetailsDrawer from '../DetailsDrawer';

describe('DetailsDrawer', () => {
  test('mostra a data do evento como dd/mm/aaaa', () => {
    render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={{ id: 1, name: 'Maria' }}
        day={7}
        details={[{ id: 9, municipio: 'Crato', tipo: 'Formação', data: '2026-12-07', inicio: '08:00', fim: '12:00' }]}
      />,
    );

    expect(screen.getByText('07/12/2026')).toBeInTheDocument();
    expect(screen.queryByText('2026-12-07')).not.toBeInTheDocument();
  });

  // C4 (sem rolagem horizontal): a tabela de 5 colunas rolava dentro do painel no celular.
  test('cada evento é um cartão da lista, sem tabela nem rolagem interna', () => {
    const { container } = render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={{ id: 1, name: 'Maria', email: 'maria.aparecida.da.conceicao@exemplo.invalid' }}
        day={7}
        details={[
          { id: 9, municipio: 'Crato', tipo: 'Formação', data: '2026-12-07', inicio: '08:00', fim: '12:00' },
          { id: 10, municipio: 'Juazeiro do Norte', tipo: 'Acompanhamento', data: '2026-12-07', inicio: '13:00', fim: '17:00' },
        ]}
      />,
    );

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(container.querySelector('.overflow-x-auto')).toBeNull();
    const eventos = screen.getAllByRole('listitem');
    expect(eventos).toHaveLength(2);
    expect(within(eventos[1] as HTMLElement).getByText('Juazeiro do Norte')).toBeInTheDocument();
    expect(within(eventos[1] as HTMLElement).getByText('Acompanhamento')).toBeInTheDocument();
    expect(within(eventos[1] as HTMLElement).getByText('13:00')).toBeInTheDocument();
    for (const rotulo of ['Tipo', 'Data', 'Início', 'Fim']) {
      expect(within(eventos[0] as HTMLElement).getByText(rotulo)).toBeInTheDocument();
    }
  });
});

/**
 * Grade mensal enxuta (27/11/2026): todo código abre a gaveta. No modo dia, um cartão por item
 * (evento, deslocamento, bloqueio); no modo pessoa (clique no nome), o mês dela. O motivo do
 * bloqueio pode ser pessoal: nunca aparece (o servidor nem manda; a tela também não mostra).
 */
describe('DetailsDrawer — modo dia, por tipo de item', () => {
  const pessoa = { id: 1, name: 'Maria', ch_month: 4.5, ch_year: 12, position_month: 2 };

  test('deslocamento: origem → destino, a data e o meio de transporte', () => {
    render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={pessoa}
        day={10}
        details={[
          { tipo_item: 'deslocamento', id: 54, origem: 'Fortaleza', destino: 'Sobral', inicio: '2025-10-10', fim: '2025-10-11', meio_transporte: 'Ônibus' },
        ]}
      />,
    );

    const cartao = screen.getByRole('listitem');
    expect(within(cartao).getByText('Fortaleza → Sobral')).toBeInTheDocument();
    expect(within(cartao).getByText('10/10/2025 a 11/10/2025')).toBeInTheDocument();
    expect(within(cartao).getByText('Ônibus')).toBeInTheDocument();
  });

  test('bloqueio parcial e total: o tipo e o horário, sem o motivo', () => {
    render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={pessoa}
        day={4}
        details={[
          // Mesmo que um motivo chegasse, a tela não o mostra.
          { tipo_item: 'bloqueio', id: 77, tipo: 'Parcial', data_inicio: '2025-10-04', data_fim: '2025-10-04', inicio: '14:00', fim: '18:00', motivo: 'Consulta médica' } as never,
          { tipo_item: 'bloqueio', id: 78, tipo: 'Total', inicio: '00:00', fim: '23:59' },
        ]}
      />,
    );

    const [parcial, total] = screen.getAllByRole('listitem') as [HTMLElement, HTMLElement];
    expect(within(parcial).getByText('Bloqueio parcial')).toBeInTheDocument();
    expect(within(parcial).getByText('14:00')).toBeInTheDocument();
    expect(within(parcial).getByText('18:00')).toBeInTheDocument();
    // No mesmo dia, só o horário: a data já é a do dia aberto.
    expect(within(parcial).queryByText(/04\/10\/2025/)).not.toBeInTheDocument();
    expect(within(total).getByText('Bloqueio total')).toBeInTheDocument();
    expect(screen.queryByText(/Consulta médica/)).not.toBeInTheDocument();
    expect(screen.queryByText(/motivo/i)).not.toBeInTheDocument();
  });

  // Bloqueio de 10/11 08:00 a 12/11 17:00 aberto no dia 11: "Início 08:00 Fim 17:00" enganaria.
  test('bloqueio de vários dias: data e hora do começo e do fim', () => {
    render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={pessoa}
        day={11}
        details={[
          { tipo_item: 'bloqueio', id: 79, tipo: 'Total', data_inicio: '2025-11-10', data_fim: '2025-11-12', inicio: '08:00', fim: '17:00' },
        ]}
      />,
    );

    const cartao = screen.getByRole('listitem');
    expect(within(cartao).getByText('Bloqueio total')).toBeInTheDocument();
    expect(within(cartao).getByText('10/11/2025 08:00 a 12/11/2025 17:00')).toBeInTheDocument();
    expect(within(cartao).queryByText('08:00')).not.toBeInTheDocument();
  });

  test('X: o evento e o bloqueio do dia, nessa ordem; item sem tipo_item conta como evento', () => {
    render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={pessoa}
        day={15}
        details={[
          { id: 456, municipio: 'Sobral', data: '2025-10-15', inicio: '08:00', fim: '12:00', tipo: 'Formação' },
          { tipo_item: 'bloqueio', id: 78, tipo: 'Total', inicio: '14:00', fim: '18:00' },
        ]}
      />,
    );

    const [evento, bloqueio] = screen.getAllByRole('listitem') as [HTMLElement, HTMLElement];
    expect(within(evento).getByText('Sobral')).toBeInTheDocument();
    expect(within(evento).getByText('15/10/2025')).toBeInTheDocument();
    expect(within(bloqueio).getByText('Bloqueio total')).toBeInTheDocument();
  });
});

describe('DetailsDrawer — modo pessoa (o mês dela)', () => {
  const pessoa = { id: 1, name: 'Maria', ch_month: 4.5, ch_year: 12, position_month: 2 };

  test('CH do mês e do ano no formato brasileiro, posição no mês e as listas do mês, sem repetir id', () => {
    render(
      <DetailsDrawer
        open
        onClose={vi.fn()}
        person={pessoa}
        day={null}
        modo="pessoa"
        details={[
          { tipo_item: 'evento', id: 9, municipio: 'Crato', tipo: 'Formação', data: '2026-01-05', inicio: '08:00', fim: '12:00' },
          { tipo_item: 'deslocamento', id: 54, origem: 'Fortaleza', destino: 'Crato', inicio: '2026-01-04', fim: '2026-01-04', meio_transporte: '' },
          // O mesmo evento e o mesmo deslocamento em outro dia do mês: aparecem uma vez só.
          { tipo_item: 'evento', id: 9, municipio: 'Crato', tipo: 'Formação', data: '2026-01-05', inicio: '08:00', fim: '12:00' },
          { tipo_item: 'deslocamento', id: 54, origem: 'Fortaleza', destino: 'Crato', inicio: '2026-01-04', fim: '2026-01-04', meio_transporte: '' },
          { id: 10, municipio: 'Barbalha', tipo: 'Acompanhamento', data: '2026-01-06', inicio: '13:00', fim: '17:00' },
          { tipo_item: 'bloqueio', id: 77, tipo: 'Parcial', inicio: '14:00', fim: '18:00' },
        ]}
      />,
    );

    expect(screen.getByRole('heading', { level: 2, name: 'Mês de Maria' })).toBeInTheDocument();
    expect(screen.getByText('4,5h')).toBeInTheDocument();
    expect(screen.getByText('12h')).toBeInTheDocument();
    expect(screen.getByText('Posição no mês')).toBeInTheDocument();

    const eventos = within(screen.getByRole('region', { name: 'Eventos do mês' })).getAllByRole('listitem');
    expect(eventos).toHaveLength(2);
    // Uma linha por evento, como a planilha: "05/01 · início–fim" e "Município · Tipo".
    expect(eventos[0]).toHaveTextContent('05/01');
    expect(eventos[0]).toHaveTextContent('Crato');
    expect(eventos[1]).toHaveTextContent('Barbalha');

    const deslocamentos = within(screen.getByRole('region', { name: 'Deslocamentos do mês' })).getAllByRole('listitem');
    expect(deslocamentos).toHaveLength(1);
    expect(within(deslocamentos[0] as HTMLElement).getByText('Fortaleza → Crato')).toBeInTheDocument();
    expect(within(deslocamentos[0] as HTMLElement).getByText('04/01/2026')).toBeInTheDocument();

    // O bloqueio não entra no mês da pessoa.
    expect(screen.queryByText(/Bloqueio/)).not.toBeInTheDocument();
  });

  // 2ª revisão do PR 8: a CH é de todos os projetos (a mesma do painel de Equipe), mas as listas
  // vêm da grade, que segue o filtro Projeto. Sem o aviso, os números e a lista parecem não bater.
  test('com o filtro Projeto, avisa que as horas são de todos os projetos', () => {
    render(<DetailsDrawer open onClose={vi.fn()} person={pessoa} day={null} modo="pessoa" details={[]} filtroProjeto="Superativar" />);

    expect(screen.getByText('Horas de todos os projetos; a lista mostra só o projeto filtrado.')).toBeInTheDocument();
  });

  test('sem o filtro Projeto, e no modo dia, não há aviso', () => {
    const { unmount } = render(
      <DetailsDrawer open onClose={vi.fn()} person={pessoa} day={null} modo="pessoa" details={[]} filtroProjeto="  " />,
    );
    expect(screen.queryByText(/Horas de todos os projetos/)).not.toBeInTheDocument();
    unmount();

    render(<DetailsDrawer open onClose={vi.fn()} person={pessoa} day={7} details={[]} filtroProjeto="Superativar" />);
    expect(screen.queryByText(/Horas de todos os projetos/)).not.toBeInTheDocument();
  });

  test('mês sem nada: uma frase simples', () => {
    render(<DetailsDrawer open onClose={vi.fn()} person={pessoa} day={null} modo="pessoa" details={[]} />);

    expect(screen.getByText('Nada neste mês.')).toBeInTheDocument();
    expect(screen.queryByRole('listitem')).not.toBeInTheDocument();
  });
});

/**
 * A gaveta é um diálogo (WCAG 2.1.2, 2.4.3, 4.1.2): leitor de tela anuncia o título, o foco vai para
 * "Fechar" ao abrir, Esc fecha e o foco volta para o botão que a abriu.
 */
describe('DetailsDrawer — diálogo e foco', () => {
  const pessoa = { id: 1, name: 'Maria' };

  test('é um diálogo modal com o nome do título, e o foco começa no Fechar', () => {
    render(<DetailsDrawer open onClose={vi.fn()} person={pessoa} day={7} details={[]} />);

    const dialogo = screen.getByRole('dialog', { name: 'Detalhes: Maria - Dia 7' });
    expect(dialogo).toHaveAttribute('aria-modal', 'true');
    expect(within(dialogo).getByRole('button', { name: 'Fechar' })).toHaveFocus();
  });

  // 2ª revisão do PR 8: aria-modal promete que o foco não sai; o Tab saía para a página atrás.
  test('Tab e Shift+Tab não saem da gaveta, e o fundo escuro não entra na tabulação', async () => {
    const usuario = userEvent.setup();
    render(
      <>
        <button type="button">Antes da gaveta</button>
        <DetailsDrawer open onClose={vi.fn()} person={pessoa} day={7} details={[]} />
        <button type="button">Depois da gaveta</button>
      </>,
    );
    const fechar = screen.getByRole('button', { name: 'Fechar' });
    expect(fechar).toHaveFocus();

    await usuario.tab();
    expect(fechar).toHaveFocus();
    await usuario.tab({ shift: true });
    expect(fechar).toHaveFocus();
    expect(screen.queryByRole('button', { name: 'Fechar detalhes' })).not.toBeInTheDocument();
  });

  // 3ª revisão: outro diálogo aberto por cima (Dar feedback, aviso de sessão) fica com o Tab e o Esc.
  test('outro diálogo por cima fica com o Tab e o Esc', async () => {
    const usuario = userEvent.setup();
    const onClose = vi.fn();
    render(
      <>
        <DetailsDrawer open onClose={onClose} person={pessoa} day={7} details={[]} />
        <div role="dialog" aria-label="Dar feedback">
          <button type="button">Nota</button>
          <button type="button">Enviar</button>
        </div>
      </>,
    );
    screen.getByRole('button', { name: 'Nota' }).focus();

    await usuario.tab();
    expect(screen.getByRole('button', { name: 'Enviar' })).toHaveFocus();
    fireEvent.keyDown(document.activeElement as Element, { key: 'Escape' });
    expect(onClose).not.toHaveBeenCalled();
  });

  test('clicar no fundo escuro fecha', () => {
    const onClose = vi.fn();
    render(<DetailsDrawer open onClose={onClose} person={pessoa} day={7} details={[]} />);

    fireEvent.click(screen.getByRole('dialog').previousElementSibling as Element);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('Esc fecha', () => {
    const onClose = vi.fn();
    render(<DetailsDrawer open onClose={onClose} person={pessoa} day={7} details={[]} />);

    fireEvent.keyDown(document.activeElement as Element, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('ao fechar, o foco volta ao botão que abriu', () => {
    function Tela() {
      const [aberta, setAberta] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setAberta(true)}>Abrir dia 7</button>
          <DetailsDrawer open={aberta} onClose={() => setAberta(false)} person={pessoa} day={7} details={[]} />
        </>
      );
    }
    render(<Tela />);
    const origem = screen.getByRole('button', { name: 'Abrir dia 7' });
    origem.focus();

    fireEvent.click(origem);
    expect(screen.getByRole('button', { name: 'Fechar' })).toHaveFocus();
    fireEvent.keyDown(document.activeElement as Element, { key: 'Escape' });

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(origem).toHaveFocus();
  });
});
