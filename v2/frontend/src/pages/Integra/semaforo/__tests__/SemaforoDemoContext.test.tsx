/**
 * Estado da sessão do Semáforo: respostas, ocorrências, relatórios e reuniões registrados na tela e as
 * decisões do Comitê ficam só na memória. Recarregar a página (um provider novo) volta ao original.
 */
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { SemaforoDemoProvider, useSemaforoDemo } from '../SemaforoDemoContext';
import { HISTORIAS_SEMAFORO, gerarDadosSemaforo } from '../dados';
import { estadoDaTarefa, tarefaAberta } from '../regras';

const original = gerarDadosSemaforo();
const REF = original.data_referencia;
const wrapper = ({ children }: { children: ReactNode }) => <SemaforoDemoProvider>{children}</SemaforoDemoProvider>;

function idDe(h: { nome: string; uf: string }): number {
  const m = original.municipios.find((x) => x.nome === h.nome && x.uf === h.uf);
  if (!m) throw new Error('fora da lista');
  return m.id;
}

type Valor = ReturnType<typeof useSemaforoDemo>;

/**
 * Um município verde, sem nada em aberto no ciclo atual e sem resposta à pesquisa no ciclo: o ponto de partida dos
 * testes de registro. Com `projetos`, um com pelo menos esse número de projetos.
 */
function verdeTranquilo(v: Valor, projetos = 1): number {
  const respondeu = new Set(v.dados.respostas.filter((r) => r.ciclo === v.dados.ciclo_atual).map((r) => r.municipio));
  const candidatos = new Set(
    v.dados.municipios
      .filter((m) => m.projetos[0]?.coordenador != null && m.projetos.length >= projetos && !respondeu.has(m.id))
      .map((m) => m.id),
  );
  const s = v.situacoes.find(
    (x) =>
      candidatos.has(x.municipio) &&
      x.cor_vigente === 'verde' &&
      x.ciclos.at(-1)?.resultado.cor === 'verde' &&
      x.ciclos.at(-1)?.decisao === null,
  );
  if (!s) throw new Error('sem município verde');
  return s.municipio;
}

