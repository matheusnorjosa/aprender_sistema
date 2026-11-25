/**
 * Contas do ICA (Índice de Carga de Acompanhamento).
 *
 * Fonte das regras: Requisitos_Modulo_ICA.pdf (NFP, nov/2026), seções 2, 3 e 6.
 * O teste de ouro é o exemplo da página 4 (configuração revisada): 169,8 → 170 · Sobrecarga.
 */
import { describe, expect, it } from 'vitest';
import type { Atendimento, BaseIca, Coordenador, MunicipioIntegra, Valores } from '../../dados/tipos';
import {
  PESOS_ORIGINAIS_V5,
  PESOS_REVISADOS,
  aplicarMovimentos,
  arredondarIca,
  calcularDispersao,
  calcularEquipe,
  calcularIca,
  carteiraDoCoordenador,
  compararPesos,
  dentroDaMeta,
  estratoDoIca,
  formatarHoras,
  formatarPercentual,
  gerarAlertas,
  icaExatoComUmaCasa,
  indiceDoComponente,
  medianaDeslocamento,
  nomeDoEstrato,
  simularRemanejamento,
  validarPesos,
  variacaoDoIca,
} from '../calculo';

const umDecimal = (v: number) => Math.round(v * 10) / 10;

function valores(parcial: Partial<Valores>): Valores {
  return { municipios: 0, frentes: 0, turmas: 0, professores: 0, deslocamento: 0, estados: 0, ...parcial };
}

function municipio(id: number, extra: Partial<MunicipioIntegra> = {}): MunicipioIntegra {
  return {
    id,
    nome: `Município ${id}`,
    uf: 'CE',
    status: 'ativo',
    status_desde: '2026-02-01',
    gestora_referencia: null,
    deslocamento_horas: 10,
    deslocamento_meio: 'carro',
    ...extra,
  };
}

function coordenador(id: number, nome = `Coord ${id}`): Coordenador {
  return { id, nome, atuacao: 'alfabetizacao_ei', gerencia: 1 };
}

let proximoAtendimento = 1;
function atendimento(
  coord: number | null,
  mun: number,
  colecao: number,
  turmas: number | null = 2,
  professores: number | null = 60,
  alunos: number | null = 1500,
): Atendimento {
  return {
    id: proximoAtendimento++,
    municipio: mun,
    projeto_geral: colecao,
    coordenador: coord,
    segmentos: [{ segmento: 'Anos Iniciais', turmas_qtde: turmas, professor_qtde: professores, aluno_qtde: alunos }],
  };
}

describe('calcularIca — teste de ouro do PDF (página 4)', () => {
  // Exemplo de cálculo do PDF de requisitos (p. 4), configuração revisada: 8 municípios, 14 frentes,
  // 23 turmas, 1.291 professores, 139h00 contra as médias 5,44 / 7,31 / 16,13 / 678,19 / 75h02.
  const conta = calcularIca(
    valores({ municipios: 8, frentes: 14, turmas: 23, professores: 1291, deslocamento: 139 }),
    valores({ municipios: 5.44, frentes: 7.31, turmas: 16.13, professores: 678.19, deslocamento: 75 + 2 / 60 }),
    PESOS_REVISADOS,
  );

  it('índices por componente: 147,1 / 191,5 / 142,6 / 190,4 / 185,3', () => {
    expect(umDecimal(conta.indices.municipios)).toBe(147.1);
    expect(umDecimal(conta.indices.frentes)).toBe(191.5);
    expect(umDecimal(conta.indices.turmas)).toBe(142.6);
    expect(umDecimal(conta.indices.professores)).toBe(190.4);
    expect(umDecimal(conta.indices.deslocamento)).toBe(185.3);
  });

  it('contribuições: 36,8 / 47,9 / 28,5 / 38,1 / 18,5', () => {
    expect(umDecimal(conta.contribuicoes.municipios)).toBe(36.8);
    expect(umDecimal(conta.contribuicoes.frentes)).toBe(47.9);
    expect(umDecimal(conta.contribuicoes.turmas)).toBe(28.5);
    expect(umDecimal(conta.contribuicoes.professores)).toBe(38.1);
    expect(umDecimal(conta.contribuicoes.deslocamento)).toBe(18.5);
    expect(conta.contribuicoes.estados).toBe(0);
  });

  it('ICA 169,8 → exibido 170 → Sobrecarga, fora da meta', () => {
    expect(umDecimal(conta.icaExato)).toBe(169.8);
    expect(conta.icaExibido).toBe(170);
    expect(conta.estrato).toBe('sobrecarga');
    expect(conta.dentroDaMeta).toBe(false);
  });
});

