/**
 * Semáforo — Painel da gestora de referência (DADOS SIMULADOS): os municípios dela, as tarefas por prazo
 * e o que vence hoje primeiro.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { QUEM_VE } from '../../quemVe';
import { avaliarMunicipio, gerarDadosSemaforo, HISTORIAS_SEMAFORO } from '../dados';
import { estadoDaTarefa, reuniaoEmDia } from '../regras';
import { renderTelaSemaforo } from './telaSemaforo';

const DADOS = gerarDadosSemaforo();
const municipio = (h: { nome: string; uf: string }) => DADOS.municipios.find((m) => m.nome === h.nome && m.uf === h.uf)!;
const nomeDa = (id: number): string => DADOS.pessoas.find((p) => p.id === id)!.nome;

const HORIZONTE = municipio(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
const JEQUIE = municipio(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos);
/** Uma gestora sem nenhuma tarefa em aberto na carteira. */
const SEM_TAREFAS = DADOS.pessoas.find((p) => {
  const ids = DADOS.municipios.filter((m) => m.gestora_referencia === p.id).map((m) => m.id);
  return DADOS.tarefas.every((t) => !ids.includes(t.municipio) || t.concluida_em !== null);
})!;

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
    expect(noPrazo[0]).toMatch(/Plano de ação pactuado.*Horizonte-CE.*17\/12\/2026/);
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
    await abrir();
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

    // Jequié-BA não respondeu à pesquisa do ciclo atual (história pronta).
    const semResposta = carteira.filter((m) => !DADOS.respostas.some((r) => r.municipio === m.id && r.ciclo === DADOS.ciclo_atual));
    expect(semResposta.map((m) => `${m.nome}-${m.uf}`)).toContain('Jequié-BA');
    expect(nomes('Pesquisa sem resposta no ciclo 2026.6').sort()).toEqual(semResposta.map((m) => `${m.nome}-${m.uf}`).sort());
    expect(screen.getByRole('heading', { level: 2, name: 'Pendências da carteira' })).toBeInTheDocument();
    expect(screen.getByText(/prazo para responder: 20\/12\/2026/)).toBeInTheDocument();

    // Reunião a agendar: sem reunião de escuta no período da cor em vigor (6 meses no verde, 3 no amarelo e no vermelho).
    const aAgendar = carteira.filter((m) => {
      const s = avaliarMunicipio(DADOS, m.id);
      const datas = DADOS.reunioes.filter((x) => x.municipio === m.id).map((x) => x.data);
      return !reuniaoEmDia(datas, s.cor_vigente, DADOS.data_referencia);
    });
    const agendar = screen.getByRole('region', { name: 'Reunião de escuta a agendar' });
    if (aAgendar.length === 0) expect(agendar).toHaveTextContent('Nenhuma reunião de escuta atrasada.');
    else expect(nomes('Reunião de escuta a agendar')).toHaveLength(aAgendar.length);

    // Atas a registrar: o protótipo não acompanha, e a tela diz isso.
    expect(screen.getByRole('region', { name: 'Atas a registrar' })).toHaveTextContent(/não acompanha/);
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
