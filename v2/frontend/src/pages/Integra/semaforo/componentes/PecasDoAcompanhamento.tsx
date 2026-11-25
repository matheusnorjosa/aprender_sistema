/**
 * Peças das telas de acompanhamento do Semáforo (Comitê, Ficha do município, Painel da gestora): a cor
 * com o nome escrito e um rótulo ("Sugerida: Vermelho"), a etiqueta do prazo da tarefa e a seta de mudança.
 * O aviso de quem vê a tela vem de `PecasDoRegistro`.
 *
 * Cores: `COR_SEMAFORO` (os pares fundo/texto das faixas do ICA, texto acima de 4,5:1, conferido em
 * `ica/__tests__/componentes.test.tsx`); a borda na cor do texto marca a etiqueta no fundo branco.
 */
import type { JSX } from 'react';

import { formatarDia } from '../../ica/componentes/estilos';
import { estadoDaTarefa, mudancaEntreCiclos, ROTULO_COR } from '../regras';
import type { Cor, CorIndicador, EstadoTarefa, TarefaResposta } from '../tipos';
import { COR_SEMAFORO as COR_ETIQUETA } from './corEAlerta';

const CLASSE_ETIQUETA = 'inline-block rounded border px-1.5 text-sm font-semibold whitespace-nowrap';

/** A cor com o nome escrito ("Vermelho"); com `rotulo`, "Sugerida: Vermelho". */
export function CorComNome({ cor, rotulo }: { cor: CorIndicador; rotulo?: string }): JSX.Element {
  const { fundo, texto } = COR_ETIQUETA[cor];
  return (
    <span className={CLASSE_ETIQUETA} style={{ background: fundo, color: texto, borderColor: texto }}>
      {rotulo ? `${rotulo}: ` : ''}
      {ROTULO_COR[cor]}
    </span>
  );
}

const COR_DO_ESTADO: Record<EstadoTarefa, CorIndicador> = {
  vence_hoje: 'amarelo',
  vencida: 'vermelho',
  no_prazo: 'sem_dado',
  concluida: 'verde',
};

const ROTULO_ESTADO: Record<Exclude<EstadoTarefa, 'concluida'>, string> = {
  no_prazo: 'No prazo',
  vence_hoje: 'Vence hoje',
  vencida: 'Vencida',
};

/** "No prazo", "Vence hoje", "Vencida" ou "Concluída em 03/12/2026". */
export function EtiquetaPrazo({ tarefa, hoje }: { tarefa: TarefaResposta; hoje: string }): JSX.Element {
  const estado = estadoDaTarefa(tarefa, hoje);
  const { fundo, texto } = COR_ETIQUETA[COR_DO_ESTADO[estado]];
  return (
    // "Concluída em 03/12/2026" não cabe numa linha na coluna de 96 px a 360 px: aqui a etiqueta quebra a linha.
    <span className={`${CLASSE_ETIQUETA} !whitespace-normal`} style={{ background: fundo, color: texto, borderColor: texto }}>
      {estado === 'concluida' ? `Concluída em ${formatarDia(tarefa.concluida_em ?? '')}` : ROTULO_ESTADO[estado]}
    </span>
  );
}

/** "▲ Piorou: era amarelo", "▼ Melhorou: era vermelho", "Sem mudança" (a seta não é lida: o texto diz). */
export function Mudanca({ anterior, atual }: { anterior: Cor | null; atual: Cor }): JSX.Element {
  const { seta, texto } = mudancaEntreCiclos(anterior, atual);
  return (
    <span>
      {seta && <span aria-hidden="true">{seta} </span>}
      {texto}
    </span>
  );
}
