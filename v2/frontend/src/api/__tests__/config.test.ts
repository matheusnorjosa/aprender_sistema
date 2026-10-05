/**
 * Tests: API Config Functions
 *
 * Cobertura:
 * - getCsrfToken: extração de cookie
 * - clearCsrfCache: limpeza de cache
 * - buildUrl: construção de URL com query params
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/mocks/server'
import { apiUrl } from '../../test/mocks/handlers'
import {
  fetchAPI,
  fetchBlob,
  getCsrfToken,
  clearCsrfCache,
  buildUrl,
  SERVIDOR_RESPONDEU,
  TROCA_DE_SENHA_OBRIGATORIA,
} from '../config'

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
      // `; Secure` evita CodeQL js/clear-text-cookie; jsdom roda em HTTPS
      // (ver vitest.config.ts) então o jar aceita.
      document.cookie = 'csrftoken=abc123xyz; Secure'
      expect(getCsrfToken()).toBe('abc123xyz')
    })

    test('deve encontrar csrftoken entre múltiplos cookies', () => {
      // Em jsdom, cookies devem ser setados individualmente
      document.cookie = 'sessionid=xyz123; Secure'
      document.cookie = 'csrftoken=token456; Secure'
      document.cookie = 'other=value; Secure'
      expect(getCsrfToken()).toBe('token456')
    })

    test('deve decodificar valor do cookie', () => {
      document.cookie = 'csrftoken=hello%20world; Secure'
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

  // ============================================================================
  // TESTES DE fetchAPI — sessão expirada global (Issue #1376)
  // ============================================================================

  describe('fetchAPI — 401 dispara evento global auth:expired (Issue #1376)', () => {
    function authExpiredFired(spy: ReturnType<typeof vi.spyOn>): boolean {
      return spy.mock.calls.some(
        ([event]) => event instanceof Event && event.type === 'auth:expired',
      )
    }

    test('emite window event "auth:expired" ao receber 401', async () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(
        http.get(apiUrl('/expired/'), () => new HttpResponse(null, { status: 401 })),
      )

      await expect(fetchAPI('/expired/')).rejects.toThrow()

      expect(authExpiredFired(dispatchSpy)).toBe(true)
      dispatchSpy.mockRestore()
    })

    test('NÃO emite "auth:expired" em 403 (permissão, não sessão)', async () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(
        http.get(apiUrl('/forbidden/'), () => new HttpResponse(null, { status: 403 })),
      )

      await expect(fetchAPI('/forbidden/')).rejects.toThrow()

      expect(authExpiredFired(dispatchSpy)).toBe(false)
      dispatchSpy.mockRestore()
    })

    // Auditoria UX 30/09, rodada 2: SessionAuthentication não manda WWW-Authenticate, então
    // o DRF responde 403 (não 401) sem sessão. O `code` NOT_AUTHENTICATED distingue esse 403
    // do de falta de permissão (PERMISSION_DENIED), que não é sessão expirada.
    test('emite "auth:expired" em 403 com code NOT_AUTHENTICATED (DRF sem sessão)', async () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(
        http.get(apiUrl('/sem-sessao/'), () =>
          HttpResponse.json(
            { code: 'NOT_AUTHENTICATED', detail: 'As credenciais de autenticação não foram fornecidas.' },
            { status: 403 },
          ),
        ),
      )

      await expect(fetchAPI('/sem-sessao/')).rejects.toThrow('As credenciais de autenticação não foram fornecidas.')

      expect(authExpiredFired(dispatchSpy)).toBe(true)
      dispatchSpy.mockRestore()
    })

    test('NÃO emite "auth:expired" em 403 com code PERMISSION_DENIED', async () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(
        http.get(apiUrl('/sem-permissao/'), () =>
          HttpResponse.json(
            { code: 'PERMISSION_DENIED', detail: 'Você não tem permissão para executar essa ação.' },
            { status: 403 },
          ),
        ),
      )

      await expect(fetchAPI('/sem-permissao/')).rejects.toThrow()

      expect(authExpiredFired(dispatchSpy)).toBe(false)
      dispatchSpy.mockRestore()
    })

    test('NÃO emite "auth:expired" em resposta 200 de sucesso', async () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(
        http.get(apiUrl('/ok2/'), () => HttpResponse.json({ ok: true })),
      )

      await fetchAPI('/ok2/')

      expect(authExpiredFired(dispatchSpy)).toBe(false)
      dispatchSpy.mockRestore()
    })
  })

  // ============================================================================
  // SERVIDOR_RESPONDEU: o monitor de sessão conta a inatividade da última resposta do servidor
  // (o Django renova a sessão em todo request que atende). Rodada 5: a resposta que diz que não
  // há sessão não renovou nada e não conta; antes, o 403 da pergunta de uma aba recomeçava o
  // relógio das outras, que só iam ao login 2 h depois.
  // ============================================================================

  describe('fetchAPI — SERVIDOR_RESPONDEU', () => {
    function respondeu(spy: { mock: { calls: Array<[Event]> } }): boolean {
      return spy.mock.calls.some(([event]) => event.type === SERVIDOR_RESPONDEU)
    }

    test.each([
      ['200', () => HttpResponse.json({ ok: true })],
      ['400 de validação', () => HttpResponse.json({ campo: ['Obrigatório.'] }, { status: 400 })],
      ['403 PERMISSION_DENIED (a sessão existe)', () => HttpResponse.json({ code: 'PERMISSION_DENIED' }, { status: 403 })],
    ])('resposta %s: avisa', async (_nome, resposta) => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(http.get(apiUrl('/avisa/'), resposta))

      await fetchAPI('/avisa/').catch(() => undefined)

      expect(respondeu(dispatchSpy)).toBe(true)
      dispatchSpy.mockRestore()
    })

    test.each([
      ['401', () => new HttpResponse(null, { status: 401 })],
      ['403 NOT_AUTHENTICATED', () => HttpResponse.json({ code: 'NOT_AUTHENTICATED', detail: 'Sem sessão.' }, { status: 403 })],
    ])('resposta %s (sem sessão): não avisa', async (_nome, resposta) => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(http.get(apiUrl('/sem-sessao/'), resposta))

      await expect(fetchAPI('/sem-sessao/')).rejects.toThrow()

      expect(respondeu(dispatchSpy)).toBe(false)
      dispatchSpy.mockRestore()
    })
  })

  // ============================================================================
  // Falha de rede (auditoria UX 30/09, rodada 3): sem rede, "Continuar logado" dizia
  // "CSRF token ausente. Faça login novamente." e os avisos de carga, "Failed to fetch".
  // ============================================================================

  describe('fetchAPI — sem conexão', () => {
    /** Resposta que o service worker (public/sw.js) devolve no lugar do fetch que falhou. */
    const offlineDoServiceWorker = () =>
      HttpResponse.json(
        { error: { code: 'OFFLINE', message: 'Voce esta offline. Verifique sua conexao.' } },
        { status: 503 },
      )

    beforeEach(() => {
      clearCsrfCache()
    })

    test('POST sem rede ao buscar o token CSRF: "Sem conexão com o servidor.", não erro de CSRF', async () => {
      server.use(http.get(apiUrl('/csrf/'), () => HttpResponse.error()))

      await expect(fetchAPI('/auth/ping/', { method: 'POST' })).rejects.toThrow('Sem conexão com o servidor.')
    })

    test('POST com o /csrf/ respondido pelo service worker offline: "Sem conexão com o servidor."', async () => {
      server.use(http.get(apiUrl('/csrf/'), offlineDoServiceWorker))

      await expect(fetchAPI('/auth/ping/', { method: 'POST' })).rejects.toThrow('Sem conexão com o servidor.')
    })

    test('GET sem rede: TypeError em português (não "Failed to fetch")', async () => {
      server.use(http.get(apiUrl('/config/'), () => HttpResponse.error()))

      const erro: unknown = await fetchAPI('/config/').catch((e: unknown) => e)

      expect(erro).toBeInstanceOf(TypeError)
      expect((erro as Error).message).toBe('Sem conexão com o servidor.')
    })

    test('GET respondido pelo service worker offline: "Sem conexão com o servidor." (não "Erro 503")', async () => {
      server.use(http.get(apiUrl('/config/'), offlineDoServiceWorker))

      await expect(fetchAPI('/config/')).rejects.toThrow('Sem conexão com o servidor.')
    })

    test('503 do servidor (não do service worker) mantém a mensagem do servidor', async () => {
      server.use(
        http.get(apiUrl('/config/'), () => HttpResponse.json({ detail: 'Manutenção.' }, { status: 503 })),
      )

      await expect(fetchAPI('/config/')).rejects.toThrow('Manutenção.')
    })

    // Rodada 4 (BAIXA): o download dos exports (fetchBlob) usava o fetch cru e dizia
    // "Failed to fetch" ou "Export failed: HTTP 503".
    test('fetchBlob, controle: com rede, devolve o arquivo', async () => {
      server.use(http.get(apiUrl('/dat/compras/export/'), () => new HttpResponse('a;b', { status: 200 })))

      const blob = await fetchBlob('/dat/compras/export/')

      expect(blob.size).toBe(3)
    })

    test('fetchBlob sem rede: "Sem conexão com o servidor."', async () => {
      server.use(http.get(apiUrl('/dat/compras/export/'), () => HttpResponse.error()))

      await expect(fetchBlob('/dat/compras/export/')).rejects.toThrow('Sem conexão com o servidor.')
    })

    test('fetchBlob com a resposta OFFLINE do service worker: "Sem conexão com o servidor."', async () => {
      server.use(http.get(apiUrl('/dat/compras/export/'), offlineDoServiceWorker))

      await expect(fetchBlob('/dat/compras/export/')).rejects.toThrow('Sem conexão com o servidor.')
    })

    test('request cancelado (AbortError) passa como veio, sem virar "sem conexão"', async () => {
      server.use(http.get(apiUrl('/config/'), () => HttpResponse.json({ ok: true })))
      const controle = new AbortController()
      controle.abort()

      const erro: unknown = await fetchAPI('/config/', { signal: controle.signal }).catch((e: unknown) => e)

      expect((erro as Error).name).toBe('AbortError')
    })
  })

  // ============================================================================
  // TESTES DE fetchAPI — limite de tentativas (429) e troca de senha obrigatória
  // ============================================================================

  describe('fetchAPI — 429 leva o tempo de espera (Retry-After)', () => {
    const limitado = (retryAfter?: string) =>
      HttpResponse.json(
        { detail: 'Request was throttled.', code: 'THROTTLED' },
        { status: 429, headers: retryAfter === undefined ? {} : { 'Retry-After': retryAfter } },
      )

    beforeEach(() => {
      clearCsrfCache()
    })

    test('429 com Retry-After: o erro carrega status 429 e retryAfter em segundos', async () => {
      server.use(http.post(apiUrl('/auth/login/'), () => limitado('37')))

      await expect(fetchAPI('/auth/login/', { method: 'POST' })).rejects.toMatchObject({
        status: 429,
        retryAfter: 37,
      })
    })

    test('429 sem Retry-After (ou com valor que não é número): retryAfter fica indefinido', async () => {
      server.use(http.post(apiUrl('/auth/login/'), () => limitado()))
      const semCabecalho = await fetchAPI('/auth/login/', { method: 'POST' }).catch((e: unknown) => e)
      expect(semCabecalho).toMatchObject({ status: 429 })
      expect((semCabecalho as { retryAfter?: number }).retryAfter).toBeUndefined()

      server.use(http.post(apiUrl('/auth/login/'), () => limitado('amanhã')))
      const invalido = await fetchAPI('/auth/login/', { method: 'POST' }).catch((e: unknown) => e)
      expect((invalido as { retryAfter?: number }).retryAfter).toBeUndefined()
    })

    // Toda carga de página antes do login busca o CSRF como anônimo; o limite é por rede.
    // Antes, o 429 daqui virava "CSRF token ausente" (erro sem status) e a tela culpava o sistema.
    test('429 no GET /csrf/ (antes de um POST): o erro carrega status 429 e retryAfter', async () => {
      const login = vi.fn(() => HttpResponse.json({}))
      server.use(
        http.get(apiUrl('/csrf/'), () => limitado('1800')),
        http.post(apiUrl('/auth/login/'), login),
      )

      await expect(fetchAPI('/auth/login/', { method: 'POST' })).rejects.toMatchObject({
        status: 429,
        retryAfter: 1800,
      })
      expect(login).not.toHaveBeenCalled()
    })
  })

  describe('fetchAPI — 403 PASSWORD_CHANGE_REQUIRED avisa a troca de senha obrigatória', () => {
    const tipos = (spy: ReturnType<typeof vi.spyOn>): string[] =>
      spy.mock.calls.flatMap(([event]) => (event instanceof Event ? [event.type] : []))

    test('emite "auth:troca-de-senha" e NÃO "auth:expired" (a sessão está viva)', async () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(
        http.get(apiUrl('/solicitacoes/'), () =>
          HttpResponse.json(
            { detail: 'Defina uma senha própria para continuar.', code: 'PASSWORD_CHANGE_REQUIRED' },
            { status: 403 },
          ),
        ),
      )

      await expect(fetchAPI('/solicitacoes/')).rejects.toMatchObject({ status: 403 })

      expect(tipos(dispatchSpy)).toContain(TROCA_DE_SENHA_OBRIGATORIA)
      expect(TROCA_DE_SENHA_OBRIGATORIA).toBe('auth:troca-de-senha')
      expect(tipos(dispatchSpy)).not.toContain('auth:expired')
      dispatchSpy.mockRestore()
    })

    test('403 de falta de permissão NÃO emite "auth:troca-de-senha"', async () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      server.use(
        http.get(apiUrl('/solicitacoes/'), () =>
          HttpResponse.json({ detail: 'Sem permissão.', code: 'PERMISSION_DENIED' }, { status: 403 }),
        ),
      )

      await expect(fetchAPI('/solicitacoes/')).rejects.toThrow()

      expect(tipos(dispatchSpy)).not.toContain(TROCA_DE_SENHA_OBRIGATORIA)
      dispatchSpy.mockRestore()
    })
  })

  // ============================================================================
  // TESTES DE fetchAPI (regression: 204 / empty body handling)
  // ============================================================================

  describe('fetchAPI — empty body responses', () => {
    test('returns undefined for 204 No Content without parsing body', async () => {
      server.use(
        http.get(apiUrl('/noop/'), () => new HttpResponse(null, { status: 204 })),
      )

      const result = await fetchAPI('/noop/')

      expect(result).toBeUndefined()
    })

    test('returns undefined when content-length is 0', async () => {
      server.use(
        http.get(
          apiUrl('/empty/'),
          () => new HttpResponse(null, { status: 200, headers: { 'content-length': '0' } }),
        ),
      )

      const result = await fetchAPI('/empty/')

      expect(result).toBeUndefined()
    })

    test('parses JSON body for 200 with content', async () => {
      server.use(
        http.get(apiUrl('/ok/'), () => HttpResponse.json({ ok: true })),
      )

      const result = await fetchAPI('/ok/')

      expect(result).toEqual({ ok: true })
    })
  })
})
