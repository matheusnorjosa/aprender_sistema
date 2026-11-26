/**
 * Semáforo — Painel da gestora de referência (DADOS SIMULADOS): os municípios dela, as tarefas por prazo
 * e o que vence hoje primeiro.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { QUEM_VE } from '../../quemVe';
import { avaliarMunicipio, gerarDadosSemaforo, HISTORIAS_SEMAFORO } from '../dados';
import { estadoDaTarefa, reuniaoEmDia, tarefaAberta } from '../regras';
import { renderTelaSemaforo } from './telaSemaforo';

const DADOS = gerarDadosSemaforo();
const municipio = (h: { nome: string; uf: string }) => DADOS.municipios.find((m) => m.nome === h.nome && m.uf === h.uf)!;
const nomeDa = (id: number): string => DADOS.pessoas.find((p) => p.id === id)!.nome;

const HORIZONTE = municipio(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
const JEQUIE = municipio(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos);
/**
 * Uma gestora sem nenhuma tarefa em aberto na carteira. Com as decisões de 25/11 (ocorrências do ano todo, tarefas
 * reabertas) toda gestora do gerador tem alguma aberta: o teste tira as tarefas da carteira de uma delas.
 */
const SEM_TAREFAS = DADOS.pessoas.find((p) => p.id !== HORIZONTE.gestora_referencia)!;
const CARTEIRA_SEM_TAREFAS = new Set(DADOS.municipios.filter((m) => m.gestora_referencia === SEM_TAREFAS.id).map((m) => m.id));
const DADOS_SEM_TAREFAS = { ...DADOS, tarefas: DADOS.tarefas.filter((t) => !CARTEIRA_SEM_TAREFAS.has(t.municipio) || !tarefaAberta(t)) };

async function abrir(rota = '/integra/semaforo/gestora', dados = DADOS): Promise<void> {
  renderTelaSemaforo(rota, dados);
  await screen.findByText('Painel da gestora de referência');
}

const tarefasEm = (secao: string): string[] =>
  within(screen.getByRole('region', { name: secao }))
    .queryAllByRole('listitem')
    .map((i) => i.textContent ?? '');

