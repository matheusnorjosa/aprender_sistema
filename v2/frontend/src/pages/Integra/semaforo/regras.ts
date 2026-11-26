/**
 * Regras do Semáforo de Risco Municipal. Funções puras: nada aqui lê a hora do relógio; a data de
 * referência sempre chega como argumento (texto AAAA-MM-DD).
 *
 * Fonte: Requisitos_Modulo_Semaforo_Risco_Municipal.pdf (NFP, nov/2026).
 * - Seção 3: os 5 indicadores e seus limites; indicador sem dado fica fora da regra do pior (sugestão).
 * - Seção 4: vale o pior; vermelho imediato; 3 amarelos valem vermelho; volta ao verde só depois de
 *   2 ciclos bimestrais seguidos sem alerta ("em recuperação"); o Comitê confirma a cor e justifica se alterar.
 * - Seção 5: tarefas e prazos por cor, contados a partir da publicação.
 * - Seção 7: ▲ piorou, ▼ melhorou desde o ciclo anterior.
 *
 * Decisões do dono de 25/11/2026 (números de `liberacao/relatorios/integra_decisoes_2026-11-24.md`):
 * - 30: a cor de média, NPS e cronograma sai do número exato (3,95 é amarelo; 89,5% é amarelo); a tela mostra
 *   2 casas, para o número que aparece ser o que deu a cor.
 * - 31: NPS é a média das notas (decisão do PDF), e a tela mostra também a maior e a menor; 8,5 é amarelo.
 * - 32: as ocorrências contam desde a 1ª formação do ano no município e zeram no ano seguinte; nada é apagado.
 * - 33 e 34: os prazos do vermelho são dias úteis, de segunda a sexta (o dono escolheu essa opção, e não a que
 *   descontava os feriados: feriado em dia de semana conta como dia útil): contato em 2, Secretaria em 5, plano em
 *   15, devolutiva em 30. 35: "no bimestre" e "no semestre" são 2 e 6 meses depois da publicação (no sábado ou no
 *   domingo, vale a segunda-feira seguinte; leitura em Para validar).
 * - 38 e 39: um vermelho ou três amarelos mudam a cor na hora (`vermelho_imediato`).
 * - 42 e 43: tarefa cancelada pelo Comitê ou substituída fica guardada com o estado.
 * - 48: ata da reunião de escuta até 5 dias úteis depois. 49: convergência. 50: tempo de resposta (meta 48 h).
 */
import { formatarDia, formatarNumero } from '../ica/componentes/estilos';
import type {
  AvaliacaoIndicador,
  ChaveTarefa,
  CicloPublicado,
  Cor,
  CorIndicador,
  EstadoTarefa,
  Indicador,
  ModeloTarefa,
  Mudanca,
  Ocorrencia,
  OrigemOcorrencia,
  Prazo,
  RelatorioMensal,
  RespostaPesquisa,
  ResultadoCor,
  TarefaResposta,
  ValoresIndicadores,
} from './tipos';

export const INDICADORES: readonly Indicador[] = ['media_pesquisa', 'nps', 'cronograma', 'ocorrencias', 'resposta_pesquisa'];

export const ROTULO_INDICADOR: Record<Indicador, string> = {
  media_pesquisa: 'Média da pesquisa do articulador',
  nps: 'Nota NPS do articulador',
  cronograma: 'Cronograma cumprido',
  ocorrencias: 'Ocorrências via Relacionamento ou distribuidor',
  resposta_pesquisa: 'Resposta à pesquisa',
};

/** Por onde a ocorrência chegou: o mesmo nome no formulário e na ficha do município. */
export const ROTULO_ORIGEM: Record<OrigemOcorrencia, string> = {
  fluxo_unico: 'Relacionamento, Comercial ou distribuidor',
  reuniao_escuta: 'Reunião de escuta (na conversa aberta)',
  momento_reservado: 'Momento reservado (confidencial)',
};

export const ROTULO_COR: Record<CorIndicador, string> = {
  verde: 'Verde',
  amarelo: 'Amarelo',
  vermelho: 'Vermelho',
  sem_dado: 'Sem dado',
};

/**
 * Os limites da seção 3 do PDF, para a tela mostrar a régua de cada indicador. Escritos sem buraco entre as
 * faixas, porque a cor sai do número exato (decisão 30): 3,95 fica em "3,0 a menos de 4,0".
 */
