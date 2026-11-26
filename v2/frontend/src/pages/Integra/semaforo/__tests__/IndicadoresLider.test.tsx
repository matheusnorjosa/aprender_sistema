/**
 * Semáforo — Indicadores da Líder do NFP: contagem por cor, por gerência, evolução dos ciclos e tarefas
 * vencidas. Gráfico feito à mão, com a tabela ao lado. DADOS SIMULADOS.
 */
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { gerarDadosSimulados } from '../../dados/gerador';
import { calcularEquipe } from '../../ica/calculo';
import * as exportar from '../../ica/exportar';
import { QUEM_VE } from '../../quemVe';
import IndicadoresLider from '../IndicadoresLider';
import { SemaforoDemoProvider } from '../SemaforoDemoContext';
import {
  avaliarMunicipio,
  gerarDadosSemaforo,
  HISTORIAS_SEMAFORO,
  mesesCurtosDoCiclo,
  SEMENTE_SEMAFORO,
  type DadosSemaforo,
} from '../dados';
import {
  duasCasas,
  estadoDaTarefa,
  mediaDaPesquisa,
  mediaNps,
  resumoNps,
  reuniaoEmDia,
  tempoDeResposta,
  textoResumoNps,
} from '../regras';
import type { RespostaPesquisa } from '../tipos';

const DADOS = gerarDadosSemaforo();
const SITUACOES = DADOS.municipios.map((m) => avaliarMunicipio(DADOS, m.id));
/** O último ciclo fechado: a pesquisa dele já fechou. */
const FECHADO = DADOS.ciclos.at(-2)!;
const contar = (cor: string): number => SITUACOES.filter((s) => s.cor_vigente === cor).length;
const ESTADOS = DADOS.tarefas.map((t) => estadoDaTarefa(t, DADOS.data_referencia));

function renderizar(dados?: DadosSemaforo): void {
  render(
    <MemoryRouter>
      <SemaforoDemoProvider dados={dados}>
        <IndicadoresLider />
      </SemaforoDemoProvider>
    </MemoryRouter>,
  );
}