describe('pesos', () => {
  it('configuração revisada (nov/2026) e original (v5) somam 100', () => {
    expect(PESOS_REVISADOS).toEqual({
      municipios: 25, frentes: 25, turmas: 20, professores: 20, deslocamento: 10, estados: 0,
    });
    expect(PESOS_ORIGINAIS_V5).toEqual({
      municipios: 20, frentes: 20, turmas: 25, professores: 25, deslocamento: 0, estados: 10,
    });
    expect(validarPesos(PESOS_REVISADOS)).toEqual({ valido: true, soma: 100, erros: [] });
    expect(validarPesos(PESOS_ORIGINAIS_V5).valido).toBe(true);
  });

  it('recusa soma diferente de 100 e peso negativo', () => {
    const v = validarPesos({ ...PESOS_REVISADOS, municipios: 30 });
    expect(v.valido).toBe(false);
    expect(v.soma).toBe(105);
    expect(v.erros.join(' ')).toMatch(/100/);
    expect(validarPesos({ ...PESOS_REVISADOS, municipios: -5, frentes: 55 }).valido).toBe(false);
  });

  it('a soma conta todo número digitado, negativo também (a tela mostra a soma real)', () => {
    const v = validarPesos({ ...PESOS_REVISADOS, estados: -5 });
    expect(v.soma).toBe(95);
    expect(v.valido).toBe(false);
    expect(v.erros.join(' ')).toMatch(/Estados \(UFs\).*0 a 100/);
  });

  it('peso acima de 100 também é recusado', () => {
    expect(validarPesos({ ...PESOS_REVISADOS, municipios: 125, frentes: -25 }).erros.join(' ')).toMatch(
      /"Municípios ativos" precisa ser um número de 0 a 100/,
    );
  });

  it('soma com decimal sai em português no erro ("99,6%")', () => {
    const v = validarPesos({ ...PESOS_REVISADOS, deslocamento: 9.6 });
    expect(v.soma).toBe(99.6);
    expect(v.erros.join(' ')).toContain('Hoje somam 99,6%.');
  });

  it('formatarPercentual mostra as casas que a soma tem', () => {
    expect(formatarPercentual(100)).toBe('100%');
    expect(formatarPercentual(99.6)).toBe('99,6%');
    expect(formatarPercentual(100.45)).toBe('100,45%');
  });
});

describe('variacaoDoIca — a mesma regra na Ficha e no Histórico', () => {
  const base: BaseIca = {
    coordenadores: [coordenador(1), coordenador(2)],
    municipios: [municipio(1), municipio(2)],
    atendimentos: [atendimento(1, 1, 10), atendimento(1, 2, 10, 4, 120)],
  };
  const r = calcularEquipe(base, PESOS_REVISADOS);
  const [com, sem] = [r.coordenadores[0]!, r.coordenadores[1]!];

  it('diferença do ICA exibido quando os dois têm carteira', () => {
    expect(variacaoDoIca(com, com)).toBe(0);
  });

  it('sem comparação quando um dos dois está sem municípios (ICA 0 não é ICA)', () => {
    expect(sem.semMunicipios).toBe(true);
    expect(variacaoDoIca(com, sem)).toBeNull();
    expect(variacaoDoIca(sem, com)).toBeNull();
    expect(variacaoDoIca(com, undefined)).toBeNull();
  });
});

