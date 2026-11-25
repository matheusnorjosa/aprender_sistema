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

/** Um município verde (em vigor e sugerido), com gestora de referência: o ponto de partida. */
const VERDE = (() => {
  const m = DADOS.municipios.find((x) => {
    const s = avaliarMunicipio(DADOS, x.id);
    return s.cor_vigente === 'verde' && s.ciclos.at(-1)?.resultado.cor === 'verde';
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
    expect(screen.getByText(/Ciclo 2026\.6/)).toHaveTextContent('prazo para responder: 20/12/2026');
    expect(screen.getByText(/sem link/)).toBeInTheDocument();
  });

  test('quem responde é o mesmo do começo ao fim: o articulador ou o secretário municipal', async () => {
    renderizar();
    const explicacao = await screen.findByText(/sem link/);
    expect(explicacao).toHaveTextContent(/como o articulador ou o secretário municipal veria/);
    expect(explicacao).toHaveTextContent(/articuladores e secretários municipais recebem um link/);
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
      `Seria enviado para: ${GESTORA} (gestora de referência), Gestora pedagógica, SPE, Líder do NFP.`,
    );
    // Pelo PDF a cor muda na hora; no protótipo a cor em vigor espera o Comitê (leitura registrada em "Para validar").
    expect(resultado).toHaveTextContent('No protótipo, a cor em vigor só muda quando o Comitê publicar.');
    expect(resultado).not.toHaveTextContent('O vermelho vale na hora');
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
    expect(resultado).not.toHaveTextContent('Seria enviado para');
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
    expect(cabecalho).toEqual(expect.arrayContaining(['Município', 'UF', 'Respondida em', 'NPS', 'O que melhorar']));
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
    expect(
      screen.getByRole('group', { name: '7. De 0 a 10, quanto você recomendaria a parceria com a Aprender Editora?' }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('O que precisamos melhorar com urgência?')).toBeInTheDocument();
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
