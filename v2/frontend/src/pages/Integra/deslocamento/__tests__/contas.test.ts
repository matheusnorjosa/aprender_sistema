/**
 * Contas das telas do Deslocamento: o resumo da página 1 do relatório (tempos REAIS) e a soma por
 * coordenador sobre as carteiras FICTÍCIAS do gerador (a mesma soma do componente "deslocamento" do ICA).
 */
import { describe, expect, it } from 'vitest';

import { calcularEquipe, formatarHoras, PESOS_REVISADOS } from '../../ica/calculo';
import { DESLOCAMENTO_MUNICIPIOS } from '../../dados/deslocamento';
import { gerarDadosSimulados } from '../../dados/gerador';
import { faixaDoMunicipio, resumoDoRelatorio, somaPorCoordenador, ufsNaOrdemDoRelatorio } from '../contas';

const dados = gerarDadosSimulados();
const resultado = calcularEquipe(dados.base, PESOS_REVISADOS);

describe('resumoDoRelatorio', () => {
  it('os números da página 1: 92, 23 por terra, 69 de avião (35 com conexão), faixas 7/7/34/44', () => {
    const r = resumoDoRelatorio(DESLOCAMENTO_MUNICIPIOS);
    expect(r.total).toBe(92);
    expect(r.porMeio).toEqual({ carro: 23, aviao: 69 });
    expect(r.comConexao).toBe(35);
    expect(r.porFaixa).toEqual({ proximo: 7, medio: 7, longo: 34, muito_longo: 44 });
  });

  it('menor e maior ida e volta, com o município', () => {
    const r = resumoDoRelatorio(DESLOCAMENTO_MUNICIPIOS);
    expect(`${r.menor.nome}-${r.menor.uf} ${r.menor.ida_volta_texto}`).toBe('Maracanaú-CE 0h40');
    expect(`${r.maior.nome}-${r.maior.uf} ${r.maior.ida_volta_texto}`).toBe('Filadélfia-BA 31h35');
  });

  it('mediana: a que o relatório escreve (17h45) e a da conta com a tabela (17h47min30s, que arredonda para 17h48)', () => {
    const r = resumoDoRelatorio(DESLOCAMENTO_MUNICIPIOS);
    expect(r.medianaDoRelatorio).toBe('17h45');
    // 17h35 e 18h00 no meio: 1067,5 min, que o ponto flutuante guarda como 1067,4999...; meio para cima dá 17h48.
    expect(formatarHoras(r.medianaCalculada)).toBe('17h48');
  });
});

describe('ufsNaOrdemDoRelatorio', () => {
  it('cada UF uma vez, na ordem do relatório, com a quantidade', () => {
    const ufs = ufsNaOrdemDoRelatorio(DESLOCAMENTO_MUNICIPIOS);
    expect(ufs.slice(0, 3)).toEqual([
      { uf: 'CE', quantidade: 17 },
      { uf: 'PB', quantidade: 2 },
      { uf: 'PE', quantidade: 5 },
    ]);
    expect(ufs.reduce((s, u) => s + u.quantidade, 0)).toBe(92);
  });
});

describe('faixaDoMunicipio', () => {
  it('a faixa que o relatório escreve; sem localidade = null', () => {
    const craibas = dados.base.municipios.find((m) => m.nome === 'Craíbas')!;
    expect(faixaDoMunicipio(craibas)).toBe('muito_longo');
    const amigosDoBem = dados.base.municipios.find((m) => m.deslocamento_horas === null)!;
    expect(faixaDoMunicipio(amigosDoBem)).toBeNull();
  });
});

describe('somaPorCoordenador', () => {
  const linhas = somaPorCoordenador(resultado);

  it('uma linha por coordenador, da maior soma para a menor; quem está sem municípios no fim', () => {
    expect(linhas).toHaveLength(17);
    const somas = linhas.map((l) => l.somaHoras);
    expect([...somas].sort((a, b) => b - a)).toEqual(somas);
    expect(linhas.at(-1)?.coordenador.nome).toBe('Priscila Vasconcelos');
    expect(linhas.at(-1)?.municipios).toBe(0);
  });

  it('a soma é a mesma do componente "Tempo de deslocamento" do ICA (só municípios ativos)', () => {
    for (const l of linhas) {
      const r = resultado.coordenadores.find((x) => x.coordenador.id === l.coordenador.id)!;
      expect(l.somaHoras).toBe(r.valores.deslocamento);
      expect(l.municipios).toBe(r.valores.municipios);
    }
  });

  it('média por município, maior trajeto e contagem por faixa', () => {
    const lucineia = linhas.find((l) => l.coordenador.id === 101)!;
    expect(lucineia.municipios).toBe(9);
    expect(lucineia.mediaHoras).toBeCloseTo(lucineia.somaHoras / 9);
    expect(lucineia.maior?.municipio.nome).toBe('Guarapuava');
    expect(lucineia.porFaixa.muito_longo + lucineia.porFaixa.longo + lucineia.porFaixa.medio + lucineia.porFaixa.proximo).toBe(9);
  });

  it('sem localidade conta a mediana e fica marcado como estimado; suspenso não entra', () => {
    const rogerio = linhas.find((l) => l.coordenador.id === 110)!;
    expect(rogerio.estimados).toEqual(['Amigos do Bem-CE']);
    const jucelia = linhas.find((l) => l.coordenador.id === 107)!;
    // Capivari-SP está com as ações suspensas: fica fora da soma.
    expect(jucelia.municipios).toBe(7);
    expect(jucelia.suspensos).toEqual(['Capivari-SP']);
  });
});