describe('arredondamento e estratos (o estrato sai do número exibido)', () => {
  it.each([
    [129.5, 130, 'sobrecarga'],
    [129.49, 129, 'atencao'],
    [130, 130, 'sobrecarga'],
    [109.5, 110, 'atencao'],
    [109.49, 109, 'adequada'],
    [79.5, 80, 'adequada'],
    [79.49, 79, 'capacidade'],
    [0, 0, 'capacidade'],
  ] as const)('%s → %s → %s', (exato, exibido, estrato) => {
    expect(arredondarIca(exato)).toBe(exibido);
    expect(estratoDoIca(arredondarIca(exato))).toBe(estrato);
  });

  it('a casa decimal mostrada leva sempre ao mesmo inteiro exibido (148,4758 → 148,4; o exemplo do PDF segue 169,8)', () => {
    expect(icaExatoComUmaCasa(148.4758)).toBe(148.4);
    expect(icaExatoComUmaCasa(169.7596466795742)).toBe(169.8);
    expect(icaExatoComUmaCasa(148.5)).toBe(148.5);
    expect(icaExatoComUmaCasa(169.79999999999998)).toBe(169.8);
    for (let n = 0; n <= 300000; n += 7) {
      const exato = n / 1000 + 0.0003;
      expect(arredondarIca(icaExatoComUmaCasa(exato))).toBe(arredondarIca(exato));
    }
  });

  it('a conta de verdade também arredonda antes de classificar (129,5 vira Sobrecarga)', () => {
    const pesos = { municipios: 100, frentes: 0, turmas: 0, professores: 0, deslocamento: 0, estados: 0 };
    const conta = calcularIca(valores({ municipios: 129.5 }), valores({ municipios: 100 }), pesos);
    expect(conta.icaExibido).toBe(130);
    expect(conta.estrato).toBe('sobrecarga');
  });

  it('nomes dos estratos para a tela', () => {
    expect(nomeDoEstrato('sobrecarga')).toBe('Sobrecarga');
    expect(nomeDoEstrato('atencao')).toBe('Atenção');
    expect(nomeDoEstrato('adequada')).toBe('Adequada');
    expect(nomeDoEstrato('capacidade')).toBe('Capacidade disponível');
  });

  it('meta de gestão 70–130, pontas incluídas', () => {
    expect(dentroDaMeta(70)).toBe(true);
    expect(dentroDaMeta(130)).toBe(true);
    expect(dentroDaMeta(69)).toBe(false);
    expect(dentroDaMeta(131)).toBe(false);
  });

  it('índice com média zero vale 0 (componente sem peso, como Estados na revisada)', () => {
    expect(indiceDoComponente(3, 0)).toBe(0);
    expect(indiceDoComponente(5, 4)).toBe(125);
  });
});

describe('formatarHoras', () => {
  it('139 → 139h00; 75h02', () => {
    expect(formatarHoras(139)).toBe('139h00');
    expect(formatarHoras(75 + 2 / 60)).toBe('75h02');
    expect(formatarHoras(16.5)).toBe('16h30');
  });
});

describe('medianaDeslocamento', () => {
  it('mediana dos municípios com localidade (par e ímpar)', () => {
    expect(medianaDeslocamento([municipio(1, { deslocamento_horas: 10 }), municipio(2, { deslocamento_horas: 30 }), municipio(3, { deslocamento_horas: 20 })])).toBe(20);
    expect(medianaDeslocamento([municipio(1, { deslocamento_horas: 10 }), municipio(2, { deslocamento_horas: 20 }), municipio(3, { deslocamento_horas: null })])).toBe(15);
  });
});

