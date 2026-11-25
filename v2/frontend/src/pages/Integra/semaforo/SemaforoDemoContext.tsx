/**
 * Estado da sessão da demonstração do Semáforo (DADOS SIMULADOS).
 *
 * Fica só na memória da aba: respostas à pesquisa, ocorrências, relatórios mensais, reuniões de escuta e
 * as decisões do Comitê registradas na tela entram aqui, e a cor sugerida é recalculada na hora (o
 * vermelho imediato da seção 4). O provider mora nas rotas do Semáforo: sair do Semáforo (ir ao ICA, por
 * exemplo) ou recarregar a página volta ao original. Nada é gravado no banco.
 *
 * Tudo o que é registrado leva a data de "hoje" da demonstração (`dados.data_referencia`, 07/12/2026), não
 * a do relógio: assim os prazos e o ciclo batem com a história que está na tela. A data escolhida (ocorrência,
 * reunião) e o mês do relatório ficam no ciclo em andamento: o ciclo já publicado não é recalculado.
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useReducer, type JSX, type ReactNode } from 'react';
import {
  avaliarMunicipio,
  gerarDadosSemaforo,
  mesesDoCiclo,
  periodoDoCiclo,
  tarefasDaPublicacao,
  type DadosSemaforo,
  type ReuniaoEscuta,
  type SituacaoMunicipio,
} from './dados';
import { lista, validarDecisao } from './regras';
import type { Cor, DecisaoComite, Ocorrencia, RelatorioMensal, RespostaPesquisa } from './tipos';

export interface EstadoSemaforoDemo {
  /** Os dados como vieram do gerador (não mudam na sessão). */
  original: DadosSemaforo;
  /** Os dados com o que foi registrado na sessão. */
  dados: DadosSemaforo;
  /** O que foi registrado na tela do relatório mensal, do mais novo ao mais antigo (inclusive a observação de formação). */
  anotacoes: string[];
}

export type AcaoSemaforoDemo =
  | { tipo: 'resposta'; resposta: RespostaPesquisa }
  | { tipo: 'ocorrencia'; ocorrencia: Ocorrencia }
  | { tipo: 'relatorio'; relatorio: RelatorioMensal }
  | { tipo: 'reuniao'; reuniao: ReuniaoEscuta }
  | { tipo: 'decisao'; decisao: DecisaoComite }
  | { tipo: 'anotacao'; texto: string }
  | { tipo: 'restaurar' };

