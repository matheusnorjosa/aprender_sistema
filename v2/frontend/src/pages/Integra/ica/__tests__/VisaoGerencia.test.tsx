/** ICA — Visão por gerência (DADOS SIMULADOS do gerador). */
import type { JSX } from 'react';
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { IntegraDemoProvider, useIntegraDemo } from '../../dados/IntegraDemoContext';
import { gerarDadosSimulados } from '../../dados/gerador';
import { calcularEquipe } from '../calculo';
import { resumoPorGerencia } from '../componentes/c2/contas';
import { formatarNumero } from '../componentes/estilos';
import * as exportar from '../exportar';
import VisaoGerencia from '../VisaoGerencia';

const DADOS = gerarDadosSimulados();
const VIGENTE = DADOS.versoes_pesos.find((v) => v.id === DADOS.versao_vigente);
const RESUMO = resumoPorGerencia(calcularEquipe(DADOS.base, VIGENTE?.pesos ?? DADOS.versoes_pesos[0]!.pesos), DADOS.gerencias, DADOS.pessoas);

function renderizar(): void {
  render(
    <MemoryRouter>
      <IntegraDemoProvider dados={gerarDadosSimulados()}>
        <VisaoGerencia />
      </IntegraDemoProvider>
    </MemoryRouter>,
  );
}

describe('ICA — Visão por gerência', { timeout: 20000 }, () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('título e a versão de pesos usada', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Visão por gerência' })).toBeInTheDocument();
    expect(screen.getByText(/Configuração revisada \(nov\/2026\)/)).toBeInTheDocument();
  });

  test('tabela: cada gerência com gestora técnica, coordenadores, municípios, professores e ICA médio', async () => {
    renderizar();
    const tabela = await screen.findByRole('table', { name: /Resumo por gerência/i });
    const cabecalhos = within(tabela).getAllByRole('columnheader').map((h) => h.textContent);
    const coluna = (titulo: string): number => {
      const i = cabecalhos.indexOf(titulo);
      expect(i).toBeGreaterThan(0);
      return i;
    };
    for (const r of RESUMO) {
      const linha = within(tabela).getByText(r.gerencia.nome).closest('tr') as HTMLElement;
      expect(linha).toHaveTextContent(r.gestoraTecnica);
      expect(linha).toHaveTextContent(`${r.coordenadores.length} (${r.comCarteira} com municípios)`);
      // Pela célula da coluna, não um algarismo solto na linha (que casaria com outra coluna).
      const celulas = within(linha).getAllByRole('cell');
      expect(celulas[coluna('Municípios ativos')]).toHaveTextContent(new RegExp(`^${formatarNumero(r.municipiosAtivos)}$`));
      expect(linha).toHaveTextContent(r.professores.toLocaleString('pt-BR'));
      expect(linha).toHaveTextContent(new RegExp(`${r.icaMedio} · `));
    }
  });

  test('gráfico do ICA médio: cada barra com o nome da gerência, o número e o estrato escritos', async () => {
    renderizar();
    const grafico = await screen.findByRole('figure', { name: /ICA médio por gerência/i });
    for (const r of RESUMO) {
      const item = within(grafico).getByText(r.gerencia.nome).closest('li') as HTMLElement;
      expect(item).toHaveTextContent(new RegExp(`${r.icaMedio} · `));
    }
  });

  test('coordenadores de cada gerência, com link para a ficha', async () => {
    renderizar();
    const primeira = RESUMO[0]!;
    const lista = await screen.findByRole('list', { name: `Coordenadores da ${primeira.gerencia.nome}` });
    expect(within(lista).getAllByRole('listitem')).toHaveLength(primeira.coordenadores.length);
    const alguem = primeira.coordenadores[0]!;
    expect(within(lista).getByRole('link', { name: alguem.coordenador.nome })).toHaveAttribute(
      'href',
      `/integra/ica/coordenador/${alguem.coordenador.id}`,
    );
  });

  test('singular quando é um: "1 município ativo"', async () => {
    function MoverBelem(): JSX.Element {
      const { proporRemanejamento, aprovarRemanejamento, aplicarRemanejamento } = useIntegraDemo();
      return (
        <button
          type="button"
          onClick={() => {
            // Belém-PA (1) da Lucinéia (101) para a Priscila (117), que estava sem municípios.
            const r = proporRemanejamento([{ municipioId: 1, deCoordenadorId: 101, paraCoordenadorId: 117 }], 'teste');
            if (!r.ok) throw new Error(r.erros.join(' '));
            aprovarRemanejamento(r.id);
            aplicarRemanejamento(r.id);
          }}
        >
          mover Belém
        </button>
      );
    }
    render(
      <MemoryRouter>
        <IntegraDemoProvider dados={gerarDadosSimulados()}>
          <MoverBelem />
          <VisaoGerencia />
        </IntegraDemoProvider>
      </MemoryRouter>,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'mover Belém' }));
    const item = screen.getByRole('link', { name: 'Priscila Vasconcelos' }).closest('li') as HTMLElement;
    expect(item).toHaveTextContent(/1 município ativo · [\d.]+ professores/);
  });

  test('baixar planilha: uma linha por gerência', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Baixar planilha/i }));
    expect(baixar).toHaveBeenCalledTimes(1);
    const [nome, cabecalho, linhas] = baixar.mock.calls[0]!;
    expect(nome).toBe('ica_por_gerencia.csv');
    expect(cabecalho).toContain('ICA médio');
    expect(linhas).toHaveLength(RESUMO.length);
    expect(linhas[0]?.[0]).toBe(RESUMO[0]!.gerencia.nome);
  });

  test('imprimir / salvar PDF chama a impressão do navegador', async () => {
    const imprimir = vi.spyOn(exportar, 'imprimirPagina').mockImplementation(() => undefined);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Imprimir/i }));
    expect(imprimir).toHaveBeenCalledTimes(1);
  });
});
