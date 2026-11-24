/**
 * Estado da sessão da demonstração: pesos com versão, remanejamento (propor → aprovar → aplicar),
 * alertas calculados e volta ao original. Nada é gravado: recarregar a página volta ao começo.
 */
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { PESOS_ORIGINAIS_V5, PESOS_REVISADOS } from '../../ica/calculo';
import { IntegraDemoProvider, estadoInicial, reducerIntegraDemo, useIntegraDemo } from '../IntegraDemoContext';
import { gerarDadosSimulados } from '../gerador';

const dados = gerarDadosSimulados();
const wrapper = ({ children }: { children: ReactNode }) => <IntegraDemoProvider>{children}</IntegraDemoProvider>;
const AUTOR = 'Você (demonstração)';

/** Um movimento válido: o primeiro município ativo da coordenadora mais carregada vai para a recém-chegada. */
function movimentoValido() {
  const de = 101;
  const a = dados.base.atendimentos.find(
    (x) => x.coordenador === de && dados.base.municipios.find((m) => m.id === x.municipio)?.status === 'ativo',
  );
  if (!a) throw new Error('sem atendimento');
  return { municipioId: a.municipio, deCoordenadorId: de, paraCoordenadorId: 117 };
}

describe('useIntegraDemo', { timeout: 20000 }, () => {
  it('fora do provider avisa com erro claro', () => {
    expect(() => renderHook(() => useIntegraDemo())).toThrow(/IntegraDemoProvider/);
  });

  it('começa com os dados da fonte, a versão revisada e o resultado calculado', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    expect(result.current.dados).toEqual(dados);
    expect(result.current.versaoVigente.id).toBe('revisada-2026-11');
    expect(result.current.pesos).toEqual(PESOS_REVISADOS);
    expect(result.current.resultado.porEstrato).toEqual({ sobrecarga: 3, atencao: 2, adequada: 6, capacidade: 5 });
    expect(result.current.resultado.semMunicipios).toBe(1);
    expect(result.current.historico.map((h) => h.semestre)).toEqual(['2025.2', '2026.1', '2026.2']);
    expect(result.current.historico[0]?.versao.id).toBe('v5');
    // Os 3 em Sobrecarga já estavam lá em 2026.1: não "entram" de novo (PDF, seção 6); ficam fora da meta.
    expect(result.current.alertas.filter((a) => a.tipo === 'sobrecarga')).toHaveLength(0);
    const foraDaMeta = result.current.alertas.filter((a) => a.tipo === 'fora_da_meta').map((a) => a.coordenadorId);
    expect(foraDaMeta).toEqual(expect.arrayContaining([101, 102, 103]));
  });

  it('"entrou em Sobrecarga" compara com o semestre anterior: só quem não estava lá', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    let id = '';
    act(() => {
      // Belém-PA sai da Lucinéia (já em Sobrecarga) e vai para a Heloísa (Atenção em 2026.1).
      const r = result.current.proporRemanejamento([{ municipioId: 1, deCoordenadorId: 101, paraCoordenadorId: 104 }], 'teste');
      if (r.ok) id = r.id;
    });
    act(() => result.current.aprovarRemanejamento(id));
    act(() => {
      result.current.aplicarRemanejamento(id);
    });
    const sobrecarga = result.current.alertas.filter((a) => a.tipo === 'sobrecarga');
    expect(sobrecarga.map((a) => a.titulo)).toEqual(['Heloísa Pimentel entrou em Sobrecarga (137)']);
    expect(sobrecarga[0]?.quemReceberia[1]).toMatch(/^Gestora técnica \(/);
  });

  it('depois de mudar a carteira, "entrou em Sobrecarga" compara com o último cálculo publicado (2026.2)', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    const manaus = dados.base.municipios.find((m) => m.nome === 'Manaus');
    if (!manaus) throw new Error('sem Manaus');
    // Jucélia (107): Sobrecarga em 2026.1, Atenção no 2026.2 publicado; com Manaus, volta à Sobrecarga.
    let id = '';
    act(() => {
      const r = result.current.proporRemanejamento([{ municipioId: manaus.id, deCoordenadorId: 101, paraCoordenadorId: 107 }], 'teste');
      if (r.ok) id = r.id;
    });
    act(() => result.current.aprovarRemanejamento(id));
    act(() => {
      result.current.aplicarRemanejamento(id);
    });
    const sobrecarga = result.current.alertas.filter((a) => a.tipo === 'sobrecarga').map((a) => a.titulo);
    expect(sobrecarga).toContain('Jucélia Montenegro entrou em Sobrecarga (131)');
  });

  it('depois de trocar os pesos, a base do "entrou em Sobrecarga" também é o 2026.2 publicado', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    // Pesos só em turmas, professores e estados: Jucélia (107, Atenção no 2026.2 publicado) passa de 130.
    act(() => {
      result.current.trocarPesos(
        { municipios: 0, frentes: 0, turmas: 40, professores: 30, deslocamento: 0, estados: 30 },
        'teste',
      );
    });
    const jucelia = result.current.resultado.coordenadores.find((r) => r.coordenador.id === 107);
    expect(jucelia?.conta.estrato).toBe('sobrecarga');
    const alertados = result.current.alertas.filter((a) => a.tipo === 'sobrecarga').map((a) => a.coordenadorId);
    expect(alertados).toContain(107);
  });

  it('trocar pesos exige soma 100 e justificativa; a versão nova vira a vigente', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    let r = result.current.trocarPesos({ ...PESOS_REVISADOS, municipios: 30 }, 'teste');
    expect(r.ok).toBe(false);
    r = result.current.trocarPesos(PESOS_ORIGINAIS_V5, '   ');
    expect(r).toEqual({ ok: false, erros: ['Escreva a justificativa da mudança.'] });
    act(() => {
      r = result.current.trocarPesos(PESOS_ORIGINAIS_V5, 'Comparar com a v5');
    });
    expect(r.ok).toBe(true);
    expect(result.current.versoesPesos).toHaveLength(3);
    expect(result.current.versaoVigente.autor).toBe(AUTOR);
    expect(result.current.versaoVigente.justificativa).toBe('Comparar com a v5');
    expect(result.current.pesos).toEqual(PESOS_ORIGINAIS_V5);
  });

  it('remanejamento: propor → aprovar → aplicar muda a carteira e recalcula', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    const antes = result.current.resultado.coordenadores.find((c) => c.coordenador.id === 117);
    expect(antes?.semMunicipios).toBe(true);

    expect(result.current.proporRemanejamento([], 'x').ok).toBe(false);
    expect(result.current.proporRemanejamento([movimentoValido()], '').ok).toBe(false);
    const invalido = { municipioId: 9999, deCoordenadorId: 101, paraCoordenadorId: 117 };
    expect(result.current.proporRemanejamento([invalido], 'x').ok).toBe(false);

    let id = '';
    act(() => {
      const r = result.current.proporRemanejamento([movimentoValido()], 'Dar a primeira carteira à recém-chegada');
      if (r.ok) id = r.id;
    });
    expect(id).not.toBe('');
    const proposto = result.current.remanejamentos.find((r) => r.id === id);
    expect(proposto).toMatchObject({ status: 'proposto', proposto_por: AUTOR, aprovado_em: null });
    // Proposto ainda não muda nada.
    expect(result.current.resultado.coordenadores.find((c) => c.coordenador.id === 117)?.semMunicipios).toBe(true);

    // Aplicar antes de aprovar não faz nada.
    act(() => {
      result.current.aplicarRemanejamento(id);
    });
    expect(result.current.remanejamentos.find((r) => r.id === id)?.status).toBe('proposto');

    act(() => result.current.aprovarRemanejamento(id));
    expect(result.current.remanejamentos.find((r) => r.id === id)).toMatchObject({ status: 'aprovado', aprovado_por: AUTOR });

    act(() => {
      result.current.aplicarRemanejamento(id);
    });
    expect(result.current.remanejamentos.find((r) => r.id === id)).toMatchObject({ status: 'aplicado', semestre: '2026.2' });
    expect(result.current.resultado.coordenadores.find((c) => c.coordenador.id === 117)?.semMunicipios).toBe(false);
    // O histórico e os dados originais não mudam.
    expect(result.current.dados).toEqual(dados);
  });

  it('proposta que ficou velha não é aplicada: nada muda e a resposta diz por quê', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    // Duas propostas para o mesmo município (Belém-PA, da Lucinéia): cada uma é válida quando é feita.
    const ids: string[] = [];
    for (const destino of [104, 105]) {
      act(() => {
        const r = result.current.proporRemanejamento([{ municipioId: 1, deCoordenadorId: 101, paraCoordenadorId: destino }], 'teste');
        if (r.ok) ids.push(r.id);
      });
    }
    const [a, b] = ids as [string, string];
    act(() => result.current.aprovarRemanejamento(a));
    act(() => result.current.aprovarRemanejamento(b));
    act(() => {
      expect(result.current.aplicarRemanejamento(a)).toEqual({ ok: true });
    });
    const baseDepoisDeA = result.current.base;

    const respostas: ReturnType<typeof result.current.aplicarRemanejamento>[] = [];
    act(() => {
      respostas.push(result.current.aplicarRemanejamento(b));
    });
    const [resposta] = respostas;
    expect(resposta?.ok).toBe(false);
    expect(resposta && !resposta.ok ? resposta.erros : []).toEqual([
      'Esta proposta ficou velha: Belém-PA já não está com Lucinéia Barreto. Proponha de novo a partir da carteira de agora.',
    ]);
    expect(result.current.base).toBe(baseDepoisDeA);
    expect(result.current.remanejamentos.find((r) => r.id === b)).toMatchObject({ status: 'aprovado', aplicado_em: null });
  });

  it('duas propostas no mesmo município em cadeia: a segunda, feita antes da primeira valer, é recusada', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    const recife = dados.base.municipios.find((m) => m.nome === 'Recife' && m.uf === 'PE')!.id;
    const ica = (id: number) => result.current.resultado.coordenadores.find((c) => c.coordenador.id === id)?.conta.icaExibido;
    // P1: Recife de 106 para 111. P2 (com a base ainda intacta): Recife de 111 para 104.
    const ids: string[] = [];
    for (const [de, para] of [[106, 111], [111, 104]] as const) {
      act(() => {
        const r = result.current.proporRemanejamento([{ municipioId: recife, deCoordenadorId: de, paraCoordenadorId: para }], 'teste');
        if (!r.ok) throw new Error(r.erros.join(' '));
        ids.push(r.id);
      });
    }
    const [p1, p2] = ids as [string, string];
    act(() => result.current.aprovarRemanejamento(p1));
    act(() => result.current.aprovarRemanejamento(p2));
    act(() => {
      expect(result.current.aplicarRemanejamento(p1)).toEqual({ ok: true });
    });
    const baseDepoisDeP1 = result.current.base;
    const icaDe104 = ica(104);

    const respostas: ReturnType<typeof result.current.aplicarRemanejamento>[] = [];
    act(() => {
      respostas.push(result.current.aplicarRemanejamento(p2));
    });
    const [resposta] = respostas;
    expect(resposta && !resposta.ok ? resposta.erros : []).toEqual([
      'Esta proposta ficou velha: a carteira de Socorro Bezerra Lins em Recife-PE mudou depois da proposta. Proponha de novo a partir da carteira de agora.',
    ]);
    // Nada mudou: a P2 não levou o que a P1 acabou de entregar.
    expect(result.current.base).toBe(baseDepoisDeP1);
    expect(ica(104)).toBe(icaDe104);
    expect(result.current.remanejamentos.find((r) => r.id === p2)).toMatchObject({ status: 'aprovado', aplicado_em: null });
  });

  it('restaurar volta tudo ao original', () => {
    const { result } = renderHook(() => useIntegraDemo(), { wrapper });
    act(() => {
      result.current.trocarPesos(PESOS_ORIGINAIS_V5, 'teste');
    });
    act(() => result.current.restaurar());
    expect(result.current.versoesPesos).toHaveLength(2);
    expect(result.current.pesos).toEqual(PESOS_REVISADOS);
    expect(result.current.base).toEqual(dados.base);
  });
});

