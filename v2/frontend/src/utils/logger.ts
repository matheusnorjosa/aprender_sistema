/**
 * Logger condicional - só loga em development
 *
 * Issue #220: Evitar exposição de dados sensíveis em console de produção
 *
 * Uso:
 *   import logger from '@/utils/logger';
 *   logger.log('mensagem');
 *   logger.debug('debug info', { data });
 *   logger.warn('aviso');
 *   logger.error('erro', error);
 */

const isDev: boolean = import.meta.env.DEV;

export interface Logger {
  log: (...args: unknown[]) => void;
  debug: (...args: unknown[]) => void;
  warn: (...args: unknown[]) => void;
  error: (...args: unknown[]) => void;
  api: (label: string, data: unknown) => void;
}

const logger: Logger = {
  /**
   * Log geral (equivalente a console.log)
   */
  log: (...args: unknown[]): void => {
    if (isDev) console.log(...args);
  },

  /**
   * Log de debug com prefixo [DEBUG]
   */
  debug: (...args: unknown[]): void => {
    if (isDev) console.log('[DEBUG]', ...args);
  },

  /**
   * Warning (sempre loga, mas sem dados sensíveis em prod)
   */
  warn: (...args: unknown[]): void => {
    if (isDev) console.warn(...args);
  },

  /**
   * Error (sempre loga em dev, mensagem genérica em prod)
   */
  error: (...args: unknown[]): void => {
    if (isDev) {
      console.error(...args);
    }
    // Em produção, erros críticos podem ser enviados para Sentry
    // mas não logamos no console para evitar exposição
  },

  /**
   * Log de API request/response (útil para debugging)
   */
  api: (label: string, data: unknown): void => {
    if (isDev) {
      console.log(`[API] ${label}:`, data);
    }
  },
};

export default logger;
