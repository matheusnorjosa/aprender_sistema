/**
 * A conta do ICA de um coordenador, componente a componente, como o exemplo do PDF:
 * valor, média da equipe, índice, peso e contribuição; no fim, o ICA exato e o exibido.
 *
 * Usa o `ResponsiveTable` (sem rolagem horizontal): no estreito, média, índice e peso vão para a
 * linha expandida.
 */
import type { JSX } from 'react';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../../components/ResponsiveTable';
import type { Componente, Pesos, Valores } from '../../dados/tipos';
import { COMPONENTES, formatarHoras, icaExatoComUmaCasa, ROTULO_COMPONENTE, type ContaIca } from '../calculo';
import { textoDoEstrato } from './EtiquetaEstrato';
import { COR_COMPONENTE, COR_ESTRATO, formatarNumero } from './estilos';

interface TabelaComponentesProps {
  valores: Valores;
  medias: Valores;
  pesos: Pesos;
  conta: ContaIca;
  /** Título acessível da tabela. */
  titulo?: string;
  /** Sem municípios: ICA 0 fora da média e dos estratos (PDF, seção 3), não "Capacidade disponível". */
  semMunicipios?: boolean;
}

interface Linha {
  componente: Componente;
  valor: number;
  media: number;
  indice: number;
  peso: number;
  contribuicao: number;
}

function formatarValor(componente: Componente, valor: number, casas: number): string {
  return componente === 'deslocamento' ? formatarHoras(valor) : formatarNumero(valor, casas);
}

const COLUNAS: ColunaResponsiva<Linha>[] = [
  {
    title: 'Componente',
    key: 'componente',
    render: (_v, l) => (
      <span className="flex items-center gap-2">
        <span aria-hidden="true" className="inline-block h-3 w-3 shrink-0 rounded-sm" style={{ background: COR_COMPONENTE[l.componente] }} />
        {ROTULO_COMPONENTE[l.componente]}
      </span>
    ),
  },
  { title: 'Valor', key: 'valor', width: 90, render: (_v, l) => formatarValor(l.componente, l.valor, 0) },
  {
    title: 'Média da equipe',
    key: 'media',
    width: 110,
    responsive: VISIVEL_A_PARTIR.md,
    render: (_v, l) => formatarValor(l.componente, l.media, 2),
  },
  { title: 'Índice', key: 'indice', width: 80, responsive: VISIVEL_A_PARTIR.lg, render: (_v, l) => formatarNumero(l.indice, 1) },
  {
    title: 'Peso',
    key: 'peso',
    width: 100,
    responsive: VISIVEL_A_PARTIR.sm,
    render: (_v, l) => (l.peso === 0 ? 'fora da conta' : `${formatarNumero(l.peso)}%`),
  },
  {
    title: 'Contribuição',
    key: 'contribuicao',
    width: 110,
    render: (_v, l) => (l.peso === 0 ? '—' : formatarNumero(l.contribuicao, 1)),
  },
];

export function TabelaComponentes({
  valores,
  medias,
  pesos,
  conta,
  titulo = 'Conta do ICA por componente',
  semMunicipios = false,
}: TabelaComponentesProps): JSX.Element {
  const linhas: Linha[] = COMPONENTES.map((c) => ({
    componente: c,
    valor: valores[c],
    media: medias[c],
    indice: conta.indices[c],
    peso: pesos[c],
    contribuicao: conta.contribuicoes[c],
  }));
  return (
    <div>
      <ResponsiveTable<Linha>
        aria-label={titulo}
        rowKey="componente"
        columns={COLUNAS}
        dataSource={linhas}
        pagination={false}
        nomeDaLinha={(l) => ROTULO_COMPONENTE[l.componente]}
      />
      {semMunicipios ? (
        <p className="mb-0 mt-2 font-semibold">Sem municípios: ICA 0, fora da média da equipe</p>
      ) : (
        <p className="mb-0 mt-2 flex flex-wrap items-center gap-2 font-semibold">
          <span aria-hidden="true" className="inline-block h-3 w-3 rounded-sm" style={{ background: COR_ESTRATO[conta.estrato].forte }} />
          <span>
            ICA: {formatarNumero(icaExatoComUmaCasa(conta.icaExato), 1)} → {textoDoEstrato(conta.estrato, conta.icaExibido)}
          </span>
        </p>
      )}
    </div>
  );
}
