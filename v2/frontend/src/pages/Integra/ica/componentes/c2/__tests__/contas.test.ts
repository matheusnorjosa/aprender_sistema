/** Contas das telas da parte C2 (por gerência, data do recálculo, situação do alerta). */
import { describe, expect, test } from 'vitest';

import { calcularEquipe, estratoDoIca, PESOS_REVISADOS } from '../../../calculo';
import type { BaseIca, Gerencia, Pessoa, Remanejamento, VersaoPesos } from '../../../../dados/tipos';
import { dataDoUltimoRecalculo, resumoPorGerencia, situacaoDoAlerta } from '../contas';

const municipio = (id: number, status: 'ativo' | 'suspenso' = 'ativo') => ({
  id,
  nome: `Município ${id}`,
  uf: 'CE' as const,
  status,
  status_desde: '2026-01-01',
  gestora_referencia: null,
  deslocamento_horas: 10,
  deslocamento_meio: 'carro' as const,
});

const atendimento = (id: number, mun: number, coord: number, professores: number) => ({
  id,
  municipio: mun,
  projeto_geral: 1,
  coordenador: coord,
  segmentos: [{ segmento: 'Anos Iniciais', turmas_qtde: 2, professor_qtde: professores, aluno_qtde: professores * 20 }],
});

/** Gerência 1: Ana (municípios 1 e 2) e Bia (município 2, compartilhado). Gerência 2: Caio (3) e Duda (sem carteira). */
const BASE: BaseIca = {
  coordenadores: [
    { id: 1, nome: 'Ana', atuacao: 'amma', gerencia: 10 },
    { id: 2, nome: 'Bia', atuacao: 'amma', gerencia: 10 },
    { id: 3, nome: 'Caio', atuacao: 'amma', gerencia: 20 },
    { id: 4, nome: 'Duda', atuacao: 'amma', gerencia: 20 },
  ],
  municipios: [municipio(1), municipio(2), municipio(3), municipio(4, 'suspenso')],
  atendimentos: [
    atendimento(1, 1, 1, 40),
    atendimento(2, 2, 1, 30),
    atendimento(3, 2, 2, 20),
    atendimento(4, 3, 3, 50),
    atendimento(5, 4, 3, 99),
  ],
};
const GERENCIAS: Gerencia[] = [
  { id: 10, nome: 'Gerência A', gestora_tecnica: 900 },
  { id: 20, nome: 'Gerência B', gestora_tecnica: 901 },
];
const PESSOAS: Pessoa[] = [
  { id: 900, nome: 'Gestora Um' },
  { id: 901, nome: 'Gestora Dois' },
];

describe('resumoPorGerencia', () => {
  const resultado = calcularEquipe(BASE, PESOS_REVISADOS);
  const [a, b] = resumoPorGerencia(resultado, GERENCIAS, PESSOAS);

  test('uma linha por gerência, com a gestora técnica', () => {
    expect(a?.gerencia.nome).toBe('Gerência A');
    expect(a?.gestoraTecnica).toBe('Gestora Um');
    expect(b?.gestoraTecnica).toBe('Gestora Dois');
  });

  test('município compartilhado dentro da gerência conta uma vez; suspenso não conta', () => {
    expect(a?.municipiosAtivos).toBe(2);
    expect(b?.municipiosAtivos).toBe(1);
  });

  test('coordenadores (todos e com carteira) e professores dos municípios ativos', () => {
    expect(a?.coordenadores.length).toBe(2);
    expect(a?.comCarteira).toBe(2);
    expect(a?.professores).toBe(90);
    expect(b?.coordenadores.length).toBe(2);
    expect(b?.comCarteira).toBe(1);
    expect(b?.professores).toBe(50);
  });

  test('ICA médio: média do ICA exato de quem tem carteira, exibido inteiro, com o estrato', () => {
    const icaDe = (id: number) => resultado.coordenadores.find((r) => r.coordenador.id === id)?.conta.icaExato ?? NaN;
    const esperadoA = (icaDe(1) + icaDe(2)) / 2;
    expect(a?.icaMedioExato).toBeCloseTo(esperadoA, 6);
    expect(a?.icaMedio).toBe(Math.round(esperadoA));
    // Gerência B: Duda está sem municípios e fica fora da média.
    expect(b?.icaMedio).toBe(Math.round(icaDe(3)));
    expect(b?.estrato).toBe(estratoDoIca(Math.round(icaDe(3))));
  });

  test('gerência sem ninguém com carteira fica sem ICA médio', () => {
    const [c] = resumoPorGerencia(resultado, [{ id: 30, nome: 'Gerência C', gestora_tecnica: 999 }], PESSOAS);
    expect(c?.icaMedio).toBeNull();
    expect(c?.estrato).toBeNull();
    expect(c?.gestoraTecnica).toBe('Não informada');
  });
});

describe('dataDoUltimoRecalculo', () => {
  const versao = (criada_em: string): VersaoPesos => ({
    id: 'x',
    nome: 'x',
    pesos: PESOS_REVISADOS,
    criada_em,
    autor: 'x',
    justificativa: 'x',
  });
  const rem = (aplicado_em: string | null): Remanejamento => ({
    id: 'r',
    movimentos: [],
    justificativa: 'x',
    status: aplicado_em ? 'aplicado' : 'proposto',
    proposto_por: 'x',
    proposto_em: '2026-01-01T00:00:00-03:00',
    aprovado_por: null,
    aprovado_em: null,
    aplicado_em,
    semestre: null,
  });

  test('sem mudança na sessão, é a data do último recálculo semestral', () => {
    expect(
      dataDoUltimoRecalculo('2026-11-17', versao('2026-11-10T09:00:00-03:00'), [rem('2026-08-03T08:00:00-03:00')]),
    ).toBe('2026-11-17');
  });

  test('versão de pesos nova ou remanejamento aplicado depois disso passam a ser a data', () => {
    expect(dataDoUltimoRecalculo('2026-11-17', versao('2026-11-24T15:00:00Z'), [])).toBe('2026-11-24T15:00:00Z');
    expect(
      dataDoUltimoRecalculo('2026-11-17', versao('2026-11-10T09:00:00-03:00'), [rem('2026-11-25T10:00:00Z'), rem(null)]),
    ).toBe('2026-11-25T10:00:00Z');
  });
});

describe('situacaoDoAlerta', () => {
  test('diz o que fecha o alerta', () => {
    expect(situacaoDoAlerta('sobrecarga')).toMatch(/próximo recálculo/);
    expect(situacaoDoAlerta('contrato_sem_coordenador')).toMatch(/coordenador/);
    expect(situacaoDoAlerta('dado_incompleto')).toMatch(/cadastro/);
  });
});
