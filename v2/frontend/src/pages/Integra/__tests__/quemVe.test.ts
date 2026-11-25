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
    expect(quemVe).toBe('Na versão real, quem vê esta tela: SPE, gestoras pedagógicas e superusuários');
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

  test('decisão 19: pesos e faixas só com a SPE; a Gestão Operacional não mexe', () => {
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
    expect(QUEM_VE.painel.quem.diretoria.aberta).toBe('P8b');
    expect(QUEM_VE.painel.aviso).toMatch(/Em aberto, para decidir no dia 7: .*Diretoria/);
    expect(QUEM_VE.historico.quem.pedagogica.aberta).toBe('P1');
    expect(QUEM_VE.dff.quem.pedagogica.aberta).toBe('P8a');
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
    expect(aviso).toMatch(/gestoras pedagógicas e a Líder do NFP veem o tempo de cada município pela ficha do ICA/);
  });

  test('as perguntas em aberto do mapa estão todas listadas, e toda pergunta citada numa tela existe', () => {
    const ids = PERGUNTAS_EM_ABERTO.map((p) => p.id);
    for (const id of ['P1', 'P3', 'P6', 'P8a', 'P8b', 'P9', 'P10']) expect(ids).toContain(id);
    for (const t of TELAS) {
      for (const p of PAPEIS) {
        const aberta = QUEM_VE[t].quem[p.chave].aberta;
        if (aberta) expect(ids, `${t} × ${p.chave}`).toContain(aberta);
      }
    }
    for (const p of PERGUNTAS_EM_ABERTO) expect(p.pergunta).toMatch(/\?$/);
  });

  test('as decisões já tomadas sobre acesso estão listadas', () => {
    expect(DECIDIDO.map((d) => d.numero)).toEqual(expect.arrayContaining([19, 20, 21, 22, 29]));
  });
});
