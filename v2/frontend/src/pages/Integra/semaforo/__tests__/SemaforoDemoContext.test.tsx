/**
 * Estado da sessão do Semáforo: respostas, ocorrências, relatórios e reuniões registrados na tela e as
 * decisões do Comitê ficam só na memória. Recarregar a página (um provider novo) volta ao original.
 */
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { SemaforoDemoProvider, useSemaforoDemo } from '../SemaforoDemoContext';
import { HISTORIAS_SEMAFORO, gerarDadosSemaforo } from '../dados';

const original = gerarDadosSemaforo();
const REF = original.data_referencia;
const wrapper = ({ children }: { children: ReactNode }) => <SemaforoDemoProvider>{children}</SemaforoDemoProvider>;

function idDe(h: { nome: string; uf: string }): number {
  const m = original.municipios.find((x) => x.nome === h.nome && x.uf === h.uf);
  if (!m) throw new Error('fora da lista');
  return m.id;
}

type Valor = ReturnType<typeof useSemaforoDemo>;

/** Um município verde, sem nada em aberto no ciclo atual: o ponto de partida dos testes de registro. */
function verdeTranquilo(v: Valor): number {
  const comCoordenador = new Set(v.dados.municipios.filter((m) => m.coordenador !== null).map((m) => m.id));
  const s = v.situacoes.find(
    (x) =>
      comCoordenador.has(x.municipio) &&
      x.cor_vigente === 'verde' &&
      x.ciclos.at(-1)?.resultado.cor === 'verde' &&
      x.ciclos.at(-1)?.decisao === null,
  );
  if (!s) throw new Error('sem município verde');
  return s.municipio;
}

const situacao = (v: Valor, id: number) => {
  const s = v.situacoes.find((x) => x.municipio === id);
  if (!s) throw new Error('sem situação');
  return s;
};

const RESPOSTA = {
  funcao_respondente: 'Articulador(a) municipal',
  identificacao: null,
  itens: [5, 4, 5, 4, 5, 5],
  nps: 10,
  comentario: 'Manter o ritmo das formações.',
};

