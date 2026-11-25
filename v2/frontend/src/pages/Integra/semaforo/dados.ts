/**
 * Gerador dos DADOS SIMULADOS do Semáforo de Risco Municipal. Determinístico: a mesma semente dá sempre a
 * mesma demonstração (o PRNG do ICA, nunca Math.random). Nada é lido nem gravado no banco.
 *
 * Municípios REAIS: os do relatório de deslocamento (`dados/deslocamento.ts`), sem os de ações suspensas.
 * Pessoas FICTÍCIAS: os coordenadores e as gestoras de referência são os da lista fixa do ICA
 * (`dados/gerador.ts`), cadastro único da seção 9 do PDF: o município que também está no ICA leva o id, o
 * coordenador e a gestora de referência de lá (ver `gerarDadosSemaforo`).
 *
 * "Hoje" da demonstração: segunda-feira, 07/12/2026 (`DATA_REFERENCIA_SEMAFORO`), dia da reunião de
 * validação, no meio do ciclo 2026.6 (nov–dez), com a pesquisa ainda no prazo (até 20/12). O histórico tem
 * 6 ciclos bimestrais fechados (2025.6 a 2026.5), cada um publicado pelo Comitê numa sexta-feira.
 *
 * A história pronta (garantida por `__tests__/dados.test.ts`) está em `HISTORIAS_SEMAFORO`. Fora dela, o
 * PRNG sorteia um perfil por município e, em alguns ciclos, um único alerta amarelo; as cores sugeridas
 * saem das regras (`regras.ts`), nunca escritas à mão.
 */
