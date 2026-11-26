/**
 * Dados simulados do Semáforo: determinísticos, sobre os municípios reais do relatório de deslocamento,
 * com as pessoas fictícias do ICA, e com a história pronta da demonstração de 07/12/2026:
 * um vermelho com prazo vencendo hoje, um em recuperação, um que não respondeu a pesquisa em dois
 * ciclos, uma cor que o Comitê alterou com justificativa e um município em que pesquisa e ocorrências divergem.
 */
import { describe, expect, it } from 'vitest';
import { contarNomesReais, guardaDeNomesReaisAtiva } from '../../__tests__/nomesReais';
import { DESLOCAMENTO_MUNICIPIOS } from '../../dados/deslocamento';
import { gerarDadosSimulados } from '../../dados/gerador';
import {
  CICLO_ATUAL_SEMAFORO,
  DATA_REFERENCIA_SEMAFORO,
  HISTORIAS_SEMAFORO,
  aplicarVermelhoAutomatico,
  avaliarMunicipio,
  cicloAnterior,
  convergencia,
  gerarDadosSemaforo,
  mesesCurtosDoCiclo,
  mesesDoCiclo,
  periodoDoCiclo,
  tarefasDepoisDaPublicacao,
  valoresDoCiclo,
  valoresPorProjeto,
  type ColetasSemaforo,
  type DadosSemaforo,
  type MunicipioSemaforo,
} from '../dados';
import {
  classificar,
  criarTarefas,
  estadoDaTarefa,
  horasEntre,
  inicioDasFormacoesNoAno,
  situacaoDaReuniao,
  somarDiasUteis,
  tarefaAberta,
  tempoDeResposta,
  validarDecisao,
} from '../regras';
import type { DecisaoComite, RelatorioMensal, RespostaPesquisa } from '../tipos';

const dados = gerarDadosSemaforo();
const ica = gerarDadosSimulados();
const REF = DATA_REFERENCIA_SEMAFORO;
const DATA = /^\d{4}-\d{2}-\d{2}$/;
const DATA_HORA = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00-03:00$/;

function municipio(h: { nome: string; uf: string }) {
  const m = dados.municipios.find((x) => x.nome === h.nome && x.uf === h.uf);
  if (!m) throw new Error(`fora da lista: ${h.nome}-${h.uf}`);
  return m;
}

const situacoes = dados.municipios.map((m) => avaliarMunicipio(dados, m.id));

describe('ciclos bimestrais', () => {
  it('período, prazo da pesquisa e ciclo anterior', () => {
    expect(periodoDoCiclo('2026.6')).toEqual({
      inicio: '2026-11-01',
      fim: '2026-12-31',
      prazo_pesquisa: '2026-12-20',
      meses: ['2026-11', '2026-12'],
    });
    expect(periodoDoCiclo('2026.1')).toEqual({
      inicio: '2026-01-01',
      fim: '2026-02-28',
      prazo_pesquisa: '2026-02-20',
      meses: ['2026-01', '2026-02'],
    });
    expect(cicloAnterior('2026.1')).toBe('2025.6');
    expect(cicloAnterior('2026.4')).toBe('2026.3');
  });

  it('os meses do ciclo, para a tela: no ICA o mesmo formato "AAAA.N" quer dizer semestre', () => {
    expect(mesesDoCiclo('2026.6')).toBe('novembro e dezembro de 2026');
    expect(mesesDoCiclo('2026.2')).toBe('março e abril de 2026');
    expect(mesesCurtosDoCiclo('2025.6')).toBe('nov–dez 2025');
    expect(mesesCurtosDoCiclo('2026.5')).toBe('set–out 2026');
  });
});

