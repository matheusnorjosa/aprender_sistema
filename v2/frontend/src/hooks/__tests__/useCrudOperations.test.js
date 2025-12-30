/**
 * Tests: useCrudOperations Hook (Issue #302)
 *
 * Cobertura:
 * - fetchData com paginação
 * - handleCreate/handleUpdate/handleSave
 * - handleDelete e confirmDelete
 * - Estados loading e error
 * - handleTableChange e refresh
 */

import { renderHook, act } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest'
import { useCrudOperations } from '../useCrudOperations'

// Mock antd
vi.mock('antd', () => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Modal: {
    confirm: vi.fn(),
  },
}))

import { message, Modal } from 'antd'

describe('useCrudOperations', () => {
  // Mock API functions
  const mockListFn = vi.fn()
  const mockCreateFn = vi.fn()
  const mockUpdateFn = vi.fn()
  const mockDeleteFn = vi.fn()

  const defaultConfig = {
    listFn: mockListFn,
    createFn: mockCreateFn,
    updateFn: mockUpdateFn,
    deleteFn: mockDeleteFn,
    entityName: 'Registro',
  }

  const mockData = [
    { id: 1, nome: 'Item 1' },
    { id: 2, nome: 'Item 2' },
  ]

  const mockPaginatedResponse = {
    results: mockData,
    count: 50,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ============================================================================
  // TESTES DE ESTADO INICIAL
  // ============================================================================

  test('deve iniciar com estado vazio', () => {
    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    expect(result.current.data).toEqual([])
    expect(result.current.loading).toBe(false)
    expect(result.current.pagination.current).toBe(1)
    expect(result.current.pagination.total).toBe(0)
  })

  // ============================================================================
  // TESTES DE FETCHDATA
  // ============================================================================

  test('fetchData deve carregar dados com sucesso', async () => {
    mockListFn.mockResolvedValueOnce(mockPaginatedResponse)

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    await act(async () => {
      await result.current.fetchData()
    })

    expect(result.current.data).toEqual(mockData)
    expect(result.current.pagination.total).toBe(50)
    expect(result.current.loading).toBe(false)
  })

  test('fetchData deve setar loading=true durante chamada', async () => {
    let resolvePromise
    mockListFn.mockImplementationOnce(() => new Promise(resolve => {
      resolvePromise = () => resolve(mockPaginatedResponse)
    }))

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    // Start fetch (non-blocking)
    act(() => {
      result.current.fetchData()
    })

    // Should be loading
    expect(result.current.loading).toBe(true)

    // Resolve
    await act(async () => {
      resolvePromise()
    })

    expect(result.current.loading).toBe(false)
  })

  test('fetchData deve lidar com erro', async () => {
    mockListFn.mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    await act(async () => {
      const response = await result.current.fetchData()
      expect(response.success).toBe(false)
    })

    expect(message.error).toHaveBeenCalledWith('Erro ao carregar Registros: Network error')
  })

  test('fetchData deve passar parâmetros para listFn', async () => {
    mockListFn.mockResolvedValueOnce(mockPaginatedResponse)

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    await act(async () => {
      await result.current.fetchData({ page: 2, search: 'test' })
    })

    expect(mockListFn).toHaveBeenCalledWith(
      expect.objectContaining({
        page: 2,
        search: 'test',
      })
    )
  })

  test('fetchData deve lidar com resposta não-paginada', async () => {
    mockListFn.mockResolvedValueOnce(mockData) // Array direto, sem .results

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    await act(async () => {
      await result.current.fetchData()
    })

    expect(result.current.data).toEqual(mockData)
    expect(result.current.pagination.total).toBe(2)
  })

  // ============================================================================
  // TESTES DE HANDLECREATE
  // ============================================================================

  test('handleCreate deve criar registro com sucesso', async () => {
    const newRecord = { nome: 'Novo Item' }
    const createdRecord = { id: 3, ...newRecord }
    mockCreateFn.mockResolvedValueOnce(createdRecord)

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    let response
    await act(async () => {
      response = await result.current.handleCreate(newRecord)
    })

    expect(response.success).toBe(true)
    expect(response.data).toEqual(createdRecord)
    expect(message.success).toHaveBeenCalledWith('Registro criado com sucesso')
  })

  test('handleCreate deve lidar com erro', async () => {
    mockCreateFn.mockRejectedValueOnce(new Error('Validation error'))

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    let response
    await act(async () => {
      response = await result.current.handleCreate({ nome: '' })
    })

    expect(response.success).toBe(false)
    expect(message.error).toHaveBeenCalledWith('Erro ao criar Registro: Validation error')
  })

  // ============================================================================
  // TESTES DE HANDLEUPDATE
  // ============================================================================

  test('handleUpdate deve atualizar registro com sucesso', async () => {
    const updatedRecord = { id: 1, nome: 'Item Atualizado' }
    mockUpdateFn.mockResolvedValueOnce(updatedRecord)

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    let response
    await act(async () => {
      response = await result.current.handleUpdate(1, { nome: 'Item Atualizado' })
    })

    expect(response.success).toBe(true)
    expect(response.data).toEqual(updatedRecord)
    expect(message.success).toHaveBeenCalledWith('Registro atualizado com sucesso')
  })

  test('handleUpdate deve lidar com erro', async () => {
    mockUpdateFn.mockRejectedValueOnce(new Error('Not found'))

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    let response
    await act(async () => {
      response = await result.current.handleUpdate(999, { nome: 'Test' })
    })

    expect(response.success).toBe(false)
    expect(message.error).toHaveBeenCalledWith('Erro ao atualizar Registro: Not found')
  })

  // ============================================================================
  // TESTES DE HANDLESAVE
  // ============================================================================

  test('handleSave deve chamar handleCreate quando id é null', async () => {
    mockCreateFn.mockResolvedValueOnce({ id: 3, nome: 'Novo' })

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    await act(async () => {
      await result.current.handleSave({ nome: 'Novo' }, null)
    })

    expect(mockCreateFn).toHaveBeenCalled()
    expect(mockUpdateFn).not.toHaveBeenCalled()
  })

  test('handleSave deve chamar handleUpdate quando id existe', async () => {
    mockUpdateFn.mockResolvedValueOnce({ id: 1, nome: 'Atualizado' })

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    await act(async () => {
      await result.current.handleSave({ nome: 'Atualizado' }, 1)
    })

    expect(mockUpdateFn).toHaveBeenCalled()
    expect(mockCreateFn).not.toHaveBeenCalled()
  })

  // ============================================================================
  // TESTES DE HANDLEDELETE
  // ============================================================================

  test('handleDelete deve excluir registro com sucesso', async () => {
    mockDeleteFn.mockResolvedValueOnce()

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    let response
    await act(async () => {
      response = await result.current.handleDelete(1)
    })

    expect(response.success).toBe(true)
    expect(mockDeleteFn).toHaveBeenCalledWith(1)
    expect(message.success).toHaveBeenCalledWith('Registro excluído com sucesso')
  })

  test('handleDelete deve lidar com erro', async () => {
    mockDeleteFn.mockRejectedValueOnce(new Error('Cannot delete'))

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    let response
    await act(async () => {
      response = await result.current.handleDelete(1)
    })

    expect(response.success).toBe(false)
    expect(message.error).toHaveBeenCalledWith('Erro ao excluir Registro: Cannot delete')
  })

  // ============================================================================
  // TESTES DE CONFIRMDELETE
  // ============================================================================

  test('confirmDelete deve abrir modal de confirmação', async () => {
    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    act(() => {
      result.current.confirmDelete({ id: 1, nome: 'Item Test' })
    })

    expect(Modal.confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Excluir Registro?',
        content: 'Deseja excluir "Item Test"? Esta ação não pode ser desfeita.',
        okText: 'Sim, excluir',
        okType: 'danger',
        cancelText: 'Cancelar',
      })
    )
  })

  test('confirmDelete deve usar idField e nameField customizados', async () => {
    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    act(() => {
      result.current.confirmDelete(
        { codigo: 'ABC', titulo: 'Custom Item' },
        { idField: 'codigo', nameField: 'titulo' }
      )
    })

    expect(Modal.confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        content: 'Deseja excluir "Custom Item"? Esta ação não pode ser desfeita.',
      })
    )
  })

  // ============================================================================
  // TESTES DE HANDLETABLECHANGE
  // ============================================================================

  test('handleTableChange deve atualizar paginação e buscar dados', async () => {
    mockListFn.mockResolvedValue(mockPaginatedResponse)

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    await act(async () => {
      result.current.handleTableChange(3, 20)
    })

    expect(result.current.pagination.current).toBe(3)
    expect(result.current.pagination.pageSize).toBe(20)
    expect(mockListFn).toHaveBeenCalledWith(
      expect.objectContaining({ page: 3, pageSize: 20 })
    )
  })

  // ============================================================================
  // TESTES DE REFRESH
  // ============================================================================

  test('refresh deve recarregar página atual', async () => {
    mockListFn.mockResolvedValue(mockPaginatedResponse)

    const { result } = renderHook(() => useCrudOperations(defaultConfig))

    // Set current page to 2
    await act(async () => {
      result.current.handleTableChange(2, 15)
    })

    vi.clearAllMocks()
    mockListFn.mockResolvedValue(mockPaginatedResponse)

    await act(async () => {
      await result.current.refresh()
    })

    expect(mockListFn).toHaveBeenCalledWith(
      expect.objectContaining({ page: 2 })
    )
  })

  // ============================================================================
  // TESTES DE FUNÇÕES NÃO FORNECIDAS
  // ============================================================================

  test('handleCreate sem createFn deve retornar success=false', async () => {
    const { result } = renderHook(() => useCrudOperations({
      listFn: mockListFn,
      entityName: 'Registro',
      // Sem createFn
    }))

    let response
    await act(async () => {
      response = await result.current.handleCreate({ nome: 'Test' })
    })

    expect(response.success).toBe(false)
  })

  test('handleDelete sem deleteFn deve retornar success=false', async () => {
    const { result } = renderHook(() => useCrudOperations({
      listFn: mockListFn,
      entityName: 'Registro',
      // Sem deleteFn
    }))

    let response
    await act(async () => {
      response = await result.current.handleDelete(1)
    })

    expect(response.success).toBe(false)
  })
})