describe('calcularEquipe — carteiras', () => {
  // A: 2 municípios ativos (M1 com 2 coleções) + 1 suspenso; B: M1 compartilhado (outra coleção) + M3;
  // C: só um município suspenso → sem municípios.
  const base: BaseIca = {
    coordenadores: [coordenador(1, 'Ana'), coordenador(2, 'Bia'), coordenador(3, 'Caio')],
    municipios: [
      municipio(1, { deslocamento_horas: 10, uf: 'CE' }),
      municipio(2, { deslocamento_horas: 20, uf: 'PE' }),
      municipio(3, { deslocamento_horas: null, deslocamento_meio: null, uf: 'PI' }),
      municipio(4, { status: 'suspenso', deslocamento_horas: 40 }),
      municipio(5, { status: 'suspenso', deslocamento_horas: 50 }),
    ],
    atendimentos: [
      atendimento(1, 1, 10, 2, 60),
      atendimento(1, 1, 11, 1, 30),
      atendimento(1, 2, 10, 3, 90),
      atendimento(1, 4, 10, 5, 500),
      atendimento(2, 1, 12, 1, 40),
      atendimento(2, 3, 10, 2, 80),
      atendimento(3, 5, 10, 4, 100),
    ],
  };
  const r = calcularEquipe(base, PESOS_REVISADOS);
  const de = (id: number) => {
    const c = r.coordenadores.find((x) => x.coordenador.id === id);
    if (!c) throw new Error(`coordenador ${id} ausente`);
    return c;
  };

  it('soma só os municípios ativos; frentes = município × coleção distintos', () => {
    expect(de(1).valores).toEqual(valores({ municipios: 2, frentes: 3, turmas: 6, professores: 180, deslocamento: 30, estados: 2 }));
  });

  it('município compartilhado: cada um soma o que é seu', () => {
    // mediana de todos os municípios com localidade: 10, 20, 40, 50 → 30
    expect(r.mediana).toBe(30);
    // M3 não tem localidade: a UF dele não conta como estado (só CE, de M1).
    expect(de(2).valores).toEqual(valores({ municipios: 2, frentes: 2, turmas: 3, professores: 120, deslocamento: 40, estados: 1 }));
    expect(de(2).deslocamentoEstimado).toBe(true);
    expect(de(1).deslocamentoEstimado).toBe(false);
  });

  it('município sem localidade (deslocamento estimado) não soma estado: a UF dele é só do formato do cadastro', () => {
    const semLocalidade: BaseIca = {
      coordenadores: [coordenador(1)],
      municipios: [municipio(1, { uf: 'CE' }), municipio(2, { uf: 'MG', deslocamento_horas: null, deslocamento_meio: null })],
      atendimentos: [atendimento(1, 1, 10), atendimento(1, 2, 10)],
    };
    const c = calcularEquipe(semLocalidade, PESOS_ORIGINAIS_V5).coordenadores[0];
    expect(c?.valores.municipios).toBe(2);
    expect(c?.valores.estados).toBe(1);
    expect(c?.deslocamentoEstimado).toBe(true);
  });

  it('a média conta só quem tem município ativo; quem não tem fica com ICA 0 e "sem municípios"', () => {
    expect(r.medias.municipios).toBe(2);
    expect(r.medias.frentes).toBe(2.5);
    expect(r.medias.professores).toBe(150);
    expect(de(3).semMunicipios).toBe(true);
    expect(de(3).conta.icaExato).toBe(0);
    expect(de(3).conta.icaExibido).toBe(0);
    expect(de(1).semMunicipios).toBe(false);
  });

  it('com pesos que somam 100, a média do ICA de quem tem carteira é 100', () => {
    const comCarteira = r.coordenadores.filter((c) => !c.semMunicipios);
    const media = comCarteira.reduce((s, c) => s + c.conta.icaExato, 0) / comCarteira.length;
    expect(media).toBeCloseTo(100, 9);
    expect(r.dispersao.media).toBeCloseTo(100, 9);
  });

  it('quem não tem municípios fica fora dos estratos e é contado à parte (PDF, seção 3)', () => {
    const total = Object.values(r.porEstrato).reduce((s, n) => s + n, 0);
    expect(total).toBe(2);
    expect(r.semMunicipios).toBe(1);
  });

  it('carteira do coordenador lista município, coleções, turmas, professores e deslocamento', () => {
    const linhas = carteiraDoCoordenador(base, 1, r.mediana);
    const m1 = linhas.find((l) => l.municipio.id === 1);
    expect(m1).toMatchObject({ colecoes: [10, 11], turmas: 3, professores: 90, horas: 10, estimado: false, ativo: true, compartilhadoCom: [2] });
    const m4 = linhas.find((l) => l.municipio.id === 4);
    expect(m4?.ativo).toBe(false);
  });
});

