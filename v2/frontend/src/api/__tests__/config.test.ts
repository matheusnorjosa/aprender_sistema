/**
 * Tests: API Config Functions
 *
 * Cobertura:
 * - getCsrfToken: extração de cookie
 * - clearCsrfCache: limpeza de cache
 * - buildUrl: construção de URL com query params
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { getCsrfToken, clearCsrfCache, buildUrl } from '../config'

// Helper para limpar cookies
function clearAllCookies() {
  document.cookie.split(';').forEach((cookie) => {
    const name = cookie.split('=')[0].trim()
    if (name) {
      document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
    }
  })
}

describe('API Config', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Limpar cookies entre testes
    clearAllCookies()
  })

  // ============================================================================
  // TESTES DE getCsrfToken
  // ============================================================================

  describe('getCsrfToken', () => {
    test('deve retornar null quando não há cookies', () => {
      document.cookie = ''
      expect(getCsrfToken()).toBeNull()
    })

    test('deve extrair csrftoken do cookie', () => {
      document.cookie = 'csrftoken=abc123xyz'
      expect(getCsrfToken()).toBe('abc123xyz')
    })

    test('deve encontrar csrftoken entre múltiplos cookies', () => {
      // Em jsdom, cookies devem ser setados individualmente
      document.cookie = 'sessionid=xyz123'
      document.cookie = 'csrftoken=token456'
      document.cookie = 'other=value'
      expect(getCsrfToken()).toBe('token456')
    })

    test('deve decodificar valor do cookie', () => {
      document.cookie = 'csrftoken=hello%20world'
      expect(getCsrfToken()).toBe('hello world')
    })
  })

  // ============================================================================
  // TESTES DE clearCsrfCache
  // ============================================================================

  describe('clearCsrfCache', () => {
    test('deve executar sem erro', () => {
      expect(() => clearCsrfCache()).not.toThrow()
    })

    test('deve poder ser chamado múltiplas vezes', () => {
      clearCsrfCache()
      clearCsrfCache()
      clearCsrfCache()
      expect(true).toBe(true) // Não deve lançar erro
    })
  })

  // ============================================================================
  // TESTES DE buildUrl
  // ============================================================================

  describe('buildUrl', () => {
    test('deve retornar path sem params quando objeto vazio', () => {
      expect(buildUrl('/solicitacoes/')).toBe('/solicitacoes/')
      expect(buildUrl('/solicitacoes/', {})).toBe('/solicitacoes/')
    })

    test('deve adicionar query params ao path', () => {
      const result = buildUrl('/solicitacoes/', { status: 'pendente' })
      expect(result).toBe('/solicitacoes/?status=pendente')
    })

    test('deve adicionar múltiplos query params', () => {
      const result = buildUrl('/solicitacoes/', { status: 'pendente', q: 'sobral' })
      expect(result).toContain('status=pendente')
      expect(result).toContain('q=sobral')
      expect(result).toMatch(/^\/solicitacoes\/\?/)
    })

    test('deve ignorar valores null/undefined/vazios', () => {
      const result = buildUrl('/test/', {
        valid: 'value',
        empty: '',
        nullVal: null,
        undefinedVal: undefined,
      })
      expect(result).toBe('/test/?valid=value')
    })

    test('deve usar & se path já contém ?', () => {
      const result = buildUrl('/test/?existing=1', { new: '2' })
      expect(result).toBe('/test/?existing=1&new=2')
    })

    test('deve encodar caracteres especiais', () => {
      const result = buildUrl('/search/', { q: 'hello world' })
      expect(result).toBe('/search/?q=hello+world')
    })

    test('deve lidar com valores numéricos', () => {
      const result = buildUrl('/items/', { page: 1, limit: 10 })
      expect(result).toContain('page=1')
      expect(result).toContain('limit=10')
    })
  })
})
