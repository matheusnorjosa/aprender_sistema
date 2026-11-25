/**
 * Dados simulados do Semáforo: determinísticos, sobre os municípios reais do relatório de deslocamento,
 * com as pessoas fictícias do ICA, e com a história pronta da demonstração de 07/12/2026:
 * um vermelho com prazo vencendo hoje, um em recuperação, um que não respondeu a pesquisa em dois
 * ciclos e uma cor que o Comitê alterou com justificativa.
 */
import { describe, expect, it } from 'vitest';
import { contarNomesReais, guardaDeNomesReaisAtiva } from '../../__tests__/nomesReais';
import { DESLOCAMENTO_MUNICIPIOS } from '../../dados/deslocamento';
import { gerarDadosSimulados } from '../../dados/gerador';
import {
  CICLO_ATUAL_SEMAFORO,
  DATA_REFERENCIA_SEMAFORO,
  HISTORIAS_SEMAFORO,
  avaliarMunicipio,
  cicloAnterior,
  gerarDadosSemaforo,
  mesesCurtosDoCiclo,
  mesesDoCiclo,
  periodoDoCiclo,
} from '../dados';
import { estadoDaTarefa, validarDecisao } from '../regras';

const dados = gerarDadosSemaforo();
const ica = gerarDadosSimulados();
const REF = DATA_REFERENCIA_SEMAFORO;
const DATA = /^\d{4}-\d{2}-\d{2}$/;

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
    expect(contarNomesReais(JSON.stringify({ ...dados, municipios: [] }))).toBe(0);
  });

  it('formatos das coletas: datas AAAA-MM-DD, 6 itens de 1 a 5, nota de 0 a 10, nada depois de hoje', () => {
    for (const r of dados.respostas) {
      expect(r.respondida_em).toMatch(DATA);
      expect(r.respondida_em <= REF).toBe(true);
      expect(r.itens).toHaveLength(6);
      expect(r.itens.every((i) => Number.isInteger(i) && i >= 1 && i <= 5)).toBe(true);
      expect(Number.isInteger(r.nps) && r.nps >= 0 && r.nps <= 10).toBe(true);
      expect(r.respondida_em <= periodoDoCiclo(r.ciclo).prazo_pesquisa).toBe(r.no_prazo);
    }
    for (const o of dados.ocorrencias) expect(o.data <= REF && DATA.test(o.data)).toBe(true);
    for (const r of dados.reunioes) expect(r.data <= REF && DATA.test(r.data)).toBe(true);
    for (const r of dados.relatorios) {
      expect(r.mes).toMatch(/^\d{4}-\d{2}$/);
      expect(r.formacoes_realizadas).toBeLessThanOrEqual(r.formacoes_previstas);
      expect(r.visitas_realizadas).toBeLessThanOrEqual(r.visitas_previstas);
    }
  });

  it('todo município com coordenador tem relatório de cada mês (nov/2025 a nov/2026); todos têm reunião semestral', () => {
    for (const m of dados.municipios) {
      const meses = dados.relatorios.filter((r) => r.municipio === m.id).map((r) => r.mes);
      if (m.coordenador === null) {
        // Sem coordenador, ninguém entrega relatório: o cronograma fica "sem dado".
        expect(meses).toEqual([]);
        continue;
      }
      expect(meses).toHaveLength(13);
      expect(meses[0]).toBe('2025-11');
      expect(meses.at(-1)).toBe('2026-11');
      expect(dados.relatorios.filter((r) => r.municipio === m.id).every((r) => r.coordenador === m.coordenador)).toBe(true);
      const semestrais = dados.reunioes.filter((r) => r.municipio === m.id && r.periodicidade === 'semestral');
      expect(semestrais.length).toBeGreaterThanOrEqual(2);
    }
  });

  it('o Comitê publicou os 6 ciclos fechados de todos; a cor sugerida guardada é a das regras', () => {
    for (const s of situacoes) {
      const fechados = s.ciclos.slice(0, 6);
      expect(fechados.every((c) => c.decisao !== null)).toBe(true);
      for (const c of fechados) expect(c.decisao?.cor_sugerida).toBe(c.resultado.cor);
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

  it('tarefas: as de prazo passado foram concluídas; só uma vence hoje', () => {
    expect(dados.tarefas.length).toBeGreaterThan(0);
    for (const t of dados.tarefas) {
      if (t.prazo_em < REF) {
        expect(t.concluida_em).not.toBeNull();
        expect(t.concluida_em! >= t.criada_em && t.concluida_em! <= t.prazo_em).toBe(true);
      } else {
        expect(t.concluida_em).toBeNull();
      }
    }
    expect(dados.tarefas.filter((t) => estadoDaTarefa(t, REF) === 'vence_hoje')).toHaveLength(1);
  });
});

describe('a história da demonstração', () => {
  it('vermelho imediato por reclamação, com a reunião com a Secretaria vencendo hoje', () => {
    const m = municipio(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const s = avaliarMunicipio(dados, m.id);
    const atual = s.ciclos.at(-1);
    expect(atual?.ciclo).toBe('2026.6');
    expect(atual?.resultado.cor).toBe('vermelho');
    expect(atual?.resultado.vermelho_imediato).toBe(true);
    expect(atual?.resultado.decisivos).toEqual(['ocorrencias']);
    // Comitê extraordinário, sem esperar o fim do ciclo.
    expect(atual?.decisao).toMatchObject({ cor_sugerida: 'vermelho', cor_publicada: 'vermelho', publicada_em: '2026-12-02' });
    expect(s.cor_vigente).toBe('vermelho');
    expect(s.ciclos[5]?.decisao?.cor_publicada).toBe('amarelo');

    const hoje = dados.tarefas.filter((t) => estadoDaTarefa(t, REF) === 'vence_hoje');
    expect(hoje).toEqual([
      expect.objectContaining({ municipio: m.id, chave: 'reuniao_secretaria', criada_em: '2026-12-02', prazo_em: REF }),
    ]);
    const contato = dados.tarefas.find((t) => t.municipio === m.id && t.chave === 'contato_48h');
    expect(contato && estadoDaTarefa(contato, REF)).toBe('concluida');
  });

  it('em recuperação: vermelho em 2026.4, ciclo limpo em 2026.5, publicado amarelo "em recuperação"', () => {
    const m = municipio(HISTORIAS_SEMAFORO.em_recuperacao);
    const s = avaliarMunicipio(dados, m.id);
    expect(s.ciclos[4]?.decisao?.cor_publicada).toBe('vermelho');
    expect(s.ciclos[5]?.resultado).toMatchObject({ cor: 'amarelo', motivo: 'em_recuperacao', ciclos_limpos: 1 });
    expect(s.ciclos[5]?.decisao?.cor_publicada).toBe('amarelo');
    expect(s.cor_vigente).toBe('amarelo');
    // É o único "em recuperação" publicado: a história não se perde no meio de outros.
    expect(situacoes.filter((x) => x.ciclos[5]?.resultado.em_recuperacao).map((x) => x.municipio)).toEqual([m.id]);
  });

  it('não respondeu a pesquisa em 2026.4 nem em 2026.5: vermelho pela resposta', () => {
    const m = municipio(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos);
    expect(dados.respostas.filter((r) => r.municipio === m.id && ['2026.4', '2026.5'].includes(r.ciclo))).toEqual([]);
    const s = avaliarMunicipio(dados, m.id);
    expect(s.ciclos[4]?.resultado.cor).toBe('amarelo');
    const c5 = s.ciclos[5]?.resultado;
    expect(c5?.cor).toBe('vermelho');
    expect(c5?.decisivos).toEqual(['resposta_pesquisa']);
    expect(c5?.avaliacoes.find((a) => a.indicador === 'resposta_pesquisa')?.texto).toBe('Não respondeu em dois ciclos seguidos');
    expect(s.cor_vigente).toBe('vermelho');
  });

  it('ciclo atual em andamento (pesquisa até 20/12) não conta como ciclo sem alerta', () => {
    // Sem resposta em 2026.6 até hoje: segue vermelho, não "melhorou".
    const jequie = avaliarMunicipio(dados, municipio(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos).id).ciclos.at(-1)?.resultado;
    expect(jequie).toMatchObject({ cor: 'vermelho', motivo: 'ciclo_em_andamento', em_recuperacao: false });
    // 1 ciclo fechado sem alerta (2026.5): segue amarelo em recuperação, não verde.
    const sobral = avaliarMunicipio(dados, municipio(HISTORIAS_SEMAFORO.em_recuperacao).id).ciclos.at(-1)?.resultado;
    expect(sobral).toMatchObject({ cor: 'amarelo', motivo: 'ciclo_em_andamento', em_recuperacao: true, ciclos_limpos: 1 });
    const porCor = (cor: string) => situacoes.filter((x) => x.ciclos.at(-1)?.resultado.cor === cor).length;
    expect([porCor('vermelho'), porCor('amarelo'), porCor('verde')]).toEqual([2, 8, 78]);
  });

  it('o Comitê alterou uma cor sugerida, com justificativa', () => {
    const m = municipio(HISTORIAS_SEMAFORO.alterada_pelo_comite);
    const d = avaliarMunicipio(dados, m.id).ciclos[5]?.decisao;
    expect(d).toMatchObject({ cor_sugerida: 'amarelo', cor_publicada: 'verde' });
    expect(d?.justificativa?.trim()).not.toBe('');
    const alteradas = dados.decisoes.filter((x) => x.cor_sugerida !== x.cor_publicada);
    expect(alteradas).toEqual([d]);
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