export const LIMITES: Record<Indicador, Record<Cor, string>> = {
  media_pesquisa: { verde: '4,0 ou mais', amarelo: '3,0 a menos de 4,0', vermelho: 'menos de 3,0' },
  nps: { verde: 'média 9,0 ou mais', amarelo: 'média de 7,0 a menos de 9,0', vermelho: 'média menos de 7,0' },
  cronograma: { verde: '90% ou mais', amarelo: '70% a menos de 90%', vermelho: 'menos de 70%' },
  ocorrencias: {
    verde: 'Nenhuma',
    amarelo: 'Uma ocorrência leve',
    vermelho: 'Reclamação sobre o coordenador ou os projetos, ou duas ou mais ocorrências',
  },
  resposta_pesquisa: {
    verde: 'Respondeu no prazo',
    amarelo: 'Não respondeu em um ciclo',
    vermelho: 'Não respondeu em dois ciclos seguidos',
  },
};

/** Ciclos bimestrais seguidos sem alerta para voltar ao verde. */
export const CICLOS_PARA_VOLTAR_AO_VERDE = 2;

/** O número com 2 casas, como a tela mostra a média, o NPS e o cronograma ("3,95"). Decisão 30. */
export function duasCasas(valor: number): string {
  return formatarNumero(valor, 2);
}

function media(numeros: readonly number[]): number | null {
  return numeros.length === 0 ? null : numeros.reduce((s, n) => s + n, 0) / numeros.length;
}