describe('reducerIntegraDemo', () => {
  it('é puro: não altera o estado recebido', () => {
    const inicial = estadoInicial(dados);
    const copia = structuredClone(inicial);
    reducerIntegraDemo(inicial, {
      tipo: 'propor_remanejamento',
      id: 'r1',
      movimentos: [movimentoValido()],
      justificativa: 'x',
      em: '2026-11-24T10:00:00-03:00',
    });
    expect(inicial).toEqual(copia);
  });

  it('propor guarda em cada movimento os atendimentos que ele move, tirados da carteira de agora', () => {
    const inicial = estadoInicial(dados);
    const m = movimentoValido();
    const depois = reducerIntegraDemo(inicial, {
      tipo: 'propor_remanejamento',
      id: 'r1',
      movimentos: [m],
      justificativa: 'x',
      em: '2026-11-24T10:00:00-03:00',
    });
    const esperados = dados.base.atendimentos
      .filter((a) => a.municipio === m.municipioId && a.coordenador === m.deCoordenadorId)
      .map((a) => a.id);
    expect(esperados.length).toBeGreaterThan(0);
    expect(depois.remanejamentos.at(-1)?.movimentos).toEqual([{ ...m, atendimentos: esperados }]);
  });

  it('aplicar proposta com movimento que já não vale devolve o estado como está', () => {
    const aprovada = (id: string, para: number) => ({
      id,
      movimentos: [{ municipioId: 1, deCoordenadorId: 101, paraCoordenadorId: para }],
      justificativa: 'x',
      status: 'aprovado' as const,
      proposto_por: AUTOR,
      proposto_em: '2026-11-24T10:00:00-03:00',
      aprovado_por: AUTOR,
      aprovado_em: '2026-11-24T10:00:00-03:00',
      aplicado_em: null,
      semestre: null,
    });
    const inicial = estadoInicial(dados);
    const comDuas = { ...inicial, remanejamentos: [...inicial.remanejamentos, aprovada('a', 104), aprovada('b', 105)] };
    const depoisDeA = reducerIntegraDemo(comDuas, { tipo: 'aplicar_remanejamento', id: 'a', em: '2026-11-24T11:00:00-03:00' });
    expect(reducerIntegraDemo(depoisDeA, { tipo: 'aplicar_remanejamento', id: 'b', em: '2026-11-24T12:00:00-03:00' })).toBe(depoisDeA);
  });
});
