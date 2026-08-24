/**
 * Tests: ImportUploader (componente reutilizável de upload de importação)
 *
 * Cobertura (presença/estado, sem fluxo assíncrono):
 * - UI de upload renderiza (área/dragger + input de arquivo)
 * - Título/label e textos-guia
 * - Descrição opcional (presente/ausente)
 * - Estado inicial: sem botões de validar/importar/nova importação
 * - Callbacks (onDryRun/onApply) não disparam na montagem
 *
 * Nota: o componente recebe onDryRun/onApply por props (callbacks injetados) e
 * não importa nenhum cliente de API nem faz fetch no mount — logo não há
 * promise pendente no teardown (sem risco de EnvironmentTeardownError). Por
 * isso não é necessário vi.mock de '../../api/*'.
 */

import { render, screen } from '@testing-library/react';
import { describe, test, expect, vi, afterEach } from 'vitest';
import ImportUploader, {
  type ApplyResult,
  type ValidationResult,
} from '../ImportUploader';

const makeDryRun = () =>
  vi.fn((_file: File): Promise<ValidationResult> => Promise.resolve({ stats: {} }));

const makeApply = () =>
  vi.fn((_file: File): Promise<ApplyResult> => Promise.resolve({ stats: {} }));

describe('ImportUploader', () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  test('renderiza o título com o label', () => {
    render(
      <ImportUploader
        label="Importar Compras"
        onDryRun={makeDryRun()}
        onApply={makeApply()}
      />,
    );

    expect(screen.getByText('Importar Compras')).toBeInTheDocument();
  });

  test('renderiza a área de upload e os textos-guia', () => {
    const { container } = render(
      <ImportUploader
        label="Importar Compras"
        onDryRun={makeDryRun()}
        onApply={makeApply()}
      />,
    );

    // Passo 1 (seleção de arquivo) e textos de orientação do dragger
    expect(screen.getByText('1. Selecione o arquivo')).toBeInTheDocument();
    expect(screen.getByText('Clique ou arraste o arquivo aqui')).toBeInTheDocument();
    expect(screen.getByText('Formatos aceitos: CSV, XLSX, XLS')).toBeInTheDocument();

    // Input de arquivo presente e restrito aos formatos aceitos
    const input = container.querySelector('input[type="file"]');
    expect(input).not.toBeNull();
    expect(input).toHaveAttribute('accept', '.csv,.xlsx,.xls');
  });

  test('renderiza a descrição quando fornecida', () => {
    render(
      <ImportUploader
        label="Importar Compras"
        description="Envie a planilha exportada do sistema."
        onDryRun={makeDryRun()}
        onApply={makeApply()}
      />,
    );

    expect(
      screen.getByText('Envie a planilha exportada do sistema.'),
    ).toBeInTheDocument();
  });

  test('não renderiza descrição quando ausente', () => {
    render(
      <ImportUploader
        label="Importar Compras"
        onDryRun={makeDryRun()}
        onApply={makeApply()}
      />,
    );

    expect(
      screen.queryByText('Envie a planilha exportada do sistema.'),
    ).not.toBeInTheDocument();
  });

  test('estado inicial: sem botões de validar, importar ou nova importação', () => {
    render(
      <ImportUploader
        label="Importar Compras"
        onDryRun={makeDryRun()}
        onApply={makeApply()}
      />,
    );

    // Sem arquivo selecionado, o passo 2 (validar) ainda não aparece
    expect(
      screen.queryByRole('button', { name: /Validar Importação/i }),
    ).not.toBeInTheDocument();
    // Nada validado/aplicado → sem botão de aplicar nem de reset
    expect(
      screen.queryByRole('button', { name: /Realizar Importação/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /Nova Importação/i }),
    ).not.toBeInTheDocument();
  });

  test('não chama onDryRun nem onApply na montagem', () => {
    const onDryRun = makeDryRun();
    const onApply = makeApply();

    render(
      <ImportUploader label="Importar Compras" onDryRun={onDryRun} onApply={onApply} />,
    );

    expect(onDryRun).not.toHaveBeenCalled();
    expect(onApply).not.toHaveBeenCalled();
  });
});
