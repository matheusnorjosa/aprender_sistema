/**
 * Semáforo — Relatório mensal e formulários (ocorrência, reunião de escuta com o momento reservado,
 * observação de formação). O que é registrado entra no estado da sessão e muda a cor sugerida na hora.
 * DADOS SIMULADOS.
 */
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent, { type UserEvent } from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import * as exportar from '../../ica/exportar';
import { QUEM_VE } from '../../quemVe';
import RelatorioMensal from '../RelatorioMensal';
import { SemaforoDemoProvider } from '../SemaforoDemoContext';
import { avaliarMunicipio, gerarDadosSemaforo } from '../dados';
import { renderTelaSemaforo } from './telaSemaforo';

const DADOS = gerarDadosSemaforo();

/** Verde em vigor e sugerido, com coordenador e sem ocorrência no trimestre. */
const VERDE = (() => {
  const m = DADOS.municipios.find((x) => {
    const s = avaliarMunicipio(DADOS, x.id);
    const atual = s.ciclos.at(-1)?.resultado;
    return x.coordenador !== null && s.cor_vigente === 'verde' && atual?.cor === 'verde' && atual.limpo;
  });
  if (!m) throw new Error('sem município verde');
  return m;
})();
const NOME = `${VERDE.nome}-${VERDE.uf}`;
const SEM_COORDENADOR = DADOS.municipios.find((m) => m.coordenador === null)!;

function renderizar(): void {
  render(
    <MemoryRouter>
      <SemaforoDemoProvider>
        <RelatorioMensal />
      </SemaforoDemoProvider>
    </MemoryRouter>,
  );
}

const secao = (nome: string): HTMLElement => screen.getByRole('region', { name: nome });

async function escolher(user: UserEvent, id: number): Promise<void> {
  await user.selectOptions(await screen.findByLabelText('Município'), String(id));
}

