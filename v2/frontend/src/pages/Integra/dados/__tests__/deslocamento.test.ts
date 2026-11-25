/**
 * Tempos de deslocamento REAIS, extraídos do PDF "Relatorio_Tempo_Deslocamento - TODOS MUNICÓPIOS."
 * (Coordenação Pedagógica, novembro de 2026) por `scripts/integra_extrair_deslocamento.py`.
 *
 * Os números conferidos aqui são os da página 1 do PDF (e da síntese no alto da página 2):
 * 92 municípios, 23 só por terra, 69 com trecho aéreo (35 com conexão), mediana de 17h45 e
 * menor e maior de 0h40 a 31h35. Todos esses números descrevem a IDA E VOLTA: a página 1 diz
 * "mediana de ida e volta" e "menor e maior ida e volta"; a página 2 diz "Distribuição por faixa
 * de ida e volta: Próximo 7 · Médio 7 · Longo 34 · Muito longo 44"; a página 3 diz "A faixa
 * considera a ida e volta".
 */
import { describe, expect, it } from 'vitest';
import { formatarHoras } from '../../ica/calculo';
import { contarNomesReais, guardaDeNomesReaisAtiva } from '../../__tests__/nomesReais';
import {
  DESLOCAMENTO_MUNICIPIOS,
  FAIXAS_DESLOCAMENTO,
  FONTE_DESLOCAMENTO,
  OBSERVACOES_DESLOCAMENTO,
  REGRAS_DO_CALCULO,
  contarPorFaixa,
  contarPorMeio,
  faixaPelasHoras,
  filtrarDeslocamento,
  medianaIdaVolta,
  type MunicipioDeslocamento,
} from '../deslocamento';

const todos = DESLOCAMENTO_MUNICIPIOS;
const nomes = (lista: readonly { nome: string }[]) => lista.map((m) => m.nome).sort();

describe('deslocamento: números da página 1 do PDF', () => {
  it('92 municípios, sem repetir nome dentro do mesmo estado', () => {
    expect(todos).toHaveLength(92);
    expect(new Set(todos.map((m) => `${m.nome}-${m.uf}`)).size).toBe(92);
  });

  it('23 só por terra (carro) e 69 com trecho aéreo (avião), 35 deles com conexão', () => {
    expect(contarPorMeio(todos)).toEqual({ carro: 23, aviao: 69 });
    expect(todos.filter((m) => m.detalhe_rota?.includes('conexão'))).toHaveLength(35);
  });

  it('mediana de ida e volta 17h45; menor 0h40 e maior 31h35', () => {
    // O 17h45 da página 1 é 2 × a mediana da coluna Ida (8h45 e 9h00 → 8h52,5). A mediana da coluna
    // Ida e volta, que o PDF arredonda à parte, dá 17h47,5 (17h35 e 18h00): 2,5 min de diferença,
    // abaixo do passo de 5 min do PDF. A tela que mostrar a mediana deve citar o 17h45 do PDF.
    const ida = todos.map((m) => ({ ida_volta_horas: 2 * m.ida_horas }) as MunicipioDeslocamento);
    expect(formatarHoras(medianaIdaVolta(ida))).toBe('17h45');
    expect(medianaIdaVolta(todos)).toBeCloseTo(17 + 47.5 / 60, 9);
    const horas = todos.map((m) => m.ida_volta_horas);
    expect(formatarHoras(Math.min(...horas))).toBe('0h40');
    expect(formatarHoras(Math.max(...horas))).toBe('31h35');
  });

  it('faixas de ida e volta: Próximo 7 · Médio 7 · Longo 34 · Muito longo 44', () => {
    expect(contarPorFaixa(todos)).toEqual({ proximo: 7, medio: 7, longo: 34, muito_longo: 44 });
  });

  it('municípios por estado, como nos títulos da tabela (seção 2)', () => {
    const porUf: Record<string, number> = {};
    for (const m of todos) porUf[m.uf] = (porUf[m.uf] ?? 0) + 1;
    expect(porUf).toEqual({
      CE: 17, PB: 2, PE: 5, AL: 6, SE: 2, BA: 19, MG: 13, ES: 1,
      RJ: 1, SP: 2, PR: 12, SC: 8, RS: 1, GO: 1, MT: 1, MS: 1,
    });
  });

  it('os 5 trajetos mais longos (página 2)', () => {
    const top = [...todos].sort((a, b) => b.ida_volta_horas - a.ida_volta_horas).slice(0, 5);
    expect(top.map((m) => `${m.nome}-${m.uf} ${m.ida_volta_texto}`)).toEqual([
      'Filadélfia-BA 31h35',
      'Guarapuava-PR 26h30',
      'Petrolina-PE 25h45',
      'Curitibanos-SC 25h20',
      'Itaquiraí-MS 25h05',
    ]);
  });

  it('marcas: ações suspensas (4), travessia marítima (2)', () => {
    expect(nomes(todos.filter((m) => m.acoes_suspensas))).toEqual(['Capivari', 'Itagi', 'Itaparica', 'Tamandaré']);
    expect(nomes(todos.filter((m) => m.travessia_maritima))).toEqual(['Cairu', 'Itaparica']);
  });

  it('terrestre por decisão da gestão: os do grupo que a regra nomeia (CE, PB, Afrânio, Lagoa Grande, Petrolina, Filadélfia)', () => {
    // A página 1 diz "16 foram definidos pela gestão", mas o grupo que a regra da página 3 nomeia
    // soma 23 (17 do CE + 2 da PB + 4). O PDF diverge de si mesmo; vale o grupo nomeado (pendência).
    const gestao = todos.filter((m) => m.terrestre_por_decisao_da_gestao);
    expect(gestao).toHaveLength(23);
    expect(gestao.every((m) => m.meio === 'carro')).toBe(true);
  });
});

