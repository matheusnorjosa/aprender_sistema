/**
 * Estado da sessão da demonstração do Semáforo (DADOS SIMULADOS).
 *
 * Fica só na memória da aba: respostas à pesquisa, ocorrências (e a resposta a elas), relatórios mensais,
 * reuniões de escuta (marcadas e com ata), as datas do Comitê e as decisões do Comitê registradas na tela entram
 * aqui, e a cor sugerida é recalculada na hora. Um vermelho na hora (um indicador em vermelho ou três amarelos)
 * muda também a cor oficial, com as tarefas (decisões 38 e 39). O provider mora nas rotas do Semáforo: sair do
 * Semáforo (ir ao ICA, por exemplo) ou recarregar a página volta ao original. Nada é gravado no banco.
 *
 * Tudo o que é registrado leva a data de "hoje" da demonstração (`dados.data_referencia`, 07/12/2026), não
 * a do relógio: assim os prazos e o ciclo batem com a história que está na tela. A data escolhida (ocorrência,
 * reunião) e o mês do relatório ficam no ciclo em andamento: o ciclo já publicado não é recalculado.
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useReducer, type JSX, type ReactNode } from 'react';
import {
  aplicarVermelhoAutomatico,
  avaliarMunicipio,
  doSistema,
  gerarDadosSemaforo,
  mesesDoCiclo,
  periodoDoCiclo,
  tarefasDepoisDaPublicacao,
  type DadosSemaforo,
  type ReuniaoComite,
  type ReuniaoEscuta,
  type SituacaoMunicipio,
} from './dados';
import { DIAS_ENTRE_REUNIOES, lista, periodicidadeDaCor, validarDecisao } from './regras';
import type { Cor, DecisaoComite, Ocorrencia, RelatorioMensal, RespostaPesquisa } from './tipos';

export interface EstadoSemaforoDemo {
  /** Os dados como vieram do gerador (não mudam na sessão). */
  original: DadosSemaforo;
  /** Os dados com o que foi registrado na sessão. */
  dados: DadosSemaforo;
  /** O que foi registrado na tela do relatório mensal, do mais novo ao mais antigo. */
  anotacoes: string[];
}

export type AcaoSemaforoDemo =
  | { tipo: 'resposta'; resposta: RespostaPesquisa }
  | { tipo: 'ocorrencia'; ocorrencia: Ocorrencia }
  | { tipo: 'resposta_ocorrencia'; id: number; respondida_em: string }
  | { tipo: 'relatorio'; relatorio: RelatorioMensal }
  | { tipo: 'reuniao'; reuniao: ReuniaoEscuta }
  | { tipo: 'ata'; id: number; ata: NovaAta; ata_em: string }
  | { tipo: 'comite'; comite: ReuniaoComite }
  | { tipo: 'decisao'; decisao: DecisaoComite }
  | { tipo: 'anotacao'; texto: string }
  | { tipo: 'restaurar' };

