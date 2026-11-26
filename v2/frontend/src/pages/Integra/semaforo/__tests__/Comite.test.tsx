/**
 * Semáforo — Comitê de Satisfação (DADOS SIMULADOS): a cor sugerida pela regra para cada município no
 * ciclo atual, confirmar ou alterar (alterar exige justificativa), a seta de mudança desde o ciclo
 * anterior, o filtro por cor e o "sem dado" explicado.
 */
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test } from 'vitest';

import { QUEM_VE } from '../../quemVe';
import { avaliarMunicipio, gerarDadosSemaforo, HISTORIAS_SEMAFORO } from '../dados';
import { renderTelaSemaforo } from './telaSemaforo';

const DADOS = gerarDadosSemaforo();
const idDe = (h: { nome: string; uf: string }): number => DADOS.municipios.find((m) => m.nome === h.nome && m.uf === h.uf)!.id;

async function abrir(): Promise<void> {
  renderTelaSemaforo('/integra/semaforo/comite');
  await screen.findByText('Comitê de Satisfação');
}

const cartoes = (): HTMLElement[] => within(screen.getByRole('list', { name: /Municípios do ciclo 2026\.6/ })).getAllByRole('article');
// Pelo texto do título, e não por getByRole('article', { name }): calcular o nome de todos os cartões a cada busca
// deixava o teste lento demais na CI (passava de 20 s). O cartão continua achado pelo título dele.
const cartao = (nome: string): HTMLElement => screen.getByText(nome, { selector: 'h3 a' }).closest('article')!;

