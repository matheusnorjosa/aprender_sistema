/**
 * Contas das telas da parte C2 do ICA (por gerência, histórico, alertas). Funções puras, em cima
 * do resultado de `calcularEquipe` (`ica/calculo.ts`).
 */
import type { Gerencia, Pessoa, Remanejamento, VersaoPesos } from '../../../dados/tipos';
import { arredondarIca, estratoDoIca, type Estrato, type ResultadoCoordenador, type ResultadoEquipe, type TipoAlerta } from '../../calculo';

export interface ResumoGerencia {
  gerencia: Gerencia;
  /** Nome da gestora técnica (ou "Não informada"). */
  gestoraTecnica: string;
  coordenadores: ResultadoCoordenador[];
  /** Quantos têm pelo menos um município ativo (entram no ICA médio). */
  comCarteira: number;
  /** Municípios ativos distintos (o compartilhado dentro da gerência conta uma vez). */
  municipiosAtivos: number;
  /** Professores em formação nos municípios ativos dos coordenadores da gerência. */
  professores: number;
  icaMedioExato: number | null;
  /** ICA médio exibido (inteiro); `null` quando ninguém da gerência tem carteira. */
  icaMedio: number | null;
  estrato: Estrato | null;
}

/** Uma linha por gerência, na ordem recebida. */
export function resumoPorGerencia(
  resultado: ResultadoEquipe,
  gerencias: readonly Gerencia[],
  pessoas: readonly Pessoa[],
): ResumoGerencia[] {
  return gerencias.map((gerencia) => {
    const coordenadores = resultado.coordenadores.filter((r) => r.coordenador.gerencia === gerencia.id);
    const comCarteira = coordenadores.filter((r) => !r.semMunicipios);
    const municipios = new Set(
      coordenadores.flatMap((r) => r.carteira.filter((l) => l.ativo).map((l) => l.municipio.id)),
    );
    const icaMedioExato =
      comCarteira.length > 0 ? comCarteira.reduce((s, r) => s + r.conta.icaExato, 0) / comCarteira.length : null;
    const icaMedio = icaMedioExato === null ? null : arredondarIca(icaMedioExato);
    return {
      gerencia,
      gestoraTecnica: pessoas.find((p) => p.id === gerencia.gestora_tecnica)?.nome ?? 'Não informada',
      coordenadores,
      comCarteira: comCarteira.length,
      municipiosAtivos: municipios.size,
      professores: coordenadores.reduce((s, r) => s + r.valores.professores, 0),
      icaMedioExato,
      icaMedio,
      estrato: icaMedio === null ? null : estratoDoIca(icaMedio),
    };
  });
}

/**
 * Data do último recálculo: a do retrato semestral, ou a de uma mudança feita depois dele na sessão
 * (versão de pesos nova ou remanejamento aplicado), a que for mais recente.
 */
export function dataDoUltimoRecalculo(
  ultimoSemestre: string,
  versaoVigente: VersaoPesos,
  remanejamentos: readonly Remanejamento[],
): string {
  const datas = [ultimoSemestre, versaoVigente.criada_em, ...remanejamentos.map((r) => r.aplicado_em)].filter(
    (d): d is string => d !== null,
  );
  return datas.reduce((maior, d) => (new Date(d).getTime() > new Date(maior).getTime() ? d : maior));
}

/** Situação do alerta no protótipo: está aberto, e o que o fecha. */
export function situacaoDoAlerta(tipo: TipoAlerta): string {
  switch (tipo) {
    case 'sobrecarga':
    case 'fora_da_meta':
      return 'Aberto: sai no próximo recálculo, se o ICA voltar para a faixa.';
    case 'sem_municipios':
      return 'Aberto: sai quando a coordenadora ou o coordenador receber um município.';
    case 'contrato_sem_coordenador':
      return 'Aberto: sai quando o projeto tiver um coordenador definido.';
    case 'dado_incompleto':
    case 'dado_improvavel':
      return 'Aberto: sai quando o cadastro for corrigido ou conferido.';
  }
}

/** Nome do tipo de alerta, como no PDF (seção 6). */
export const NOME_DO_ALERTA: Record<TipoAlerta, string> = {
  sobrecarga: 'Está em Sobrecarga',
  sem_municipios: 'Sem municípios',
  contrato_sem_coordenador: 'Projeto sem coordenador',
  dado_incompleto: 'Dado incompleto',
  dado_improvavel: 'Valor improvável',
  fora_da_meta: 'Fora da meta',
};