describe('gerarDadosSemaforo', () => {
  it('é determinístico (semente fixa) e é simulado', () => {
    expect(gerarDadosSemaforo()).toEqual(dados);
    expect(dados.origem).toBe('simulado');
  });

  it('a "hoje" da demonstração é 07/12/2026 (segunda-feira), no ciclo 2026.6, depois de 6 ciclos de histórico', () => {
    expect(REF).toBe('2026-12-07');
    expect(new Date(`${REF}T00:00:00Z`).getUTCDay()).toBe(1);
    expect(dados.data_referencia).toBe(REF);
    expect(CICLO_ATUAL_SEMAFORO).toBe('2026.6');
    expect(dados.ciclo_atual).toBe('2026.6');
    expect(dados.ciclos).toEqual(['2025.6', '2026.1', '2026.2', '2026.3', '2026.4', '2026.5', '2026.6']);
  });

  it('municípios reais do relatório de deslocamento, sem os de ações suspensas, ids únicos', () => {
    const esperados = DESLOCAMENTO_MUNICIPIOS.filter((m) => !m.acoes_suspensas).map((m) => `${m.nome}-${m.uf}`);
    expect(dados.municipios.map((m) => `${m.nome}-${m.uf}`)).toEqual(esperados);
    expect(new Set(dados.municipios.map((m) => m.id)).size).toBe(dados.municipios.length);
  });

  it('pessoas fictícias: coordenadores e gestoras de referência são os da lista fixa do ICA', () => {
    const coordenadoresIca = new Set(ica.base.coordenadores.map((c) => `${c.id}:${c.nome}`));
    const pessoasIca = new Set(ica.pessoas.map((p) => `${p.id}:${p.nome}`));
    expect(dados.coordenadores.every((c) => coordenadoresIca.has(`${c.id}:${c.nome}`))).toBe(true);
    expect(dados.pessoas.every((p) => pessoasIca.has(`${p.id}:${p.nome}`))).toBe(true);
    const coordenadores = new Set(dados.coordenadores.map((c) => c.id));
    const pessoas = new Set(dados.pessoas.map((p) => p.id));
    for (const m of dados.municipios) {
      if (m.coordenador !== null) expect(coordenadores.has(m.coordenador)).toBe(true);
      for (const p of m.projetos) if (p.coordenador !== null) expect(coordenadores.has(p.coordenador)).toBe(true);
      expect(pessoas.has(m.gestora_referencia)).toBe(true);
    }
    // A pesquisa só identifica por função; ninguém assina com nome.
    expect(dados.respostas.every((r) => r.identificacao === null)).toBe(true);
  });

  it('cadastro único com o ICA: município que está no ICA tem o mesmo id, coordenador e gestora de referência', () => {
    for (const m of dados.municipios) {
      const noIca = ica.base.municipios.find((x) => x.nome === m.nome && x.uf === m.uf);
      if (!noIca) {
        // Fora do ICA: id em outra faixa, para não colidir com um id do ICA.
        expect(m.id).toBeGreaterThan(1000);
        continue;
      }
      expect(m.id).toBe(noIca.id);
      if (noIca.gestora_referencia !== null) expect(m.gestora_referencia).toBe(noIca.gestora_referencia);
      const doIca = ica.base.atendimentos.filter((a) => a.municipio === noIca.id).map((a) => a.coordenador);
      if (doIca.length > 0) expect(m.coordenador).toBe(doIca.find((c) => c !== null) ?? null);
    }
  });

  it.skipIf(!guardaDeNomesReaisAtiva)('nenhum nome da ata nem dos PDFs em nenhum texto (guarda local)', () => {
    expect(contarNomesReais(JSON.stringify({ ...dados, municipios: dados.municipios.map((m) => m.projetos) }))).toBe(0);
  });

  it('formatos das coletas: datas AAAA-MM-DD, 6 itens de 1 a 5, nota de 0 a 10, nada registrado depois de hoje', () => {
    for (const r of dados.respostas) {
      expect(r.respondida_em).toMatch(DATA);
      expect(r.respondida_em <= REF).toBe(true);
      expect(r.itens).toHaveLength(6);
      expect(r.itens.every((i) => Number.isInteger(i) && i >= 1 && i <= 5)).toBe(true);
      expect(Number.isInteger(r.nps) && r.nps >= 0 && r.nps <= 10).toBe(true);
      expect(r.respondida_em <= periodoDoCiclo(r.ciclo).prazo_pesquisa).toBe(r.no_prazo);
    }
    for (const o of dados.ocorrencias) expect(o.data <= REF && DATA.test(o.data)).toBe(true);
    // A reunião agendada pode ser depois de hoje (decisão 48); a ata, nunca.
    for (const r of dados.reunioes) {
      expect(r.data).toMatch(DATA);
      if (r.ata_em !== null) expect(r.data <= r.ata_em && r.ata_em <= REF).toBe(true);
    }
    for (const r of dados.relatorios) {
      expect(r.mes).toMatch(/^\d{4}-\d{2}$/);
      expect(r.formacoes_realizadas).toBeLessThanOrEqual(r.formacoes_previstas);
      expect(r.visitas_realizadas).toBeLessThanOrEqual(r.visitas_previstas);
    }
  });

  it('o Comitê publicou os 6 ciclos fechados de todos; a cor sugerida guardada é a das regras', () => {
    // Rodada 3: o projeto novo no ICA em 2026.2 (Itaquiraí-MS) só tem cor publicada a partir de 2026.4.
    const novo = dados.municipios.find((m) => m.nome === 'Itaquiraí' && m.uf === 'MS')!.id;
    for (const s of situacoes) {
      const fechados = s.ciclos.slice(0, 6).filter((c) => s.municipio !== novo || c.ciclo >= '2026.4');
      expect(fechados.every((c) => c.decisao !== null)).toBe(true);
      for (const c of fechados) {
        expect(c.decisao?.origem).toBe('comite_ordinario');
        expect(c.decisao?.cor_sugerida).toBe(c.resultado.cor);
      }
    }
    for (const d of dados.decisoes) {
      expect(validarDecisao(d.cor_sugerida, d.cor_publicada, d.justificativa).valida).toBe(true);
      expect(d.publicada_em).toMatch(DATA);
    }
  });

  it('a maioria fica verde, com alguns amarelos e poucos vermelhos', () => {
    const porCor = { verde: 0, amarelo: 0, vermelho: 0 };
    for (const s of situacoes) porCor[s.cor_vigente] += 1;
    expect(porCor.verde / situacoes.length).toBeGreaterThanOrEqual(0.6);
    expect(porCor.amarelo).toBeGreaterThanOrEqual(3);
    expect(porCor.vermelho).toBeGreaterThanOrEqual(2);
    expect(porCor.vermelho).toBeLessThanOrEqual(5);
  });

  it('tarefas: ids únicos; as de prazo passado que valem foram concluídas; só uma vence hoje', () => {
    expect(dados.tarefas.length).toBeGreaterThan(0);
    expect(new Set(dados.tarefas.map((t) => t.id)).size).toBe(dados.tarefas.length);
    for (const t of dados.tarefas) {
      if (t.encerramento !== null) {
        // Cancelada ou substituída quando ainda estava aberta: fica guardada, sem conclusão (decisão 57).
        expect(t.concluida_em).toBeNull();
        expect(t.encerramento.em >= t.criada_em && t.encerramento.em <= t.prazo_em).toBe(true);
      } else if (t.prazo_em < REF) {
        expect(t.concluida_em).not.toBeNull();
        expect(t.concluida_em! >= t.criada_em && t.concluida_em! <= t.prazo_em).toBe(true);
      } else {
        expect(t.concluida_em).toBeNull();
      }
    }
    expect(dados.tarefas.filter((t) => estadoDaTarefa(t, REF) === 'vence_hoje')).toHaveLength(1);
  });

  it('as decisões de cada município estão em ordem de data (a última é a cor em vigor)', () => {
    for (const m of dados.municipios) {
      const datas = dados.decisoes.filter((d) => d.municipio === m.id).map((d) => d.publicada_em);
      expect(datas).toEqual([...datas].sort());
    }
  });
});

