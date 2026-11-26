/**
 * Regras do Semáforo de Risco Municipal.
 *
 * Fonte: Requisitos_Modulo_Semaforo_Risco_Municipal.pdf (NFP, nov/2026). Cada `it.each` abaixo é uma linha
 * das tabelas do PDF: seção 3 (os 5 indicadores e seus limites), seção 4 (regras da cor), seção 5 (tarefas e
 * prazos por cor) e seção 7 (cor sugerida × confirmada, seta ▲▼ entre ciclos).
 */
import { describe, expect, it } from 'vitest';
import type {
  CicloPublicado,
  Ocorrencia,
  RelatorioMensal,
  RespostaPesquisa,
  TarefaResposta,
  ValoresIndicadores,
} from '../tipos';
import {
  INDICADORES,
  LIMITES,
  RESPOSTA_POR_COR,
  ROTULO_INDICADOR,
  ROTULO_ORIGEM,
  avaliarIndicadores,
  META_RESPOSTA_HORAS,
  classificar,
  contarOcorrencias,
  corCronograma,
  corDaPesquisa,
  corMediaPesquisa,
  corNps,
  corOcorrencias,
  corRespostaPesquisa,
  criarTarefas,
  divergem,
  duasCasas,
  estadoDaTarefa,
  explicarCor,
  horasEntre,
  inicioDasFormacoesNoAno,
  mediaDaPesquisa,
  mediaNps,
  mudancaEntreCiclos,
  ocorrenciasDoAno,
  ocorrenciasForaDaContagem,
  percentualCronograma,
  prazoDaAta,
  respondeuNoPrazo,
  resumoNps,
  reuniaoEmDia,
  situacaoDaReuniao,
  somarDiasUteis,
  somarMeses,
  tarefaAberta,
  tempoDeResposta,
  textoDataHora,
  textoDaReuniao,
  textoHoras,
  textoResumoNps,
  textoSemDado,
  validarDecisao,
} from '../regras';

/** Tudo verde: o ponto de partida dos testes de regra; cada teste muda só o que importa. */
function valores(parcial: Partial<ValoresIndicadores> = {}): ValoresIndicadores {
  return {
    media_pesquisa: 4.5,
    nps: 9.5,
    cronograma: 95,
    ocorrencias: { leves: 0, reclamacoes: 0 },
    resposta_pesquisa: { ciclo_atual: true, ciclo_anterior: true },
    ...parcial,
  };
}

const AMARELO = {
  media_pesquisa: 3.5,
  nps: 8,
  cronograma: 80,
  ocorrencias: { leves: 1, reclamacoes: 0 },
  resposta_pesquisa: { ciclo_atual: false, ciclo_anterior: true },
} satisfies ValoresIndicadores;

function publicado(cor_publicada: CicloPublicado['cor_publicada'], limpo: boolean, ciclo = '2026.4'): CicloPublicado {
  return { ciclo, limpo, cor_publicada };
}

let proximoId = 1;
function resposta(itens: number[], nps: number, no_prazo = true): RespostaPesquisa {
  return {
    id: proximoId++,
    municipio: 1,
    projeto: 1,
    ciclo: '2026.6',
    respondida_em: '2026-11-10',
    no_prazo,
    funcao_respondente: 'Diretor(a) de ensino',
    identificacao: null,
    itens,
    nps,
    comentario: '',
  };
}

function relatorio(fp: number, fr: number, vp: number, vr: number, mes = '2026-10'): RelatorioMensal {
  return {
    id: proximoId++,
    municipio: 1,
    projeto: 1,
    coordenador: 1,
    mes,
    formacoes_previstas: fp,
    formacoes_realizadas: fr,
    visitas_previstas: vp,
    visitas_realizadas: vr,
  };
}

function ocorrencia(data: string, tipo: Ocorrencia['tipo'] = 'leve'): Ocorrencia {
  return { id: proximoId++, municipio: 1, data, registrada_em: `${data}T09:00:00-03:00`, respondida_em: null, origem: 'fluxo_unico', tipo };
}

