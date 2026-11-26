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

  test('revisão: sem municípios fora dos estratos, alerta de Sobrecarga a cada recálculo e acesso de hoje e da versão real', async () => {
    renderizar();
    const semMunicipios = await item(/sem municípios entra na conta de .Capacidade disponível/i);
    expect(semMunicipios).toHaveTextContent(/5 com capacidade disponível e 1 sem municípios/);
    expect(within(semMunicipios).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    const alerta = await item(/alerta de Sobrecarga: só quem entra/i);
    // Decisão 69: era "compara com o semestre anterior"; agora o alerta sai a cada recálculo.
    expect(alerta).toHaveTextContent(/a cada recálculo/);
    expect(alerta).not.toHaveTextContent(/semestre anterior/);
    const acesso = await item(/coordenador vê a própria ficha/i);
    // Decisão 67: a Diretoria não entra na Integra com login próprio; era "entra quando a gerência dela...".
    expect(acesso).not.toHaveTextContent(/Diretoria entra quando/);
    expect(acesso).toHaveTextContent(/a Diretoria não entra com login próprio \(decisão 67\)/);
    expect(acesso).toHaveTextContent(/Equipe ou Gerente na gerência SPE/);
    // Decisões 87 e 68: a marca de cargo na Integra; aprovar eventos fica separado.
    expect(acesso).toHaveTextContent(/marca de cargo na Integra/);
    expect(acesso).toHaveTextContent(/decisão 68/);
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
    // Decisão 94: a observação nasce na DFF, junto do PDI; o Aprender Sistema lê de lá (era "Não existe ainda").
    const observacao = await item(/^Observação de formação$/);
    expect(observacao).not.toHaveTextContent(/Não existe ainda/);
    expect(observacao).toHaveTextContent(/decisão 94/);
    expect(observacao).toHaveTextContent(/Relatório mensal e formulários/);
    expect(observacao).toHaveTextContent(/PDI do coordenador na Plataforma DFF/);
    expect(observacao).not.toHaveTextContent(/Formulário novo/);
    expect(await item(/^Vínculo formador × coordenador$/)).toHaveTextContent(/decisão 93/);
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

  test('alerta de Sobrecarga: com 130 exato, dentro da meta, mas na faixa de Sobrecarga (decisão 69)', async () => {
    renderizar();
    // Era "Com 130 exato, fica dentro da meta e sem alerta".
    expect(await item(/alerta de Sobrecarga: só quem entra/i)).toHaveTextContent(/Com 130 exato, .*recebe o alerta de Sobrecarga/);
  });

  test('para quem vai cada resultado: ICA, cor do Semáforo e o PDI na DFF', async () => {
    renderizar();
    expect(await item(/^ICA de cada coordenador$/)).toHaveTextContent(/Semáforo/);
    expect(await item(/^Cor do Semáforo$/)).toHaveTextContent(/Aprender Sistema/);
    expect(await item(/^Observação de formação e relatório de visita$/)).toHaveTextContent(/PDI/);
    // Decisão 86: a Avaliação do Coordenador se chama Tríade.
    expect(await item(/^Resposta do articulador$/)).toHaveTextContent(/Tríade/);
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
      expect(cargos).toEqual(['SPE', 'Gerente Operacional', 'Gerente Pedagógica', 'Líder do NFP', 'Coordenador', 'Relacionamento e Comercial', 'Diretoria', 'Superusuário']);
    }
    // Decisão 87: os cargos na Integra são Gerente Operacional e Gerente Pedagógica. "Gestão Operacional" fica só
    // como nome da gerência, no texto da decisão 19.
    expect(matriz).not.toHaveTextContent(/Gestão Operacional|Gestora pedagógica/);
  });

  test('cada célula diz o que o papel faz por escrito: simulador (decisão 20) e coordenador fora do ICA (decisão 21)', async () => {
    renderizar();
    const matriz = await screen.findByRole('region', { name: /Quem faz o quê em cada tela/ });
    const celula = (tela: string, papel: string): HTMLElement => {
      const cartao = within(matriz).getByRole('heading', { level: 5, name: tela }).closest('li') as HTMLElement;
      const dt = within(cartao).getAllByRole('term').find((t) => t.textContent === papel);
      return dt?.nextElementSibling as HTMLElement;
    };
    expect(celula('Simulador', 'Gerente Pedagógica')).toHaveTextContent(/Propõe/);
    expect(celula('Simulador', 'Gerente Pedagógica')).toHaveTextContent(/decisão 20/);
    expect(celula('Simulador', 'SPE')).toHaveTextContent(/Aplica/);
    expect(celula('Simulador', 'Líder do NFP')).toHaveTextContent(/Vê/);
    expect(celula('Ficha do coordenador', 'Coordenador')).toHaveTextContent(/Nada.*nem a própria ficha/);
    // Decisão 67: a Diretoria não entra (era "Em aberto (P8b)"). Decisão 90: a Gerente Operacional vê os painéis.
    expect(celula('Painel', 'Diretoria')).toHaveTextContent(/Nada.*decisão 67/);
    expect(celula('Painel', 'Gerente Operacional')).toHaveTextContent(/Vê.*decisão 90/);
    // Decisão 78: a Líder do NFP lê o momento reservado.
    expect(celula('Ficha do município', 'Líder do NFP')).toHaveTextContent(/Vê.*momento reservado.*decisão 78/);
  });

  test('o que já foi decidido aparece como decidido, e as perguntas abertas como "em aberto — decidir no dia 7"', async () => {
    renderizar();
    const decidido = (await screen.findByRole('heading', { name: 'Já decidido' })).parentElement as HTMLElement;
    for (const n of [19, 20, 21, 22, 29, 58, 67, 78, 87, 90, 94]) {
      expect(within(decidido).getByText(`Decidido (decisão ${n})`)).toBeInTheDocument();
    }
    const aberto = screen.getByRole('heading', { name: 'Em aberto — decidir no dia 7' }).parentElement as HTMLElement;
    expect(within(aberto).getByText('P1: em aberto — decidir no dia 7')).toBeInTheDocument();
    // Perguntas que nenhuma decisão de 26/11 respondeu: a Líder no Comitê, a gestora pedagógica no Histórico e nos
    // Indicadores da Líder, e o superusuário diante do "ninguém mais" da decisão 78.
    for (const [p, texto, telas] of [
      ['P11', /A Líder do NFP vê o Comitê\?/, /Nos cartões: Comitê \(Semáforo\)\./],
      ['P12', /vê o Histórico do ICA e os Indicadores da Líder\?/, /Nos cartões: Histórico \(ICA\), Indicadores da Líder \(Semáforo\)\./],
      ['P13', /superusuário .*lê o momento reservado\?/, /Nos cartões: Ficha do município \(Semáforo\)\./],
      ['P14', /Quem faz a observação de formação do amarelo/, /Nos cartões: DFF \(no link atual\) \(DFF\)\./],
    ] as const) {
      const cartao = within(aberto).getByText(`${p}: em aberto — decidir no dia 7`).closest('li') as HTMLElement;
      expect(cartao, p).toHaveTextContent(texto);
      expect(cartao, p).toHaveTextContent(telas);
    }
    // A P1 ficou só com "quem é quem": não aponta mais para o Comitê.
    const p1 = within(aberto).getByText('P1: em aberto — decidir no dia 7').closest('li') as HTMLElement;
    expect(p1).not.toHaveTextContent(/Nos cartões/);
    // Respondidas em 26/11 (decisões 61 a 68, 87, 89, 90, 92 e 93).
    for (const p of ['P2', 'P3', 'P6', 'P8a', 'P8b', 'P9', 'P10']) {
      expect(within(aberto).queryByText(`${p}: em aberto — decidir no dia 7`)).not.toBeInTheDocument();
    }
    expect(aberto).toHaveTextContent(/quem é a Líder do NFP\?/);
    expect(aberto).not.toHaveTextContent(/a Diretoria entra na Integra\?/);
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
    // Decisão 76: era "até o dia 20 do segundo mês"; agora 10 dias úteis depois do envio do link.
    const pesquisa = await item(/10 dias/i);
    expect(pesquisa).toHaveTextContent(/10 dias úteis/);
    // O dia do envio (e daí as datas do ciclo atual) é leitura do protótipo: fica no ponto dele, sem selo.
    expect(await item(/^Quando a gestora manda o link da pesquisa\?$/)).toHaveTextContent(/01\/12\/2026.*15\/12\/2026/);
    expect(pesquisa).not.toHaveTextContent(/dia 20 do segundo mês/);
    // Decisões 77, 81 e 82: era "sem prazo"; agora vence no 5º dia útil e vem pré-preenchido.
    const relatorio = await item(/5º dia útil/i);
    expect(relatorio).toHaveTextContent(/07\/12\/2026/);
    expect(relatorio).toHaveTextContent(/Atrasado/);
    expect(relatorio).toHaveTextContent(/justificativa/);
    expect(relatorio).not.toHaveTextContent(/sem prazo/);
    // Decisão 48: marca antes, ata até 5 dias úteis depois, "ata atrasada".
    expect(await item(/ata da reunião de escuta/i)).toHaveTextContent(/ata atrasada/);
    // Decisão 51: a pesquisa é por projeto.
    expect(await item(/vários articuladores/i)).toHaveTextContent(/cada projeto/);
    expect(await item(/sem dado/i)).toHaveTextContent(/não conta para a cor/);
    const semResposta = await item(/município que não responde/i);
    expect(semResposta).toHaveTextContent(/enquanto o prazo está aberto/i);
    expect(semResposta).toHaveTextContent(/justificativa/);
    // Decisões 84 e 86: era "5 cartões"; Formar e Avaliar viram atalhos e a Avaliação do Coordenador se chama Tríade.
    expect(await item(/que outras ferramentas/i)).toHaveTextContent(/7 cartões: ICA, Semáforo, Deslocamento, DFF, Formar, Avaliar e Tríade/);
  });

  test('observação de formação: decisão 94, registrada na DFF e lida pelo Aprender Sistema', async () => {
    renderizar();
    const h3 = await screen.findByRole('heading', { level: 3, name: 'A Integra e as outras ferramentas' });
    const tema = h3.closest('section') as HTMLElement;
    const artigo = within(tema)
      .getByRole('heading', { level: 4, name: /Observação de formação: registrada no Semáforo ou feita na DFF/ })
      .closest('article') as HTMLElement;
    expect(artigo).toHaveTextContent(/coleta 6/);
    expect(artigo).toHaveTextContent(/Relatório mensal e formulários/);
    expect(artigo).toHaveTextContent(/o Aprender Sistema lê de lá/);
    expect(within(artigo).getByText('Decidido (decisão 94)')).toBeInTheDocument();
    // Era "Segue o PDF: a observação é registrada na tela Relatório mensal e formulários".
    expect(artigo).not.toHaveTextContent(/Segue o PDF/);
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
    // Decisão 54: Longo, pelo limite do próprio relatório.
    expect(craibas).toHaveTextContent(/Decidido \(decisão 54\)/);
    // Os dois números saem da mesma tabela: a pergunta era qual coluna o ICA usa. Decisão 55: 17h45.
    const mediana = await item(/Mediana: coluna Ida \(17h45\) ou coluna Ida e volta \(17h48\)\?/);
    expect(mediana).toHaveTextContent(/O relatório calcula a mediana pela coluna Ida/);
    expect(mediana).toHaveTextContent(/Decidido \(decisão 55\)/);
    expect(mediana).not.toHaveTextContent(/arredondou cada tempo para 5 minutos/);
    expect(within(mediana).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    // Decisão 56 ganhou um 2º cartão (como o protótipo contou no ICA): o título exato separa os dois.
    const amigos = await item(/^Amigos do Bem: em que município e estado\?$/);
    expect(amigos).toHaveTextContent(/Decidido \(decisão 56\)/);
    expect(amigos).toHaveTextContent(/o local é o de cada formação/);
  });

  test('o que a seção 7 do PDF pedia e o protótipo não media agora está decidido e medido (decisões 49 a 51)', async () => {
    renderizar();
    const lider = await item(/indicadores da Líder do NFP que o protótipo não media/i);
    expect(lider).toHaveTextContent(/tempo médio de resposta a ocorrências/i);
    expect(lider).toHaveTextContent(/convergência entre a pesquisa e as ocorrências/i);
    expect(lider).toHaveTextContent(/por projeto/);
    expect(lider).toHaveTextContent(/Decidido \(decisão 49\)/);
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

  test('Amigos do Bem: decisão 56, o tempo é o do local de cada formação (AL, CE ou PE)', async () => {
    renderizar();
    // Os estados vão pela UF: um dos nomes por extenso também é sobrenome e a guarda de nomes reais o pega.
    const amigos = await item(/^Amigos do Bem: em que município e estado\?$/);
    expect(amigos).toHaveTextContent(/em AL, CE ou PE/);
    // O protótipo mostra uma linha por local de formação, como o Aprender Sistema.
    expect(amigos).toHaveTextContent(/Mauriti-CE, Santana do Ipanema-AL e Petrolina-PE/);
    expect(amigos).toHaveTextContent(/Mauriti-CE não está no relatório/);
  });

  test('decisões 55 e 56 (rodada 3): o local conhecido que não está no relatório fica como leitura, fora do selo da 55', async () => {
    renderizar();
    const meio = await item(/^Mediana: coluna Ida \(17h45\) ou coluna Ida e volta \(17h48\)\?$/);
    expect(meio).toHaveTextContent(/para o município sem localidade definida/);
    expect(meio).not.toHaveTextContent(/local de formação que não está no relatório/);
    const local = await leitura(/^Local de formação conhecido que não está no relatório: que tempo usar\?$/);
    expect(local).toHaveTextContent(/Mauriti-CE/);
    expect(local).toHaveTextContent(/17h45/);
    // A exceção da contagem de estados (decisão 56): o CE de Mauriti não conta.
    expect(local).toHaveTextContent(/não entra na contagem de estados/);
    const conta = await item(/^Amigos do Bem no ICA: como o protótipo contou$/);
    expect(conta).toHaveTextContent(/não soma estado/);
  });

  test('decisão 56: como o protótipo contou o Amigos do Bem no ICA fica como leitura para o dono validar', async () => {
    renderizar();
    const conta = await item(/^Amigos do Bem no ICA: como o protótipo contou$/);
    expect(conta).toHaveTextContent(/cada local de formação conta como um município/);
    expect(conta).toHaveTextContent(/uma ida e volta/);
    expect(within(conta).queryByText(/^Decidido \(decisão/)).not.toBeInTheDocument();
    expect(within(conta).getByText('Como o protótipo resolveu por enquanto')).toBeInTheDocument();
  });

  test('vermelho imediato: decisão 38, a cor em vigor muda na hora e o Comitê confirma ou desfaz depois', async () => {
    renderizar();
    const publica = await item(/quando o Comitê publica/i);
    expect(publica).toHaveTextContent(/permite convocar o Comitê em caráter extraordinário/);
    expect(publica).not.toHaveTextContent(/chama uma reunião extraordinária/);
    expect(publica).toHaveTextContent(/data marcada pela SPE/);
    const imediato = await item(/vermelho imediato: a cor em vigor muda na hora/i);
    expect(imediato).toHaveTextContent(/O sistema muda a cor na hora/);
    expect(imediato).toHaveTextContent(/o Comitê confirma e publica/);
    expect(within(imediato).getByText(/Como o protótipo resolveu/)).toBeInTheDocument();
    expect(imediato).toHaveTextContent(/A cor em vigor muda na hora/);
    expect(imediato).toHaveTextContent(/canceladas pelo Comitê/);
    expect(imediato).not.toHaveTextContent(/só muda quando o Comitê publica/);
  });

  /** Os cartões das perguntas que o dono respondeu em 25/11 e 26/11 (decisões 30 a 94). */
  const DECIDIDOS: [RegExp, number][] = [
    [/^Média, NPS e cronograma: a cor sai do número exato$/, 30],
    [/^NPS: média das notas/, 31],
    [/^Ocorrências no trimestre: que trimestre\?$/, 32],
    [/^Prazos das tarefas/, 33],
    [/^.No bimestre. e .no semestre./, 35],
    [/^Quem faz cada tarefa de cada cor$/, 36],
    [/^Vermelho imediato: a cor em vigor muda na hora/, 38],
    [/^Três amarelos também mudam a cor na hora\?$/, 39],
    [/^Quando o Comitê publica a cor$/, 40],
    [/^Mesma cor confirmada de novo: as tarefas abrem de novo\?$/, 43],
    [/^O amarelo .em recuperação. recebe as tarefas do amarelo$/, 44],
    [/^A volta ao verde depois de um alerta$/, 45],
    [/^Um relatório mensal por município ou por coordenador\?$/, 46],
    [/^O .cronograma confirmado. da reunião de escuta entra na conta\?$/, 47],
    [/^Ata da reunião de escuta em até 5 dias úteis$/, 48],
    [/^Painel da gestora: atas a registrar$/, 48],
    [/^Os indicadores da Líder do NFP que o protótipo não media$/, 49],
    [/^Vários articuladores no mesmo município$/, 51],
    [/^Aviso quando o município piora para amarelo$/, 52],
    [/^16 ou 23 municípios só por terra\?$/, 53],
    [/^Craíbas-AL: Longo ou Muito longo\?$/, 54],
    [/^Mediana: coluna Ida/, 55],
    [/^Amigos do Bem: em que município e estado\?$/, 56],
    [/^Frente é município × coleção/, 59],
    [/^Quem é a gestora de referência de cada município/, 61],
    [/^A gestora com 29 municípios fica sozinha\?$/, 66],
    [/^Alerta de Sobrecarga: só quem entra/, 69],
    [/^Quem está sem municípios entra na conta/, 70],
    [/^Publicação em até 5 dias úteis/, 72],
    [/^Município que não responde à pesquisa$/, 75],
    [/^Pesquisa respondida em até 10 dias/, 76],
    [/^Relatório mensal até o 5º dia útil/, 77],
    [/^Quem vê o registro do momento reservado/, 78],
    [/^Indicador sem dado fica fora/, 79],
    [/^Painel do coordenador no Semáforo$/, 80],
    [/^Que outras ferramentas entram na Integra$/, 84],
    [/^Como avaliar a parte subjetiva/, 88],
    [/^Filtrar na DFF os formadores/, 93],
    [/^Observação de formação: registrada no Semáforo ou feita na DFF\?$/, 94],
  ];

  test('decisões 30 a 94: cada pergunta respondida pelo dono aparece como decidida, com o selo e a resposta', async () => {
    renderizar();
    for (const [titulo, numero] of DECIDIDOS) {
      const artigo = await item(titulo);
      expect(within(artigo).getByText(`Decidido (decisão ${numero})`), String(titulo)).toBeInTheDocument();
      // O par "Para decidir" vira "Decidido"; o rótulo do protótipo continua.
      const termos = within(artigo).getAllByRole('term').map((t) => t.textContent);
      expect(termos, String(titulo)).toEqual(['O que dizem', 'Como o protótipo resolveu', 'Decidido']);
    }
  });

  test('decisões 30 a 57: o selo de decidido usa o verde já conferido em contraste (o mesmo de "Vê")', async () => {
    renderizar();
    const selo = within(await item(/^Média, NPS e cronograma: a cor sai do número exato$/)).getByText('Decidido (decisão 30)');
    expect(selo).toHaveStyle({ background: '#E3F0EC' });
  });

  test('o que o dono ainda não decidiu continua "para decidir", e as leituras do protótipo ficam sem selo', async () => {
    renderizar();
    // Decisões 76 e 79: os 10 dias e o "sem dado" saíram desta lista (agora decididos).
    for (const titulo of [/vai dirigindo/i, /^Cronograma por projeto/, /^Relatório do último mês do ciclo/, /Ocorrências do ano: a partir de que dia conta/, /Convergência: quem entra na conta/]) {
      const artigo = await item(titulo);
      expect(within(artigo).queryByText(/^Decidido \(decisão/)).not.toBeInTheDocument();
      expect(within(artigo).getAllByRole('term').map((t) => t.textContent)).toEqual([
        'O que dizem',
        'Como o protótipo resolveu por enquanto',
        'Para decidir',
      ]);
    }
  });

  test('as contas que o protótipo escolheu na tela da Líder ficam como leitura para validar, sem selo de decidido', async () => {
    renderizar();
    const artigo = await item(/^Indicadores da Líder: como o protótipo fez as contas novas$/);
    expect(artigo).toHaveTextContent(/pelo nome do projeto/);
    expect(artigo).toHaveTextContent(/ocorrências do ano/);
    expect(artigo).toHaveTextContent(/todos os projetos dele responderam/);
    expect(within(artigo).queryByText(/^Decidido \(decisão/)).not.toBeInTheDocument();
    expect(within(artigo).getByText('Para decidir')).toBeInTheDocument();
  });

  // Rodada 1 de revisão: as leituras do protótipo que faltavam na pauta ficam sem selo, com "Para decidir".
  async function leitura(titulo: RegExp): Promise<HTMLElement> {
    const artigo = await item(titulo);
    expect(within(artigo).queryByText(/^Decidido \(decisão/)).not.toBeInTheDocument();
    expect(within(artigo).getByText('Para decidir')).toBeInTheDocument();
    return artigo;
  }

  test('decisões 32, 38 e 45: a régua de 1 e 2 ocorrências valendo o ano inteiro fica como leitura para o dono', async () => {
    renderizar();
    const regua = await leitura(/^Ocorrências do ano: a régua de 1 e 2 vale o ano inteiro\?$/);
    expect(regua).toHaveTextContent(/uma ocorrência leve deixa o indicador amarelo até janeiro/);
    expect(regua).toHaveTextContent(/duas no ano dão vermelho na hora/);
    // Decisão 45: enquanto a ocorrência conta, não há "2 ciclos sem alerta".
    expect(regua).toHaveTextContent(/não acontece enquanto a ocorrência contar/);
    expect(regua).toHaveTextContent(/Maringá-PR/);
    expect(regua).toHaveTextContent(/limites de 1 e 2 ocorrências continuam valendo para o ano inteiro/);
    // Rodada 5 (decisão 39): a ocorrência de outro ciclo também entra como um dos três amarelos (Pereiro-CE).
    expect(regua).toHaveTextContent(/três amarelos/);
    expect(regua).toHaveTextContent(/Pereiro-CE/);
    expect(regua).toHaveTextContent(/06\/06\/2026/);
    expect(regua).toHaveTextContent(/conta como amarelo .no mesmo ciclo./);
  });

  test('decisões 46 e 51: a média e o NPS do município juntando os projetos é leitura do protótipo, fora do cartão decidido', async () => {
    renderizar();
    expect(await item(/^Vários articuladores no mesmo município$/)).not.toHaveTextContent(/juntam as respostas de todos os projetos/);
    const media = await leitura(/^Média e NPS do município: juntar os projetos ou valer o pior\?$/);
    expect(media).toHaveTextContent(/juntam as respostas de todos os projetos/);
    expect(media).toHaveTextContent(/decisão 46/);
    // Rodada 5 (decisão 51): a nota de recomendação pergunta pelo projeto, não pela parceria inteira.
    expect(media).toHaveTextContent(/a nota de recomendação pergunta pelo projeto avaliado/);
  });

  test('decisões 46 e 52: o aviso de piora e o alerta de prazo vão para os coordenadores de todos os projetos', async () => {
    renderizar();
    const aviso = await leitura(/^Aviso e alerta de prazo: para qual coordenador\?$/);
    expect(aviso).toHaveTextContent(/coordenadores de todos os projetos do município/);
    expect(aviso).toHaveTextContent(/Por gerência/);
    expect(await item(/^Aviso quando o município piora para amarelo$/)).toHaveTextContent(/os coordenadores dos projetos/);
  });

  test('decisão 32: no município sem formação registrada no ano (projeto sem coordenador), nenhuma ocorrência conta', async () => {
    renderizar();
    const sem = await leitura(/^Município sem formação registrada no ano: a reclamação não conta\?$/);
    expect(sem).toHaveTextContent(/projeto sem coordenador/);
    expect(sem).toHaveTextContent(/Nenhuma que conte/);
  });

  test('decisão 50: o texto do tempo médio de resposta diz o ano do calendário, como a conta (não "a mesma janela da cor")', async () => {
    renderizar();
    const lider = await item(/^Indicadores da Líder: como o protótipo fez as contas novas$/);
    expect(lider).not.toHaveTextContent(/a mesma janela da cor/);
    expect(lider).toHaveTextContent(/de 1º de janeiro até hoje/);
    expect(lider).toHaveTextContent(/de antes da 1ª formação/);
  });

  test('decisões 39 e 45: a volta ao verde cita os três amarelos, que também valem na hora', async () => {
    renderizar();
    expect(await item(/^A volta ao verde depois de um alerta$/)).toHaveTextContent(/um vermelho, ou três amarelos, vale na hora/);
  });

  test('decisão 57: corrigir o relatório mensal guarda a versão anterior, e a pauta diz isso', async () => {
    renderizar();
    expect(await item(/^Relatório mensal de cada projeto$/)).toHaveTextContent(/a versão anterior fica guardada/);
  });

  test('de onde virá cada dado: os campos novos das decisões de 25/11 (36, 40, 41, 46, 48, 50 e 51)', async () => {
    renderizar();
    const pesquisa = await item(/^Pesquisa do articulador$/);
    expect(pesquisa).toHaveTextContent(/o projeto avaliado/i);
    expect(pesquisa).toHaveTextContent(/uma por projeto/);
    expect(await item(/^Ocorrências$/)).toHaveTextContent(/data e hora do registro e da resposta/);
    const reuniao = await item(/^Reunião de escuta$/);
    expect(reuniao).toHaveTextContent(/data marcada/);
    expect(reuniao).toHaveTextContent(/até 5 dias úteis/);
    expect(await item(/^Relatório mensal de cada projeto$/)).toHaveTextContent(/um por projeto e mês/);
    const comite = await item(/^Datas do Comitê$/);
    expect(comite).toHaveTextContent(/Não existe ainda/);
    expect(comite).toHaveTextContent(/extraordinário/);
    expect(await item(/^Coordenador de cada projeto$/)).toHaveTextContent(/Plano Anual/);
    const cor = await item(/^Cor do Semáforo$/);
    expect(cor).toHaveTextContent(/gestora pedagógica/);
    expect(cor).toHaveTextContent(/coordenadores/);
  });

  test('decisão 46: nenhum texto da página chama o projeto de contrato', async () => {
    renderizar();
    await screen.findByRole('heading', { level: 1 });
    expect(document.body.textContent ?? '').not.toMatch(/contrato/i);
  });

  // Rodada 2 de revisão: leituras que faltavam na pauta (sem selo; o dono decide no dia 7).
  test('decisões 42 a 44 e 57: ao sair do vermelho pelo ciclo, as tarefas abertas do vermelho continuam (Sobral-CE)', async () => {
    renderizar();
    const sair = await leitura(/^Quando o município sai do vermelho, as tarefas abertas do vermelho continuam\?$/);
    expect(sair).toHaveTextContent(/Sobral-CE/);
    expect(sair).toHaveTextContent(/15\/02\/2027/);
    expect(sair).toHaveTextContent(/decisão 57/);
  });

  test('decisão 33 (rodada 3): feriado em dia de semana conta como dia útil por decisão do dono, não por falta de calendário', async () => {
    renderizar();
    const prazos = await item(/^Prazos das tarefas: horas, dias corridos e dias úteis$/);
    expect(prazos).not.toHaveTextContent(/Feriados não entram na conta/);
    expect(prazos).not.toHaveTextContent(/não tem calendário de feriados/);
    expect(prazos).toHaveTextContent(/Feriado em dia de semana conta como dia útil/);
    // A pergunta 29 (a) tinha a opção de descontar os feriados; o dono escolheu dias úteis de segunda a sexta.
    const feriados = await item(/^Feriados contam como dia útil nos prazos\?$/);
    expect(within(feriados).getByText('Decidido (decisão 33)')).toBeInTheDocument();
    expect(feriados).not.toHaveTextContent(/sem falar de feriados/);
    expect(feriados).toHaveTextContent(/descontando também os feriados/);
    expect(feriados).toHaveTextContent(/Horizonte-CE/);
    expect(feriados).toHaveTextContent(/11\/01\/2027/);
    expect(feriados).toHaveTextContent(/25\/12 e 01\/01/);
  });

  test('decisão 51: a segunda resposta do mesmo projeto é recusada, mesmo de outra pessoa; fica como leitura', async () => {
    renderizar();
    const uma = await leitura(/^Uma resposta por projeto: e se outra pessoa do mesmo projeto já respondeu\?$/);
    expect(uma).toHaveTextContent(/secretário/i);
    expect(uma).toHaveTextContent(/recusada/);
  });

  test('decisões 34 e 50: a meta de 48 h da resposta à ocorrência conta horas corridas; fica como leitura', async () => {
    renderizar();
    const meta = await leitura(/^Meta de 48 h da resposta à ocorrência: horas corridas ou dias úteis\?$/);
    expect(meta).toHaveTextContent(/66 h/);
    expect(meta).toHaveTextContent(/2 dias úteis/);
  });

  test('decisão 36: quem faz a observação de formação do amarelo e quem recebe o alerta do prazo fica como leitura', async () => {
    renderizar();
    const obs = await leitura(/^Observação de formação do amarelo: quem faz e quem recebe o alerta do prazo\?$/);
    expect(obs).toHaveTextContent(/gestora pedagógica/);
    expect(obs).toHaveTextContent(/decisão 36/);
    // Decisão 94: não há mais formulário da observação no Semáforo.
    expect(obs).toHaveTextContent(/registrada na DFF \(decisão 94\)/);
    expect(obs).not.toHaveTextContent(/o formulário da observação/);
  });

  test('decisão 38: dado registrado com atraso; o vermelho na hora nunca fica antes da decisão em vigor', async () => {
    renderizar();
    const atraso = await leitura(/^Dado registrado com atraso: as tarefas contam do dia do dado ou do dia do registro\?$/);
    expect(atraso).toHaveTextContent(/Sobral-CE/);
    expect(atraso).toHaveTextContent(/27\/11/);
    expect(atraso).toHaveTextContent(/decisão que estava em vigor/);
    // Rodada 3: uma queixa leve só deixa amarelo; o exemplo do vermelho é com uma reclamação.
    expect(atraso).toHaveTextContent(/uma reclamação no momento reservado deixa o município vermelho desde 27\/11/);
  });

  test('decisões 48 e 50 (rodada 3): a queixa do momento reservado conta o tempo de resposta do registro da ata; fica como leitura', async () => {
    renderizar();
    const queixa = await leitura(/^Queixa feita na reunião e registrada com a ata: de onde conta o tempo de resposta\?$/);
    expect(queixa).toHaveTextContent(/momento reservado/);
    expect(queixa).toHaveTextContent(/conta do dia e da hora em que a ata é registrada/);
    expect(queixa).toHaveTextContent(/5 dias úteis/);
  });

  test('decisão 42 (rodada 3): só o vermelho desfeito pelo Comitê cancela as tarefas; as do amarelo seguem abertas', async () => {
    renderizar();
    const confirmar = await item(/^Confirmar o vermelho na hora não reabre as tarefas$/);
    expect(confirmar).toHaveTextContent(/mesmo quando o Comitê muda o amarelo no mesmo ciclo/);
    expect(confirmar).toHaveTextContent(/só as do vermelho que o Comitê desfaz ficam canceladas/);
  });

  test('decisão 49 (rodada 3): a convergência diz que as ocorrências contam o ano e a pesquisa, só o ciclo', async () => {
    renderizar();
    const conv = await leitura(/^Convergência: quem entra na conta e o que é "concordar"$/);
    expect(conv).toHaveTextContent(/ocorrências do ano até o fim do ciclo \(decisão 32\)/);
    expect(conv).toHaveTextContent(/a pesquisa é só a do ciclo/);
  });

  test('decisões 33 e 35 (rodada 3): o prazo em meses que cai no fim de semana passa para a segunda-feira; fica como leitura', async () => {
    renderizar();
    const fim = await leitura(/^Prazo em meses que cai no sábado ou no domingo$/);
    expect(fim).toHaveTextContent(/31\/05\/2027/);
    expect(fim).toHaveTextContent(/segunda-feira/);
  });

  test('decisão 35 (rodada 4): o exemplo do prazo em meses bate com a conta (31/12/2026 + 2 meses dá domingo, vence na segunda 01/03/2027)', async () => {
    renderizar();
    const bimestre = await item(/^"No bimestre" e "no semestre": a partir de quando\?$/);
    expect(bimestre).toHaveTextContent(/28\/02\/2027, um domingo.*01\/03\/2027/);
    expect(bimestre).not.toHaveTextContent(/31\/12 mais 2 meses dá 28\/02\)/);
  });

  test('decisões 46 e 51 (rodada 4): o Amigos do Bem fica fora do Semáforo; fica como leitura', async () => {
    renderizar();
    const fora = await leitura(/^Amigos do Bem no Semáforo: entra\?$/);
    expect(fora).toHaveTextContent(/fica fora do Semáforo/);
    expect(fora).toHaveTextContent(/Petrolina-PE e Santana do Ipanema-AL/);
  });

  test('decisões 46 e 47 (rodada 4): mais formações realizadas que previstas no mês; fica como leitura', async () => {
    renderizar();
    const mais = await leitura(/^Relatório mensal com mais formações realizadas que previstas$/);
    expect(mais).toHaveTextContent(/aceita/);
    expect(mais).toHaveTextContent(/pode passar de 100%/);
    // Decisões 81 e 82: só as formações são digitadas, e mudar um número do sistema pede justificativa.
    expect(mais).not.toHaveTextContent(/visitas realizadas que previstas/);
    expect(mais).toHaveTextContent(/visitas vêm da Logística e do pedido de viagem \(FRV\)/);
    expect(mais).toHaveTextContent(/justificativa/);
  });

  test('decisões 73 e 76: o dia em que a gestora manda o link é leitura do protótipo, fora do cartão decidido', async () => {
    renderizar();
    const envio = await leitura(/^Quando a gestora manda o link da pesquisa\?$/);
    expect(envio).toHaveTextContent(/1º dia útil do segundo mês do ciclo/);
    expect(envio).toHaveTextContent(/01\/12\/2026/);
    expect(await item(/^Pesquisa respondida em até 10 dias após o envio$/)).not.toHaveTextContent(/1º dia útil/);
  });

  test('decisões 81 e 82: quando a justificativa é obrigatória e se a visita pode ser corrigida ficam como leitura', async () => {
    renderizar();
    const relatorio = await leitura(/^Relatório mensal: quando o coordenador justifica, e as visitas podem ser corrigidas\?$/);
    expect(relatorio).toHaveTextContent(/só quando o coordenador muda um número que veio do sistema/);
    expect(relatorio).toHaveTextContent(/visita/);
  });

  test('decisões 61 e 62: o que a gestora compartilhada faz fica como leitura; só o momento reservado foi decidido', async () => {
    renderizar();
    const compartilhada = await leitura(/^Gestora compartilhada: o que ela faz no município\?$/);
    expect(compartilhada).toHaveTextContent(/decisão 62/);
  });

  test('decisões 20 e 58: quem grava na carteira o remanejamento aplicado fica como leitura', async () => {
    renderizar();
    const carteira = await leitura(/^Quem grava na carteira o remanejamento aplicado\?$/);
    expect(carteira).toHaveTextContent(/decisão 58/);
    expect(carteira).toHaveTextContent(/decisão 20/);
    expect(await item(/^Coordenador de cada projeto$/)).toHaveTextContent(/decisão 58/);
  });

  test('"Já decidido" não promete selo nos cartões para as decisões que não têm ponto na primeira parte', async () => {
    renderizar();
    const secao = (await screen.findByRole('heading', { name: 'Já decidido' })).closest('section') as HTMLElement;
    expect(secao).not.toHaveTextContent(/decisões 30 a 94\), que também aparecem nos cartões/);
    expect(secao).toHaveTextContent(/as que respondem a um ponto da primeira parte também aparecem no cartão dele/);
  });

  test('decisões 33 e 34 (rodada 4): o alerta "um dia antes" conta o dia útil; fica como leitura', async () => {
    renderizar();
    const antes = await leitura(/^Alerta de prazo "um dia antes": dia corrido ou dia útil\?$/);
    expect(antes).toHaveTextContent(/na sexta-feira, avisa a tarefa que vence na segunda/);
  });

  test('rodada 5 (decisão 50): a ocorrência sem resposta passada das 48 h fica fora da conta da meta; fica como leitura', async () => {
    renderizar();
    const semResposta = await leitura(/^Ocorrência sem resposta há mais de 48 h: conta como fora da meta\?$/);
    expect(semResposta).toHaveTextContent(/só as ocorrências já respondidas/);
    expect(semResposta).toHaveTextContent(/Sem resposta/);
  });

  test('rodada 5: o relatório mensal entra só nos meses do ciclo atual; a virada do ciclo fica para o dono', async () => {
    renderizar();
    const relatorio = await item(/^Relatório mensal até o 5º dia útil do mês seguinte$/);
    expect(relatorio).not.toHaveTextContent(/a qualquer momento/);
    expect(relatorio).toHaveTextContent(/só para os meses do ciclo atual, até o mês corrente/);
    expect(relatorio).toHaveTextContent(/até o 5º dia útil/);
    expect(relatorio).toHaveTextContent(/antes de o mês terminar/);
    expect(relatorio).toHaveTextContent(/ocorrência de um ciclo que já fechou/);
    // Decisão 77 fechou o prazo; a virada do ciclo continua como leitura num cartão à parte.
    const virada = await leitura(/^Relatório do último mês do ciclo/);
    expect(virada).toHaveTextContent(/começo do ciclo seguinte/);
    expect(virada).toHaveTextContent(/ocorrência de um ciclo que já fechou/);
  });

  test('rodada 5: a reunião de escuta marcada na tela é uma por vez, a 30 dias ou mais da outra; fica como leitura', async () => {
    renderizar();
    const reuniao = await leitura(/^Reunião de escuta: uma por vez, a 30 dias ou mais da outra\?$/);
    expect(reuniao).toHaveTextContent(/Jequié-BA/);
    expect(reuniao).toHaveTextContent(/periodicidade sai da cor em vigor/);
  });

  test('rodada 5 (decisões 42, 43 e 57): desfazer o vermelho na hora devolve a tarefa que ele tinha substituído; fica como leitura', async () => {
    renderizar();
    const desfazer = await leitura(/^O Comitê desfaz o vermelho na hora: a tarefa que ele substituiu volta\?$/);
    expect(desfazer).toHaveTextContent(/Sobral-CE/);
    expect(desfazer).toHaveTextContent(/15\/02\/2027/);
    expect(desfazer).toHaveTextContent(/volta a ficar aberta/);
  });

  test('decisão 36 (rodada 3): a reunião de escuta tem situação (a agendar e em dia); só a pesquisa e o acompanhamento são texto', async () => {
    renderizar();
    const quem = await item(/^Quem faz cada tarefa de cada cor$/);
    expect(quem).not.toHaveTextContent(/sem prazo nem situação/);
    expect(quem).toHaveTextContent(/a agendar/);
  });

  test('as leituras das regras do Semáforo que ficaram para validar no dia 7', async () => {
    renderizar();
    const h3 = await screen.findByRole('heading', { level: 3, name: 'Semáforo: como o protótipo leu o PDF' });
    const tema = h3.closest('section') as HTMLElement;
    const esperados: [RegExp, RegExp][] = [
      // Decisão 30: o número exato, com 2 casas na tela.
      [/número exato/i, /3,95 é amarelo/],
      [/número exato/i, /89,50%/],
      // Decisão 31: maior, menor e média; a cor sai da média.
      [/NPS: média das notas/i, /8,5 é amarelo/],
      [/NPS: média das notas/i, /a maior nota, a menor e a média/],
      // Decisão 32: desde a 1ª formação do ano; zera em janeiro; o histórico fica.
      [/ocorrências no trimestre/i, /desde a 1ª formação do ano/],
      [/ocorrências no trimestre/i, /fica guardado/],
      // Decisões 33 e 34: dias úteis; publicada na sexta 04/12, o contato vence na terça 08/12.
      [/prazos das tarefas/i, /dias úteis/],
      [/prazos das tarefas/i, /04\/12\/2026.*08\/12\/2026.*11\/12\/2026/],
      [/no bimestre.*no semestre/i, /2 e 6 meses depois da publicação/],
      [/três amarelos/i, /vermelho na hora/],
      [/três amarelos/i, /extraordinário/],
      [/volta ao verde/i, /2 ciclos seguidos sem alerta/],
      [/volta ao verde/i, /ciclo em andamento .*não soma/],
      // Seção 4: no meio do ciclo a cor só muda para piorar; um amarelo não tira o município do vermelho.
      [/volta ao verde/i, /só muda na hora para piorar.*Sair do vermelho espera o ciclo fechar/],
      // Decisões 36 e 37: as duas gestoras juntas; o contato é com o articulador municipal.
      [/quem faz cada tarefa/i, /Contato com o articulador municipal/],
      // Escolhas que os relatórios de implementação mandaram confirmar no dia 7.
      [/quando o Comitê publica/i, /sexta-feira.*02\/12\/2026/],
      // Decisão 43: a mesma cor publicada de novo reabre as tarefas; as abertas de antes ficam substituídas.
      [/mesma cor confirmada de novo/i, /reabre todas as tarefas da cor/],
      [/em recuperação. recebe as tarefas do amarelo/i, /10 dias úteis/],
      // Decisão 46: cada projeto manda o seu relatório.
      [/um relatório mensal por município ou por coordenador/i, /cada projeto/],
      [/cronograma confirmado.*reunião de escuta/i, /coleta 4/],
      // Decisão 47: a formação adiada de comum acordo é só observação.
      [/cronograma confirmado.*reunião de escuta/i, /só observação/],
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