describe('projetos dentro do município (decisões 46 e 51)', () => {
  it('cada município tem os seus projetos; no ICA, um por atendimento (município × coleção × coordenador)', () => {
    for (const m of dados.municipios) {
      expect(m.projetos.length).toBeGreaterThan(0);
      const doIca = ica.base.atendimentos.filter((a) => a.municipio === m.id);
      if (doIca.length > 0) {
        expect(m.projetos.map((p) => [p.id, p.coordenador])).toEqual(doIca.map((a) => [a.id, a.coordenador]));
      }
      expect(m.coordenador).toBe(m.projetos.find((p) => p.coordenador !== null)?.coordenador ?? null);
    }
    const maisDeUmCoordenador = dados.municipios.filter((m) => new Set(m.projetos.map((p) => p.coordenador)).size > 1);
    expect(maisDeUmCoordenador).toHaveLength(11);
    expect(municipio({ nome: 'Maringá', uf: 'PR' }).projetos.map((p) => p.nome)).toEqual(['NOVO LENDO', 'TEMA', 'AMMA']);
  });

  it('o articulador não tem nome; num município com vários projetos pode ser o mesmo ou um por projeto', () => {
    const todos = dados.municipios.flatMap((m) => m.projetos.map((p) => p.articulador));
    expect(todos.every((a) => /^Articulador\(a\) [A-F]$/.test(a))).toBe(true);
    const varios = dados.municipios.filter((m) => m.projetos.length > 1);
    const mesmo = (m: MunicipioSemaforo) => new Set(m.projetos.map((p) => p.articulador)).size === 1;
    expect(varios.some(mesmo)).toBe(true);
    expect(varios.some((m) => !mesmo(m))).toBe(true);
  });

  it('relatório mensal por projeto: um por município, projeto e mês, com o coordenador do projeto', () => {
    const chaves = dados.relatorios.map((r) => `${r.municipio}/${r.projeto}/${r.mes}`);
    expect(new Set(chaves).size).toBe(chaves.length);
    for (const r of dados.relatorios) {
      const p = dados.municipios.find((m) => m.id === r.municipio)?.projetos.find((x) => x.id === r.projeto);
      expect(p?.coordenador).toBe(r.coordenador);
    }
    // Projeto sem coordenador não entrega relatório: o cronograma dele fica "sem dado".
    const semCoordenador = dados.municipios.flatMap((m) => m.projetos.filter((p) => p.coordenador === null).map((p) => p.id));
    expect(semCoordenador.length).toBeGreaterThan(0);
    expect(dados.relatorios.filter((r) => semCoordenador.includes(r.projeto))).toEqual([]);
  });

  it('rodada 3: o projeto novo no ICA em 2026.2 (Itaquiraí-MS, sem coordenador) só tem coleta e cor a partir de jul/2026 (ciclo 2026.4)', () => {
    const m = dados.municipios.find((x) => x.nome === 'Itaquiraí' && x.uf === 'MS')!;
    const projetos = new Set(m.projetos.map((p) => p.id));
    // No ICA, o projeto só aparece no retrato de 2026.2.
    expect(ica.historico.filter((h) => h.base.atendimentos.some((a) => projetos.has(a.id))).map((h) => h.semestre)).toEqual(['2026.2']);
    expect(dados.respostas.filter((r) => r.municipio === m.id && r.ciclo < '2026.4')).toEqual([]);
    expect(dados.reunioes.filter((r) => r.municipio === m.id && r.data < '2026-07-01')).toEqual([]);
    const ciclosPublicados = dados.decisoes.filter((d) => d.municipio === m.id).map((d) => d.ciclo);
    expect(ciclosPublicados.length).toBeGreaterThan(0);
    expect(ciclosPublicados.every((c) => c >= '2026.4')).toBe(true);
  });

  it('pesquisa por projeto: no máximo uma resposta por projeto e ciclo, de um projeto do município', () => {
    const chaves = dados.respostas.map((r) => `${r.municipio}/${r.projeto}/${r.ciclo}`);
    expect(new Set(chaves).size).toBe(chaves.length);
    for (const r of dados.respostas) {
      expect(dados.municipios.find((m) => m.id === r.municipio)?.projetos.some((p) => p.id === r.projeto)).toBe(true);
    }
  });

  describe('na cor do município entra o pior projeto', () => {
    const projetos = [
      { id: 1, nome: 'NOVO LENDO', coordenador: 101, articulador: 'Articulador(a) A' },
      { id: 2, nome: 'TEMA', coordenador: 102, articulador: 'Articulador(a) A' },
    ];
    const m: MunicipioSemaforo = { id: 7, nome: 'Teste', uf: 'CE', coordenador: 101, gestora_referencia: 1, projetos };
    const rel = (projeto: number, mes: string, previstas: number, realizadas: number): RelatorioMensal => ({
      id: projeto * 100 + Number(mes.slice(5)),
      municipio: 7,
      projeto,
      coordenador: projeto === 1 ? 101 : 102,
      mes,
      formacoes_previstas: previstas,
      formacoes_realizadas: realizadas,
      visitas_previstas: 0,
      visitas_realizadas: 0,
    });
    const resp = (projeto: number, ciclo: string): RespostaPesquisa => ({
      id: projeto,
      municipio: 7,
      projeto,
      ciclo,
      respondida_em: '2026-10-10',
      no_prazo: true,
      funcao_respondente: 'Articulador(a) municipal',
      identificacao: null,
      itens: [5, 5, 5, 5, 5, 5],
      nps: 10,
      comentario: '',
    });
    const coletas = (relatorios: RelatorioMensal[], respostas: RespostaPesquisa[]): ColetasSemaforo => ({
      ciclos: ['2026.4', '2026.5'],
      municipios: [m],
      respostas,
      relatorios,
      ocorrencias: [],
    });

    it('projeto A com 95% (verde) e projeto B com 60% (vermelho): o município fica vermelho', () => {
      const relatorios = [rel(1, '2026-09', 10, 9), rel(1, '2026-10', 10, 10), rel(2, '2026-09', 5, 3), rel(2, '2026-10', 5, 3)];
      const v = valoresDoCiclo(coletas(relatorios, [resp(1, '2026.5'), resp(2, '2026.5'), resp(1, '2026.4'), resp(2, '2026.4')]), 7, '2026.5', '2026-10-31');
      expect(v.cronograma).toBe(60);
      expect(classificar(v, [])).toMatchObject({ cor: 'vermelho', decisivos: ['cronograma'] });
    });

    it('resposta à pesquisa olha cada projeto: se um projeto não respondeu, o município não respondeu (o pior conta)', () => {
      const relatorios = [rel(1, '2026-10', 4, 4), rel(2, '2026-10', 4, 4)];
      const v = valoresDoCiclo(coletas(relatorios, [resp(1, '2026.5'), resp(1, '2026.4'), resp(2, '2026.4')]), 7, '2026.5', '2026-10-31');
      expect(v.resposta_pesquisa).toEqual({ ciclo_atual: false, ciclo_anterior: true });
      // Média e NPS juntam as respostas de todos os projetos.
      expect(v.media_pesquisa).toBe(5);
    });
  });
});