describe('Comitê', { timeout: 20000 }, () => {
  test('título, aviso de quem vê na versão real e o "sem dado" explicado', async () => {
    await abrir();
    expect(screen.getByRole('heading', { level: 1, name: 'Comitê de Satisfação' })).toBeInTheDocument();
    expect(screen.getByText(QUEM_VE.comite.aviso)).toBeInTheDocument();
    const semDado = screen.getByText(/^Sem dado:/);
    expect(semDado).toHaveTextContent(/fica fora da regra/);
    // Decisão 76: a pesquisa fica aberta 10 dias úteis depois do envio do link (01/12): até 15/12.
    expect(semDado).toHaveTextContent(/15\/12\/2026/);
    // O ciclo vem com os meses: no ICA, o mesmo formato quer dizer semestre.
    const intro = screen.getByText(/^A cor sugerida sai da regra do Semáforo/);
    expect(intro).toHaveTextContent('com os dados do ciclo 2026.6 (novembro e dezembro de 2026) até hoje');
    expect(intro).toHaveTextContent('publicada no ciclo 2026.5 (setembro e outubro de 2026)');
  });

  test('resumo das cores sugeridas, com o nome e o número', async () => {
    await abrir();
    const resumo = screen.getByRole('list', { name: 'Cores sugeridas no ciclo 2026.6' });
    // Contagem da história re-ajustada (decisões 32 e 49, ver dados.test.ts).
    expect(resumo).toHaveTextContent('Vermelho: 3');
    expect(resumo).toHaveTextContent('Amarelo: 18');
    expect(resumo).toHaveTextContent('Verde: 67');
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
    expect(sobral).toHaveTextContent('Ainda sem decisão neste ciclo. Em vigor: Amarelo');
    // Jequié ainda não respondeu a pesquisa do ciclo (a história): o cartão diz o que ficou sem dado.
    expect(cartao('Jequié-BA')).toHaveTextContent('Sem dado neste ciclo, fora da regra: Média da pesquisa do articulador');
  });

  test('filtro por cor sugerida', async () => {
    await abrir();
    await userEvent.click(screen.getByRole('radio', { name: /Amarelo/ }));
    expect(cartoes()).toHaveLength(18);
    expect(cartao('Sobral-CE')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: /Vermelho/ }));
    // Jequié segue vermelho: não respondeu a pesquisa em 2026.4 e 2026.5, e o ciclo atual ainda não fechou.
    // Mucambo segue vermelho pelo NPS de 2026.5 (decisão 49: pesquisa e ocorrências divergem).
    expect(cartoes().map((c) => within(c).getByRole('heading').textContent)).toEqual(['Horizonte-CE', 'Jequié-BA', 'Mucambo-CE']);
    await userEvent.click(screen.getByRole('radio', { name: /Todas/ }));
    expect(cartoes()).toHaveLength(88);
  });

  test('confirmar a cor sugerida publica a decisão com a data de hoje', async () => {
    await abrir();
    // Maringá: a ocorrência leve de 2026.5 segue contando no ano (decisão 32), então a sugerida é amarelo.
    await userEvent.click(within(cartao('Maringá-PR')).getByRole('button', { name: /Confirmar Amarelo/ }));
    expect(screen.getByRole('status')).toHaveTextContent('Publicado: Maringá-PR em Amarelo.');
    expect(cartao('Maringá-PR')).toHaveTextContent('Decisão deste ciclo: Amarelo, publicada em 07/12/2026');
  });

  test('leitura do protótipo: ao publicar, o aviso diz quais tarefas de outra cor continuam abertas (Sobral-CE, visita técnica do vermelho)', async () => {
    await abrir();
    await userEvent.click(within(cartao('Sobral-CE')).getByRole('button', { name: /Confirmar Amarelo/ }));
    expect(screen.getByRole('status')).toHaveTextContent(
      'As tarefas abertas do vermelho que vinham de antes continuam abertas: Visita técnica.',
    );
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

  test('decisão 41: a decisão do Comitê extraordinário diz de onde veio', async () => {
    await abrir();
    expect(cartao('Horizonte-CE')).toHaveTextContent(
      'Decisão deste ciclo: Vermelho, publicada em 02/12/2026 pelo Comitê extraordinário',
    );
  });

  test('decisão 40: a SPE marca a data do Comitê ordinário; data antes de hoje é recusada', async () => {
    await abrir();
    const datas = screen.getByRole('region', { name: 'Datas do Comitê' });
    expect(datas).toHaveTextContent('Próximo Comitê ordinário, na data marcada pela SPE: 08/01/2027');
    expect(datas).toHaveTextContent('Comitê extraordinário deste ciclo, convocado pela SPE: 02/12/2026');
    const campo = within(datas).getByLabelText('Data do próximo Comitê ordinário');
    expect(campo).toHaveValue('2027-01-08');
    expect(campo).toHaveAttribute('min', '2026-12-07');

    await userEvent.clear(campo);
    await userEvent.type(campo, '2026-12-01');
    await userEvent.click(within(datas).getByRole('button', { name: 'Marcar a data' }));
    expect(within(datas).getByRole('alert')).toHaveTextContent('A SPE marca a data do Comitê a partir de hoje (07/12/2026).');

    await userEvent.clear(campo);
    await userEvent.type(campo, '2026-12-18');
    await userEvent.click(within(datas).getByRole('button', { name: 'Marcar a data' }));
    expect(screen.getByRole('status')).toHaveTextContent('Comitê ordinário marcado para 18/12/2026.');
    expect(datas).toHaveTextContent('Próximo Comitê ordinário, na data marcada pela SPE: 18/12/2026');
    expect(within(datas).queryByRole('alert')).not.toBeInTheDocument();
  });

  test('decisão 41: a SPE convoca o extraordinário; a decisão de hoje vale como dele', async () => {
    await abrir();
    const datas = screen.getByRole('region', { name: 'Datas do Comitê' });
    expect(datas).toHaveTextContent(/a critério da SPE/);
    await userEvent.click(within(datas).getByRole('button', { name: 'Convocar o Comitê extraordinário para hoje' }));
    expect(screen.getByRole('status')).toHaveTextContent('Comitê extraordinário convocado para hoje (07/12/2026).');
    expect(datas).toHaveTextContent('Comitê extraordinário deste ciclo, convocado pela SPE: 02/12/2026 e 07/12/2026');
    await userEvent.click(within(cartao('Maringá-PR')).getByRole('button', { name: /Confirmar Amarelo/ }));
    expect(cartao('Maringá-PR')).toHaveTextContent('Decisão deste ciclo: Amarelo, publicada em 07/12/2026 pelo Comitê extraordinário');
  });

  test('o texto da tela diz a regra nova: o vermelho muda na hora; o Comitê confirma ou desfaz (decisões 38 a 41)', async () => {
    await abrir();
    const intro = screen.getByText(/^A cor sugerida sai da regra do Semáforo/);
    expect(intro).toHaveTextContent(/Um indicador em vermelho ou três amarelos mudam a cor em vigor para vermelho na hora/);
    expect(intro).toHaveTextContent(/o Comitê confirma ou desfaz depois/);
  });

  describe('vermelho na hora ainda sem o Comitê (decisões 38 e 42)', () => {
    // Sem a decisão do extraordinário de 02/12, Horizonte fica com o vermelho na hora de 30/11 esperando o Comitê.
    const ultima = DADOS.decisoes.filter((d) => d.municipio === idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje)).at(-1);
    const SEM_COMITE = { ...DADOS, decisoes: DADOS.decisoes.filter((d) => d !== ultima) };

    async function abrirSemComite(): Promise<void> {
      renderTelaSemaforo('/integra/semaforo/comite', SEM_COMITE);
      await screen.findByText('Comitê de Satisfação');
    }

    test('o cartão diz que o vermelho valeu na hora e oferece confirmar ou desfazer', async () => {
      await abrirSemComite();
      const horizonte = cartao('Horizonte-CE');
      expect(horizonte).toHaveTextContent(
        'Vermelho na hora em 30/11/2026: a cor em vigor mudou e as tarefas do vermelho começaram. O Comitê confirma ou desfaz.',
      );
      // Rodada 1 de revisão: no vermelho na hora, os botões partem do vermelho em vigor, não da sugerida.
      expect(within(horizonte).getByRole('button', { name: 'Confirmar o vermelho para Horizonte-CE' })).toBeInTheDocument();
      expect(within(horizonte).getByRole('button', { name: 'Desfazer o vermelho de Horizonte-CE' })).toBeInTheDocument();
    });

    test('confirmar: as tarefas seguem', async () => {
      await abrirSemComite();
      await userEvent.click(within(cartao('Horizonte-CE')).getByRole('button', { name: /Confirmar o vermelho/ }));
      expect(screen.getByRole('status')).toHaveTextContent(
        'Publicado: Horizonte-CE em Vermelho. O Comitê confirmou o vermelho na hora: as tarefas seguem.',
      );
    });

    test('desfazer: as tarefas abertas do vermelho ficam canceladas pelo Comitê, e as feitas continuam (decisões 42 e 57)', async () => {
      const user = userEvent.setup();
      await abrirSemComite();
      await user.click(within(cartao('Horizonte-CE')).getByRole('button', { name: /Desfazer o vermelho/ }));
      const horizonte = cartao('Horizonte-CE');
      // Desfazer o vermelho não oferece o próprio vermelho.
      expect(within(horizonte).getAllByRole('radio').map((r) => r.getAttribute('value'))).toEqual(['amarelo', 'verde']);
      await user.click(within(horizonte).getByRole('radio', { name: 'Amarelo' }));
      // paste: digitar letra a letra numa tela com 88 cartões estoura o tempo na CI.
      await user.click(within(horizonte).getByLabelText('Justificativa do Comitê'));
      await user.paste('A reclamação foi resolvida com a Secretaria.');
      await user.click(within(horizonte).getByRole('button', { name: 'Publicar a cor alterada' }));
      expect(screen.getByRole('status')).toHaveTextContent(
        'Publicado: Horizonte-CE em Amarelo. As tarefas abertas do vermelho ficam canceladas pelo Comitê; as feitas continuam registradas.',
      );
      // Horizonte tinha amarelo publicado em 2026.5, com tarefa do amarelo ainda aberta: o aviso diz que ela fica substituída.
      expect(screen.getByRole('status')).toHaveTextContent(
        'As tarefas do amarelo começam hoje; as que estavam abertas do amarelo ficam substituídas.',
      );

      await user.click(within(cartao('Horizonte-CE')).getByRole('link', { name: 'Horizonte-CE' }));
      await screen.findByText('Ficha do município');
      const tarefas = within(screen.getByRole('table', { name: /Tarefas e prazos/ }))
        .getAllByRole('row')
        .slice(1)
        .map((l) => l.textContent ?? '');
      expect(tarefas.find((t) => t.startsWith('Reunião com a Secretaria'))).toMatch(/Cancelada pelo Comitê em 07\/12\/2026/);
      expect(tarefas.find((t) => t.startsWith('Contato com o articulador municipal'))).toMatch(/Concluída em 01\/12\/2026/);
    });
  });

  describe('vermelho na hora com a sugerida que já mudou (o registro que deu o vermelho foi corrigido)', () => {
    // Sem a reclamação de 30/11 e sem o extraordinário, a sugerida de Horizonte volta a Amarelo, e o vermelho na hora fica.
    const id = idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const ultima = DADOS.decisoes.filter((d) => d.municipio === id).at(-1);
    const SUGERIDA_MUDOU = {
      ...DADOS,
      decisoes: DADOS.decisoes.filter((d) => d !== ultima),
      ocorrencias: DADOS.ocorrencias.filter((o) => !(o.municipio === id && o.tipo === 'reclamacao')),
    };

    async function abrirSugeridaMudou(): Promise<HTMLElement> {
      renderTelaSemaforo('/integra/semaforo/comite', SUGERIDA_MUDOU);
      await screen.findByText('Comitê de Satisfação');
      return cartao('Horizonte-CE');
    }

    test('o cartão diz que a sugerida agora é outra, e os botões partem do vermelho em vigor', async () => {
      const horizonte = await abrirSugeridaMudou();
      expect(horizonte).toHaveTextContent('Sugerida: Amarelo');
      expect(horizonte).toHaveTextContent('A cor sugerida agora é Amarelo.');
      expect(within(horizonte).queryByRole('button', { name: /Confirmar Amarelo/ })).not.toBeInTheDocument();
      expect(within(horizonte).getByRole('button', { name: 'Confirmar o vermelho para Horizonte-CE' })).toBeInTheDocument();
    });

    test('confirmar o vermelho com a sugerida diferente pede a justificativa', async () => {
      const user = userEvent.setup();
      await user.click(within(await abrirSugeridaMudou()).getByRole('button', { name: /Confirmar o vermelho/ }));
      const horizonte = cartao('Horizonte-CE');
      expect(within(horizonte).queryByRole('radio')).not.toBeInTheDocument();
      await user.click(within(horizonte).getByRole('button', { name: 'Publicar o vermelho' }));
      expect(within(horizonte).getByRole('alert')).toHaveTextContent('A cor é diferente da sugerida (Amarelo). Escreva a justificativa do Comitê.');
      await user.click(within(horizonte).getByLabelText('Justificativa do Comitê'));
      await user.paste('A Secretaria confirmou a reclamação.');
      await user.click(within(horizonte).getByRole('button', { name: 'Publicar o vermelho' }));
      expect(screen.getByRole('status')).toHaveTextContent(
        'Publicado: Horizonte-CE em Vermelho. O Comitê confirmou o vermelho na hora: as tarefas seguem.',
      );
    });

    test('desfazer o vermelho oferece só verde e amarelo, e a legenda diz a sugerida de agora', async () => {
      const user = userEvent.setup();
      await user.click(within(await abrirSugeridaMudou()).getByRole('button', { name: /Desfazer o vermelho/ }));
      const horizonte = cartao('Horizonte-CE');
      expect(within(horizonte).getByRole('group', { name: 'Nova cor (a sugerida agora é Amarelo)' })).toBeInTheDocument();
      expect(within(horizonte).getAllByRole('radio').map((r) => r.getAttribute('value'))).toEqual(['amarelo', 'verde']);
      // Voltar à sugerida não pede justificativa (a regra da tela: só quando a cor publicada difere da sugerida).
      expect(within(horizonte).getByText('Obrigatória se a nova cor for diferente da sugerida (Amarelo).')).toBeInTheDocument();
    });
  });

  test('decisão 42 só vale para o vermelho: confirmar amarelo e depois mudar para vermelho no mesmo ciclo deixa as tarefas do amarelo abertas', async () => {
    const user = userEvent.setup();
    const s = DADOS.municipios
      .map((m) => avaliarMunicipio(DADOS, m.id))
      .find((x) => x.ciclos.at(-1)!.resultado.cor === 'amarelo' && x.ciclos.at(-1)!.decisao === null && x.cor_vigente === 'verde')!;
    const nome = `${DADOS.municipios.find((m) => m.id === s.municipio)!.nome}-${DADOS.municipios.find((m) => m.id === s.municipio)!.uf}`;
    await abrir();
    await user.click(within(cartao(nome)).getByRole('button', { name: `Confirmar Amarelo para ${nome}` }));
    await user.click(within(cartao(nome)).getByRole('button', { name: `Alterar a cor de ${nome}` }));
    await user.click(within(cartao(nome)).getByRole('radio', { name: 'Vermelho' }));
    await user.click(within(cartao(nome)).getByLabelText('Justificativa do Comitê'));
    await user.paste('A Secretaria pediu ajuda.');
    await user.click(within(cartao(nome)).getByRole('button', { name: 'Publicar a cor alterada' }));
    const aviso = screen.getByRole('status');
    expect(aviso).toHaveTextContent(`Publicado: ${nome} em Vermelho.`);
    expect(aviso).not.toHaveTextContent('canceladas pelo Comitê');
    expect(aviso).toHaveTextContent(/As tarefas abertas do amarelo que vinham de antes continuam abertas/);
  });

  test('o nome do município abre a ficha', async () => {
    await abrir();
    expect(within(cartao('Horizonte-CE')).getByRole('link', { name: 'Horizonte-CE' })).toHaveAttribute(
      'href',
      `/integra/semaforo/municipio/${idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje)}`,
    );
  });
});