import { criarPrng, gerarDadosSimulados, SEMENTE_DEMO } from '../dados/gerador';
import { DESLOCAMENTO_MUNICIPIOS } from '../dados/deslocamento';
import type { Coordenador, Pessoa } from '../dados/tipos';
import type { UFCode } from '@/types/organizacao';
import {
  classificar,
  contarOcorrencias,
  criarTarefas,
  mediaDaPesquisa,
  mediaNps,
  ocorrenciasNoTrimestre,
  percentualCronograma,
  respondeuNoPrazo,
  somarDias,
  somarMeses,
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

/** Município monitorado (`Municipio`: id, nome, uf) com quem responde por ele. */
export interface MunicipioSemaforo {
  id: number;
  nome: string;
  uf: UFCode;
  /** id do `Coordenador` responsável; `null` = contrato ainda sem coordenador (sem relatório mensal). */
  coordenador: number | null;
  /** id da gestora de referência (`Pessoa`). */
  gestora_referencia: number;
}

/** Coleta 4: a reunião de escuta com o município (semestral no verde, trimestral no amarelo e no vermelho). */
export interface ReuniaoEscuta {
  id: number;
  municipio: number;
  /** Data (AAAA-MM-DD) da reunião. */
  data: string;
  periodicidade: 'semestral' | 'trimestral';
  /** O município confirmou o cronograma na reunião. */
  cronograma_confirmado: boolean;
  /** O que ficou combinado (sem nomes de pessoas). */
  encaminhamentos: string;
}

/** Tudo o que o Semáforo lê. Hoje vem do gerador; na versão real, da API do Aprender Sistema. */
export interface DadosSemaforo {
  origem: 'simulado' | 'aprender_sistema';
  /** O "hoje" das contas (AAAA-MM-DD): tarefas, pesquisa no prazo, ocorrências do trimestre. */
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
  ocorrencias: Ocorrencia[];
  reunioes: ReuniaoEscuta[];
  /** Na ordem em que foram publicadas: a última de cada município é a cor em vigor. */
  decisoes: DecisaoComite[];
  tarefas: TarefaResposta[];
}

/** Os municípios da história pronta da demonstração. */
export const HISTORIAS_SEMAFORO = {
  /** Reclamação em 01/12, Comitê extraordinário em 02/12: a reunião com a Secretaria vence hoje. */
  vermelho_prazo_hoje: { nome: 'Horizonte', uf: 'CE' },
  /** Vermelho em 2026.4, ciclo limpo em 2026.5: amarelo "em recuperação" (1 de 2). */
  em_recuperacao: { nome: 'Sobral', uf: 'CE' },
  /** Sem resposta à pesquisa em 2026.4 e 2026.5: vermelho pela resposta. */
  sem_resposta_dois_ciclos: { nome: 'Jequié', uf: 'BA' },
  /** Um pedido de material em 2026.5 sugeriu amarelo; o Comitê publicou verde, com justificativa. */
  alterada_pelo_comite: { nome: 'Maringá', uf: 'PR' },
} as const satisfies Record<string, { nome: string; uf: UFCode }>;

// ---------------------------------------------------------------- ciclos

export interface PeriodoCiclo {
  inicio: string;
  fim: string;
  /** Último dia para responder a pesquisa no prazo: dia 20 do segundo mês. */
  prazo_pesquisa: string;
  /** Os dois meses (AAAA-MM) do ciclo. */
  meses: [string, string];
}

export function periodoDoCiclo(ciclo: Ciclo): PeriodoCiclo {
  const [ano, n] = ciclo.split('.').map(Number) as [number, number];
  const mes = (m: number) => `${ano}-${String(m).padStart(2, '0')}`;
  const meses: [string, string] = [mes(2 * n - 1), mes(2 * n)];
  return {
    inicio: `${meses[0]}-01`,
    fim: somarDias(somarMeses(`${meses[1]}-01`, 1), -1),
    prazo_pesquisa: `${meses[1]}-20`,
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

export type ColetasSemaforo = Pick<DadosSemaforo, 'ciclos' | 'respostas' | 'relatorios' | 'ocorrencias'>;

/**
 * Os 5 indicadores do município no ciclo, com o que se sabia na data de referência. Num ciclo fechado,
 * a data de referência é o fim do ciclo; no ciclo atual, é o "hoje" da demonstração.
 */
export function valoresDoCiclo(
  coletas: ColetasSemaforo,
  municipio: number,
  ciclo: Ciclo,
  dataReferencia: string,
): ValoresIndicadores {
  const { meses, prazo_pesquisa } = periodoDoCiclo(ciclo);
  const anterior = cicloAnterior(ciclo);
  const respostas = coletas.respostas.filter(
    (r) => r.municipio === municipio && r.ciclo === ciclo && r.respondida_em <= dataReferencia,
  );
  return {
    media_pesquisa: mediaDaPesquisa(respostas),
    nps: mediaNps(respostas),
    cronograma: percentualCronograma(coletas.relatorios.filter((r) => r.municipio === municipio && meses.includes(r.mes))),
    ocorrencias: contarOcorrencias(
      ocorrenciasNoTrimestre(
        coletas.ocorrencias.filter((o) => o.municipio === municipio),
        dataReferencia,
      ),
    ),
    resposta_pesquisa: {
      ciclo_atual: respondeuNoPrazo(respostas, dataReferencia > prazo_pesquisa),
      // Antes do primeiro ciclo dos dados não se sabe (não é "não respondeu").
      ciclo_anterior: coletas.ciclos.includes(anterior)
        ? respondeuNoPrazo(
            coletas.respostas.filter((r) => r.municipio === municipio && r.ciclo === anterior),
            true,
          )
        : null,
    },
  };
}

export interface CicloAvaliado {
  ciclo: Ciclo;
  /** A cor que as regras sugerem com os dados do ciclo. */
  resultado: ResultadoCor;
  /** A última decisão do Comitê para o ciclo; `null` = ainda não publicada. */
  decisao: DecisaoComite | null;
}

export interface SituacaoMunicipio {
  municipio: number;
  /** Todos os ciclos, do mais antigo ao atual (o atual com os dados até a data de referência). */
  ciclos: CicloAvaliado[];
  /** A última decisão publicada (de qualquer ciclo) e a cor que está em vigor. */
  decisao_vigente: DecisaoComite | null;
  cor_vigente: Cor;
}

/** A situação do município: a cor sugerida de cada ciclo, o que o Comitê publicou e a cor em vigor. */
export function avaliarMunicipio(dados: DadosSemaforo, municipio: number): SituacaoMunicipio {
  const decisoes = dados.decisoes.filter((d) => d.municipio === municipio);
  const historico: CicloPublicado[] = [];
  const ciclos = dados.ciclos.map((ciclo): CicloAvaliado => {
    const { fim } = periodoDoCiclo(ciclo);
    const cicloFechado = fim < dados.data_referencia;
    const referencia = cicloFechado ? fim : dados.data_referencia;
    const resultado = classificar(valoresDoCiclo(dados, municipio, ciclo, referencia), historico, { cicloFechado });
    const decisao = decisoes.filter((d) => d.ciclo === ciclo).at(-1) ?? null;
    if (decisao) historico.push({ ciclo, limpo: resultado.limpo && cicloFechado, cor_publicada: decisao.cor_publicada });
    return { ciclo, resultado, decisao };
  });
  const decisao_vigente = decisoes.at(-1) ?? null;
  return { municipio, ciclos, decisao_vigente, cor_vigente: decisao_vigente?.cor_publicada ?? 'verde' };
}

/**
 * As tarefas da publicação (seção 5), com prazo contado da data publicada. Só nascem quando a cor em vigor
 * muda: o Comitê que confirma o mesmo vermelho no ciclo seguinte não reabre o "contato em 48 h".
 */
export function tarefasDaPublicacao(corAnterior: Cor | null, decisao: DecisaoComite): TarefaResposta[] {
  if (decisao.cor_publicada === corAnterior) return [];
  return criarTarefas(decisao.cor_publicada, decisao.municipio, decisao.publicada_em);
}

// ---------------------------------------------------------------- o gerador

/** Os ciclos fechados e a sexta-feira em que o Comitê publicou cada um. */
const PUBLICACAO: Readonly<Record<Ciclo, string>> = {
  '2025.6': '2026-01-09',
  '2026.1': '2026-03-06',
  '2026.2': '2026-05-08',
  '2026.3': '2026-07-10',
  '2026.4': '2026-09-11',
  '2026.5': '2026-11-06',
};
const CICLOS_FECHADOS = Object.keys(PUBLICACAO);
/** Comitê extraordinário do vermelho imediato (quarta-feira). */
const EXTRAORDINARIA = '2026-12-02';

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
};
const ALTERACAO_DO_COMITE = {
  municipio: chave(H.alterada_pelo_comite),
  ciclo: '2026.5',
  cor: 'verde' as Cor,
  justificativa: 'A ocorrência foi um pedido de material, entregue na mesma semana. A Secretaria confirmou que está tudo em dia.',
};

const ALERTAS_SORTEAVEIS: readonly Indicador[] = ['media_pesquisa', 'nps', 'cronograma', 'ocorrencias', 'resposta_pesquisa'];

const FUNCOES = ['Articulador(a) municipal', 'Secretário(a) municipal de educação'];
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

export function gerarDadosSemaforo(semente: number = SEMENTE_SEMAFORO): DadosSemaforo {
  const rng = criarPrng(semente);
  const inteiro = (min: number, max: number) => min + Math.floor(rng() * (max - min + 1));
  const sortear = <T>(lista: readonly T[]): T => lista[Math.floor(rng() * lista.length)] as T;
  const dia = (mes: string, d: number) => `${mes}-${String(d).padStart(2, '0')}`;

  const ica = gerarDadosSimulados(semente);
  const comCarteira = ica.base.coordenadores.filter((c) => ica.base.atendimentos.some((a) => a.coordenador === c.id));
  const idsGestoras = new Set(ica.base.municipios.map((m) => m.gestora_referencia));
  const pessoas = ica.pessoas.filter((p) => idsGestoras.has(p.id));

  // Cadastro único (seção 9 do PDF): o município que está no ICA leva o id, o coordenador (o do primeiro
  // contrato com coordenador) e a gestora de referência de lá. Fora do ICA, id acima de 1000 (não colide),
  // carteira por estado (o relatório vem em ordem de UF) e gestora sorteada.
  const reais = DESLOCAMENTO_MUNICIPIOS.filter((m) => !m.acoes_suspensas);
  const municipios: MunicipioSemaforo[] = reais.map((m, i) => {
    const noIca = ica.base.municipios.find((x) => x.nome === m.nome && x.uf === m.uf);
    const contratos = noIca ? ica.base.atendimentos.filter((a) => a.municipio === noIca.id) : [];
    const porEstado = comCarteira[Math.floor((i * comCarteira.length) / reais.length)]!.id;
    const sorteada = sortear(pessoas).id;
    return {
      id: noIca?.id ?? 1001 + i,
      nome: m.nome,
      uf: m.uf,
      coordenador: contratos.length > 0 ? (contratos.find((a) => a.coordenador !== null)?.coordenador ?? null) : porEstado,
      gestora_referencia: noIca?.gestora_referencia ?? sorteada,
    };
  });
  const coordenadores = comCarteira.filter((c) => municipios.some((m) => m.coordenador === c.id));

  const respostas: RespostaPesquisa[] = [];
  const relatorios: RelatorioMensal[] = [];
  const ocorrencias: Ocorrencia[] = [];
  const reunioes: ReuniaoEscuta[] = [];
  const decisoes: DecisaoComite[] = [];
  const tarefas: TarefaResposta[] = [];

  const responder = (m: MunicipioSemaforo, ciclo: Ciclo, data: string, plano: Plano) => {
    const media = plano.media_pesquisa ?? 'verde';
    const nps = plano.nps ?? 'verde';
    const quantas = rng() < 0.35 ? 2 : 1;
    for (let k = 0; k < quantas; k++) {
      const itens = Array.from({ length: 6 }, (_, i) =>
        media === 'verde' ? (rng() < 0.55 ? 5 : 4) : media === 'amarelo' ? (i < 3 || rng() < 0.5 ? 3 : 4) : i < 3 || rng() < 0.5 ? 2 : 3,
      );
      respostas.push({
        id: respostas.length + 1,
        municipio: m.id,
        ciclo,
        respondida_em: data,
        no_prazo: data <= periodoDoCiclo(ciclo).prazo_pesquisa,
        funcao_respondente: FUNCOES[k]!,
        identificacao: null,
        itens,
        nps: nps === 'verde' ? inteiro(9, 10) : nps === 'amarelo' ? inteiro(7, 8) : inteiro(5, 6),
        comentario: sortear(COMENTARIOS[media === 'verde' ? nps : media]),
      });
    }
  };

  const relatar = (m: MunicipioSemaforo, plano: Plano, meses: readonly string[]) => {
    const coordenador = m.coordenador;
    if (coordenador === null) return;
    const doCiclo = meses.map((mes): Omit<RelatorioMensal, 'id'> => {
      const formacoes = inteiro(3, 4);
      const visitas = inteiro(1, 2);
      return {
        municipio: m.id,
        coordenador,
        mes,
        formacoes_previstas: formacoes,
        formacoes_realizadas: formacoes,
        visitas_previstas: visitas,
        visitas_realizadas: visitas,
      };
    });
    if (plano.cronograma === 'amarelo' && doCiclo[0]) {
      // 8 a 12 previstas no ciclo, 2 que não aconteceram: 75% a 83%.
      doCiclo[0].formacoes_realizadas -= 2;
    }
    for (const r of doCiclo) relatorios.push({ ...r, id: relatorios.length + 1 });
  };

  // 1. As coletas de cada município, ciclo a ciclo.
  for (const m of municipios) {
    const historia = PLANOS_DA_HISTORIA[`${m.nome}-${m.uf}`];
    const chanceDeAlerta = rng() < 0.7 ? 0.05 : 0.3;
    let semRespostaAntes = false;

    for (const ciclo of CICLOS_FECHADOS) {
      const { meses } = periodoDoCiclo(ciclo);
      let plano: Plano = historia?.[ciclo] ?? {};
      // Nada sorteado no penúltimo ciclo: um amarelo ali viraria outro "em recuperação" no último publicado,
      // e a história tem um só.
      if (!historia && ciclo !== CICLOS_FECHADOS.at(-2) && rng() < chanceDeAlerta) {
        // Um só amarelo por ciclo; sem resposta duas vezes seguidas daria vermelho (fica para a história).
        const opcoes = ALERTAS_SORTEAVEIS.filter((i) => !(semRespostaAntes && i === 'resposta_pesquisa'));
        plano = { [sortear(opcoes)]: 'amarelo' };
      }
      semRespostaAntes = plano.resposta_pesquisa !== undefined;

      if (!semRespostaAntes) responder(m, ciclo, dia(meses[1], inteiro(3, 18)), plano);
      relatar(m, plano, meses);
      if (plano.ocorrencias) {
        // Nos primeiros dias do ciclo: fica fora do trimestre do ciclo seguinte e do "hoje" da demonstração.
        ocorrencias.push({ id: ocorrencias.length + 1, municipio: m.id, data: dia(meses[0], inteiro(2, 6)), origem: 'fluxo_unico', tipo: 'leve' });
      }
    }

    // Ciclo atual (nov–dez/2026): relatório de novembro entregue; a pesquisa está aberta até 20/12.
    relatar(m, {}, ['2026-11']);
    const sem_resposta = `${m.nome}-${m.uf}` === chave(H.sem_resposta_dois_ciclos);
    if (!sem_resposta && rng() < 0.5) responder(m, CICLO_ATUAL_SEMAFORO, dia('2026-12', inteiro(1, 7)), {});
    if (`${m.nome}-${m.uf}` === chave(H.vermelho_prazo_hoje)) {
      ocorrencias.push({ id: ocorrencias.length + 1, municipio: m.id, data: '2026-12-01', origem: 'fluxo_unico', tipo: 'reclamacao' });
    }

    // Reuniões semestrais de escuta (março e setembro).
    for (const mes of ['2026-03', '2026-09']) {
      reunioes.push({
        id: reunioes.length + 1,
        municipio: m.id,
        data: dia(mes, inteiro(10, 26)),
        periodicidade: 'semestral',
        cronograma_confirmado: rng() < 0.9,
        encaminhamentos: sortear(ENCAMINHAMENTOS.semestral),
      });
    }
  }

  // 2. O Comitê publica cada ciclo fechado com a cor das regras (e a alteração da história).
  const coletas: ColetasSemaforo = { ciclos: [...CICLOS_FECHADOS, CICLO_ATUAL_SEMAFORO], respostas, relatorios, ocorrencias };
  for (const m of municipios) {
    const historico: CicloPublicado[] = [];
    let vigente: Cor | null = null;
    const publicar = (ciclo: Ciclo, resultado: ResultadoCor, publicada_em: string) => {
      const alterada = ALTERACAO_DO_COMITE.municipio === `${m.nome}-${m.uf}` && ALTERACAO_DO_COMITE.ciclo === ciclo;
      const decisao: DecisaoComite = {
        municipio: m.id,
        ciclo,
        cor_sugerida: resultado.cor,
        cor_publicada: alterada ? ALTERACAO_DO_COMITE.cor : resultado.cor,
        justificativa: alterada ? ALTERACAO_DO_COMITE.justificativa : null,
        publicada_em,
      };
      decisoes.push(decisao);
      for (const t of tarefasDaPublicacao(vigente, decisao)) {
        // Tudo o que venceu antes de hoje foi feito na véspera do prazo; o resto está em aberto.
        const feita = t.prazo_em < DATA_REFERENCIA_SEMAFORO;
        const vespera = somarDias(t.prazo_em, -1);
        tarefas.push({ ...t, concluida_em: feita ? (vespera < t.criada_em ? t.criada_em : vespera) : null });
      }
      if (decisao.cor_publicada !== 'verde') {
        const data = somarDias(publicada_em, 21);
        if (data <= DATA_REFERENCIA_SEMAFORO) {
          reunioes.push({
            id: reunioes.length + 1,
            municipio: m.id,
            data,
            periodicidade: 'trimestral',
            cronograma_confirmado: true,
            encaminhamentos: sortear(ENCAMINHAMENTOS.trimestral),
          });
        }
      }
      historico.push({ ciclo, limpo: resultado.limpo, cor_publicada: decisao.cor_publicada });
      vigente = decisao.cor_publicada;
    };

    for (const ciclo of CICLOS_FECHADOS) {
      publicar(ciclo, classificar(valoresDoCiclo(coletas, m.id, ciclo, periodoDoCiclo(ciclo).fim), historico), PUBLICACAO[ciclo]!);
    }
    if (`${m.nome}-${m.uf}` === chave(H.vermelho_prazo_hoje)) {
      const valores = valoresDoCiclo(coletas, m.id, CICLO_ATUAL_SEMAFORO, EXTRAORDINARIA);
      publicar(CICLO_ATUAL_SEMAFORO, classificar(valores, historico, { cicloFechado: false }), EXTRAORDINARIA);
    }
  }

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
    ocorrencias,
    reunioes,
    decisoes,
    tarefas,
  };
}
