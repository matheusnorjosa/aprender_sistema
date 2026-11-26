/**
 * Ficha do coordenador (DADOS SIMULADOS): ICA atual, estrato, variação desde o semestre anterior,
 * contribuição de cada componente (barra empilhada + tabela), carteira e histórico semestral.
 */
import type { JSX } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { IntegraDemoProvider, useIntegraDemo } from '../../dados/IntegraDemoContext';
import { PESOS_ORIGINAIS_V5 } from '../calculo';
import FichaCoordenador from '../FichaCoordenador';
import { renderTelaIca } from './telaIca';

const LUCINEIA = '/integra/ica/coordenador/101';

async function abrir(rota: string): Promise<void> {
  renderTelaIca(rota);
  await screen.findByRole('heading', { level: 1, name: 'Ficha do coordenador' });
}

function linhasDaTabela(nome: string): HTMLElement[] {
  const secao = screen.getByRole('region', { name: nome });
  return within(within(secao).getByRole('table')).getAllByRole('row').slice(1);
}

describe('Ficha do coordenador', { timeout: 20000 }, () => {
  test('ICA atual, estrato e variação desde o semestre anterior', async () => {
    await abrir(LUCINEIA);
    expect(screen.getByRole('heading', { level: 2, name: 'Lucinéia Barreto' })).toBeInTheDocument();
    const situacao = screen.getByRole('list', { name: 'Situação atual' });
    expect(situacao).toHaveTextContent('ICA atual: 169 · Sobrecarga');
    // Decisão 56 (rodada 4): quem muda o 2026.1 é a carga do Rogério, baixada para 0,2 (perfil 110 em dados/gerador.ts);
    // o Amigos do Bem só entra em 2026.2 (era −22, de 191).
    expect(situacao).toHaveTextContent('Variação desde 2026.1: −20 (era 189 · Sobrecarga)');
    expect(situacao).toHaveTextContent('Fora da meta (70 a 130)');
  });

  test('contribuição de cada componente: legenda com nome e número, e a tabela da conta', async () => {
    await abrir(LUCINEIA);
    const legenda = screen.getByRole('list', { name: 'Contribuição por componente' });
    const itens = within(legenda).getAllByRole('listitem');
    expect(itens).toHaveLength(6);
    expect(itens[0]).toHaveTextContent(/Municípios ativos: \d+,\d pontos/);
    expect(itens[5]).toHaveTextContent('Estados (UFs): fora da conta');
    expect(screen.getByText(/ICA: 168,9 → 169 · Sobrecarga/)).toBeInTheDocument();
  });

  test('carteira: municípios com coleções, turmas, professores, deslocamento e quem divide', async () => {
    await abrir(LUCINEIA);
    const linhas = linhasDaTabela('Carteira');
    expect(linhas).toHaveLength(9);
    const pontaGrossa = linhas.find((l) => l.textContent?.includes('Ponta Grossa-PR')) as HTMLElement;
    expect(pontaGrossa).toHaveTextContent('Rosimeire Cavalcante');
    // Tempo real do relatório de deslocamento (ida e volta).
    expect(pontaGrossa).toHaveTextContent('22h05');
  });

  test('município com ações suspensas aparece como "Suspenso" na carteira', async () => {
    await abrir('/integra/ica/coordenador/107');
    const capivari = linhasDaTabela('Carteira').find((l) => l.textContent?.includes('Capivari-SP')) as HTMLElement;
    expect(within(capivari).getByText('Suspenso')).toBeInTheDocument();
  });

  test('Amigos do Bem: o tempo é o do local de cada formação; fora do relatório, o tempo do meio estimado (55, 56)', async () => {
    await abrir('/integra/ica/coordenador/110');
    const linhas = linhasDaTabela('Carteira');
    const linha = (nome: string) => linhas.find((l) => l.textContent?.includes(nome)) as HTMLElement;
    // Mauriti-CE não está no relatório: o tempo do meio do relatório, 17h45 (antes, a mediana da tabela, 17h48).
    expect(linha('Amigos do Bem (Mauriti)-CE')).toHaveTextContent('17h45 (estimado)');
    // Santana do Ipanema-AL e Petrolina-PE estão no relatório: o tempo de lá, sem "estimado".
    expect(linha('Amigos do Bem (Santana do Ipanema)-AL')).toHaveTextContent('19h00');
    expect(linha('Amigos do Bem (Santana do Ipanema)-AL')).not.toHaveTextContent('estimado');
    expect(linha('Amigos do Bem (Petrolina)-PE')).toHaveTextContent('25h45');
    expect(screen.getByText(/Deslocamento estimado/)).toHaveTextContent(
      'Deslocamento estimado: Amigos do Bem (Mauriti)-CE não está no relatório de tempos; a conta usa o tempo do meio do relatório (17h45).',
    );
    expect(document.body).not.toHaveTextContent('17h48');
    expect(screen.getByText(/Turmas não informadas em Amigos do Bem \(Mauriti\)-CE/)).toBeInTheDocument();
  });

  test('histórico semestral do ICA, com a versão de pesos de cada semestre', async () => {
    await abrir(LUCINEIA);
    const linhas = linhasDaTabela('Histórico semestral');
    expect(linhas.map((l) => l.textContent)).toEqual([
      // Decisão 56 (rodada 4): em 2025.2 e 2026.1 ainda não há Amigos do Bem; quem muda as médias da equipe é a carga
      // do Rogério, baixada para 0,2 (perfil 110 em dados/gerador.ts). Eram 190 e 191.
      expect.stringMatching(/2025\.2.*188 · Sobrecarga.*proposta v5/),
      expect.stringMatching(/2026\.1.*189 · Sobrecarga.*proposta v5/),
      expect.stringMatching(/2026\.2.*169 · Sobrecarga.*revisada/),
    ]);
  });

  test('depois de mudar os pesos na sessão, 2026.2 continua o retrato publicado e a sessão ganha a linha "Agora"', async () => {
    function TrocarPesos(): JSX.Element {
      const { trocarPesos } = useIntegraDemo();
      return (
        <button type="button" onClick={() => trocarPesos(PESOS_ORIGINAIS_V5, 'Teste da ficha')}>
          trocar pesos
        </button>
      );
    }
    render(
      <MemoryRouter initialEntries={[LUCINEIA]}>
        <IntegraDemoProvider>
          <TrocarPesos />
          <Routes>
            <Route path="/integra/ica/coordenador/:id" element={<FichaCoordenador />} />
          </Routes>
        </IntegraDemoProvider>
      </MemoryRouter>,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'trocar pesos' }));
    const linhas = linhasDaTabela('Histórico semestral').map((l) => l.textContent);
    expect(linhas).toHaveLength(4);
    // Como no Histórico: o retrato publicado não é trocado pelo cálculo da sessão.
    expect(linhas[2]).toMatch(/2026\.2.*169 · Sobrecarga.*revisada.*calculado em/);
    expect(linhas[3]).toMatch(/Agora \(nesta demonstração\).*Versão 3 \(demonstração\).*nesta sessão/);
    expect(linhas[3]).not.toMatch(/calculado em/);
    expect(screen.getByRole('list', { name: 'Situação atual' })).toHaveTextContent(/Variação desde 2026\.2: .* \(era 169 · Sobrecarga\)/);
  });

  test('a conta de quem está sem municípios não termina em "Capacidade disponível"', async () => {
    await abrir('/integra/ica/coordenador/117');
    const conta = screen.getByRole('region', { name: 'Contribuição de cada componente' });
    expect(within(conta).getByText('Sem municípios: ICA 0, fora da média da equipe')).toBeInTheDocument();
    expect(conta).not.toHaveTextContent(/Capacidade disponível/);
  });

  test('barra empilhada: os pedaços ficam mais baixos que a linha da média, que aparece acima e abaixo deles', async () => {
    await abrir(LUCINEIA);
    const conta = screen.getByRole('region', { name: 'Contribuição de cada componente' });
    const pedacos = conta.querySelector('[data-parte="pedacos"]');
    const media = conta.querySelector('[data-parte="media"]');
    expect(pedacos).toHaveClass('inset-y-1.5');
    expect(media).toHaveClass('inset-y-0');
    expect(pedacos?.parentElement).toBe(media?.parentElement);
  });

  test('quem chegou agora e está sem municípios', async () => {
    await abrir('/integra/ica/coordenador/117');
    const situacao = screen.getByRole('list', { name: 'Situação atual' });
    expect(situacao).toHaveTextContent('ICA atual: 0 · Sem municípios');
    expect(situacao).toHaveTextContent('Sem cálculo em 2026.1');
    expect(screen.getByText(/Nenhum município na carteira/)).toBeInTheDocument();
  });

  test('coordenador que não existe: avisa e volta ao painel', async () => {
    await abrir('/integra/ica/coordenador/1');
    expect(screen.getByText('Coordenador não encontrado.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Voltar ao painel' })).toHaveAttribute('href', '/integra/ica');
  });
});
