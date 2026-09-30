/**
 * Vitest setup file
 *
 * Configures testing environment with:
 * - jest-dom matchers for DOM assertions
 * - Global mocks for browser APIs not available in jsdom
 * - MSW server for intercepting HTTP traffic (see src/test/mocks/)
 */
import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest'
import { LARGURA_PADRAO, definirLarguraTela, matchMediaDeTeste } from './larguraTela'
import { server } from './mocks/server'

// --- MSW lifecycle --------------------------------------------------------
// `onUnhandledRequest: 'bypass'` during rollout so tests that still rely on
// module-level mocks (vi.mock('../config'), injected callbacks) keep working
// without forcing every file to declare a handler. Flip to 'error' once
// coverage is broad enough. See v2/docs/TESTING_MSW.md.
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// matchMedia por largura (Programa C, C1): avalia min-width/max-width contra 1280 px por
// padrão; `definirLarguraTela(px)` (src/test/larguraTela.ts) muda a largura no teste.
// Definido antes de qualquer componente do AntD ser importado.
vi.stubGlobal('matchMedia', matchMediaDeTeste)
definirLarguraTela(LARGURA_PADRAO)
beforeEach(() => definirLarguraTela(LARGURA_PADRAO))

// Mock scrollTo for components that use it
Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: () => {},
})

// Mock ResizeObserver for Ant Design components
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
