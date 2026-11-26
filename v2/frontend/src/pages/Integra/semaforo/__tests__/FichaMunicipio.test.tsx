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
import { avaliarMunicipio, gerarDadosSemaforo, HISTORIAS_SEMAFORO } from '../dados';
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
    // Horizonte ainda não respondeu a pesquisa do ciclo (sem dado); o cronograma aparece com 2 casas (decisão 30).
    expect(indicadores[0]).toMatch(/Média da pesquisa do articulador.*Sem dado/);
    expect(indicadores[2]).toMatch(/Cronograma cumprido.*\d+,\d\d%.*Verde/);
    expect(indicadores[3]).toMatch(/Ocorrências via Relacionamento ou distribuidor.*1 reclamação.*Vermelho/);
    expect(indicadores[0]).toMatch(/4,0 ou mais.*3,0 a menos de 4,0.*menos de 3,0/);
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
    // Decisões 33 e 34: dias úteis contados do vermelho na hora (30/11).
    expect(tarefas[1]).toMatch(/Plano de ação pactuado.*21\/12\/2026.*No prazo/);
    expect(tarefas.find((t) => t.includes('Contato com o articulador municipal'))).toMatch(/Concluída em 01\/12\/2026/);
  });

  test('ocorrências e reuniões de escuta', async () => {
    await abrir(HORIZONTE);
    // O mesmo nome da origem que o formulário usa (Relatório mensal), sem o nome interno "Fluxo único".
    // Decisão 50: a hora do registro e quando foi respondida (54 h: fora da meta de 48 h).
    expect(linhas(/Ocorrências de 2026/)).toEqual([
      expect.stringMatching(/30\/11\/2026 às 10:15.*Reclamação.*Relacionamento, Comercial ou distribuidor.*02\/12\/2026 às 16:15, em 54 h: fora da meta de 48 h.*Sim/),
    ]);
    expect(screen.queryByText(/Fluxo único/)).not.toBeInTheDocument();
    const reunioes = linhas(/Reuniões de escuta/);
    // A de 04/12 ainda está com a ata por registrar (decisão 48): prazo de 5 dias úteis, até 11/12.
    // Rodada 4: uma reunião por vez; a trimestral de 27/11 (do amarelo) saiu, e fica só a de depois da reclamação.
    expect(reunioes).toHaveLength(3);
    expect(reunioes[0]).toMatch(/04\/12\/2026.*Trimestral.*Ata a registrar até 11\/12\/2026/);
    expect(reunioes[1]).toMatch(/14\/09\/2026.*Semestral.*Ata registrada em/);
  });

  test('decisão 48: reunião sem ata passado o prazo aparece como ata atrasada', async () => {
    await abrir(`/integra/semaforo/municipio/${idDe(HISTORIAS_SEMAFORO.em_recuperacao)}`);
    expect(linhas(/Reuniões de escuta/)[0]).toMatch(/27\/11\/2026.*Ata atrasada: o prazo era 04\/12\/2026/);
  });

  test('decisões 32 e 57: as ocorrências por ano; o ano anterior não conta na cor, mas fica guardado', async () => {
    const antiga = DADOS.ocorrencias.find((o) => o.data < '2026-01-01')!;
    await abrir(`/integra/semaforo/municipio/${antiga.municipio}`);
    const secao = screen.getByRole('region', { name: 'Ocorrências' });
    // Rodada 4 (WCAG 2.4.6): o título do ano diz que é de ocorrências; a região herda o nome.
    expect(within(secao).getByRole('heading', { level: 4, name: 'Ocorrências de 2025' })).toBeInTheDocument();
    expect(within(secao).getByRole('region', { name: 'Ocorrências de 2025' })).toBeInTheDocument();
    expect(secao).toHaveTextContent('Ano anterior: não conta mais na cor; fica guardado no histórico.');
    expect(linhas(/Ocorrências de 2025/)).toEqual([expect.stringMatching(new RegExp(`${antiga.data.split('-').reverse().join('/')}.*Não`))]);
  });

  test('decisão 32: no ano atual, a ficha diz desde quando as ocorrências contam', async () => {
    await abrir(HORIZONTE);
    expect(screen.getByRole('region', { name: 'Ocorrências' })).toHaveTextContent(
      /Contam na cor desde 01\/\d\d\/2026, o mês da 1ª formação do ano no município\./,
    );
  });

  test('decisões 46 e 51: cada projeto com o seu coordenador, articulador, cronograma e cor', async () => {
    const sobral = DADOS.municipios.find((m) => m.id === idDe(HISTORIAS_SEMAFORO.em_recuperacao))!;
    expect(sobral.projetos.length).toBeGreaterThan(1);
    await abrir(`/integra/semaforo/municipio/${sobral.id}`);
    const projetos = within(screen.getByRole('list', { name: 'Projetos de Sobral-CE' })).getAllByRole('listitem');
    expect(projetos).toHaveLength(sobral.projetos.length);
    sobral.projetos.forEach((p, i) => {
      const coordenador = DADOS.coordenadores.find((c) => c.id === p.coordenador)!.nome;
      expect(projetos[i]).toHaveTextContent(p.nome);
      expect(projetos[i]).toHaveTextContent(`Coordenador: ${coordenador}`);
      expect(projetos[i]).toHaveTextContent(`Quem responde a pesquisa: ${p.articulador}`);
      expect(projetos[i]).toHaveTextContent(/Cronograma cumprido: (\d+,\d\d% · (Verde|Amarelo|Vermelho)|Sem dado)/);
    });
    expect(screen.getByText(/na cor do município entra o pior projeto/)).toBeInTheDocument();
  });

  test('decisão 31: a nota de recomendação mostra a maior, a menor e a média', async () => {
    await abrir(`/integra/semaforo/municipio/${idDe(HISTORIAS_SEMAFORO.em_recuperacao)}`);
    expect(linhas(/Indicadores do ciclo 2026\.6/)[1]).toMatch(/Nota NPS do articulador.*Maior \d+, menor \d+, média \d+,\d\d/);
  });

  test('decisões 43 e 57: a tarefa substituída fica na lista, com o estado e a data', async () => {
    const id = DADOS.tarefas.find((t) => t.encerramento?.motivo === 'substituida')!.municipio;
    await abrir(`/integra/semaforo/municipio/${id}`);
    expect(linhas(/Tarefas e prazos/).some((t) => /Substituída em \d\d\/\d\d\/\d{4}/.test(t))).toBe(true);
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
    // Decisão 46: o projeto é que tem coordenador.
    expect(screen.getByText(/Sem coordenador: o relatório mensal deste projeto não chega/)).toBeInTheDocument();
    expect(linhas(/Indicadores do ciclo/)[2]).toMatch(/Cronograma cumprido.*Sem dado/);
  });

  test('rodada 4: Itaquiraí-MS não mostra cor nos ciclos de antes do projeto (começou em 2026.4)', async () => {
    await abrir(`/integra/semaforo/municipio/${DADOS.municipios.find((m) => m.coordenador === null)!.id}`);
    const historico = linhas(/Histórico dos 2 ciclos/);
    expect(historico.map((l) => l.slice(0, 6))).toEqual(['2026.4', '2026.5']);
    expect(historico.join(' ')).not.toMatch(/Vermelho/);
    expect(screen.getByRole('heading', { level: 3, name: 'Histórico dos 2 ciclos' })).toBeInTheDocument();
    expect(screen.getByText(/O projeto do município começou no ciclo 2026\.4/)).toHaveTextContent(
      'O projeto do município começou no ciclo 2026.4 (julho e agosto de 2026): os 4 ciclos de antes não têm coleta nem cor.',
    );
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

  test('no celular, cada tarefa e cada ocorrência tem o botão de expandir com nome próprio (decisões 43, 50 e 57)', async () => {
    definirLarguraTela(400);
    // A tarefa substituída fica na lista ao lado da nova, com o mesmo título: o nome do botão diz o prazo.
    const id = DADOS.tarefas.find((t) => t.encerramento?.motivo === 'substituida')!.municipio;
    await abrir(`/integra/semaforo/municipio/${id}`);
    const tarefas = screen.getByRole('table', { name: /Tarefas e prazos/ });
    const nomes = within(tarefas)
      .getAllByRole('button', { name: /^Expandir linha de / })
      .map((b) => b.getAttribute('aria-label'));
    expect(nomes.length).toBeGreaterThan(1);
    expect(new Set(nomes).size).toBe(nomes.length);
  });

  test('no celular, o botão de expandir da ocorrência diz o dia e a hora do registro (decisão 50)', async () => {
    definirLarguraTela(400);
    await abrir(HORIZONTE);
    const ocorrencias = screen.getByRole('table', { name: /Ocorrências de 2026/ });
    expect(within(ocorrencias).getByRole('button', { name: 'Expandir linha de ocorrência de 30/11/2026 às 10:15' })).toBeInTheDocument();
  });

  test('decisão 57: o vermelho na hora que o Comitê desfez continua visível, com todas as decisões em ordem', async () => {
    const id = idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    // A história: vermelho na hora em 30/11, confirmado pelo extraordinário em 02/12. Aqui, o extraordinário desfez.
    const ultima = DADOS.decisoes.filter((d) => d.municipio === id).at(-1)!;
    const DESFEITO = {
      ...DADOS,
      decisoes: DADOS.decisoes.map((d) =>
        d === ultima ? { ...d, cor_publicada: 'amarelo' as const, justificativa: 'A reclamação foi resolvida.' } : d,
      ),
    };
    await abrir(HORIZONTE, DESFEITO);
    const itens = within(screen.getByRole('list', { name: 'Todas as decisões, em ordem' }))
      .getAllByRole('listitem')
      .map((li) => li.textContent ?? '');
    expect(itens).toHaveLength(DADOS.decisoes.filter((d) => d.municipio === id).length);
    expect(itens.at(-2)).toMatch(/^30\/11\/2026 · ciclo 2026\.6.*Vermelho.*vermelho na hora/);
    expect(itens.at(-1)).toMatch(
      /^02\/12\/2026 · ciclo 2026\.6.*Amarelo.*Comitê extraordinário, desfez o vermelho na hora.*Justificativa: A reclamação foi resolvida\./,
    );
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

  test('decisão 38: com o vermelho na hora em vigor, a ficha diz que o Comitê ainda confirma ou desfaz (e não "publicada em")', async () => {
    // Horizonte-CE antes do extraordinário de 02/12: o vermelho na hora de 30/11 ainda espera o Comitê.
    const id = idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const extraordinario = DADOS.decisoes.filter((d) => d.municipio === id).at(-1)!;
    const SEM_COMITE = { ...DADOS, decisoes: DADOS.decisoes.filter((d) => d !== extraordinario) };
    expect(avaliarMunicipio(SEM_COMITE, id).aguardando_comite).toBe(true);
    await abrir(HORIZONTE, SEM_COMITE);
    const situacao = screen.getByRole('list', { name: 'Situação atual' });
    expect(situacao).toHaveTextContent(
      'Em vigor: Vermelho na hora desde 30/11/2026 (ciclo 2026.6, novembro e dezembro de 2026): as tarefas do vermelho começaram; o Comitê confirma ou desfaz.',
    );
    expect(situacao).not.toHaveTextContent('publicada em');
  });

  test('a 360 px, a data da ocorrência cabe inteira: "Registrada em" fica com pelo menos 96 px, o dia e a hora em linhas separadas', async () => {
    definirLarguraTela(360);
    await abrir(HORIZONTE);
    const tabela = screen.getByRole('table', { name: /Ocorrências de 2026/ });
    const fixas = [...tabela.querySelectorAll('colgroup col')].reduce((soma, col) => soma + (parseFloat((col as HTMLElement).style.width) || 0), 0);
    expect(312 - fixas).toBeGreaterThanOrEqual(96);
    const linha = within(tabela).getAllByRole('row')[1]!;
    expect(within(linha).getByText('30/11/2026')).toHaveClass('block');
    expect(within(linha).getByText('às 10:15')).toHaveClass('block');
    // Decisão 50 (leitura para o dono): a meta conta horas corridas, com sábado e domingo.
    expect(screen.getByText(/A contagem zera em janeiro/)).toHaveTextContent('A resposta ao município tem a meta de 48 h corridas (sábado e domingo contam).');
  });

  test('decisões 42, 43 e 57 (rodada 3): a 360 px, a coluna Situação tem largura fixa para a etiqueta com a data', async () => {
    // Medido no Chromium a 360 px: "Substituída em 06/03/2026" e "Concluída em 24/09/2026" pedem 88 px (a data
    // inteira, 74 px, mais a borda e a margem da etiqueta) e vazavam a célula automática de 96 px (80 px úteis).
    // Rodada 4: abaixo de 576 px, o Prazo sai da linha (vai para a célula da tarefa e para o detalhe), e a Tarefa
    // fica com o espaço: só sobram a coluna de expandir (40) e a Situação (104).
    definirLarguraTela(360);
    await abrir(HORIZONTE);
    const tabela = screen.getByRole('table', { name: /Tarefas e prazos/ });
    const larguras = [...tabela.querySelectorAll('colgroup col')]
      .map((col) => parseFloat((col as HTMLElement).style.width) || 0)
      .filter((w) => w > 0)
      .sort((a, b) => a - b);
    expect(larguras).toEqual([40, 104]);
  });

  test('rodada 4: a 360 px, o nome da tarefa e o do indicador cabem sem quebrar a palavra no meio', async () => {
    // A palavra mais longa a 14 px: "Relacionamento" (cerca de 105 px) no indicador, "Observação" (cerca de 76 px) na
    // tarefa; mais 16 px do espaço interno da célula. Cada tabela tem uma só coluna automática a 360 px.
    definirLarguraTela(360);
    await abrir(HORIZONTE);
    const livre = (nome: RegExp): number => {
      const tabela = screen.getByRole('table', { name: nome });
      return 312 - [...tabela.querySelectorAll('colgroup col')].reduce((soma, col) => soma + (parseFloat((col as HTMLElement).style.width) || 0), 0);
    };
    expect(livre(/Tarefas e prazos/)).toBeGreaterThanOrEqual(76 + 16);
    expect(livre(/Indicadores do ciclo/)).toBeGreaterThanOrEqual(105 + 16);
    const indicadores = screen.getByRole('table', { name: /Indicadores do ciclo/ });
    expect(within(indicadores).getAllByRole('columnheader').map((c) => c.textContent?.trim())).toEqual(['Detalhes', 'Indicador', 'Cor']);
    // O prazo e o valor continuam na linha, na célula do nome (só abaixo de 576 px).
    expect(linhas(/Tarefas e prazos/)[0]).toMatch(/Reunião com a Secretaria\s*Prazo: 07\/12\/2026/);
    expect(linhas(/Indicadores do ciclo/)[3]).toMatch(/Ocorrências via Relacionamento ou distribuidor\s*Valor: 1 reclamação/);
  });

  test('decisões 48 e 50 (rodada 3): a queixa do momento reservado mostra o dia do registro da ata e o dia da reunião', async () => {
    const id = idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const COM_QUEIXA = {
      ...DADOS,
      ocorrencias: [
        ...DADOS.ocorrencias,
        {
          id: 9101,
          municipio: id,
          data: '2026-12-01',
          registrada_em: '2026-12-04T15:20:00-03:00',
          respondida_em: null,
          origem: 'momento_reservado' as const,
          tipo: 'leve' as const,
        },
      ],
    };
    await abrir(HORIZONTE, COM_QUEIXA);
    const linha = linhas(/Ocorrências de 2026/).find((l) => l.includes('às 15:20'))!;
    expect(linha).toMatch(/^04\/12\/2026 às 15:20 feita em 01\/12\/2026/);
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
