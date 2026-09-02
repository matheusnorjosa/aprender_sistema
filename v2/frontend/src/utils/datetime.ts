import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

// Plugins necessários para converter instantes UTC em um fuso IANA fixo.
// (mesmo par usado em DateTimeRange / NewSolicitacaoWizard)
dayjs.extend(utc);
dayjs.extend(timezone);

/**
 * Fuso de exibição do sistema.
 *
 * RD-06 / CP-03: eventos são armazenados em UTC e exibidos em America/Fortaleza.
 */
export const FORTALEZA_TZ = 'America/Fortaleza';

/**
 * Formata um instante (string ISO/UTC vinda do backend, `Date`, epoch ou `Dayjs`)
 * no fuso `America/Fortaleza`.
 *
 * Independe do fuso do navegador — essa é justamente a garantia do RD-06: dois
 * usuários em fusos diferentes veem o MESMO horário (o de Fortaleza).
 *
 * @param value  instante a formatar; `null`/`undefined`/`''` retornam `''`.
 * @param format máscara dayjs (padrão `DD/MM/YYYY HH:mm`).
 */
export function formatFortaleza(value: dayjs.ConfigType, format = 'DD/MM/YYYY HH:mm'): string {
  if (value === null || value === undefined || value === '') return '';
  const d = dayjs(value);
  return d.isValid() ? d.tz(FORTALEZA_TZ).format(format) : '';
}

/**
 * Inverso de `formatFortaleza` no lado da ESCRITA (RD-06). Um DatePicker devolve um `Dayjs`
 * cujo wall-clock (dia+hora que o usuário viu/digitou) está ancorado no fuso do NAVEGADOR.
 * Este util reinterpreta esse mesmo wall-clock COMO America/Fortaleza e serializa em UTC ISO —
 * assim "08:00" digitado é sempre 08:00 em Fortaleza, não no fuso local de quem preencheu.
 *
 * @returns ISO UTC (ex.: `2026-05-10T11:00:00.000Z`); `''` para valor inválido/nulo.
 */
export function fortalezaWallClockToISO(value: dayjs.ConfigType): string {
  if (value === null || value === undefined || value === '') return '';
  const d = dayjs(value);
  if (!d.isValid()) return '';
  // Extrai o wall-clock como o usuário o viu e o reancora em Fortaleza (não no fuso do navegador).
  return dayjs.tz(d.format('YYYY-MM-DDTHH:mm:ss'), FORTALEZA_TZ).toISOString();
}
