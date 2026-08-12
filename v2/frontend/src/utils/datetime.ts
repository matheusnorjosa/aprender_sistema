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
