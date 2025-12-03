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

const isDev = import.meta.env.DEV;

const logger = {
  /**
   * Log geral (equivalente a console.log)
   */
  log: (...args) => {
    if (isDev) console.log(...args);
  },

  /**
   * Log de debug com prefixo [DEBUG]
   */
  debug: (...args) => {
    if (isDev) console.log('[DEBUG]', ...args);
  },

  /**
   * Warning (sempre loga, mas sem dados sensíveis em prod)
   */
  warn: (...args) => {
    if (isDev) console.warn(...args);
  },

  /**
   * Error (sempre loga em dev, mensagem genérica em prod)
   */
  error: (...args) => {
    if (isDev) {
      console.error(...args);
    }
    // Em produção, erros críticos podem ser enviados para Sentry
    // mas não logamos no console para evitar exposição
  },

  /**
   * Log de API request/response (útil para debugging)
   */
  api: (label, data) => {
    if (isDev) {
      console.log(`[API] ${label}:`, data);
    }
  },
};

export default logger;
