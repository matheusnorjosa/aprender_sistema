/** Quem vê cada tela da Integra na versão real: a matriz de cargos × telas e o aviso de cada tela. */
import { describe, expect, test } from 'vitest';

import { DECIDIDO, PAPEIS, PERGUNTAS_EM_ABERTO, QUEM_VE, TELAS, type ChaveTela } from '../quemVe';

const TELAS_ICA: ChaveTela[] = ['painel', 'coordenador', 'simulador', 'pesos', 'gerencias', 'comparativo', 'historico', 'alertas'];
const TELAS_SEMAFORO: ChaveTela[] = ['comite', 'municipio', 'gestora', 'pesquisa', 'lider', 'relatorio-mensal'];

describe('quem vê cada tela na versão real', () => {
  test('tem as 8 telas do ICA, as 6 do Semáforo, o Deslocamento e a DFF, nessa ordem', () => {
    expect(TELAS).toEqual([...TELAS_ICA, ...TELAS_SEMAFORO, 'deslocamento', 'dff']);
    for (const t of TELAS_ICA) expect(QUEM_VE[t].modulo).toBe('ICA');
    for (const t of TELAS_SEMAFORO) expect(QUEM_VE[t].modulo).toBe('Semáforo');
    expect(QUEM_VE.deslocamento.modulo).toBe('Deslocamento');
    expect(QUEM_VE.dff.modulo).toBe('DFF');
  });

  test('cada tela diz o que cada papel faz, e o aviso começa pela frase combinada', () => {
    for (const t of TELAS) {
      for (const p of PAPEIS) {
        const c = QUEM_VE[t].quem[p.chave];
        expect(c.faz ?? c.aberta, `${t} × ${p.chave}`).toBeDefined();
      }
      expect(QUEM_VE[t].aviso).toMatch(/^Na versão real, quem vê esta tela: .+\.$/);
    }
  });

  test('decisão 21: o coordenador não vê nenhuma tela do ICA nem da Integra no Semáforo', () => {
    for (const t of [...TELAS_ICA, 'comite', 'municipio', 'gestora', 'pesquisa', 'lider'] as ChaveTela[]) {
      expect(QUEM_VE[t].quem.coordenador.faz, t).toBe('nada');
      expect(QUEM_VE[t].aviso, t).not.toMatch(/coordenador/i);
    }
    expect(QUEM_VE['relatorio-mensal'].quem.coordenador.faz).toBe('registra');
    expect(QUEM_VE['relatorio-mensal'].aviso).toMatch(/tela à parte/);
  });

  test('quem registra por fora (tela à parte, link sem conta) não entra em "quem vê esta tela"', () => {
    const { aviso } = QUEM_VE['relatorio-mensal'];
    const quemVe = aviso.split('.')[0]!;
    expect(quemVe).toBe('Na versão real, quem vê esta tela: SPE, Gerentes Pedagógicas e superusuários');
    expect(aviso).toMatch(/O coordenador preenche o relatório mensal numa tela à parte, fora da Integra/);
    expect(aviso).toMatch(/o Relacionamento e o Comercial registram a ocorrência por link, sem conta/);
    for (const t of TELAS) {
      expect(QUEM_VE[t].aviso, t).not.toMatch(/Relacionamento e Comercial e|e Relacionamento e Comercial/);
      expect(QUEM_VE[t].aviso.match(/Na versão real/g), t).toHaveLength(1);
    }
  });

  test('decisão 20: no simulador a gestora pedagógica propõe, a SPE aplica e a Líder só vê', () => {
    const { quem } = QUEM_VE.simulador;
    expect(quem.pedagogica.faz).toBe('propoe');
    expect(quem.spe.faz).toBe('aplica');
    expect(quem.lider.faz).toBe('ve');
    expect(quem.pedagogica.decisao).toBe(20);
  });

  test('decisão 19: pesos e faixas só com a SPE; a Gerente Operacional não mexe', () => {
    const { quem, aviso } = QUEM_VE.pesos;
    expect(quem.spe.faz).toBe('aplica');
    for (const p of ['operacional', 'pedagogica', 'lider', 'coordenador', 'comercial', 'diretoria'] as const) {
      expect(quem[p].faz, p).toBe('nada');
    }
    expect(aviso).toBe('Na versão real, quem vê esta tela: SPE e superusuários.');
  });

  test('decisão 22: Relacionamento e Comercial só registram ocorrência, por link', () => {
    for (const t of TELAS) {
      const c = QUEM_VE[t].quem.comercial;
      expect(c.faz, t).toBe(t === 'relatorio-mensal' ? 'registra' : 'nada');
    }
    expect(QUEM_VE['relatorio-mensal'].quem.comercial.nota).toMatch(/link/);
  });

  test('o que ainda está em aberto aparece no aviso como "em aberto"', () => {
    // Decisão 67: a Diretoria não entra na Integra; o Painel não tem mais nada em aberto.
    expect(QUEM_VE.painel.quem.diretoria).toEqual({ faz: 'nada', decisao: 67 });
    expect(QUEM_VE.painel.aviso).not.toMatch(/Em aberto/);
    // P1 fica só com "quem é quem"; a Líder no Comitê continua em aberto, com pergunta própria (P11).
    expect(QUEM_VE.comite.quem.lider.aberta).toBe('P11');
    expect(QUEM_VE.comite.aviso).toMatch(/Em aberto, para decidir no dia 7: Líder do NFP\./);
    // Nenhuma decisão diz se a gestora pedagógica vê o Histórico e os Indicadores da Líder: é leitura do documento
    // de 24/11, em aberto (P12), e sem selo de decisão.
    for (const t of ['historico', 'lider'] as ChaveTela[]) {
      const c = QUEM_VE[t].quem.pedagogica;
      expect(c, t).toMatchObject({ aberta: 'P12' });
      expect(c.faz, t).toBeUndefined();
      expect(c.decisao, t).toBeUndefined();
      expect(c.nota, t).toMatch(/documento de 24\/11/);
      expect(QUEM_VE[t].aviso, t).toMatch(/Em aberto, para decidir no dia 7: Gerentes Pedagógicas\./);
    }
    // A Líder vê as duas telas pelo documento de 24/11; a decisão 87 só deu a marca de cargo (P12).
    for (const t of ['historico', 'lider'] as ChaveTela[]) {
      expect(QUEM_VE[t].quem.lider, t).toEqual({ faz: 've', nota: 'pelo documento de 24/11' });
    }
    // Decisão 93 diz "a gerente", sem dizer qual: a célula da gestora pedagógica não leva o selo dela.
    // Quem faz a observação de formação está em aberto (P14, o mesmo ponto do cartão "Observação de formação do
    // amarelo"): o PDF do Semáforo diz a gestora pedagógica na coleta 6 e outra coisa na seção 5; a decisão 94 só
    // diz onde a observação fica.
    const dff = QUEM_VE.dff.quem.pedagogica;
    expect(dff).toMatchObject({ aberta: 'P14' });
    expect(dff.faz).toBeUndefined();
    expect(dff.decisao).toBeUndefined();
    expect(dff.nota).toMatch(/coleta 6/);
    expect(dff.nota).not.toMatch(/PDI/);
    expect(QUEM_VE.dff.aviso).toMatch(/a gerente confirma, acrescenta ou tira \(decisão 93\)/);
  });

  test('decisão 29: o Deslocamento junta-se à tela de viagens; a SPE cuida dos tempos de referência', () => {
    const { quem, aviso } = QUEM_VE.deslocamento;
    expect(quem.spe.faz).toBe('aplica');
    // Decisão 21: o coordenador não entra na Integra; registra as viagens na tela de viagens do sistema.
    expect(quem.coordenador.faz).toBe('nada');
    expect(quem.coordenador.nota).toMatch(/tela de viagens/);
    expect(aviso.split('.')[0]).not.toMatch(/coordenador/i);
    expect(aviso).toMatch(/tela de viagens/);
  });

  test('Deslocamento: gestoras pedagógicas e Líder do NFP veem o tempo pela ficha do ICA, não por esta tela', () => {
    const { quem, aviso } = QUEM_VE.deslocamento;
    expect(quem.pedagogica.faz).toBe('ve');
    expect(quem.lider.faz).toBe('ve');
    expect(aviso.split('.')[0]).toBe('Na versão real, quem vê esta tela: SPE e superusuários');
    expect(aviso).toMatch(/Gerentes Pedagógicas e a Líder do NFP veem o tempo de cada município pela ficha do ICA/);
  });

  test('as perguntas em aberto do mapa estão todas listadas, e toda pergunta citada numa tela existe', () => {
    const ids = PERGUNTAS_EM_ABERTO.map((p) => p.id);
    // Respondidas em 26/11: P2 (decisão 90), P3 (68), P6 (61 a 64 e 66), P8a (92 e 93), P8b (67), P9 (87), P10 (89).
    // P11 a P13: pontos que as decisões de 26/11 não responderam (a Líder no Comitê; a gestora pedagógica no
    // Histórico e nos Indicadores da Líder; o superusuário diante do "ninguém mais" da decisão 78).
    // P14: quem faz a observação de formação (o PDF do Semáforo diz uma coisa na seção 5 e outra na coleta 6).
    expect(ids).toEqual(['P1', 'P11', 'P12', 'P13', 'P14']);
    expect(PERGUNTAS_EM_ABERTO[0]!.pergunta).toMatch(/quem é a Líder do NFP\?$/);
    expect(PERGUNTAS_EM_ABERTO[0]!.pergunta).not.toMatch(/marca/);
    // Toda pergunta em aberto aparece em pelo menos uma célula, menos a P1 (quem é quem).
    for (const id of ['P11', 'P12', 'P13', 'P14']) {
      expect(TELAS.some((t) => PAPEIS.some((p) => QUEM_VE[t].quem[p.chave].aberta === id)), id).toBe(true);
    }
    for (const t of TELAS) {
      for (const p of PAPEIS) {
        const aberta = QUEM_VE[t].quem[p.chave].aberta;
        if (aberta) expect(ids, `${t} × ${p.chave}`).toContain(aberta);
      }
    }
    for (const p of PERGUNTAS_EM_ABERTO) expect(p.pergunta).toMatch(/\?$/);
  });

  test('o selo de decisão de cada célula é o da decisão que diz o que a célula afirma', () => {
    // Decisão 61 é a lista de gestora de referência por município, não as tarefas da Gerente Pedagógica.
    expect(QUEM_VE.gestora.quem.pedagogica.decisao).toBeUndefined();
    // Quem recebe a Sobrecarga é a decisão 69; a 64 só diz quem mantém o vínculo.
    expect(QUEM_VE.alertas.quem.pedagogica.decisao).toBe(69);
    // A decisão 19 só fala de pesos e do momento reservado; quem grava o remanejamento na carteira está em aberto.
    expect(QUEM_VE.simulador.quem.operacional.decisao).toBeUndefined();
    expect(QUEM_VE.simulador.quem.operacional.nota).toMatch(/Quem grava na carteira o remanejamento aplicado\?/);
    // A decisão 94 só diz que a observação de formação fica na DFF: o selo vai junto dessa parte da nota.
    const relatorio = QUEM_VE['relatorio-mensal'].quem.pedagogica;
    expect(relatorio.decisao).toBeUndefined();
    expect(relatorio.nota).toMatch(/a observação de formação fica na DFF \(decisão 94\)$/);
  });

  test('as decisões já tomadas sobre acesso estão listadas', () => {
    expect(DECIDIDO.map((d) => d.numero)).toEqual(expect.arrayContaining([19, 20, 21, 22, 29]));
  });

  test('as respostas do dono de 25/11 e 26/11 entram como decididas: decisões 30 a 94, uma vez cada, em ordem', () => {
    const numeros = DECIDIDO.map((d) => d.numero);
    const novas = Array.from({ length: 65 }, (_, i) => 30 + i);
    expect(numeros.filter((n) => n >= 30)).toEqual(novas);
    for (const d of DECIDIDO) expect(d.texto.trim(), `decisão ${d.numero}`).not.toBe('');
    // Decisão 57: zerar contagem nunca apaga dado.
    expect(DECIDIDO.find((d) => d.numero === 57)!.texto).toMatch(/nunca apaga/);
    // Decisão 81 com as palavras do documento; "só quando muda um número" é leitura do protótipo, na pauta.
    expect(DECIDIDO.find((d) => d.numero === 81)!.texto).toBe(
      'O relatório mensal vem pré-preenchido com as formações do sistema; o coordenador confere e justifica.',
    );
  });

  test('o Comitê: a SPE marca a data do ordinário e convoca o extraordinário (decisões 40 e 41); a pesquisa é por projeto (51)', () => {
    expect(QUEM_VE.comite.quem.spe.nota).toMatch(/marca a data do Comitê ordinário e convoca o extraordinário/);
    expect(QUEM_VE.pesquisa.aviso).toMatch(/uma vez por projeto/);
  });

  test('decisão 87: os cargos na Integra se chamam Gerente Operacional e Gerente Pedagógica', () => {
    expect(PAPEIS.find((p) => p.chave === 'operacional')).toMatchObject({ nome: 'Gerente Operacional', naFrase: 'Gerente Operacional' });
    expect(PAPEIS.find((p) => p.chave === 'pedagogica')).toMatchObject({ nome: 'Gerente Pedagógica', naFrase: 'Gerentes Pedagógicas' });
    for (const d of DECIDIDO) expect(d.texto, `decisão ${d.numero}`).not.toMatch(/gestora técnica|gestora operacional/i);
    // A 87 manteve a gerência: a decisão 19 continua com o nome dela (Gestão Operacional); o cargo é Gerente Operacional.
    const d19 = DECIDIDO.find((d) => d.numero === 19)!.texto;
    expect(d19).toMatch(/^A SPE e a Gestão Operacional são duas gerências/);
    expect(d19).toMatch(/A Gerente Operacional não mexe em pesos/);
    for (const d of DECIDIDO.filter((x) => x.numero !== 19)) expect(d.texto, `decisão ${d.numero}`).not.toMatch(/Gestão Operacional/);
  });

  test('decisões 67 e 90: a Diretoria não entra; a Gerente Operacional vê os painéis, nunca o momento reservado', () => {
    for (const t of ['painel', 'coordenador', 'gerencias'] as ChaveTela[]) {
      expect(QUEM_VE[t].quem.operacional, t).toEqual({ faz: 've', decisao: 90 });
      expect(QUEM_VE[t].quem.diretoria, t).toEqual({ faz: 'nada', decisao: 67 });
    }
    expect(QUEM_VE.comite.quem.diretoria).toEqual({ faz: 'nada', decisao: 67 });
    expect(QUEM_VE.municipio.quem.operacional).toEqual({ faz: 've', nota: 'nunca o momento reservado', decisao: 90 });
    expect(QUEM_VE.painel.aviso).toBe(
      'Na versão real, quem vê esta tela: SPE, Gerente Operacional, Gerentes Pedagógicas, Líder do NFP e superusuários.',
    );
    expect(QUEM_VE.pesos.quem.operacional.faz).toBe('nada');
  });

  test('decisões 62 e 78: o momento reservado, só a gestora de referência principal, a Líder do NFP e a SPE', () => {
    const { quem } = QUEM_VE.municipio;
    expect(quem.lider).toMatchObject({ faz: 've', decisao: 78 });
    expect(quem.lider.nota).toMatch(/momento reservado/);
    expect(quem.pedagogica.nota).toMatch(/só a gestora de referência principal/);
    expect(quem.pedagogica.decisao).toBe(62);
    expect(quem.spe.nota).toMatch(/inclusive o momento reservado/);
    // "Ninguém mais": cada papel da matriz, um por um.
    expect(quem.operacional.nota).toMatch(/nunca o momento reservado/);
    for (const p of ['coordenador', 'comercial', 'diretoria'] as const) expect(quem[p].faz, p).toBe('nada');
    // O superusuário vê a ficha; ler o momento reservado fica para o dia 7 (P13).
    expect(quem.superusuario).toMatchObject({ faz: 've', aberta: 'P13' });
    expect(quem.superusuario.nota).toMatch(/momento reservado/);
    const conferidos = ['spe', 'lider', 'pedagogica', 'operacional', 'coordenador', 'comercial', 'diretoria', 'superusuario'];
    expect(PAPEIS.map((p) => p.chave)).toEqual(expect.arrayContaining(conferidos));
    expect(PAPEIS).toHaveLength(conferidos.length);
    // O aviso da Ficha do município diz quem lê o momento reservado (a tela mostra as queixas do momento reservado).
    expect(QUEM_VE.municipio.aviso).toMatch(
      /O momento reservado só é lido pela gestora de referência principal do município, pela Líder do NFP e pela SPE \(decisões 62 e 78\)\./,
    );
  });

  test('a Gerente Operacional recebe alertas do ICA (dado incompleto, dado improvável, projeto sem coordenador): vê a tela', () => {
    expect(QUEM_VE.alertas.quem.operacional.faz).toBe('ve');
    expect(QUEM_VE.alertas.quem.operacional.nota).toMatch(/dado incompleto, dado improvável e projeto sem coordenador/);
    expect(QUEM_VE.alertas.aviso).toMatch(/^Na versão real, quem vê esta tela: SPE, Gerente Operacional, /);
  });

  test('decisões 69, 73 e 91: alerta de Sobrecarga para a Líder; link da pesquisa pela gestora; deslocamento pela ficha', () => {
    // A decisão 69 cobre só a Sobrecarga; o alerta de coordenador sem municípios também vai para ela (ica/calculo.ts).
    expect(QUEM_VE.alertas.quem.lider).toMatchObject({ faz: 've' });
    expect(QUEM_VE.alertas.quem.lider.decisao).toBeUndefined();
    expect(QUEM_VE.alertas.quem.lider.nota).toMatch(/Sobrecarga \(decisão 69\)/);
    expect(QUEM_VE.alertas.quem.lider.nota).toMatch(/sem municípios/);
    expect(QUEM_VE.pesquisa.quem.pedagogica.decisao).toBe(73);
    expect(QUEM_VE.pesquisa.quem.coordenador).toMatchObject({ faz: 'nada', decisao: 73 });
    expect(QUEM_VE.deslocamento.quem.pedagogica.decisao).toBe(91);
    expect(QUEM_VE.deslocamento.quem.lider.decisao).toBe(91);
  });
});