describe('Seção 3: os 5 indicadores', () => {
  it('são 5, na ordem da tabela do PDF, com os limites escritos para a tela', () => {
    expect(INDICADORES).toEqual(['media_pesquisa', 'nps', 'cronograma', 'ocorrencias', 'resposta_pesquisa']);
    expect(INDICADORES.map((i) => ROTULO_INDICADOR[i])).toEqual([
      'Média da pesquisa do articulador',
      'Nota NPS do articulador',
      'Cronograma cumprido',
      'Ocorrências via Relacionamento ou distribuidor',
      'Resposta à pesquisa',
    ]);
    // Decisão 30: a cor sai do número exato, então a régua não pode ter buraco entre 3,9 e 4,0.
    expect(LIMITES.media_pesquisa).toEqual({ verde: '4,0 ou mais', amarelo: '3,0 a menos de 4,0', vermelho: 'menos de 3,0' });
    expect(LIMITES.nps).toEqual({ verde: 'média 9,0 ou mais', amarelo: 'média de 7,0 a menos de 9,0', vermelho: 'média menos de 7,0' });
    expect(LIMITES.cronograma).toEqual({ verde: '90% ou mais', amarelo: '70% a menos de 90%', vermelho: 'menos de 70%' });
    expect(LIMITES.ocorrencias.verde).toBe('Nenhuma');
    expect(LIMITES.resposta_pesquisa.vermelho).toBe('Não respondeu em dois ciclos seguidos');
  });

  describe('Média da pesquisa do articulador: verde 4,0 ou mais · amarelo 3,0 a menos de 4,0 · vermelho menos de 3,0', () => {
    it.each([
      [5, 'verde'],
      [4, 'verde'],
      [3.9, 'amarelo'],
      [3, 'amarelo'],
      [2.9, 'vermelho'],
      [1, 'vermelho'],
      [null, 'sem_dado'],
    ] as const)('%s → %s', (media, cor) => {
      expect(corMediaPesquisa(media)).toBe(cor);
    });

    it('decisão 30: a cor sai do número exato, não do arredondado (3,95 é amarelo; 2,95 é vermelho)', () => {
      expect(corMediaPesquisa(3.95)).toBe('amarelo');
      expect(corMediaPesquisa(3.999)).toBe('amarelo');
      expect(corMediaPesquisa(2.95)).toBe('vermelho');
      expect(corMediaPesquisa(2.999)).toBe('vermelho');
    });

    it('decisão 30: a tela mostra 2 casas (3,95 aparece "3,95", não "4,0")', () => {
      expect(duasCasas(3.95)).toBe('3,95');
      expect(duasCasas(4)).toBe('4,00');
      expect(duasCasas(8.5)).toBe('8,50');
    });

    it('é a média dos 6 itens de todas as respostas do ciclo; sem resposta, sem dado', () => {
      expect(mediaDaPesquisa([resposta([5, 5, 5, 5, 5, 5], 10), resposta([3, 3, 3, 3, 3, 3], 5)])).toBe(4);
      expect(mediaDaPesquisa([resposta([4, 4, 4, 3, 3, 3], 8)])).toBe(3.5);
      expect(mediaDaPesquisa([])).toBeNull();
    });
  });

  describe('Nota NPS do articulador (média): verde 9,0 ou mais · amarelo 7,0 a menos de 9,0 · vermelho menos de 7,0', () => {
    it.each([
      [10, 'verde'],
      [9, 'verde'],
      [8, 'amarelo'],
      [7, 'amarelo'],
      [6, 'vermelho'],
      [0, 'vermelho'],
      [null, 'sem_dado'],
    ] as const)('nota %s → %s', (nota, cor) => {
      expect(corNps(nota)).toBe(cor);
    });

    it('decisão 30: a média exata fica na faixa de baixo até chegar à nota de cima (8,96 amarelo; 6,99 vermelho)', () => {
      expect(corNps(8.9)).toBe('amarelo');
      expect(corNps(8.5)).toBe('amarelo');
      expect(corNps(6.9)).toBe('vermelho');
      expect(corNps(8.96)).toBe('amarelo');
      expect(corNps(6.99)).toBe('vermelho');
    });

    it('é a média das notas do ciclo (decisão do PDF para vários respondentes); sem resposta, sem dado', () => {
      expect(mediaNps([resposta([5, 5, 5, 5, 5, 5], 10), resposta([4, 4, 4, 4, 4, 4], 7)])).toBe(8.5);
      expect(mediaNps([])).toBeNull();
    });

    it('decisão 31: a tela mostra a maior nota, a menor e a média; a cor sai da média (notas 8 e 9 → amarelo)', () => {
      const r = resumoNps([resposta([5, 5, 5, 5, 5, 5], 8), resposta([5, 5, 5, 5, 5, 5], 9)]);
      expect(r).toEqual({ maior: 9, menor: 8, media: 8.5 });
      expect(textoResumoNps(r!)).toBe('Maior 9, menor 8, média 8,50');
      expect(corNps(r!.media)).toBe('amarelo');
      expect(resumoNps([])).toBeNull();
    });
  });

  describe('Cronograma cumprido: verde 90% ou mais · amarelo 70% a menos de 90% · vermelho menos de 70%', () => {
    it.each([
      [100, 'verde'],
      [90, 'verde'],
      [89, 'amarelo'],
      [70, 'amarelo'],
      [69, 'vermelho'],
      [0, 'vermelho'],
      [null, 'sem_dado'],
    ] as const)('%s%% → %s', (pct, cor) => {
      expect(corCronograma(pct)).toBe(cor);
    });

    it('decisão 30: a cor sai do percentual exato (89,5% é amarelo; 69,5% é vermelho)', () => {
      expect(corCronograma(89.5)).toBe('amarelo');
      expect(corCronograma(89.99)).toBe('amarelo');
      expect(corCronograma(69.5)).toBe('vermelho');
    });

    it('formações e visitas realizadas ÷ previstas no período; nada previsto = sem dado', () => {
      expect(percentualCronograma([relatorio(8, 6, 2, 2), relatorio(8, 8, 2, 1)])).toBe(85);
      expect(percentualCronograma([relatorio(0, 0, 0, 0)])).toBeNull();
      expect(percentualCronograma([])).toBeNull();
    });
  });

  describe('Ocorrências: verde nenhuma · amarelo uma leve · vermelho reclamação ou duas ou mais', () => {
    it.each([
      [0, 0, 'verde'],
      [1, 0, 'amarelo'],
      [0, 1, 'vermelho'],
      [1, 1, 'vermelho'],
      [2, 0, 'vermelho'],
      [3, 0, 'vermelho'],
    ] as const)('%s leve(s) e %s reclamação(ões) → %s', (leves, reclamacoes, cor) => {
      expect(corOcorrencias({ leves, reclamacoes })).toBe(cor);
    });

    describe('decisão 32: contam desde a 1ª formação do ano no município e zeram no ano seguinte', () => {
      // Formações de 2026 começaram em março (fevereiro previsto, nada realizado).
      const relatorios = [
        relatorio(4, 4, 1, 1, '2025-09'),
        relatorio(3, 0, 1, 0, '2026-02'),
        relatorio(4, 3, 1, 1, '2026-03'),
        relatorio(4, 4, 1, 1, '2026-10'),
      ];

      it('a contagem começa no primeiro dia do mês da 1ª formação realizada no ano (o relatório é mensal)', () => {
        expect(inicioDasFormacoesNoAno(relatorios, 2026)).toBe('2026-03-01');
        expect(inicioDasFormacoesNoAno(relatorios, 2025)).toBe('2025-09-01');
        expect(inicioDasFormacoesNoAno(relatorios, 2024)).toBeNull();
      });

      it('conta de março até a data de referência, das coletas 3, 4 e 5 (não só os 3 últimos meses)', () => {
        const lista = [
          ocorrencia('2026-02-10'),
          ocorrencia('2026-03-02'),
          { ...ocorrencia('2026-05-20', 'reclamacao'), origem: 'momento_reservado' as const },
          { ...ocorrencia('2026-11-24'), origem: 'reuniao_escuta' as const },
          ocorrencia('2026-11-25'),
        ];
        const doAno = ocorrenciasDoAno(lista, relatorios, '2026-11-24');
        expect(doAno.map((o) => o.data)).toEqual(['2026-03-02', '2026-05-20', '2026-11-24']);
        expect(contarOcorrencias(doAno)).toEqual({ leves: 2, reclamacoes: 1 });
      });

      it('reclamação de setembro do ano anterior não conta em fevereiro, nem antes da 1ª formação do ano', () => {
        const lista = [ocorrencia('2025-09-20', 'reclamacao')];
        expect(ocorrenciasDoAno(lista, relatorios, '2025-12-31')).toHaveLength(1);
        expect(ocorrenciasDoAno(lista, relatorios, '2026-02-20')).toEqual([]);
        expect(ocorrenciasDoAno(lista, relatorios, '2026-03-20')).toEqual([]);
      });

      it('sem formação no ano até a data, nada conta (zero ocorrências: verde)', () => {
        expect(ocorrenciasDoAno([ocorrencia('2026-01-15', 'reclamacao')], relatorios, '2026-02-27')).toEqual([]);
        expect(corOcorrencias(contarOcorrencias([]))).toBe('verde');
      });

      it('decisão 32: as do ano de antes da 1ª formação (ou sem formação no ano) ficam guardadas e são contadas à parte', () => {
        const lista = [ocorrencia('2025-09-20', 'reclamacao'), ocorrencia('2026-02-10'), ocorrencia('2026-03-02'), ocorrencia('2026-11-25')];
        expect(ocorrenciasForaDaContagem(lista, relatorios, '2026-11-24').map((o) => o.data)).toEqual(['2026-02-10']);
        // Sem formação no ano até a data: todas as do ano ficam de fora, nenhuma conta.
        expect(ocorrenciasForaDaContagem([ocorrencia('2026-01-15', 'reclamacao')], relatorios, '2026-02-27')).toHaveLength(1);
      });

      it('decisão 57: zerar a contagem não apaga nada (a lista de entrada fica igual)', () => {
        const lista = [ocorrencia('2025-09-20', 'reclamacao'), ocorrencia('2026-03-05')];
        const copia = structuredClone(lista);
        ocorrenciasDoAno(lista, relatorios, '2026-11-24');
        expect(lista).toEqual(copia);
      });
    });
  });

  describe('Resposta à pesquisa: verde respondeu no prazo · amarelo não respondeu em um ciclo · vermelho dois seguidos', () => {
    it.each([
      [true, true, 'verde'],
      [true, false, 'verde'],
      [true, null, 'verde'],
      [false, true, 'amarelo'],
      [false, null, 'amarelo'],
      [false, false, 'vermelho'],
      [null, false, 'sem_dado'],
    ] as const)('ciclo atual %s, ciclo anterior %s → %s', (ciclo_atual, ciclo_anterior, cor) => {
      expect(corRespostaPesquisa({ ciclo_atual, ciclo_anterior })).toBe(cor);
    });

    it('respondeu = ao menos um articulador no prazo; com a pesquisa ainda aberta e ninguém no prazo, sem dado', () => {
      expect(respondeuNoPrazo([resposta([4, 4, 4, 4, 4, 4], 9, false), resposta([4, 4, 4, 4, 4, 4], 9)], true)).toBe(true);
      expect(respondeuNoPrazo([resposta([4, 4, 4, 4, 4, 4], 9, false)], true)).toBe(false);
      expect(respondeuNoPrazo([], true)).toBe(false);
      expect(respondeuNoPrazo([], false)).toBeNull();
      expect(respondeuNoPrazo([resposta([4, 4, 4, 4, 4, 4], 9)], false)).toBe(true);
    });
  });

  it('cada indicador sai com a cor e o valor escrito para a tela, com 2 casas (decisão 30)', () => {
    expect(
      avaliarIndicadores({
        media_pesquisa: 4.24,
        nps: 7,
        cronograma: 78.2,
        ocorrencias: { leves: 1, reclamacoes: 1 },
        resposta_pesquisa: { ciclo_atual: false, ciclo_anterior: false },
      }),
    ).toEqual([
      { indicador: 'media_pesquisa', cor: 'verde', texto: '4,24' },
      { indicador: 'nps', cor: 'amarelo', texto: '7,00' },
      { indicador: 'cronograma', cor: 'amarelo', texto: '78,20%' },
      { indicador: 'ocorrencias', cor: 'vermelho', texto: '1 reclamação e 1 leve' },
      { indicador: 'resposta_pesquisa', cor: 'vermelho', texto: 'Não respondeu em dois ciclos seguidos' },
    ]);
    const vazio = avaliarIndicadores(
      valores({ media_pesquisa: null, ocorrencias: { leves: 0, reclamacoes: 0 }, resposta_pesquisa: { ciclo_atual: null, ciclo_anterior: null } }),
    );
    expect(vazio.map((a) => a.texto)).toEqual(['Sem dado', '9,50', '95,00%', 'Nenhuma', 'Sem dado']);
    // O número que dá a cor é o mesmo que aparece: 89,5% aparece "89,50%" e é amarelo.
    expect(avaliarIndicadores(valores({ cronograma: 89.5 }))[2]).toEqual({ indicador: 'cronograma', cor: 'amarelo', texto: '89,50%' });
    expect(avaliarIndicadores(valores({ ocorrencias: { leves: 2, reclamacoes: 0 } }))[3]!.texto).toBe('2 leves');
  });

  it('decisão 32: sem nenhuma que conte, mas com ocorrência guardada de antes da 1ª formação, o texto não diz só "Nenhuma"', () => {
    expect(avaliarIndicadores(valores({ ocorrencias: { leves: 0, reclamacoes: 0, fora_da_contagem: 1 } }))[3]).toEqual({
      indicador: 'ocorrencias',
      cor: 'verde',
      texto: 'Nenhuma que conte (1 registrada antes da 1ª formação do ano)',
    });
    expect(avaliarIndicadores(valores({ ocorrencias: { leves: 0, reclamacoes: 0, fora_da_contagem: 2 } }))[3]!.texto).toBe(
      'Nenhuma que conte (2 registradas antes da 1ª formação do ano)',
    );
  });
});