describe('dado incompleto e valor improvável', () => {
  const base: BaseIca = {
    coordenadores: [coordenador(1), coordenador(2)],
    municipios: [municipio(1), municipio(2), municipio(3)],
    atendimentos: [
      atendimento(1, 1, 10, null, 60),
      atendimento(2, 2, 10, 2, 0, 800),
      atendimento(2, 3, 10, 2, 5, 9000),
    ],
  };
  const r = calcularEquipe(base, PESOS_REVISADOS);
  const c1 = r.coordenadores[0];
  const c2 = r.coordenadores[1];

  it('turmas não informadas: aceita, conta como 0 e marca "dado incompleto"', () => {
    expect(c1?.dadoIncompleto).toBe(true);
    expect(c1?.motivosIncompleto[0]).toMatch(/turmas/i);
    expect(c1?.valores.turmas).toBe(0);
    expect(c2?.dadoIncompleto).toBe(false);
  });

  it('turma sem professor e menos de 1 professor por 100 alunos viram aviso', () => {
    expect(c2?.valoresImprovaveis.some((t) => /sem professor/i.test(t))).toBe(true);
    expect(c2?.valoresImprovaveis.some((t) => /100 alunos/.test(t))).toBe(true);
    expect(c1?.valoresImprovaveis).toEqual([]);
  });
});

describe('dispersão', () => {
  it('desvio padrão, menor e maior entre quem tem carteira', () => {
    const d = calcularDispersao([
      { semMunicipios: false, conta: { icaExato: 80 } },
      { semMunicipios: false, conta: { icaExato: 120 } },
      { semMunicipios: true, conta: { icaExato: 0 } },
    ]);
    expect(d).toEqual({ media: 100, desvioPadrao: 20, menor: 80, maior: 120, quantidade: 2 });
  });
});

