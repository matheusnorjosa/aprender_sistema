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
 * Leituras escolhidas onde o PDF não fecha a conta (para validar no dia 7):
 * - A cor de média, NPS e cronograma sai do número exibido (média e NPS com uma casa, cronograma em % inteiro),
 *   como no ICA. Assim a tabela do PDF não tem buraco: 3,95 aparece "4,0" e é verde; 89,5% aparece "90%".
 * - NPS é a média das notas (decisão do PDF); a média com casa decimal fica na faixa de baixo até chegar à
 *   nota de cima: 8,5 é amarelo, 6,9 é vermelho.
 * - "Ocorrências no trimestre" = os 3 meses corridos até a data de referência.
 * - Prazos: "48 h" vira 2 dias de calendário; "5, 15, 30 dias" são dias corridos; "10 dias úteis" contam de
 *   segunda a sexta, sem feriados; "no bimestre" e "no semestre" são 2 e 6 meses depois da publicação.
 */
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

/** Os limites como o PDF escreve (seção 3), para a tela mostrar a régua de cada indicador. */
export const LIMITES: Record<Indicador, Record<Cor, string>> = {
  media_pesquisa: { verde: '4,0 ou mais', amarelo: '3,0 a 3,9', vermelho: 'abaixo de 3,0' },
  nps: { verde: '9 ou 10', amarelo: '7 ou 8', vermelho: '0 a 6' },
  cronograma: { verde: '90% ou mais', amarelo: '70% a 89%', vermelho: 'abaixo de 70%' },
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

/** Arredonda (meio para cima) sem cair no ruído do ponto flutuante. */
function arredondar(valor: number, casas: number): number {
  const fator = 10 ** casas;
  return Math.round(Number((valor * fator).toFixed(6))) / fator;
}

/** O número com uma casa, como a tela mostra a média e o NPS ("4,5"). */
export function umaCasa(valor: number): string {
  return arredondar(valor, 1).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function media(numeros: readonly number[]): number | null {
  return numeros.length === 0 ? null : numeros.reduce((s, n) => s + n, 0) / numeros.length;
}

/** "a", "a e b", "a, b e c". */
export function lista(itens: readonly string[]): string {
  return itens.length <= 1 ? (itens[0] ?? '') : `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
}

// ---------------------------------------------------------------- seção 3: cor de cada indicador

export function corMediaPesquisa(valor: number | null): CorIndicador {
  if (valor === null) return 'sem_dado';
  const exibido = arredondar(valor, 1);
  return exibido >= 4 ? 'verde' : exibido >= 3 ? 'amarelo' : 'vermelho';
}

export function corNps(valor: number | null): CorIndicador {
  if (valor === null) return 'sem_dado';
  const exibido = arredondar(valor, 1);
  return exibido >= 9 ? 'verde' : exibido >= 7 ? 'amarelo' : 'vermelho';
}

export function corCronograma(percentual: number | null): CorIndicador {
  if (percentual === null) return 'sem_dado';
  const exibido = arredondar(percentual, 0);
  return exibido >= 90 ? 'verde' : exibido >= 70 ? 'amarelo' : 'vermelho';
}

/** Ocorrência é contínua: nenhuma no trimestre é um dado (verde), nunca "sem dado". */
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

/**
 * O município "respondeu" quando ao menos um articulador respondeu no prazo (sugestão do PDF).
 * Com o prazo ainda aberto e ninguém no prazo, ainda não se sabe: `null` (sem dado).
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

/** As ocorrências dos 3 meses corridos até a data de referência (inclusive). */
export function ocorrenciasNoTrimestre(ocorrencias: readonly Ocorrencia[], dataReferencia: string): Ocorrencia[] {
  const inicio = somarMeses(dataReferencia, -3);
  return ocorrencias.filter((o) => o.data > inicio && o.data <= dataReferencia);
}

export function contarOcorrencias(ocorrencias: readonly Ocorrencia[]): ValoresIndicadores['ocorrencias'] {
  const reclamacoes = ocorrencias.filter((o) => o.tipo === 'reclamacao').length;
  return { leves: ocorrencias.length - reclamacoes, reclamacoes };
}

// ---------------------------------------------------------------- seção 3: os 5 indicadores juntos

function textoOcorrencias({ leves, reclamacoes }: ValoresIndicadores['ocorrencias']): string {
  const partes: string[] = [];
  if (reclamacoes > 0) partes.push(`${reclamacoes} ${reclamacoes === 1 ? 'reclamação' : 'reclamações'}`);
  if (leves > 0) partes.push(`${leves} ${leves === 1 ? 'leve' : 'leves'}`);
  return partes.length === 0 ? 'Nenhuma' : lista(partes);
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
      texto: v.media_pesquisa === null ? 'Sem dado' : umaCasa(v.media_pesquisa),
    },
    { indicador: 'nps', cor: corNps(v.nps), texto: v.nps === null ? 'Sem dado' : umaCasa(v.nps) },
    {
      indicador: 'cronograma',
      cor: corCronograma(v.cronograma),
      texto: v.cronograma === null ? 'Sem dado' : `${arredondar(v.cronograma, 0)}%`,
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
 * quando chega um dado, e `vermelho_imediato` diz que a cor mudou por um indicador em vermelho.
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

  const base = { avaliacoes, sem_dado: com('sem_dado'), limpo, ciclos_limpos, vermelho_imediato: vermelhos.length > 0 };
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
    o_que_fazer:
      'Reunião com a Secretaria, visita técnica, plano de ação pactuado, reunião de escuta trimestral e acompanhamento até a saída do vermelho',
    tarefas: [
      tarefa('contato_48h', 'Contato com o município', { tipo: 'horas', valor: 48 }, 'em 48 h'),
      tarefa('reuniao_secretaria', 'Reunião com a Secretaria', { tipo: 'dias', valor: 5 }, 'em 5 dias'),
      tarefa('plano_acao', 'Plano de ação pactuado', { tipo: 'dias', valor: 15 }, 'em 15 dias'),
      tarefa('devolutiva', 'Devolutiva', { tipo: 'dias', valor: 30 }, 'em 30 dias'),
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

/** Dias úteis de segunda a sexta, sem feriados; o dia da publicação não conta. */
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

/** Soma meses; o dia que não existe no mês de chegada vira o último dia dele (31/12 + 2 meses = 28/02). */
export function somarMeses(data: string, meses: number): string {
  const [ano, mes, dia] = data.split('-').map(Number);
  const ultimoDia = new Date(Date.UTC(ano!, mes! - 1 + meses + 1, 0)).getUTCDate();
  return paraTexto(new Date(Date.UTC(ano!, mes! - 1 + meses, Math.min(dia!, ultimoDia))));
}

function prazoEm(prazo: Prazo, publicadaEm: string): string {
  switch (prazo.tipo) {
    case 'horas':
      return somarDias(publicadaEm, Math.ceil(prazo.valor / 24));
    case 'dias':
      return somarDias(publicadaEm, prazo.valor);
    case 'dias_uteis':
      return somarDiasUteis(publicadaEm, prazo.valor);
    case 'meses':
      return somarMeses(publicadaEm, prazo.valor);
  }
}

/** As tarefas da resposta à cor publicada, com prazo contado a partir da data de publicação. */
export function criarTarefas(cor: Cor, municipio: number, publicadaEm: string): TarefaResposta[] {
  return RESPOSTA_POR_COR[cor].tarefas.map((t) => ({
    chave: t.chave,
    titulo: t.titulo,
    municipio,
    cor,
    criada_em: publicadaEm,
    prazo_em: prazoEm(t.prazo, publicadaEm),
    concluida_em: null,
  }));
}

/** Situação da tarefa na data de referência: no prazo, vence hoje, vencida (ou concluída). */
export function estadoDaTarefa(t: TarefaResposta, dataReferencia: string): EstadoTarefa {
  if (t.concluida_em !== null) return 'concluida';
  if (dataReferencia < t.prazo_em) return 'no_prazo';
  return dataReferencia === t.prazo_em ? 'vence_hoje' : 'vencida';
}
