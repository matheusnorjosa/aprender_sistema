/**
 * Cores e formatos das telas do ICA.
 *
 * Toda cor vem acompanhada do nome e do número na tela (nunca só a cor). Contraste conferido em
 * `__tests__/componentes.test.tsx`: texto 4,5:1 no fundo do estrato e a barra 3:1 em qualquer faixa.
 */
import type { Componente } from '../../dados/tipos';
import type { Estrato } from '../calculo';

export interface CorEstrato {
  /** Fundo claro da faixa e da etiqueta. */
  fundo: string;
  /** Texto sobre o fundo (4,5:1). */
  texto: string;
  /** Barra do gráfico (3:1 sobre qualquer faixa). */
  forte: string;
}

/**
 * As cores do documento de requisitos do ICA (seção "Estratos e cores" e o painel ilustrativo; decisão do dono,
 * 26/11/2026). A cor do documento que falha como texto (menos de 4,5:1) fica só como preenchimento, e o texto ganha
 * um tom escuro: Atenção #A86F00 vira a barra e o texto fica #8A5A00. As barras do painel do documento que não dão
 * 3:1 nas faixas (#E5A21C, #2BA84A, #8A958D) dão lugar ao texto do estrato ou ao cinza do número do painel.
 */
export const COR_ESTRATO: Record<Estrato, CorEstrato> = {
  sobrecarga: { fundo: '#FBE6E5', texto: '#C0392B', forte: '#D9473B' },
  atencao: { fundo: '#FDF4E3', texto: '#8A5A00', forte: '#A86F00' },
  adequada: { fundo: '#E8F5EB', texto: '#1E7B3A', forte: '#1E7B3A' },
  capacidade: { fundo: '#F1F2F1', texto: '#444444', forte: '#6B7A70' },
};

/** Traço fino nas divisas 80, 110 e 130 dos gráficos (3:1 sobre o fundo de qualquer faixa). */
export const COR_DIVISA = '#6B6B6B';

/** Cortes entre as faixas, para marcar a divisa nos gráficos. */
export const DIVISAS_DAS_FAIXAS = [80, 110, 130] as const;

/** Uma cor por componente na barra empilhada da ficha (3:1 no branco), sempre com o nome ao lado. */
export const COR_COMPONENTE: Record<Componente, string> = {
  municipios: '#1D5E9E',
  frentes: '#6B3FA0',
  turmas: '#0F7B6C',
  professores: '#A3480B',
  deslocamento: '#8A1C5C',
  estados: '#4B5563',
};

/** Campo de formulário nativo com foco visível na cor da marca. */
export const CLASSE_CAMPO = [
  'w-full rounded border border-[#8c8c8c] bg-white px-2 py-1 text-sm text-[#1f1f1f]',
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark',
].join(' ');

/** Rótulo de campo. */
export const CLASSE_ROTULO = 'mb-1 block text-sm font-semibold text-[#1f1f1f]';

/** Número no formato brasileiro (1.291; 30,8). */
export function formatarNumero(valor: number, casas = 0): string {
  return valor.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

/** Variação com sinal: "+5", "−23" (sinal de menos de verdade), "0". */
export function formatarVariacao(valor: number): string {
  if (valor > 0) return `+${formatarNumero(valor)}`;
  if (valor < 0) return `−${formatarNumero(Math.abs(valor))}`;
  return '0';
}

/** Data AAAA-MM-DD (sem hora) → DD/MM/AAAA, sem passar por fuso. */
export function formatarDia(data: string): string {
  const [ano, mes, dia] = data.slice(0, 10).split('-');
  return `${dia}/${mes}/${ano}`;
}
