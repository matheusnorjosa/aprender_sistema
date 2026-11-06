/**
 * Tests: ComboBox Component (PR16)
 *
 * Cobertura:
 * - Renderização inicial
 * - Carregamento de opções
 * - Seleção de item
 */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { Button, Form } from 'antd'
import ComboBox from '../ComboBox'

describe('ComboBox', () => {
  const mockOptions = [
    { id: 1, label: 'Fortaleza' },
    { id: 2, label: 'Sobral' },
    { id: 3, label: 'Juazeiro do Norte' },
  ]

  const mockLookupFunction = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockLookupFunction.mockResolvedValue(mockOptions)
  })

  // ============================================================================
  // TESTES DE RENDERIZAÇÃO
  // ============================================================================

  test('deve renderizar o componente AutoComplete', async () => {
    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        placeholder="Selecione um município"
      />
    )

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalled()
    })

    // AutoComplete renderiza como ant-select
    const selectElement = document.querySelector('.ant-select')
    expect(selectElement).toBeInTheDocument()
  })

  // Pedido do dono (03/11/2026): a opção pode levar uma marca ("sem compra") sem mudar o texto escolhido.
  test('renderOption desenha a opção; o campo mostra só o label do escolhido', async () => {
    const onChange = vi.fn()
    mockLookupFunction.mockResolvedValue([{ id: 9, label: 'Crato', sem_compra: true }])
    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        onChange={onChange}
        renderOption={(item) => (item.sem_compra ? <span>{item.label} <span>sem compra</span></span> : item.label)}
      />
    )
    await waitFor(() => expect(mockLookupFunction).toHaveBeenCalled())

    fireEvent.mouseDown(screen.getByRole('combobox'))
    fireEvent.click(await screen.findByText('sem compra'))

    expect(onChange).toHaveBeenCalledWith({ id: 9, label: 'Crato', sem_compra: true })
  })

  // Revisão de 03/11: trocar o projeto troca a função de busca; a marca "sem compra" do projeto
  // anterior não pode ficar na lista enquanto a busca nova não responde.
  test('trocar a função de busca tira as opções antigas antes de a nova responder', async () => {
    const antiga = vi.fn().mockResolvedValue([{ id: 1, label: 'Crato · sem compra' }])
    const { rerender } = render(<ComboBox lookupFunction={antiga} />)
    fireEvent.mouseDown(screen.getByRole('combobox'))
    expect(await screen.findByText('Crato · sem compra')).toBeInTheDocument()

    const nova = vi.fn().mockReturnValue(new Promise(() => {}))
    rerender(<ComboBox lookupFunction={nova} />)

    await waitFor(() => expect(nova).toHaveBeenCalled())
    expect(screen.queryByText('Crato · sem compra')).not.toBeInTheDocument()
  })

  test('deve exibir placeholder', async () => {
    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        placeholder="Selecione um município"
      />
    )

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalled()
    })

    // Placeholder aparece em um span
    expect(screen.getByText('Selecione um município')).toBeInTheDocument()
  })

  test('deve carregar opções iniciais no mount', async () => {
    render(<ComboBox lookupFunction={mockLookupFunction} />)

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalledWith('')
    })
  })

  // ============================================================================
  // TESTES DE VALOR CONTROLADO
  // ============================================================================

  test('deve exibir label do value fornecido', async () => {
    const selectedValue = { id: 1, label: 'Fortaleza' }

    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        value={selectedValue}
      />
    )

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalled()
    })

    // O input deve ter o valor "Fortaleza"
    const input = document.querySelector('.ant-select-selection-search-input')
    expect(input).toHaveValue('Fortaleza')
  })

  test('deve limpar input quando value é null', async () => {
    const { rerender } = render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        value={{ id: 1, label: 'Fortaleza' }}
      />
    )

    await waitFor(() => {
      expect(mockLookupFunction).toHaveBeenCalled()
    })

    rerender(
      <ComboBox
        lookupFunction={mockLookupFunction}
        value={null}
      />
    )

    const input = document.querySelector('.ant-select-selection-search-input')
    expect(input).toHaveValue('')
  })

  // ============================================================================
  // TESTES DE ESTADO DISABLED
  // ============================================================================

  test('deve estar desabilitado quando disabled=true', async () => {
    render(
      <ComboBox
        lookupFunction={mockLookupFunction}
        disabled={true}
      />
    )

    // AutoComplete desabilitado tem classe específica
    const selectElement = document.querySelector('.ant-select-disabled')
    expect(selectElement).toBeInTheDocument()
  })

  // ============================================================================
  // TESTES DE ERRO
  // ============================================================================

  test('deve lidar com erro no lookupFunction graciosamente', async () => {
    const failingLookup = vi.fn().mockRejectedValue(new Error('Network error'))

    render(<ComboBox lookupFunction={failingLookup} />)

    await waitFor(() => {
      expect(failingLookup).toHaveBeenCalled()
    })

    // Componente não deve quebrar
    const selectElement = document.querySelector('.ant-select')
    expect(selectElement).toBeInTheDocument()
  })

  // ============================================================================
  // ITEM 36 (19/10/2026): rótulo, texto solto e falha ao carregar
  // ============================================================================

  test('dentro do Form.Item, o rótulo nomeia o campo e o erro chega ao leitor de tela', async () => {
    render(
      <Form>
        <Form.Item label="Município" name="municipio" rules={[{ required: true, message: 'Selecione um município' }]}>
          <ComboBox lookupFunction={mockLookupFunction} />
        </Form.Item>
        <Button htmlType="submit">Enviar</Button>
      </Form>
    )
    const campo = screen.getByRole('combobox', { name: 'Município' })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
    const erro = await screen.findByText('Selecione um município')
    await waitFor(() => expect(campo).toHaveAttribute('aria-invalid', 'true'))
    const descritores = (campo.getAttribute('aria-describedby') ?? '').split(' ')
    expect(descritores.some((id) => id && document.getElementById(id)?.contains(erro))).toBe(true)
  })

  test('texto digitado sem escolher uma opção volta para o valor guardado ao sair do campo', async () => {
    const onChange = vi.fn()
    render(
      <ComboBox lookupFunction={mockLookupFunction} value={{ id: 1, label: 'Fortaleza' }} onChange={onChange} />
    )
    await waitFor(() => expect(mockLookupFunction).toHaveBeenCalled())
    const campo = screen.getByRole('combobox')
    fireEvent.change(campo, { target: { value: 'Caucaia' } })
    expect(campo).toHaveValue('Caucaia')
    fireEvent.blur(campo)
    await waitFor(() => expect(campo).toHaveValue('Fortaleza'))
    expect(onChange).not.toHaveBeenCalled()
  })

  test('falha ao carregar mostra o motivo e "Tentar de novo", não "Nenhum resultado"', async () => {
    const lookup = vi.fn().mockRejectedValueOnce(new Error('Servidor indisponível.')).mockResolvedValue(mockOptions)
    render(<ComboBox lookupFunction={lookup} oQueCarrega="os municípios" />)
    expect(await screen.findByText('Não foi possível carregar os municípios.')).toBeInTheDocument()
    expect(screen.getByText('Servidor indisponível.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo: carregar os municípios' }))
    await waitFor(() => expect(screen.queryByText('Não foi possível carregar os municípios.')).not.toBeInTheDocument())
    expect(lookup).toHaveBeenCalledTimes(2)
  })

  // ============================================================================
  // D6 (06/11/2026): só a busca mais recente mexe na lista (latest-wins)
  // ============================================================================

  type Item = { id: number; label: string }
  function adiado<T>() {
    let resolve!: (v: T) => void
    let reject!: (e: unknown) => void
    const promise = new Promise<T>((res, rej) => {
      resolve = res
      reject = rej
    })
    return { promise, resolve, reject }
  }

  describe('buscas fora de ordem', { timeout: 20000 }, () => {
    /** Abre a lista, espera a busca inicial e digita 'Fo' e depois 'For'. */
    async function digitarFoFor() {
      const A = adiado<Item[]>()
      const B = adiado<Item[]>()
      const lookup = vi.fn((q: string) => {
        if (q === 'Fo') return A.promise
        if (q === 'For') return B.promise
        return Promise.resolve([{ id: 3, label: 'Juazeiro do Norte' }])
      })
      render(<ComboBox lookupFunction={lookup} />)
      const campo = screen.getByRole('combobox')
      fireEvent.mouseDown(campo)
      expect(await screen.findByText('Juazeiro do Norte')).toBeInTheDocument()
      fireEvent.change(campo, { target: { value: 'Fo' } })
      fireEvent.change(campo, { target: { value: 'For' } })
      await waitFor(() => expect(lookup).toHaveBeenCalledWith('For'))
      await act(async () => B.resolve([{ id: 1, label: 'Fortaleza' }]))
      expect(await screen.findByText('Fortaleza')).toBeInTheDocument()
      expect(screen.queryByText('Juazeiro do Norte')).not.toBeInTheDocument()
      return { A }
    }

    test('resposta antiga que chega depois não sobrescreve a busca mais nova', async () => {
      const { A } = await digitarFoFor()
      await act(async () => A.resolve([{ id: 2, label: 'Sobral' }]))
      expect(screen.queryByText('Sobral')).not.toBeInTheDocument()
      expect(screen.getByText('Fortaleza')).toBeInTheDocument()
    })

    test('erro de busca antiga não aparece sobre a lista nova', async () => {
      const { A } = await digitarFoFor()
      await act(async () => A.reject(new Error('x')))
      expect(screen.queryByText('Não foi possível carregar as opções.')).not.toBeInTheDocument()
      expect(screen.getByText('Fortaleza')).toBeInTheDocument()
    })

    test('trocar a função de busca: a resposta atrasada da função antiga não volta', async () => {
      const A = adiado<Item[]>()
      const antiga = vi.fn(() => A.promise)
      const { rerender } = render(<ComboBox lookupFunction={antiga} />)
      await waitFor(() => expect(antiga).toHaveBeenCalled())
      const nova = vi.fn().mockResolvedValue([{ id: 3, label: 'Crato' }])
      rerender(<ComboBox lookupFunction={nova} />)
      fireEvent.mouseDown(screen.getByRole('combobox'))
      expect(await screen.findByText('Crato')).toBeInTheDocument()
      await act(async () => A.resolve([{ id: 1, label: 'Iguatu · sem compra' }]))
      expect(screen.queryByText('Iguatu · sem compra')).not.toBeInTheDocument()
    })
  })
})