describe('Painel da gestora de referência', { timeout: 20000 }, () => {
  test('abre na gestora que tem tarefa vencendo hoje, com o aviso de quem vê', async () => {
    await abrir();
    expect(screen.getByText(QUEM_VE.gestora.aviso)).toBeInTheDocument();
    const escolha = screen.getByLabelText('Gestora de referência');
    expect(escolha).toHaveValue(String(HORIZONTE.gestora_referencia));
    expect(within(escolha).getByRole('option', { selected: true })).toHaveTextContent(nomeDa(HORIZONTE.gestora_referencia));
  });

  test('o que vence hoje vem primeiro; depois as vencidas e as que estão no prazo', async () => {
    await abrir();
    const titulos = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(titulos.slice(0, 3)).toEqual(['Vence hoje', 'Vencidas', 'No prazo']);
    expect(tarefasEm('Vence hoje')).toEqual([expect.stringMatching(/Reunião com a Secretaria.*Horizonte-CE.*07\/12\/2026/)]);
    expect(tarefasEm('Vencidas')).toEqual([]);
    expect(within(screen.getByRole('region', { name: 'Vencidas' })).getByText('Nenhuma tarefa vencida.')).toBeInTheDocument();
    const noPrazo = tarefasEm('No prazo');
    expect(noPrazo.length).toBeGreaterThan(0);
    // Do prazo mais perto para o mais longe.
    // Decisão 33: 15 dias úteis desde o vermelho na hora (30/11).
    expect(noPrazo[0]).toMatch(/Plano de ação pactuado.*Horizonte-CE.*21\/12\/2026/);
  });

  test('rodada 3: a tarefa nascida do vermelho na hora diz isso, e não "quando a cor foi publicada"', async () => {
    await abrir();
    const [horizonte] = tarefasEm('Vence hoje');
    expect(horizonte).toContain('Criada em 30/11/2026, quando a cor mudou na hora.');
    expect(horizonte).not.toContain('quando a cor foi publicada');
  });

  test('os municípios da carteira, com a cor em vigor escrita e o link para a ficha', async () => {
    await abrir();
    const tabela = screen.getByRole('table', { name: /Municípios de/ });
    const linhas = within(tabela).getAllByRole('row').slice(1);
    expect(linhas).toHaveLength(DADOS.municipios.filter((m) => m.gestora_referencia === HORIZONTE.gestora_referencia).length);
    // O pior primeiro.
    expect(linhas[0]).toHaveTextContent(/Horizonte-CE.*Vermelho/);
    expect(within(linhas[0]!).getByRole('link', { name: 'Horizonte-CE' })).toHaveAttribute('href', `/integra/semaforo/municipio/${HORIZONTE.id}`);
  });

  test('trocar de gestora mostra a carteira dela; sem nada em aberto, diz isso', async () => {
    await abrir(undefined, DADOS_SEM_TAREFAS);
    await userEvent.selectOptions(screen.getByLabelText('Gestora de referência'), String(SEM_TAREFAS.id));
    expect(within(screen.getByRole('region', { name: 'Vence hoje' })).getByText('Nada vence hoje.')).toBeInTheDocument();
    expect(within(screen.getByRole('region', { name: 'No prazo' })).getByText('Nenhuma tarefa no prazo.')).toBeInTheDocument();
    expect(screen.getByRole('table', { name: `Municípios de ${SEM_TAREFAS.nome}` })).toBeInTheDocument();
  });

  test('a gestora pode vir no endereço (?gestora=)', async () => {
    await abrir(`/integra/semaforo/gestora?gestora=${JEQUIE.gestora_referencia}`);
    const tabela = screen.getByRole('table', { name: `Municípios de ${nomeDa(JEQUIE.gestora_referencia)}` });
    expect(within(tabela).getByRole('link', { name: 'Jequié-BA' })).toBeInTheDocument();
  });

  test('pendências da carteira (seção 7): pesquisas sem resposta no ciclo, reuniões de escuta a agendar e atas', async () => {
    await abrir(`/integra/semaforo/gestora?gestora=${JEQUIE.gestora_referencia}`);
    const carteira = DADOS.municipios.filter((m) => m.gestora_referencia === JEQUIE.gestora_referencia);
    const nomes = (lista: string): string[] =>
      within(screen.getByRole('list', { name: lista }))
        .queryAllByRole('listitem')
        .map((li) => li.textContent ?? '');

    // Jequié-BA não respondeu à pesquisa do ciclo atual (história pronta). Decisão 51: a pesquisa é por projeto, e o
    // município fica na lista enquanto algum projeto dele não respondeu.
    const semResposta = carteira.filter((m) =>
      m.projetos.some((p) => !DADOS.respostas.some((r) => r.municipio === m.id && r.projeto === p.id && r.ciclo === DADOS.ciclo_atual)),
    );
    expect(semResposta.map((m) => `${m.nome}-${m.uf}`)).toContain('Jequié-BA');
    expect(nomes('Pesquisa sem resposta no ciclo 2026.6').map((t) => t.split(' (')[0]).sort()).toEqual(
      semResposta.map((m) => `${m.nome}-${m.uf}`).sort(),
    );
    expect(screen.getByRole('heading', { level: 2, name: 'Pendências da carteira' })).toBeInTheDocument();
    expect(screen.getByText(/prazo para responder: 20\/12\/2026/)).toBeInTheDocument();

    // Reunião a agendar: sem reunião de escuta no período da cor em vigor (6 meses no verde, 3 no amarelo e no
    // vermelho) e sem reunião já marcada (decisão 48: Jequié tem uma marcada para 10/12).
    const aAgendar = carteira.filter((m) => {
      const s = avaliarMunicipio(DADOS, m.id);
      const datas = DADOS.reunioes.filter((x) => x.municipio === m.id).map((x) => x.data);
      const marcada = DADOS.reunioes.some((x) => x.municipio === m.id && x.data > DADOS.data_referencia);
      return !marcada && !reuniaoEmDia(datas, s.cor_vigente, DADOS.data_referencia);
    });
    const agendar = screen.getByRole('region', { name: 'Reunião de escuta a agendar' });
    if (aAgendar.length === 0) expect(agendar).toHaveTextContent('Nenhuma reunião de escuta atrasada.');
    else expect(nomes('Reunião de escuta a agendar')).toHaveLength(aAgendar.length);
    expect(agendar).not.toHaveTextContent('Jequié-BA');
    expect(screen.getByRole('region', { name: 'Reuniões marcadas' })).toHaveTextContent('Jequié-BA · 10/12/2026');
  });

  test('decisão 48: atas a registrar e ata atrasada, a atrasada primeiro', async () => {
    const sobral = municipio(HISTORIAS_SEMAFORO.em_recuperacao);
    await abrir(`/integra/semaforo/gestora?gestora=${sobral.gestora_referencia}`);
    const atas = within(screen.getByRole('list', { name: 'Atas a registrar' })).getAllByRole('listitem').map((li) => li.textContent);
    expect(atas[0]).toMatch(/Sobral-CE · reunião de 27\/11\/2026 · Ata atrasada: o prazo era 04\/12\/2026/);
  });

  test('decisão 48: a ata da reunião de 04/12 de Horizonte está por registrar, com o prazo', async () => {
    await abrir();
    const atas = within(screen.getByRole('list', { name: 'Atas a registrar' })).getAllByRole('listitem').map((li) => li.textContent);
    expect(atas).toContainEqual(expect.stringMatching(/Horizonte-CE · reunião de 04\/12\/2026 · Ata a registrar até 11\/12\/2026/));
  });

  test('decisão 57: as tarefas canceladas e substituídas não somem; o painel diz quantas são', async () => {
    const gestora = DADOS.municipios.find((m) => m.id === DADOS.tarefas.find((t) => t.encerramento)!.municipio)!.gestora_referencia;
    const carteira = new Set(DADOS.municipios.filter((m) => m.gestora_referencia === gestora).map((m) => m.id));
    const encerradas = DADOS.tarefas.filter((t) => carteira.has(t.municipio) && t.encerramento !== null).length;
    await abrir(`/integra/semaforo/gestora?gestora=${gestora}`);
    expect(screen.getByText(/Hoje é 07\/12\/2026/)).toHaveTextContent(
      `${encerradas} ${encerradas === 1 ? 'tarefa encerrada' : 'tarefas encerradas'} sem fazer (canceladas pelo Comitê ou substituídas), que continuam na ficha de cada município`,
    );
  });

  test('a reunião vira pendência quando passa do período da cor', async () => {
    // Seis meses depois de hoje, a reunião semestral de setembro já não está em dia no verde.
    await abrir(`/integra/semaforo/gestora?gestora=${JEQUIE.gestora_referencia}`, { ...DADOS, data_referencia: '2027-06-07' });
    const lista = screen.getByRole('list', { name: 'Reunião de escuta a agendar' });
    expect(within(lista).getAllByRole('listitem')).toHaveLength(
      DADOS.municipios.filter((m) => m.gestora_referencia === JEQUIE.gestora_referencia).length,
    );
  });

  test('no dia seguinte, a reunião que vencia hoje aparece como vencida', async () => {
    const amanha = { ...DADOS, data_referencia: '2026-12-08' };
    expect(DADOS.tarefas.filter((t) => estadoDaTarefa(t, '2026-12-08') === 'vencida')).toHaveLength(1);
    await abrir(undefined, amanha);
    expect(tarefasEm('Vencidas')).toEqual([expect.stringMatching(/Reunião com a Secretaria.*Horizonte-CE/)]);
    expect(within(screen.getByRole('region', { name: 'Vence hoje' })).getByText('Nada vence hoje.')).toBeInTheDocument();
  });
});