describe('Seção 4: regras da cor', () => {
  it('tudo verde → verde, sem alerta', () => {
    const r = classificar(valores(), []);
    expect(r).toMatchObject({ cor: 'verde', motivo: 'sem_alerta', decisivos: [], limpo: true, em_recuperacao: false });
    expect(explicarCor(r)).toBe('Verde: nenhum indicador em amarelo ou vermelho.');
  });

  describe('vale o pior indicador', () => {
    it.each([
      ['media_pesquisa', { media_pesquisa: 3.5 }],
      ['nps', { nps: 8 }],
      ['cronograma', { cronograma: 80 }],
      ['ocorrencias', { ocorrencias: { leves: 1, reclamacoes: 0 } }],
      ['resposta_pesquisa', { resposta_pesquisa: { ciclo_atual: false, ciclo_anterior: true } }],
    ] as const)('um amarelo em %s → amarelo', (indicador, parcial) => {
      const r = classificar(valores(parcial), []);
      expect(r).toMatchObject({ cor: 'amarelo', motivo: 'pior_indicador', decisivos: [indicador], limpo: false });
    });

    it('dois amarelos → amarelo, com os dois como decisivos', () => {
      const r = classificar(valores({ nps: AMARELO.nps, cronograma: AMARELO.cronograma }), []);
      expect(r).toMatchObject({ cor: 'amarelo', motivo: 'pior_indicador', decisivos: ['nps', 'cronograma'] });
      expect(explicarCor(r)).toBe('Amarelo: Nota NPS do articulador e Cronograma cumprido em amarelo.');
    });
  });

  describe('vermelho imediato: basta um indicador em vermelho', () => {
    it.each([
      ['media_pesquisa', { media_pesquisa: 2.5 }],
      ['nps', { nps: 6 }],
      ['cronograma', { cronograma: 60 }],
      ['ocorrencias', { ocorrencias: { leves: 0, reclamacoes: 1 } }],
      ['resposta_pesquisa', { resposta_pesquisa: { ciclo_atual: false, ciclo_anterior: false } }],
    ] as const)('um vermelho em %s → vermelho na hora', (indicador, parcial) => {
      const r = classificar(valores(parcial), []);
      expect(r).toMatchObject({ cor: 'vermelho', motivo: 'indicador_vermelho', decisivos: [indicador], vermelho_imediato: true });
    });

    it('vale mesmo com o município verde e limpo no ciclo anterior, e a explicação diz qual indicador', () => {
      const r = classificar(valores({ nps: 5 }), [publicado('verde', true)]);
      expect(r.cor).toBe('vermelho');
      expect(explicarCor(r)).toBe('Vermelho: Nota NPS do articulador em vermelho.');
    });
  });

  describe('acúmulo de alertas: três ou mais amarelos no mesmo ciclo valem vermelho', () => {
    it('dois amarelos ainda são amarelo', () => {
      expect(classificar(valores({ media_pesquisa: AMARELO.media_pesquisa, nps: AMARELO.nps }), []).cor).toBe('amarelo');
    });

    it('três amarelos → vermelho, e também na hora (decisão 39)', () => {
      const r = classificar(
        valores({ media_pesquisa: AMARELO.media_pesquisa, nps: AMARELO.nps, cronograma: AMARELO.cronograma }),
        [],
      );
      expect(r).toMatchObject({
        cor: 'vermelho',
        motivo: 'tres_amarelos',
        decisivos: ['media_pesquisa', 'nps', 'cronograma'],
        vermelho_imediato: true,
      });
      expect(explicarCor(r)).toBe(
        'Vermelho: 3 indicadores em amarelo no mesmo ciclo (Média da pesquisa do articulador, Nota NPS do articulador e Cronograma cumprido).',
      );
    });

    it('cinco amarelos → vermelho', () => {
      expect(classificar(AMARELO, []).motivo).toBe('tres_amarelos');
    });

    it('decisão 39: no ciclo em andamento, três amarelos viram vermelho na hora, como um vermelho', () => {
      const tres = valores({ media_pesquisa: AMARELO.media_pesquisa, nps: AMARELO.nps, cronograma: AMARELO.cronograma });
      expect(classificar(tres, [publicado('verde', true)], { cicloFechado: false })).toMatchObject({
        cor: 'vermelho',
        vermelho_imediato: true,
      });
    });

    it('com um vermelho junto, o motivo é o vermelho', () => {
      const r = classificar({ ...AMARELO, nps: 3 }, []);
      expect(r).toMatchObject({ cor: 'vermelho', motivo: 'indicador_vermelho', decisivos: ['nps'] });
    });
  });

  describe('indicador sem dado fica fora da regra do pior', () => {
    it('sem dado não puxa a cor e a tela pode dizer quais ficaram de fora', () => {
      const r = classificar(valores({ cronograma: null, media_pesquisa: null }), []);
      expect(r).toMatchObject({ cor: 'verde', sem_dado: ['media_pesquisa', 'cronograma'], limpo: true });
      expect(r.avaliacoes.find((a) => a.indicador === 'cronograma')?.cor).toBe('sem_dado');
      expect(textoSemDado(r)).toBe(
        'Sem dado neste ciclo, fora da regra: Média da pesquisa do articulador e Cronograma cumprido.',
      );
    });

    it('sem dado não conta como amarelo no acúmulo (2 amarelos + 2 sem dado = amarelo)', () => {
      const r = classificar(
        valores({ media_pesquisa: null, cronograma: null, nps: AMARELO.nps, ocorrencias: AMARELO.ocorrencias }),
        [],
      );
      expect(r.cor).toBe('amarelo');
    });

    it('sem nenhum indicador sem dado, não há texto', () => {
      expect(textoSemDado(classificar(valores(), []))).toBeNull();
    });
  });

  describe('retorno ao verde só depois de dois ciclos bimestrais seguidos sem alerta', () => {
    it('vermelho no ciclo anterior + 1º ciclo limpo → amarelo "em recuperação"', () => {
      const r = classificar(valores(), [publicado('vermelho', false)]);
      expect(r).toMatchObject({ cor: 'amarelo', motivo: 'em_recuperacao', em_recuperacao: true, limpo: true, ciclos_limpos: 1 });
      expect(explicarCor(r)).toBe('Amarelo, em recuperação: 1 de 2 ciclos sem alerta para voltar ao verde.');
    });

    it('amarelo no ciclo anterior + 1º ciclo limpo → amarelo "em recuperação"', () => {
      expect(classificar(valores(), [publicado('amarelo', false)]).em_recuperacao).toBe(true);
    });

    it('2º ciclo limpo seguido → verde', () => {
      const r = classificar(valores(), [publicado('vermelho', false, '2026.4'), publicado('amarelo', true, '2026.5')]);
      expect(r).toMatchObject({ cor: 'verde', motivo: 'sem_alerta', em_recuperacao: false, ciclos_limpos: 2 });
    });

    it('um alerta no meio zera a contagem', () => {
      const r = classificar(valores(), [
        publicado('amarelo', true, '2026.3'),
        publicado('amarelo', false, '2026.4'),
        publicado('amarelo', true, '2026.5'),
      ]);
      expect(r).toMatchObject({ cor: 'verde', ciclos_limpos: 2 });
      const r2 = classificar(valores(), [publicado('amarelo', true, '2026.4'), publicado('amarelo', false, '2026.5')]);
      expect(r2).toMatchObject({ cor: 'amarelo', em_recuperacao: true, ciclos_limpos: 1 });
    });

    it('ciclo com alerta não é "em recuperação": vale a cor do pior indicador', () => {
      const r = classificar(valores({ nps: 8 }), [publicado('vermelho', false)]);
      expect(r).toMatchObject({ cor: 'amarelo', motivo: 'pior_indicador', em_recuperacao: false, ciclos_limpos: 0 });
    });

    it('verde publicado no ciclo anterior (ou primeiro ciclo) + ciclo limpo → verde direto', () => {
      expect(classificar(valores(), [publicado('verde', true)]).cor).toBe('verde');
      expect(classificar(valores(), []).cor).toBe('verde');
    });

    describe('ciclo em andamento: só ciclo fechado conta como ciclo sem alerta', () => {
      const aberto = { cicloFechado: false };
      const semPesquisa = valores({ media_pesquisa: null, nps: null, resposta_pesquisa: { ciclo_atual: null, ciclo_anterior: true } });

      it('em recuperação + ciclo aberto sem alerta → continua amarelo em recuperação, sem somar o ciclo aberto', () => {
        const r = classificar(semPesquisa, [publicado('vermelho', false, '2026.4'), publicado('amarelo', true, '2026.5')], aberto);
        expect(r).toMatchObject({ cor: 'amarelo', motivo: 'ciclo_em_andamento', em_recuperacao: true, limpo: true, ciclos_limpos: 1 });
        expect(explicarCor(r)).toBe(
          'Amarelo, em recuperação: 1 de 2 ciclos sem alerta para voltar ao verde. O ciclo em andamento só conta quando fechar.',
        );
      });

      it('vermelho publicado + ciclo aberto sem alerta → continua vermelho', () => {
        const r = classificar(semPesquisa, [publicado('vermelho', false, '2026.5')], aberto);
        expect(r).toMatchObject({ cor: 'vermelho', motivo: 'ciclo_em_andamento', em_recuperacao: false, ciclos_limpos: 0 });
        expect(explicarCor(r)).toBe('Vermelho: continua a cor publicada. O ciclo em andamento só conta quando fechar.');
      });

      it('verde publicado (ou sem histórico) + ciclo aberto sem alerta → verde', () => {
        expect(classificar(semPesquisa, [publicado('verde', true)], aberto)).toMatchObject({ cor: 'verde', motivo: 'sem_alerta' });
        expect(classificar(semPesquisa, [], aberto).cor).toBe('verde');
      });

      it('no ciclo aberto, o vermelho imediato e o amarelo valem na hora', () => {
        expect(classificar(valores({ nps: 5 }), [publicado('amarelo', true)], aberto)).toMatchObject({
          cor: 'vermelho',
          vermelho_imediato: true,
        });
        expect(classificar(valores({ nps: 8 }), [publicado('verde', true)], aberto).cor).toBe('amarelo');
      });

      // Seção 4 do PDF: no meio do ciclo a cor só muda para PIORAR ("Vermelho imediato"); sair do vermelho
      // espera o ciclo fechar. Uma nota pior não pode dar uma cor melhor.
      it('vermelho publicado + amarelo no ciclo aberto → continua vermelho, com o amarelo como motivo', () => {
        const r = classificar(valores({ nps: 8 }), [publicado('vermelho', false)], aberto);
        expect(r).toMatchObject({ cor: 'vermelho', motivo: 'ciclo_em_andamento', decisivos: ['nps'], em_recuperacao: false });
        expect(explicarCor(r)).toBe(
          'Vermelho: continua a cor publicada (Nota NPS do articulador em amarelo). O ciclo em andamento só conta quando fechar.',
        );
      });

      it.each([10, 9, 8, 7, 6])('vermelho publicado + NPS %d no ciclo aberto → nunca melhor que vermelho', (nps) => {
        expect(classificar(valores({ nps }), [publicado('vermelho', false)], aberto).cor).toBe('vermelho');
      });
    });
  });
});

