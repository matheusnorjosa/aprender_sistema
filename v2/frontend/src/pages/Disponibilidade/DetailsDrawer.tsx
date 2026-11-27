/**
 * Gaveta de detalhes da Grade Mensal.
 *
 * Dois modos (grade enxuta, 27/11/2026):
 * - dia (clique num código): um cartão por item do `details_index` da célula: evento,
 *   deslocamento ou bloqueio. Do bloqueio, só o tipo e o período: o motivo pode ser pessoal, e o
 *   servidor nem o manda. Item sem `tipo_item` (formato antigo) é evento.
 * - pessoa (clique no nome): CH do mês e do ano, posição no mês e as listas de eventos e de
 *   deslocamentos do mês, juntadas de todas as células da linha, sem repetir o mesmo id.
 *
 * Sem rolagem horizontal (C4): cada item é um cartão (lista), não uma tabela, e texto longo
 * quebra linha. O painel rola na vertical, e por isso qualquer excesso na horizontal viraria
 * rolagem interna.
 *
 * É um diálogo modal: ao abrir, o foco vai para "Fechar"; Tab e Shift+Tab não saem do painel; Esc
 * fecha; ao fechar, o foco volta para o botão que a abriu. O fundo escuro fecha no clique do mouse,
 * mas fica fora da tabulação: no teclado, Esc e "Fechar" já fecham.
 */

import { useEffect, useRef } from 'react';
import type { JSX } from 'react';
import dayjs from 'dayjs';
import type { ID } from '../../types';
import { formatarHoras } from './horas';

/** Person record from the monthly grid */
export interface PersonType {
  id: ID;
  name: string;
  email?: string | null;
  ch_month?: number;
  ch_year?: number;
  position_month?: number | string;
}

/** Evento do dia (sem `tipo_item` no formato antigo). */
export interface EventDetailType {
  tipo_item?: 'evento';
  id?: ID;
  municipio?: string;
  tipo?: string;
  data?: string;
  inicio?: string;
  fim?: string;
}

/** Deslocamento: `inicio`/`fim` são datas AAAA-MM-DD. */
export interface DeslocamentoDetailType {
  tipo_item: 'deslocamento';
  id?: ID;
  origem?: string;
  destino?: string;
  inicio?: string;
  fim?: string;
  meio_transporte?: string;
}

/**
 * Bloqueio: `tipo` é "Total" ou "Parcial"; `data_inicio`/`data_fim` são AAAA-MM-DD e
 * `inicio`/`fim` são HH:MM, tudo no fuso de Fortaleza. Sem motivo.
 */
export interface BloqueioDetailType {
  tipo_item: 'bloqueio';
  id?: ID;
  tipo?: string;
  data_inicio?: string;
  data_fim?: string;
  inicio?: string;
  fim?: string;
}

export type DetailItemType = EventDetailType | DeslocamentoDetailType | BloqueioDetailType;

interface DetailsDrawerProps {
  open: boolean;
  onClose: () => void;
  person: PersonType | null;
  day: number | null;
  details: DetailItemType[];
  /** `dia`: os itens da célula; `pessoa`: os itens de todas as células da linha. */
  modo?: 'dia' | 'pessoa';
  /** O filtro Projeto da grade: a lista segue o filtro, a CH não (é de todos os projetos). */
  filtroProjeto?: string;
}

/** O que o Tab alcança dentro do painel. */
const FOCAVEIS = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** O servidor já manda o dia de Fortaleza (AAAA-MM-DD): só troca o formato. */
const dataBR = (data?: string): string => (data ? dayjs(data).format('DD/MM/YYYY') : '');

const periodo = (inicio?: string, fim?: string): string =>
  fim && fim !== inicio ? `${dataBR(inicio)} a ${dataBR(fim)}` : dataBR(inicio);

const trajeto = (d: DeslocamentoDetailType): string => `${d.origem ?? ''} → ${d.destino ?? ''}`;

/** O mesmo evento ou deslocamento aparece em várias células do mês: uma vez só. */
function semRepetir<T extends { id?: ID }>(itens: T[]): T[] {
  const vistos = new Set<ID>();
  return itens.filter((d) => {
    if (d.id === undefined) return true;
    if (vistos.has(d.id)) return false;
    vistos.add(d.id);
    return true;
  });
}

function Campo({ rotulo, valor }: { rotulo: string; valor: string }): JSX.Element {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-gray-600">{rotulo}</dt>
      <dd className="text-gray-900 break-words">{valor}</dd>
    </div>
  );
}