describe('deslocamento: coerência de cada linha', () => {
  it('textos e horas batem ("17h45" = 17,75 h)', () => {
    for (const m of todos) {
      expect(formatarHoras(m.ida_horas)).toBe(m.ida_texto);
      expect(formatarHoras(m.ida_volta_horas)).toBe(m.ida_volta_texto);
    }
  });

  it('ida e volta = 2 × ida, com até 5 minutos de diferença (o PDF arredonda cada coluna)', () => {
    for (const m of todos) expect(Math.abs(m.ida_volta_horas - 2 * m.ida_horas)).toBeLessThanOrEqual(5 / 60 + 1e-9);
  });

  it('a faixa do PDF segue os limites de ida e volta, exceto Craíbas-AL (18h00 marcada como Muito longo)', () => {
    const divergentes = todos.filter((m) => faixaPelasHoras(m.ida_volta_horas) !== m.faixa);
    expect(divergentes.map((m) => `${m.nome}-${m.uf}`)).toEqual(['Craíbas-AL']);
  });

  it('todo município tem rota e alternativa; detalhe do voo só quando vai de avião', () => {
    for (const m of todos) {
      expect(m.rota.length).toBeGreaterThan(10);
      expect(m.alternativa).toMatch(/^(Terrestre|Aéreo \+ terrestre): \d+h\d{2}$/);
      expect(m.detalhe_rota === null).toBe(m.meio === 'carro');
    }
  });
});

describe('deslocamento: textos para a tela', () => {
  it('regras do cálculo (8 componentes), faixas (4) e observações (6)', () => {
    expect(REGRAS_DO_CALCULO.map((r) => r.componente)).toEqual([
      'Traslado e antecedência no aeroporto de Fortaleza',
      'Tempo de voo',
      'Conexão',
      'Desembarque',
      'Trecho rodoviário',
      'Travessia marítima',
      'Escolha do modal',
      'Ida e volta',
    ]);
    expect(REGRAS_DO_CALCULO.every((r) => r.tempo.length > 0 && r.criterio.length > 20)).toBe(true);
    expect(FAIXAS_DESLOCAMENTO.map((f) => f.rotulo)).toEqual(['Próximo', 'Médio', 'Longo', 'Muito longo']);
    expect(OBSERVACOES_DESLOCAMENTO).toHaveLength(6);
    expect(FONTE_DESLOCAMENTO.ponto_de_partida).toBe('Fortaleza (CE)');
  });

  it('nenhum texto traz a marca d\'água nem nome de coordenador', () => {
    const texto = JSON.stringify({ todos, REGRAS_DO_CALCULO, OBSERVACOES_DESLOCAMENTO, FAIXAS_DESLOCAMENTO });
    expect(texto).not.toMatch(/coordenador não informado/);
    // Letras soltas da marca d'água viram "palavras" de uma letra maiúscula coladas no texto.
    for (const m of todos) expect(m.nome).toMatch(/^[\p{Lu}][\p{L}' -]+$/u);
  });

  it.skipIf(!guardaDeNomesReaisAtiva)('guarda local: nenhum nome real de pessoa nos dados', () => {
    const texto = JSON.stringify({ todos, REGRAS_DO_CALCULO, OBSERVACOES_DESLOCAMENTO, FAIXAS_DESLOCAMENTO });
    expect(contarNomesReais(texto)).toBe(0);
  });
});

describe('deslocamento: helpers', () => {
  it('filtra por UF, faixa e meio (juntos ou separados)', () => {
    expect(filtrarDeslocamento(todos, {})).toHaveLength(92);
    expect(filtrarDeslocamento(todos, { uf: 'BA' })).toHaveLength(19);
    expect(filtrarDeslocamento(todos, { meio: 'carro', faixa: 'proximo' })).toHaveLength(7);
    expect(nomes(filtrarDeslocamento(todos, { uf: 'BA', meio: 'carro' }))).toEqual(['Filadélfia']);
  });

  it('mediana de lista vazia é 0; de lista par é a média dos dois do meio', () => {
    expect(medianaIdaVolta([])).toBe(0);
    const osDoisDaParaiba = filtrarDeslocamento(todos, { uf: 'PB' });
    expect(medianaIdaVolta(osDoisDaParaiba)).toBeCloseTo((11 + 50 / 60 + 12 + 5 / 60) / 2, 9);
  });

  it('contagens zeradas quando a lista é vazia', () => {
    expect(contarPorFaixa([])).toEqual({ proximo: 0, medio: 0, longo: 0, muito_longo: 0 });
    expect(contarPorMeio([])).toEqual({ carro: 0, aviao: 0 });
  });

  it('faixaPelasHoras usa os limites do PDF (até 3h, até 10h, até 18h, acima de 18h)', () => {
    expect([3, 3.01, 10, 10.01, 18, 18.01].map(faixaPelasHoras)).toEqual([
      'proximo', 'medio', 'medio', 'longo', 'longo', 'muito_longo',
    ]);
  });
});