describe('Seção 4: cor sugerida × cor confirmada pelo Comitê', () => {
  it('confirmar a sugestão não pede justificativa', () => {
    expect(validarDecisao('amarelo', 'amarelo', '')).toEqual({ valida: true, alterada: false, erros: [] });
  });

  it.each(['', '   ', null])('alterar a sugestão sem justificativa (%j) não vale', (justificativa) => {
    expect(validarDecisao('vermelho', 'amarelo', justificativa)).toEqual({
      valida: false,
      alterada: true,
      erros: ['A cor é diferente da sugerida (Vermelho). Escreva a justificativa do Comitê.'],
    });
  });

  it('alterar com justificativa vale', () => {
    expect(validarDecisao('vermelho', 'amarelo', 'Reclamação resolvida na reunião com a Secretaria.')).toEqual({
      valida: true,
      alterada: true,
      erros: [],
    });
  });
});

describe('Seção 7: a seta de mudança entre ciclos (▲ piorou, ▼ melhorou)', () => {
  it.each([
    ['verde', 'amarelo', 'piorou', '▲'],
    ['verde', 'vermelho', 'piorou', '▲'],
    ['amarelo', 'vermelho', 'piorou', '▲'],
    ['vermelho', 'amarelo', 'melhorou', '▼'],
    ['vermelho', 'verde', 'melhorou', '▼'],
    ['amarelo', 'verde', 'melhorou', '▼'],
    ['amarelo', 'amarelo', 'igual', ''],
    [null, 'vermelho', 'sem_anterior', ''],
  ] as const)('%s → %s: %s %s', (anterior, atual, mudanca, seta) => {
    expect(mudancaEntreCiclos(anterior, atual)).toMatchObject({ mudanca, seta });
  });

  it('a seta vem com o texto escrito (a cor nunca fala sozinha)', () => {
    expect(mudancaEntreCiclos('verde', 'vermelho').texto).toBe('Piorou: era verde');
    expect(mudancaEntreCiclos('vermelho', 'amarelo').texto).toBe('Melhorou: era vermelho');
    expect(mudancaEntreCiclos('verde', 'verde').texto).toBe('Sem mudança');
    expect(mudancaEntreCiclos(null, 'verde').texto).toBe('Primeiro ciclo');
  });
});