function CartaoEvento({ d }: { d: EventDetailType }): JSX.Element {
  return (
    <>
      <p className="font-medium text-gray-900 break-words">{d.municipio ?? ''}</p>
      <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-sm">
        <Campo rotulo="Tipo" valor={d.tipo ?? ''} />
        <Campo rotulo="Data" valor={dataBR(d.data)} />
        <Campo rotulo="Início" valor={d.inicio ?? ''} />
        <Campo rotulo="Fim" valor={d.fim ?? ''} />
      </dl>
    </>
  );
}

function CartaoDeslocamento({ d }: { d: DeslocamentoDetailType }): JSX.Element {
  return (
    <>
      <p className="font-medium text-gray-900 break-words">{trajeto(d)}</p>
      <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-sm">
        <Campo rotulo="Data" valor={periodo(d.inicio, d.fim)} />
        {d.meio_transporte && <Campo rotulo="Meio de transporte" valor={d.meio_transporte} />}
      </dl>
    </>
  );
}

/** Bloqueio de vários dias: no dia do meio, só o horário enganaria; por isso data e hora. */
function CartaoBloqueio({ d }: { d: BloqueioDetailType }): JSX.Element {
  const variosDias = Boolean(d.data_inicio && d.data_fim && d.data_inicio !== d.data_fim);
  return (
    <>
      <p className="font-medium text-gray-900">Bloqueio {(d.tipo ?? '').toLowerCase()}</p>
      <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-sm">
        {variosDias ? (
          <div className="col-span-2 min-w-0">
            <dt className="text-xs text-gray-600">Período</dt>
            <dd className="text-gray-900 break-words">
              {`${dataBR(d.data_inicio)} ${d.inicio ?? ''} a ${dataBR(d.data_fim)} ${d.fim ?? ''}`}
            </dd>
          </div>
        ) : (
          <>
            <Campo rotulo="Início" valor={d.inicio ?? ''} />
            <Campo rotulo="Fim" valor={d.fim ?? ''} />
          </>
        )}
      </dl>
    </>
  );
}

function Cartao({ d }: { d: DetailItemType }): JSX.Element {
  if (d.tipo_item === 'deslocamento') return <CartaoDeslocamento d={d} />;
  if (d.tipo_item === 'bloqueio') return <CartaoBloqueio d={d} />;
  return <CartaoEvento d={d} />;
}

const ehEvento = (d: DetailItemType): d is EventDetailType => d.tipo_item === undefined || d.tipo_item === 'evento';
const ehDeslocamento = (d: DetailItemType): d is DeslocamentoDetailType => d.tipo_item === 'deslocamento';

