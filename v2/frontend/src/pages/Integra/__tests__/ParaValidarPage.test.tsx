/** "Para validar no dia 7": sugestões dos PDFs, pontos em aberto da ata, origem e destino dos dados. */
import { MemoryRouter } from 'react-router';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, test } from 'vitest';

import ParaValidarPage from '../ParaValidarPage';
import { contarNomesReais, guardaDeNomesReaisAtiva } from './nomesReais';

function renderizar(): void {
  render(
    <MemoryRouter>
      <ParaValidarPage />
    </MemoryRouter>,
  );
}

/** O item (article) cujo título casa com o texto. Os cartões da matriz "Quem vê o quê" (h5) repetem nomes de tela e ficam de fora. */
async function item(titulo: RegExp): Promise<HTMLElement> {
  const titulos = (await screen.findAllByRole('heading', { name: titulo })).filter((h) => h.tagName !== 'H5');
  expect(titulos, String(titulo)).toHaveLength(1);
  return titulos[0]!.closest('article, li') as HTMLElement;
}

describe('Para validar no dia 7', { timeout: 20000 }, () => {
  test('título, as três partes e o índice que leva a elas', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Para validar no dia 7' })).toBeInTheDocument();
    const partes = ['Sugestões e pontos em aberto', 'De onde virá cada dado', 'Para quem vai cada resultado'];
    const indice = screen.getByRole('navigation', { name: 'Nesta página' });
    for (const parte of partes) {
      const h2 = screen.getByRole('heading', { level: 2, name: parte });
      expect(within(indice).getByRole('link', { name: parte })).toHaveAttribute('href', `#${h2.id}`);
    }
    expect(screen.getByRole('link', { name: 'Voltar para a Integra' })).toHaveAttribute('href', '/integra');
  });

  test('cada ponto em aberto da ata e cada conflito com o PDF, com como o protótipo resolveu', async () => {
    renderizar();
    const titulos = [
      /vai dirigindo/i,
      /município que não responde/i,
      /gestora de referência de cada município/i,
      /29 municípios/i,
      /que outras ferramentas/i,
      /parte subjetiva/i,
      /formadores que cada coordenador acompanhou/i,
      /coordenador vê a própria ficha/i,
      /quem aprova o remanejamento/i,
    ];
    for (const t of titulos) {
      const artigo = await item(t);
      expect(within(artigo).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    }
    expect(await item(/quem aprova o remanejamento/i)).toHaveTextContent(/consultiv/i);
  });

  test('revisão: sem municípios fora dos estratos, alerta de quem entra em Sobrecarga e acesso da Diretoria', async () => {
    renderizar();
    const semMunicipios = await item(/sem municípios entra na conta de .Capacidade disponível/i);
    expect(semMunicipios).toHaveTextContent(/5 com capacidade disponível e 1 sem municípios/);
    expect(within(semMunicipios).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    const alerta = await item(/alerta de Sobrecarga: só quem entra/i);
    expect(alerta).toHaveTextContent(/semestre anterior/);
    const acesso = await item(/coordenador vê a própria ficha/i);
    expect(acesso).toHaveTextContent(/Diretoria entra quando a gerência dela/);
    expect(acesso).toHaveTextContent(/Equipe ou Gerente na gerência SPE/);
  });

  test('as sugestões marcadas nos dois PDFs aparecem como sugestão', async () => {
    renderizar();
    for (const t of [/5 dias úteis.*SPE/i, /10 dias/i, /5º dia útil/i, /ata da reunião de escuta/i, /sem dado/i, /vários articuladores/i, /painel do coordenador/i, /momento reservado/i]) {
      expect(await item(t)).toHaveTextContent(/sugestão/i);
    }
  });

  test('de onde virá cada dado: Aprender Sistema, DFF, Logística e FRV ou "não existe ainda"', async () => {
    renderizar();
    expect(await item(/^Turmas de formação$/)).toHaveTextContent(/Não existe ainda/);
    expect(await item(/^Professores em formação$/)).toHaveTextContent(/Registros de Turmas do DAT/);
    // O mesmo texto do bloco Deslocamento (decisão 29): o tempo fica no cadastro de municípios.
    const tempo = await item(/^Tempo de deslocamento$/);
    expect(tempo).toHaveTextContent(/relatório de deslocamento \(92 municípios\)/);
    expect(tempo).toHaveTextContent(/cadastro de municípios/);
    expect(tempo).toHaveTextContent(/decisão 29/);
    expect(tempo).not.toHaveTextContent(/relatório da SPE/);
    expect(await item(/^Status ativo ou suspenso$/)).toHaveTextContent(/Não existe ainda/);
    expect(await item(/^Gestora de referência$/)).toHaveTextContent(/Não existe ainda/);
    expect(await item(/^Pesquisa do articulador$/)).toHaveTextContent(/Não existe ainda/);
    expect(await item(/^Ocorrências$/)).toHaveTextContent(/Não existe ainda/);
    // Uma origem só na mesma página: pelo PDF do Semáforo (coleta 6), formulário novo; a DFF é o destino.
    const observacao = await item(/^Observação de formação$/);
    expect(observacao).toHaveTextContent(/Não existe ainda/);
    expect(observacao).toHaveTextContent(/Relatório mensal e formulários/);
    expect(observacao).toHaveTextContent(/PDI do coordenador na Plataforma DFF/);
    expect(observacao).not.toHaveTextContent(/já é feita na Plataforma DFF/);
    expect(await item(/^Cronograma cumprido$/)).toHaveTextContent(/Aprender Sistema/);
  });

  test('texto para gestor: nenhum nome de tabela ou de campo do código', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1 });
    const texto = document.body.textContent ?? '';
    for (const termo of ['Municipio)', 'ProjetoGeral', 'PlanoFormacoes', 'EquipeGerencia', 'Gerencia,', 'DATRegistro', '_qtde', 'Solicitacao', 'Formacao)']) {
      expect(texto).not.toContain(termo);
    }
  });

  test('alerta de Sobrecarga: diz que com 130 exato não há alerta', async () => {
    renderizar();
    expect(await item(/alerta de Sobrecarga: só quem entra/i)).toHaveTextContent(/Com 130 exato, fica dentro da meta e sem alerta/);
  });

  test('para quem vai cada resultado: ICA, cor do Semáforo e o PDI na DFF', async () => {
    renderizar();
    expect(await item(/^ICA de cada coordenador$/)).toHaveTextContent(/Semáforo/);
    expect(await item(/^Cor do Semáforo$/)).toHaveTextContent(/Aprender Sistema/);
    expect(await item(/^Observação de formação e relatório de visita$/)).toHaveTextContent(/PDI/);
    const tempo = await item(/^Tempo de deslocamento de cada município$/);
    expect(tempo).toHaveTextContent(/ICA/);
    expect(tempo).toHaveTextContent(/tela de viagens/);
  });

  test('quem vê o quê na versão real: um cartão por tela, agrupado por módulo, com cada cargo escrito; nada rola para o lado', async () => {
    renderizar();
    const h2 = await screen.findByRole('heading', { level: 2, name: 'Quem vê o quê na versão real' });
    expect(within(screen.getByRole('navigation', { name: 'Nesta página' })).getByRole('link', { name: 'Quem vê o quê na versão real' })).toHaveAttribute('href', `#${h2.id}`);
    const matriz = screen.getByRole('region', { name: /Quem faz o quê em cada tela/ });
    // A matriz de 9 colunas (pelo menos 1168 px) rolava dentro do próprio contêiner: o gate de 400 px reprova
    // qualquer rolagem interna, e a regra do dono é nenhuma rolagem para o lado.
    expect(within(matriz).queryByRole('table')).not.toBeInTheDocument();
    expect(matriz.querySelector('.overflow-x-auto')).toBeNull();
    expect(screen.queryByText(/arraste a tabela para o lado/)).not.toBeInTheDocument();
    for (const modulo of ['ICA', 'Semáforo', 'Deslocamento', 'DFF']) {
      expect(within(matriz).getByRole('heading', { level: 4, name: modulo })).toBeInTheDocument();
    }
    for (const tela of ['Painel', 'Ficha do coordenador', 'Simulador', 'Pesos e faixas', 'Por gerência', 'Comparativo', 'Histórico', 'Alertas e exportação', 'Comitê', 'Ficha do município', 'Painel da gestora', 'Pesquisa do articulador', 'Indicadores da Líder', 'Relatório mensal e formulários']) {
      const cartao = within(matriz).getByRole('heading', { level: 5, name: tela }).closest('li') as HTMLElement;
      const cargos = within(cartao).getAllByRole('term').map((dt) => dt.textContent);
      expect(cargos).toEqual(['SPE', 'Gestão Operacional', 'Gestora pedagógica', 'Líder do NFP', 'Coordenador', 'Relacionamento e Comercial', 'Diretoria', 'Superusuário']);
    }
  });

  test('cada célula diz o que o papel faz por escrito: simulador (decisão 20) e coordenador fora do ICA (decisão 21)', async () => {
    renderizar();
    const matriz = await screen.findByRole('region', { name: /Quem faz o quê em cada tela/ });
    const celula = (tela: string, papel: string): HTMLElement => {
      const cartao = within(matriz).getByRole('heading', { level: 5, name: tela }).closest('li') as HTMLElement;
      const dt = within(cartao).getAllByRole('term').find((t) => t.textContent === papel);
      return dt?.nextElementSibling as HTMLElement;
    };
    expect(celula('Simulador', 'Gestora pedagógica')).toHaveTextContent(/Propõe/);
    expect(celula('Simulador', 'Gestora pedagógica')).toHaveTextContent(/decisão 20/);
    expect(celula('Simulador', 'SPE')).toHaveTextContent(/Aplica/);
    expect(celula('Simulador', 'Líder do NFP')).toHaveTextContent(/Vê/);
    expect(celula('Ficha do coordenador', 'Coordenador')).toHaveTextContent(/Nada.*nem a própria ficha/);
    expect(celula('Painel', 'Diretoria')).toHaveTextContent(/Em aberto.*P8b/);
  });

  test('o que já foi decidido aparece como decidido, e as perguntas abertas como "em aberto — decidir no dia 7"', async () => {
    renderizar();
    const decidido = (await screen.findByRole('heading', { name: 'Já decidido' })).parentElement as HTMLElement;
    for (const n of [19, 20, 21, 22, 29]) {
      expect(within(decidido).getByText(`Decidido (decisão ${n})`)).toBeInTheDocument();
    }
    const aberto = screen.getByRole('heading', { name: 'Em aberto — decidir no dia 7' }).parentElement as HTMLElement;
    for (const p of ['P1', 'P3', 'P6', 'P8a', 'P8b', 'P9', 'P10']) {
      expect(within(aberto).getByText(`${p}: em aberto — decidir no dia 7`)).toBeInTheDocument();
    }
    expect(aberto).toHaveTextContent(/a Diretoria entra na Integra\?/);
  });

  test('de onde virá cada dado: o Deslocamento, do relatório de hoje para o cadastro de municípios', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 3, name: 'Deslocamento' })).toBeInTheDocument();
    const tempo = await item(/^Tempo de referência de cada município$/);
    expect(tempo).toHaveTextContent(/relatório de deslocamento \(92 municípios\)/);
    expect(tempo).toHaveTextContent(/cadastro de municípios/);
    expect(tempo).toHaveTextContent(/o ICA, a Logística e a FRV leem/);
    expect(await item(/^Viagens registradas$/)).toHaveTextContent(/tempo esperado ao lado do registrado/);
    expect(await item(/^Viagens registradas$/)).toHaveTextContent(/decisão 29/);
  });

  test('o Semáforo já existe: nenhum texto diz que ele ainda vai chegar, e cada ponto diz o que o protótipo faz', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1 });
    expect(document.body).not.toHaveTextContent(/próxima entrega/i);
    expect(await item(/momento reservado/i)).toHaveTextContent(/Relatório mensal e formulários/);
    expect(await item(/10 dias/i)).toHaveTextContent(/dia 20 do segundo mês/);
    expect(await item(/5º dia útil/i)).toHaveTextContent(/sem prazo/);
    expect(await item(/ata da reunião de escuta/i)).toHaveTextContent(/sem prazo/);
    expect(await item(/vários articuladores/i)).toHaveTextContent(/pelo menos um articulador/);
    expect(await item(/sem dado/i)).toHaveTextContent(/não conta para a cor/);
    const semResposta = await item(/município que não responde/i);
    expect(semResposta).toHaveTextContent(/enquanto o prazo está aberto/i);
    expect(semResposta).toHaveTextContent(/justificativa/);
    expect(await item(/que outras ferramentas/i)).toHaveTextContent(/5 cartões: ICA, Semáforo, Deslocamento, DFF/);
  });

  test('observação de formação: registrada no Semáforo ou feita na DFF fica para decidir no dia 7', async () => {
    renderizar();
    const h3 = await screen.findByRole('heading', { level: 3, name: 'A Integra e as outras ferramentas' });
    const tema = h3.closest('section') as HTMLElement;
    const artigo = within(tema)
      .getByRole('heading', { level: 4, name: /Observação de formação: registrada no Semáforo ou feita na DFF/ })
      .closest('article') as HTMLElement;
    expect(artigo).toHaveTextContent(/coleta 6/);
    expect(artigo).toHaveTextContent(/Relatório mensal e formulários/);
    expect(artigo).toHaveTextContent(/o Aprender Sistema lê de lá/);
  });

  test('as duas contradições do relatório de deslocamento, para o dono decidir', async () => {
    renderizar();
    expect(await screen.findByRole('heading', { level: 3, name: /Deslocamento: o relatório se contradiz/ })).toBeInTheDocument();
    const terra = await item(/16 ou 23 municípios/);
    expect(terra).toHaveTextContent(/decisão da gestão/);
    expect(terra).toHaveTextContent(/os 23/);
    expect(within(terra).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    const craibas = await item(/Craíbas-AL/);
    expect(craibas).toHaveTextContent(/18h00/);
    expect(craibas).toHaveTextContent(/Muito longo/);
    expect(craibas).toHaveTextContent(/Longo até 18h/);
    // A mesma lista da tela "Como o tempo é calculado", mais o estado do Amigos do Bem.
    // Os dois números saem da mesma tabela: a pergunta é qual coluna o ICA usa.
    const mediana = await item(/Mediana: coluna Ida \(17h45\) ou coluna Ida e volta \(17h48\)\?/);
    expect(mediana).toHaveTextContent(/O relatório calcula a mediana pela coluna Ida/);
    expect(mediana).toHaveTextContent(/Qual coluna o ICA usa para o município sem localidade/);
    expect(mediana).not.toHaveTextContent(/arredondou cada tempo para 5 minutos/);
    expect(within(mediana).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    const amigos = await item(/Amigos do Bem/);
    expect(amigos).toHaveTextContent(/Amigos do Bem-CE/);
    expect(amigos).toHaveTextContent(/estado/);
  });

  test('o que a seção 7 do PDF pede e o protótipo não mede fica registrado para o dia 7', async () => {
    renderizar();
    const lider = await item(/indicadores da Líder do NFP que o protótipo não mede/i);
    expect(lider).toHaveTextContent(/tempo médio de resposta a ocorrências/i);
    expect(lider).toHaveTextContent(/convergência entre a pesquisa e as ocorrências/i);
    expect(lider).toHaveTextContent(/por projeto/);
    expect(within(lider).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    const atas = await item(/painel da gestora: atas a registrar/i);
    expect(atas).toHaveTextContent(/pesquisas sem resposta/);
    expect(atas).toHaveTextContent(/reuniões a agendar/);
  });

  test('o que a decisão 20 e a decisão 21 já fecharam não aparece como pergunta em aberto', async () => {
    renderizar();
    const remanejamento = await item(/quem aprova o remanejamento/i);
    expect(remanejamento).toHaveTextContent(/decisão 20/);
    expect(remanejamento).toHaveTextContent(/a gestora pedagógica propõe e a SPE aplica/);
    expect(remanejamento).not.toHaveTextContent(/Quem aprova: a SPE/);
    const ficha = await item(/coordenador vê a própria ficha/i);
    expect(ficha).toHaveTextContent(/decisão 21/);
    expect(ficha).not.toHaveTextContent(/Confirmar que a sugestão do PDF sai/);
    const painel = await item(/painel do coordenador/i);
    expect(painel).toHaveTextContent(/decisão 21/);
    expect(painel).toHaveTextContent(/tela à parte/);
    expect(painel).not.toHaveTextContent(/por onde o coordenador entra/);
  });

  test('um nome só para o cargo: gestora pedagógica (o PDF também diz "gestora técnica")', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1 });
    expect(document.body).not.toHaveTextContent(/gestora técnica/i);
  });

  test('Amigos do Bem: a UF provisória não conta como estado no ICA', async () => {
    renderizar();
    expect(await item(/Amigos do Bem/)).toHaveTextContent(/não conta como estado/);
  });

  test('vermelho imediato: o PDF muda a cor na hora e só permite convocar o Comitê; o protótipo espera o Comitê', async () => {
    renderizar();
    const publica = await item(/quando o Comitê publica/i);
    expect(publica).toHaveTextContent(/permite convocar o Comitê em caráter extraordinário/);
    expect(publica).not.toHaveTextContent(/chama uma reunião extraordinária/);
    const imediato = await item(/vermelho imediato: a cor em vigor muda na hora/i);
    expect(imediato).toHaveTextContent(/O sistema muda a cor na hora/);
    expect(imediato).toHaveTextContent(/o Comitê confirma e publica/);
    expect(within(imediato).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    expect(imediato).toHaveTextContent(/só muda quando o Comitê publica/);
  });

  test('as leituras das regras do Semáforo que ficaram para validar no dia 7', async () => {
    renderizar();
    const h3 = await screen.findByRole('heading', { level: 3, name: 'Semáforo: como o protótipo leu o PDF' });
    const tema = h3.closest('section') as HTMLElement;
    const esperados: [RegExp, RegExp][] = [
      [/número que aparece na tela/i, /3,95 aparece .4,0. e fica verde/],
      [/NPS: média das notas/i, /8,5 é amarelo/],
      [/ocorrências no trimestre/i, /3 meses corridos/],
      // Duas janelas: o ciclo fechado conta até o último dia dele; o ciclo atual, até hoje.
      [/ocorrências no trimestre/i, /no ciclo fechado, até o último dia do ciclo; no ciclo atual, até hoje/],
      [/prazos das tarefas/i, /29\/11/],
      [/no bimestre.*no semestre/i, /2 e 6 meses depois da publicação/],
      [/três amarelos/i, /extraordinária/],
      [/volta ao verde/i, /2 ciclos seguidos sem alerta/],
      [/volta ao verde/i, /ciclo em andamento .*não soma/],
      // Seção 4: no meio do ciclo a cor só muda para piorar; um amarelo não tira o município do vermelho.
      [/volta ao verde/i, /só muda na hora para piorar.*Sair do vermelho espera o ciclo fechar/],
      [/quem faz cada tarefa/i, /Contato com o município/],
      // Escolhas que os relatórios de implementação mandaram confirmar no dia 7.
      [/quando o Comitê publica/i, /sexta-feira.*02\/12\/2026/],
      [/tarefa só nasce quando a cor em vigor muda/i, /contato em 48 h. não volta a abrir/],
      [/em recuperação. recebe as tarefas do amarelo/i, /10 dias úteis/],
      [/um relatório mensal por município ou por coordenador/i, /primeiro contrato/],
      [/cronograma confirmado.*reunião de escuta/i, /coleta 4/],
    ];
    for (const [titulo, texto] of esperados) {
      const h = within(tema).getByRole('heading', { level: 4, name: titulo });
      const artigo = h.closest('article') as HTMLElement;
      expect(artigo).toHaveTextContent(texto);
      expect(within(artigo).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    }
  });

  // Guarda local: a lista dos nomes reais fica fora do git (ver `nomesReais.ts`); sem ela, o teste é pulado.
  test.skipIf(!guardaDeNomesReaisAtiva)('não usa nomes de pessoas reais da ata nem dos PDFs', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1 });
    // Texto de cada nó separado: o textContent do body cola "resolveu:" com a palavra do elemento seguinte.
    const textos: string[] = [];
    const nos = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (nos.nextNode()) textos.push(nos.currentNode.textContent ?? '');
    expect(contarNomesReais(textos.join(' '))).toBe(0);
  });
});
