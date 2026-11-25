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
  classificar,
  contarOcorrencias,
  corCronograma,
  corMediaPesquisa,
  corNps,
  corOcorrencias,
  corRespostaPesquisa,
  criarTarefas,
  estadoDaTarefa,
  explicarCor,
  mediaDaPesquisa,
  mediaNps,
  mudancaEntreCiclos,
  ocorrenciasNoTrimestre,
  percentualCronograma,
  respondeuNoPrazo,
  reuniaoEmDia,
  somarDiasUteis,
  somarMeses,
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

function relatorio(fp: number, fr: number, vp: number, vr: number): RelatorioMensal {
  return {
    id: proximoId++,
    municipio: 1,
    coordenador: 1,
    mes: '2026-10',
    formacoes_previstas: fp,
    formacoes_realizadas: fr,
    visitas_previstas: vp,
    visitas_realizadas: vr,
  };
}

function ocorrencia(data: string, tipo: Ocorrencia['tipo'] = 'leve'): Ocorrencia {
  return { id: proximoId++, municipio: 1, data, origem: 'fluxo_unico', tipo };
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
    expect(LIMITES.media_pesquisa).toEqual({ verde: '4,0 ou mais', amarelo: '3,0 a 3,9', vermelho: 'abaixo de 3,0' });
    expect(LIMITES.nps).toEqual({ verde: '9 ou 10', amarelo: '7 ou 8', vermelho: '0 a 6' });
    expect(LIMITES.cronograma).toEqual({ verde: '90% ou mais', amarelo: '70% a 89%', vermelho: 'abaixo de 70%' });
    expect(LIMITES.ocorrencias.verde).toBe('Nenhuma');
    expect(LIMITES.resposta_pesquisa.vermelho).toBe('Não respondeu em dois ciclos seguidos');
  });

  describe('Média da pesquisa do articulador: verde 4,0 ou mais · amarelo 3,0 a 3,9 · vermelho abaixo de 3,0', () => {
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

    it('a cor sai do número exibido com uma casa (3,95 aparece "4,0" e é verde; 2,95 aparece "3,0")', () => {
      expect(corMediaPesquisa(3.95)).toBe('verde');
      expect(corMediaPesquisa(3.94)).toBe('amarelo');
      expect(corMediaPesquisa(2.95)).toBe('amarelo');
      expect(corMediaPesquisa(2.94)).toBe('vermelho');
    });

    it('é a média dos 6 itens de todas as respostas do ciclo; sem resposta, sem dado', () => {
      expect(mediaDaPesquisa([resposta([5, 5, 5, 5, 5, 5], 10), resposta([3, 3, 3, 3, 3, 3], 5)])).toBe(4);
      expect(mediaDaPesquisa([resposta([4, 4, 4, 3, 3, 3], 8)])).toBe(3.5);
      expect(mediaDaPesquisa([])).toBeNull();
    });
  });

  describe('Nota NPS do articulador: verde 9 ou 10 · amarelo 7 ou 8 · vermelho 0 a 6', () => {
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

    it('a média com casa decimal fica na faixa de baixo até chegar à nota de cima (8,9 amarelo; 6,9 vermelho)', () => {
      expect(corNps(8.9)).toBe('amarelo');
      expect(corNps(8.5)).toBe('amarelo');
      expect(corNps(6.9)).toBe('vermelho');
      expect(corNps(8.96)).toBe('verde');
    });

    it('é a média das notas do ciclo (decisão do PDF para vários respondentes); sem resposta, sem dado', () => {
      expect(mediaNps([resposta([5, 5, 5, 5, 5, 5], 10), resposta([4, 4, 4, 4, 4, 4], 7)])).toBe(8.5);
      expect(mediaNps([])).toBeNull();
    });
  });

  describe('Cronograma cumprido: verde 90% ou mais · amarelo 70% a 89% · vermelho abaixo de 70%', () => {
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

    it('a cor sai do percentual inteiro exibido (89,5% aparece 90%)', () => {
      expect(corCronograma(89.5)).toBe('verde');
      expect(corCronograma(89.4)).toBe('amarelo');
      expect(corCronograma(69.5)).toBe('amarelo');
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

    it('conta as ocorrências dos 3 meses até a data de referência, das coletas 3, 4 e 5', () => {
      const lista = [
        ocorrencia('2026-08-24'),
        ocorrencia('2026-08-25'),
        { ...ocorrencia('2026-10-01', 'reclamacao'), origem: 'momento_reservado' as const },
        { ...ocorrencia('2026-11-24'), origem: 'reuniao_escuta' as const },
        ocorrencia('2026-11-25'),
      ];
      const trimestre = ocorrenciasNoTrimestre(lista, '2026-11-24');
      expect(trimestre.map((o) => o.data)).toEqual(['2026-08-25', '2026-10-01', '2026-11-24']);
      expect(contarOcorrencias(trimestre)).toEqual({ leves: 2, reclamacoes: 1 });
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

  it('cada indicador sai com a cor e o valor escrito para a tela', () => {
    expect(
      avaliarIndicadores({
        media_pesquisa: 4.24,
        nps: 7,
        cronograma: 78.2,
        ocorrencias: { leves: 1, reclamacoes: 1 },
        resposta_pesquisa: { ciclo_atual: false, ciclo_anterior: false },
      }),
    ).toEqual([
      { indicador: 'media_pesquisa', cor: 'verde', texto: '4,2' },
      { indicador: 'nps', cor: 'amarelo', texto: '7,0' },
      { indicador: 'cronograma', cor: 'amarelo', texto: '78%' },
      { indicador: 'ocorrencias', cor: 'vermelho', texto: '1 reclamação e 1 leve' },
      { indicador: 'resposta_pesquisa', cor: 'vermelho', texto: 'Não respondeu em dois ciclos seguidos' },
    ]);
    const vazio = avaliarIndicadores(
      valores({ media_pesquisa: null, ocorrencias: { leves: 0, reclamacoes: 0 }, resposta_pesquisa: { ciclo_atual: null, ciclo_anterior: null } }),
    );
    expect(vazio.map((a) => a.texto)).toEqual(['Sem dado', '9,5', '95%', 'Nenhuma', 'Sem dado']);
    expect(avaliarIndicadores(valores({ ocorrencias: { leves: 2, reclamacoes: 0 } }))[3]!.texto).toBe('2 leves');
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

    it('três amarelos → vermelho', () => {
      const r = classificar(
        valores({ media_pesquisa: AMARELO.media_pesquisa, nps: AMARELO.nps, cronograma: AMARELO.cronograma }),
        [],
      );
      expect(r).toMatchObject({
        cor: 'vermelho',
        motivo: 'tres_amarelos',
        decisivos: ['media_pesquisa', 'nps', 'cronograma'],
        vermelho_imediato: false,
      });
      expect(explicarCor(r)).toBe(
        'Vermelho: 3 indicadores em amarelo no mesmo ciclo (Média da pesquisa do articulador, Nota NPS do articulador e Cronograma cumprido).',
      );
    });

    it('cinco amarelos → vermelho', () => {
      expect(classificar(AMARELO, []).motivo).toBe('tres_amarelos');
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
      ['observacao_formacao', '2027-01-24'],
    ]);
    expect(tarefas[0]).toMatchObject({ municipio: 7, cor: 'amarelo', criada_em: PUBLICADA, concluida_em: null });
    expect(RESPOSTA_POR_COR.amarelo.quem_age).toBe('Gestora de referência e coordenador(es)');
    expect(RESPOSTA_POR_COR.amarelo.rotina).toEqual(['Reunião de escuta a cada 3 meses']);
  });

  it('vermelho: contato em 48 h, Secretaria em 5 dias, plano em 15, devolutiva em 30, visita técnica no semestre', () => {
    expect(criarTarefas('vermelho', 7, PUBLICADA).map((t) => [t.chave, t.prazo_em])).toEqual([
      ['contato_48h', '2026-11-26'],
      ['reuniao_secretaria', '2026-11-29'],
      ['plano_acao', '2026-12-09'],
      ['devolutiva', '2026-12-24'],
      ['visita_tecnica', '2027-05-24'],
    ]);
    expect(RESPOSTA_POR_COR.vermelho.tarefas.map((t) => t.prazo_texto)).toEqual([
      'em 48 h',
      'em 5 dias',
      'em 15 dias',
      'em 30 dias',
      'no semestre',
    ]);
    expect(RESPOSTA_POR_COR.vermelho.quem_age).toBe('Gestora de referência e gestora pedagógica');
    expect(RESPOSTA_POR_COR.vermelho.rotina).toEqual(['Acompanhamento a cada 15 dias', 'Reunião de escuta a cada 3 meses']);
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
