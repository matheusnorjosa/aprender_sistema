/**
 * Gerador dos DADOS SIMULADOS do Semáforo de Risco Municipal. Determinístico: a mesma semente dá sempre a
 * mesma demonstração (o PRNG do ICA, nunca Math.random). Nada é lido nem gravado no banco.
 *
 * Municípios REAIS: os do relatório de deslocamento (`dados/deslocamento.ts`), sem os de ações suspensas.
 * Pessoas FICTÍCIAS: os coordenadores e as gestoras de referência são os da lista fixa do ICA
 * (`dados/gerador.ts`), cadastro único da seção 9 do PDF: o município que também está no ICA leva o id, os
 * projetos (um por atendimento: município × coleção × coordenador) e a gestora de referência de lá (ver
 * `gerarDadosSemaforo`). Os articuladores não têm nome ("Articulador(a) A").
 *
 * "Hoje" da demonstração: segunda-feira, 07/12/2026 (`DATA_REFERENCIA_SEMAFORO`), dia da reunião de
 * validação, no meio do ciclo 2026.6 (nov–dez), com a pesquisa ainda no prazo (link enviado em 01/12, resposta até
 * 15/12: decisão 76). O histórico tem
 * 6 ciclos bimestrais fechados (2025.6 a 2026.5), cada um publicado pelo Comitê ordinário numa sexta-feira,
 * na data marcada pela SPE (decisão 40).
 *
 * A história pronta (garantida por `__tests__/dados.test.ts`) está em `HISTORIAS_SEMAFORO`. Fora dela, o
 * PRNG sorteia um perfil por município e, em alguns ciclos, um único alerta amarelo; as cores sugeridas
 * saem das regras (`regras.ts`), nunca escritas à mão. O vermelho na hora (decisões 38 e 39) também sai das
 * regras, com a data do dado que o disparou.
 */
import { criarPrng, gerarDadosSimulados, SEMENTE_DEMO } from '../dados/gerador';
import { DESLOCAMENTO_MUNICIPIOS } from '../dados/deslocamento';
import type { Coordenador, Pessoa } from '../dados/tipos';
import type { UFCode } from '@/types/organizacao';
import {
  cicloSemAlerta,
  classificar,
  DIAS_ENTRE_REUNIOES,
  contarOcorrencias,
  ocorrenciasForaDaContagem,
  corDaPesquisa,
  corRespostaPesquisa,
  criarTarefas,
  divergem,
  emDiaUtil,
  mediaDaPesquisa,
  mediaNps,
  ocorrenciasDoAno,
  percentualCronograma,
  periodicidadeDaCor,
  piorCor,
  prazoDaPesquisa,
  respondeuNoPrazo,
  somarDias,
  somarDiasUteis,
  somarMeses,
  tarefaAberta,
} from './regras';
import type {
  Ciclo,
  CicloPublicado,
  Cor,
  DecisaoComite,
  Indicador,
  Ocorrencia,
  RelatorioMensal,
  RespostaPesquisa,
  ResultadoCor,
  TarefaResposta,
  ValoresIndicadores,
} from './tipos';

export const SEMENTE_SEMAFORO = SEMENTE_DEMO;
/** O "hoje" fixo da demonstração (segunda-feira da reunião de validação). */
export const DATA_REFERENCIA_SEMAFORO = '2026-12-07';
export const CICLO_ATUAL_SEMAFORO: Ciclo = '2026.6';

/**
 * Um projeto da Aprender Editora contratado pelo município, coordenado por um coordenador (decisão 46). Cada
 * projeto tem o seu relatório mensal, o seu cronograma e a sua pesquisa (decisões 46 e 51).
 */
export interface ProjetoMunicipio {
  /** No ICA, o id do `Atendimento` (município × coleção × coordenador); fora do ICA, acima de 10000. */
  id: number;
  /** O nome da coleção do projeto ("NOVO LENDO"). */
  nome: string;
  /** id do `Coordenador`; `null` = projeto ainda sem coordenador (sem relatório mensal). */
  coordenador: number | null;
  /** Quem responde a pesquisa do projeto, sem nome ("Articulador(a) A"); pode ser o mesmo em dois projetos. */
  articulador: string;
  /**
   * O ciclo em que o projeto começou, quando foi depois do primeiro ciclo dos dados (Itaquiraí-MS, 2026.4). Sem ele,
   * o projeto existe desde antes do histórico. Antes desse ciclo, o projeto não tem coleta nem cor.
   */
  desde?: Ciclo;
}

/** Município monitorado (`Municipio`: id, nome, uf) com quem responde por ele. */
export interface MunicipioSemaforo {
  id: number;
  nome: string;
  uf: UFCode;
  /**
   * id do coordenador do primeiro projeto que tem coordenador; `null` = nenhum projeto com coordenador. Para ver
   * cada projeto, use `projetos`.
   */
  coordenador: number | null;
  /** id da gestora de referência (`Pessoa`); é ela quem manda o link da pesquisa, sem o coordenador (decisão 73). */
  gestora_referencia: number;
  /** Os projetos do município (pelo menos um). */
  projetos: ProjetoMunicipio[];
}

/**
 * Coleta 4: a reunião de escuta com o município (semestral no verde, trimestral no amarelo e no vermelho). É
 * marcada antes e a ata é registrada até 5 dias úteis depois (decisão 48; ver `situacaoDaReuniao`).
 */
export interface ReuniaoEscuta {
  id: number;
  municipio: number;
  /** Data (AAAA-MM-DD) marcada para a reunião. */
  data: string;
  periodicidade: 'semestral' | 'trimestral';
  /** Data (AAAA-MM-DD) em que a ata foi registrada; `null` = ata ainda não registrada. */
  ata_em: string | null;
  /** O município confirmou o cronograma na reunião (vem na ata). */
  cronograma_confirmado: boolean;
  /** O que ficou combinado, sem nomes de pessoas (vem na ata). */
  encaminhamentos: string;
}

export type TipoComite = 'ordinario' | 'extraordinario';

/**
 * Uma reunião do Comitê de Satisfação. O ordinário tem a data marcada pela SPE a cada ciclo (decisão 40); o
 * extraordinário é convocado a critério da SPE (decisão 41).
 */
export interface ReuniaoComite {
  id: number;
  /** O ciclo que o Comitê decide. */
  ciclo: Ciclo;
  tipo: TipoComite;
  /** Data (AAAA-MM-DD) marcada pela SPE. */
  data: string;
}

/** Um relatório mensal que o coordenador corrigiu: a versão anterior, com o dia da correção (AAAA-MM-DD). */
export type RelatorioCorrigido = RelatorioMensal & { corrigido_em: string };