export function reducerSemaforoDemo(estado: EstadoSemaforoDemo, acao: AcaoSemaforoDemo): EstadoSemaforoDemo {
  const d = estado.dados;
  // Depois de um dado novo, o vermelho na hora muda a cor oficial na data do dado (decisões 38 e 39).
  const comDado = (depois: DadosSemaforo, municipio: number, data: string): EstadoSemaforoDemo => ({
    ...estado,
    dados: aplicarVermelhoAutomatico(d, depois, municipio, data),
  });
  switch (acao.tipo) {
    case 'resposta':
      return comDado({ ...d, respostas: [...d.respostas, acao.resposta] }, acao.resposta.municipio, acao.resposta.respondida_em);
    case 'ocorrencia':
      return comDado({ ...d, ocorrencias: [...d.ocorrencias, acao.ocorrencia] }, acao.ocorrencia.municipio, acao.ocorrencia.data);
    case 'resposta_ocorrencia': {
      const ocorrencias = d.ocorrencias.map((o) => (o.id === acao.id ? { ...o, respondida_em: acao.respondida_em } : o));
      return { ...estado, dados: { ...d, ocorrencias } };
    }
    case 'relatorio': {
      // O relatório do mesmo projeto e mês substitui o anterior nas contas (o coordenador corrigiu). Decisão 57: o
      // anterior não some; fica em `relatorios_corrigidos`, com o dia da correção.
      const { municipio, projeto, mes } = acao.relatorio;
      const mesmo = (r: RelatorioMensal): boolean => r.municipio === municipio && r.projeto === projeto && r.mes === mes;
      const corrigidos = d.relatorios.filter(mesmo).map((r) => ({ ...r, corrigido_em: d.data_referencia }));
      return comDado(
        {
          ...d,
          relatorios: [...d.relatorios.filter((r) => !mesmo(r)), acao.relatorio],
          relatorios_corrigidos: [...d.relatorios_corrigidos, ...corrigidos],
        },
        municipio,
        d.data_referencia,
      );
    }
    case 'reuniao':
      return { ...estado, dados: { ...d, reunioes: [...d.reunioes, acao.reuniao] } };
    case 'ata': {
      const reunioes = d.reunioes.map((r) => (r.id === acao.id ? { ...r, ...acao.ata, ata_em: acao.ata_em } : r));
      return { ...estado, dados: { ...d, reunioes } };
    }
    case 'comite': {
      const outros = d.comites.filter((c) => c.id !== acao.comite.id);
      return { ...estado, dados: { ...d, comites: [...outros, acao.comite] } };
    }
    case 'decisao': {
      // A decisão nova entra no registro; as tarefas seguem as decisões 42 e 43 (`tarefasDepoisDaPublicacao`):
      // confirmar a mesma cor no mesmo ciclo não mexe nelas; desfazer o vermelho no mesmo ciclo cancela as abertas do
      // vermelho (decisão 42); a mesma cor num ciclo seguinte reabre as tarefas e substitui as abertas dela (decisão 43);
      // as abertas de outra cor seguem abertas (leitura em Para validar).
      const nova = acao.decisao;
      const anterior = d.decisoes.filter((x) => x.municipio === nova.municipio).at(-1) ?? null;
      return {
        ...estado,
        dados: { ...d, decisoes: [...d.decisoes, nova], tarefas: tarefasDepoisDaPublicacao(d.tarefas, anterior, nova) },
      };
    }
    case 'anotacao':
      return { ...estado, anotacoes: [acao.texto, ...estado.anotacoes] };
    case 'restaurar':
      return { ...estado, dados: estado.original, anotacoes: [] };
  }
}

export type Resultado = { ok: true } | { ok: false; erros: string[] };

export type NovaResposta = Pick<
  RespostaPesquisa,
  'municipio' | 'projeto' | 'funcao_respondente' | 'identificacao' | 'itens' | 'nps' | 'comentario'
>;
/**
 * Sem `data`, vale hoje; sem `hora` (HH:MM), 09:00. `respondida_em` (AAAA-MM-DDTHH:MM, como o campo de data e
 * hora do navegador) é opcional: a resposta pode vir depois, por `responderOcorrencia`.
 */
export type NovaOcorrencia = Pick<Ocorrencia, 'municipio' | 'origem' | 'tipo'> & {
  data?: string;
  /** O dia do registro, quando é outro que o da ocorrência (a queixa do momento reservado chega com a ata). */
  registrada_no_dia?: string;
  hora?: string;
  respondida_em?: string | null;
};
export type NovoRelatorio = Omit<RelatorioMensal, 'id' | 'coordenador'>;
/** Reunião já feita, registrada com a ata de hoje. */
export type NovaReuniao = Omit<ReuniaoEscuta, 'id' | 'ata_em'>;
/** Reunião marcada; a ata vem depois (decisão 48). A periodicidade sai da cor em vigor (rodada 5). */
export type NovaAgenda = Pick<ReuniaoEscuta, 'municipio' | 'data'>;
export type NovaAta = Pick<ReuniaoEscuta, 'cronograma_confirmado' | 'encaminhamentos'>;