describe('simulador de remanejamento', () => {
  const base: BaseIca = {
    coordenadores: [coordenador(1, 'Ana'), coordenador(2, 'Bia')],
    municipios: [municipio(1), municipio(2), municipio(3), municipio(4)],
    atendimentos: [
      atendimento(1, 1, 10),
      atendimento(1, 2, 10),
      atendimento(1, 3, 10),
      atendimento(2, 4, 10),
    ],
  };

  it('aplicarMovimentos não altera a base original e acusa movimento inválido', () => {
    const { base: nova, invalidos } = aplicarMovimentos(base, [
      { municipioId: 3, deCoordenadorId: 1, paraCoordenadorId: 2 },
      { municipioId: 4, deCoordenadorId: 1, paraCoordenadorId: 2 },
    ]);
    expect(nova.atendimentos.find((a) => a.municipio === 3)?.coordenador).toBe(2);
    expect(base.atendimentos.find((a) => a.municipio === 3)?.coordenador).toBe(1);
    expect(invalidos).toEqual([{ municipioId: 4, deCoordenadorId: 1, paraCoordenadorId: 2 }]);
  });

  it('troca no mesmo município: cada movimento leva o que a origem tinha antes, em qualquer ordem', () => {
    // Município 5: Ana atende a coleção 1; Bia, as coleções 3 e 4.
    const troca: BaseIca = {
      ...base,
      municipios: [...base.municipios, municipio(5)],
      atendimentos: [...base.atendimentos, atendimento(1, 5, 1), atendimento(2, 5, 3), atendimento(2, 5, 4)],
    };
    const colecoesEm5 = (b: BaseIca, coord: number) =>
      b.atendimentos.filter((a) => a.municipio === 5 && a.coordenador === coord).map((a) => a.projeto_geral).sort();
    const daAnaParaBia = { municipioId: 5, deCoordenadorId: 1, paraCoordenadorId: 2 };
    const daBiaParaAna = { municipioId: 5, deCoordenadorId: 2, paraCoordenadorId: 1 };
    for (const movimentos of [[daAnaParaBia, daBiaParaAna], [daBiaParaAna, daAnaParaBia]]) {
      const { base: nova, invalidos } = aplicarMovimentos(troca, movimentos);
      expect(invalidos).toEqual([]);
      expect(colecoesEm5(nova, 1)).toEqual([3, 4]);
      expect(colecoesEm5(nova, 2)).toEqual([1]);
    }
  });

  it('movimento com os atendimentos da proposta: move só esses; recusa se a origem mudou no município', () => {
    // Município 5: Ana atende a coleção 1; Bia, as coleções 3 e 4.
    const troca: BaseIca = {
      ...base,
      municipios: [...base.municipios, municipio(5)],
      atendimentos: [...base.atendimentos, atendimento(1, 5, 1), atendimento(2, 5, 3), atendimento(2, 5, 4)],
    };
    const em5 = (b: BaseIca, coord: number) => b.atendimentos.filter((a) => a.municipio === 5 && a.coordenador === coord);
    const daAna = em5(troca, 1).map((a) => a.id);
    const daBia = em5(troca, 2).map((a) => a.id);
    const daBiaParaAna = { municipioId: 5, deCoordenadorId: 2, paraCoordenadorId: 1, atendimentos: daBia };

    // Base como na proposta: vale e move só os atendimentos guardados.
    const intacta = aplicarMovimentos(troca, [daBiaParaAna]);
    expect(intacta.invalidos).toEqual([]);
    expect(em5(intacta.base, 1).map((a) => a.projeto_geral).sort()).toEqual([1, 3, 4]);

    // Outra proposta deu a coleção 1 de 5 para a Bia depois: a origem ganhou um atendimento no município.
    const depoisDeOutra = aplicarMovimentos(troca, [{ municipioId: 5, deCoordenadorId: 1, paraCoordenadorId: 2 }]).base;
    const recusada = aplicarMovimentos(depoisDeOutra, [daBiaParaAna]);
    expect(recusada.invalidos).toEqual([daBiaParaAna]);
    expect(em5(recusada.base, 2).map((a) => a.projeto_geral).sort()).toEqual([1, 3, 4]);

    // Atendimento guardado que já não está com a origem.
    const alheio = { ...daBiaParaAna, atendimentos: [...daBia, ...daAna] };
    expect(aplicarMovimentos(troca, [alheio]).invalidos).toEqual([alheio]);
  });

  it('mostra antes e depois de cada envolvido, a mudança de estrato e a nova dispersão', () => {
    const s = simularRemanejamento(base, PESOS_REVISADOS, [{ municipioId: 3, deCoordenadorId: 1, paraCoordenadorId: 2 }]);
    expect(s.envolvidos.map((e) => e.coordenadorId)).toEqual([1, 2]);
    const ana = s.envolvidos[0];
    const bia = s.envolvidos[1];
    expect(ana?.antes.conta.icaExibido).toBe(150);
    expect(ana?.depois.conta.icaExibido).toBe(100);
    expect(ana?.mudouEstrato).toBe(true);
    expect(bia?.antes.conta.icaExibido).toBe(50);
    expect(bia?.depois.conta.icaExibido).toBe(100);
    expect(ana?.variacao).toBe(-50);
    expect(s.dispersaoAntes.desvioPadrao).toBe(50);
    expect(s.dispersaoDepois.desvioPadrao).toBe(0);
    expect(s.mudancasDeEstrato).toHaveLength(2);
  });
});

describe('comparativo entre duas versões de pesos', () => {
  it('aponta quem muda de estrato', () => {
    // Ana: 3 municípios em 3 estados, poucas turmas e professores; Bia: o contrário.
    // v5: Ana 100 (Adequada); revisada: Ana 110 (Atenção). Bia: 100 → 90, segue Adequada.
    const base: BaseIca = {
      coordenadores: [coordenador(1, 'Ana'), coordenador(2, 'Bia')],
      municipios: [municipio(1, { uf: 'CE' }), municipio(2, { uf: 'PE' }), municipio(3, { uf: 'PI' }), municipio(4, { uf: 'CE' })],
      atendimentos: [
        atendimento(1, 1, 10, 1, 40),
        atendimento(1, 2, 10, 1, 40),
        atendimento(1, 3, 10, 1, 40),
        atendimento(2, 4, 10, 9, 360),
      ],
    };
    const c = compararPesos(base, PESOS_ORIGINAIS_V5, PESOS_REVISADOS);
    expect(c.linhas).toHaveLength(2);
    expect(c.linhas.map((l) => [l.antes.conta.icaExibido, l.depois.conta.icaExibido])).toEqual([[100, 110], [100, 90]]);
    expect(c.mudaramDeEstrato.map((l) => l.coordenadorId)).toEqual([1]);
    expect(c.mudaramDeEstrato[0]?.antes.conta.estrato).toBe('adequada');
    expect(c.mudaramDeEstrato[0]?.depois.conta.estrato).toBe('atencao');
  });
});