/** Tudo o que o Semáforo lê. Hoje vem do gerador; na versão real, da API do Aprender Sistema. */
export interface DadosSemaforo {
  origem: 'simulado' | 'aprender_sistema';
  /** O "hoje" das contas (AAAA-MM-DD): tarefas, pesquisa no prazo, ocorrências do ano. */
  data_referencia: string;
  ciclo_atual: Ciclo;
  /** Do mais antigo ao atual (o último está em andamento). */
  ciclos: Ciclo[];
  municipios: MunicipioSemaforo[];
  coordenadores: Coordenador[];
  /** As gestoras de referência. */
  pessoas: Pessoa[];
  respostas: RespostaPesquisa[];
  relatorios: RelatorioMensal[];
  /**
   * Decisão 57: as versões anteriores dos relatórios corrigidos (mesmo projeto e mês), com o dia da correção. Ficam
   * guardadas e fora das contas, que leem só `relatorios`.
   */
  relatorios_corrigidos: RelatorioCorrigido[];
  /**
   * Decisões 81 e 82: o que o sistema sabe de cada projeto em cada mês do ciclo atual, e que o relatório mensal traz
   * pré-preenchido: as formações (do Aprender Sistema) e as visitas (da Logística e do pedido de viagem, FRV).
   */
  do_sistema: NumerosDoMes[];
  ocorrencias: Ocorrencia[];
  reunioes: ReuniaoEscuta[];
  /** As reuniões do Comitê marcadas ou convocadas pela SPE. */
  comites: ReuniaoComite[];
  /**
   * Na ordem em que foram publicadas: a última de cada município é a cor em vigor. Inclui o vermelho na hora
   * (`origem: 'vermelho_automatico'`).
   */
  decisoes: DecisaoComite[];
  /** Todas as tarefas, inclusive as concluídas, canceladas e substituídas (decisão 57: nada some). */
  tarefas: TarefaResposta[];
}

/** Os números de um projeto num mês, sem o coordenador: o que o sistema traz para o relatório mensal. */
export type NumerosDoMes = Omit<RelatorioMensal, 'id' | 'coordenador' | 'justificativa'>;

/** Decisões 81 e 82: os números do sistema para o relatório do projeto no mês (AAAA-MM); sem dado, `undefined`. */
export function doSistema(dados: Pick<DadosSemaforo, 'do_sistema'>, projeto: number, mes: string): NumerosDoMes | undefined {
  return dados.do_sistema.find((x) => x.projeto === projeto && x.mes === mes);
}

/** Os municípios da história pronta da demonstração. */
export const HISTORIAS_SEMAFORO = {
  /**
   * Reclamação em 30/11: vermelho na hora, com as tarefas nascendo em 30/11; o Comitê extraordinário, convocado
   * pela SPE, confirmou em 02/12. A reunião com a Secretaria (5 dias úteis) vence hoje. A reclamação foi
   * respondida em 54 h (fora da meta de 48 h) e a ata da reunião de escuta de 04/12 ainda está por registrar.
   */
  vermelho_prazo_hoje: { nome: 'Horizonte', uf: 'CE' },
  /** Vermelho em 2026.4, ciclo limpo em 2026.5: amarelo "em recuperação" (1 de 2). A ata da reunião de 27/11 está atrasada. */
  em_recuperacao: { nome: 'Sobral', uf: 'CE' },
  /** Sem resposta à pesquisa em 2026.4 e 2026.5: vermelho pela resposta. Tem uma reunião de escuta agendada. */
  sem_resposta_dois_ciclos: { nome: 'Jequié', uf: 'BA' },
  /**
   * Um pedido de material em 2026.5 sugeriu amarelo; o Comitê publicou verde, com justificativa. Com a contagem do
   * ano (decisão 32), a mesma ocorrência continua contando até dezembro: no ciclo atual, a sugerida volta a amarelo, e
   * o Comitê teria de alterar de novo (ponto "a régua de 1 e 2 vale o ano inteiro?" na Para validar).
   */
  alterada_pelo_comite: { nome: 'Maringá', uf: 'PR' },
  /** NPS em vermelho em 2026.5 sem nenhuma ocorrência: a pesquisa e as ocorrências divergem (decisão 49). */
  divergente: { nome: 'Mucambo', uf: 'CE' },
} as const satisfies Record<string, { nome: string; uf: UFCode }>;

// ---------------------------------------------------------------- ciclos

export interface PeriodoCiclo {
  inicio: string;
  fim: string;
  /** Decisões 73 e 76: a gestora de referência manda o link no 1º dia útil do segundo mês. */
  envio_pesquisa: string;
  /** Decisão 76: último dia para responder a pesquisa no prazo, 10 dias úteis depois do envio do link. */
  prazo_pesquisa: string;
  /** Os dois meses (AAAA-MM) do ciclo. */
  meses: [string, string];
}

export function periodoDoCiclo(ciclo: Ciclo): PeriodoCiclo {
  const [ano, n] = ciclo.split('.').map(Number) as [number, number];
  const mes = (m: number) => `${ano}-${String(m).padStart(2, '0')}`;
  const meses: [string, string] = [mes(2 * n - 1), mes(2 * n)];
  const envio = emDiaUtil(`${meses[1]}-01`);
  return {
    inicio: `${meses[0]}-01`,
    fim: somarDias(somarMeses(`${meses[1]}-01`, 1), -1),
    envio_pesquisa: envio,
    prazo_pesquisa: prazoDaPesquisa(envio),
    meses,
  };
}

export function cicloAnterior(ciclo: Ciclo): Ciclo {
  const [ano, n] = ciclo.split('.').map(Number) as [number, number];
  return n === 1 ? `${ano - 1}.6` : `${ano}.${n - 1}`;
}

const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

/**
 * Os meses do ciclo, para mostrar junto do código: '2026.6' → 'novembro e dezembro de 2026'. Na tela, o código
 * sozinho confunde: no ICA, o mesmo formato 'AAAA.N' é semestre.
 */
export function mesesDoCiclo(ciclo: Ciclo): string {
  const [primeiro, segundo] = periodoDoCiclo(ciclo).meses.map((m) => MESES[Number(m.slice(5)) - 1]);
  return `${primeiro} e ${segundo} de ${ciclo.slice(0, 4)}`;
}

/** Os meses do ciclo, curtos, para tabela e gráfico: '2026.5' → 'set–out 2026'. */
export function mesesCurtosDoCiclo(ciclo: Ciclo): string {
  const [primeiro, segundo] = periodoDoCiclo(ciclo).meses.map((m) => MESES[Number(m.slice(5)) - 1]!.slice(0, 3));
  return `${primeiro}–${segundo} ${ciclo.slice(0, 4)}`;
}

// ---------------------------------------------------------------- a cor de cada ciclo, a partir das coletas

export type ColetasSemaforo = Pick<DadosSemaforo, 'ciclos' | 'municipios' | 'respostas' | 'relatorios' | 'ocorrencias'>;

/** Os indicadores de um projeto no ciclo (decisões 46 e 51): cada projeto com o seu cronograma e a sua pesquisa. */
export interface ValoresProjeto {
  projeto: number;
  media_pesquisa: number | null;
  nps: number | null;
  cronograma: number | null;
  resposta_pesquisa: ValoresIndicadores['resposta_pesquisa'];
}