describe('Seção 5: tarefas e prazos por cor, contados a partir da publicação', () => {
  // 24/11/2026 é uma terça-feira.
  const PUBLICADA = '2026-11-24';

  it('verde: só o ciclo regular, sem tarefa com prazo', () => {
    expect(criarTarefas('verde', 7, PUBLICADA)).toEqual([]);
    expect(RESPOSTA_POR_COR.verde.rotina).toEqual(['Pesquisa a cada 2 meses', 'Reunião de escuta a cada 6 meses']);
  });

  it('amarelo: contato com o articulador em até 10 dias úteis e observação de formação no bimestre', () => {
    const tarefas = criarTarefas('amarelo', 7, PUBLICADA);
    expect(tarefas.map((t) => [t.chave, t.prazo_em])).toEqual([
      ['contato_articulador', '2026-12-08'],
      // Rodada 3: 24/01/2027 é domingo; o prazo em meses passa para a segunda-feira.
      ['observacao_formacao', '2027-01-25'],
    ]);
    expect(tarefas[0]).toMatchObject({ municipio: 7, cor: 'amarelo', criada_em: PUBLICADA, concluida_em: null, encerramento: null });
    expect(RESPOSTA_POR_COR.amarelo.quem_age).toBe('Gestora de referência e coordenador(es)');
    expect(RESPOSTA_POR_COR.amarelo.rotina).toEqual(['Reunião de escuta a cada 3 meses']);
  });

  it('cada tarefa tem id próprio, a partir do id dado (decisão 43: a mesma chave e data podem se repetir)', () => {
    expect(criarTarefas('vermelho', 7, PUBLICADA, 40).map((t) => t.id)).toEqual([40, 41, 42, 43, 44]);
    expect(criarTarefas('amarelo', 7, PUBLICADA).map((t) => t.id)).toEqual([1, 2]);
  });

  it('vermelho (decisões 33, 34 e 37): contato com o articulador em 2 dias úteis, Secretaria em 5, plano em 15, devolutiva em 30, visita no semestre', () => {
    expect(criarTarefas('vermelho', 7, PUBLICADA).map((t) => [t.chave, t.prazo_em])).toEqual([
      ['contato_48h', '2026-11-26'],
      ['reuniao_secretaria', '2026-12-01'],
      ['plano_acao', '2026-12-15'],
      ['devolutiva', '2027-01-05'],
      ['visita_tecnica', '2027-05-24'],
    ]);
    expect(RESPOSTA_POR_COR.vermelho.tarefas.map((t) => t.prazo_texto)).toEqual([
      'em 2 dias úteis',
      'em 5 dias úteis',
      'em 15 dias úteis',
      'em 30 dias úteis',
      'no semestre',
    ]);
    expect(RESPOSTA_POR_COR.vermelho.tarefas[0]?.titulo).toBe('Contato com o articulador municipal');
    expect(RESPOSTA_POR_COR.vermelho.quem_age).toBe('Gestora de referência e gestora pedagógica');
    expect(RESPOSTA_POR_COR.vermelho.rotina).toEqual(['Acompanhamento a cada 15 dias', 'Reunião de escuta a cada 3 meses']);
  });

  it('decisões 34 e 37 (rodada 3): o "O que fazer" do vermelho segue as tarefas, do contato com o articulador municipal à devolutiva', () => {
    const texto = RESPOSTA_POR_COR.vermelho.o_que_fazer;
    expect(texto.startsWith('Contato com o articulador municipal em 2 dias úteis')).toBe(true);
    const posicoes = ['articulador municipal', 'Secretaria', 'plano de ação', 'devolutiva', 'visita técnica'].map((t) => texto.indexOf(t));
    expect(posicoes.every((p) => p >= 0)).toBe(true);
    expect([...posicoes].sort((x, y) => x - y)).toEqual(posicoes);
  });

  it('decisões 33 e 35 (rodada 3): o prazo em meses que cai no sábado ou no domingo passa para a segunda-feira', () => {
    // 30/11/2026 + 6 meses = 30/05/2027, um domingo (Horizonte-CE); 14/08/2026 + 6 meses = 14/02/2027, outro domingo.
    const visita = (publicada: string) => criarTarefas('vermelho', 7, publicada).find((t) => t.chave === 'visita_tecnica')!.prazo_em;
    expect(visita('2026-11-30')).toBe('2027-05-31');
    expect(visita('2026-08-14')).toBe('2027-02-15');
    // 06/11/2026 + 2 meses = 06/01/2027, uma quarta: fica.
    expect(criarTarefas('amarelo', 7, '2026-11-06').find((t) => t.chave === 'observacao_formacao')!.prazo_em).toBe('2027-01-06');
  });

  it('decisão 34: publicada na sexta, o contato de 2 dias úteis vence na terça', () => {
    // 27/11/2026 é uma sexta-feira.
    expect(criarTarefas('vermelho', 7, '2026-11-27')[0]?.prazo_em).toBe('2026-12-01');
  });

  describe('dias úteis: segunda a sexta', () => {
    it.each([
      ['2026-11-24', 10, '2026-12-08'],
      ['2026-11-27', 1, '2026-11-30'],
      ['2026-11-28', 1, '2026-11-30'],
      ['2026-11-29', 1, '2026-11-30'],
      ['2026-11-24', 3, '2026-11-27'],
    ] as const)('%s + %s dia(s) útil(eis) = %s', (data, dias, esperado) => {
      expect(somarDiasUteis(data, dias)).toBe(esperado);
    });
  });

  it('meses: o dia que não existe no mês do prazo vira o último dia do mês', () => {
    expect(somarMeses('2026-12-31', 2)).toBe('2027-02-28');
    expect(somarMeses('2026-08-31', 6)).toBe('2027-02-28');
    expect(somarMeses('2026-11-24', -3)).toBe('2026-08-24');
  });

  describe('situação da tarefa a partir da data de referência (no prazo, vence hoje, vencida)', () => {
    const tarefa: TarefaResposta = criarTarefas('vermelho', 7, PUBLICADA)[0]!;

    it.each([
      ['2026-11-24', 'no_prazo'],
      ['2026-11-25', 'no_prazo'],
      ['2026-11-26', 'vence_hoje'],
      ['2026-11-27', 'vencida'],
    ] as const)('em %s: %s', (referencia, estado) => {
      expect(estadoDaTarefa(tarefa, referencia)).toBe(estado);
    });

    it('concluída não vence', () => {
      expect(estadoDaTarefa({ ...tarefa, concluida_em: '2026-11-25' }, '2026-12-30')).toBe('concluida');
    });

    it('decisões 42 e 43: a tarefa cancelada pelo Comitê ou substituída fica com o estado (não some, não vence)', () => {
      const cancelada = { ...tarefa, encerramento: { motivo: 'cancelada_comite' as const, em: '2026-11-25' } };
      const substituida = { ...tarefa, encerramento: { motivo: 'substituida' as const, em: '2026-11-25' } };
      expect(estadoDaTarefa(cancelada, '2026-12-30')).toBe('cancelada_comite');
      expect(estadoDaTarefa(substituida, '2026-12-30')).toBe('substituida');
      expect([tarefa, cancelada, substituida, { ...tarefa, concluida_em: '2026-11-25' }].map(tarefaAberta)).toEqual([
        true,
        false,
        false,
        false,
      ]);
    });
  });
});

