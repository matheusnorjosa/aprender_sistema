/**
 * Cores e alertas das telas do Semáforo (Pesquisa, Indicadores da Líder, Relatório mensal).
 *
 * As cores são as do ICA (`ica/componentes/estilos.ts`), com o contraste já conferido lá: texto 4,5:1
 * sobre o fundo e barra 3:1. Toda cor vai para a tela com o nome escrito ao lado.
 */
import { COR_ESTRATO, type CorEstrato } from '../../ica/componentes/estilos';
import type { MunicipioSemaforo, SituacaoMunicipio } from '../dados';
import type { Cor, CorIndicador, DecisaoComite, ResultadoCor, TarefaResposta } from '../tipos';

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

/**
 * De onde nasceu a tarefa: o vermelho na hora (decisão 38, o Comitê ainda confirma ou desfaz) ou a cor que o Comitê
 * publicou. A tarefa nasce no dia da decisão, com a cor dela (`tarefasDepoisDaPublicacao`).
 */
export function nasceuNaHora(tarefa: TarefaResposta, decisoes: readonly DecisaoComite[]): boolean {
  return decisoes.some(
    (d) =>
      d.municipio === tarefa.municipio &&
      d.publicada_em === tarefa.criada_em &&
      d.cor_publicada === tarefa.cor &&
      d.origem === 'vermelho_automatico',
  );
}

/** A cor sugerida do ciclo atual (o último ciclo da situação). */
export function sugeridaAgora(situacoes: readonly SituacaoMunicipio[], municipio: number): ResultadoCor | null {
  return situacoes.find((s) => s.municipio === municipio)?.ciclos.at(-1)?.resultado ?? null;
}

/**
 * Decisão 46: cada projeto do município tem o seu coordenador. Os coordenadores de todos os projetos, sem repetir,
 * na ordem dos projetos (o projeto sem coordenador fica de fora).
 */
export function coordenadoresDoMunicipio<C extends { id: number }>(m: MunicipioSemaforo | undefined, coordenadores: readonly C[]): C[] {
  const ids = [...new Set((m?.projetos ?? []).flatMap((p) => (p.coordenador === null ? [] : [p.coordenador])))];
  return ids.flatMap((id) => coordenadores.filter((c) => c.id === id));
}

/**
 * Quem age na cor (seção 5 do PDF): a gestora de referência e, no vermelho, a gestora pedagógica; no amarelo, os
 * coordenadores (de todos os projetos do município: a cor e as tarefas são do município; ver a Para validar).
 */
function quemAge(cor: Cor, gestora: string, coordenadores: readonly string[]): string[] {
  const ref = `${gestora} (gestora de referência)`;
  if (cor === 'vermelho') return [ref, 'Gestora pedagógica'];
  return [ref, ...coordenadores.map((c) => `${c} (coordenador)`)];
}

/**
 * Para quem iria o alerta de piora. Seção 8 do PDF: "Município passa a vermelho" vai, na hora, para a gestora de
 * referência, a gestora pedagógica, a SPE e a Líder do NFP. A tabela não tem linha para "passa a amarelo": o
 * protótipo avisa quem age no amarelo e a SPE. No protótipo nada é enviado.
 */
export function destinatariosDaPiora(cor: Cor, gestora: string, coordenadores: readonly string[]): string[] {
  return [...quemAge(cor, gestora, coordenadores), 'SPE', ...(cor === 'vermelho' ? ['Líder do NFP'] : [])];
}

/**
 * Para quem iria o alerta de prazo da tarefa. Seção 8 do PDF: "Prazo de resposta a cor vencendo ou vencido" vai
 * para o responsável pela tarefa (quem age na cor da tarefa) e a SPE, um dia antes e no vencimento.
 */
export function destinatariosDoPrazo(cor: Cor, gestora: string, coordenadores: readonly string[]): string[] {
  return [...quemAge(cor, gestora, coordenadores), 'SPE'];
}

/** O que uma tela guarda depois de tentar registrar: os erros, ou a cor de antes para comparar com a de agora. */
export type Retorno =
  | { ok: false; erros: string[] }
  | {
      ok: true;
      municipio: number;
      /** Frase do que foi registrado ("Relatório de 12/2026 registrado para Sobral-CE."). */
      titulo: string;
      /** A cor sugerida antes do registro; sem ela (registro que não mexe na cor), a tela mostra só o título. */
      antes?: ResultadoCor;
      /** Veio do momento reservado: o alerta leva só a cor, sem o conteúdo da queixa. */
      reservado?: boolean;
      /** Antes do registro, a cor em vigor já era um vermelho na hora esperando o Comitê (não foi este registro que a mudou). */
      aguardandoAntes?: boolean;
    };