describe('decisão 32: ocorrências desde a 1ª formação do ano; o gerador tem um mês de início por município', () => {
  it('as formações de 2026 começam em fevereiro, março ou abril, conforme o município (janeiro é férias)', () => {
    const inicios = new Set<string | null>();
    for (const m of dados.municipios) {
      const doMunicipio = dados.relatorios.filter((r) => r.municipio === m.id);
      if (doMunicipio.length === 0) continue;
      inicios.add(inicioDasFormacoesNoAno(doMunicipio, 2026));
      expect(doMunicipio.some((r) => r.mes === '2026-01')).toBe(false);
      expect(doMunicipio.some((r) => r.mes === '2025-11')).toBe(true);
      expect(doMunicipio.some((r) => r.mes === '2026-11')).toBe(true);
    }
    expect([...inicios].sort()).toEqual(['2026-02-01', '2026-03-01', '2026-04-01']);
  });

  it('o amarelo de ocorrência sorteado cai depois da 1ª formação do município, em qualquer semente (senão não contaria)', () => {
    // Em 2026.1, o 2º mês (fevereiro) pode vir antes do início das formações do município (março ou abril).
    // 8 sementes cobrem o caso de fevereiro antes do início; 40 estouravam o tempo na CI.
    for (let semente = 1; semente <= 8; semente++) {
      const d = gerarDadosSemaforo(semente);
      for (const o of d.ocorrencias.filter((x) => x.data.startsWith('2026-') && x.tipo === 'leve')) {
        const inicio = inicioDasFormacoesNoAno(d.relatorios.filter((r) => r.municipio === o.municipio), 2026);
        expect(inicio, `semente ${semente}, município ${o.municipio}`).not.toBeNull();
        expect(o.data >= inicio!, `semente ${semente}, município ${o.municipio}, ${o.data} antes de ${inicio}`).toBe(true);
      }
    }
  });

  it('a ocorrência leve de Maringá (2026.5) continua contando no ciclo atual; o histórico fica (decisão 57)', () => {
    const m = municipio(HISTORIAS_SEMAFORO.alterada_pelo_comite);
    const atual = avaliarMunicipio(dados, m.id).ciclos.at(-1)?.resultado;
    expect(atual?.avaliacoes.find((a) => a.indicador === 'ocorrencias')).toMatchObject({ cor: 'amarelo', texto: '1 leve' });
    expect(dados.ocorrencias.filter((o) => o.municipio === m.id)).toHaveLength(1);
  });

  it('decisão 32: no município sem formação no ano (o único projeto sem coordenador), a reclamação fica guardada e o indicador diz que não conta', () => {
    const m = dados.municipios.find((x) => x.coordenador === null)!;
    const com: DadosSemaforo = {
      ...dados,
      ocorrencias: [
        ...dados.ocorrencias,
        {
          id: dados.ocorrencias.length + 1,
          municipio: m.id,
          data: REF,
          registrada_em: `${REF}T09:00:00-03:00`,
          respondida_em: null,
          origem: 'fluxo_unico',
          tipo: 'reclamacao',
        },
      ],
    };
    expect(avaliarMunicipio(com, m.id).ciclos.at(-1)?.resultado.avaliacoes.find((a) => a.indicador === 'ocorrencias')).toEqual({
      indicador: 'ocorrencias',
      cor: 'verde',
      texto: 'Nenhuma que conte (1 registrada antes da 1ª formação do ano)',
    });
  });

  it('em janeiro a contagem zera: a ocorrência de 2025 não conta em 2026.1', () => {
    const com2025 = dados.ocorrencias.filter((o) => o.data.startsWith('2025-'));
    for (const o of com2025) {
      const ciclo = avaliarMunicipio(dados, o.municipio).ciclos.find((c) => c.ciclo === '2026.1');
      expect(ciclo?.resultado.avaliacoes.find((a) => a.indicador === 'ocorrencias')?.texto).toBe('Nenhuma');
    }
  });
});

describe('decisão 50: a ocorrência guarda quando foi registrada e quando foi respondida', () => {
  it('data e hora de Fortaleza; a resposta vem depois do registro; o dia do registro é a data', () => {
    for (const o of dados.ocorrencias) {
      expect(o.registrada_em).toMatch(DATA_HORA);
      expect(o.registrada_em.slice(0, 10)).toBe(o.data);
      if (o.respondida_em !== null) {
        expect(o.respondida_em).toMatch(DATA_HORA);
        expect(horasEntre(o.registrada_em, o.respondida_em)).toBeGreaterThan(0);
      }
    }
  });

  it('só a reclamação de Horizonte passou da meta (54 h)', () => {
    const t = tempoDeResposta(dados.ocorrencias);
    expect(t.fora_da_meta).toBe(1);
    const horizonte = municipio(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const reclamacao = dados.ocorrencias.find((o) => o.municipio === horizonte.id && o.tipo === 'reclamacao');
    expect(horasEntre(reclamacao!.registrada_em, reclamacao!.respondida_em!)).toBe(54);
  });
});

describe('decisão 48: reunião marcada antes, ata em até 5 dias úteis', () => {
  const situacaoDe = (h: { nome: string; uf: string }) =>
    dados.reunioes.filter((r) => r.municipio === municipio(h).id).map((r) => situacaoDaReuniao(r, REF));

  it('a ata registrada fica dentro de 5 dias úteis', () => {
    for (const r of dados.reunioes) if (r.ata_em !== null) expect(r.ata_em <= somarDiasUteis(r.data, 5)).toBe(true);
  });

  it('Sobral: ata atrasada; Horizonte: ata a registrar; Jequié: reunião agendada; as demais, realizadas', () => {
    expect(situacaoDe(HISTORIAS_SEMAFORO.em_recuperacao)).toContain('ata_atrasada');
    expect(situacaoDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje)).toContain('ata_a_registrar');
    expect(situacaoDe(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos)).toContain('agendada');
    const contagem = dados.reunioes.map((r) => situacaoDaReuniao(r, REF)).filter((s) => s !== 'realizada');
    expect(contagem.sort()).toEqual(['agendada', 'ata_a_registrar', 'ata_atrasada']);
  });
});

describe('decisões 40 e 41: o Comitê ordinário em data marcada pela SPE; o extraordinário a critério da SPE', () => {
  it('um ordinário por ciclo fechado, na data em que publicou; o do ciclo atual já está marcado', () => {
    const ordinarios = dados.comites.filter((c) => c.tipo === 'ordinario');
    expect(ordinarios.map((c) => c.ciclo)).toEqual(dados.ciclos);
    for (const d of dados.decisoes.filter((x) => x.origem === 'comite_ordinario')) {
      expect(ordinarios.find((c) => c.ciclo === d.ciclo)?.data).toBe(d.publicada_em);
    }
    expect(ordinarios.at(-1)?.data).toBe('2027-01-08');
    expect(dados.comites.filter((c) => c.tipo === 'extraordinario')).toEqual([
      expect.objectContaining({ ciclo: '2026.6', data: '2026-12-02' }),
    ]);
  });
});

