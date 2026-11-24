/** ICA — Histórico semestral (DADOS SIMULADOS do gerador). */
import type { JSX } from 'react';
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import { IntegraDemoProvider, useIntegraDemo } from '../../dados/IntegraDemoContext';
import { gerarDadosSimulados } from '../../dados/gerador';
import { calcularEquipe } from '../calculo';
import * as exportar from '../exportar';
import Historico from '../Historico';

const DADOS = gerarDadosSimulados();
const SEMESTRES = DADOS.historico.map((h) => {
  const versao = DADOS.versoes_pesos.find((v) => v.id === h.versao_pesos)!;
  return { ...h, versao, resultado: calcularEquipe(h.base, versao.pesos) };
});
const ICA_EM = (semestre: number, id: number) =>
  SEMESTRES[semestre]!.resultado.coordenadores.find((r) => r.coordenador.id === id)?.conta.icaExibido;

/** Propõe, aprova e aplica um remanejamento, como o Simulador faria. */
function AplicarRemanejamento(): JSX.Element {
  const { base, proporRemanejamento, aprovarRemanejamento, aplicarRemanejamento } = useIntegraDemo();
  return (
    <button
      type="button"
      onClick={() => {
        const municipioId = base.atendimentos.find((a) => a.coordenador === 103)!.municipio;
        const r = proporRemanejamento([{ municipioId, deCoordenadorId: 103, paraCoordenadorId: 117 }], 'Teste do histórico');
        if (!r.ok) throw new Error(r.erros.join(' '));
        aprovarRemanejamento(r.id);
        aplicarRemanejamento(r.id);
      }}
    >
      aplicar remanejamento
    </button>
  );
}

function renderizar(): void {
  render(
    <MemoryRouter>
      <IntegraDemoProvider dados={gerarDadosSimulados()}>
        <AplicarRemanejamento />
        <Historico />
      </IntegraDemoProvider>
    </MemoryRouter>,
  );
}

describe('ICA — Histórico semestral', { timeout: 20000 }, () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('dispersão da equipe por semestre, com a versão de pesos de cada um', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Histórico semestral' })).toBeInTheDocument();
    const tabela = screen.getByRole('table', { name: /Dispersão da equipe/i });
    for (const s of SEMESTRES) {
      const linha = within(tabela).getByText(s.semestre).closest('tr') as HTMLElement;
      expect(linha).toHaveTextContent(s.versao.nome);
      expect(linha).toHaveTextContent(s.resultado.dispersao.desvioPadrao.toLocaleString('pt-BR', { maximumFractionDigits: 1, minimumFractionDigits: 1 }));
      expect(linha).toHaveTextContent(String(Math.round(s.resultado.dispersao.maior)));
    }
  });

  test('gráfico da dispersão: cada semestre com menor, maior e desvio escritos', async () => {
    renderizar();
    const grafico = await screen.findByRole('figure', { name: /Dispersão da equipe/i });
    const ultimo = SEMESTRES.at(-1)!;
    const item = within(grafico).getByText(ultimo.semestre).closest('li') as HTMLElement;
    expect(item).toHaveTextContent(`de ${Math.round(ultimo.resultado.dispersao.menor)} a ${Math.round(ultimo.resultado.dispersao.maior)}`);
  });

  test('legenda da dispersão não chama de 100 os traços do menor e do maior ICA', async () => {
    renderizar();
    const grafico = await screen.findByRole('figure', { name: /Dispersão da equipe/i });
    expect(grafico).not.toHaveTextContent('traço preto = 100');
    expect(grafico).toHaveTextContent('traços pretos = menor e maior ICA; bolinha = média');
  });

  test('ICA de cada coordenador em cada semestre; quem chegou depois aparece como "não estava na equipe"', async () => {
    renderizar();
    const tabela = await screen.findByRole('table', { name: /ICA por coordenador/i });
    const lucineia = within(tabela).getByText('Lucinéia Barreto').closest('tr') as HTMLElement;
    for (let i = 0; i < SEMESTRES.length; i++) expect(lucineia).toHaveTextContent(`${ICA_EM(i, 101)} · `);
    const priscila = within(tabela).getByText('Priscila Vasconcelos').closest('tr') as HTMLElement;
    expect(priscila).toHaveTextContent(/Não estava na equipe/);
    expect(priscila).toHaveTextContent(/Sem municípios/);
  });

  test('registro dos remanejamentos aplicados, do mais novo para o mais antigo', async () => {
    renderizar();
    const lista = await screen.findByRole('list', { name: 'Remanejamentos aplicados' });
    const itens = within(lista).getAllByRole('listitem').filter((li) => li.parentElement === lista);
    expect(itens).toHaveLength(2);
    expect(itens[0]).toHaveTextContent(/2026\.2/);
    expect(itens[0]).toHaveTextContent(/Imperatriz-MA: de Lucinéia Barreto para Rogério Assunção/);
    expect(itens[0]).toHaveTextContent(/Aprovado por Líder do NFP em 13\/07\/2026/);
    expect(itens[1]).toHaveTextContent(/Campina Grande-PB: de Edvaldo Quaresma para Ivonete Sampaio/);
  });

  test('remanejamento aplicado na sessão entra no registro e ganha a coluna "Agora"', async () => {
    renderizar();
    expect(screen.queryByText(/Agora \(nesta demonstração\)/)).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'aplicar remanejamento' }));
    const lista = screen.getByRole('list', { name: 'Remanejamentos aplicados' });
    const itens = within(lista).getAllByRole('listitem').filter((li) => li.parentElement === lista);
    expect(itens).toHaveLength(3);
    expect(itens[0]).toHaveTextContent(/Teste do histórico/);
    expect(itens[0]).toHaveTextContent(/Você \(demonstração\)/);
    const tabela = screen.getByRole('table', { name: /ICA por coordenador/i });
    expect(within(tabela).getByText('Agora (nesta demonstração)')).toBeInTheDocument();
  });

  test('variação: sem comparação quando um dos dois cálculos está sem municípios (a mesma regra da Ficha)', async () => {
    renderizar();
    // O remanejamento dá à Priscila (117, sem municípios em 2026.2) um município da Rosimeire.
    await userEvent.click(await screen.findByRole('button', { name: 'aplicar remanejamento' }));
    const tabela = screen.getByRole('table', { name: /ICA por coordenador/i });
    const cabecalhos = within(tabela).getAllByRole('columnheader').map((h) => h.textContent);
    const coluna = cabecalhos.indexOf('Variação desde o anterior');
    expect(coluna).toBeGreaterThan(0);
    const linha = within(tabela).getByRole('link', { name: 'Priscila Vasconcelos' }).closest('tr') as HTMLElement;
    expect(within(linha).getAllByRole('cell')[coluna]).toHaveTextContent(/^—$/);
  });

  test('baixar planilha: uma linha por coordenador e uma coluna de ICA por semestre', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Baixar planilha/i }));
    const [nome, cabecalho, linhas] = baixar.mock.calls[0]!;
    expect(nome).toBe('ica_historico.csv');
    for (const s of SEMESTRES) expect(cabecalho).toContain(`ICA ${s.semestre}`);
    expect(linhas).toHaveLength(DADOS.base.coordenadores.length);
  });
});