/** "a", "a e b", "a, b e c". */
export function lista(itens: readonly string[]): string {
  return itens.length <= 1 ? (itens[0] ?? '') : `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
}

// ---------------------------------------------------------------- seção 3: cor de cada indicador

// Decisão 30: as três cores abaixo saem do número exato, sem arredondar.

export function corMediaPesquisa(valor: number | null): CorIndicador {
  if (valor === null) return 'sem_dado';
  return valor >= 4 ? 'verde' : valor >= 3 ? 'amarelo' : 'vermelho';
}

export function corNps(valor: number | null): CorIndicador {
  if (valor === null) return 'sem_dado';
  return valor >= 9 ? 'verde' : valor >= 7 ? 'amarelo' : 'vermelho';
}

export function corCronograma(percentual: number | null): CorIndicador {
  if (percentual === null) return 'sem_dado';
  return percentual >= 90 ? 'verde' : percentual >= 70 ? 'amarelo' : 'vermelho';
}

/** Ocorrência é contínua: nenhuma no ano é um dado (verde), nunca "sem dado". */
export function corOcorrencias({ leves, reclamacoes }: ValoresIndicadores['ocorrencias']): Cor {
  if (reclamacoes > 0 || leves >= 2) return 'vermelho';
  return leves === 1 ? 'amarelo' : 'verde';
}

export function corRespostaPesquisa({ ciclo_atual, ciclo_anterior }: ValoresIndicadores['resposta_pesquisa']): CorIndicador {
  if (ciclo_atual === null) return 'sem_dado';
  if (ciclo_atual) return 'verde';
  return ciclo_anterior === false ? 'vermelho' : 'amarelo';
}

// ---------------------------------------------------------------- seção 3: valores a partir das coletas

/** Média dos 6 itens de todas as respostas do município no ciclo; sem resposta, sem dado. */
export function mediaDaPesquisa(respostas: readonly RespostaPesquisa[]): number | null {
  return media(respostas.flatMap((r) => r.itens));
}

/** Média das notas NPS do ciclo (o PDF adota a média, não o NPS clássico de promotores − detratores). */
export function mediaNps(respostas: readonly RespostaPesquisa[]): number | null {
  return media(respostas.map((r) => r.nps));
}

export interface ResumoNps {
  maior: number;
  menor: number;
  /** A média, que dá a cor. */
  media: number;
}

/** Decisão 31: a maior nota, a menor e a média do ciclo; sem resposta, `null`. */
export function resumoNps(respostas: readonly RespostaPesquisa[]): ResumoNps | null {
  const notas = respostas.map((r) => r.nps);
  const m = media(notas);
  return m === null ? null : { maior: Math.max(...notas), menor: Math.min(...notas), media: m };
}

/** "Maior 9, menor 8, média 8,50". */
export function textoResumoNps({ maior, menor, media: m }: ResumoNps): string {
  return `Maior ${maior}, menor ${menor}, média ${duasCasas(m)}`;
}

/**
 * O projeto respondeu quando houve ao menos uma resposta dele no prazo; o município vale o pior projeto (decisão 51,
 * em `valoresDoCiclo`). Com o prazo ainda aberto e nenhuma resposta no prazo, ainda não se sabe: `null` (sem dado).
 */
export function respondeuNoPrazo(respostas: readonly RespostaPesquisa[], prazoEncerrado: boolean): boolean | null {
  if (respostas.some((r) => r.no_prazo)) return true;
  return prazoEncerrado ? false : null;
}

/** Formações e visitas realizadas ÷ previstas, em %. Nada previsto no período = sem dado. */
export function percentualCronograma(relatorios: readonly RelatorioMensal[]): number | null {
  let previstas = 0;
  let realizadas = 0;
  for (const r of relatorios) {
    previstas += r.formacoes_previstas + r.visitas_previstas;
    realizadas += r.formacoes_realizadas + r.visitas_realizadas;
  }
  return previstas === 0 ? null : (realizadas / previstas) * 100;
}

/**
 * O primeiro dia do mês da 1ª formação realizada no ano, pelos relatórios mensais do município (o relatório é
 * mensal, sem o dia da formação); `null` = nenhuma formação no ano.
 */
export function inicioDasFormacoesNoAno(relatorios: readonly RelatorioMensal[], ano: number): string | null {
  const meses = relatorios
    .filter((r) => r.mes.startsWith(`${ano}-`) && r.formacoes_realizadas > 0)
    .map((r) => r.mes)
    .sort();
  return meses.length === 0 ? null : `${meses[0]}-01`;
}

/**
 * Decisão 32: as ocorrências que contam na data de referência são as do ano dela, desde a 1ª formação do ano no
 * município (`relatorios` são os do município) até a data (inclusive). Em janeiro a contagem zera; antes da 1ª
 * formação do ano, nada conta. Decisão 57: só filtra, nada é apagado (o histórico continua na lista).
 */
export function ocorrenciasDoAno(
  ocorrencias: readonly Ocorrencia[],
  relatorios: readonly RelatorioMensal[],
  dataReferencia: string,
): Ocorrencia[] {
  const inicio = inicioDasFormacoesNoAno(relatorios, Number(dataReferencia.slice(0, 4)));
  if (inicio === null) return [];
  return ocorrencias.filter((o) => o.data >= inicio && o.data <= dataReferencia);
}

/**
 * Decisão 32: as ocorrências do ano da data de referência (até ela) que não contam na cor, por serem de antes da 1ª
 * formação do ano no município, ou porque ainda não houve formação no ano. Ficam guardadas (decisão 57).
 */
export function ocorrenciasForaDaContagem(
  ocorrencias: readonly Ocorrencia[],
  relatorios: readonly RelatorioMensal[],
  dataReferencia: string,
): Ocorrencia[] {
  const contam = new Set(ocorrenciasDoAno(ocorrencias, relatorios, dataReferencia));
  const ano = dataReferencia.slice(0, 4);
  return ocorrencias.filter((o) => o.data.startsWith(`${ano}-`) && o.data <= dataReferencia && !contam.has(o));
}

export function contarOcorrencias(ocorrencias: readonly Ocorrencia[]): ValoresIndicadores['ocorrencias'] {
  const reclamacoes = ocorrencias.filter((o) => o.tipo === 'reclamacao').length;
  return { leves: ocorrencias.length - reclamacoes, reclamacoes };
}

// ---------------------------------------------------------------- seção 3: os 5 indicadores juntos

function textoOcorrencias({ leves, reclamacoes, fora_da_contagem = 0 }: ValoresIndicadores['ocorrencias']): string {
  const partes: string[] = [];
  if (reclamacoes > 0) partes.push(`${reclamacoes} ${reclamacoes === 1 ? 'reclamação' : 'reclamações'}`);
  if (leves > 0) partes.push(`${leves} ${leves === 1 ? 'leve' : 'leves'}`);
  if (partes.length > 0) return lista(partes);
  // "Nenhuma" sozinho esconderia a ocorrência guardada que não conta (decisão 32: antes da 1ª formação do ano).
  if (fora_da_contagem === 0) return 'Nenhuma';
  return `Nenhuma que conte (${fora_da_contagem} ${fora_da_contagem === 1 ? 'registrada' : 'registradas'} antes da 1ª formação do ano)`;
}

function textoResposta({ ciclo_atual, ciclo_anterior }: ValoresIndicadores['resposta_pesquisa']): string {
  if (ciclo_atual === null) return 'Sem dado';
  if (ciclo_atual) return 'Respondeu no prazo';
  return ciclo_anterior === false ? 'Não respondeu em dois ciclos seguidos' : 'Não respondeu neste ciclo';
}

/** Os 5 indicadores, na ordem do PDF, com a cor e o valor escrito para a tela. */
export function avaliarIndicadores(v: ValoresIndicadores): AvaliacaoIndicador[] {
  return [
    {
      indicador: 'media_pesquisa',
      cor: corMediaPesquisa(v.media_pesquisa),
      texto: v.media_pesquisa === null ? 'Sem dado' : duasCasas(v.media_pesquisa),
    },
    { indicador: 'nps', cor: corNps(v.nps), texto: v.nps === null ? 'Sem dado' : duasCasas(v.nps) },
    {
      indicador: 'cronograma',
      cor: corCronograma(v.cronograma),
      texto: v.cronograma === null ? 'Sem dado' : `${duasCasas(v.cronograma)}%`,
    },
    { indicador: 'ocorrencias', cor: corOcorrencias(v.ocorrencias), texto: textoOcorrencias(v.ocorrencias) },
    {
      indicador: 'resposta_pesquisa',
      cor: corRespostaPesquisa(v.resposta_pesquisa),
      texto: textoResposta(v.resposta_pesquisa),
    },
  ];
}

// ---------------------------------------------------------------- seção 4: a cor do município

/**
 * A cor sugerida do ciclo. `historico` são os ciclos já publicados, seguidos, do mais antigo para o último.
 *
 * Ordem das regras: um vermelho → vermelho (imediato); 3 ou mais amarelos → vermelho; algum amarelo →
 * amarelo; ciclo limpo depois de amarelo ou vermelho publicado → amarelo "em recuperação" até somar
 * 2 ciclos limpos seguidos; senão, verde. Indicador sem dado não conta em nenhuma regra.
 *
 * "Vermelho imediato": esta função vale a qualquer momento do ciclo, não só no fim; a tela chama de novo
 * quando chega um dado, e `vermelho_imediato` diz que a cor mudou por um indicador em vermelho (decisão 38) ou
 * por três amarelos (decisão 39). A cor oficial muda na hora (`aplicarVermelhoAutomatico`, em `dados.ts`).
 *
 * Ciclo em andamento (`cicloFechado: false`): a cor só muda na hora para piorar (um vermelho, ou um amarelo
 * sobre verde publicado); o ciclo ainda não conta como ciclo sem alerta (a pesquisa pode nem ter fechado).
 * Sem alerta, ou com amarelo sobre vermelho publicado, continua a cor publicada.
 */
export function classificar(
  valores: ValoresIndicadores,
  historico: readonly CicloPublicado[],
  { cicloFechado = true }: { cicloFechado?: boolean } = {},
): ResultadoCor {
  const avaliacoes = avaliarIndicadores(valores);
  const com = (cor: CorIndicador) => avaliacoes.filter((a) => a.cor === cor).map((a) => a.indicador);
  const vermelhos = com('vermelho');
  const amarelos = com('amarelo');
  const limpo = vermelhos.length === 0 && amarelos.length === 0;

  let ciclos_limpos = 0;
  if (limpo) {
    ciclos_limpos = cicloFechado ? 1 : 0;
    for (let i = historico.length - 1; i >= 0 && historico[i]!.limpo; i--) ciclos_limpos++;
  }

  const vermelho_imediato = vermelhos.length > 0 || amarelos.length >= 3;
  const base = { avaliacoes, sem_dado: com('sem_dado'), limpo, ciclos_limpos, vermelho_imediato };
  if (vermelhos.length > 0) {
    return { ...base, cor: 'vermelho', motivo: 'indicador_vermelho', decisivos: vermelhos, em_recuperacao: false };
  }
  if (amarelos.length >= 3) {
    return { ...base, cor: 'vermelho', motivo: 'tres_amarelos', decisivos: amarelos, em_recuperacao: false };
  }
  const anterior = historico[historico.length - 1]?.cor_publicada;
  if (amarelos.length > 0) {
    // No meio do ciclo a cor só muda para piorar: sair do vermelho espera o ciclo fechar.
    if (!cicloFechado && anterior === 'vermelho') {
      return { ...base, cor: 'vermelho', motivo: 'ciclo_em_andamento', decisivos: amarelos, em_recuperacao: false };
    }
    return { ...base, cor: 'amarelo', motivo: 'pior_indicador', decisivos: amarelos, em_recuperacao: false };
  }
  if (!cicloFechado && anterior !== undefined && anterior !== 'verde') {
    const em_recuperacao = anterior === 'amarelo' && ciclos_limpos > 0;
    return { ...base, cor: anterior, motivo: 'ciclo_em_andamento', decisivos: [], em_recuperacao };
  }
  if (anterior !== undefined && anterior !== 'verde' && ciclos_limpos < CICLOS_PARA_VOLTAR_AO_VERDE) {
    return { ...base, cor: 'amarelo', motivo: 'em_recuperacao', decisivos: [], em_recuperacao: true };
  }
  return { ...base, cor: 'verde', motivo: 'sem_alerta', decisivos: [], em_recuperacao: false };
}

/** Por que a cor, em uma frase para a tela. */
export function explicarCor(r: ResultadoCor): string {
  const nomes = lista(r.decisivos.map((i) => ROTULO_INDICADOR[i]));
  switch (r.motivo) {
    case 'indicador_vermelho':
      return `Vermelho: ${nomes} em vermelho.`;
    case 'tres_amarelos':
      return `Vermelho: ${r.decisivos.length} indicadores em amarelo no mesmo ciclo (${nomes}).`;
    case 'pior_indicador':
      return `Amarelo: ${nomes} em amarelo.`;
    case 'em_recuperacao':
      return `Amarelo, em recuperação: ${r.ciclos_limpos} de ${CICLOS_PARA_VOLTAR_AO_VERDE} ciclos sem alerta para voltar ao verde.`;
    case 'ciclo_em_andamento': {
      const fecho = 'O ciclo em andamento só conta quando fechar.';
      if (r.em_recuperacao) {
        return `Amarelo, em recuperação: ${r.ciclos_limpos} de ${CICLOS_PARA_VOLTAR_AO_VERDE} ciclos sem alerta para voltar ao verde. ${fecho}`;
      }
      const motivo = r.decisivos.length > 0 ? ` (${nomes} em amarelo)` : '';
      return `${ROTULO_COR[r.cor]}: continua a cor publicada${motivo}. ${fecho}`;
    }
    case 'sem_alerta':
      return 'Verde: nenhum indicador em amarelo ou vermelho.';
  }
}

/** O aviso dos indicadores que ficaram fora da regra; `null` quando todos têm dado. */
export function textoSemDado(r: ResultadoCor): string | null {
  if (r.sem_dado.length === 0) return null;
  return `Sem dado neste ciclo, fora da regra: ${lista(r.sem_dado.map((i) => ROTULO_INDICADOR[i]))}.`;
}

/** O Comitê confirma a cor sugerida ou a altera; alterar exige justificativa (seção 4, "Atualização"). */
export function validarDecisao(
  sugerida: Cor,
  confirmada: Cor,
  justificativa: string | null,
): { valida: boolean; alterada: boolean; erros: string[] } {
  const alterada = sugerida !== confirmada;
  const erros =
    alterada && !justificativa?.trim()
      ? [`A cor é diferente da sugerida (${ROTULO_COR[sugerida]}). Escreva a justificativa do Comitê.`]
      : [];
  return { valida: erros.length === 0, alterada, erros };
}

const GRAVIDADE: Record<Cor, number> = { verde: 0, amarelo: 1, vermelho: 2 };

/** Mudança da cor publicada desde o ciclo anterior (seção 7: ▲ piorou, ▼ melhorou), com o texto escrito. */
export function mudancaEntreCiclos(
  anterior: Cor | null,
  atual: Cor,
): { mudanca: Mudanca; seta: '▲' | '▼' | ''; texto: string } {
  if (anterior === null) return { mudanca: 'sem_anterior', seta: '', texto: 'Primeiro ciclo' };
  const diferenca = GRAVIDADE[atual] - GRAVIDADE[anterior];
  if (diferenca > 0) return { mudanca: 'piorou', seta: '▲', texto: `Piorou: era ${anterior}` };
  if (diferenca < 0) return { mudanca: 'melhorou', seta: '▼', texto: `Melhorou: era ${anterior}` };
  return { mudanca: 'igual', seta: '', texto: 'Sem mudança' };
}

/**
 * O ciclo conta como "sem alerta" para a volta ao verde (decisão 45, contada da cor publicada): os dados não têm
 * alerta e o Comitê não publicou uma cor pior que a sugerida. Com o vermelho ou o amarelo publicado sobre dados
 * limpos, a contagem começa no ciclo seguinte.
 */
export function cicloSemAlerta(resultado: ResultadoCor, publicada: Cor): boolean {
  return resultado.limpo && piorCor(publicada, resultado.cor) === resultado.cor;
}

// ---------------------------------------------------------------- seção 5: resposta a cada cor

export interface RespostaDaCor {
  quem_age: string;
  o_que_fazer: string;
  /** Tarefas com prazo, criadas quando a cor é publicada. */
  tarefas: readonly ModeloTarefa[];
  /** O que passa a se repetir (sem prazo único). */
  rotina: readonly string[];
}

function tarefa(chave: ChaveTarefa, titulo: string, prazo: Prazo, prazo_texto: string): ModeloTarefa {
  return { chave, titulo, prazo, prazo_texto };
}

export const RESPOSTA_POR_COR: Record<Cor, RespostaDaCor> = {
  verde: {
    quem_age: 'Gestora de referência',
    o_que_fazer: 'Manter a reunião semestral de escuta e a pesquisa bimestral',
    tarefas: [],
    rotina: ['Pesquisa a cada 2 meses', 'Reunião de escuta a cada 6 meses'],
  },
  amarelo: {
    quem_age: 'Gestora de referência e coordenador(es)',
    o_que_fazer: 'Conversar com o articulador, observar uma formação e acompanhar o caso no Comitê',
    tarefas: [
      tarefa('contato_articulador', 'Contato com o articulador', { tipo: 'dias_uteis', valor: 10 }, 'em até 10 dias úteis'),
      tarefa('observacao_formacao', 'Observação de uma formação', { tipo: 'meses', valor: 2 }, 'no bimestre'),
    ],
    rotina: ['Reunião de escuta a cada 3 meses'],
  },
  vermelho: {
    quem_age: 'Gestora de referência e gestora pedagógica',
    // Rodada 3: na ordem das tarefas, começando pelo contato com o articulador municipal (decisões 34 e 37).
    o_que_fazer:
      'Contato com o articulador municipal em 2 dias úteis, reunião com a Secretaria, plano de ação pactuado, devolutiva, visita técnica no semestre, reunião de escuta trimestral e acompanhamento até a saída do vermelho',
    // Decisões 33 e 34: dias úteis; o "contato em 48 h" do PDF vira 2 dias úteis, com o articulador (decisão 37).
    // A chave `contato_48h` é o nome interno de antes; só o texto mudou.
    tarefas: [
      tarefa('contato_48h', 'Contato com o articulador municipal', { tipo: 'dias_uteis', valor: 2 }, 'em 2 dias úteis'),
      tarefa('reuniao_secretaria', 'Reunião com a Secretaria', { tipo: 'dias_uteis', valor: 5 }, 'em 5 dias úteis'),
      tarefa('plano_acao', 'Plano de ação pactuado', { tipo: 'dias_uteis', valor: 15 }, 'em 15 dias úteis'),
      tarefa('devolutiva', 'Devolutiva', { tipo: 'dias_uteis', valor: 30 }, 'em 30 dias úteis'),
      tarefa('visita_tecnica', 'Visita técnica', { tipo: 'meses', valor: 6 }, 'no semestre'),
    ],
    rotina: ['Acompanhamento a cada 15 dias', 'Reunião de escuta a cada 3 meses'],
  },
};

/** Meses entre as reuniões de escuta (seção 5): a cada 6 no verde, a cada 3 no amarelo e no vermelho. */
export const MESES_ENTRE_REUNIOES: Record<Cor, number> = { verde: 6, amarelo: 3, vermelho: 3 };

/** Houve reunião de escuta dentro do período da cor, contado para trás a partir da data de referência. */
export function reuniaoEmDia(datas: readonly string[], cor: Cor, dataReferencia: string): boolean {
  const inicio = somarMeses(dataReferencia, -MESES_ENTRE_REUNIOES[cor]);
  return datas.some((d) => d > inicio && d <= dataReferencia);
}

// As contas de data usam só o dia (AAAA-MM-DD) em UTC: sem hora, o fuso do navegador não muda o resultado.
function paraData(texto: string): Date {
  const [ano, mes, dia] = texto.split('-').map(Number);
  return new Date(Date.UTC(ano!, mes! - 1, dia));
}

function paraTexto(data: Date): string {
  return data.toISOString().slice(0, 10);
}

export function somarDias(data: string, dias: number): string {
  const d = paraData(data);
  d.setUTCDate(d.getUTCDate() + dias);
  return paraTexto(d);
}

/**
 * Dias úteis de segunda a sexta; o dia da publicação não conta. O feriado em dia de semana conta como dia útil:
 * decisão 33, o dono escolheu dias úteis de segunda a sexta, e não a opção que descontava os feriados.
 */
export function somarDiasUteis(data: string, dias: number): string {
  const d = paraData(data);
  let faltam = dias;
  while (faltam > 0) {
    d.setUTCDate(d.getUTCDate() + 1);
    const semana = d.getUTCDay();
    if (semana !== 0 && semana !== 6) faltam--;
  }
  return paraTexto(d);
}

/** O próprio dia, se for de segunda a sexta; senão, a segunda-feira seguinte. */
export function emDiaUtil(data: string): string {
  return somarDiasUteis(somarDias(data, -1), 1);
}

/** Soma meses; o dia que não existe no mês de chegada vira o último dia dele (31/12 + 2 meses = 28/02). */
export function somarMeses(data: string, meses: number): string {
  const [ano, mes, dia] = data.split('-').map(Number);
  const ultimoDia = new Date(Date.UTC(ano!, mes! - 1 + meses + 1, 0)).getUTCDate();
  return paraTexto(new Date(Date.UTC(ano!, mes! - 1 + meses, Math.min(dia!, ultimoDia))));
}

function prazoEm(prazo: Prazo, publicadaEm: string): string {
  switch (prazo.tipo) {
    case 'dias_uteis':
      return somarDiasUteis(publicadaEm, prazo.valor);
    case 'meses':
      // Rodada 3 (leitura em Para validar): como os outros prazos são em dias úteis (decisão 33), o prazo em meses
      // que cai no sábado ou no domingo passa para a segunda-feira (30/11/2026 + 6 meses = segunda, 31/05/2027).
      return emDiaUtil(somarMeses(publicadaEm, prazo.valor));
  }
}

/**
 * As tarefas da resposta à cor publicada, com prazo contado a partir da data de publicação. Os ids começam em
 * `primeiroId` (quem guarda a lista passa o próximo id livre).
 */
export function criarTarefas(cor: Cor, municipio: number, publicadaEm: string, primeiroId = 1): TarefaResposta[] {
  return RESPOSTA_POR_COR[cor].tarefas.map((t, i) => ({
    id: primeiroId + i,
    chave: t.chave,
    titulo: t.titulo,
    municipio,
    cor,
    criada_em: publicadaEm,
    prazo_em: prazoEm(t.prazo, publicadaEm),
    concluida_em: null,
    encerramento: null,
  }));
}

/**
 * Situação da tarefa na data de referência: no prazo, vence hoje, vencida, concluída, ou o motivo de ter deixado
 * de valer (cancelada pelo Comitê, substituída). A feita continua feita mesmo depois (decisão 42).
 */
export function estadoDaTarefa(t: TarefaResposta, dataReferencia: string): EstadoTarefa {
  if (t.concluida_em !== null) return 'concluida';
  if (t.encerramento !== null) return t.encerramento.motivo;
  if (dataReferencia < t.prazo_em) return 'no_prazo';
  return dataReferencia === t.prazo_em ? 'vence_hoje' : 'vencida';
}

/** A tarefa ainda está para fazer: nem concluída, nem cancelada, nem substituída. */
export function tarefaAberta(t: TarefaResposta): boolean {
  return t.concluida_em === null && t.encerramento === null;
}

// ---------------------------------------------------------------- decisão 48: a ata da reunião de escuta

/** Dias úteis para registrar a ata depois da reunião. */
export const DIAS_UTEIS_PARA_A_ATA = 5;

export type SituacaoReuniao = 'agendada' | 'ata_a_registrar' | 'ata_atrasada' | 'realizada';

/** A reunião de escuta é semestral no verde e trimestral no amarelo e no vermelho (seção 5 do PDF). */
export function periodicidadeDaCor(cor: Cor): 'semestral' | 'trimestral' {
  return cor === 'verde' ? 'semestral' : 'trimestral';
}

/** Rodada 5: uma reunião de escuta por vez; a seguinte fica a 30 dias ou mais (leitura em Para validar). */
export const DIAS_ENTRE_REUNIOES = 30;

/** O último dia para registrar a ata: 5 dias úteis depois da reunião. */
export function prazoDaAta(dataReuniao: string): string {
  return somarDiasUteis(dataReuniao, DIAS_UTEIS_PARA_A_ATA);
}

/**
 * A reunião é marcada antes e a ata registrada depois: com a ata, realizada; antes do dia, agendada; do dia da
 * reunião até o prazo, ata a registrar; passado o prazo sem ata, ata atrasada.
 */
export function situacaoDaReuniao(reuniao: { data: string; ata_em: string | null }, hoje: string): SituacaoReuniao {
  if (reuniao.ata_em !== null) return 'realizada';
  if (hoje < reuniao.data) return 'agendada';
  return hoje <= prazoDaAta(reuniao.data) ? 'ata_a_registrar' : 'ata_atrasada';
}

/** A situação da reunião escrita para a tela, com o prazo da ata ("Ata a registrar até 04/12/2026"). */
export function textoDaReuniao(reuniao: { data: string; ata_em: string | null }, hoje: string): string {
  const prazo = formatarDia(prazoDaAta(reuniao.data));
  switch (situacaoDaReuniao(reuniao, hoje)) {
    case 'agendada':
      return 'Agendada';
    case 'ata_a_registrar':
      return `Ata a registrar até ${prazo}`;
    case 'ata_atrasada':
      return `Ata atrasada: o prazo era ${prazo}`;
    case 'realizada':
      return `Ata registrada em ${formatarDia(reuniao.ata_em ?? '')}`;
  }
}

// ---------------------------------------------------------------- decisão 50: o tempo de resposta às ocorrências

/** Meta de resposta à ocorrência, em horas. */
export const META_RESPOSTA_HORAS = 48;

/** Horas entre duas datas com hora e fuso (AAAA-MM-DDTHH:MM:SS-03:00). */
export function horasEntre(inicio: string, fim: string): number {
  return (Date.parse(fim) - Date.parse(inicio)) / 3_600_000;
}

export interface TempoDeResposta {
  /** Média das horas das ocorrências respondidas; `null` = nenhuma respondida. */
  media_horas: number | null;
  respondidas: number;
  sem_resposta: number;
  /** Respondidas em até 48 h. */
  dentro_da_meta: number;
  fora_da_meta: number;
}

/** As horas para a tela, com o minuto arredondado: "54 h", "2 h 30 min". */
export function textoHoras(horas: number): string {
  const minutos = Math.round(horas * 60);
  const resto = minutos % 60;
  return resto === 0 ? `${minutos / 60} h` : `${Math.floor(minutos / 60)} h ${resto} min`;
}

/** "2026-11-30T10:15:00-03:00" → "30/11/2026 às 10:15" (a hora gravada já é a de Fortaleza). */
export function textoDataHora(dataHora: string): string {
  return `${formatarDia(dataHora.slice(0, 10))} às ${dataHora.slice(11, 16)}`;
}

export function tempoDeResposta(ocorrencias: readonly Ocorrencia[]): TempoDeResposta {
  const horas = ocorrencias.flatMap((o) => (o.respondida_em === null ? [] : [horasEntre(o.registrada_em, o.respondida_em)]));
  const dentro = horas.filter((h) => h <= META_RESPOSTA_HORAS).length;
  return {
    media_horas: media(horas),
    respondidas: horas.length,
    sem_resposta: ocorrencias.length - horas.length,
    dentro_da_meta: dentro,
    fora_da_meta: horas.length - dentro,
  };
}

// ---------------------------------------------------------------- decisão 49: pesquisa × ocorrências

const GRAVIDADE_INDICADOR: Record<CorIndicador, number> = { sem_dado: -1, ...GRAVIDADE };

/** A pior de duas cores; "sem dado" perde para qualquer cor. */
export function piorCor(a: CorIndicador, b: CorIndicador): CorIndicador {
  return GRAVIDADE_INDICADOR[b] > GRAVIDADE_INDICADOR[a] ? b : a;
}

/** A cor da pesquisa: a pior entre a média e o NPS ("sem dado" só quando os dois não têm dado). */
export function corDaPesquisa(media: CorIndicador, nps: CorIndicador): CorIndicador {
  return piorCor(media, nps);
}

/** Pesquisa e ocorrências divergem quando uma está verde e a outra vermelha. */
export function divergem(pesquisa: Cor, ocorrencias: Cor): boolean {
  return (pesquisa === 'verde' && ocorrencias === 'vermelho') || (pesquisa === 'vermelho' && ocorrencias === 'verde');
}