/** Os indicadores de cada projeto do município no ciclo, com o que se sabia na data de referência. */
export function valoresPorProjeto(
  coletas: ColetasSemaforo,
  municipio: number,
  ciclo: Ciclo,
  dataReferencia: string,
): ValoresProjeto[] {
  const { meses, prazo_pesquisa } = periodoDoCiclo(ciclo);
  const anterior = cicloAnterior(ciclo);
  // Rodada 4: o projeto só conta a partir do ciclo em que começou (`desde`).
  const projetos = (coletas.municipios.find((m) => m.id === municipio)?.projetos ?? []).filter(
    (p) => p.desde === undefined || ciclo >= p.desde,
  );
  return projetos.map((p) => {
    const respostas = coletas.respostas.filter(
      (r) => r.municipio === municipio && r.projeto === p.id && r.ciclo === ciclo && r.respondida_em <= dataReferencia,
    );
    return {
      projeto: p.id,
      media_pesquisa: mediaDaPesquisa(respostas),
      nps: mediaNps(respostas),
      cronograma: percentualCronograma(
        coletas.relatorios.filter((r) => r.municipio === municipio && r.projeto === p.id && meses.includes(r.mes)),
      ),
      resposta_pesquisa: {
        ciclo_atual: respondeuNoPrazo(respostas, dataReferencia > prazo_pesquisa),
        // Antes do primeiro ciclo dos dados, ou do projeto, não se sabe (não é "não respondeu").
        ciclo_anterior: coletas.ciclos.includes(anterior) && (p.desde === undefined || anterior >= p.desde)
          ? respondeuNoPrazo(
              coletas.respostas.filter((r) => r.municipio === municipio && r.projeto === p.id && r.ciclo === anterior),
              true,
            )
          : null,
      },
    };
  });
}

/**
 * Os 5 indicadores do município no ciclo, com o que se sabia na data de referência. Num ciclo fechado,
 * a data de referência é o fim do ciclo; no ciclo atual, é o "hoje" da demonstração.
 *
 * Com mais de um projeto: média e NPS juntam as respostas de todos os projetos; cronograma e resposta à
 * pesquisa valem os do pior projeto (decisões 46 e 51). Ocorrências contam desde a 1ª formação do ano no
 * município, de qualquer projeto (decisão 32).
 */
export function valoresDoCiclo(
  coletas: ColetasSemaforo,
  municipio: number,
  ciclo: Ciclo,
  dataReferencia: string,
): ValoresIndicadores {
  const porProjeto = valoresPorProjeto(coletas, municipio, ciclo, dataReferencia);
  const respostas = coletas.respostas.filter(
    (r) => r.municipio === municipio && r.ciclo === ciclo && r.respondida_em <= dataReferencia,
  );
  const cronogramas = porProjeto.flatMap((p) => (p.cronograma === null ? [] : [p.cronograma]));
  const doMunicipio = coletas.ocorrencias.filter((o) => o.municipio === municipio);
  const relatoriosDoMunicipio = coletas.relatorios.filter((r) => r.municipio === municipio);
  const fora = ocorrenciasForaDaContagem(doMunicipio, relatoriosDoMunicipio, dataReferencia).length;
  const semDado: ValoresIndicadores['resposta_pesquisa'] = { ciclo_atual: null, ciclo_anterior: null };
  const resposta = porProjeto
    .map((p) => p.resposta_pesquisa)
    .reduce((pior, r) => (piorCor(corRespostaPesquisa(pior), corRespostaPesquisa(r)) === corRespostaPesquisa(pior) ? pior : r), semDado);
  return {
    media_pesquisa: mediaDaPesquisa(respostas),
    nps: mediaNps(respostas),
    cronograma: cronogramas.length === 0 ? null : Math.min(...cronogramas),
    ocorrencias: { ...contarOcorrencias(ocorrenciasDoAno(doMunicipio, relatoriosDoMunicipio, dataReferencia)), fora_da_contagem: fora },
    resposta_pesquisa: resposta,
  };
}

export interface CicloAvaliado {
  ciclo: Ciclo;
  /** A cor que as regras sugerem com os dados do ciclo. */
  resultado: ResultadoCor;
  /** A última decisão do ciclo (do Comitê ou o vermelho na hora); `null` = ainda não publicada. */
  decisao: DecisaoComite | null;
  /**
   * Rodada 4: o ciclo é de antes do primeiro projeto do município (`ProjetoMunicipio.desde`). Não tem coleta nem cor:
   * a tela não mostra a cor sugerida dele.
   */
  antes_do_projeto: boolean;
}

export interface SituacaoMunicipio {
  municipio: number;
  /** Todos os ciclos, do mais antigo ao atual (o atual com os dados até a data de referência). */
  ciclos: CicloAvaliado[];
  /** A última decisão publicada (de qualquer ciclo) e a cor que está em vigor. */
  decisao_vigente: DecisaoComite | null;
  cor_vigente: Cor;
  /** A cor em vigor é um vermelho na hora que o Comitê ainda não confirmou nem desfez (decisão 38). */
  aguardando_comite: boolean;
}

/** A situação do município: a cor sugerida de cada ciclo, o que foi publicado e a cor em vigor. */
export function avaliarMunicipio(dados: DadosSemaforo, municipio: number): SituacaoMunicipio {
  const decisoes = dados.decisoes.filter((d) => d.municipio === municipio);
  const projetos = dados.municipios.find((m) => m.id === municipio)?.projetos ?? [];
  const historico: CicloPublicado[] = [];
  const ciclos = dados.ciclos.map((ciclo): CicloAvaliado => {
    const { fim } = periodoDoCiclo(ciclo);
    const cicloFechado = fim < dados.data_referencia;
    const referencia = cicloFechado ? fim : dados.data_referencia;
    const resultado = classificar(valoresDoCiclo(dados, municipio, ciclo, referencia), historico, { cicloFechado });
    const decisao = decisoes.filter((d) => d.ciclo === ciclo).at(-1) ?? null;
    if (decisao) {
      historico.push({ ciclo, limpo: cicloFechado && cicloSemAlerta(resultado, decisao.cor_publicada), cor_publicada: decisao.cor_publicada });
    }
    const antes_do_projeto = projetos.length > 0 && projetos.every((p) => p.desde !== undefined && ciclo < p.desde);
    return { ciclo, resultado, decisao, antes_do_projeto };
  });
  const decisao_vigente = decisoes.at(-1) ?? null;
  return {
    municipio,
    ciclos,
    decisao_vigente,
    cor_vigente: decisao_vigente?.cor_publicada ?? 'verde',
    aguardando_comite: decisao_vigente?.origem === 'vermelho_automatico',
  };
}

const proximoId = (lista: readonly { id: number }[]): number => lista.reduce((max, x) => Math.max(max, x.id), 0) + 1;