export interface ValorSemaforoDemo {
  /** Os dados com o que foi registrado na sessão. */
  dados: DadosSemaforo;
  /** A situação de cada município (cor sugerida de cada ciclo, decisão e cor em vigor), na ordem de `dados.municipios`. */
  situacoes: SituacaoMunicipio[];
  /** Algo foi registrado na sessão. */
  mudouNaSessao: boolean;
  /** Entra no ciclo atual com a data de hoje; uma resposta por projeto no ciclo (decisão 51). */
  registrarResposta: (resposta: NovaResposta) => Resultado;
  registrarOcorrencia: (ocorrencia: NovaOcorrencia) => Resultado;
  /** Registra quando a ocorrência foi respondida (AAAA-MM-DDTHH:MM). Decisão 50. */
  responderOcorrencia: (id: number, respondidaEm: string) => Resultado;
  /**
   * O coordenador é o do projeto; o relatório do mesmo projeto e mês substitui o anterior, que fica guardado (decisão 57).
   * Decisão 81: mudar um número que veio do sistema (`doSistema`) exige a justificativa.
   */
  registrarRelatorio: (relatorio: NovoRelatorio) => Resultado;
  /** Reunião já feita, com a ata registrada hoje. */
  registrarReuniao: (reuniao: NovaReuniao) => Resultado;
  /** Marca a reunião de escuta (a data pode ser depois de hoje). */
  agendarReuniao: (reuniao: NovaAgenda) => Resultado;
  /** Registra a ata (hoje) de uma reunião marcada, no dia dela ou depois. */
  registrarAta: (reuniao: number, ata: NovaAta) => Resultado;
  /** A SPE marca a data do Comitê ordinário do ciclo atual (decisão 40). */
  marcarComite: (data: string) => Resultado;
  /** A SPE convoca o Comitê extraordinário para hoje (decisão 41). */
  convocarExtraordinario: () => Resultado;
  /**
   * O Comitê confirma ou altera a cor sugerida do ciclo atual; alterar exige justificativa. Vale como do Comitê
   * extraordinário quando a SPE o convocou para hoje; senão, do ordinário.
   */
  decidir: (municipio: number, cor: Cor, justificativa: string | null) => Resultado;
  /** O que foi registrado na tela do relatório mensal, do mais novo ao mais antigo. */
  anotacoes: string[];
  anotar: (texto: string) => void;
  restaurar: () => void;
}

const SemaforoDemoContext = createContext<ValorSemaforoDemo | undefined>(undefined);

const proximoId = (lista: readonly { id: number }[]): number => lista.reduce((max, x) => Math.max(max, x.id), 0) + 1;

const dataBr = (data: string): string => data.split('-').reverse().join('/');

const naoNegativo = (n: number): boolean => Number.isInteger(n) && n >= 0;
const notaDeItem = (n: number | undefined): boolean => n !== undefined && Number.isInteger(n) && n >= 1 && n <= 5;

const DATA = /^\d{4}-\d{2}-\d{2}$/;
const HORA = /^([01]\d|2[0-3]):[0-5]\d$/;
const DATA_HORA = /^\d{4}-\d{2}-\d{2}T([01]\d|2[0-3]):[0-5]\d$/;
/** Hora de Fortaleza (UTC−3, sem horário de verão). */
const FUSO = ':00-03:00';
/** Só para chamadas sem a hora (os testes do contexto): as telas pedem a hora a quem registra. */
const HORA_PADRAO = '09:00';

interface SemaforoDemoProviderProps {
  children: ReactNode;
  /** Para testes; por padrão, `gerarDadosSemaforo()`. */
  dados?: DadosSemaforo;
}

