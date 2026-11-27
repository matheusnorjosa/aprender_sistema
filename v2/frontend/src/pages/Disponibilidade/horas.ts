const HORAS = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 });

/** Horas no formato brasileiro: 4.5 → "4,5h". */
export const formatarHoras = (horas: number): string => `${HORAS.format(horas)}h`;