/**
 * As tarefas depois de uma publicação (seção 5). `anterior` é a cor que valia antes (a última decisão do
 * município). Nenhuma tarefa é apagada (decisão 57):
 * - mesma cor no mesmo ciclo (o Comitê confirma o vermelho na hora, ou repete a decisão): nada muda;
 * - o Comitê desfaz um vermelho no mesmo ciclo (o vermelho na hora, ou o que ele mesmo publicou): as abertas do
 *   vermelho ficam "canceladas pelo Comitê"; as feitas continuam feitas (decisão 42). A decisão 42 fala só do
 *   vermelho: quando o Comitê muda um amarelo no mesmo ciclo, as abertas do amarelo continuam abertas;
 * - nascem as tarefas da cor publicada, e as abertas da mesma cor que vinham de antes ficam "substituídas": a
 *   mesma cor publicada de novo reabre todas as tarefas da cor (decisão 43).
 * - rodada 5: ao desfazer o vermelho, as tarefas do vermelho que ele tinha substituído voltam a ficar abertas, como
 *   estavam antes dele (leitura em Para validar; o vermelho desfeito não deixa o município sem elas).
 */
export function tarefasDepoisDaPublicacao(
  tarefas: readonly TarefaResposta[],
  anterior: DecisaoComite | null,
  nova: DecisaoComite,
): TarefaResposta[] {
  if (anterior && anterior.ciclo === nova.ciclo && anterior.cor_publicada === nova.cor_publicada) return [...tarefas];
  const desfazVermelho =
    anterior?.ciclo === nova.ciclo && anterior.cor_publicada === 'vermelho' && nova.origem !== 'vermelho_automatico';
  const corDesfeita = desfazVermelho ? 'vermelho' : null;
  const encerrar = (t: TarefaResposta, motivo: 'cancelada_comite' | 'substituida'): TarefaResposta => ({
    ...t,
    encerramento: { motivo, em: nova.publicada_em },
  });
  const substituidaPeloDesfeito = (t: TarefaResposta): boolean =>
    desfazVermelho && t.cor === 'vermelho' && t.encerramento?.motivo === 'substituida' && t.encerramento.em === anterior.publicada_em;
  const atualizadas = tarefas.map((t) => {
    if (t.municipio !== nova.municipio) return t;
    if (substituidaPeloDesfeito(t)) return { ...t, encerramento: null };
    if (!tarefaAberta(t)) return t;
    if (t.cor === corDesfeita) return encerrar(t, 'cancelada_comite');
    if (t.cor === nova.cor_publicada) return encerrar(t, 'substituida');
    return t;
  });
  return [...atualizadas, ...criarTarefas(nova.cor_publicada, nova.municipio, nova.publicada_em, proximoId(tarefas))];
}

/** Indicador e cor de cada indicador decisivo ("ocorrencias:vermelho"). */
function alertasDecisivos(r: ResultadoCor): string[] {
  return r.avaliacoes.filter((a) => r.decisivos.includes(a.indicador)).map((a) => `${a.indicador}:${a.cor}`);
}

/**
 * Decisões 38 e 39: um indicador em vermelho ou três amarelos mudam a cor oficial na hora, sem esperar o Comitê.
 * Depois de registrar um dado em `depois` (com a data `data`), publica o vermelho na hora (com as tarefas
 * nascendo nessa data, ou no dia da decisão em vigor, se ela for depois), se a cor em vigor ainda não é vermelho.
 *
 * O mesmo alerta que já estava lá antes do registro não volta a disparar: se o Comitê desfez o vermelho, só um
 * alerta novo (outro indicador, ou um indicador que piorou) muda a cor de novo.
 */
export function aplicarVermelhoAutomatico(
  antes: DadosSemaforo,
  depois: DadosSemaforo,
  municipio: number,
  data: string,
): DadosSemaforo {
  const s = avaliarMunicipio(depois, municipio);
  const atual = s.ciclos.at(-1);
  if (!atual?.resultado.vermelho_imediato || s.cor_vigente === 'vermelho') return depois;
  const anterior = avaliarMunicipio(antes, municipio).ciclos.at(-1)?.resultado;
  if (anterior?.vermelho_imediato) {
    const jaHavia = new Set(alertasDecisivos(anterior));
    if (alertasDecisivos(atual.resultado).every((a) => jaHavia.has(a))) return depois;
  }
  // O dado registrado com atraso não põe o vermelho antes da decisão em vigor: o histórico fica em ordem. Se as
  // tarefas contam do dia do dado ou do dia do registro fica para o dono (Para validar).
  const vigente = s.decisao_vigente?.publicada_em;
  const decisao: DecisaoComite = {
    municipio,
    ciclo: atual.ciclo,
    cor_sugerida: 'vermelho',
    cor_publicada: 'vermelho',
    justificativa: null,
    publicada_em: vigente !== undefined && vigente > data ? vigente : data,
    origem: 'vermelho_automatico',
  };
  return {
    ...depois,
    decisoes: [...depois.decisoes, decisao],
    tarefas: tarefasDepoisDaPublicacao(depois.tarefas, s.decisao_vigente, decisao),
  };
}

// ---------------------------------------------------------------- decisão 49: convergência

export interface Convergencia {
  /** O último ciclo fechado. */
  ciclo: Ciclo;
  /** Municípios com pesquisa no ciclo (sem pesquisa, não há o que comparar). */
  comparados: number;
  /** Os que não divergem. */
  concordam: number;
  /** % dos comparados que concordam; `null` = nenhum comparado. */
  percentual: number | null;
  /** Pesquisa verde e ocorrências vermelhas, ou o contrário. */
  divergentes: { municipio: number; pesquisa: Cor; ocorrencias: Cor }[];
}

/**
 * No último ciclo fechado, compara para cada município a cor da pesquisa (a pior entre a média e o NPS) com a
 * cor das ocorrências. Divergem quando uma é verde e a outra vermelha.
 */
export function convergencia(dados: DadosSemaforo, situacoes: readonly SituacaoMunicipio[]): Convergencia {
  const ciclo = dados.ciclos.filter((c) => periodoDoCiclo(c).fim < dados.data_referencia).at(-1) ?? dados.ciclo_atual;
  const divergentes: Convergencia['divergentes'] = [];
  let comparados = 0;
  for (const s of situacoes) {
    const avaliacoes = s.ciclos.find((c) => c.ciclo === ciclo)?.resultado.avaliacoes ?? [];
    const cor = (i: Indicador) => avaliacoes.find((a) => a.indicador === i)?.cor ?? 'sem_dado';
    const pesquisa = corDaPesquisa(cor('media_pesquisa'), cor('nps'));
    const ocorrencias = cor('ocorrencias');
    if (pesquisa === 'sem_dado' || ocorrencias === 'sem_dado') continue;
    comparados++;
    if (divergem(pesquisa, ocorrencias)) divergentes.push({ municipio: s.municipio, pesquisa, ocorrencias });
  }
  const concordam = comparados - divergentes.length;
  return { ciclo, comparados, concordam, percentual: comparados === 0 ? null : (concordam / comparados) * 100, divergentes };
}

// ---------------------------------------------------------------- o gerador