describe('Decisão 48: a reunião de escuta é marcada antes e a ata registrada até 5 dias úteis depois', () => {
  // 27/11/2026 é uma sexta-feira: o prazo da ata é a sexta seguinte, 04/12.
  const reuniao = { data: '2026-11-27', ata_em: null };

  it('o prazo da ata é 5 dias úteis depois da reunião', () => {
    expect(prazoDaAta('2026-11-27')).toBe('2026-12-04');
  });

  it.each([
    ['2026-11-26', 'agendada'],
    ['2026-11-27', 'ata_a_registrar'],
    ['2026-12-04', 'ata_a_registrar'],
    // 6 dias úteis depois: ata atrasada.
    ['2026-12-07', 'ata_atrasada'],
  ] as const)('sem ata, em %s: %s', (hoje, situacao) => {
    expect(situacaoDaReuniao(reuniao, hoje)).toBe(situacao);
  });

  it('com a ata registrada, a reunião está realizada', () => {
    expect(situacaoDaReuniao({ ...reuniao, ata_em: '2026-12-01' }, '2026-12-07')).toBe('realizada');
  });

  it.each([
    ['2026-11-26', null, 'Agendada'],
    ['2026-12-01', null, 'Ata a registrar até 04/12/2026'],
    ['2026-12-07', null, 'Ata atrasada: o prazo era 04/12/2026'],
    ['2026-12-07', '2026-12-01', 'Ata registrada em 01/12/2026'],
  ] as const)('o texto da tela em %s (ata em %s): "%s"', (hoje, ata_em, texto) => {
    expect(textoDaReuniao({ ...reuniao, ata_em }, hoje)).toBe(texto);
  });
});