describe('Semáforo — Indicadores da Líder', { timeout: 20000 }, () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('título, quem vê na versão real e a contagem por cor em vigor (nome e número)', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Indicadores da Líder do NFP' })).toBeInTheDocument();
    expect(screen.getByText(QUEM_VE.lider.aviso)).toBeInTheDocument();
    const lista = screen.getByRole('list', { name: 'Municípios por cor em vigor' });
    const itens = within(lista).getAllByRole('listitem');
    expect(itens.map((li) => li.textContent)).toEqual([
      `Verde: ${contar('verde')} municípios`,
      `Amarelo: ${contar('amarelo')} municípios`,
      `Vermelho: ${contar('vermelho')} municípios`,
    ]);
    expect(contar('verde') + contar('amarelo') + contar('vermelho')).toBe(DADOS.municipios.length);
  });

  test('rodada 3: a seta de "Em amarelo e vermelho" compara com o mesmo ciclo que a ficha, e diz com qual', async () => {
    renderizar();
    const lista = await screen.findByRole('list', { name: 'Em amarelo e vermelho' });
    // Jequié-BA: amarelo em 2026.4, vermelho em 2026.5, sem decisão em 2026.6. A ficha diz "Sem mudança" desde 2026.5.
    const jequie = within(lista).getByRole('link', { name: 'Jequié-BA' }).closest('li') as HTMLElement;
    expect(jequie).toHaveTextContent('Sem mudança desde o ciclo 2026.5');
    expect(jequie).not.toHaveTextContent('Piorou');
    // Horizonte-CE: amarelo em 2026.5 e vermelho em 2026.6.
    const horizonte = within(lista).getByRole('link', { name: 'Horizonte-CE' }).closest('li') as HTMLElement;
    expect(horizonte).toHaveTextContent('Piorou: era amarelo desde o ciclo 2026.5');
  });

  test('evolução dos ciclos: gráfico com texto e tabela com caption, uma linha por ciclo publicado e hoje', async () => {
    renderizar();
    const tabela = await screen.findByRole('table', { name: 'Cor publicada em cada ciclo' });
    const linhas = within(tabela).getAllByRole('row').slice(1);
    expect(linhas).toHaveLength(DADOS.ciclos.length);
    const ultimoFechado = DADOS.ciclos.at(-2)!;
    const i = DADOS.ciclos.indexOf(ultimoFechado);
    const doCiclo = (cor: string) => SITUACOES.filter((s) => s.ciclos[i]?.decisao?.cor_publicada === cor).length;
    // O ciclo vem com os meses (no ICA, o mesmo formato quer dizer semestre).
    const rotulo = `${ultimoFechado} (${mesesCurtosDoCiclo(ultimoFechado)})`;
    const linha = linhas.find((l) => within(l).queryByRole('rowheader', { name: rotulo }))!;
    expect(within(linha).getAllByRole('cell').map((c) => c.textContent)).toEqual([
      String(doCiclo('verde')),
      String(doCiclo('amarelo')),
      String(doCiclo('vermelho')),
    ]);
    expect(within(linhas.at(-1)!).getByRole('rowheader')).toHaveTextContent('Hoje (07/12/2026)');
    // O gráfico escreve os números: a cor nunca fala sozinha.
    const grafico = screen.getByRole('figure', { name: /Evolução das cores/ });
    expect(grafico).toHaveTextContent(
      `${rotulo}: Verde ${doCiclo('verde')} · Amarelo ${doCiclo('amarelo')} · Vermelho ${doCiclo('vermelho')}`,
    );
  });

  test('barra da evolução: uma divisória branca separa as cores (os tons forte têm quase a mesma luminância)', async () => {
    renderizar();
    const grafico = await screen.findByRole('figure', { name: /Evolução das cores/ });
    const barras = [...grafico.querySelectorAll('[aria-hidden="true"]')].map((b) => [...b.children] as HTMLElement[]);
    expect(barras.some((pedacos) => pedacos.length > 1)).toBe(true);
    for (const [primeiro, ...depois] of barras) {
      expect(primeiro).not.toHaveStyle({ borderLeft: '2px solid #ffffff' });
      for (const pedaco of depois) expect(pedaco).toHaveStyle({ borderLeft: '2px solid #ffffff' });
    }
  });

  test('por gerência: as três gerências e a linha sem coordenador; o município conta na gerência de cada coordenador dos seus projetos (decisão 46)', async () => {
    renderizar();
    const tabela = await screen.findByRole('table', { name: 'Municípios por gerência, pela cor em vigor' });
    const linhas = within(tabela).getAllByRole('row').slice(1);
    const nomes = linhas.map((l) => within(l).getByRole('rowheader').textContent);
    expect(nomes).toEqual(['Gerência 1', 'Gerência 2', 'Gerência 3', 'Sem coordenador']);
    const total = linhas.reduce((s, l) => s + Number(within(l).getAllByRole('cell')[0]!.textContent), 0);
    // Antes, cada município contava uma vez só (na gerência do 1º projeto). Agora, uma vez em cada gerência dos seus projetos.
    const gerencias = DADOS.municipios.map((m) => {
      const doMunicipio = new Set(
        m.projetos.flatMap((p) => DADOS.coordenadores.filter((c) => c.id === p.coordenador).map((c) => c.gerencia)),
      );
      return Math.max(doMunicipio.size, 1);
    });
    expect(total).toBe(gerencias.reduce((a, b) => a + b, 0));
    expect(screen.getByText(/conta na gerência de cada coordenador dos seus projetos/)).toBeInTheDocument();
  });

  test('nada rola para o lado: no celular, a tabela por gerência vira lista com as cores escritas, e a dos ciclos sai (o gráfico já escreve os números)', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1 });
    expect(document.querySelector('.overflow-x-auto')).toBeNull();
    const nome = 'Municípios por gerência, pela cor em vigor';
    expect(screen.getByRole('table', { name: nome }).closest('.hidden.sm\\:block')).not.toBeNull();
    const lista = screen.getByRole('list', { name: nome });
    expect(lista).toHaveClass('sm:hidden');
    const itens = within(lista).getAllByRole('listitem').map((li) => li.textContent);
    expect(itens.map((t) => t?.split(':')[0])).toEqual(['Gerência 1', 'Gerência 2', 'Gerência 3', 'Sem coordenador']);
    expect(itens[0]).toMatch(/^Gerência 1: \d+ municípios · Verde \d+ · Amarelo \d+ · Vermelho \d+$/);
    expect(screen.getByRole('table', { name: 'Cor publicada em cada ciclo' }).closest('.hidden.sm\\:block')).not.toBeNull();
    expect(screen.queryByRole('list', { name: 'Cor publicada em cada ciclo' })).not.toBeInTheDocument();
  });

  test('decisão 38: o retrato diz que as cores são as em vigor, e que o vermelho muda na hora', async () => {
    renderizar();
    const retrato = await screen.findByText(/Retrato de hoje/);
    expect(retrato).toHaveTextContent(/As cores desta tela são as em vigor: as publicadas pelo Comitê e o vermelho na hora/);
    expect(retrato).toHaveTextContent(/um indicador em vermelho ou três amarelos mudam a cor em vigor assim que o dado chega/);
    expect(retrato).not.toHaveTextContent(/muda só a cor sugerida/);
  });

  test('os indicadores da seção 7 do PDF para a Líder: resposta à pesquisa, reuniões, satisfação, plano de ação e ICA', async () => {
    renderizar();
    const lista = await screen.findByRole('list', { name: 'Indicadores da seção 7 do PDF' });
    const item = (titulo: RegExp): string =>
      within(lista)
        .getAllByRole('listitem')
        .find((li) => titulo.test(li.textContent ?? ''))?.textContent ?? '';
    const pct = (n: number, total: number): string => `${Math.round((n * 100) / total)}%`;
    const N = DADOS.municipios.length;

    // Taxa de resposta (meta 80%): o último ciclo fechado, em que o prazo da pesquisa já acabou. Decisão 51: a
    // pesquisa é por projeto; o município respondeu quando todos os projetos dele responderam no prazo.
    const responderam = DADOS.municipios.filter((m) =>
      m.projetos.every((p) => DADOS.respostas.some((r) => r.projeto === p.id && r.ciclo === FECHADO && r.no_prazo)),
    ).length;
    expect(item(/Taxa de resposta à pesquisa/)).toContain(`${responderam} de ${N} municípios (${pct(responderam, N)})`);
    expect(item(/Taxa de resposta à pesquisa/)).toContain('Meta: 80% ou mais');

    // Reunião de escuta no período da cor em vigor (meta 100%).
    const emDia = SITUACOES.filter((s) =>
      reuniaoEmDia(DADOS.reunioes.filter((x) => x.municipio === s.municipio).map((x) => x.data), s.cor_vigente, DADOS.data_referencia),
    ).length;
    expect(item(/Reuniões de escuta no período/)).toContain(`${emDia} de ${N} municípios (${pct(emDia, N)})`);
    expect(item(/Reuniões de escuta no período/)).toContain('Meta: 100%');

    // Satisfação média e NPS de todas as respostas do ciclo fechado; decisão 31: maior, menor e média.
    const doCiclo = DADOS.respostas.filter((r) => r.ciclo === FECHADO);
    expect(item(/Satisfação média e NPS/)).toContain(`Média ${duasCasas(mediaDaPesquisa(doCiclo)!)} · NPS: ${textoResumoNps(resumoNps(doCiclo)!)}`);
    expect(mediaNps(doCiclo)).not.toBeNull();

    // Vermelho com o plano de ação no prazo (Horizonte-CE: vermelho na hora em 30/11, prazo 21/12 em dias úteis).
    const vermelhos = SITUACOES.filter((s) => s.cor_vigente === 'vermelho').length;
    expect(item(/plano de ação no prazo/)).toContain(`${vermelhos} de ${vermelhos} municípios em vermelho`);

    // Distribuição do ICA (meta entre 70 e 130), do retrato publicado do ICA.
    const ica = gerarDadosSimulados(SEMENTE_SEMAFORO);
    const equipe = calcularEquipe(ica.base, ica.versoes_pesos.find((v) => v.id === ica.versao_vigente)!.pesos);
    const comCarteira = equipe.coordenadores.filter((c) => !c.semMunicipios);
    const dentro = comCarteira.filter((c) => c.conta.dentroDaMeta).length;
    expect(item(/Distribuição do ICA/)).toContain(`${dentro} de ${comCarteira.length} coordenadores entre 70 e 130`);
    expect(item(/Distribuição do ICA/)).toContain('Meta: entre 70 e 130');
  });

  /** As células de uma linha da tabela de satisfação: a média e o NPS com a maior e a menor nota (decisão 31). */
  const celulasEsperadas = (respostas: readonly RespostaPesquisa[]): string[] => {
    const nps = resumoNps(respostas)!;
    return [duasCasas(mediaDaPesquisa(respostas)!), `${duasCasas(nps.media)} maior ${nps.maior}, menor ${nps.menor}`];
  };

  test('satisfação média e NPS por coordenador e por gestora de referência, no último ciclo fechado', async () => {
    renderizar();
    const porCoordenador = await screen.findByRole('table', { name: `Satisfação por coordenador, ciclo ${FECHADO}` });
    const m = DADOS.municipios.find((x) => x.coordenador !== null)!;
    const coordenador = DADOS.coordenadores.find((c) => c.id === m.coordenador)!;
    // Decisão 46: a resposta é do projeto, e o projeto tem o coordenador.
    const projetos = new Set(DADOS.municipios.flatMap((x) => x.projetos).filter((p) => p.coordenador === coordenador.id).map((p) => p.id));
    const respostas = DADOS.respostas.filter((r) => r.ciclo === FECHADO && projetos.has(r.projeto));
    const linha = within(porCoordenador).getByRole('rowheader', { name: coordenador.nome }).closest('tr')!;
    expect(within(linha).getAllByRole('cell').map((c) => c.textContent)).toEqual(celulasEsperadas(respostas));
    const porGestora = screen.getByRole('table', { name: `Satisfação por gestora de referência, ciclo ${FECHADO}` });
    expect(within(porGestora).getAllByRole('row').slice(1)).toHaveLength(DADOS.pessoas.length);
  });

  test('decisão 51: satisfação por projeto, juntando as respostas de cada projeto pelo nome', async () => {
    renderizar();
    const porProjeto = await screen.findByRole('table', { name: `Satisfação por projeto, ciclo ${FECHADO}` });
    const nomes = [...new Set(DADOS.municipios.flatMap((m) => m.projetos.map((p) => p.nome)))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
    expect(within(porProjeto).getAllByRole('rowheader').map((h) => h.textContent)).toEqual(nomes);
    const ids = new Set(DADOS.municipios.flatMap((m) => m.projetos).filter((p) => p.nome === 'NOVO LENDO').map((p) => p.id));
    const respostas = DADOS.respostas.filter((r) => r.ciclo === FECHADO && ids.has(r.projeto));
    const linha = within(porProjeto).getByRole('rowheader', { name: 'NOVO LENDO' }).closest('tr')!;
    expect(within(linha).getAllByRole('cell').map((c) => c.textContent)).toEqual(celulasEsperadas(respostas));
  });

  test('decisão 50: o tempo médio de resposta às ocorrências do ano, contra a meta de 48 h, e as que passaram', async () => {
    renderizar();
    const lista = await screen.findByRole('list', { name: 'Indicadores da seção 7 do PDF' });
    const tempo = within(lista).getAllByRole('listitem').find((li) => /Tempo médio de resposta/.test(li.textContent ?? ''))!;
    const t = tempoDeResposta(DADOS.ocorrencias.filter((o) => o.data.startsWith('2026')));
    expect(t.fora_da_meta).toBe(1);
    expect(tempo).toHaveTextContent(
      `${t.respondidas} respondidas: ${t.dentro_da_meta} em até 48 h e ${t.fora_da_meta} fora da meta; ${t.sem_resposta} sem resposta`,
    );
    // Leitura para o dono (Para validar): a meta conta horas corridas, com sábado e domingo.
    expect(tempo).toHaveTextContent(/Meta: 48 h corridas ou menos em média: na meta/);
    expect(tempo).toHaveTextContent('Fora da meta: Horizonte-CE (54 h)');
  });

  test('decisão 49: a convergência entre a pesquisa e as ocorrências, com a lista dos que divergem', async () => {
    renderizar();
    const lista = await screen.findByRole('list', { name: 'Indicadores da seção 7 do PDF' });
    const convergencia = within(lista).getAllByRole('listitem').find((li) => /Convergência/.test(li.textContent ?? ''))!;
    expect(convergencia).toHaveTextContent(/ciclo 2026\.5/);
    expect(convergencia).toHaveTextContent(/\d+ de \d+ municípios \(\d+%\) com a pesquisa e as ocorrências de acordo/);
    const divergem = within(convergencia).getByRole('list', { name: 'Municípios em que a pesquisa e as ocorrências divergem' });
    expect(within(divergem).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'Mucambo-CE: pesquisa Vermelho, ocorrências Verde',
    ]);
    expect(within(divergem).getByRole('link', { name: 'Mucambo-CE' })).toHaveAttribute(
      'href',
      `/integra/semaforo/municipio/${DADOS.municipios.find((m) => m.nome === 'Mucambo')!.id}`,
    );
  });

  test('o que a seção 7 pede o protótipo agora mede: nada fica como "ainda não medido" (decisões 49 a 51)', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1 });
    expect(screen.queryByRole('list', { name: 'Ainda não medidos no protótipo' })).not.toBeInTheDocument();
    expect(screen.queryByText(/não guardam quando foram respondidas/)).not.toBeInTheDocument();
  });

  test('tarefas: contagem por situação e a que vence hoje (Horizonte-CE), com quem receberia o alerta', async () => {
    renderizar();
    const resumo = await screen.findByRole('list', { name: 'Tarefas por situação' });
    expect(resumo).toHaveTextContent(`Vencidas: ${ESTADOS.filter((e) => e === 'vencida').length}`);
    expect(resumo).toHaveTextContent(`Vencem hoje: ${ESTADOS.filter((e) => e === 'vence_hoje').length}`);
    expect(resumo).toHaveTextContent(`No prazo: ${ESTADOS.filter((e) => e === 'no_prazo').length}`);
    expect(resumo).toHaveTextContent(`Concluídas: ${ESTADOS.filter((e) => e === 'concluida').length}`);
    // Decisão 57: as que deixaram de valer continuam contadas.
    expect(resumo).toHaveTextContent(`Canceladas pelo Comitê: ${ESTADOS.filter((e) => e === 'cancelada_comite').length}`);
    expect(resumo).toHaveTextContent(`Substituídas: ${ESTADOS.filter((e) => e === 'substituida').length}`);

    const { nome, uf } = HISTORIAS_SEMAFORO.vermelho_prazo_hoje;
    const cartao = screen.getByText(`Reunião com a Secretaria · ${nome}-${uf}`).closest('li') as HTMLElement;
    expect(cartao).toHaveTextContent('Vence hoje');
    expect(cartao).toHaveTextContent('Prazo: 07/12/2026');
    // Seção 8 do PDF: o alerta de prazo vai para o responsável pela tarefa (no vermelho, a gestora de referência e a
    // gestora pedagógica) e para a SPE. A Líder do NFP não recebe este alerta.
    const municipio = DADOS.municipios.find((m) => m.nome === nome && m.uf === uf)!;
    const gestora = DADOS.pessoas.find((p) => p.id === municipio.gestora_referencia)!.nome;
    expect(cartao).toHaveTextContent(`Seria enviado para: ${gestora} (gestora de referência), Gestora pedagógica, SPE`);
    expect(cartao).not.toHaveTextContent('Líder do NFP');
    expect(screen.getByText(/Nada é enviado/)).toBeInTheDocument();
  });

  test('tarefa que vence amanhã também aparece (seção 8: um dia antes e no vencimento), para o responsável e a SPE', async () => {
    const m = DADOS.municipios.find((x) => x.coordenador !== null)!;
    const gestora = DADOS.pessoas.find((p) => p.id === m.gestora_referencia)!.nome;
    const coordenador = DADOS.coordenadores.find((c) => c.id === m.coordenador)!.nome;
    renderizar({
      ...DADOS,
      tarefas: [
        ...DADOS.tarefas,
        {
          id: Math.max(...DADOS.tarefas.map((t) => t.id)) + 1,
          chave: 'contato_articulador',
          titulo: 'Contato com o articulador',
          municipio: m.id,
          cor: 'amarelo',
          criada_em: '2026-11-24',
          prazo_em: '2026-12-08',
          concluida_em: null,
          encerramento: null,
        },
      ],
    });
    expect(await screen.findByRole('heading', { level: 3, name: 'Vencidas e que vencem hoje ou amanhã' })).toBeInTheDocument();
    const cartao = screen.getByText(`Contato com o articulador · ${m.nome}-${m.uf}`).closest('li') as HTMLElement;
    expect(cartao).toHaveTextContent('Situação: Vence amanhã');
    expect(cartao).toHaveTextContent('Prazo: 08/12/2026');
    // Rodada 3: a cor da tarefa e quando ela nasceu, sem chamar de "publicada" o que o Comitê ainda não viu.
    expect(cartao).toHaveTextContent('Cor da tarefa: Amarelo · criada em 24/11/2026');
    expect(cartao).not.toHaveTextContent('Cor publicada');
    expect(cartao).toHaveTextContent(`Seria enviado para: ${gestora} (gestora de referência), ${coordenador} (coordenador), SPE`);
  });

  test('rodada 4 (decisões 33 e 34, leitura): na sexta, a tarefa que vence na segunda aparece como "Vence no próximo dia útil"', async () => {
    const m = DADOS.municipios.find((x) => x.coordenador !== null)!;
    renderizar({
      ...DADOS,
      data_referencia: '2026-12-04',
      tarefas: [
        ...DADOS.tarefas,
        {
          id: Math.max(...DADOS.tarefas.map((t) => t.id)) + 1,
          chave: 'contato_articulador',
          titulo: 'Contato com o articulador',
          municipio: m.id,
          cor: 'amarelo',
          criada_em: '2026-11-20',
          prazo_em: '2026-12-07',
          concluida_em: null,
          encerramento: null,
        },
      ],
    });
    await screen.findByRole('heading', { level: 3, name: 'Vencidas e que vencem hoje ou amanhã' });
    const cartao = screen.getByText(`Contato com o articulador · ${m.nome}-${m.uf}`).closest('li') as HTMLElement;
    expect(cartao).toHaveTextContent('Situação: Vence no próximo dia útil');
    expect(cartao).toHaveTextContent('Prazo: 07/12/2026');
  });

  test('decisão 46: com projetos de coordenadores diferentes, o alerta de prazo do amarelo vai para todos eles', async () => {
    const m = DADOS.municipios.find((x) => new Set(x.projetos.flatMap((p) => (p.coordenador === null ? [] : [p.coordenador]))).size > 1)!;
    const gestora = DADOS.pessoas.find((p) => p.id === m.gestora_referencia)!.nome;
    const nomes = [...new Set(m.projetos.map((p) => p.coordenador))].map((id) => DADOS.coordenadores.find((c) => c.id === id)!.nome);
    expect(nomes.length).toBeGreaterThan(1);
    renderizar({
      ...DADOS,
      tarefas: [
        ...DADOS.tarefas,
        {
          id: Math.max(...DADOS.tarefas.map((t) => t.id)) + 1,
          chave: 'contato_articulador',
          titulo: 'Contato com o articulador',
          municipio: m.id,
          cor: 'amarelo',
          criada_em: '2026-11-24',
          prazo_em: '2026-12-08',
          concluida_em: null,
          encerramento: null,
        },
      ],
    });
    await screen.findByRole('heading', { level: 3, name: 'Vencidas e que vencem hoje ou amanhã' });
    expect(screen.getByRole('heading', { level: 2, name: 'Tarefas de cada cor' })).toBeInTheDocument();
    // Horizonte-CE: a reunião com a Secretaria nasceu do vermelho na hora de 30/11 (rodada 3).
    const horizonte = screen.getByText(/^Reunião com a Secretaria · Horizonte-CE/).closest('li') as HTMLElement;
    expect(horizonte).toHaveTextContent('Cor da tarefa: Vermelho · criada em 30/11/2026, quando a cor mudou na hora');
    const cartao = screen.getByText(`Contato com o articulador · ${m.nome}-${m.uf}`).closest('li') as HTMLElement;
    expect(cartao).toHaveTextContent(
      `Seria enviado para: ${gestora} (gestora de referência), ${nomes.map((n) => `${n} (coordenador)`).join(', ')}, SPE`,
    );
  });

  test('decisão 46: na planilha, a coluna do coordenador lista os coordenadores de todos os projetos', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    const m = DADOS.municipios.find((x) => new Set(x.projetos.flatMap((p) => (p.coordenador === null ? [] : [p.coordenador]))).size > 1)!;
    const nomes = [...new Set(m.projetos.map((p) => p.coordenador))].map((id) => DADOS.coordenadores.find((c) => c.id === id)!.nome);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Baixar planilha/ }));
    const [, cabecalho, linhas] = baixar.mock.calls[0]!;
    const coluna = (cabecalho as string[]).indexOf('Coordenador');
    const linha = (linhas as (string | number)[][]).find((l) => l[0] === m.nome && l[1] === m.uf)!;
    expect(linha[coluna]).toBe(nomes.length === 2 ? `${nomes[0]} e ${nomes[1]}` : `${nomes.slice(0, -1).join(', ')} e ${nomes.at(-1)}`);
  });

  test('o ciclo aparece com os meses: no ICA, o mesmo formato quer dizer semestre', async () => {
    renderizar();
    expect(await screen.findByText(/com o ciclo 2026\.6 \(novembro e dezembro de 2026\) em andamento/)).toBeInTheDocument();
    const tabela = screen.getByRole('table', { name: 'Cor publicada em cada ciclo' });
    expect(within(tabela).getByRole('rowheader', { name: '2026.5 (set–out 2026)' })).toBeInTheDocument();
  });

  test('baixar planilha: um município por linha, com a cor de cada ciclo', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Baixar planilha/ }));
    const [nome, cabecalho, linhas] = baixar.mock.calls[0]!;
    expect(nome).toBe('semaforo_indicadores_lider.csv');
    const publicadas = DADOS.ciclos.slice(0, -1).map((c) => `Publicada em ${c}`);
    expect(cabecalho).toEqual(expect.arrayContaining(['Município', 'UF', 'Gerência', 'Cor em vigor', ...publicadas]));
    // A satisfação por município (seção 7) vai na planilha: na tela, por coordenador e por gestora.
    expect(cabecalho).toEqual(
      expect.arrayContaining([
        `Média da pesquisa (${FECHADO})`,
        `NPS (${FECHADO})`,
        `NPS maior (${FECHADO})`,
        `NPS menor (${FECHADO})`,
        `Respondeu no prazo (${FECHADO})`,
        'Reunião de escuta em dia',
      ]),
    );
    expect(linhas).toHaveLength(DADOS.municipios.length);
  });
});
