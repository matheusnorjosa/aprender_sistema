/**
 * Semáforo — Pesquisa do articulador, respondida na própria tela (sem link público). DADOS SIMULADOS.
 * Responder recalcula a cor sugerida do município na hora e mostra "antes → agora".
 */
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import userEvent, { type UserEvent } from '@testing-library/user-event';
import { afterEach, describe, expect, test, vi } from 'vitest';

import * as exportar from '../../ica/exportar';
import { QUEM_VE } from '../../quemVe';
import PesquisaArticulador from '../PesquisaArticulador';
import { SemaforoDemoProvider } from '../SemaforoDemoContext';
import { avaliarMunicipio, gerarDadosSemaforo } from '../dados';

const DADOS = gerarDadosSemaforo();

/**
 * Um município verde (em vigor e sugerido), com gestora de referência, que ainda não respondeu no ciclo: o ponto
 * de partida (decisão 51: a segunda resposta do mesmo projeto no ciclo é recusada).
 */
const VERDE = (() => {
  const m = DADOS.municipios.find((x) => {
    const s = avaliarMunicipio(DADOS, x.id);
    const respondeu = DADOS.respostas.some((r) => r.municipio === x.id && r.ciclo === DADOS.ciclo_atual);
    return !respondeu && s.cor_vigente === 'verde' && s.ciclos.at(-1)?.resultado.cor === 'verde';
  });
  if (!m) throw new Error('sem município verde');
  return m;
})();
const GESTORA = DADOS.pessoas.find((p) => p.id === VERDE.gestora_referencia)!.nome;

function renderizar(): void {
  render(
    <MemoryRouter>
      <SemaforoDemoProvider>
        <PesquisaArticulador />
      </SemaforoDemoProvider>
    </MemoryRouter>,
  );
}

/** Marca a mesma nota nos 6 itens e a nota de recomendação. */
async function responder(user: UserEvent, item: string, nps: string): Promise<void> {
  for (let i = 1; i <= 6; i++) {
    const grupo = screen.getByRole('group', { name: new RegExp(`^${i}\\.`) });
    await user.click(within(grupo).getByLabelText(item));
  }
  const recomendacao = screen.getByRole('group', { name: /recomendaria/ });
  await user.click(within(recomendacao).getByLabelText(nps));
}

