/**
 * Tests: Logger Utility (Issue #220)
 *
 * Cobertura:
 * - Logs em development (DEV=true)
 * - Silenciado em production (DEV=false)
 * - Métodos: log, debug, warn, error, api
 */

import { describe, test, expect, vi, beforeEach, afterEach, type MockInstance } from 'vitest'

type ConsoleSpy = MockInstance<(...args: unknown[]) => void>;

describe('logger', () => {
  let consoleSpy: {
    log: ConsoleSpy;
    warn: ConsoleSpy;
    error: ConsoleSpy;
  };

  beforeEach(() => {
    // Spy nos métodos do console
    consoleSpy = {
      log: vi.spyOn(console, 'log').mockImplementation(() => {}) as ConsoleSpy,
      warn: vi.spyOn(console, 'warn').mockImplementation(() => {}) as ConsoleSpy,
      error: vi.spyOn(console, 'error').mockImplementation(() => {}) as ConsoleSpy,
    }
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.resetModules()
  })

  describe('em development (DEV=true)', () => {
    beforeEach(() => {
      vi.stubEnv('DEV', true)
    })

    test('log() deve chamar console.log', async () => {
      // Re-import para pegar nova env
      const { default: logger } = await import('../logger')

      logger.log('test message')

      expect(consoleSpy.log).toHaveBeenCalledWith('test message')
    })

    test('debug() deve chamar console.log com prefixo [DEBUG]', async () => {
      const { default: logger } = await import('../logger')

      logger.debug('debug info', { data: 123 })

      expect(consoleSpy.log).toHaveBeenCalledWith('[DEBUG]', 'debug info', { data: 123 })
    })

    test('warn() deve chamar console.warn', async () => {
      const { default: logger } = await import('../logger')

      logger.warn('warning message')

      expect(consoleSpy.warn).toHaveBeenCalledWith('warning message')
    })

    test('error() deve chamar console.error', async () => {
      const { default: logger } = await import('../logger')
      const testError = new Error('test error')

      logger.error('error message', testError)

      expect(consoleSpy.error).toHaveBeenCalledWith('error message', testError)
    })

    test('api() deve chamar console.log com prefixo [API]', async () => {
      const { default: logger } = await import('../logger')

      logger.api('GET /users', { status: 200 })

      expect(consoleSpy.log).toHaveBeenCalledWith('[API] GET /users:', { status: 200 })
    })
  })

  describe('em production (DEV=false)', () => {
    beforeEach(() => {
      vi.stubEnv('DEV', false)
    })

    test('log() NÃO deve chamar console.log', async () => {
      vi.resetModules()
      const { default: logger } = await import('../logger')

      logger.log('test message')

      expect(consoleSpy.log).not.toHaveBeenCalled()
    })

    test('debug() NÃO deve chamar console.log', async () => {
      vi.resetModules()
      const { default: logger } = await import('../logger')

      logger.debug('debug info')

      expect(consoleSpy.log).not.toHaveBeenCalled()
    })

    test('warn() NÃO deve chamar console.warn', async () => {
      vi.resetModules()
      const { default: logger } = await import('../logger')

      logger.warn('warning')

      expect(consoleSpy.warn).not.toHaveBeenCalled()
    })

    test('error() NÃO deve chamar console.error (evita exposição)', async () => {
      vi.resetModules()
      const { default: logger } = await import('../logger')

      logger.error('error')

      expect(consoleSpy.error).not.toHaveBeenCalled()
    })

    test('api() NÃO deve chamar console.log', async () => {
      vi.resetModules()
      const { default: logger } = await import('../logger')

      logger.api('GET /users', {})

      expect(consoleSpy.log).not.toHaveBeenCalled()
    })
  })
})
