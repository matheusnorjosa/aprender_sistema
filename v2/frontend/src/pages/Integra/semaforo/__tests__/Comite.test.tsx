/**
 * Semáforo — Comitê de Satisfação (DADOS SIMULADOS): a cor sugerida pela regra para cada município no
 * ciclo atual, confirmar ou alterar (alterar exige justificativa), a seta de mudança desde o ciclo
 * anterior, o filtro por cor e o "sem dado" explicado.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { QUEM_VE } from '../../quemVe';
import { gerarDadosSemaforo, HISTORIAS_SEMAFORO } from '../dados';
import { renderTelaSemaforo } from './telaSemaforo';

const DADOS = gerarDadosSemaforo();
const idDe = (h: { nome: string; uf: string }): number => DADOS.municipios.find((m) => m.nome === h.nome && m.uf === h.uf)!.id;

async function abrir(): Promise<void> {
  renderTelaSemaforo('/integra/semaforo/comite');
  await screen.findByText('Comitê de Satisfação');
}

const cartoes = (): HTMLElement[] => within(screen.getByRole('list', { name: /Municípios do ciclo 2026\.6/ })).getAllByRole('article');
const cartao = (nome: string): HTMLElement => screen.getByRole('article', { name: nome });

describe('Comitê', { timeout: 20000 }, () => {
  test('título, aviso de quem vê na versão real e o "sem dado" explicado', async () => {
    await abrir();
    expect(screen.getByRole('heading', { level: 1, name: 'Comitê de Satisfação' })).toBeInTheDocument();
    expect(screen.getByText(QUEM_VE.comite.aviso)).toBeInTheDocument();
    const semDado = screen.getByText(/^Sem dado:/);
    expect(semDado).toHaveTextContent(/fica fora da regra/);
    expect(semDado).toHaveTextContent(/20\/12\/2026/);
    // O ciclo vem com os meses: no ICA, o mesmo formato quer dizer semestre.
    const intro = screen.getByText(/^A cor sugerida sai da regra do Semáforo/);
    expect(intro).toHaveTextContent('com os dados do ciclo 2026.6 (novembro e dezembro de 2026) até hoje');
    expect(intro).toHaveTextContent('publicada no ciclo 2026.5 (setembro e outubro de 2026)');
  });

  test('resumo das cores sugeridas, com o nome e o número', async () => {
    await abrir();
    const resumo = screen.getByRole('list', { name: 'Cores sugeridas no ciclo 2026.6' });
    expect(resumo).toHaveTextContent('Vermelho: 2');
    expect(resumo).toHaveTextContent('Amarelo: 8');
    expect(resumo).toHaveTextContent('Verde: 78');
  });

  test('lista com o pior primeiro: cor sugerida escrita, o motivo, a seta e a decisão do ciclo', async () => {
    await abrir();
    const todos = cartoes();
    expect(todos).toHaveLength(88);
    expect(todos[0]).toBe(cartao('Horizonte-CE'));
    const horizonte = cartao('Horizonte-CE');
    expect(horizonte).toHaveTextContent('Sugerida: Vermelho');
    expect(horizonte).toHaveTextContent('Ocorrências via Relacionamento ou distribuidor em vermelho');
    expect(horizonte).toHaveTextContent('▲ Piorou: era amarelo');
    expect(horizonte).toHaveTextContent('Decisão deste ciclo: Vermelho, publicada em 02/12/2026');
  });

  test('em recuperação com o ciclo em andamento: segue amarelo; o cartão diz o que ficou sem dado', async () => {
    await abrir();
    const sobral = cartao('Sobral-CE');
    expect(sobral).toHaveTextContent('Sugerida: Amarelo');
    expect(sobral).toHaveTextContent(
      'Amarelo, em recuperação: 1 de 2 ciclos sem alerta para voltar ao verde. O ciclo em andamento só conta quando fechar.',
    );
    expect(sobral).not.toHaveTextContent('Melhorou');
    expect(sobral).toHaveTextContent('Sem dado neste ciclo, fora da regra: Média da pesquisa do articulador');
    expect(sobral).toHaveTextContent('Ainda sem decisão neste ciclo. Em vigor: Amarelo');
  });

  test('filtro por cor sugerida', async () => {
    await abrir();
    await userEvent.click(screen.getByRole('radio', { name: /Amarelo/ }));
    expect(cartoes()).toHaveLength(8);
    expect(cartao('Sobral-CE')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: /Vermelho/ }));
    // Jequié segue vermelho: não respondeu a pesquisa em 2026.4 e 2026.5, e o ciclo atual ainda não fechou.
    expect(cartoes().map((c) => within(c).getByRole('heading').textContent)).toEqual(['Horizonte-CE', 'Jequié-BA']);
    await userEvent.click(screen.getByRole('radio', { name: /Todas/ }));
    expect(cartoes()).toHaveLength(88);
  });

  test('confirmar a cor sugerida publica a decisão com a data de hoje', async () => {
    await abrir();
    await userEvent.click(within(cartao('Afrânio-PE')).getByRole('button', { name: /Confirmar Amarelo/ }));
    expect(screen.getByRole('status')).toHaveTextContent('Publicado: Afrânio-PE em Amarelo.');
    expect(cartao('Afrânio-PE')).toHaveTextContent('Decisão deste ciclo: Amarelo, publicada em 07/12/2026');
  });

  test('alterar a cor exige a justificativa escrita', async () => {
    await abrir();
    await userEvent.click(within(cartao('Sobral-CE')).getByRole('button', { name: /Alterar a cor/ }));
    const sobral = cartao('Sobral-CE');
    await userEvent.click(within(sobral).getByRole('radio', { name: 'Verde' }));
    await userEvent.click(within(sobral).getByRole('button', { name: 'Publicar a cor alterada' }));
    expect(within(sobral).getByRole('alert')).toHaveTextContent('Escreva a justificativa do Comitê.');
    expect(sobral).not.toHaveTextContent('Decisão deste ciclo');

    await userEvent.type(within(sobral).getByLabelText('Justificativa do Comitê'), 'A Secretaria já mandou a pesquisa e está tudo em dia.');
    await userEvent.click(within(sobral).getByRole('button', { name: 'Publicar a cor alterada' }));
    const depois = cartao('Sobral-CE');
    expect(depois).toHaveTextContent('Decisão deste ciclo: Verde, publicada em 07/12/2026');
    expect(depois).toHaveTextContent('Justificativa: A Secretaria já mandou a pesquisa e está tudo em dia.');
    expect(screen.getByRole('status')).toHaveTextContent('Publicado: Sobral-CE em Verde.');
  });

  test('o nome do município abre a ficha', async () => {
    await abrir();
    expect(within(cartao('Horizonte-CE')).getByRole('link', { name: 'Horizonte-CE' })).toHaveAttribute(
      'href',
      `/integra/semaforo/municipio/${idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje)}`,
    );
  });
});