/** Os ciclos fechados e a sexta-feira em que o Comitê ordinário publicou cada um (data marcada pela SPE). */
const PUBLICACAO: Readonly<Record<Ciclo, string>> = {
  '2025.6': '2026-01-09',
  '2026.1': '2026-03-06',
  '2026.2': '2026-05-08',
  '2026.3': '2026-07-10',
  '2026.4': '2026-09-11',
  '2026.5': '2026-11-06',
};
const CICLOS_FECHADOS = Object.keys(PUBLICACAO);
/** Comitê extraordinário convocado pela SPE para o vermelho na hora de Horizonte (quarta-feira). */
const EXTRAORDINARIA = '2026-12-02';
/** O Comitê ordinário do ciclo atual, marcado pela SPE (sexta-feira depois do fim do ciclo). */
const ORDINARIO_DO_CICLO_ATUAL = '2027-01-08';

type Nivel = 'amarelo' | 'vermelho';
/** O alerta planejado de um município num ciclo; o resto do ciclo sai verde. */
type Plano = Partial<Record<Indicador, Nivel>>;

const H = HISTORIAS_SEMAFORO;
const chave = (h: { nome: string; uf: string }) => `${h.nome}-${h.uf}`;
const PLANOS_DA_HISTORIA: Record<string, Record<Ciclo, Plano>> = {
  [chave(H.vermelho_prazo_hoje)]: { '2026.5': { cronograma: 'amarelo' } },
  [chave(H.em_recuperacao)]: { '2026.4': { media_pesquisa: 'vermelho' } },
  [chave(H.sem_resposta_dois_ciclos)]: { '2026.4': { resposta_pesquisa: 'amarelo' }, '2026.5': { resposta_pesquisa: 'amarelo' } },
  [chave(H.alterada_pelo_comite)]: { '2026.5': { ocorrencias: 'amarelo' } },
  [chave(H.divergente)]: { '2026.5': { nps: 'vermelho' } },
};
const ALTERACAO_DO_COMITE = {
  municipio: chave(H.alterada_pelo_comite),
  ciclo: '2026.5',
  cor: 'verde' as Cor,
  justificativa: 'A ocorrência foi um pedido de material, entregue na mesma semana. A Secretaria confirmou que está tudo em dia.',
};
/** A reclamação de Horizonte: registrada numa segunda-feira e respondida 54 h depois (fora da meta de 48 h). */
const RECLAMACAO_DA_HISTORIA = { registrada_em: '2026-11-30T10:15:00-03:00', respondida_em: '2026-12-02T16:15:00-03:00' };

const ALERTAS_SORTEAVEIS: readonly Indicador[] = ['media_pesquisa', 'nps', 'cronograma', 'ocorrencias', 'resposta_pesquisa'];
/** O mês em que as formações do ano começam no município (janeiro é férias). */
const INICIO_DAS_FORMACOES_2026 = ['2026-02', '2026-03', '2026-04'];
const LETRAS = ['A', 'B', 'C', 'D', 'E', 'F'];

const FUNCAO_RESPONDENTE = 'Articulador(a) municipal';
const COMENTARIOS = {
  verde: [
    'Manter o ritmo das formações.',
    'Os professores elogiaram as últimas formações.',
    'Seria bom receber os materiais um pouco antes.',
    'Nada urgente no momento.',
  ],
  amarelo: [
    'Precisamos ajustar o calendário das formações.',
    'Alguns materiais chegaram atrasados.',
    'As devolutivas das avaliações demoraram.',
  ],
  vermelho: ['As formações não estão acontecendo como combinado.', 'Falta retorno da equipe sobre as avaliações.'],
};
const ENCAMINHAMENTOS = {
  semestral: ['Cronograma do semestre confirmado.', 'Agenda das próximas formações combinada.'],
  trimestral: ['Plano de acompanhamento revisto com a Secretaria.', 'Novas datas de formação combinadas.'],
};

/** Data e hora de Fortaleza (UTC−3, sem horário de verão) no formato das ocorrências. */
function comHora(data: string, hora: number, minuto: number): string {
  return `${data}T${String(hora).padStart(2, '0')}:${String(minuto).padStart(2, '0')}:00-03:00`;
}

function somarHoras(dataHora: string, horas: number): string {
  const fortaleza = new Date(Date.parse(dataHora) + (horas - 3) * 3_600_000);
  return `${fortaleza.toISOString().slice(0, 19)}-03:00`;
}

