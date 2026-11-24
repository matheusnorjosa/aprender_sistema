/** ICA — Comparativo de pesos (DADOS SIMULADOS do gerador). */
import type { JSX } from 'react';
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { IntegraDemoProvider, useIntegraDemo } from '../../dados/IntegraDemoContext';
import { gerarDadosSimulados } from '../../dados/gerador';
import { compararPesos, PESOS_ORIGINAIS_V5, PESOS_REVISADOS } from '../calculo';
import Comparativo from '../Comparativo';
import * as exportar from '../exportar';

const DADOS = gerarDadosSimulados();
const COMPARACAO = compararPesos(DADOS.base, PESOS_ORIGINAIS_V5, PESOS_REVISADOS);

/** Cria uma versão de pesos na sessão, como a tela "Pesos e faixas" faria. */
function CriarVersao(): JSX.Element {
  const { trocarPesos } = useIntegraDemo();
  return (
    <button
      type="button"
      onClick={() =>
        trocarPesos({ municipios: 30, frentes: 30, turmas: 15, professores: 15, deslocamento: 10, estados: 0 }, 'Teste')
      }
    >
      criar versão
    </button>
  );
}

function renderizar(): void {
  render(
    <MemoryRouter>
      <IntegraDemoProvider dados={gerarDadosSimulados()}>
        <CriarVersao />
        <Comparativo />
      </IntegraDemoProvider>
    </MemoryRouter>,
  );
}

describe('ICA — Comparativo de pesos', { timeout: 20000 }, () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('começa comparando a original (v5) com a vigente (revisada)', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Comparativo de pesos' })).toBeInTheDocument();
    expect(screen.getByLabelText('Versão A')).toHaveValue('v5');
    expect(screen.getByLabelText('Versão B')).toHaveValue('revisada-2026-11');
  });

  test('os pesos das duas versões lado a lado', async () => {
    renderizar();
    const tabela = await screen.findByRole('table', { name: /Pesos das duas versões/i });
    const estados = within(tabela).getByText('Estados (UFs)').closest('tr') as HTMLElement;
    expect(estados).toHaveTextContent('10%');
    expect(estados).toHaveTextContent('0%');
  });

  test('quem muda de estrato aparece em destaque, com o antes e o depois escritos', async () => {
    renderizar();
    const n = COMPARACAO.mudaramDeEstrato.length;
    expect(n).toBeGreaterThan(0);
    const destaque = await screen.findByRole('region', { name: 'Quem muda de estrato' });
    expect(destaque).toHaveTextContent(`${n} ${n === 1 ? 'coordenador muda' : 'coordenadores mudam'} de estrato`);
    for (const l of COMPARACAO.mudaramDeEstrato) {
      const item = within(destaque).getByText(l.nome).closest('li') as HTMLElement;
      expect(item).toHaveTextContent(`${l.antes.conta.icaExibido} · `);
      expect(item).toHaveTextContent(`${l.depois.conta.icaExibido} · `);
    }
    // A história do gerador: Socorro sai de Adequada e vai para Capacidade disponível.
    const socorro = within(destaque).getByText('Socorro Bezerra Lins').closest('li') as HTMLElement;
    expect(socorro).toHaveTextContent(/Adequada.*Capacidade disponível/);
  });

  test('tabela com todos os coordenadores: ICA nas duas versões, variação e se muda de estrato', async () => {
    renderizar();
    const tabela = await screen.findByRole('table', { name: /ICA de cada coordenador/i });
    for (const l of COMPARACAO.linhas) {
      const linha = within(tabela).getByText(l.nome).closest('tr') as HTMLElement;
      expect(linha).toHaveTextContent(l.mudouEstrato ? /Muda de estrato/ : /Mesmo estrato/);
    }
  });

  test('escolher a mesma versão nos dois lados avisa que são iguais', async () => {
    renderizar();
    await userEvent.selectOptions(await screen.findByLabelText('Versão A'), 'revisada-2026-11');
    expect(screen.getByText(/As duas versões são a mesma/i)).toBeInTheDocument();
  });

  test('a versão criada na sessão entra na lista e passa a ser a B (vigente)', async () => {
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: 'criar versão' }));
    const b = screen.getByLabelText('Versão B');
    expect(within(b).getByRole('option', { name: /Versão 3 \(demonstração\)/ })).toBeInTheDocument();
    expect(b).toHaveValue('sessao-3');
  });

  test('baixar planilha: uma linha por coordenador', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Baixar planilha/i }));
    const [nome, cabecalho, linhas] = baixar.mock.calls[0]!;
    expect(nome).toBe('ica_comparativo_de_pesos.csv');
    expect(cabecalho).toContain('Muda de estrato');
    expect(linhas).toHaveLength(COMPARACAO.linhas.length);
  });
});
