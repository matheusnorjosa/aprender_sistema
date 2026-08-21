/**
 * Vitest setup file
 *
 * Configures testing environment with:
 * - jest-dom matchers for DOM assertions
 * - Global mocks for browser APIs not available in jsdom
 * - MSW server for intercepting HTTP traffic (see src/test/mocks/)
 */
import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll, vi } from 'vitest'
import { server } from './mocks/server'

// --- MSW lifecycle --------------------------------------------------------
// `onUnhandledRequest: 'bypass'` during rollout so tests that still rely on
// module-level mocks (vi.mock('../config'), injected callbacks) keep working
// without forcing every file to declare a handler. Flip to 'error' once
// coverage is broad enough. See v2/docs/TESTING_MSW.md.
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// Mock matchMedia for Ant Design components
// This must be defined before any Ant Design components are imported
const mockMatchMedia = vi.fn().mockImplementation((query) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}))

vi.stubGlobal('matchMedia', mockMatchMedia)

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
