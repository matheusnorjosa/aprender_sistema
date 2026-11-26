/**
 * Semáforo — Relatório mensal e formulários (ocorrência, reunião de escuta com o momento reservado) e a
 * observação de formação, lida da DFF (decisão 94). O que é registrado entra no estado da sessão e muda a cor
 * sugerida na hora. DADOS SIMULADOS.
 */
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent, { type UserEvent } from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import * as exportar from '../../ica/exportar';
import { QUEM_VE } from '../../quemVe';
import RelatorioMensal from '../RelatorioMensal';
import { SemaforoDemoProvider } from '../SemaforoDemoContext';
import { avaliarMunicipio, doSistema, gerarDadosSemaforo } from '../dados';
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

/** Rodada 3: a hora do registro começa vazia (nada de 09:00 inventado); quem registra informa. */
async function informarHora(user: UserEvent, form: HTMLElement, hora = '10:00', rotulo = 'Hora'): Promise<void> {
  const campo = within(form).getByLabelText(rotulo);
  await user.clear(campo);
  await user.type(campo, hora);
}

/** Decisão 81: o número vem preenchido do sistema; o coordenador apaga e escreve outro. */
async function trocarNumero(user: UserEvent, form: HTMLElement, rotulo: string, valor: string): Promise<void> {
  const campo = within(form).getByLabelText(rotulo);
  await user.clear(campo);
  await user.type(campo, valor);
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
    // Decisão 78: o momento reservado é lido só pela gestora de referência principal, pela Líder do NFP e pela SPE.
    const reservado = screen.getByText(/o momento reservado é confidencial/);
    expect(reservado).toHaveTextContent(
      /só a gestora de referência principal do município, a Líder do NFP e a SPE leem o que for registrado aqui; ninguém mais/,
    );
    await escolher(user, VERDE.id);
    const coordenador = DADOS.coordenadores.find((c) => c.id === VERDE.coordenador)!.nome;
    // Decisão 46: o coordenador é do projeto.
    expect(screen.getByRole('list', { name: `Projetos de ${NOME}` })).toHaveTextContent(`${VERDE.projetos[0]!.nome}: coordenador ${coordenador}`);
    expect(screen.getByRole('link', { name: `Abrir a ficha de ${NOME}` })).toHaveAttribute(
      'href',
      `/integra/semaforo/municipio/${VERDE.id}`,
    );
  });

  test('a abertura diz o que vai para a ficha e o que apaga a demonstração', async () => {
    renderizar();
    const abertura = await screen.findByText(/Os formulários que alimentam o Semáforo/);
    expect(abertura).toHaveTextContent(/o relatório, a ocorrência e a reunião aparecem na ficha do município/);
    // Decisão 94: a observação de formação não é registrada aqui; vem da DFF.
    expect(abertura).toHaveTextContent(/A observação de formação vem da DFF, só para leitura/);
    expect(abertura).toHaveTextContent(/Sair do Semáforo ou recarregar a página apaga tudo/);
    // Decisão 48: a reunião de escuta é marcada antes, então é a única data que pode passar de hoje.
    expect(abertura).toHaveTextContent(/até hoje; só a reunião de escuta pode ser marcada para depois de hoje/);
  });

  test('cada formulário diz para qual município vai registrar, ou leva ao campo do município', async () => {
    const user = userEvent.setup();
    renderizar();
    // Decisão 94: são 4 formulários; a observação de formação vem da DFF.
    const formularios = ['Relatório mensal do coordenador', 'Ocorrência', 'Marcar a reunião de escuta', 'Ata da reunião de escuta'];
    await screen.findByRole('region', { name: formularios[0] });
    for (const nome of formularios) {
      expect(within(secao(nome)).getByRole('link', { name: 'Escolha o município no topo da página' })).toHaveAttribute(
        'href',
        '#relatorio-municipio',
      );
    }
    await user.click(within(secao('Ata da reunião de escuta')).getByRole('link', { name: 'Escolha o município no topo da página' }));
    expect(screen.getByLabelText('Município')).toHaveFocus();

    await escolher(user, VERDE.id);
    for (const nome of formularios) {
      expect(within(secao(nome)).getByText(`Para: ${NOME}`)).toBeInTheDocument();
      expect(within(secao(nome)).queryByRole('link', { name: /Escolha o município/ })).not.toBeInTheDocument();
    }
  });

  test('decisão 94: a observação de formação é registrada na DFF, junto do PDI; aqui ela só é lida', async () => {
    renderizar();
    const observacao = await screen.findByRole('region', { name: 'Observação de formação' });
    expect(within(observacao).getByText('A observação de formação é registrada na DFF, junto do PDI; o sistema lê de lá.')).toBeInTheDocument();
    expect(observacao).not.toHaveTextContent(/Para validar no dia 7/);
  });

  test('decisões 38 e 50: a nota da ocorrência diz que a reclamação muda a cor em vigor na hora e pede a resposta', async () => {
    renderizar();
    const nota = within(await screen.findByRole('region', { name: 'Ocorrência' })).getByText(/registram por link/);
    expect(nota).toHaveTextContent(/Uma reclamação deixa o município vermelho na hora: a cor em vigor muda e as tarefas do vermelho começam/);
    expect(nota).toHaveTextContent(/o Comitê confirma ou desfaz depois/);
    expect(nota).toHaveTextContent(/meta de 48 h corridas/);
    // Depois que o Comitê desfaz o vermelho, o mesmo motivo não muda a cor de novo.
    expect(nota).toHaveTextContent(/salvo se o Comitê já desfez o vermelho por esse mesmo motivo/);
    expect(nota).not.toHaveTextContent(/a cor em vigor muda quando o Comitê publicar/);
  });

  test('as datas da ocorrência e da reunião ficam no ciclo atual (o ciclo publicado não muda)', async () => {
    renderizar();
    const campo = within(await screen.findByRole('region', { name: 'Ocorrência' })).getByLabelText('Data');
    expect(campo).toHaveAttribute('min', '2026-11-01');
    expect(campo).toHaveAttribute('max', '2026-12-07');
    // Decisão 48: a reunião é marcada antes; a data pode ser depois de hoje.
    const marcar = within(screen.getByRole('region', { name: 'Marcar a reunião de escuta' })).getByLabelText('Data da reunião');
    expect(marcar).toHaveAttribute('min', '2026-11-01');
    expect(marcar).not.toHaveAttribute('max');
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

  test('decisão 94: a observação de formação não tem formulário aqui (nem data, nem texto, nem botão)', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const observacao = secao('Observação de formação');
    expect(within(observacao).queryByRole('textbox')).not.toBeInTheDocument();
    expect(within(observacao).queryByLabelText('Data')).not.toBeInTheDocument();
    expect(within(observacao).queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Registrar observação' })).not.toBeInTheDocument();
  });

  test('relatório mensal com formações que não aconteceram: o cronograma cai e a cor muda na hora', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-12');
    // Decisões 81 e 82: as formações vêm do sistema (o coordenador muda e justifica); as visitas, só leitura.
    await trocarNumero(user, form, 'Formações previstas', '6');
    await trocarNumero(user, form, 'Formações realizadas', '0');
    await user.type(within(form).getByLabelText(/^Justificativa/), 'A Secretaria suspendeu as formações do mês.');
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));

    const resultado = within(form).getByRole('status');
    expect(resultado).toHaveTextContent(`Relatório de 12/2026 registrado para ${NOME}, projeto ${VERDE.projetos[0]!.nome}`);
    expect(resultado).toHaveTextContent(/Antes: Verde → Agora: (Amarelo|Vermelho)/);
    expect(resultado).toHaveTextContent(/Cronograma cumprido/);
  });

  test('decisão 57: o mês já entregue avisa que mandar de novo corrige, e que a versão anterior fica guardada', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-11');
    expect(within(form).getByText(/^Já entregue para 11\/2026 neste projeto/)).toHaveTextContent(
      'Mandar de novo corrige o relatório: vale o novo, e o anterior fica guardado.',
    );
  });

  test('relatório de município sem coordenador: explica o motivo', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, SEM_COORDENADOR.id);
    const form = secao('Relatório mensal do coordenador');
    // Sem coordenador, o sistema não traz números (decisão 81); as visitas não são digitadas (decisão 82).
    for (const rotulo of ['Formações previstas', 'Formações realizadas']) {
      expect(within(form).getByLabelText(rotulo)).toHaveValue(null);
      await user.type(within(form).getByLabelText(rotulo), '1');
    }
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));
    // Decisão 46: o relatório é por projeto; o único projeto de Itaquiraí-MS ainda não tem coordenador.
    expect(within(form).getByRole('alert')).toHaveTextContent('Este projeto ainda não tem coordenador.');
  });

  test('ocorrência leve pelo Relacionamento: verde vira amarelo', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    await user.selectOptions(within(form).getByLabelText('Tipo'), 'leve');
    await informarHora(user, form);
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    const resultado = within(form).getByRole('status');
    expect(resultado).toHaveTextContent('Antes: Verde → Agora: Amarelo');
    expect(resultado).toHaveTextContent(/Seria enviado no sistema e por e-mail institucional para: .+ \(gestora de referência\), .+ \(coordenador\), SPE/);
  });

  test('decisão 46: o aviso de piora para amarelo vai para os coordenadores de todos os projetos do município', async () => {
    const user = userEvent.setup();
    const DOIS = DADOS.municipios.find((x) => {
      const s = avaliarMunicipio(DADOS, x.id);
      const atual = s.ciclos.at(-1)?.resultado;
      const coordenadores = new Set(x.projetos.flatMap((p) => (p.coordenador === null ? [] : [p.coordenador])));
      return coordenadores.size > 1 && s.cor_vigente === 'verde' && atual?.cor === 'verde' && atual.limpo;
    })!;
    const nomes = [...new Set(DOIS.projetos.map((p) => p.coordenador))].map((id) => DADOS.coordenadores.find((c) => c.id === id)!.nome);
    renderizar();
    await escolher(user, DOIS.id);
    const form = secao('Ocorrência');
    await user.selectOptions(within(form).getByLabelText('Tipo'), 'leve');
    await informarHora(user, form);
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    const resultado = within(form).getByRole('status');
    expect(resultado).toHaveTextContent('Antes: Verde → Agora: Amarelo');
    expect(resultado).toHaveTextContent(`${nomes.map((n) => `${n} (coordenador)`).join(', ')}, SPE`);
  });

  test('decisões 38 e 39: o retorno só diz "com este registro" quando foi este registro que mudou a cor em vigor', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    await user.selectOptions(within(form).getByLabelText('Tipo'), 'reclamacao');
    await informarHora(user, form);
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    expect(within(form).getByRole('status')).toHaveTextContent(
      'Cor em vigor: Vermelho. Mudou na hora com este registro: as tarefas do vermelho começaram em 07/12/2026.',
    );
    // Um registro leve depois: o vermelho na hora já valia, e o retorno não diz que foi este registro.
    await user.selectOptions(within(form).getByLabelText('Tipo'), 'leve');
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    const segundo = within(form).getByRole('status');
    expect(segundo).toHaveTextContent(
      'Cor em vigor: Vermelho, na hora desde 07/12/2026: as tarefas do vermelho começaram nessa data. O Comitê confirma ou desfaz depois.',
    );
    expect(segundo).not.toHaveTextContent('com este registro');
  });

  test('decisões 38 e 42: depois que o Comitê desfez o vermelho, o retorno do registro diz que o mesmo alerta não muda a cor de novo', async () => {
    const user = userEvent.setup();
    const naHora = { municipio: VERDE.id, ciclo: '2026.6', cor_sugerida: 'vermelho' as const, justificativa: null };
    const DESFEITO = {
      ...DADOS,
      ocorrencias: [
        ...DADOS.ocorrencias,
        {
          id: 9001,
          municipio: VERDE.id,
          data: '2026-12-01',
          registrada_em: '2026-12-01T09:00:00-03:00',
          respondida_em: null,
          origem: 'fluxo_unico' as const,
          tipo: 'reclamacao' as const,
        },
      ],
      decisoes: [
        ...DADOS.decisoes,
        { ...naHora, cor_publicada: 'vermelho' as const, publicada_em: '2026-12-01', origem: 'vermelho_automatico' as const },
        {
          ...naHora,
          cor_publicada: 'amarelo' as const,
          justificativa: 'A reclamação foi resolvida.',
          publicada_em: '2026-12-02',
          origem: 'comite_extraordinario' as const,
        },
      ],
    };
    render(
      <MemoryRouter>
        <SemaforoDemoProvider dados={DESFEITO}>
          <RelatorioMensal />
        </SemaforoDemoProvider>
      </MemoryRouter>,
    );
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    await user.selectOptions(within(form).getByLabelText('Tipo'), 'leve');
    await informarHora(user, form);
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    const resultado = within(form).getByRole('status');
    expect(resultado).toHaveTextContent('Antes: Vermelho → Agora: Vermelho');
    expect(resultado).toHaveTextContent(
      'Cor em vigor: Amarelo. O Comitê desfez o vermelho em 02/12/2026: o mesmo alerta não muda a cor em vigor de novo; só um alerta novo (outro indicador, ou um que piore) muda.',
    );
    expect(resultado).not.toHaveTextContent('Só o vermelho muda a cor em vigor na hora');
  });

  test('rodada 5: trocar o município limpa o retorno do registro anterior (o erro já resolvido e o "antes → agora" do outro)', async () => {
    const user = userEvent.setup();
    renderizar();
    const form = await screen.findByRole('region', { name: 'Relatório mensal do coordenador' });
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));
    expect(within(form).getByRole('alert')).toHaveTextContent('Escolha um município da lista.');
    await escolher(user, VERDE.id);
    expect(within(form).queryByRole('alert')).not.toBeInTheDocument();

    const ocorrencia = secao('Ocorrência');
    await informarHora(user, ocorrencia);
    await user.click(within(ocorrencia).getByRole('button', { name: 'Registrar ocorrência' }));
    expect(within(ocorrencia).getByRole('status')).toHaveTextContent(`Ocorrência registrada para ${NOME}`);
    await escolher(user, SEM_COORDENADOR.id);
    expect(within(ocorrencia).getByRole('status')).toBeEmptyDOMElement();
  });

  test('rodada 5: o retorno de um registro não ganha a piora causada por outro registro depois (fica só o último)', async () => {
    const user = userEvent.setup();
    const maringa = DADOS.municipios.find((m) => m.nome === 'Maringá' && m.uf === 'PR')!;
    renderizar();
    await escolher(user, maringa.id);
    const relatorio = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(relatorio).getByLabelText('Projeto'), String(maringa.projetos[0]!.id));
    await user.selectOptions(within(relatorio).getByLabelText('Mês'), '2026-12');
    // Decisão 81: o coordenador confere os números que vieram do sistema e manda sem mudar.
    await user.click(within(relatorio).getByRole('button', { name: 'Registrar relatório' }));
    expect(within(relatorio).getByRole('status')).toHaveTextContent('Relatório de 12/2026 registrado para Maringá-PR');

    // A segunda ocorrência leve no ano dá vermelho na hora (decisão 38): o alerta é do registro da ocorrência.
    const ocorrencia = secao('Ocorrência');
    await informarHora(user, ocorrencia);
    await user.click(within(ocorrencia).getByRole('button', { name: 'Registrar ocorrência' }));
    expect(within(ocorrencia).getByRole('status')).toHaveTextContent('Alerta: Maringá-PR passou para vermelho');
    expect(within(relatorio).getByRole('status')).toBeEmptyDOMElement();
    expect(screen.getAllByText(/passou para vermelho/)).toHaveLength(1);
  });

  test('rodada 5: a periodicidade da reunião marcada vem da cor em vigor, como nos dados simulados', async () => {
    const user = userEvent.setup();
    const horizonte = DADOS.municipios.find((m) => m.nome === 'Horizonte' && m.uf === 'CE')!;
    renderizar();
    const marcar = await screen.findByRole('region', { name: 'Marcar a reunião de escuta' });
    expect(within(marcar).queryByRole('combobox', { name: 'Periodicidade' })).not.toBeInTheDocument();
    await escolher(user, VERDE.id);
    expect(within(marcar).getByText(/^Periodicidade:/)).toHaveTextContent('Periodicidade: semestral, pela cor em vigor (Verde).');
    await escolher(user, horizonte.id);
    expect(within(marcar).getByText(/^Periodicidade:/)).toHaveTextContent('Periodicidade: trimestral, pela cor em vigor (Vermelho).');
    // Horizonte-CE já tem a reunião de 04/12: hoje fica a menos de 30 dias dela.
    await user.click(within(marcar).getByRole('button', { name: 'Marcar a reunião' }));
    expect(within(marcar).getByRole('alert')).toHaveTextContent('Já há uma reunião de escuta em 04/12/2026, a menos de 30 dias desta data.');
  });

  test('decisão 48: a reunião é marcada antes; a ata só depois do dia da reunião', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const marcar = secao('Marcar a reunião de escuta');
    const data = within(marcar).getByLabelText('Data da reunião');
    await user.clear(data);
    await user.type(data, '2026-12-15');
    await user.click(within(marcar).getByRole('button', { name: 'Marcar a reunião' }));
    expect(within(marcar).getByRole('status')).toHaveTextContent(`Reunião de escuta marcada para 15/12/2026 (${NOME}). A ata vai até 5 dias úteis depois.`);

    const ata = secao('Ata da reunião de escuta');
    const reuniao = within(ata).getByLabelText('Reunião');
    await user.selectOptions(reuniao, within(reuniao).getByRole('option', { name: '15/12/2026 · agendada' }));
    await user.type(within(ata).getByLabelText('O que ficou combinado'), 'Agenda combinada.');
    await user.click(within(ata).getByRole('button', { name: 'Registrar a ata' }));
    expect(within(ata).getByRole('alert')).toHaveTextContent('A ata só pode ser registrada no dia da reunião ou depois (15/12/2026).');
  });

  test('decisão 48: a reunião sem ata passado o prazo aparece como ata atrasada', async () => {
    const user = userEvent.setup();
    const sobral = DADOS.municipios.find((m) => m.nome === 'Sobral')!;
    renderizar();
    await escolher(user, sobral.id);
    const reuniao = within(secao('Ata da reunião de escuta')).getByLabelText('Reunião');
    expect(within(reuniao).getByRole('option', { name: '27/11/2026 · ata atrasada (o prazo era 04/12/2026)' })).toBeInTheDocument();
  });

  test('decisões 48 e 50 (rodada 3): a queixa do momento reservado conta o tempo de resposta do registro da ata, não da reunião às 09:00', async () => {
    const user = userEvent.setup();
    const sobral = DADOS.municipios.find((m) => m.nome === 'Sobral')!;
    renderizar();
    await escolher(user, sobral.id);
    const form = secao('Ata da reunião de escuta');
    const reuniao = within(form).getByLabelText('Reunião');
    await user.selectOptions(reuniao, within(reuniao).getByRole('option', { name: /^27\/11\/2026/ }));
    await user.type(within(form).getByLabelText('O que ficou combinado'), 'Agenda combinada.');
    const reservado = within(form).getByRole('group', { name: 'Momento reservado' });
    // Sem queixa, a hora não aparece; com queixa, ela é pedida e começa vazia.
    expect(within(reservado).queryByLabelText('Hora deste registro')).not.toBeInTheDocument();
    await user.selectOptions(within(reservado).getByLabelText(/Queixa no momento reservado/), 'leve');
    expect(within(reservado).getByLabelText('Hora deste registro')).toHaveValue('');
    await user.click(within(form).getByRole('button', { name: 'Registrar a ata' }));
    expect(within(form).getByRole('alert')).toHaveTextContent('Informe a hora deste registro (horas e minutos).');
    // A ata não entrou sem a hora da queixa: a reunião continua entre as que estão sem ata.
    expect(within(reuniao).getByRole('option', { name: /^27\/11\/2026/ })).toBeInTheDocument();

    await informarHora(user, reservado, '15:20', 'Hora deste registro');
    await user.click(within(form).getByRole('button', { name: 'Registrar a ata' }));
    expect(within(form).getByRole('status')).toHaveTextContent('Ata da reunião de 27/11/2026 registrada para Sobral-CE');
    // A queixa chega hoje, às 15:20: é daí que conta o tempo de resposta.
    const pendentes = within(secao('Ocorrência')).getByRole('list', { name: 'Ocorrências sem resposta de Sobral-CE' });
    expect(pendentes).toHaveTextContent('07/12/2026 às 15:20 · Leve');
    expect(pendentes).not.toHaveTextContent('27/11/2026 às 09:00');
  });

  test('ata com reclamação no momento reservado: vermelho imediato, e o alerta leva só a cor, sem o que foi dito (rodada 3)', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    // Marca para hoje e registra a ata no mesmo dia.
    await user.click(within(secao('Marcar a reunião de escuta')).getByRole('button', { name: 'Marcar a reunião' }));
    const form = secao('Ata da reunião de escuta');
    const reuniao = within(form).getByLabelText('Reunião');
    await user.selectOptions(reuniao, within(reuniao).getByRole('option', { name: /^07\/12\/2026/ }));
    await user.type(within(form).getByLabelText('O que ficou combinado'), 'Agenda de 2027 combinada.');
    const reservado = within(form).getByRole('group', { name: 'Momento reservado' });
    await user.selectOptions(within(reservado).getByLabelText(/Queixa no momento reservado/), 'reclamacao');
    await informarHora(user, reservado, '16:10', 'Hora deste registro');
    await user.click(within(form).getByRole('button', { name: 'Registrar a ata' }));

    const resultado = within(form).getByRole('status');
    expect(resultado).toHaveTextContent(`Ata da reunião de 07/12/2026 registrada para ${NOME}`);
    expect(resultado).toHaveTextContent('Antes: Verde → Agora: Vermelho');
    // Rodada 3: a Gestão Operacional nunca esteve entre os destinatários; o que fica de fora é o conteúdo da queixa.
    expect(resultado).not.toHaveTextContent(/Gestão Operacional não recebe este alerta/);
    // Decisão 78: só a gestora de referência principal, a Líder do NFP e a SPE leem a queixa.
    expect(resultado).toHaveTextContent(
      'O alerta diz só a cor: o que foi dito no momento reservado não vai junto; a queixa só é lida pela gestora de referência principal, pela Líder do NFP e pela SPE.',
    );
    // A reunião e a queixa entram no estado da sessão (a ficha lê de lá); a tela lista o que foi feito.
    expect(screen.getByRole('list', { name: 'Registrado nesta sessão' })).toHaveTextContent(/Ata da reunião de escuta/);
  });

  test('decisão 50 (rodada 3): a hora do registro começa vazia, como a da resposta; sem ela, o registro é recusado', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    expect(within(form).getByLabelText('Hora')).toHaveValue('');
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    expect(within(form).getByRole('alert')).toHaveTextContent('Informe a hora do registro (horas e minutos).');
    expect(within(form).queryByRole('list', { name: `Ocorrências sem resposta de ${NOME}` })).not.toBeInTheDocument();
  });

  test('decisão 50: a ocorrência guarda a hora e quando foi respondida; a resposta pode vir depois', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    const hora = within(form).getByLabelText('Hora');
    await user.clear(hora);
    await user.type(hora, '08:30');
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    expect(within(form).getByRole('status')).toHaveTextContent(`Ocorrência registrada para ${NOME}`);

    const pendentes = within(form).getByRole('list', { name: `Ocorrências sem resposta de ${NOME}` });
    const item = within(pendentes).getByRole('listitem');
    expect(item).toHaveTextContent('07/12/2026 às 08:30 · Leve');
    // Rodada 1 de revisão: o nome do campo diz de qual ocorrência é a resposta.
    const horaResposta = within(item).getByLabelText('Hora da resposta à ocorrência de 07/12/2026 às 08:30');
    await user.clear(horaResposta);
    await user.type(horaResposta, '11:00');
    await user.click(within(item).getByRole('button', { name: /Registrar a resposta/ }));
    expect(within(form).getByText('Resposta registrada: em 2 h 30 min, dentro da meta de 48 h.')).toBeInTheDocument();
    expect(within(form).queryByRole('list', { name: `Ocorrências sem resposta de ${NOME}` })).not.toBeInTheDocument();
  });

  test('decisão 50, acessibilidade: o erro da resposta fica na ocorrência, com os campos marcados, e o foco vai para o aviso', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    const hora = within(form).getByLabelText('Hora');
    await user.clear(hora);
    await user.type(hora, '08:30');
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    const pendentes = within(form).getByRole('list', { name: `Ocorrências sem resposta de ${NOME}` });
    const item = within(pendentes).getByRole('listitem');
    const dia = within(item).getByLabelText('Dia da resposta à ocorrência de 07/12/2026 às 08:30');
    const campoHora = within(item).getByLabelText('Hora da resposta à ocorrência de 07/12/2026 às 08:30');
    await user.click(within(item).getByRole('button', { name: /Registrar a resposta/ }));
    // O erro aparece dentro da ocorrência, perto do botão, e os dois campos apontam para ele.
    const erro = within(item).getByRole('alert');
    expect(erro).toHaveTextContent('Informe quando a ocorrência foi respondida (dia e hora).');
    for (const campo of [dia, campoHora]) {
      expect(campo).toHaveAttribute('aria-invalid', 'true');
      expect(campo.getAttribute('aria-describedby') ?? '').toContain(erro.id);
    }
    await user.type(campoHora, '11:00');
    await user.click(within(item).getByRole('button', { name: /Registrar a resposta/ }));
    // A ocorrência respondida sai da lista: o foco não cai no começo da página, vai para o aviso.
    expect(within(form).getByText('Resposta registrada: em 2 h 30 min, dentro da meta de 48 h.')).toHaveFocus();
  });

  test('decisão 50: a ocorrência já respondida entra com a data e a hora da resposta', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Ocorrência');
    await informarHora(user, form, '09:00');
    await user.click(within(form).getByLabelText('Já foi respondida'));
    const hora = within(form).getByLabelText('Hora da resposta');
    await user.clear(hora);
    await user.type(hora, '17:00');
    await user.click(within(form).getByRole('button', { name: 'Registrar ocorrência' }));
    expect(within(form).getByRole('status')).toHaveTextContent(`Ocorrência registrada para ${NOME}`);
    expect(within(form).queryByRole('list', { name: `Ocorrências sem resposta de ${NOME}` })).not.toBeInTheDocument();
  });

  test('decisão 46: com mais de um projeto, o relatório é de um projeto; a tela mostra o cronograma de cada um e o do município', async () => {
    const user = userEvent.setup();
    const VARIOS = DADOS.municipios.find((m) => m.projetos.length > 1 && m.projetos.every((p) => p.coordenador !== null))!;
    const segundo = VARIOS.projetos[1]!;
    renderizar();
    await escolher(user, VARIOS.id);
    const form = secao('Relatório mensal do coordenador');
    const projeto = within(form).getByLabelText('Projeto');
    expect(within(projeto).getAllByRole('option')).toHaveLength(VARIOS.projetos.length + 1);
    await user.selectOptions(projeto, String(segundo.id));
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-12');
    await trocarNumero(user, form, 'Formações previstas', '60');
    await trocarNumero(user, form, 'Formações realizadas', '0');
    await user.type(within(form).getByLabelText(/^Justificativa/), 'Formações do projeto suspensas no mês.');
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));
    expect(within(form).getByRole('status')).toHaveTextContent(`Relatório de 12/2026 registrado para ${VARIOS.nome}-${VARIOS.uf}, projeto ${segundo.nome}`);

    const cronograma = within(form).getByRole('list', { name: 'Cronograma do ciclo 2026.6 por projeto' });
    const itens = within(cronograma).getAllByRole('listitem').map((li) => li.textContent ?? '');
    expect(itens).toHaveLength(VARIOS.projetos.length);
    expect(itens[1]).toMatch(new RegExp(`^${segundo.nome}.*\\d+,\\d\\d% · Vermelho`));
    // Na cor do município entra o pior projeto.
    expect(within(form).getByText(/^Cronograma do município \(o pior projeto\):/)).toHaveTextContent(/\d+,\d\d% · Vermelho/);
  });

  test('decisão 94: as observações de formação do município aparecem como lidas da DFF, só leitura', async () => {
    const user = userEvent.setup();
    const feitas = DADOS.tarefas.filter((t) => t.chave === 'observacao_formacao' && t.concluida_em !== null);
    const municipio = DADOS.municipios.find((m) => feitas.some((t) => t.municipio === m.id))!;
    const nome = `${municipio.nome}-${municipio.uf}`;
    renderizar();
    await escolher(user, municipio.id);
    const lista = within(secao('Observação de formação')).getByRole('list', { name: `Observações de formação de ${nome}, lidas da DFF` });
    const itens = within(lista).getAllByRole('listitem');
    expect(itens).toHaveLength(feitas.filter((t) => t.municipio === municipio.id).length);
    expect(itens[0]).toHaveTextContent(/^Registrada na DFF em \d\d\/\d\d\/\d{4} \(lida da DFF\)$/);
    // Município sem observação: a tela diz que não há nenhuma.
    await escolher(user, VERDE.id);
    expect(within(secao('Observação de formação')).getByText(`Nenhuma observação de formação de ${NOME} lida da DFF.`)).toBeInTheDocument();
  });

  test('a lista do que foi registrado continua depois de ir à ficha e voltar (fica no estado da sessão)', async () => {
    const user = userEvent.setup();
    renderTelaSemaforo('/integra/semaforo/relatorio-mensal');
    await escolher(user, VERDE.id);
    await informarHora(user, secao('Ocorrência'));
    await user.click(within(secao('Ocorrência')).getByRole('button', { name: 'Registrar ocorrência' }));

    await user.click(screen.getByRole('link', { name: `Abrir a ficha de ${NOME}` }));
    await screen.findByRole('heading', { level: 1, name: 'Ficha do município' });
    await user.click(screen.getByRole('link', { name: 'Relatório mensal' }));

    const lista = await screen.findByRole('list', { name: 'Registrado nesta sessão' });
    expect(lista).toHaveTextContent(/Ocorrência leve/);
    // Decisão 94: a observação de formação não é registrada nesta tela.
    expect(lista).not.toHaveTextContent(/Observação de formação/);
  });

  test('decisões 81 e 82: o relatório vem pré-preenchido com as formações do sistema; as visitas vêm da Logística e do FRV, só leitura', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-12');
    const sistema = doSistema(DADOS, VERDE.projetos[0]!.id, '2026-12')!;
    expect(within(form).getByLabelText('Formações previstas')).toHaveValue(sistema.formacoes_previstas);
    expect(within(form).getByLabelText('Formações realizadas')).toHaveValue(sistema.formacoes_realizadas);
    expect(within(form).queryByLabelText('Visitas previstas')).not.toBeInTheDocument();
    expect(within(form).queryByLabelText('Visitas realizadas')).not.toBeInTheDocument();
    expect(within(form).getByText(/^Visitas, da Logística e do pedido de viagem \(FRV\), só leitura:/)).toHaveTextContent(
      `${sistema.visitas_realizadas} de ${sistema.visitas_previstas} realizadas`,
    );
    // Mandar sem mudar nada não pede justificativa.
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));
    expect(within(form).getByRole('status')).toHaveTextContent(`Relatório de 12/2026 registrado para ${NOME}`);
  });

  test('decisão 81: mudar um número do sistema sem justificativa é recusado; com a justificativa, entra', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-12');
    const sistema = doSistema(DADOS, VERDE.projetos[0]!.id, '2026-12')!;
    await trocarNumero(user, form, 'Formações realizadas', String(sistema.formacoes_realizadas - 1));
    const justificativa = within(form).getByLabelText(/^Justificativa/);
    expect(justificativa).toHaveAccessibleDescription(/obrigatória só se você mudar um número que veio do sistema/);
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));
    expect(within(form).getByRole('alert')).toHaveTextContent('Você mudou um número que veio do sistema: escreva a justificativa.');
    expect(within(form).getByRole('status')).toBeEmptyDOMElement();

    await user.type(justificativa, 'Uma formação foi adiada pela Secretaria.');
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));
    expect(within(form).queryByRole('alert')).not.toBeInTheDocument();
    expect(within(form).getByRole('status')).toHaveTextContent(`Relatório de 12/2026 registrado para ${NOME}`);
  });

  test('decisão 81: o relatório corrigido mostra o que foi entregue e a justificativa, na tela e na planilha', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-12');
    const sistema = doSistema(DADOS, VERDE.projetos[0]!.id, '2026-12')!;
    const entregue = sistema.formacoes_realizadas - 1;
    const motivo = 'Uma formação foi adiada pela Secretaria.';
    await trocarNumero(user, form, 'Formações realizadas', String(entregue));
    await user.type(within(form).getByLabelText(/^Justificativa/), motivo);
    await user.click(within(form).getByRole('button', { name: 'Registrar relatório' }));

    expect(within(form).getByText(/^Já entregue para 12\/2026 neste projeto/)).toHaveTextContent(`Justificativa: ${motivo}`);
    // O formulário fica com o que foi entregue: mandar de novo sem mexer não desfaz a correção sem justificativa.
    expect(within(form).getByLabelText('Formações realizadas')).toHaveValue(entregue);
    expect(within(form).getByLabelText(/^Justificativa/)).toHaveValue(motivo);

    await user.click(screen.getByRole('button', { name: /Baixar planilha/ }));
    const [, cabecalho, linhas] = baixar.mock.calls[0]!;
    const coluna = cabecalho.indexOf('Justificativa');
    expect(coluna).toBeGreaterThan(-1);
    expect(linhas.map((l) => l[coluna])).toContain(motivo);
  });

  test('decisão 77: o relatório vence no 5º dia útil do mês seguinte', async () => {
    const user = userEvent.setup();
    renderizar();
    await escolher(user, VERDE.id);
    const form = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-11');
    expect(within(form).getByText(/^Prazo do relatório de 11\/2026:/)).toHaveTextContent(
      'Prazo do relatório de 11/2026: vence em 07/12/2026 (5º dia útil do mês seguinte).',
    );
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-12');
    expect(within(form).getByText(/^Prazo do relatório de 12\/2026:/)).toHaveTextContent('vence em 07/01/2027');
    expect(form).not.toHaveTextContent(/atrasado/i);
  });

  test('decisão 77: passado o prazo sem o relatório do mês, a tela diz que está atrasado', async () => {
    const user = userEvent.setup();
    const projeto = VERDE.projetos[0]!.id;
    const ATRASADO = {
      ...DADOS,
      data_referencia: '2026-12-08',
      relatorios: DADOS.relatorios.filter((r) => !(r.projeto === projeto && r.mes === '2026-11')),
    };
    render(
      <MemoryRouter>
        <SemaforoDemoProvider dados={ATRASADO}>
          <RelatorioMensal />
        </SemaforoDemoProvider>
      </MemoryRouter>,
    );
    await escolher(user, VERDE.id);
    const form = secao('Relatório mensal do coordenador');
    await user.selectOptions(within(form).getByLabelText('Mês'), '2026-11');
    expect(within(form).getByText(/^Prazo do relatório de 11\/2026:/)).toHaveTextContent(
      'Prazo do relatório de 11/2026: vence em 07/12/2026 (5º dia útil do mês seguinte). Atrasado: ainda não foi entregue.',
    );
  });

  test('baixar planilha: os relatórios mensais do ciclo atual', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    renderizar();
    await userEvent.click(await screen.findByRole('button', { name: /Baixar planilha/ }));
    const [nome, cabecalho, linhas] = baixar.mock.calls[0]!;
    expect(nome).toBe('semaforo_relatorios_2026.6.csv');
    expect(cabecalho).toEqual(expect.arrayContaining(['Mês', 'Município', 'Projeto', 'Coordenador', 'Formações previstas', 'Cumprido (%)']));
    expect(linhas).toHaveLength(DADOS.relatorios.filter((r) => r.mes === '2026-11' || r.mes === '2026-12').length);
  });
});
