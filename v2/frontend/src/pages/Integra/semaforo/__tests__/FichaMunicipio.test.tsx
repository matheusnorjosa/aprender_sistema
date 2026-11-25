/**
 * Semáforo — Ficha do município (DADOS SIMULADOS): os 5 indicadores do ciclo com valor, limite e cor, o
 * histórico dos 6 ciclos fechados, as tarefas com o prazo (no prazo / vence hoje / vencida), as
 * ocorrências e as reuniões de escuta.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { definirLarguraTela } from '../../../../test/larguraTela';
import { QUEM_VE } from '../../quemVe';
import { gerarDadosSemaforo, HISTORIAS_SEMAFORO } from '../dados';
import { renderTelaSemaforo } from './telaSemaforo';

const DADOS = gerarDadosSemaforo();
const idDe = (h: { nome: string; uf: string }): number => DADOS.municipios.find((m) => m.nome === h.nome && m.uf === h.uf)!.id;
const HORIZONTE = `/integra/semaforo/municipio/${idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje)}`;

async function abrir(rota: string, dados = DADOS): Promise<void> {
  renderTelaSemaforo(rota, dados);
  await screen.findByText('Ficha do município');
}

function linhas(nomeDaTabela: string | RegExp): string[] {
  const tabela = screen.getByRole('table', { name: nomeDaTabela });
  return within(tabela)
    .getAllByRole('row')
    .slice(1)
    .map((l) => l.textContent ?? '');
}

describe('Ficha do município', { timeout: 20000 }, () => {
  test('quem responde pelo município, a cor em vigor, a sugerida e a mudança', async () => {
    await abrir(HORIZONTE);
    expect(screen.getByText(QUEM_VE.municipio.aviso)).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Horizonte-CE' })).toBeInTheDocument();
    const situacao = screen.getByRole('list', { name: 'Situação atual' });
    expect(situacao).toHaveTextContent('Em vigor: Vermelho');
    expect(situacao).toHaveTextContent('publicada em 02/12/2026');
    expect(situacao).toHaveTextContent('Sugerida agora: Vermelho');
    expect(situacao).toHaveTextContent('▲ Piorou: era amarelo');
    // O ciclo vem com os meses: no ICA, "2026.2" é semestre.
    expect(situacao).toHaveTextContent('publicada em 02/12/2026 (ciclo 2026.6, novembro e dezembro de 2026)');
    expect(situacao).toHaveTextContent('Sugerida agora: Vermelho (ciclo 2026.6, novembro e dezembro de 2026)');
    expect(situacao).toHaveTextContent('Desde o ciclo 2026.5 (setembro e outubro de 2026)');
    expect(screen.getByText(/Gestora de referência:/)).toHaveTextContent(DADOS.pessoas.find((p) => p.id === DADOS.municipios.find((m) => m.nome === 'Horizonte')!.gestora_referencia)!.nome);
  });

  test('os 5 indicadores do ciclo atual com valor, cor escrita e limites', async () => {
    await abrir(HORIZONTE);
    const indicadores = linhas(/Indicadores do ciclo 2026\.6/);
    expect(indicadores).toHaveLength(5);
    expect(indicadores[0]).toMatch(/Média da pesquisa do articulador.*4,5.*Verde/);
    expect(indicadores[3]).toMatch(/Ocorrências via Relacionamento ou distribuidor.*1 reclamação.*Vermelho/);
    expect(indicadores[0]).toMatch(/4,0 ou mais.*3,0 a 3,9.*abaixo de 3,0/);
  });

  test('histórico dos 6 ciclos fechados, com a seta de mudança', async () => {
    await abrir(HORIZONTE);
    const historico = linhas(/Histórico dos 6 ciclos/);
    expect(historico).toHaveLength(6);
    expect(historico[0]).toMatch(/^2025\.6 \(nov–dez 2025\)/);
    expect(screen.getByRole('heading', { level: 3, name: 'Indicadores do ciclo 2026.6 (novembro e dezembro de 2026)' })).toBeInTheDocument();
    expect(historico[5]).toMatch(/2026\.5.*Amarelo.*Amarelo.*Piorou: era verde/);
  });

  test('tarefas: vence hoje primeiro, depois no prazo, e as concluídas com a data', async () => {
    await abrir(HORIZONTE);
    const tarefas = linhas(/Tarefas e prazos/);
    expect(tarefas[0]).toMatch(/Reunião com a Secretaria.*07\/12\/2026.*Vence hoje/);
    expect(tarefas[1]).toMatch(/Plano de ação pactuado.*17\/12\/2026.*No prazo/);
    expect(tarefas.find((t) => t.includes('Contato com o município'))).toMatch(/Concluída em 03\/12\/2026/);
  });

  test('ocorrências e reuniões de escuta', async () => {
    await abrir(HORIZONTE);
    // O mesmo nome da origem que o formulário usa (Relatório mensal), sem o nome interno "Fluxo único".
    expect(linhas(/Ocorrências/)).toEqual([expect.stringMatching(/01\/12\/2026.*Reclamação.*Relacionamento, Comercial ou distribuidor/)]);
    expect(screen.queryByText(/Fluxo único/)).not.toBeInTheDocument();
    const reunioes = linhas(/Reuniões de escuta/);
    expect(reunioes).toHaveLength(3);
    expect(reunioes[0]).toMatch(/27\/11\/2026.*Trimestral/);
  });

  test('tarefa com o prazo passado e em aberto aparece como vencida', async () => {
    await abrir(HORIZONTE, { ...DADOS, data_referencia: '2026-12-08' });
    expect(linhas(/Tarefas e prazos/)[0]).toMatch(/Reunião com a Secretaria.*Vencida/);
  });

  test('a cor que o Comitê alterou aparece com a justificativa', async () => {
    await abrir(`/integra/semaforo/municipio/${idDe(HISTORIAS_SEMAFORO.alterada_pelo_comite)}`);
    expect(linhas(/Histórico dos 6 ciclos/)[5]).toMatch(/2026\.5.*Amarelo.*Verde.*pedido de material/);
  });

  test('município sem coordenador: sem relatório mensal, o cronograma fica sem dado', async () => {
    await abrir(`/integra/semaforo/municipio/${DADOS.municipios.find((m) => m.coordenador === null)!.id}`);
    expect(screen.getByRole('heading', { level: 2, name: 'Itaquiraí-MS' })).toBeInTheDocument();
    expect(screen.getByText(/Sem coordenador/)).toBeInTheDocument();
    expect(linhas(/Indicadores do ciclo/)[2]).toMatch(/Cronograma cumprido.*Sem dado/);
  });

  test('no celular (400 px), as colunas que não cabem vão para o detalhe da linha', async () => {
    definirLarguraTela(400);
    await abrir(HORIZONTE);
    const historico = screen.getByRole('table', { name: /Histórico dos 6 ciclos/ });
    expect(within(historico).getAllByRole('columnheader').map((c) => c.textContent?.trim())).toEqual([
      'Detalhes',
      'Ciclo',
      'Sugerida',
      'Publicada',
    ]);
    expect(within(historico).getByRole('button', { name: 'Expandir linha de ciclo 2026.5' })).toBeInTheDocument();
  });

  test('a 360 px, as larguras fixas das tabelas cabem nos 312 px úteis (sem rolagem dentro da tabela)', async () => {
    // 360 px menos o p-6 da moldura da Integra (2 × 24 px). Com `table-layout: fixed`, a tabela fica pelo menos
    // com a soma das larguras fixas; passando disso, rola para o lado dentro do próprio contêiner.
    definirLarguraTela(360);
    await abrir(HORIZONTE);
    for (const tabela of screen.getAllByRole('table')) {
      const fixas = [...tabela.querySelectorAll('colgroup col')].reduce((soma, col) => soma + (parseFloat((col as HTMLElement).style.width) || 0), 0);
      expect(fixas, tabela.querySelector('caption')?.textContent ?? '').toBeLessThanOrEqual(312);
    }
  });

  test('município que não existe: avisa e volta ao Comitê', async () => {
    await abrir('/integra/semaforo/municipio/99999');
    expect(screen.getByText('Município não encontrado.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Voltar ao Comitê' })).toHaveAttribute('href', '/integra/semaforo/comite');
  });
});

/** A ficha abre de seis telas; o link de volta leva à tela de onde ela foi aberta, com o endereço completo. */
describe('Ficha do município: voltar para a tela de origem', { timeout: 20000 }, () => {
  const GESTORA = DADOS.municipios.find((m) => m.id === idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje))!.gestora_referencia;
  const ORIGENS: readonly [string, string, boolean][] = [
    ['/integra/semaforo', 'Voltar ao início do Semáforo', false],
    ['/integra/semaforo/comite', 'Voltar ao Comitê', false],
    [`/integra/semaforo/gestora?gestora=${GESTORA}`, 'Voltar ao painel da gestora', false],
    ['/integra/semaforo/pesquisa', 'Voltar à pesquisa do articulador', true],
    ['/integra/semaforo/lider', 'Voltar aos indicadores da Líder', false],
    ['/integra/semaforo/relatorio-mensal', 'Voltar ao relatório mensal', true],
  ];

  test.each(ORIGENS)('aberta de %s: "%s"', async (origem, rotulo, escolherMunicipio) => {
    const user = userEvent.setup();
    renderTelaSemaforo(origem, DADOS);
    if (escolherMunicipio) await user.selectOptions(await screen.findByLabelText('Município'), String(idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje)));
    const links = await screen.findAllByRole('link');
    const daFicha = links.find((l) => /^\/integra\/semaforo\/municipio\/\d+$/.test(l.getAttribute('href') ?? ''));
    expect(daFicha, 'a tela não tem link para a ficha').toBeDefined();
    await user.click(daFicha!);
    await screen.findByText('Ficha do município');
    const voltar = screen.getAllByRole('link', { name: rotulo });
    expect(voltar.length).toBeGreaterThan(0);
    for (const v of voltar) expect(v).toHaveAttribute('href', origem);
    if (rotulo !== 'Voltar ao Comitê') expect(screen.queryByRole('link', { name: 'Voltar ao Comitê' })).toBeNull();
  });

  test('aberta direto pelo endereço (sem origem): volta ao Comitê', async () => {
    await abrir(HORIZONTE);
    for (const v of screen.getAllByRole('link', { name: 'Voltar ao Comitê' })) expect(v).toHaveAttribute('href', '/integra/semaforo/comite');
  });
});
