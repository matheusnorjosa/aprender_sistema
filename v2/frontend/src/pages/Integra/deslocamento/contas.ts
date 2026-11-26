/**
 * Contas das telas do Deslocamento. Funções puras.
 *
 * - `resumoDoRelatorio`: os números da página 1 do relatório de tempos (dados REAIS, `dados/deslocamento.ts`).
 * - `somaPorCoordenador`: o tempo de ida e volta somado na carteira de cada coordenador (FICTÍCIA, do
 *   gerador). É o mesmo valor do componente "Tempo de deslocamento" do ICA: só municípios ativos, e o
 *   local que não está no relatório conta o tempo do meio, 17h45 (estimado). A decisão 55 vale para o município sem
 *   localidade definida; para o local conhecido fora do relatório, é leitura do protótipo (Para validar).
 */
import type { UFCode } from '@/types/organizacao';

import { formatarHoras, type LinhaCarteira, type ResultadoCoordenador, type ResultadoEquipe } from '../ica/calculo';
import {
  contarPorFaixa,
  contarPorMeio,
  DESLOCAMENTO_MUNICIPIOS,
  TEMPO_DO_MEIO_HORAS,
  type FaixaDeslocamento,
  type MunicipioDeslocamento,
} from '../dados/deslocamento';
import { localidadeDoMunicipio } from '../dados/municipios';
import type { MeioDeslocamento, MunicipioIntegra } from '../dados/tipos';

export interface ResumoDoRelatorio {
  total: number;
  porMeio: Record<MeioDeslocamento, number>;
  /** Com trecho aéreo e pelo menos uma conexão. */
  comConexao: number;
  porFaixa: Record<FaixaDeslocamento, number>;
  menor: MunicipioDeslocamento;
  maior: MunicipioDeslocamento;
  /** A mediana que a página 1 do relatório escreve (17h45): o tempo do meio (decisão 55). */
  medianaDoRelatorio: string;
}

export function resumoDoRelatorio(municipios: readonly MunicipioDeslocamento[]): ResumoDoRelatorio {
  const ordenados = [...municipios].sort((a, b) => a.ida_volta_horas - b.ida_volta_horas);
  const menor = ordenados[0];
  const maior = ordenados.at(-1);
  if (!menor || !maior) throw new Error('Relatório sem municípios.');
  return {
    total: municipios.length,
    porMeio: contarPorMeio(municipios),
    comConexao: municipios.filter((m) => m.detalhe_rota?.includes('conexão')).length,
    porFaixa: contarPorFaixa(municipios),
    menor,
    maior,
    medianaDoRelatorio: formatarHoras(TEMPO_DO_MEIO_HORAS),
  };
}

/** Cada UF uma vez, na ordem em que o relatório as apresenta, com quantos municípios tem. */
export function ufsNaOrdemDoRelatorio(municipios: readonly MunicipioDeslocamento[]): { uf: UFCode; quantidade: number }[] {
  const ufs: { uf: UFCode; quantidade: number }[] = [];
  for (const m of municipios) {
    const item = ufs.find((u) => u.uf === m.uf);
    if (item) item.quantidade += 1;
    else ufs.push({ uf: m.uf, quantidade: 1 });
  }
  return ufs;
}

/**
 * A linha do relatório para um município do ICA (mesmo nome e UF; a linha do Amigos do Bem usa a localidade
 * dela, decisão 56); `undefined` se não estiver lá.
 */
export function linhaDoRelatorio(municipio: Pick<MunicipioIntegra, 'nome' | 'uf'>): MunicipioDeslocamento | undefined {
  const nome = localidadeDoMunicipio(municipio.nome);
  return DESLOCAMENTO_MUNICIPIOS.find((m) => m.nome === nome && m.uf === municipio.uf);
}

/** A faixa que o relatório dá ao município; `null` quando ele não tem tempo no relatório. */
export function faixaDoMunicipio(municipio: MunicipioIntegra): FaixaDeslocamento | null {
  if (municipio.deslocamento_horas === null) return null;
  return linhaDoRelatorio(municipio)?.faixa ?? null;
}

export interface SomaDoCoordenador {
  coordenador: ResultadoCoordenador['coordenador'];
  /** Municípios ativos da carteira. */
  municipios: number;
  /** Horas de ida e volta somadas (o componente "deslocamento" do ICA). */
  somaHoras: number;
  /** Média por município ativo; 0 quando não há nenhum. */
  mediaHoras: number;
  /** O município ativo mais longe. */
  maior: LinhaCarteira | null;
  porFaixa: Record<FaixaDeslocamento, number>;
  /** "Nome-UF" dos que entram com o tempo do meio (sem tempo no relatório). */
  estimados: string[];
  /** "Nome-UF" dos suspensos: ficam fora da soma. */
  suspensos: string[];
}

const nomeUf = (l: LinhaCarteira): string => `${l.municipio.nome}-${l.municipio.uf}`;

export function somaPorCoordenador(resultado: ResultadoEquipe): SomaDoCoordenador[] {
  const linhas = resultado.coordenadores.map((r): SomaDoCoordenador => {
    const ativas = r.carteira.filter((l) => l.ativo);
    const porFaixa: Record<FaixaDeslocamento, number> = { proximo: 0, medio: 0, longo: 0, muito_longo: 0 };
    for (const l of ativas) {
      const faixa = faixaDoMunicipio(l.municipio);
      if (faixa) porFaixa[faixa] += 1;
    }
    const maior = ativas.filter((l) => !l.estimado).reduce<LinhaCarteira | null>((m, l) => (m === null || l.horas > m.horas ? l : m), null);
    return {
      coordenador: r.coordenador,
      municipios: r.valores.municipios,
      somaHoras: r.valores.deslocamento,
      mediaHoras: ativas.length > 0 ? r.valores.deslocamento / ativas.length : 0,
      maior,
      porFaixa,
      estimados: ativas.filter((l) => l.estimado).map(nomeUf),
      suspensos: r.carteira.filter((l) => !l.ativo).map(nomeUf),
    };
  });
  return linhas.sort((a, b) => b.somaHoras - a.somaHoras || a.coordenador.nome.localeCompare(b.coordenador.nome, 'pt-BR'));
}
