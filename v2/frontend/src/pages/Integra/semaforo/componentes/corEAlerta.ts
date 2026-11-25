/**
 * Cores e alertas das telas do Semáforo (Pesquisa, Indicadores da Líder, Relatório mensal).
 *
 * As cores são as do ICA (`ica/componentes/estilos.ts`), com o contraste já conferido lá: texto 4,5:1
 * sobre o fundo e barra 3:1. Toda cor vai para a tela com o nome escrito ao lado.
 */
import { COR_ESTRATO, type CorEstrato } from '../../ica/componentes/estilos';
import type { SituacaoMunicipio } from '../dados';
import type { Cor, CorIndicador, ResultadoCor } from '../tipos';

export const COR_SEMAFORO: Record<CorIndicador, CorEstrato> = {
  verde: COR_ESTRATO.adequada,
  amarelo: COR_ESTRATO.atencao,
  vermelho: COR_ESTRATO.sobrecarga,
  sem_dado: { fundo: '#F0F0F0', texto: '#3D3D3D', forte: '#6B6B6B' },
};

export const CORES: readonly Cor[] = ['verde', 'amarelo', 'vermelho'];

/** "Horizonte-CE". */
export function nomeDoMunicipio(m: { nome: string; uf: string }): string {
  return `${m.nome}-${m.uf}`;
}

/** A cor sugerida do ciclo atual (o último ciclo da situação). */
export function sugeridaAgora(situacoes: readonly SituacaoMunicipio[], municipio: number): ResultadoCor | null {
  return situacoes.find((s) => s.municipio === municipio)?.ciclos.at(-1)?.resultado ?? null;
}

/** Quem age na cor (seção 5 do PDF): a gestora de referência e, no vermelho, a gestora pedagógica; no amarelo, o coordenador. */
function quemAge(cor: Cor, gestora: string, coordenador: string | null): string[] {
  const ref = `${gestora} (gestora de referência)`;
  if (cor === 'vermelho') return [ref, 'Gestora pedagógica'];
  return [ref, ...(coordenador ? [`${coordenador} (coordenador)`] : [])];
}

/**
 * Para quem iria o alerta de piora. Seção 8 do PDF: "Município passa a vermelho" vai, na hora, para a gestora de
 * referência, a gestora pedagógica, a SPE e a Líder do NFP. A tabela não tem linha para "passa a amarelo": o
 * protótipo avisa quem age no amarelo e a SPE. No protótipo nada é enviado.
 */
export function destinatariosDaPiora(cor: Cor, gestora: string, coordenador: string | null): string[] {
  return [...quemAge(cor, gestora, coordenador), 'SPE', ...(cor === 'vermelho' ? ['Líder do NFP'] : [])];
}

/**
 * Para quem iria o alerta de prazo da tarefa. Seção 8 do PDF: "Prazo de resposta a cor vencendo ou vencido" vai
 * para o responsável pela tarefa (quem age na cor da tarefa) e a SPE, um dia antes e no vencimento.
 */
export function destinatariosDoPrazo(cor: Cor, gestora: string, coordenador: string | null): string[] {
  return [...quemAge(cor, gestora, coordenador), 'SPE'];
}

/** O que uma tela guarda depois de tentar registrar: os erros, ou a cor de antes para comparar com a de agora. */
export type Retorno =
  | { ok: false; erros: string[] }
  | {
      ok: true;
      municipio: number;
      /** Frase do que foi registrado ("Relatório de 12/2026 registrado para Sobral-CE."). */
      titulo: string;
      antes: ResultadoCor;
      /** Veio do momento reservado: na versão real, a Gestão Operacional não recebe. */
      reservado?: boolean;
    };