describe('Decisão 50: o tempo de resposta às ocorrências (meta de 48 h)', () => {
  const comResposta = (registrada_em: string, respondida_em: string | null): Ocorrencia => ({
    ...ocorrencia(registrada_em.slice(0, 10), 'reclamacao'),
    registrada_em,
    respondida_em,
  });

  it('conta as horas entre o registro e a resposta, com data e hora', () => {
    expect(horasEntre('2026-11-30T10:15:00-03:00', '2026-12-02T16:15:00-03:00')).toBe(54);
    expect(META_RESPOSTA_HORAS).toBe(48);
  });

  it('reclamação respondida em 54 h fica fora da meta; a média é das respondidas; sem resposta fica à parte', () => {
    const lista = [
      comResposta('2026-11-30T10:15:00-03:00', '2026-12-02T16:15:00-03:00'),
      comResposta('2026-12-01T08:00:00-03:00', '2026-12-01T14:00:00-03:00'),
      comResposta('2026-12-03T09:00:00-03:00', null),
    ];
    expect(tempoDeResposta(lista)).toEqual({ media_horas: 30, respondidas: 2, sem_resposta: 1, dentro_da_meta: 1, fora_da_meta: 1 });
  });

  it.each([
    [54, '54 h'],
    [2.5, '2 h 30 min'],
    [28.307692307692307, '28 h 18 min'],
    [0.25, '0 h 15 min'],
    // Arredonda o minuto: 59,9 min vira a hora seguinte, sem "60 min".
    [1.999, '2 h'],
  ] as const)('as horas para a tela: %s → "%s"', (horas, texto) => {
    expect(textoHoras(horas)).toBe(texto);
  });

  it('a data e a hora da ocorrência para a tela, na hora de Fortaleza', () => {
    expect(textoDataHora('2026-11-30T10:15:00-03:00')).toBe('30/11/2026 às 10:15');
  });

  it('exatamente 48 h está dentro da meta; sem nenhuma respondida, a média é sem dado', () => {
    expect(tempoDeResposta([comResposta('2026-12-01T08:00:00-03:00', '2026-12-03T08:00:00-03:00')]).dentro_da_meta).toBe(1);
    expect(tempoDeResposta([]).media_horas).toBeNull();
  });
});