describe('useSemaforoDemo', { timeout: 20000 }, () => {
  it('fora do provider avisa com erro claro', () => {
    expect(() => renderHook(() => useSemaforoDemo())).toThrow(/SemaforoDemoProvider/);
  });

  it('começa com os dados gerados e a situação de cada município', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    expect(result.current.dados).toEqual(original);
    expect(result.current.mudouNaSessao).toBe(false);
    expect(result.current.situacoes).toHaveLength(original.municipios.length);
    expect(situacao(result.current, idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje)).cor_vigente).toBe('vermelho');
  });

  it('ocorrência: uma reclamação muda a cor sugerida na hora (vermelho imediato)', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    expect(result.current.registrarOcorrencia({ municipio: 9999, origem: 'fluxo_unico', tipo: 'leve' }).ok).toBe(false);
    expect(
      result.current.registrarOcorrencia({ municipio: id, origem: 'fluxo_unico', tipo: 'leve', data: '2026-12-08' }),
    ).toEqual({ ok: false, erros: ['A data não pode ser depois de hoje (07/12/2026).'] });

    let r: { ok: boolean } = { ok: false };
    act(() => {
      r = result.current.registrarOcorrencia({ municipio: id, origem: 'momento_reservado', tipo: 'reclamacao' });
    });
    expect(r.ok).toBe(true);
    const nova = result.current.dados.ocorrencias.at(-1);
    expect(nova).toMatchObject({ municipio: id, data: REF, origem: 'momento_reservado', tipo: 'reclamacao' });
    expect(nova?.id).toBe(Math.max(...original.ocorrencias.map((o) => o.id)) + 1);
    const atual = situacao(result.current, id).ciclos.at(-1)?.resultado;
    expect(atual).toMatchObject({ cor: 'vermelho', vermelho_imediato: true, decisivos: ['ocorrencias'] });
    expect(result.current.mudouNaSessao).toBe(true);
  });

  it('resposta à pesquisa: valida itens e nota; entra no ciclo atual, no prazo, com a data de hoje', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = idDe(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos);
    const ruim = result.current.registrarResposta({ ...RESPOSTA, municipio: id, itens: [5, 4, 6], nps: 11 });
    expect(ruim).toEqual({
      ok: false,
      erros: ['Falta responder, com nota de 1 a 5: item 3, item 4, item 5 e item 6.', 'A nota de recomendação vai de 0 a 10.'],
    });
    expect(situacao(result.current, id).ciclos.at(-1)?.resultado.avaliacoes.at(-1)?.cor).toBe('sem_dado');
    act(() => {
      result.current.registrarResposta({ ...RESPOSTA, municipio: id });
    });
    expect(result.current.dados.respostas.at(-1)).toMatchObject({
      municipio: id,
      ciclo: '2026.6',
      respondida_em: REF,
      no_prazo: true,
      nps: 10,
    });
    const resposta = situacao(result.current, id).ciclos.at(-1)?.resultado.avaliacoes.find((a) => a.indicador === 'resposta_pesquisa');
    expect(resposta?.cor).toBe('verde');
  });

  it('relatório mensal: o do mesmo mês substitui o anterior; o coordenador é o do município', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    const coordenador = original.municipios.find((m) => m.id === id)?.coordenador;
    const base = { municipio: id, mes: '2026-12', formacoes_previstas: 4, formacoes_realizadas: 1, visitas_previstas: 2, visitas_realizadas: 0 };
    // WCAG 3.3.1: o erro diz qual campo está errado, com o nome que a tela mostra.
    expect(result.current.registrarRelatorio({ ...base, visitas_realizadas: -1 })).toEqual({
      ok: false,
      erros: ['Visitas realizadas: escreva um número inteiro a partir de 0.'],
    });
    expect(result.current.registrarRelatorio({ ...base, formacoes_previstas: Number.NaN, visitas_previstas: 1.5 })).toEqual({
      ok: false,
      erros: [
        'Formações previstas: escreva um número inteiro a partir de 0.',
        'Visitas previstas: escreva um número inteiro a partir de 0.',
      ],
    });
    act(() => {
      result.current.registrarRelatorio(base);
    });
    act(() => {
      result.current.registrarRelatorio({ ...base, formacoes_realizadas: 4, visitas_realizadas: 2 });
    });
    const dezembro = result.current.dados.relatorios.filter((r) => r.municipio === id && r.mes === '2026-12');
    expect(dezembro).toEqual([expect.objectContaining({ coordenador, formacoes_realizadas: 4, visitas_realizadas: 2 })]);
  });

  it('reunião de escuta: registra na sessão, com data até hoje', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    const reuniao = { municipio: id, data: REF, periodicidade: 'semestral' as const, cronograma_confirmado: true, encaminhamentos: 'Agenda de 2027 combinada.' };
    expect(result.current.registrarReuniao({ ...reuniao, data: '2027-01-10' }).ok).toBe(false);
    act(() => {
      result.current.registrarReuniao(reuniao);
    });
    expect(result.current.dados.reunioes.at(-1)).toMatchObject(reuniao);
  });

  it('data antes do ciclo atual é recusada: o ciclo já publicado não muda (seção 9: histórico preservado)', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = idDe(HISTORIAS_SEMAFORO.em_recuperacao);
    const antes = situacao(result.current, id).ciclos;
    const erro = 'A data precisa ser do ciclo atual: de 01/11/2026 até hoje (07/12/2026).';

    // 03/09/2026 fica no ciclo 2026.5, já publicado pelo Comitê.
    expect(
      result.current.registrarOcorrencia({ municipio: id, origem: 'fluxo_unico', tipo: 'leve', data: '2026-09-03' }),
    ).toEqual({ ok: false, erros: [erro] });
    const reuniao = { municipio: id, periodicidade: 'trimestral' as const, cronograma_confirmado: true, encaminhamentos: 'Datas revistas.' };
    expect(result.current.registrarReuniao({ ...reuniao, data: '2026-10-31' })).toEqual({ ok: false, erros: [erro] });
    const relatorio = { municipio: id, formacoes_previstas: 4, formacoes_realizadas: 0, visitas_previstas: 2, visitas_realizadas: 0 };
    expect(result.current.registrarRelatorio({ ...relatorio, mes: '2026-09' })).toEqual({
      ok: false,
      erros: ['Escolha um mês do ciclo atual (novembro e dezembro de 2026).'],
    });
    expect(situacao(result.current, id).ciclos).toEqual(antes);
    expect(result.current.mudouNaSessao).toBe(false);

    // O primeiro dia do ciclo atual vale.
    let r: { ok: boolean } = { ok: false };
    act(() => {
      r = result.current.registrarReuniao({ ...reuniao, data: '2026-11-01' });
    });
    expect(r.ok).toBe(true);
  });

  it('Comitê: alterar a cor exige justificativa; publicar cria as tarefas quando a cor muda', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    act(() => {
      result.current.registrarOcorrencia({ municipio: id, origem: 'fluxo_unico', tipo: 'reclamacao' });
    });
    expect(result.current.decidir(id, 'amarelo', '  ')).toEqual({
      ok: false,
      erros: ['A cor é diferente da sugerida (Vermelho). Escreva a justificativa do Comitê.'],
    });
    act(() => {
      result.current.decidir(id, 'vermelho', null);
    });
    const s = situacao(result.current, id);
    expect(s.cor_vigente).toBe('vermelho');
    expect(s.ciclos.at(-1)?.decisao).toEqual({
      municipio: id,
      ciclo: '2026.6',
      cor_sugerida: 'vermelho',
      cor_publicada: 'vermelho',
      justificativa: null,
      publicada_em: REF,
    });
    const tarefas = result.current.dados.tarefas.filter((t) => t.municipio === id && t.criada_em === REF);
    expect(tarefas.map((t) => t.chave)).toEqual(['contato_48h', 'reuniao_secretaria', 'plano_acao', 'devolutiva', 'visita_tecnica']);
    expect(tarefas[0]?.prazo_em).toBe('2026-12-09');

    // Mesma cor de novo: a decisão fica registrada, mas as tarefas não se repetem.
    act(() => {
      result.current.decidir(id, 'vermelho', null);
    });
    expect(result.current.dados.tarefas.filter((t) => t.municipio === id && t.criada_em === REF)).toHaveLength(5);

    // Alterar com justificativa: a justificativa fica guardada.
    act(() => {
      result.current.decidir(id, 'amarelo', '  Reclamação já resolvida com a Secretaria.  ');
    });
    expect(result.current.dados.decisoes.at(-1)).toMatchObject({
      cor_sugerida: 'vermelho',
      cor_publicada: 'amarelo',
      justificativa: 'Reclamação já resolvida com a Secretaria.',
    });
    expect(situacao(result.current, id).cor_vigente).toBe('amarelo');
  });

  it('Comitê: mudar a decisão no mesmo ciclo troca as tarefas, sem deixar as da cor anterior nem repetir', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    const abertas = () =>
      result.current.dados.tarefas.filter((t) => t.municipio === id && t.concluida_em === null && t.criada_em === REF);
    const chaves = () => abertas().map((t) => `${t.chave}-${t.criada_em}`);

    act(() => {
      result.current.decidir(id, 'vermelho', 'Reclamação grave na Secretaria.');
    });
    expect(abertas()).toHaveLength(5);

    // Confirmar a sugerida (verde): a cor em vigor volta a verde e as tarefas do vermelho saem.
    act(() => {
      result.current.decidir(id, 'verde', null);
    });
    expect(situacao(result.current, id).cor_vigente).toBe('verde');
    expect(abertas()).toEqual([]);

    // Alterar de novo para vermelho: as 5 tarefas do vermelho, uma vez só.
    act(() => {
      result.current.decidir(id, 'vermelho', 'Reclamação grave na Secretaria.');
    });
    expect(abertas().every((t) => t.cor === 'vermelho')).toBe(true);
    expect(chaves()).toHaveLength(5);
    expect(new Set(chaves()).size).toBe(5);

    // Trocar vermelho por amarelo: saem as do vermelho, entram as do amarelo.
    act(() => {
      result.current.decidir(id, 'amarelo', 'A Secretaria já respondeu.');
    });
    expect(abertas().map((t) => t.chave)).toEqual(['contato_articulador', 'observacao_formacao']);
  });

  it('Comitê: confirmar de novo a cor do vermelho extraordinário não reabre nem apaga as tarefas dele', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const antes = result.current.dados.tarefas.filter((t) => t.municipio === id);
    let r: { ok: boolean } = { ok: false };
    act(() => {
      r = result.current.decidir(id, 'vermelho', 'Confirma o vermelho do Comitê extraordinário.');
    });
    expect(r.ok).toBe(true);
    expect(result.current.dados.tarefas.filter((t) => t.municipio === id)).toEqual(antes);
  });

  it('restaurar volta ao original; recarregar a página (provider novo) também', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    act(() => {
      result.current.registrarOcorrencia({ municipio: id, origem: 'fluxo_unico', tipo: 'leve' });
      result.current.anotar('Ocorrência leve');
    });
    expect(result.current.anotacoes).toEqual(['Ocorrência leve']);
    const outra = renderHook(() => useSemaforoDemo(), { wrapper });
    expect(outra.result.current.dados).toEqual(original);
    expect(outra.result.current.anotacoes).toEqual([]);
    act(() => result.current.restaurar());
    expect(result.current.dados).toEqual(original);
    expect(result.current.anotacoes).toEqual([]);
    expect(result.current.mudouNaSessao).toBe(false);
  });
});