describe('alertas (PDF, seção 6) com quem receberia', () => {
  const base: BaseIca = {
    coordenadores: [coordenador(1, 'Ana'), coordenador(2, 'Bia'), coordenador(3, 'Caio'), coordenador(4, 'Duda')],
    municipios: [municipio(1), municipio(2), municipio(3), municipio(4), municipio(5), municipio(6)],
    atendimentos: [
      atendimento(1, 1, 10, 4, 200),
      atendimento(1, 2, 10, 4, 200),
      atendimento(1, 3, 10, 4, 200),
      atendimento(2, 4, 10, null, 20),
      atendimento(null, 5, 10),
      atendimento(4, 6, 10, 1, 0, 400),
    ],
  };
  const gerencias = [{ id: 1, nome: 'Gerência 1', gestora_tecnica: 900 }];
  const pessoas = [{ id: 900, nome: 'Gestora Fictícia' }];
  const r = calcularEquipe(base, PESOS_REVISADOS);
  const alertas = gerarAlertas(base, r, { gerencias, pessoas });
  const doTipo = (t: string) => alertas.filter((a) => a.tipo === t);

  it('Sobrecarga vai para SPE, gestora técnica e Líder do NFP', () => {
    const [a] = doTipo('sobrecarga');
    expect(a?.coordenadorId).toBe(1);
    expect(a?.quemReceberia).toEqual(['SPE', 'Gestora técnica (Gestora Fictícia)', 'Líder do NFP']);
  });

  it('fora da meta vai para a SPE', () => {
    const fora = doTipo('fora_da_meta');
    expect(fora.map((a) => a.coordenadorId)).toContain(1);
    expect(fora.every((a) => a.quemReceberia.join() === 'SPE')).toBe(true);
  });

  it('contrato sem coordenador vai para gestora operacional e SPE', () => {
    const [a] = doTipo('contrato_sem_coordenador');
    expect(a?.municipioId).toBe(5);
    expect(a?.quemReceberia).toEqual(['Gestora operacional', 'SPE']);
  });

  it('dado incompleto e improvável vão para a gestora operacional', () => {
    expect(doTipo('dado_incompleto')[0]?.coordenadorId).toBe(2);
    expect(doTipo('dado_improvavel')[0]?.coordenadorId).toBe(4);
    expect(doTipo('dado_incompleto')[0]?.quemReceberia).toEqual(['Gestora operacional']);
  });

  it('coordenador sem municípios vai para SPE e Líder do NFP', () => {
    const [a] = doTipo('sem_municipios');
    expect(a?.coordenadorId).toBe(3);
    expect(a?.quemReceberia).toEqual(['SPE', 'Líder do NFP']);
  });

  it('dois contratos sem coordenador no mesmo município: um alerta para cada, com a coleção no título', () => {
    const doisNoMesmo: BaseIca = {
      ...base,
      atendimentos: [...base.atendimentos, atendimento(null, 5, 11)],
    };
    const titulos = gerarAlertas(doisNoMesmo, calcularEquipe(doisNoMesmo, PESOS_REVISADOS), {
      gerencias,
      pessoas,
      colecoes: [
        { id: 10, nome: 'NOVO LENDO' },
        { id: 11, nome: 'TEMA' },
      ],
    })
      .filter((a) => a.tipo === 'contrato_sem_coordenador')
      .map((a) => a.titulo);
    expect(titulos).toEqual([
      'Contrato sem coordenador em Município 5-CE (NOVO LENDO)',
      'Contrato sem coordenador em Município 5-CE (TEMA)',
    ]);
  });

  it('"entra em Sobrecarga" só para quem não estava antes, quando há o retrato anterior', () => {
    const repetido = gerarAlertas(base, r, { gerencias, pessoas, anterior: r });
    expect(repetido.filter((a) => a.tipo === 'sobrecarga')).toHaveLength(0);
  });
});
