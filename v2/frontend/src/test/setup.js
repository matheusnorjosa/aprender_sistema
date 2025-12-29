/**
 * Vitest setup file
 *
 * Configures testing environment with:
 * - jest-dom matchers for DOM assertions
 * - Global mocks for browser APIs not available in jsdom
 */
import '@testing-library/jest-dom'
import { vi } from 'vitest'

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
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