describe('Semáforo — Pesquisa do articulador', { timeout: 20000 }, () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('mostra quem vê na versão real, o ciclo e o prazo, e que aqui não há link', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Pesquisa do articulador' })).toBeInTheDocument();
    expect(screen.getByText(QUEM_VE.pesquisa.aviso)).toBeInTheDocument();
    // Decisão 76: o link sai em 01/12 (1º dia útil do 2º mês) e a resposta vai até 10 dias úteis depois.
    expect(screen.getByText(/Ciclo 2026\.6/)).toHaveTextContent(
      'link enviado pela gestora de referência em 01/12/2026 · prazo para responder: 15/12/2026 (10 dias úteis)',
    );
    expect(screen.getByText(/sem link/)).toBeInTheDocument();
  });

  test('quem responde é o mesmo do começo ao fim: o articulador ou o secretário municipal', async () => {
    renderizar();
    const explicacao = await screen.findByText(/sem link/);
    expect(explicacao).toHaveTextContent(/como o articulador ou o secretário municipal veria/);
    // Decisões 73 e 74: a gestora de referência manda o link, sem o coordenador; a identificação é opcional.
    expect(explicacao).toHaveTextContent(
      /a gestora de referência manda o link a articuladores e secretários municipais, sem passar pelo coordenador/,
    );
    expect(explicacao).toHaveTextContent(/Dizer o nome é opcional/);
    expect(explicacao).not.toHaveTextContent(/o articulador recebe um link/);
  });

  test('responder mal num município verde: a cor sugerida vira vermelho na hora, com o alerta', async () => {
    const user = userEvent.setup();
    renderizar();
    await user.selectOptions(await screen.findByLabelText('Município'), String(VERDE.id));
    await responder(user, '1', '0');
    await user.type(screen.getByLabelText(/O que precisamos melhorar/), 'As formações não acontecem.');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));

    const resultado = await screen.findByRole('status');
    expect(resultado).toHaveTextContent(`Resposta registrada para ${VERDE.nome}-${VERDE.uf}`);
    expect(resultado).toHaveTextContent('Antes: Verde → Agora: Vermelho');
    expect(resultado).toHaveTextContent(/Vermelho: .*em vermelho\./);
    // Seção 8 do PDF: "Município passa a vermelho" vai para a gestora de referência, a gestora pedagógica, a SPE e a
    // Líder do NFP (a lista inteira, com o ponto final).
    expect(resultado).toHaveTextContent(
      `Seria enviado no sistema e por e-mail institucional para: ${GESTORA} (gestora de referência), Gestora pedagógica, SPE, Líder do NFP.`,
    );
    // Decisões 38 e 41: a cor em vigor muda na hora, as tarefas começam; o Comitê confirma ou desfaz, e a SPE decide
    // se convoca o extraordinário. O número das decisões não aparece para quem registra (rodada 1 de revisão).
    expect(resultado).toHaveTextContent(
      'Cor em vigor: Vermelho. Mudou na hora com este registro: as tarefas do vermelho começaram em 07/12/2026. O Comitê confirma ou desfaz depois.',
    );
    expect(resultado).not.toHaveTextContent(/decisões \d/);
    expect(resultado).toHaveTextContent('A SPE decide se convoca o Comitê extraordinário.');
    expect(resultado).not.toHaveTextContent('só muda quando o Comitê publicar');
    expect(resultado).not.toHaveTextContent('espera o Comitê');
    expect(resultado).toHaveTextContent('Nada é enviado');
  });

  test('responder bem num município verde: a cor fica igual', async () => {
    const user = userEvent.setup();
    renderizar();
    await user.selectOptions(await screen.findByLabelText('Município'), String(VERDE.id));
    await responder(user, '5', '10');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));
    const resultado = await screen.findByRole('status');
    expect(resultado).toHaveTextContent('Antes: Verde → Agora: Verde');
    expect(resultado).not.toHaveTextContent('Seria enviado');
    expect(resultado).toHaveTextContent('Cor em vigor: Verde. Só o vermelho muda a cor em vigor na hora; as outras mudanças esperam o Comitê.');
  });

  test('decisão 51: a resposta é por projeto; a segunda resposta do mesmo projeto no ciclo é recusada, e a tela avisa antes', async () => {
    const user = userEvent.setup();
    renderizar();
    await user.selectOptions(await screen.findByLabelText('Município'), String(VERDE.id));
    // Um projeto só: já vem escolhido.
    const projeto = screen.getByLabelText('Projeto');
    expect(projeto).toHaveValue(String(VERDE.projetos[0]!.id));
    expect(projeto).not.toHaveAccessibleDescription(/já respondeu/);
    await responder(user, '4', '9');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      `Resposta registrada para ${VERDE.nome}-${VERDE.uf}, projeto ${VERDE.projetos[0]!.nome}.`,
    );

    // Rodada 3: logo depois do envio, o campo não mostra o aviso vermelho de recusa, e sim que a resposta entrou.
    const registrada = screen.getByText(/^Resposta deste projeto registrada hoje/);
    expect(registrada).toHaveTextContent('Resposta deste projeto registrada hoje, 07/12/2026. A pesquisa é uma por projeto.');
    expect(registrada).not.toHaveClass('text-[#8A1C14]');
    expect(screen.getByLabelText('Projeto')).not.toHaveAccessibleDescription(/uma segunda resposta não entra/);
    // A segunda resposta é recusada com o motivo.
    await responder(user, '1', '0');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Este projeto já tem resposta neste ciclo: a pesquisa é uma por projeto.');
    // Quem volta ao município depois vê o aviso no campo, antes de responder (WCAG 3.3.1).
    await user.selectOptions(screen.getByLabelText('Município'), '');
    await user.selectOptions(screen.getByLabelText('Município'), String(VERDE.id));
    expect(screen.getByLabelText('Projeto')).toHaveAccessibleDescription(
      /Este projeto já respondeu neste ciclo, em 07\/12\/2026\. A pesquisa é uma por projeto: uma segunda resposta não entra\./,
    );
  });

  test('decisão 51: com mais de um projeto, a tela pede o projeto e diz quem responde por cada um', async () => {
    const user = userEvent.setup();
    const VARIOS = DADOS.municipios.find(
      (m) => m.projetos.length > 1 && m.projetos.some((p) => !DADOS.respostas.some((r) => r.projeto === p.id && r.ciclo === DADOS.ciclo_atual)),
    )!;
    const livre = VARIOS.projetos.find((p) => !DADOS.respostas.some((r) => r.projeto === p.id && r.ciclo === DADOS.ciclo_atual))!;
    renderizar();
    await user.selectOptions(await screen.findByLabelText('Município'), String(VARIOS.id));
    const projeto = screen.getByLabelText('Projeto');
    expect(projeto).toHaveValue('');
    expect(within(projeto).getAllByRole('option')).toHaveLength(VARIOS.projetos.length + 1);
    expect(within(projeto).getByRole('option', { name: `${livre.nome} · ${livre.articulador}` })).toBeInTheDocument();

    await responder(user, '5', '10');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Escolha um projeto do município.');

    await user.selectOptions(projeto, String(livre.id));
    await responder(user, '5', '10');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));
    expect(await screen.findByRole('status')).toHaveTextContent(`Resposta registrada para ${VARIOS.nome}-${VARIOS.uf}, projeto ${livre.nome}.`);
  });

  test('sem município e sem notas: mostra o que falta, em português simples', async () => {
    const user = userEvent.setup();
    renderizar();
    await user.click(await screen.findByRole('button', { name: 'Enviar resposta' }));
    const erros = await screen.findByRole('alert');
    expect(erros).toHaveTextContent('Escolha um município da lista.');
    expect(erros).toHaveTextContent('Falta responder, com nota de 1 a 5: item 1, item 2, item 3, item 4, item 5 e item 6.');
    expect(erros).toHaveTextContent('A nota de recomendação vai de 0 a 10.');
  });

  test('item sem resposta: o erro diz qual item falta e marca o grupo dele (WCAG 3.3.1)', async () => {
    const user = userEvent.setup();
    renderizar();
    await user.selectOptions(await screen.findByLabelText('Município'), String(VERDE.id));
    for (const i of [1, 2, 3, 5]) {
      await user.click(within(screen.getByRole('group', { name: new RegExp(`^${i}\\.`) })).getByLabelText('4'));
    }
    await user.click(within(screen.getByRole('group', { name: /recomendaria/ })).getByLabelText('9'));
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Falta responder, com nota de 1 a 5: item 4 e item 6.');
    const item4 = screen.getByRole('group', { name: /^4\./ });
    expect(item4).toHaveAccessibleDescription(/Falta responder este item\./);
    for (const radio of within(item4).getAllByRole('radio')) expect(radio).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('group', { name: /^6\./ })).toHaveAccessibleDescription(/Falta responder este item\./);
    const item1 = screen.getByRole('group', { name: /^1\./ });
    expect(item1).not.toHaveAccessibleDescription(/Falta responder/);
    for (const radio of within(item1).getAllByRole('radio')) expect(radio).not.toHaveAttribute('aria-invalid');

    // Respondido o item, a marca de erro dele some.
    await user.click(within(item4).getByLabelText('3'));
    expect(item4).not.toHaveAccessibleDescription(/Falta responder/);
  });

  test('baixar planilha: as respostas do ciclo atual, com a resposta da sessão', async () => {
    const baixar = vi.spyOn(exportar, 'baixarCsv').mockImplementation(() => undefined);
    const user = userEvent.setup();
    renderizar();
    await user.selectOptions(await screen.findByLabelText('Município'), String(VERDE.id));
    await responder(user, '4', '9');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));
    await screen.findByRole('status');
    await user.click(screen.getByRole('button', { name: /Baixar planilha/ }));
    const [nome, cabecalho, linhas] = baixar.mock.calls[0]!;
    expect(nome).toBe('semaforo_pesquisa_2026.6.csv');
    expect(cabecalho).toEqual(expect.arrayContaining(['Município', 'UF', 'Projeto', 'Respondida em', 'NPS', 'O que melhorar']));
    const doCiclo = DADOS.respostas.filter((r) => r.ciclo === '2026.6').length;
    expect(linhas).toHaveLength(doCiclo + 1);
  });

  test('os 6 itens e a recomendação perguntam o que o PDF do Semáforo pergunta, na ordem dele', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1, name: 'Pesquisa do articulador' });
    // [item do PDF ("Itens da pesquisa do articulador", página 2), frase da tela]: a frase é simples, o objeto é o mesmo.
    const doPdf: [string, string][] = [
      ['Cumprimento do cronograma acordado', 'O cronograma acordado é cumprido.'],
      ['Qualidade e pertinência das formações', 'As formações têm qualidade e tratam do que a rede precisa.'],
      ['Presença, disponibilidade e comunicação do coordenador', 'O coordenador está presente, disponível e se comunica bem.'],
      ['Apoio nas avaliações internas', 'A equipe apoia a rede nas avaliações internas.'],
      ['Uso das coleções e materiais em sala', 'Os professores usam as coleções e os materiais em sala.'],
      ['Percepção de avanço nas aprendizagens', 'Percebemos avanço nas aprendizagens.'],
    ];
    doPdf.forEach(([, frase], i) => {
      expect(screen.getByRole('group', { name: `${i + 1}. ${frase}` })).toBeInTheDocument();
    });
    // Rodada 5 (decisão 51: a pesquisa é por projeto): a nota de recomendação pergunta pelo projeto avaliado.
    expect(
      screen.getByRole('group', { name: '7. De 0 a 10, quanto você recomendaria o projeto avaliado da Aprender Editora?' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('O que precisamos melhorar com urgência?')).toBeInTheDocument();
  });

  test('rodada 5 (decisão 51): o título e a nota de recomendação dizem qual projeto está sendo avaliado', async () => {
    const user = userEvent.setup();
    renderizar();
    expect(await screen.findByRole('heading', { level: 2, name: 'Pesquisa de satisfação do projeto' })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Município'), String(VERDE.id));
    const projeto = VERDE.projetos[0]!.nome;
    if (VERDE.projetos.length > 1) await user.selectOptions(screen.getByLabelText('Projeto'), String(VERDE.projetos[0]!.id));
    expect(screen.getByRole('heading', { level: 2, name: `Pesquisa de satisfação do projeto ${projeto}` })).toBeInTheDocument();
    expect(screen.getByText(/^Responda pensando no projeto/)).toHaveTextContent(`Responda pensando no projeto ${projeto}.`);
    expect(
      screen.getByRole('group', { name: `7. De 0 a 10, quanto você recomendaria o projeto ${projeto} da Aprender Editora?` }),
    ).toBeInTheDocument();
  });

  test('rodada 5: trocar o município limpa o retorno anterior (o erro já resolvido e a resposta do outro município)', async () => {
    const user = userEvent.setup();
    renderizar();
    await user.click(await screen.findByRole('button', { name: 'Enviar resposta' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Escolha um município da lista.');
    await user.selectOptions(screen.getByLabelText('Município'), String(VERDE.id));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    // O grupo do item sem resposta também deixa de ficar marcado.
    expect(screen.getByRole('group', { name: /^1\./ })).not.toHaveAccessibleDescription(/Falta responder/);

    await responder(user, '4', '9');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));
    expect(screen.getByRole('status')).toHaveTextContent(`Resposta registrada para ${VERDE.nome}-${VERDE.uf}`);
    const outro = DADOS.municipios.find((m) => m.id !== VERDE.id)!;
    await user.selectOptions(screen.getByLabelText('Município'), String(outro.id));
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });

  test('o campo do nome declara a finalidade para o preenchimento automático (WCAG 1.3.5)', async () => {
    renderizar();
    expect(await screen.findByLabelText('Seu nome (opcional)')).toHaveAttribute('autocomplete', 'name');
  });

  test('o retorno entra numa região viva que já estava na tela, para o leitor de tela anunciar', async () => {
    const user = userEvent.setup();
    renderizar();
    const regiao = screen.getByRole('status');
    expect(regiao).toBeEmptyDOMElement();
    await user.click(await screen.findByRole('button', { name: 'Enviar resposta' }));
    await user.selectOptions(screen.getByLabelText('Município'), String(VERDE.id));
    await responder(user, '4', '9');
    await user.click(screen.getByRole('button', { name: 'Enviar resposta' }));
    expect(screen.getByRole('status')).toBe(regiao);
    expect(regiao).toHaveTextContent('Antes: Verde → Agora: Verde');
  });
});