export function SemaforoDemoProvider({ children, dados }: SemaforoDemoProviderProps): JSX.Element {
  const [estado, dispatch] = useReducer(reducerSemaforoDemo, dados, (d) => {
    const original = d ?? gerarDadosSemaforo();
    return { original, dados: original, anotacoes: [] };
  });
  const atual = estado.dados;
  const hoje = atual.data_referencia;
  // O registro só entra no ciclo em andamento: com data de um ciclo já publicado, o histórico seria recalculado
  // (seção 9 do PDF: o ciclo publicado fica como o Comitê o viu).
  const cicloAtual = useMemo(() => periodoDoCiclo(atual.ciclo_atual), [atual.ciclo_atual]);

  const situacoes = useMemo(() => atual.municipios.map((m) => avaliarMunicipio(atual, m.id)), [atual]);

  const errosBase = useCallback(
    (municipio: number, data?: string): string[] => {
      const erros: string[] = [];
      if (!atual.municipios.some((m) => m.id === municipio)) erros.push('Escolha um município da lista.');
      if (data !== undefined && !DATA.test(data)) erros.push('Informe a data (dia, mês e ano).');
      else if (data !== undefined && data > hoje) erros.push(`A data não pode ser depois de hoje (${dataBr(hoje)}).`);
      else if (data !== undefined && data < cicloAtual.inicio) {
        erros.push(`A data precisa ser do ciclo atual: de ${dataBr(cicloAtual.inicio)} até hoje (${dataBr(hoje)}).`);
      }
      return erros;
    },
    [atual.municipios, hoje, cicloAtual],
  );

  const projetoDe = useCallback(
    (municipio: number, projeto: number) => atual.municipios.find((m) => m.id === municipio)?.projetos.find((p) => p.id === projeto),
    [atual.municipios],
  );

  /** Erros da data e hora da resposta à ocorrência (decisão 50). */
  const errosDaResposta = useCallback(
    (respondidaEm: string, registradaEm: string): string[] => {
      if (!DATA_HORA.test(respondidaEm)) return ['Informe quando a ocorrência foi respondida (dia e hora).'];
      if (`${respondidaEm}${FUSO}` < registradaEm) return ['A resposta não pode ser antes do registro da ocorrência.'];
      if (respondidaEm.slice(0, 10) > hoje) return [`A resposta não pode ser depois de hoje (${dataBr(hoje)}).`];
      return [];
    },
    [hoje],
  );

  const registrarResposta = useCallback(
    (r: NovaResposta): Resultado => {
      const erros = errosBase(r.municipio);
      if (erros.length === 0 && !projetoDe(r.municipio, r.projeto)) erros.push('Escolha um projeto do município.');
      else if (
        atual.respostas.some((x) => x.municipio === r.municipio && x.projeto === r.projeto && x.ciclo === atual.ciclo_atual)
      ) {
        erros.push('Este projeto já tem resposta neste ciclo: a pesquisa é uma por projeto.');
      }
      // WCAG 3.3.1: o erro diz qual item falta.
      const faltam = [1, 2, 3, 4, 5, 6].filter((n) => !notaDeItem(r.itens[n - 1]));
      if (faltam.length > 0) erros.push(`Falta responder, com nota de 1 a 5: ${lista(faltam.map((n) => `item ${n}`))}.`);
      if (!Number.isInteger(r.nps) || r.nps < 0 || r.nps > 10) erros.push('A nota de recomendação vai de 0 a 10.');
      if (erros.length > 0) return { ok: false, erros };
      const resposta: RespostaPesquisa = {
        ...r,
        itens: [...r.itens],
        id: proximoId(atual.respostas),
        ciclo: atual.ciclo_atual,
        respondida_em: hoje,
        no_prazo: hoje <= periodoDoCiclo(atual.ciclo_atual).prazo_pesquisa,
      };
      dispatch({ tipo: 'resposta', resposta });
      return { ok: true };
    },
    [atual, hoje, errosBase, projetoDe],
  );

  const registrarOcorrencia = useCallback(
    ({ data: dataEscolhida, registrada_no_dia, hora, respondida_em, ...o }: NovaOcorrencia): Resultado => {
      const data = dataEscolhida ?? hoje;
      const erros = errosBase(o.municipio, data);
      const horaDoRegistro = hora ?? HORA_PADRAO;
      if (!HORA.test(horaDoRegistro)) erros.push('Informe a hora do registro (horas e minutos).');
      const registrada_em = `${registrada_no_dia ?? data}T${horaDoRegistro}${FUSO}`;
      if (erros.length === 0 && respondida_em) erros.push(...errosDaResposta(respondida_em, registrada_em));
      if (erros.length > 0) return { ok: false, erros };
      const ocorrencia: Ocorrencia = {
        ...o,
        data,
        registrada_em,
        respondida_em: respondida_em ? `${respondida_em}${FUSO}` : null,
        id: proximoId(atual.ocorrencias),
      };
      dispatch({ tipo: 'ocorrencia', ocorrencia });
      return { ok: true };
    },
    [atual.ocorrencias, hoje, errosBase, errosDaResposta],
  );

  const responderOcorrencia = useCallback(
    (id: number, respondidaEm: string): Resultado => {
      const o = atual.ocorrencias.find((x) => x.id === id);
      if (!o) return { ok: false, erros: ['Escolha uma ocorrência da lista.'] };
      if (o.respondida_em !== null) return { ok: false, erros: ['Esta ocorrência já tem resposta.'] };
      const erros = errosDaResposta(respondidaEm, o.registrada_em);
      if (erros.length > 0) return { ok: false, erros };
      dispatch({ tipo: 'resposta_ocorrencia', id, respondida_em: `${respondidaEm}${FUSO}` });
      return { ok: true };
    },
    [atual.ocorrencias, errosDaResposta],
  );

  const registrarRelatorio = useCallback(
    (r: NovoRelatorio): Resultado => {
      const erros = errosBase(r.municipio);
      // WCAG 3.3.1: o erro diz qual campo está errado, com o nome que a tela mostra.
      const numeros = [
        ['Formações previstas', r.formacoes_previstas],
        ['Formações realizadas', r.formacoes_realizadas],
        ['Visitas previstas', r.visitas_previstas],
        ['Visitas realizadas', r.visitas_realizadas],
      ] as const;
      for (const [rotulo, n] of numeros) {
        if (!naoNegativo(n)) erros.push(`${rotulo}: escreva um número inteiro a partir de 0.`);
      }
      if (!/^\d{4}-\d{2}$/.test(r.mes) || r.mes > hoje.slice(0, 7)) erros.push('Escolha um mês até o mês atual.');
      else if (!cicloAtual.meses.includes(r.mes)) erros.push(`Escolha um mês do ciclo atual (${mesesDoCiclo(atual.ciclo_atual)}).`);
      const projeto = projetoDe(r.municipio, r.projeto);
      if (erros.length === 0 && !projeto) erros.push('Escolha um projeto do município.');
      const coordenador = projeto?.coordenador ?? null;
      if (erros.length === 0 && coordenador === null) erros.push('Este projeto ainda não tem coordenador.');
      const sistema = doSistema(atual, r.projeto, r.mes);
      const mudou =
        sistema !== undefined &&
        (r.formacoes_previstas !== sistema.formacoes_previstas ||
          r.formacoes_realizadas !== sistema.formacoes_realizadas ||
          r.visitas_previstas !== sistema.visitas_previstas ||
          r.visitas_realizadas !== sistema.visitas_realizadas);
      const justificativa = r.justificativa?.trim() ?? '';
      if (erros.length === 0 && mudou && justificativa === '') erros.push('Você mudou um número que veio do sistema: escreva a justificativa.');
      if (erros.length > 0 || coordenador === null) return { ok: false, erros };
      const relatorio: RelatorioMensal = { ...r, id: proximoId(atual.relatorios), coordenador };
      if (justificativa === '') delete relatorio.justificativa;
      else relatorio.justificativa = justificativa;
      dispatch({ tipo: 'relatorio', relatorio });
      return { ok: true };
    },
    [atual, cicloAtual, hoje, errosBase, projetoDe],
  );

  const registrarReuniao = useCallback(
    (r: NovaReuniao): Resultado => {
      const erros = errosBase(r.municipio, r.data);
      if (erros.length > 0) return { ok: false, erros };
      dispatch({ tipo: 'reuniao', reuniao: { ...r, ata_em: hoje, id: proximoId(atual.reunioes) } });
      return { ok: true };
    },
    [atual.reunioes, hoje, errosBase],
  );

  const agendarReuniao = useCallback(
    (r: NovaAgenda): Resultado => {
      const erros = errosBase(r.municipio);
      if (!DATA.test(r.data)) erros.push('Informe a data (dia, mês e ano).');
      else if (r.data < cicloAtual.inicio) erros.push(`A data precisa ser a partir do início do ciclo atual (${dataBr(cicloAtual.inicio)}).`);
      // Rodada 5: como nos dados simulados, uma reunião por vez (a 30 dias ou mais da outra; leitura em Para validar).
      const perto =
        erros.length === 0
          ? atual.reunioes
              .filter((x) => x.municipio === r.municipio)
              .find((x) => Math.abs(Date.parse(x.data) - Date.parse(r.data)) < DIAS_ENTRE_REUNIOES * 86_400_000)
          : undefined;
      if (perto) {
        erros.push(
          `Já há uma reunião de escuta em ${dataBr(perto.data)}, a menos de ${DIAS_ENTRE_REUNIOES} dias desta data. A reunião é uma por vez: escolha uma data a ${DIAS_ENTRE_REUNIOES} dias ou mais dela.`,
        );
      }
      const situacao = situacoes.find((s) => s.municipio === r.municipio);
      if (erros.length > 0 || !situacao) return { ok: false, erros };
      const reuniao: ReuniaoEscuta = {
        ...r,
        // Rodada 5: a periodicidade sai da cor em vigor, como nos dados simulados.
        periodicidade: periodicidadeDaCor(situacao.cor_vigente),
        id: proximoId(atual.reunioes),
        ata_em: null,
        cronograma_confirmado: false,
        encaminhamentos: '',
      };
      dispatch({ tipo: 'reuniao', reuniao });
      return { ok: true };
    },
    [atual.reunioes, cicloAtual, errosBase, situacoes],
  );

  const registrarAta = useCallback(
    (id: number, ata: NovaAta): Resultado => {
      const r = atual.reunioes.find((x) => x.id === id);
      if (!r) return { ok: false, erros: ['Escolha uma reunião da lista.'] };
      if (r.ata_em !== null) return { ok: false, erros: ['A ata desta reunião já foi registrada.'] };
      const erros: string[] = [];
      if (r.data > hoje) erros.push(`A ata só pode ser registrada no dia da reunião ou depois (${dataBr(r.data)}).`);
      if (ata.encaminhamentos.trim() === '') erros.push('Escreva o que ficou combinado.');
      if (erros.length > 0) return { ok: false, erros };
      dispatch({ tipo: 'ata', id, ata: { ...ata, encaminhamentos: ata.encaminhamentos.trim() }, ata_em: hoje });
      return { ok: true };
    },
    [atual.reunioes, hoje],
  );

  const marcarComite = useCallback(
    (data: string): Resultado => {
      if (!DATA.test(data)) return { ok: false, erros: ['Informe a data (dia, mês e ano).'] };
      if (data < hoje) return { ok: false, erros: [`A SPE marca a data do Comitê a partir de hoje (${dataBr(hoje)}).`] };
      const ordinario = atual.comites.find((c) => c.ciclo === atual.ciclo_atual && c.tipo === 'ordinario');
      const comite: ReuniaoComite = ordinario
        ? { ...ordinario, data }
        : { id: proximoId(atual.comites), ciclo: atual.ciclo_atual, tipo: 'ordinario', data };
      dispatch({ tipo: 'comite', comite });
      return { ok: true };
    },
    [atual.comites, atual.ciclo_atual, hoje],
  );

  const convocarExtraordinario = useCallback((): Resultado => {
    const jaConvocado = atual.comites.some((c) => c.ciclo === atual.ciclo_atual && c.tipo === 'extraordinario' && c.data === hoje);
    if (!jaConvocado) {
      dispatch({
        tipo: 'comite',
        comite: { id: proximoId(atual.comites), ciclo: atual.ciclo_atual, tipo: 'extraordinario', data: hoje },
      });
    }
    return { ok: true };
  }, [atual.comites, atual.ciclo_atual, hoje]);

  const decidir = useCallback(
    (municipio: number, cor: Cor, justificativa: string | null): Resultado => {
      const situacao = situacoes.find((s) => s.municipio === municipio);
      const sugerida = situacao?.ciclos.at(-1)?.resultado.cor;
      if (!situacao || !sugerida) return { ok: false, erros: ['Escolha um município da lista.'] };
      const validacao = validarDecisao(sugerida, cor, justificativa);
      if (!validacao.valida) return { ok: false, erros: validacao.erros };
      const texto = justificativa?.trim() ?? '';
      const extraordinario = atual.comites.some(
        (c) => c.ciclo === atual.ciclo_atual && c.tipo === 'extraordinario' && c.data === hoje,
      );
      dispatch({
        tipo: 'decisao',
        decisao: {
          municipio,
          ciclo: atual.ciclo_atual,
          cor_sugerida: sugerida,
          cor_publicada: cor,
          justificativa: texto === '' ? null : texto,
          publicada_em: hoje,
          origem: extraordinario ? 'comite_extraordinario' : 'comite_ordinario',
        },
      });
      return { ok: true };
    },
    [situacoes, atual.comites, atual.ciclo_atual, hoje],
  );

  const anotar = useCallback((texto: string) => dispatch({ tipo: 'anotacao', texto }), []);
  const restaurar = useCallback(() => dispatch({ tipo: 'restaurar' }), []);

  const valor = useMemo<ValorSemaforoDemo>(
    () => ({
      dados: atual,
      situacoes,
      mudouNaSessao: atual !== estado.original,
      registrarResposta,
      registrarOcorrencia,
      responderOcorrencia,
      registrarRelatorio,
      registrarReuniao,
      agendarReuniao,
      registrarAta,
      marcarComite,
      convocarExtraordinario,
      decidir,
      anotacoes: estado.anotacoes,
      anotar,
      restaurar,
    }),
    [
      atual,
      estado.original,
      estado.anotacoes,
      situacoes,
      registrarResposta,
      registrarOcorrencia,
      responderOcorrencia,
      registrarRelatorio,
      registrarReuniao,
      agendarReuniao,
      registrarAta,
      marcarComite,
      convocarExtraordinario,
      decidir,
      anotar,
      restaurar,
    ],
  );

  return <SemaforoDemoContext.Provider value={valor}>{children}</SemaforoDemoContext.Provider>;
}

export function useSemaforoDemo(): ValorSemaforoDemo {
  const valor = useContext(SemaforoDemoContext);
  if (!valor) throw new Error('useSemaforoDemo precisa estar dentro de <SemaforoDemoProvider>.');
  return valor;
}
