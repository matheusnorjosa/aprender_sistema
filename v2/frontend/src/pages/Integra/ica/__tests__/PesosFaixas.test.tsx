/**
 * Pesos e faixas (DADOS SIMULADOS): editar os pesos (soma 100% obrigatória), justificativa
 * obrigatória, nova versão na lista, resultado recalculado ao vivo e a configuração original (v5)
 * para comparar.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { renderTelaIca } from './telaIca';

type Usuario = ReturnType<typeof userEvent.setup>;

async function abrir(): Promise<void> {
  renderTelaIca('/integra/ica/pesos');
  await screen.findByRole('heading', { level: 1, name: 'Pesos e faixas' });
}

async function trocarPeso(user: Usuario, rotulo: string, valor: string): Promise<void> {
  const campo = screen.getByLabelText(`${rotulo}: peso em %`);
  await user.clear(campo);
  await user.type(campo, valor);
}

function linhaDaTabela(regiao: string, texto: string): HTMLElement {
  const tabela = within(screen.getByRole('region', { name: regiao })).getByRole('table');
  return within(tabela)
    .getAllByRole('row')
    .find((l) => l.textContent?.includes(texto)) as HTMLElement;
}

describe('Pesos e faixas', { timeout: 20000 }, () => {
  test('mostra a versão em vigor e os pesos dela no formulário, somando 100%', async () => {
    await abrir();
    expect(screen.getByRole('region', { name: 'Versão em vigor' })).toHaveTextContent('Configuração revisada (nov/2026)');
    expect(screen.getByLabelText('Municípios ativos: peso em %')).toHaveValue(25);
    expect(screen.getByLabelText('Tempo de deslocamento (ida e volta): peso em %')).toHaveValue(10);
    expect(screen.getByLabelText('Estados (UFs): peso em %')).toHaveValue(0);
    expect(screen.getByRole('status', { name: 'Soma dos pesos' })).toHaveTextContent('Soma: 100%');
  });

  test('soma diferente de 100% não salva e o resultado espera o ajuste', async () => {
    const user = userEvent.setup();
    await abrir();
    await trocarPeso(user, 'Municípios ativos', '30');
    expect(screen.getByRole('status', { name: 'Soma dos pesos' })).toHaveTextContent('Soma: 105%');
    expect(screen.getByText(/Ajuste os pesos para somarem 100%/)).toBeInTheDocument();
    await user.type(screen.getByLabelText('Justificativa da mudança'), 'Teste.');
    await user.click(screen.getByRole('button', { name: 'Salvar como nova versão' }));
    expect(screen.getByText('Os pesos precisam somar 100%. Hoje somam 105%.')).toBeInTheDocument();
  });

  test('justificativa é obrigatória', async () => {
    const user = userEvent.setup();
    await abrir();
    await trocarPeso(user, 'Municípios ativos', '30');
    await trocarPeso(user, 'Tempo de deslocamento (ida e volta)', '5');
    await user.click(screen.getByRole('button', { name: 'Salvar como nova versão' }));
    expect(screen.getByText('Escreva a justificativa da mudança.')).toBeInTheDocument();
  });

  test('peso negativo: a soma mostrada é a real e o motivo é o peso fora de 0 a 100', async () => {
    const user = userEvent.setup();
    await abrir();
    await trocarPeso(user, 'Estados (UFs)', '-5');
    expect(screen.getByRole('status', { name: 'Soma dos pesos' })).toHaveTextContent('Soma: 95% (há peso fora de 0 a 100)');
    expect(screen.getByLabelText('Estados (UFs): peso em %')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Municípios ativos: peso em %')).not.toHaveAttribute('aria-invalid');
  });

  test('peso com decimal: a soma mostra as casas ("99,6%") e o erro fala em português', async () => {
    const user = userEvent.setup();
    await abrir();
    await trocarPeso(user, 'Tempo de deslocamento (ida e volta)', '9.6');
    expect(screen.getByRole('status', { name: 'Soma dos pesos' })).toHaveTextContent('Soma: 99,6% (precisa dar 100%)');
    await user.type(screen.getByLabelText('Justificativa da mudança'), 'Teste.');
    await user.click(screen.getByRole('button', { name: 'Salvar como nova versão' }));
    expect(screen.getByText('Os pesos precisam somar 100%. Hoje somam 99,6%.')).toBeInTheDocument();
  });

  test('sem justificativa: o erro fica ligado ao campo e o foco vai para ele (como no Simulador)', async () => {
    const user = userEvent.setup();
    await abrir();
    await trocarPeso(user, 'Municípios ativos', '30');
    await trocarPeso(user, 'Tempo de deslocamento (ida e volta)', '5');
    await user.click(screen.getByRole('button', { name: 'Salvar como nova versão' }));
    const campo = screen.getByLabelText('Justificativa da mudança');
    expect(campo).toHaveAttribute('aria-invalid', 'true');
    const descricao = document.getElementById(campo.getAttribute('aria-describedby') ?? '');
    expect(descricao).toHaveTextContent('Escreva a justificativa da mudança.');
    expect(campo).toHaveFocus();
  });

  test('soma errada ao salvar: os seis pesos ficam marcados e o foco vai para a mensagem', async () => {
    const user = userEvent.setup();
    await abrir();
    await trocarPeso(user, 'Municípios ativos', '30');
    await user.type(screen.getByLabelText('Justificativa da mudança'), 'Teste.');
    await user.click(screen.getByRole('button', { name: 'Salvar como nova versão' }));
    for (const rotulo of ['Municípios ativos', 'Estados (UFs)']) {
      expect(screen.getByLabelText(`${rotulo}: peso em %`)).toHaveAttribute('aria-invalid', 'true');
    }
    expect(screen.getByLabelText('Justificativa da mudança')).not.toHaveAttribute('aria-invalid');
    expect(screen.getByText('Os pesos precisam somar 100%. Hoje somam 105%.').closest('[tabindex="-1"]')).toHaveFocus();
  });

  test('configuração original (v5) para comparar, componente a componente', async () => {
    await abrir();
    const estados = linhaDaTabela('Comparação com a configuração original (v5)', 'Estados (UFs)');
    expect(within(estados).getAllByRole('cell').map((c) => c.textContent)).toEqual(['Estados (UFs)', '10%', '0%', '0%']);
  });

  test('usar a v5 recalcula ao vivo; salvar cria a versão nova, em vigor, com autor e justificativa', async () => {
    const user = userEvent.setup();
    await abrir();
    await user.click(screen.getByRole('button', { name: 'Usar a configuração original (v5)' }));
    const previa = screen.getByRole('region', { name: 'Como fica com estes pesos' });
    expect(previa).toHaveTextContent('Socorro Bezerra Lins: 77 · Capacidade disponível → 90 · Adequada');
    expect(previa).toHaveTextContent('Valdir Maciel: 82 · Adequada → 79 · Capacidade disponível');
    const contagem = within(previa).getByRole('list', { name: 'Quantos em cada estrato' });
    expect(within(contagem).getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'Sobrecarga: 3 → 3',
      'Atenção: 2 → 2',
      'Adequada: 6 → 6',
      'Capacidade disponível: 5 → 5',
      'Sem municípios: 1 → 1',
    ]);

    // O aviso de "salvou" é uma região viva que já está na tela, vazia, antes de salvar.
    const aviso = screen.getByRole('status', { name: '' });
    expect(aviso).toBeEmptyDOMElement();
    await user.type(screen.getByLabelText('Justificativa da mudança'), 'Comparar com a proposta original.');
    await user.click(screen.getByRole('button', { name: 'Salvar como nova versão' }));
    expect(aviso).toHaveTextContent(/Versão 3 \(demonstração\) criada e em vigor/);

    const nova = linhaDaTabela('Versões', 'Versão 3 (demonstração)');
    expect(nova).toHaveTextContent('Em vigor');
    expect(nova).toHaveTextContent('Você (demonstração)');
    expect(nova).toHaveTextContent('Comparar com a proposta original.');
    expect(linhaDaTabela('Versões', 'Configuração revisada (nov/2026)')).not.toHaveTextContent('Em vigor');
    expect(screen.getByRole('region', { name: 'Versão em vigor' })).toHaveTextContent('Versão 3 (demonstração)');
  });

  test('faixas: legenda com nome, valores e orientação', async () => {
    await abrir();
    expect(screen.getByRole('list', { name: 'Faixas do ICA' })).toBeInTheDocument();
    expect(screen.getByText(/as faixas ficam fixas/i)).toBeInTheDocument();
  });
});