describe('Decisão 49: convergência entre a pesquisa e as ocorrências', () => {
  it('a cor da pesquisa é a pior entre a média e o NPS; sem dado nos dois, sem dado', () => {
    expect(corDaPesquisa('verde', 'amarelo')).toBe('amarelo');
    expect(corDaPesquisa('vermelho', 'verde')).toBe('vermelho');
    expect(corDaPesquisa('sem_dado', 'amarelo')).toBe('amarelo');
    expect(corDaPesquisa('sem_dado', 'sem_dado')).toBe('sem_dado');
  });

  it.each([
    ['verde', 'vermelho', true],
    ['vermelho', 'verde', true],
    ['verde', 'amarelo', false],
    ['amarelo', 'vermelho', false],
    ['vermelho', 'vermelho', false],
  ] as const)('pesquisa %s e ocorrências %s: divergem = %s', (pesquisa, ocorrencias, esperado) => {
    expect(divergem(pesquisa, ocorrencias)).toBe(esperado);
  });
});

describe('Seção 5: a reunião de escuta em dia (a cada 6 meses no verde, a cada 3 no amarelo e no vermelho)', () => {
  const HOJE = '2026-12-07';

  it.each([
    ['verde', ['2026-06-08'], true],
    ['verde', ['2026-06-07'], false],
    ['amarelo', ['2026-09-08'], true],
    ['amarelo', ['2026-09-07'], false],
    ['vermelho', ['2026-03-20', '2026-11-30'], true],
    ['vermelho', [], false],
  ] as const)('%s com reuniões em %j: em dia = %s', (cor, datas, esperado) => {
    expect(reuniaoEmDia(datas, cor, HOJE)).toBe(esperado);
  });

  it('reunião marcada depois de hoje não conta como feita', () => {
    expect(reuniaoEmDia(['2026-12-20'], 'verde', HOJE)).toBe(false);
  });
});

describe('A origem da ocorrência tem um nome só em todas as telas', () => {
  it('o fluxo único diz quem registra (Relacionamento, Comercial ou distribuidor), sem o nome interno', () => {
    expect(ROTULO_ORIGEM.fluxo_unico).toBe('Relacionamento, Comercial ou distribuidor');
    expect(Object.values(ROTULO_ORIGEM).join(' ')).not.toMatch(/Fluxo único/i);
  });
});