const projetoDe = (v: Valor, id: number, k = 0): number => v.dados.municipios.find((m) => m.id === id)!.projetos[k]!.id;

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

  it('ocorrência: uma reclamação muda a cor sugerida e a cor oficial na hora (decisão 38), com as tarefas', () => {
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
    expect(nova).toMatchObject({
      municipio: id,
      data: REF,
      registrada_em: `${REF}T09:00:00-03:00`,
      respondida_em: null,
      origem: 'momento_reservado',
      tipo: 'reclamacao',
    });
    expect(nova?.id).toBe(Math.max(...original.ocorrencias.map((o) => o.id)) + 1);
    const s = situacao(result.current, id);
    expect(s.ciclos.at(-1)?.resultado).toMatchObject({ cor: 'vermelho', vermelho_imediato: true, decisivos: ['ocorrencias'] });
    expect(s).toMatchObject({ cor_vigente: 'vermelho', aguardando_comite: true });
    expect(s.decisao_vigente).toMatchObject({ origem: 'vermelho_automatico', publicada_em: REF });
    const tarefas = result.current.dados.tarefas.filter((t) => t.municipio === id && t.criada_em === REF);
    expect(tarefas.map((t) => t.chave)).toEqual(['contato_48h', 'reuniao_secretaria', 'plano_acao', 'devolutiva', 'visita_tecnica']);
    expect(result.current.mudouNaSessao).toBe(true);
  });

  it('ocorrência com data passada do ciclo: o vermelho na hora vale desde a data dela (as tarefas nascem nessa data)', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    act(() => {
      result.current.registrarOcorrencia({ municipio: id, origem: 'fluxo_unico', tipo: 'reclamacao', data: '2026-11-27', hora: '14:30' });
    });
    expect(result.current.dados.ocorrencias.at(-1)?.registrada_em).toBe('2026-11-27T14:30:00-03:00');
    expect(situacao(result.current, id).decisao_vigente?.publicada_em).toBe('2026-11-27');
    // Publicado na sexta, o contato de 2 dias úteis venceu na terça (decisão 34).
    const contato = result.current.dados.tarefas.find((t) => t.municipio === id && t.chave === 'contato_48h');
    expect(contato).toMatchObject({ criada_em: '2026-11-27', prazo_em: '2026-12-01' });
    expect(contato && estadoDaTarefa(contato, REF)).toBe('vencida');
  });

  it('decisão 50: a ocorrência guarda quando foi respondida (na hora do registro ou depois)', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    const base = { municipio: id, origem: 'fluxo_unico' as const, tipo: 'leve' as const, data: '2026-12-01', hora: '10:00' };
    expect(result.current.registrarOcorrencia({ ...base, hora: '25:00' })).toEqual({
      ok: false,
      erros: ['Informe a hora do registro (horas e minutos).'],
    });
    expect(result.current.registrarOcorrencia({ ...base, respondida_em: '2026-12-01T09:00' })).toEqual({
      ok: false,
      erros: ['A resposta não pode ser antes do registro da ocorrência.'],
    });
    expect(result.current.registrarOcorrencia({ ...base, respondida_em: '2026-12-08T09:00' })).toEqual({
      ok: false,
      erros: ['A resposta não pode ser depois de hoje (07/12/2026).'],
    });
    act(() => {
      result.current.registrarOcorrencia({ ...base, respondida_em: '2026-12-03T16:00' });
    });
    expect(result.current.dados.ocorrencias.at(-1)?.respondida_em).toBe('2026-12-03T16:00:00-03:00');

    act(() => {
      result.current.registrarOcorrencia({ ...base, data: REF });
    });
    const semResposta = result.current.dados.ocorrencias.at(-1)!;
    expect(semResposta.respondida_em).toBeNull();
    act(() => {
      result.current.responderOcorrencia(semResposta.id, `${REF}T11:30`);
    });
    expect(result.current.dados.ocorrencias.find((o) => o.id === semResposta.id)?.respondida_em).toBe(`${REF}T11:30:00-03:00`);
    expect(result.current.responderOcorrencia(semResposta.id, `${REF}T12:00`)).toEqual({
      ok: false,
      erros: ['Esta ocorrência já tem resposta.'],
    });
  });

  it('resposta à pesquisa: valida itens e nota; entra no ciclo atual, no prazo, com a data de hoje', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = idDe(HISTORIAS_SEMAFORO.sem_resposta_dois_ciclos);
    const projeto = projetoDe(result.current, id);
    const ruim = result.current.registrarResposta({ ...RESPOSTA, municipio: id, projeto, itens: [5, 4, 6], nps: 11 });
    expect(ruim).toEqual({
      ok: false,
      erros: ['Falta responder, com nota de 1 a 5: item 3, item 4, item 5 e item 6.', 'A nota de recomendação vai de 0 a 10.'],
    });
    expect(situacao(result.current, id).ciclos.at(-1)?.resultado.avaliacoes.at(-1)?.cor).toBe('sem_dado');
    act(() => {
      result.current.registrarResposta({ ...RESPOSTA, municipio: id, projeto });
    });
    expect(result.current.dados.respostas.at(-1)).toMatchObject({
      municipio: id,
      projeto,
      ciclo: '2026.6',
      respondida_em: REF,
      no_prazo: true,
      nps: 10,
    });
    const resposta = situacao(result.current, id).ciclos.at(-1)?.resultado.avaliacoes.find((a) => a.indicador === 'resposta_pesquisa');
    expect(resposta?.cor).toBe('verde');
  });

  it('decisão 51: uma resposta por projeto no ciclo; a segunda do mesmo projeto é recusada, a de outro projeto entra', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current, 2);
    const [a, b] = [projetoDe(result.current, id, 0), projetoDe(result.current, id, 1)];
    expect(result.current.registrarResposta({ ...RESPOSTA, municipio: id, projeto: 999999 })).toEqual({
      ok: false,
      erros: ['Escolha um projeto do município.'],
    });
    act(() => {
      result.current.registrarResposta({ ...RESPOSTA, municipio: id, projeto: a });
    });
    expect(result.current.registrarResposta({ ...RESPOSTA, municipio: id, projeto: a })).toEqual({
      ok: false,
      erros: ['Este projeto já tem resposta neste ciclo: a pesquisa é uma por projeto.'],
    });
    act(() => {
      result.current.registrarResposta({ ...RESPOSTA, municipio: id, projeto: b });
    });
    expect(result.current.dados.respostas.filter((r) => r.municipio === id && r.ciclo === '2026.6').map((r) => r.projeto)).toEqual([a, b]);
  });

  it('decisão 38: uma resposta com nota de recomendação em vermelho muda a cor oficial na hora', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    act(() => {
      result.current.registrarResposta({ ...RESPOSTA, municipio: id, projeto: projetoDe(result.current, id), nps: 2 });
    });
    expect(situacao(result.current, id)).toMatchObject({ cor_vigente: 'vermelho', aguardando_comite: true });
  });

  it('relatório mensal: o do mesmo mês substitui o anterior; o coordenador é o do município', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    const projeto = original.municipios.find((m) => m.id === id)!.projetos[0]!;
    const coordenador = projeto.coordenador;
    const base = {
      municipio: id,
      projeto: projeto.id,
      mes: '2026-12',
      formacoes_previstas: 4,
      formacoes_realizadas: 1,
      visitas_previstas: 2,
      visitas_realizadas: 0,
    };
    expect(result.current.registrarRelatorio({ ...base, projeto: 999999 })).toEqual({ ok: false, erros: ['Escolha um projeto do município.'] });
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
    expect(dezembro).toEqual([expect.objectContaining({ projeto: projeto.id, coordenador, formacoes_realizadas: 4, visitas_realizadas: 2 })]);
    // Decisão 57: corrigir não apaga. A versão anterior fica guardada, fora das contas, com o dia da correção.
    expect(result.current.dados.relatorios_corrigidos).toEqual([
      expect.objectContaining({ municipio: id, projeto: projeto.id, mes: '2026-12', formacoes_realizadas: base.formacoes_realizadas, corrigido_em: REF }),
    ]);
  });

  it('decisão 46: relatório de projeto sem coordenador é recusado', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const m = original.municipios.find((x) => x.projetos.some((p) => p.coordenador === null))!;
    const projeto = m.projetos.find((p) => p.coordenador === null)!.id;
    const relatorio = { municipio: m.id, projeto, mes: '2026-12', formacoes_previstas: 4, formacoes_realizadas: 4, visitas_previstas: 1, visitas_realizadas: 1 };
    expect(result.current.registrarRelatorio(relatorio)).toEqual({ ok: false, erros: ['Este projeto ainda não tem coordenador.'] });
  });

  it('reunião de escuta já feita: registra com a ata de hoje, com data até hoje', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    const reuniao = { municipio: id, data: REF, periodicidade: 'semestral' as const, cronograma_confirmado: true, encaminhamentos: 'Agenda de 2027 combinada.' };
    expect(result.current.registrarReuniao({ ...reuniao, data: '2027-01-10' }).ok).toBe(false);
    act(() => {
      result.current.registrarReuniao(reuniao);
    });
    expect(result.current.dados.reunioes.at(-1)).toMatchObject({ ...reuniao, ata_em: REF });
  });

  it('decisão 48: a reunião é marcada antes (pode ser depois de hoje) e a ata registrada depois dela', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    act(() => {
      result.current.agendarReuniao({ municipio: id, data: '2026-12-15' });
    });
    const agendada = result.current.dados.reunioes.at(-1)!;
    // Rodada 5: a periodicidade vem da cor em vigor (verde: semestral), como nos dados simulados.
    expect(agendada).toMatchObject({ municipio: id, data: '2026-12-15', periodicidade: 'semestral', ata_em: null, encaminhamentos: '' });
    const ata = { cronograma_confirmado: true, encaminhamentos: 'Cronograma confirmado.' };
    expect(result.current.registrarAta(agendada.id, ata)).toEqual({
      ok: false,
      erros: ['A ata só pode ser registrada no dia da reunião ou depois (15/12/2026).'],
    });
    expect(result.current.registrarAta(agendada.id, { ...ata, encaminhamentos: '  ' })).toEqual({
      ok: false,
      erros: ['A ata só pode ser registrada no dia da reunião ou depois (15/12/2026).', 'Escreva o que ficou combinado.'],
    });

    // A reunião de Horizonte de 04/12 está com a ata por registrar.
    const horizonte = idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    const aRegistrar = result.current.dados.reunioes.find((r) => r.municipio === horizonte && r.ata_em === null)!;
    act(() => {
      result.current.registrarAta(aRegistrar.id, ata);
    });
    expect(result.current.dados.reunioes.find((r) => r.id === aRegistrar.id)).toMatchObject({ ...ata, ata_em: REF });
    expect(result.current.registrarAta(aRegistrar.id, ata)).toEqual({ ok: false, erros: ['A ata desta reunião já foi registrada.'] });
  });

  it('rodada 5: a reunião marcada tira a periodicidade da cor em vigor, e fica uma reunião por vez (30 dias)', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    // Horizonte-CE está vermelho e tem a reunião de 04/12: a próxima, a 30 dias ou mais, é trimestral.
    const horizonte = idDe(HISTORIAS_SEMAFORO.vermelho_prazo_hoje);
    expect(result.current.agendarReuniao({ municipio: horizonte, data: '2026-12-15' })).toEqual({
      ok: false,
      erros: ['Já há uma reunião de escuta em 04/12/2026, a menos de 30 dias desta data. A reunião é uma por vez: escolha uma data a 30 dias ou mais dela.'],
    });
    act(() => {
      result.current.agendarReuniao({ municipio: horizonte, data: '2027-01-11' });
    });
    expect(result.current.dados.reunioes.at(-1)).toMatchObject({ municipio: horizonte, data: '2027-01-11', periodicidade: 'trimestral' });
    // Jequié-BA já tem a reunião de 10/12 marcada: outra em 11/12 é recusada.
    const jequie = original.municipios.find((m) => m.nome === 'Jequié')!.id;
    expect(result.current.agendarReuniao({ municipio: jequie, data: '2026-12-11' }).ok).toBe(false);
  });

  it('rodada 5: o Comitê desfaz o vermelho na hora e a tarefa do vermelho que ele tinha substituído volta a ficar aberta (Sobral-CE)', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const sobral = idDe(HISTORIAS_SEMAFORO.em_recuperacao);
    const visita = result.current.dados.tarefas.find((t) => t.municipio === sobral && t.cor === 'vermelho' && tarefaAberta(t))!;
    expect(visita).toMatchObject({ chave: 'visita_tecnica', prazo_em: '2027-02-15' });
    act(() => {
      result.current.registrarOcorrencia({ municipio: sobral, origem: 'fluxo_unico', tipo: 'reclamacao' });
    });
    // O vermelho na hora reabre as tarefas do vermelho (decisão 43): a visita de antes fica substituída.
    expect(result.current.dados.tarefas.find((t) => t.id === visita.id)?.encerramento).toEqual({ motivo: 'substituida', em: REF });
    act(() => {
      result.current.decidir(sobral, 'amarelo', 'A reclamação já foi resolvida.');
    });
    const tarefas = result.current.dados.tarefas;
    // Decisão 42: as do vermelho desfeito ficam canceladas; a que ele tinha substituído volta como estava.
    const novas = tarefas.filter((t) => t.municipio === sobral && t.cor === 'vermelho' && t.criada_em === REF);
    expect(novas).toHaveLength(5);
    expect(novas.every((t) => t.encerramento?.motivo === 'cancelada_comite')).toBe(true);
    expect(tarefas.find((t) => t.id === visita.id)).toEqual(visita);
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
    const relatorio = {
      municipio: id,
      projeto: projetoDe(result.current, id),
      formacoes_previstas: 4,
      formacoes_realizadas: 0,
      visitas_previstas: 2,
      visitas_realizadas: 0,
    };
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
    // A reclamação já mudou a cor oficial na hora (decisão 38): as tarefas nasceram com ela.
    const doVermelho = () =>
      result.current.dados.tarefas.filter((t) => t.municipio === id && t.criada_em === REF && t.cor === 'vermelho');
    expect(doVermelho()).toHaveLength(5);
    act(() => {
      result.current.decidir(id, 'vermelho', null);
    });
    const s = situacao(result.current, id);
    expect(s).toMatchObject({ cor_vigente: 'vermelho', aguardando_comite: false });
    expect(s.ciclos.at(-1)?.decisao).toEqual({
      municipio: id,
      ciclo: '2026.6',
      cor_sugerida: 'vermelho',
      cor_publicada: 'vermelho',
      justificativa: null,
      publicada_em: REF,
      origem: 'comite_ordinario',
    });
    // O Comitê confirmou: as tarefas seguem, sem repetir.
    const tarefas = doVermelho();
    expect(tarefas.map((t) => t.chave)).toEqual(['contato_48h', 'reuniao_secretaria', 'plano_acao', 'devolutiva', 'visita_tecnica']);
    expect(tarefas[0]?.prazo_em).toBe('2026-12-09');

    // Mesma cor de novo no mesmo ciclo: a decisão fica registrada, mas as tarefas não se repetem.
    act(() => {
      result.current.decidir(id, 'vermelho', null);
    });
    expect(doVermelho()).toHaveLength(5);

    // Alterar com justificativa: a justificativa fica guardada, e as tarefas abertas do vermelho ficam canceladas.
    act(() => {
      result.current.decidir(id, 'amarelo', '  Reclamação já resolvida com a Secretaria.  ');
    });
    expect(result.current.dados.decisoes.at(-1)).toMatchObject({
      cor_sugerida: 'vermelho',
      cor_publicada: 'amarelo',
      justificativa: 'Reclamação já resolvida com a Secretaria.',
    });
    expect(situacao(result.current, id).cor_vigente).toBe('amarelo');
    expect(doVermelho().map((t) => estadoDaTarefa(t, REF))).toEqual(Array(5).fill('cancelada_comite'));
  });

  it('decisão 42: o Comitê extraordinário desfaz o vermelho na hora; as tarefas abertas ficam "canceladas pelo Comitê"', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    act(() => {
      result.current.registrarOcorrencia({ municipio: id, origem: 'fluxo_unico', tipo: 'reclamacao', data: '2026-11-27' });
    });
    act(() => {
      result.current.convocarExtraordinario();
    });
    act(() => {
      result.current.decidir(id, 'verde', 'A reclamação era de outro município.');
    });
    const s = situacao(result.current, id);
    expect(s.cor_vigente).toBe('verde');
    expect(s.decisao_vigente).toMatchObject({ origem: 'comite_extraordinario', publicada_em: REF });
    const doVermelho = result.current.dados.tarefas.filter((t) => t.municipio === id && t.cor === 'vermelho');
    expect(doVermelho).toHaveLength(5);
    // O contato venceu em 01/12 sem registro de conclusão: na sessão nada é concluído sozinho, então também fica cancelado.
    expect(doVermelho.every((t) => t.encerramento?.motivo === 'cancelada_comite')).toBe(true);
    // Uma segunda reclamação do mesmo tipo não refaz o vermelho que o Comitê desfez.
    act(() => {
      result.current.registrarOcorrencia({ municipio: id, origem: 'fluxo_unico', tipo: 'reclamacao' });
    });
    expect(situacao(result.current, id).cor_vigente).toBe('verde');
  });

  it('dado com data passada: o vermelho na hora não fica antes da decisão em vigor, e o histórico fica em ordem', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    // A cor em vigor é o verde que o Comitê ordinário publicou em 06/11.
    expect(situacao(result.current, id).decisao_vigente).toMatchObject({ origem: 'comite_ordinario', publicada_em: '2026-11-06' });
    act(() => {
      result.current.registrarOcorrencia({ municipio: id, origem: 'fluxo_unico', tipo: 'reclamacao', data: '2026-11-03' });
    });
    const doMunicipio = result.current.dados.decisoes.filter((d) => d.municipio === id);
    expect(doMunicipio.at(-1)).toMatchObject({ origem: 'vermelho_automatico', publicada_em: '2026-11-06' });
    const datas = doMunicipio.map((d) => d.publicada_em);
    expect(datas).toEqual([...datas].sort());
    const doVermelho = result.current.dados.tarefas.filter((t) => t.municipio === id && t.cor === 'vermelho');
    expect(doVermelho.map((t) => t.criada_em)).toEqual(Array(5).fill('2026-11-06'));
    // A ocorrência continua com a data em que aconteceu.
    expect(result.current.dados.ocorrencias.at(-1)).toMatchObject({ municipio: id, data: '2026-11-03' });
  });

  it('decisões 40 e 41: a SPE marca a data do Comitê ordinário e convoca o extraordinário', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const ordinario = () => result.current.dados.comites.find((c) => c.ciclo === '2026.6' && c.tipo === 'ordinario');
    expect(ordinario()?.data).toBe('2027-01-08');
    expect(result.current.marcarComite('2026-12-01')).toEqual({
      ok: false,
      erros: ['A SPE marca a data do Comitê a partir de hoje (07/12/2026).'],
    });
    expect(result.current.marcarComite('amanhã')).toEqual({ ok: false, erros: ['Informe a data (dia, mês e ano).'] });
    act(() => {
      result.current.marcarComite('2027-01-15');
    });
    expect(ordinario()?.data).toBe('2027-01-15');
    expect(result.current.dados.comites.filter((c) => c.ciclo === '2026.6' && c.tipo === 'ordinario')).toHaveLength(1);

    act(() => {
      result.current.convocarExtraordinario();
    });
    act(() => {
      result.current.convocarExtraordinario();
    });
    expect(result.current.dados.comites.filter((c) => c.tipo === 'extraordinario' && c.data === REF)).toHaveLength(1);
  });

  it('Comitê: mudar a decisão no mesmo ciclo troca as tarefas, sem deixar as da cor anterior nem repetir', () => {
    const { result } = renderHook(() => useSemaforoDemo(), { wrapper });
    const id = verdeTranquilo(result.current);
    const abertas = () => result.current.dados.tarefas.filter((t) => t.municipio === id && tarefaAberta(t) && t.criada_em === REF);
    const chaves = () => abertas().map((t) => `${t.chave}-${t.criada_em}`);

    act(() => {
      result.current.decidir(id, 'vermelho', 'Reclamação grave na Secretaria.');
    });
    expect(abertas()).toHaveLength(5);

    // Confirmar a sugerida (verde): a cor em vigor volta a verde e as tarefas do vermelho ficam canceladas
    // (decisão 42: continuam guardadas, com o estado).
    act(() => {
      result.current.decidir(id, 'verde', null);
    });
    expect(situacao(result.current, id).cor_vigente).toBe('verde');
    expect(abertas()).toEqual([]);
    expect(result.current.dados.tarefas.filter((t) => t.municipio === id && t.encerramento?.motivo === 'cancelada_comite')).toHaveLength(5);

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