export function gerarDadosSemaforo(semente: number = SEMENTE_SEMAFORO): DadosSemaforo {
  const rng = criarPrng(semente);
  const inteiro = (min: number, max: number) => min + Math.floor(rng() * (max - min + 1));
  const sortear = <T>(lista: readonly T[]): T => lista[Math.floor(rng() * lista.length)] as T;
  const dia = (mes: string, d: number) => `${mes}-${String(d).padStart(2, '0')}`;

  const ica = gerarDadosSimulados(semente);
  const comCarteira = ica.base.coordenadores.filter((c) => ica.base.atendimentos.some((a) => a.coordenador === c.id));
  const idsGestoras = new Set(ica.base.municipios.map((m) => m.gestora_referencia));
  const pessoas = ica.pessoas.filter((p) => idsGestoras.has(p.id));
  const nomeDaColecao = (id: number) => ica.colecoes.find((c) => c.id === id)?.nome ?? 'Projeto';

  // Rodada 3: o projeto que entrou no ICA depois (Itaquiraí-MS, novo em 2026.2) começa no 1º ciclo do semestre em
  // que entrou (`desde`). Só fica guardado o de quem entrou depois do primeiro ciclo dos dados.
  const cicloDeEntrada = new Map<number, Ciclo>();
  for (const a of ica.base.atendimentos) {
    const semestre = ica.historico.find((h) => h.base.atendimentos.some((x) => x.id === a.id))?.semestre;
    const ciclo = semestre ? `${semestre.slice(0, 4)}.${semestre.endsWith('.1') ? 1 : 4}` : '';
    if (ciclo > CICLOS_FECHADOS[0]!) cicloDeEntrada.set(a.id, ciclo);
  }

  // Cadastro único (seção 9 do PDF): o município que está no ICA leva o id, os projetos (um por atendimento) e a
  // gestora de referência de lá. Fora do ICA, id acima de 1000 (não colide), um projeto simulado com o
  // coordenador da carteira do estado (o relatório vem em ordem de UF) e gestora sorteada.
  const reais = DESLOCAMENTO_MUNICIPIOS.filter((m) => !m.acoes_suspensas);
  const municipios: MunicipioSemaforo[] = reais.map((m, i) => {
    const noIca = ica.base.municipios.find((x) => x.nome === m.nome && x.uf === m.uf);
    const contratos = noIca ? ica.base.atendimentos.filter((a) => a.municipio === noIca.id) : [];
    const porEstado = comCarteira[Math.floor((i * comCarteira.length) / reais.length)]!.id;
    const sorteada = sortear(pessoas).id;
    const base =
      contratos.length > 0
        ? contratos.map((a) => {
            const desde = cicloDeEntrada.get(a.id);
            return { id: a.id, nome: nomeDaColecao(a.projeto_geral), coordenador: a.coordenador, ...(desde !== undefined && { desde }) };
          })
        : [{ id: 10001 + i, nome: sortear(ica.colecoes).nome, coordenador: porEstado }];
    // Decisão 51: cada projeto pode ter o seu articulador; às vezes é o mesmo para todos.
    const mesmoArticulador = base.length > 1 && rng() < 0.5;
    const projetos = base.map((p, k) => ({ ...p, articulador: `Articulador(a) ${LETRAS[mesmoArticulador ? 0 : k]}` }));
    return {
      id: noIca?.id ?? 1001 + i,
      nome: m.nome,
      uf: m.uf,
      coordenador: projetos.find((p) => p.coordenador !== null)?.coordenador ?? null,
      gestora_referencia: noIca?.gestora_referencia ?? sorteada,
      projetos,
    };
  });
  const coordenadores = comCarteira.filter((c) => municipios.some((m) => m.projetos.some((p) => p.coordenador === c.id)));

  const respostas: RespostaPesquisa[] = [];
  const relatorios: RelatorioMensal[] = [];
  const ocorrencias: Ocorrencia[] = [];
  const reunioes: ReuniaoEscuta[] = [];
  // Rodada 4: contador próprio. Com `reunioes.length + 1`, a reunião tirada abaixo fazia o id se repetir.
  let ultimaReuniao = 0;
  const idDaReuniao = () => ++ultimaReuniao;
  /** As reuniões que a história pede (Horizonte e Jequié): ficam quando outra cai perto delas. */
  const daHistoria = new Set<ReuniaoEscuta>();
  const decisoes: DecisaoComite[] = [];
  let tarefas: TarefaResposta[] = [];

  /** Uma resposta por projeto no ciclo (decisão 51), cada uma num dia sorteado por `quando`. */
  const responder = (m: MunicipioSemaforo, ciclo: Ciclo, quando: () => string, plano: Plano) => {
    const media = plano.media_pesquisa ?? 'verde';
    const nps = plano.nps ?? 'verde';
    for (const p of m.projetos) {
      const data = quando();
      const itens = Array.from({ length: 6 }, (_, i) =>
        media === 'verde' ? (rng() < 0.55 ? 5 : 4) : media === 'amarelo' ? (i < 3 || rng() < 0.5 ? 3 : 4) : i < 3 || rng() < 0.5 ? 2 : 3,
      );
      respostas.push({
        id: respostas.length + 1,
        municipio: m.id,
        projeto: p.id,
        ciclo,
        respondida_em: data,
        no_prazo: data <= periodoDoCiclo(ciclo).prazo_pesquisa,
        funcao_respondente: FUNCAO_RESPONDENTE,
        identificacao: null,
        itens,
        nps: nps === 'verde' ? inteiro(9, 10) : nps === 'amarelo' ? inteiro(7, 8) : inteiro(5, 6),
        comentario: sortear(COMENTARIOS[media === 'verde' ? nps : media]),
      });
    }
  };

  /** Um relatório por projeto com coordenador e mês; o cronograma amarelo vai no primeiro projeto. */
  const relatar = (m: MunicipioSemaforo, plano: Plano, meses: readonly string[]) => {
    m.projetos.forEach((p, k) => {
      const coordenador = p.coordenador;
      if (coordenador === null) return;
      const doCiclo = meses.map((mes): Omit<RelatorioMensal, 'id'> => {
        const formacoes = inteiro(3, 4);
        const visitas = inteiro(1, 2);
        return {
          municipio: m.id,
          projeto: p.id,
          coordenador,
          mes,
          formacoes_previstas: formacoes,
          formacoes_realizadas: formacoes,
          visitas_previstas: visitas,
          visitas_realizadas: visitas,
        };
      });
      if (k === 0 && plano.cronograma === 'amarelo' && doCiclo[0]) {
        // Dois meses: 8 a 12 previstas, 2 que não aconteceram (75% a 83%). Um mês: 4 a 6 previstas, 1 a menos.
        doCiclo[0].formacoes_realizadas -= doCiclo.length === 2 ? 2 : 1;
      }
      for (const r of doCiclo) relatorios.push({ ...r, id: relatorios.length + 1 });
    });
  };

  const registrarOcorrencia = (o: Omit<Ocorrencia, 'id'>) => ocorrencias.push({ ...o, id: ocorrencias.length + 1 });

  // 1. As coletas de cada município, ciclo a ciclo.
  for (const m of municipios) {
    const historia = PLANOS_DA_HISTORIA[`${m.nome}-${m.uf}`];
    const chanceDeAlerta = rng() < 0.7 ? 0.05 : 0.3;
    // Decisão 32: as formações de 2026 começam num mês diferente em cada município.
    const inicio2026 = sortear(INICIO_DAS_FORMACOES_2026);
    let semRespostaAntes = false;
    // Ocorrências contam o ano todo: uma segunda no mesmo ano daria vermelho (fica para a história).
    const anosComOcorrencia = new Set<string>();

    for (const ciclo of CICLOS_FECHADOS) {
      const { meses } = periodoDoCiclo(ciclo);
      let plano: Plano = historia?.[ciclo] ?? {};
      // Nada sorteado no penúltimo ciclo: um amarelo ali viraria outro "em recuperação" no último publicado,
      // e a história tem um só.
      if (!historia && ciclo !== CICLOS_FECHADOS.at(-2) && rng() < chanceDeAlerta) {
        // Um só amarelo por ciclo; sem resposta duas vezes seguidas daria vermelho (fica para a história).
        const opcoes = ALERTAS_SORTEAVEIS.filter(
          (i) => !(semRespostaAntes && i === 'resposta_pesquisa') && !(i === 'ocorrencias' && anosComOcorrencia.has(ciclo.slice(0, 4))),
        );
        plano = { [sortear(opcoes)]: 'amarelo' };
        // Decisão 32: antes da 1ª formação do ano, a ocorrência não conta, e o amarelo sorteado sumiria sem aviso. Em
        // 2026.1, o 2º mês (fevereiro) pode vir antes do início das formações do município; e o município só com
        // projeto sem coordenador não tem relatório, nem formação. Nesses casos o ciclo fica verde. Não consome
        // sorteio, para não mudar o resto dos dados da semente.
        const antesDaFormacao = meses[1].startsWith('2026-') && meses[1] < inicio2026;
        if (plano.ocorrencias && (antesDaFormacao || m.coordenador === null)) plano = {};
      }
      semRespostaAntes = plano.resposta_pesquisa !== undefined;

      // Decisão 76: a resposta fica entre o envio do link (no máximo dia 3) e o prazo (no mínimo dia 15). O dia
      // sorteado depois do 14 fica no 14: o sorteio não muda, e as datas da história ficam as mesmas.
      if (!semRespostaAntes) responder(m, ciclo, () => dia(meses[1], Math.min(inteiro(3, 18), 14)), plano);
      relatar(
        m,
        plano,
        meses.filter((mes) => !mes.startsWith('2026-') || mes >= inicio2026),
      );
      if (plano.ocorrencias) {
        anosComOcorrencia.add(ciclo.slice(0, 4));
        // No segundo mês do ciclo, depois do início das formações do ano no município (garantido acima).
        const data = dia(meses[1], inteiro(2, 6));
        const registrada_em = comHora(data, inteiro(8, 16), sortear([0, 15, 30, 45]));
        registrarOcorrencia({
          municipio: m.id,
          data,
          registrada_em,
          respondida_em: somarHoras(registrada_em, inteiro(2, 40)),
          origem: 'fluxo_unico',
          tipo: 'leve',
        });
      }
    }

    // Ciclo atual (nov–dez/2026): relatório de novembro entregue; a pesquisa está aberta até 15/12 (decisão 76).
    relatar(m, {}, ['2026-11']);
    const sem_resposta = `${m.nome}-${m.uf}` === chave(H.sem_resposta_dois_ciclos);
    if (!sem_resposta && rng() < 0.5) responder(m, CICLO_ATUAL_SEMAFORO, () => dia('2026-12', inteiro(1, 7)), {});
    if (`${m.nome}-${m.uf}` === chave(H.vermelho_prazo_hoje)) {
      registrarOcorrencia({
        municipio: m.id,
        data: RECLAMACAO_DA_HISTORIA.registrada_em.slice(0, 10),
        ...RECLAMACAO_DA_HISTORIA,
        origem: 'fluxo_unico',
        tipo: 'reclamacao',
      });
    }

    // Reuniões semestrais de escuta (março e setembro), num dia útil, com a ata em até 4 dias úteis.
    for (const mes of ['2026-03', '2026-09']) {
      const data = emDiaUtil(dia(mes, inteiro(10, 26)));
      reunioes.push({
        id: idDaReuniao(),
        municipio: m.id,
        data,
        periodicidade: 'semestral',
        ata_em: somarDiasUteis(data, inteiro(1, 4)),
        cronograma_confirmado: rng() < 0.9,
        encaminhamentos: sortear(ENCAMINHAMENTOS.semestral),
      });
    }
  }

  // Rodada 3: o projeto que entrou no ICA depois (Itaquiraí-MS) não tem coleta nem cor antes do ciclo em que
  // começou. As coletas são sorteadas antes e tiradas aqui, para não mudar o resto dos dados da semente.
  // Ciclo vazio = desde sempre (o projeto que está fora do ICA ou que já estava no retrato mais antigo).
  const entradaDoProjeto = (projeto: number): Ciclo => cicloDeEntrada.get(projeto) ?? '';
  const entradaDoMunicipio = (municipio: number): Ciclo =>
    municipios.find((m) => m.id === municipio)!.projetos.map((p) => entradaDoProjeto(p.id)).sort()[0] ?? '';
  const inicioDe = (ciclo: Ciclo): string => (ciclo === '' ? '' : periodoDoCiclo(ciclo).inicio);
  const tirar = <T,>(lista: T[], antes: (x: T) => boolean) => lista.splice(0, lista.length, ...lista.filter((x) => !antes(x)));
  tirar(respostas, (r) => r.ciclo < entradaDoProjeto(r.projeto));
  tirar(relatorios, (r) => `${r.mes}-01` < inicioDe(entradaDoProjeto(r.projeto)));
  tirar(reunioes, (r) => r.data < inicioDe(entradaDoMunicipio(r.municipio)));

  // Decisões 81 e 82: o que o sistema traz para o relatório de cada projeto no ciclo atual. Novembro é o que foi
  // entregue; dezembro segue o ritmo de novembro (sem sorteio, para não mudar o resto dos dados da semente).
  const do_sistema: NumerosDoMes[] = relatorios
    .filter((r) => r.mes === periodoDoCiclo(CICLO_ATUAL_SEMAFORO).meses[0])
    .flatMap((r) =>
      periodoDoCiclo(CICLO_ATUAL_SEMAFORO).meses.map((mes) => ({
        municipio: r.municipio,
        projeto: r.projeto,
        mes,
        formacoes_previstas: r.formacoes_previstas,
        formacoes_realizadas: r.formacoes_realizadas,
        visitas_previstas: r.visitas_previstas,
        visitas_realizadas: r.visitas_realizadas,
      })),
    );

  // 2. A cor oficial de cada ciclo: o vermelho na hora, na data do dado, e o Comitê ordinário no fim do ciclo.
  const coletas: ColetasSemaforo = { ciclos: [...CICLOS_FECHADOS, CICLO_ATUAL_SEMAFORO], municipios, respostas, relatorios, ocorrencias };
  const ehDaHistoria = (m: MunicipioSemaforo, h: { nome: string; uf: string }) => `${m.nome}-${m.uf}` === chave(h);

  for (const m of municipios) {
    const historico: CicloPublicado[] = [];
    const doMunicipio: DecisaoComite[] = [];

    /** O que venceu antes da data foi feito na véspera do prazo (ou no dia em que nasceu). */
    const concluirAte = (data: string) => {
      tarefas = tarefas.map((t) => {
        if (t.municipio !== m.id || !tarefaAberta(t) || t.prazo_em >= data) return t;
        const vespera = somarDias(t.prazo_em, -1);
        return { ...t, concluida_em: vespera < t.criada_em ? t.criada_em : vespera };
      });
    };

    const publicar = (decisao: DecisaoComite) => {
      concluirAte(decisao.publicada_em);
      const anterior = doMunicipio.at(-1) ?? null;
      const confirmacao = anterior?.ciclo === decisao.ciclo && anterior.cor_publicada === decisao.cor_publicada;
      tarefas = tarefasDepoisDaPublicacao(tarefas, anterior, decisao);
      decisoes.push(decisao);
      doMunicipio.push(decisao);
      // Reunião de escuta trimestral 3 semanas depois da cor nova (a confirmação não marca outra).
      const data = emDiaUtil(somarDias(decisao.publicada_em, 21));
      if (decisao.cor_publicada !== 'verde' && !confirmacao && data <= DATA_REFERENCIA_SEMAFORO) {
        const ata = somarDiasUteis(data, inteiro(1, 4));
        reunioes.push({
          id: idDaReuniao(),
          municipio: m.id,
          data,
          periodicidade: 'trimestral',
          // A ata de Sobral (27/11) passou do prazo de 5 dias úteis sem registro: "ata atrasada".
          ata_em: (ehDaHistoria(m, H.em_recuperacao) && decisao.ciclo === '2026.5') || ata > DATA_REFERENCIA_SEMAFORO ? null : ata,
          cronograma_confirmado: true,
          encaminhamentos: sortear(ENCAMINHAMENTOS.trimestral),
        });
      }
    };

    /** O primeiro dia em que o ciclo ficou em vermelho na hora (até `ate`), depois da última publicação. */
    const dataDoVermelhoNaHora = (ciclo: Ciclo, ate: string): string | null => {
      const aberto = { cicloFechado: false };
      if (!classificar(valoresDoCiclo(coletas, m.id, ciclo, ate), historico, aberto).vermelho_imediato) return null;
      const { inicio, prazo_pesquisa } = periodoDoCiclo(ciclo);
      const ultima = doMunicipio.at(-1)?.publicada_em;
      const desde = ultima !== undefined && ultima >= inicio ? somarDias(ultima, 1) : inicio;
      const candidatas = [
        desde,
        somarDias(prazo_pesquisa, 1),
        ...respostas.filter((r) => r.municipio === m.id && r.ciclo === ciclo).map((r) => r.respondida_em),
        ...ocorrencias.filter((o) => o.municipio === m.id).map((o) => o.data),
      ];
      const datas = [...new Set(candidatas)].filter((d) => d >= desde && d <= ate).sort();
      return datas.find((d) => classificar(valoresDoCiclo(coletas, m.id, ciclo, d), historico, aberto).vermelho_imediato) ?? null;
    };

    const vermelhoNaHora = (ciclo: Ciclo, ate: string) => {
      if (doMunicipio.at(-1)?.cor_publicada === 'vermelho') return;
      const data = dataDoVermelhoNaHora(ciclo, ate);
      if (data === null) return;
      publicar({
        municipio: m.id,
        ciclo,
        cor_sugerida: 'vermelho',
        cor_publicada: 'vermelho',
        justificativa: null,
        publicada_em: data,
        origem: 'vermelho_automatico',
      });
    };

    for (const ciclo of CICLOS_FECHADOS) {
      if (ciclo < entradaDoMunicipio(m.id)) continue;
      const { fim } = periodoDoCiclo(ciclo);
      vermelhoNaHora(ciclo, fim);
      const resultado = classificar(valoresDoCiclo(coletas, m.id, ciclo, fim), historico);
      const alterada = ALTERACAO_DO_COMITE.municipio === `${m.nome}-${m.uf}` && ALTERACAO_DO_COMITE.ciclo === ciclo;
      publicar({
        municipio: m.id,
        ciclo,
        cor_sugerida: resultado.cor,
        cor_publicada: alterada ? ALTERACAO_DO_COMITE.cor : resultado.cor,
        justificativa: alterada ? ALTERACAO_DO_COMITE.justificativa : null,
        publicada_em: PUBLICACAO[ciclo]!,
        origem: 'comite_ordinario',
      });
      const publicada = doMunicipio.at(-1)!.cor_publicada;
      historico.push({ ciclo, limpo: cicloSemAlerta(resultado, publicada), cor_publicada: publicada });
    }

    vermelhoNaHora(CICLO_ATUAL_SEMAFORO, DATA_REFERENCIA_SEMAFORO);
    if (ehDaHistoria(m, H.vermelho_prazo_hoje)) {
      // A SPE convocou o Comitê extraordinário, que confirmou o vermelho na hora: as tarefas seguem.
      const valores = valoresDoCiclo(coletas, m.id, CICLO_ATUAL_SEMAFORO, EXTRAORDINARIA);
      const resultado = classificar(valores, historico, { cicloFechado: false });
      publicar({
        municipio: m.id,
        ciclo: CICLO_ATUAL_SEMAFORO,
        cor_sugerida: resultado.cor,
        cor_publicada: resultado.cor,
        justificativa: null,
        publicada_em: EXTRAORDINARIA,
        origem: 'comite_extraordinario',
      });
      // Reunião de escuta depois da reclamação; a ata ainda está no prazo (até 11/12). A trimestral de 27/11, marcada
      // depois do amarelo, sai no fim (rodada 4: uma reunião por vez).
      const depoisDaReclamacao: ReuniaoEscuta = {
        id: idDaReuniao(),
        municipio: m.id,
        data: '2026-12-04',
        periodicidade: 'trimestral',
        ata_em: null,
        cronograma_confirmado: false,
        encaminhamentos: '',
      };
      reunioes.push(depoisDaReclamacao);
      daHistoria.add(depoisDaReclamacao);
    }
    if (ehDaHistoria(m, H.sem_resposta_dois_ciclos)) {
      // Reunião de escuta já marcada, ainda por acontecer.
      const agendada: ReuniaoEscuta = {
        id: idDaReuniao(),
        municipio: m.id,
        data: '2026-12-10',
        periodicidade: 'trimestral',
        ata_em: null,
        cronograma_confirmado: false,
        encaminhamentos: '',
      };
      reunioes.push(agendada);
      daHistoria.add(agendada);
    }
    concluirAte(DATA_REFERENCIA_SEMAFORO);
  }

  // Rodada 4: uma reunião de escuta por vez. A semestral de março e de setembro é sorteada antes das cores; quando
  // duas caem a menos de 30 dias uma da outra, fica a da história, depois a trimestral (a que a cor pediu), depois a
  // mais antiga. A periodicidade vem da cor em vigor no dia: semestral no verde, trimestral no amarelo e no vermelho.
  const prioridade = (r: ReuniaoEscuta) => (daHistoria.has(r) ? 2 : r.periodicidade === 'trimestral' ? 1 : 0);
  const TRINTA_DIAS = DIAS_ENTRE_REUNIOES * 86_400_000;
  const ficam: ReuniaoEscuta[] = [];
  for (const r of [...reunioes].sort((a, b) => prioridade(b) - prioridade(a) || a.data.localeCompare(b.data))) {
    const perto = ficam.some((x) => x.municipio === r.municipio && Math.abs(Date.parse(x.data) - Date.parse(r.data)) < TRINTA_DIAS);
    if (!perto) ficam.push(r);
  }
  const corNoDia = (r: ReuniaoEscuta): Cor =>
    decisoes.filter((d) => d.municipio === r.municipio && d.publicada_em <= r.data).at(-1)?.cor_publicada ?? 'verde';
  const periodicas = reunioes
    .filter((r) => ficam.includes(r))
    .map((r): ReuniaoEscuta => {
      const periodicidade = periodicidadeDaCor(corNoDia(r));
      // O encaminhamento sorteado troca pelo da mesma posição na lista da periodicidade certa.
      const posicao = ENCAMINHAMENTOS[r.periodicidade].indexOf(r.encaminhamentos);
      const encaminhamentos = posicao < 0 ? r.encaminhamentos : ENCAMINHAMENTOS[periodicidade][posicao]!;
      return { ...r, periodicidade, encaminhamentos };
    });
  reunioes.splice(0, reunioes.length, ...periodicas);

  const comites: ReuniaoComite[] = [
    ...CICLOS_FECHADOS.map((ciclo, i): ReuniaoComite => ({ id: i + 1, ciclo, tipo: 'ordinario', data: PUBLICACAO[ciclo]! })),
    { id: CICLOS_FECHADOS.length + 1, ciclo: CICLO_ATUAL_SEMAFORO, tipo: 'extraordinario', data: EXTRAORDINARIA },
    { id: CICLOS_FECHADOS.length + 2, ciclo: CICLO_ATUAL_SEMAFORO, tipo: 'ordinario', data: ORDINARIO_DO_CICLO_ATUAL },
  ];

  return {
    origem: 'simulado',
    data_referencia: DATA_REFERENCIA_SEMAFORO,
    ciclo_atual: CICLO_ATUAL_SEMAFORO,
    ciclos: coletas.ciclos,
    municipios,
    coordenadores: coordenadores.map((c) => ({ ...c })),
    pessoas: pessoas.map((p) => ({ ...p })),
    respostas,
    relatorios,
    relatorios_corrigidos: [],
    do_sistema,
    ocorrencias,
    reunioes,
    comites,
    decisoes,
    tarefas,
  };
}