describe('a história da demonstração', () => {
  it('vermelho na hora por reclamação em 30/11, confirmado pelo Comitê extraordinário; a reunião com a Secretaria vence hoje', () => {
    const m = municipio(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const s = avaliarMunicipio(dados, m.id);
    const atual = s.ciclos.at(-1);
    expect(atual?.ciclo).toBe('2026.6');
    expect(atual?.resultado.cor).toBe('vermelho');
    expect(atual?.resultado.vermelho_imediato).toBe(true);
    expect(atual?.resultado.decisivos).toEqual(['ocorrencias']);
    // Decisão 38: a cor oficial mudou na hora (30/11); o Comitê extraordinário confirmou depois (02/12).
    expect(dados.decisoes.filter((d) => d.municipio === m.id && d.ciclo === '2026.6')).toEqual([
      expect.objectContaining({ origem: 'vermelho_automatico', cor_publicada: 'vermelho', publicada_em: '2026-11-30' }),
      expect.objectContaining({ origem: 'comite_extraordinario', cor_sugerida: 'vermelho', cor_publicada: 'vermelho', publicada_em: '2026-12-02' }),
    ]);
    expect(atual?.decisao).toMatchObject({ origem: 'comite_extraordinario', publicada_em: '2026-12-02' });
    expect(s).toMatchObject({ cor_vigente: 'vermelho', aguardando_comite: false });
    expect(s.ciclos[5]?.decisao?.cor_publicada).toBe('amarelo');

    // As tarefas nasceram com o vermelho na hora; a confirmação não as repetiu.
    const doVermelho = dados.tarefas.filter((t) => t.municipio === m.id && t.cor === 'vermelho');
    expect(doVermelho.map((t) => [t.chave, t.criada_em])).toEqual([
      ['contato_48h', '2026-11-30'],
      ['reuniao_secretaria', '2026-11-30'],
      ['plano_acao', '2026-11-30'],
      ['devolutiva', '2026-11-30'],
      ['visita_tecnica', '2026-11-30'],
    ]);
    const hoje = dados.tarefas.filter((t) => estadoDaTarefa(t, REF) === 'vence_hoje');
    expect(hoje).toEqual([
      expect.objectContaining({ municipio: m.id, chave: 'reuniao_secretaria', criada_em: '2026-11-30', prazo_em: REF }),
    ]);
    const contato = doVermelho.find((t) => t.chave === 'contato_48h');
    expect(contato).toMatchObject({ prazo_em: '2026-12-02', concluida_em: '2026-12-01' });
  });

  it('em recuperação: vermelho na hora em 2026.4, ciclo limpo em 2026.5, publicado amarelo "em recuperação"', () => {
    const m = municipio(HISTORIAS_SEMAFORO.em_recuperacao);
    const s = avaliarMunicipio(dados, m.id);
    const de2026_4 = dados.decisoes.filter((d) => d.municipio === m.id && d.ciclo === '2026.4');
    expect(de2026_4.map((d) => [d.origem, d.cor_publicada])).toEqual([
      ['vermelho_automatico', 'vermelho'],
      ['comite_ordinario', 'vermelho'],
    ]);
    // O vermelho veio da pesquisa: na data da primeira resposta (um projeto por vez), antes do Comitê de 11/09.
    const datas = dados.respostas.filter((r) => r.municipio === m.id && r.ciclo === '2026.4').map((r) => r.respondida_em);
    expect(m.projetos).toHaveLength(2);
    expect(de2026_4[0]?.publicada_em).toBe([...datas].sort()[0]);
    expect(de2026_4[0]!.publicada_em < '2026-09-11').toBe(true);
    expect(s.ciclos[4]?.decisao?.cor_publicada).toBe('vermelho');
    expect(s.ciclos[5]?.resultado).toMatchObject({ cor: 'amarelo', motivo: 'em_recuperacao', ciclos_limpos: 1 });
    expect(s.ciclos[5]?.decisao?.cor_publicada).toBe('amarelo');
    expect(s.cor_vigente).toBe('amarelo');
    // É o único "em recuperação" publicado: a história não se perde no meio de outros.
    expect(situacoes.filter((x) => x.ciclos[5]?.resultado.em_recuperacao).map((x) => x.municipio)).toEqual([m.id]);
  });

  it('não respondeu a pesquisa em 2026.4 nem em 2026.5: vermelho pela resposta, na hora em que o prazo passou', () => {
    const m = municipio(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos);
    expect(dados.respostas.filter((r) => r.municipio === m.id && ['2026.4', '2026.5'].includes(r.ciclo))).toEqual([]);
    const s = avaliarMunicipio(dados, m.id);
    expect(s.ciclos[4]?.resultado.cor).toBe('amarelo');
    const c5 = s.ciclos[5]?.resultado;
    expect(c5?.cor).toBe('vermelho');
    expect(c5?.decisivos).toEqual(['resposta_pesquisa']);
    expect(c5?.avaliacoes.find((a) => a.indicador === 'resposta_pesquisa')?.texto).toBe('Não respondeu em dois ciclos seguidos');
    expect(s.cor_vigente).toBe('vermelho');
    expect(dados.decisoes.find((d) => d.municipio === m.id && d.origem === 'vermelho_automatico')).toMatchObject({
      ciclo: '2026.5',
      publicada_em: '2026-10-21',
    });
  });

  it('ciclo atual em andamento (pesquisa até 20/12) não conta como ciclo sem alerta', () => {
    // Sem resposta em 2026.6 até hoje: segue vermelho, não "melhorou".
    const jequie = avaliarMunicipio(dados, municipio(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos).id).ciclos.at(-1)?.resultado;
    expect(jequie).toMatchObject({ cor: 'vermelho', motivo: 'ciclo_em_andamento', em_recuperacao: false });
    // 1 ciclo fechado sem alerta (2026.5): segue amarelo em recuperação, não verde.
    const sobral = avaliarMunicipio(dados, municipio(HISTORIAS_SEMAFORO.em_recuperacao).id).ciclos.at(-1)?.resultado;
    expect(sobral).toMatchObject({ cor: 'amarelo', motivo: 'ciclo_em_andamento', em_recuperacao: true, ciclos_limpos: 1 });
    // Antes das decisões de 25/11 eram 2/8/78. Agora: Mucambo é o 3º vermelho (decisão 49), e quem teve ocorrência
    // leve no ano segue amarelo até janeiro (decisão 32).
    const porCor = (cor: string) => situacoes.filter((x) => x.ciclos.at(-1)?.resultado.cor === cor).length;
    expect([porCor('vermelho'), porCor('amarelo'), porCor('verde')]).toEqual([3, 18, 67]);
    const pelaOcorrenciaDoAno = situacoes.filter((x) => {
      const r = x.ciclos.at(-1)?.resultado;
      return r?.cor === 'amarelo' && r.decisivos.includes('ocorrencias');
    });
    expect(pelaOcorrenciaDoAno.length).toBeGreaterThan(0);
  });

  it('o Comitê alterou uma cor sugerida, com justificativa', () => {
    const m = municipio(HISTORIAS_SEMAFORO.alterada_pelo_comite);
    const d = avaliarMunicipio(dados, m.id).ciclos[5]?.decisao;
    expect(d).toMatchObject({ cor_sugerida: 'amarelo', cor_publicada: 'verde' });
    expect(d?.justificativa?.trim()).not.toBe('');
    const alteradas = dados.decisoes.filter((x) => x.cor_sugerida !== x.cor_publicada);
    expect(alteradas).toEqual([d]);
  });

  it('decisão 49: no último ciclo fechado, só Mucambo diverge (NPS vermelho, nenhuma ocorrência)', () => {
    const c = convergencia(dados, situacoes);
    expect(c.ciclo).toBe('2026.5');
    expect(c.divergentes).toEqual([
      { municipio: municipio(HISTORIAS_SEMAFORO.divergente).id, pesquisa: 'vermelho', ocorrencias: 'verde' },
    ]);
    // Quem não respondeu (Jequié e os que tiveram "sem resposta" sorteado) fica fora da comparação.
    const comPesquisa = new Set(dados.respostas.filter((r) => r.ciclo === '2026.5').map((r) => r.municipio));
    expect(comPesquisa.has(municipio(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos).id)).toBe(false);
    expect(c.comparados).toBe(comPesquisa.size);
    expect(c.concordam).toBe(c.comparados - 1);
    expect(c.percentual).toBeCloseTo((c.concordam / c.comparados) * 100);
  });
});

describe('decisão 45 (rodada 3): a volta ao verde conta da cor publicada', () => {
  // Um município verde nos ciclos 2026.4 e 2026.5, com os dados limpos nos dois.
  const s = situacoes.find((x) =>
    ['2026.4', '2026.5'].every((c) => {
      const ciclo = x.ciclos.find((y) => y.ciclo === c);
      return ciclo?.resultado.limpo && ciclo.resultado.cor === 'verde' && ciclo.decisao?.cor_publicada === 'verde';
    }),
  )!;
  const ultimaDe2026_4 = dados.decisoes.filter((d) => d.municipio === s.municipio && d.ciclo === '2026.4').at(-1)!;

  it.each(['vermelho', 'amarelo'] as const)('o Comitê publica %s com os dados limpos: o ciclo seguinte limpo fica amarelo "em recuperação 1 de 2"', (cor) => {
    const alterado: DadosSemaforo = {
      ...dados,
      decisoes: dados.decisoes.map((d) => (d === ultimaDe2026_4 ? { ...d, cor_publicada: cor, justificativa: 'O Comitê subiu a cor.' } : d)),
    };
    const seguinte = avaliarMunicipio(alterado, s.municipio).ciclos.find((c) => c.ciclo === '2026.5')!.resultado;
    expect(seguinte.limpo).toBe(true);
    expect(seguinte.ciclos_limpos).toBe(1);
    expect(seguinte.cor).toBe('amarelo');
    expect(seguinte.em_recuperacao).toBe(true);
  });
});

describe('decisões 38, 39, 42 e 43: a cor oficial e as tarefas', () => {
  const decisao = (parcial: Partial<DecisaoComite>): DecisaoComite => ({
    municipio: 7,
    ciclo: '2026.6',
    cor_sugerida: 'vermelho',
    cor_publicada: 'vermelho',
    justificativa: null,
    publicada_em: '2026-11-30',
    origem: 'vermelho_automatico',
    ...parcial,
  });
  const automatico = decisao({});
  const tarefasDoVermelho = tarefasDepoisDaPublicacao([], decisao({ ciclo: '2026.5', cor_publicada: 'amarelo', cor_sugerida: 'amarelo', origem: 'comite_ordinario' }), automatico);

  it('o vermelho na hora cria as tarefas na data do dado', () => {
    expect(tarefasDoVermelho.map((t) => [t.chave, t.criada_em, t.id])).toEqual([
      ['contato_48h', '2026-11-30', 1],
      ['reuniao_secretaria', '2026-11-30', 2],
      ['plano_acao', '2026-11-30', 3],
      ['devolutiva', '2026-11-30', 4],
      ['visita_tecnica', '2026-11-30', 5],
    ]);
  });

  it('o Comitê confirma: as tarefas seguem (nada muda)', () => {
    const confirma = decisao({ origem: 'comite_extraordinario', publicada_em: '2026-12-02' });
    expect(tarefasDepoisDaPublicacao(tarefasDoVermelho, automatico, confirma)).toEqual(tarefasDoVermelho);
  });

  it('o Comitê desfaz: as abertas ficam "canceladas pelo Comitê", as feitas continuam feitas, e nascem as da cor nova', () => {
    const feita = { ...tarefasDoVermelho[0]!, concluida_em: '2026-12-01' };
    const antes = [feita, ...tarefasDoVermelho.slice(1)];
    const desfaz = decisao({ origem: 'comite_extraordinario', cor_publicada: 'amarelo', justificativa: 'Resolvido.', publicada_em: '2026-12-02' });
    const depois = tarefasDepoisDaPublicacao(antes, automatico, desfaz);
    expect(depois[0]).toEqual(feita);
    expect(depois.slice(1, 5).every((t) => t.encerramento?.motivo === 'cancelada_comite' && t.encerramento.em === '2026-12-02')).toBe(true);
    expect(depois.slice(5).map((t) => [t.chave, t.cor, t.id])).toEqual([
      ['contato_articulador', 'amarelo', 6],
      ['observacao_formacao', 'amarelo', 7],
    ]);
    // Nada sumiu (decisão 57).
    expect(depois).toHaveLength(antes.length + 2);
  });

  it('decisão 42 só cancela as tarefas do vermelho: o Comitê que muda amarelo para vermelho (ou para verde) no mesmo ciclo deixa as do amarelo abertas', () => {
    const amarelo6 = decisao({ cor_sugerida: 'amarelo', cor_publicada: 'amarelo', origem: 'comite_ordinario', publicada_em: '2026-12-02' });
    const doAmarelo = tarefasDepoisDaPublicacao([], null, amarelo6);
    for (const cor of ['vermelho', 'verde'] as const) {
      const muda = { ...amarelo6, cor_publicada: cor, justificativa: 'Mudou de ideia.', publicada_em: '2026-12-03' };
      const depois = tarefasDepoisDaPublicacao(doAmarelo, amarelo6, muda);
      expect(depois.slice(0, 2)).toEqual(doAmarelo);
      expect(depois.some((t) => t.encerramento?.motivo === 'cancelada_comite')).toBe(false);
    }
  });

  it('a mesma cor publicada de novo no ciclo seguinte reabre todas as tarefas; as abertas de antes ficam substituídas', () => {
    const amarelo5 = decisao({ ciclo: '2026.5', cor_sugerida: 'amarelo', cor_publicada: 'amarelo', origem: 'comite_ordinario', publicada_em: '2026-11-06' });
    const antes = tarefasDepoisDaPublicacao([], null, amarelo5);
    const amarelo6 = { ...amarelo5, ciclo: '2026.6', publicada_em: '2027-01-08' };
    const depois = tarefasDepoisDaPublicacao(antes, amarelo5, amarelo6);
    expect(depois.filter(tarefaAberta).map((t) => [t.chave, t.criada_em])).toEqual([
      ['contato_articulador', '2027-01-08'],
      ['observacao_formacao', '2027-01-08'],
    ]);
    expect(depois.filter((t) => t.encerramento?.motivo === 'substituida').map((t) => t.criada_em)).toEqual(['2026-11-06', '2026-11-06']);
    expect(new Set(depois.map((t) => t.id)).size).toBe(4);
  });

  it('as tarefas substituídas aparecem no gerador (amarelo publicado em ciclos seguidos)', () => {
    expect(dados.tarefas.some((t) => t.encerramento?.motivo === 'substituida')).toBe(true);
  });

  describe('aplicarVermelhoAutomatico (o registro de um dado na sessão)', () => {
    const tranquilo = situacoes.find((s) => s.cor_vigente === 'verde' && s.ciclos.at(-1)?.resultado.cor === 'verde')!.municipio;
    const comReclamacao = (d: DadosSemaforo, data: string, tipo: 'leve' | 'reclamacao' = 'reclamacao'): DadosSemaforo => ({
      ...d,
      ocorrencias: [
        ...d.ocorrencias,
        {
          id: d.ocorrencias.length + 1000,
          municipio: tranquilo,
          data,
          registrada_em: `${data}T09:00:00-03:00`,
          respondida_em: null,
          origem: 'fluxo_unico',
          tipo,
        },
      ],
    });

    it('uma reclamação muda a cor oficial na hora, com as tarefas nascendo na data dela', () => {
      const depois = aplicarVermelhoAutomatico(dados, comReclamacao(dados, '2026-12-03'), tranquilo, '2026-12-03');
      const s = avaliarMunicipio(depois, tranquilo);
      expect(s).toMatchObject({ cor_vigente: 'vermelho', aguardando_comite: true });
      expect(s.decisao_vigente).toMatchObject({ origem: 'vermelho_automatico', publicada_em: '2026-12-03', ciclo: '2026.6' });
      expect(depois.tarefas.filter((t) => t.municipio === tranquilo && t.criada_em === '2026-12-03')).toHaveLength(5);
    });

    it('sem vermelho na hora, nada muda', () => {
      const comLeve = comReclamacao(dados, '2026-12-03', 'leve');
      expect(aplicarVermelhoAutomatico(dados, comLeve, tranquilo, '2026-12-03')).toBe(comLeve);
    });

    it('depois que o Comitê desfez, o mesmo alerta não volta sozinho; um alerta novo volta', () => {
      const vermelho = aplicarVermelhoAutomatico(dados, comReclamacao(dados, '2026-12-03'), tranquilo, '2026-12-03');
      const desfeito: DadosSemaforo = {
        ...vermelho,
        decisoes: [
          ...vermelho.decisoes,
          decisao({ municipio: tranquilo, origem: 'comite_extraordinario', cor_publicada: 'amarelo', justificativa: 'Resolvido.', publicada_em: REF }),
        ],
      };
      // Segunda reclamação: o indicador de ocorrências já estava em vermelho quando o Comitê decidiu.
      const outra = comReclamacao(desfeito, REF);
      expect(aplicarVermelhoAutomatico(desfeito, outra, tranquilo, REF)).toBe(outra);
      // NPS em vermelho é um alerta novo.
      const comNps: DadosSemaforo = {
        ...outra,
        respostas: [
          ...outra.respostas,
          {
            id: 99999,
            municipio: tranquilo,
            projeto: dados.municipios.find((x) => x.id === tranquilo)!.projetos[0]!.id,
            ciclo: '2026.6',
            respondida_em: REF,
            no_prazo: true,
            funcao_respondente: 'Articulador(a) municipal',
            identificacao: null,
            itens: [5, 5, 5, 5, 5, 5],
            nps: 0,
            comentario: '',
          },
        ],
      };
      const deNovo = aplicarVermelhoAutomatico(outra, comNps, tranquilo, REF);
      expect(avaliarMunicipio(deNovo, tranquilo).decisao_vigente).toMatchObject({ origem: 'vermelho_automatico', publicada_em: REF });
    });
  });

  it('criarTarefas e tarefasDepoisDaPublicacao dão ids seguidos a partir do maior', () => {
    expect(criarTarefas('amarelo', 1, REF, 10).map((t) => t.id)).toEqual([10, 11]);
  });
});

describe('os ids que o e2e da Integra usa (e2e/checklist/integra-telas.spec.ts)', () => {
  it('a ficha do vermelho com prazo hoje abre pelo id 5; o coordenador 101 tem municípios para mover e o 117 não tem', () => {
    const h = HISTORIAS_SEMAFORO.vermelho_prazo_hoje;
    expect(dados.municipios.find((m) => m.nome === h.nome && m.uf === h.uf)?.id).toBe(5);
    const carteira = (id: number) => ica.base.atendimentos.filter((a) => a.coordenador === id);
    expect(carteira(101).length).toBeGreaterThan(0);
    expect(carteira(117)).toEqual([]);
  });
});

describe('reuniões de escuta simuladas caem em dia útil (decisões 33, 34 e 48: os prazos contam em dias úteis)', () => {
  it('nenhuma reunião de escuta cai em sábado ou domingo', () => {
    const fimDeSemana = dados.reunioes.filter((r) => [0, 6].includes(new Date(`${r.data}T00:00:00Z`).getUTCDay()));
    expect(fimDeSemana.map((r) => r.data)).toEqual([]);
  });
});

describe('leitura do protótipo (Para validar): sair do vermelho pelo ciclo não encerra as tarefas do vermelho', () => {
  it('Sobral-CE, amarelo em recuperação, continua com a visita técnica do vermelho aberta até 15/02/2027 (decisão 57: nada some)', () => {
    const sobral = municipio(HISTORIAS_SEMAFORO.em_recuperacao);
    expect(avaliarMunicipio(dados, sobral.id).cor_vigente).toBe('amarelo');
    const abertas = dados.tarefas.filter((t) => t.municipio === sobral.id && t.cor === 'vermelho' && tarefaAberta(t));
    // Rodada 3: 14/02/2027 é domingo; o prazo em meses passa para a segunda-feira.
    expect(abertas.map((t) => [t.chave, t.criada_em, t.prazo_em])).toEqual([['visita_tecnica', '2026-08-14', '2027-02-15']]);
  });

  it('rodada 5 (decisões 32 e 39): a ocorrência leve de Pereiro-CE de 06/06/2026 ainda é um amarelo no ciclo atual; com a média e o NPS em amarelo, são três', () => {
    const pereiro = municipio({ nome: 'Pereiro', uf: 'CE' });
    const inicio = periodoDoCiclo(dados.ciclo_atual).inicio;
    expect(dados.ocorrencias.filter((o) => o.municipio === pereiro.id).map((o) => [o.data, o.tipo])).toEqual([['2026-06-06', 'leve']]);
    expect('2026-06-06' < inicio).toBe(true);
    const atual = avaliarMunicipio(dados, pereiro.id).ciclos.at(-1)!.resultado;
    expect(atual.avaliacoes.find((a) => a.indicador === 'ocorrencias')).toMatchObject({ cor: 'amarelo', texto: '1 leve' });
    // A ocorrência de outro ciclo entra como um dos três amarelos "do mesmo ciclo" (Para validar).
    const r = classificar(
      {
        media_pesquisa: 3.5,
        nps: 8,
        cronograma: 100,
        ocorrencias: { leves: 1, reclamacoes: 0 },
        resposta_pesquisa: { ciclo_atual: true, ciclo_anterior: true },
      },
      [],
    );
    expect(r).toMatchObject({ cor: 'vermelho', motivo: 'tres_amarelos' });
  });

  it('feriado em dia de semana conta como dia útil: a devolutiva de Horizonte-CE (30/11) vence em 11/01/2027, passando por 25/12 e 01/01', () => {
    expect(somarDiasUteis('2026-11-30', 30)).toBe('2027-01-11');
    const horizonte = municipio(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const devolutiva = dados.tarefas.find((t) => t.municipio === horizonte.id && t.chave === 'devolutiva' && tarefaAberta(t));
    expect(devolutiva).toMatchObject({ criada_em: '2026-11-30', prazo_em: '2027-01-11' });
  });
});

describe('rodada 4: correções dos dados simulados', () => {
  const ITAQUIRAI = { nome: 'Itaquiraí', uf: 'MS' };

  it('decisão 35: a cor publicada em 31/12/2026 dá a observação em 01/03/2027 (28/02/2027 é domingo; passa para a segunda)', () => {
    const observacao = criarTarefas('amarelo', 1, '2026-12-31').find((t) => t.chave === 'observacao_formacao');
    expect(observacao?.prazo_em).toBe('2027-03-01');
  });

  it('Itaquiraí-MS: antes do 1º ciclo do projeto (2026.4) não há cor sugerida; no 1º ciclo, o ciclo anterior fica sem dado', () => {
    const m = municipio(ITAQUIRAI);
    expect(m.projetos.map((p) => p.desde)).toEqual(m.projetos.map(() => '2026.4'));
    const ciclos = avaliarMunicipio(dados, m.id).ciclos;
    expect(ciclos.filter((c) => c.antes_do_projeto).map((c) => c.ciclo)).toEqual(['2025.6', '2026.1', '2026.2', '2026.3']);
    expect(valoresPorProjeto(dados, m.id, '2026.3', periodoDoCiclo('2026.3').fim)).toEqual([]);
    const primeiro = valoresPorProjeto(dados, m.id, '2026.4', periodoDoCiclo('2026.4').fim);
    expect(primeiro.map((p) => p.resposta_pesquisa.ciclo_anterior)).toEqual(m.projetos.map(() => null));
    // Os outros municípios têm projeto desde antes do histórico.
    const outros = situacoes.filter((s) => s.municipio !== m.id);
    expect(outros.flatMap((s) => s.ciclos.filter((c) => c.antes_do_projeto))).toEqual([]);
  });

  it('os ids de reuniões, respostas, relatórios, ocorrências e tarefas são únicos', () => {
    for (const lista of [dados.reunioes, dados.respostas, dados.relatorios, dados.ocorrencias, dados.tarefas]) {
      const ids = lista.map((x) => x.id);
      expect(new Set(ids).size).toBe(ids.length);
    }
  });

  it('nenhum município tem duas reuniões de escuta a menos de 30 dias uma da outra', () => {
    const perto: string[] = [];
    for (const m of dados.municipios) {
      const datas = dados.reunioes.filter((r) => r.municipio === m.id).map((r) => r.data).sort();
      for (let i = 1; i < datas.length; i++) {
        const dias = (Date.parse(datas[i]!) - Date.parse(datas[i - 1]!)) / 86_400_000;
        if (dias < 30) perto.push(`${m.nome}-${m.uf}: ${datas[i - 1]} e ${datas[i]}`);
      }
    }
    expect(perto).toEqual([]);
  });

  it('a periodicidade da reunião vem da cor em vigor no dia: semestral no verde, trimestral no amarelo e no vermelho', () => {
    for (const r of dados.reunioes) {
      const cor = dados.decisoes.filter((d) => d.municipio === r.municipio && d.publicada_em <= r.data).at(-1)?.cor_publicada ?? 'verde';
      expect(r.periodicidade, `${r.municipio} ${r.data}`).toBe(cor === 'verde' ? 'semestral' : 'trimestral');
    }
  });

  it('Horizonte-CE: uma reunião de escuta só depois da reclamação, a de 04/12, com a ata a registrar', () => {
    const h = municipio(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const recentes = dados.reunioes.filter((r) => r.municipio === h.id && r.data >= '2026-11-01');
    expect(recentes.map((r) => [r.data, r.ata_em])).toEqual([['2026-12-04', null]]);
  });
});