function MesDaPessoa({ details }: { details: DetailItemType[] }): JSX.Element {
  const eventos = semRepetir(details.filter(ehEvento));
  const deslocamentos = semRepetir(details.filter(ehDeslocamento));

  if (eventos.length === 0 && deslocamentos.length === 0) {
    return <p className="px-3 py-4 text-sm text-gray-500 text-center">Nada neste mês.</p>;
  }
  return (
    <>
      {eventos.length > 0 && (
        <section aria-labelledby="mes-eventos" className="px-3 py-2 sm:p-4">
          <h3 id="mes-eventos" className="text-sm font-semibold text-gray-900 mb-1">Eventos do mês</h3>
          {/* Uma linha por evento, como a lista da planilha: data e horário, depois município e tipo. */}
          <ul className="divide-y text-sm">
            {eventos.map((d, idx) => (
              <li key={d.id ?? idx} className="py-1.5">
                <p className="text-gray-900">
                  <span className="font-medium">{dataBR(d.data).slice(0, 5)}</span> · {d.inicio ?? ''}–{d.fim ?? ''}
                </p>
                <p className="text-gray-700 break-words">
                  {d.municipio ?? ''}
                  {d.tipo ? ` · ${d.tipo}` : ''}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}
      {deslocamentos.length > 0 && (
        <section aria-labelledby="mes-deslocamentos" className="px-3 py-2 sm:p-4">
          <h3 id="mes-deslocamentos" className="text-sm font-semibold text-gray-900 mb-1">Deslocamentos do mês</h3>
          <ul className="divide-y text-sm">
            {deslocamentos.map((d, idx) => (
              <li key={d.id ?? idx} className="py-1.5">
                <p className="text-gray-900">
                  <span className="font-medium">{periodo(d.inicio, d.fim)}</span>
                </p>
                <p className="text-gray-700 break-words">{trajeto(d)}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

export default function DetailsDrawer({ open, onClose, person, day, details, modo = 'dia', filtroProjeto }: DetailsDrawerProps): JSX.Element | null {
  const aberta = open && person !== null;
  const painelRef = useRef<HTMLDivElement>(null);
  const fecharRef = useRef<HTMLButtonElement>(null);
  // A última versão de onClose, para o Esc não depender de o pai memoizar a função.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!aberta) return undefined;
    const origem = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    fecharRef.current?.focus();
    const aoTeclar = (e: KeyboardEvent): void => {
      // Outro diálogo aberto por cima (Dar feedback, aviso de sessão): o teclado é dele, não da gaveta.
      const ativo = document.activeElement;
      if (
        ativo instanceof Element &&
        !painelRef.current?.contains(ativo) &&
        ativo.closest('[role="dialog"], [role="alertdialog"]')
      ) {
        return;
      }
      if (e.key === 'Escape') {
        onCloseRef.current();
        return;
      }
      const painel = painelRef.current;
      if (e.key !== 'Tab' || !painel) return;
      // Foco preso: do último focável vai ao primeiro, e com Shift ao contrário. Com um só, fica nele.
      const focaveis = painel.querySelectorAll<HTMLElement>(FOCAVEIS);
      const primeiro = focaveis[0];
      const ultimo = focaveis[focaveis.length - 1];
      if (!primeiro || !ultimo) return;
      const atual = document.activeElement;
      const fora = !painel.contains(atual);
      if (e.shiftKey && (atual === primeiro || fora)) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && (atual === ultimo || fora)) {
        e.preventDefault();
        primeiro.focus();
      }
    };
    document.addEventListener('keydown', aoTeclar);
    return () => {
      document.removeEventListener('keydown', aoTeclar);
      origem?.focus();
    };
  }, [aberta]);

  if (!aberta) return null;

  return (
    <>
      {/* Overlay: só o mouse; no teclado, Esc e "Fechar" (fora da tabulação para o foco não escapar). */}
      <div className="fixed inset-0 bg-black/30 z-[999]" onClick={onClose}></div>

      {/* Drawer: acima do botão "Dar feedback" (998) e abaixo dos modais do AntD (1000). */}
      <div
        ref={painelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="detalhes-titulo"
        className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-white shadow-2xl z-[999] overflow-y-auto"
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-3 py-2 sm:p-4 flex items-center justify-between gap-3">
          <h2 id="detalhes-titulo" className="min-w-0 break-words text-base sm:text-xl font-bold text-gray-900">
            {modo === 'pessoa' ? `Mês de ${person.name}` : `Detalhes: ${person.name} - Dia ${day}`}
          </h2>
          <button
            ref={fecharRef}
            type="button"
            onClick={onClose}
            className="shrink-0 px-3 py-1 text-sm text-gray-600 hover:text-gray-900 border rounded"
          >
            Fechar
          </button>
        </div>

        {/* Métricas */}
        <div className="px-3 py-2 sm:p-4 border-b bg-gray-50">
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center">
              <div className="text-lg sm:text-2xl font-bold text-blue-600">
                {formatarHoras(person.ch_month ?? 0)}
              </div>
              <div className="text-xs text-gray-600">CH Mês</div>
            </div>
            <div className="text-center">
              <div className="text-lg sm:text-2xl font-bold text-green-600">
                {formatarHoras(person.ch_year ?? 0)}
              </div>
              <div className="text-xs text-gray-600">CH Ano</div>
            </div>
            <div className="text-center">
              <div className="text-lg sm:text-2xl font-bold text-purple-600">
                {person.position_month ?? '-'}
              </div>
              <div className="text-xs text-gray-600">Posição no mês</div>
            </div>
          </div>
        </div>

        {/* Informações da pessoa */}
        <div className="px-3 py-2 sm:p-4 border-b">
          <div className="space-y-1 text-sm">
            <div>
              <span className="font-medium text-gray-700">Nome: </span>
              <span className="text-gray-900 break-words">{person.name}</span>
            </div>
            {person.email && (
              <div>
                <span className="font-medium text-gray-700">Email: </span>
                <span className="text-gray-900 [overflow-wrap:anywhere]">{person.email}</span>
              </div>
            )}
          </div>
        </div>

        {modo === 'pessoa' && filtroProjeto?.trim() && (
          <p className="px-3 pt-2 sm:px-4 sm:pt-4 text-sm text-gray-700">
            Horas de todos os projetos; a lista mostra só o projeto filtrado.
          </p>
        )}

        {modo === 'pessoa' ? (
          <MesDaPessoa details={details} />
        ) : (
          <div className="px-3 py-2 sm:p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Agenda do dia {day}
            </h3>

            {details.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">Nada neste dia.</p>
            ) : (
              <ul className="space-y-2">
                {details.map((d, idx) => (
                  <li key={`${d.tipo_item ?? 'evento'}-${d.id ?? idx}`} className="border rounded p-2 sm:p-3">
                    <Cartao d={d} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </>
  );
}
