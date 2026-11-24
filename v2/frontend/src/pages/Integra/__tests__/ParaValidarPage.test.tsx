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

/** O item (article) cujo título casa com o texto. */
async function item(titulo: RegExp): Promise<HTMLElement> {
  const h = await screen.findByRole('heading', { name: titulo });
  return h.closest('article, li') as HTMLElement;
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
    expect(await item(/^Tempo de deslocamento$/)).toHaveTextContent(/Logística e FRV/);
    expect(await item(/^Status ativo ou suspenso$/)).toHaveTextContent(/Não existe ainda/);
    expect(await item(/^Gestora de referência$/)).toHaveTextContent(/Não existe ainda/);
    expect(await item(/^Pesquisa do articulador$/)).toHaveTextContent(/Não existe ainda/);
    expect(await item(/^Ocorrências$/)).toHaveTextContent(/Não existe ainda/);
    expect(await item(/^Observação de formação$/)).toHaveTextContent(/DFF/);
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