describe('Semáforo — Relatório mensal e formulários', { timeout: 20000 }, () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('título, quem vê na versão real, o aviso do momento reservado e o link para a ficha', async () => {
    const user = userEvent.setup();
    renderizar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Relatório mensal e formulários' })).toBeInTheDocument();
    expect(screen.getByText(QUEM_VE['relatorio-mensal'].aviso)).toBeInTheDocument();
    // O momento reservado: o coordenador do município também nunca vê (Para validar, matriz "Quem vê o quê").
    const reservado = screen.getByText(/o momento reservado é confidencial/);
    expect(reservado).toHaveTextContent(/o coordenador do município e a Gestão Operacional nunca veem/);
    expect(reservado).toHaveTextContent(/Quem vê o quê/);
    await escolher(user, VERDE.id);
    const coordenador = DADOS.coordenadores.find((c) => c.id === VERDE.coordenador)!.nome;
    expect(screen.getByText(`Coordenador: ${coordenador}`)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: `Abrir a ficha de ${NOME}` })).toHaveAttribute(
      'href',
      `/integra/semaforo/municipio/${VERDE.id}`,
    );
  });

  test('a abertura diz o que vai para a ficha e o que apaga a demonstração', async () => {
    renderizar();
    const abertura = await screen.findByText(/Os formulários que alimentam o Semáforo/);
    expect(abertura).toHaveTextContent(/o relatório, a ocorrência e a reunião aparecem na ficha do município/);
    expect(abertura).toHaveTextContent(/A observação de formação fica só na lista .Registrado nesta sessão./);
    expect(abertura).toHaveTextContent(/Sair do Semáforo ou recarregar a página apaga tudo/);
  });

  test('cada formulário diz para qual município vai registrar, ou leva ao campo do município', async () => {
    const user = userEvent.setup();
    renderizar();
    const formularios = ['Relatório mensal do coordenador', 'Ocorrência', 'Reunião de escuta', 'Observação de formação'];
    await screen.findByRole('region', { name: formularios[0] });
    for (const nome of formularios) {
      expect(within(secao(nome)).getByRole('link', { name: 'Escolha o município no topo da página' })).toHaveAttribute(
        'href',
        '#relatorio-municipio',
      );
    }
    await user.click(within(secao('Observação de formação')).getByRole('link', { name: 'Escolha o município no topo da página' }));
    expect(screen.getByLabelText('Município')).toHaveFocus();

    await escolher(user, VERDE.id);
    for (const nome of formularios) {
      expect(within(secao(nome)).getByText(`Para: ${NOME}`)).toBeInTheDocument();
      expect(within(secao(nome)).queryByRole('link', { name: /Escolha o município/ })).not.toBeInTheDocument();
    }
  });

  test('a nota da observação diz que ela vai para o PDI na DFF e que a origem fica para o dia 7', async () => {
    renderizar();
    const nota = within(await screen.findByRole('region', { name: 'Observação de formação' })).getByText(/tarefa do amarelo/);
    expect(nota).toHaveTextContent(/PDI do coordenador na Plataforma DFF/);
    expect(nota).toHaveTextContent(/Para validar no dia 7/);
  });

  test('a nota da ocorrência separa a cor sugerida (na hora) da cor em vigor (espera o Comitê)', async () => {
    renderizar();
    const nota = within(await screen.findByRole('region', { name: 'Ocorrência' })).getByText(/registram por link/);
    expect(nota).toHaveTextContent(/Uma reclamação deixa a cor sugerida em vermelho na hora/);
    expect(nota).toHaveTextContent(/a cor em vigor muda quando o Comitê publicar/);
    expect(nota).not.toHaveTextContent(/deixa o município vermelho na hora/);
  });

  test('as datas da ocorrência e da reunião ficam no ciclo atual (o ciclo publicado não muda)', async () => {
    renderizar();
    for (const [secaoNome, rotulo] of [['Ocorrência', 'Data'], ['Reunião de escuta', 'Data']] as const) {
      const campo = within(await screen.findByRole('region', { name: secaoNome })).getByLabelText(rotulo);
      expect(campo).toHaveAttribute('min', '2026-11-01');
      expect(campo).toHaveAttribute('max', '2026-12-07');
    }
  });

  test('ocorrência com data de um ciclo já publicado: recusa com o motivo', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    const data = within(form).getByLabelText('Data');
    await user.clear(data);
    await user.type(data, '2026-09-03');
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    expect(within(form).getByRole('alert')).toHaveTextContent('A data precisa ser do ciclo atual: de 01/11/2026 até hoje (07/12/2026).');
  });

  test('observação de formação com data antes do ciclo atual: recusa com o mesmo motivo dos outros formulários', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Observação de formação');
    const data = within(form).getByLabelText('Data');
    expect(data).toHaveAttribute('min', '2026-11-01');
    await user.clear(data);
    await user.type(data, '2020-01-01');
    await user.type(within(form).getByLabelText('O que foi observado'), 'Turma participativa.');
    await user.click(within(form).getByRole('button', { name: 'Registrar observação' }));
    expect(within(form).getByRole('alert')).toHaveTextContent('A data precisa ser do ciclo atual: de 01/11/2026 até hoje (07/12/2026).');
    expect(screen.queryByRole('list', { name: 'Registrado nesta sessão' })).toBeNull();
  });

  test('relatório mensal com formações que não aconteceram: o cronograma cai e a cor muda na hora', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-12');
    await user.type(within(form).getByLabelText('Formações previstas'), '6');
    await user.type(within(form).getByLabelText('Formações realizadas'), '0');
    await user.type(within(form).getByLabelText('Visitas previstas'), '3');
    await user.type(within(form).getByLabelText('Visitas realizadas'), '0');
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));

    const resultado = within(form).getByRole('status');
    expect(resultado).toHaveTextContent(`Relatório de 12/2026 registrado para ${NOME}`);
    expect(resultado).toHaveTextContent(/Antes: Verde → Agora: (Amarelo|Vermelho)/);
    expect(resultado).toHaveTextContent(/Cronograma cumprido/);
  });

  test('relatório de município sem coordenador: explica o motivo', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, SEM_COORDENADOR.id);
    const form = secao('Relatório mensal do coordenador');
    for (const rotulo of ['Formações previstas', 'Formações realizadas', 'Visitas previstas', 'Visitas realizadas']) {
      await user.type(within(form).getByLabelText(rotulo), '1');
    }
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));
    expect(within(form).getByRole('alert')).toHaveTextContent('Este município ainda não tem coordenador.');
  });

  test('ocorrência leve pelo Relacionamento: verde vira amarelo', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    await user.selectOptions(within(form).getByLabelText('Tipo'), 'leve');
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    const resultado = within(form).getByRole('status');
    expect(resultado).toHaveTextContent('Antes: Verde → Agora: Amarelo');
    expect(resultado).toHaveTextContent(/Seria enviado para: .+ \(gestora de referência\), .+ \(coordenador\), SPE/);
  });

  test('reunião de escuta com reclamação no momento reservado: vermelho imediato e a Gestão Operacional fora do alerta', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Reunião de escuta');
    await user.type(within(form).getByLabelText('O que ficou combinado'), 'Agenda de 2027 combinada.');
    const reservado = within(form).getByRole('group', { name: 'Momento reservado' });
    await user.selectOptions(within(reservado).getByLabelText(/Queixa no momento reservado/), 'reclamacao');
    await user.click(within(form).getByRole('button', { name: 'Registrar reunião' }));

    const resultado = within(form).getByRole('status');
    expect(resultado).toHaveTextContent(`Reunião de escuta registrada para ${NOME}`);
    expect(resultado).toHaveTextContent('Antes: Verde → Agora: Vermelho');
    expect(resultado).toHaveTextContent(/Gestão Operacional não recebe/);
    // A reunião e a queixa entram no estado da sessão (a ficha lê de lá); a tela lista o que foi feito.
    expect(screen.getByRole('list', { name: 'Registrado nesta sessão' })).toHaveTextContent(/Reunião de escuta/);
  });

  test('observação de formação: valida o texto e entra na lista da sessão', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Observação de formação');
    await user.click(within(form).getByRole('button', { name: 'Registrar observação' }));
    expect(within(form).getByRole('alert')).toHaveTextContent('Escreva o que foi observado.');
    await user.click(within(form).getByLabelText('Com pontos a melhorar'));
    await user.type(within(form).getByLabelText('O que foi observado'), 'Turma participativa; faltou material.');
    await user.click(within(form).getByRole('button', { name: 'Registrar observação' }));
    expect(screen.getByRole('list', { name: 'Registrado nesta sessão' })).toHaveTextContent(
      /Observação de formação .*Com pontos a melhorar/,
    );
  });

  test('a lista do que foi registrado continua depois de ir à ficha e voltar (fica no estado da sessão)', async () => {
    const user = userEvent.setup();
    renderTelaSemaforo('/integra/semaforo/relatorio-mensal');
    await escolher(user, VERDE.id);
    await user.click(within(secao('Ocorrência')).getByRole('button', { name: 'Registrar ocorrência' }));
    const form = secao('Observação de formação');
    await user.type(within(form).getByLabelText('O que foi observado'), 'Turma participativa.');
    await user.click(within(form).getByRole('button', { name: 'Registrar observação' }));

    await user.click(screen.getByRole('link', { name: `Abrir a ficha de ${NOME}` }));
    await screen.findByRole('heading', { level: 1, name: 'Ficha do município' });
    await user.click(screen.getByRole('link', { name: 'Relatório mensal' }));

    const lista = await screen.findByRole('list', { name: 'Registrado nesta sessão' });
    expect(lista).toHaveTextContent(/Ocorrência leve/);
    expect(lista).toHaveTextContent(/Observação de formação .*Turma participativa\./);
  });

  test('baixar planilha: os relatórios mensais do ciclo atual', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Baixar planilha/ }));
    const [nome, cabecalho, linhas] = baixar.mock.calls[0]!;
    expect(nome).toBe('semaforo_relatorios_2026.6.csv');
    expect(cabecalho).toEqual(expect.arrayContaining(['Mês', 'Município', 'Coordenador', 'Formações previstas', 'Cumprido (%)']));
    expect(linhas).toHaveLength(DADOS.relatorios.filter((r) => r.mes === '2026-11' || r.mes === '2026-12').length);
  });
});