export function reducerSemaforoDemo(estado: EstadoSemaforoDemo, acao: AcaoSemaforoDemo): EstadoSemaforoDemo {
  const d = estado.dados;
  switch (acao.tipo) {
    case 'resposta':
      return { ...estado, dados: { ...d, respostas: [...d.respostas, acao.resposta] } };
    case 'ocorrencia':
      return { ...estado, dados: { ...d, ocorrencias: [...d.ocorrencias, acao.ocorrencia] } };
    case 'relatorio': {
      // O relatório do mesmo mês substitui o anterior (o coordenador corrigiu).
      const { municipio, mes } = acao.relatorio;
      const outros = d.relatorios.filter((r) => !(r.municipio === municipio && r.mes === mes));
      return { ...estado, dados: { ...d, relatorios: [...outros, acao.relatorio] } };
    }
    case 'reuniao':
      return { ...estado, dados: { ...d, reunioes: [...d.reunioes, acao.reuniao] } };
    case 'decisao': {
      // O Comitê pode mudar a decisão no mesmo ciclo. A decisão nova entra no registro, mas as tarefas comparam
      // com a cor publicada no ciclo anterior: as tarefas ainda abertas das decisões deste ciclo saem e entram as
      // da cor nova. Confirmar a mesma cor não mexe nas tarefas.
      const nova = acao.decisao;
      const doMunicipio = d.decisoes.filter((x) => x.municipio === nova.municipio);
      const desteCiclo = doMunicipio.filter((x) => x.ciclo === nova.ciclo);
      const corAnterior = doMunicipio.filter((x) => x.ciclo !== nova.ciclo).at(-1)?.cor_publicada ?? null;
      const corEmVigor = desteCiclo.at(-1)?.cor_publicada ?? corAnterior;
      const decisoes = [...d.decisoes, nova];
      if (nova.cor_publicada === corEmVigor) return { ...estado, dados: { ...d, decisoes } };
      const datas = new Set(desteCiclo.map((x) => x.publicada_em));
      const tarefas = d.tarefas.filter(
        (t) => !(t.municipio === nova.municipio && t.concluida_em === null && datas.has(t.criada_em)),
      );
      return { ...estado, dados: { ...d, decisoes, tarefas: [...tarefas, ...tarefasDaPublicacao(corAnterior, nova)] } };
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
  'municipio' | 'funcao_respondente' | 'identificacao' | 'itens' | 'nps' | 'comentario'
>;
/** Sem `data`, vale hoje. */
export type NovaOcorrencia = Omit<Ocorrencia, 'id' | 'data'> & { data?: string };
export type NovoRelatorio = Omit<RelatorioMensal, 'id' | 'coordenador'>;
export type NovaReuniao = Omit<ReuniaoEscuta, 'id'>;

export interface ValorSemaforoDemo {
  /** Os dados com o que foi registrado na sessão. */
  dados: DadosSemaforo;
  /** A situação de cada município (cor sugerida de cada ciclo, decisão e cor em vigor), na ordem de `dados.municipios`. */
  situacoes: SituacaoMunicipio[];
  /** Algo foi registrado na sessão. */
  mudouNaSessao: boolean;
  /** Entra no ciclo atual com a data de hoje. */
  registrarResposta: (resposta: NovaResposta) => Resultado;
  registrarOcorrencia: (ocorrencia: NovaOcorrencia) => Resultado;
  /** O coordenador é o do município; o relatório do mesmo mês substitui o anterior. */
  registrarRelatorio: (relatorio: NovoRelatorio) => Resultado;
  registrarReuniao: (reuniao: NovaReuniao) => Resultado;
  /** O Comitê confirma ou altera a cor sugerida do ciclo atual; alterar exige justificativa. */
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
      if (data !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(data)) erros.push('Informe a data (dia, mês e ano).');
      else if (data !== undefined && data > hoje) erros.push(`A data não pode ser depois de hoje (${dataBr(hoje)}).`);
      else if (data !== undefined && data < cicloAtual.inicio) {
        erros.push(`A data precisa ser do ciclo atual: de ${dataBr(cicloAtual.inicio)} até hoje (${dataBr(hoje)}).`);
      }
      return erros;
    },
    [atual.municipios, hoje, cicloAtual],
  );

  const registrarResposta = useCallback(
    (r: NovaResposta): Resultado => {
      const erros = errosBase(r.municipio);
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
    [atual, hoje, errosBase],
  );

  const registrarOcorrencia = useCallback(
    (o: NovaOcorrencia): Resultado => {
      const data = o.data ?? hoje;
      const erros = errosBase(o.municipio, data);
      if (erros.length > 0) return { ok: false, erros };
      dispatch({ tipo: 'ocorrencia', ocorrencia: { ...o, data, id: proximoId(atual.ocorrencias) } });
      return { ok: true };
    },
    [atual.ocorrencias, hoje, errosBase],
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
      const coordenador = atual.municipios.find((m) => m.id === r.municipio)?.coordenador ?? null;
      if (erros.length === 0 && coordenador === null) erros.push('Este município ainda não tem coordenador.');
      if (erros.length > 0 || coordenador === null) return { ok: false, erros };
      dispatch({ tipo: 'relatorio', relatorio: { ...r, id: proximoId(atual.relatorios), coordenador } });
      return { ok: true };
    },
    [atual.municipios, atual.relatorios, atual.ciclo_atual, cicloAtual, hoje, errosBase],
  );

  const registrarReuniao = useCallback(
    (r: NovaReuniao): Resultado => {
      const erros = errosBase(r.municipio, r.data);
      if (erros.length > 0) return { ok: false, erros };
      dispatch({ tipo: 'reuniao', reuniao: { ...r, id: proximoId(atual.reunioes) } });
      return { ok: true };
    },
    [atual.reunioes, errosBase],
  );

  const decidir = useCallback(
    (municipio: number, cor: Cor, justificativa: string | null): Resultado => {
      const situacao = situacoes.find((s) => s.municipio === municipio);
      const sugerida = situacao?.ciclos.at(-1)?.resultado.cor;
      if (!situacao || !sugerida) return { ok: false, erros: ['Escolha um município da lista.'] };
      const validacao = validarDecisao(sugerida, cor, justificativa);
      if (!validacao.valida) return { ok: false, erros: validacao.erros };
      const texto = justificativa?.trim() ?? '';
      dispatch({
        tipo: 'decisao',
        decisao: {
          municipio,
          ciclo: atual.ciclo_atual,
          cor_sugerida: sugerida,
          cor_publicada: cor,
          justificativa: texto === '' ? null : texto,
          publicada_em: hoje,
        },
      });
      return { ok: true };
    },
    [situacoes, atual.ciclo_atual, hoje],
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
      registrarRelatorio,
      registrarReuniao,
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
      registrarRelatorio,
      registrarReuniao,
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
