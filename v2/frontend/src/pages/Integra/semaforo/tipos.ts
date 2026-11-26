/**
 * Tipos do Semáforo de Risco Municipal (protótipo com DADOS SIMULADOS).
 *
 * Fonte: Requisitos_Modulo_Semaforo_Risco_Municipal.pdf (NFP, nov/2026). Como em `dados/tipos.ts`, os nomes
 * de campo seguem o padrão do backend (snake_case) e as datas vão em texto (AAAA-MM-DD). Nada disto existe no
 * cadastro real ainda: são as coletas e as decisões que o módulo vai guardar. `municipio` e `coordenador` são
 * ids de `MunicipioIntegra` e `Coordenador` (cadastro único com o ICA, seção 9 do PDF).
 */

export type Cor = 'verde' | 'amarelo' | 'vermelho';

/** Cor de um indicador. `sem_dado` fica fora da regra do pior (sugestão do PDF, seção 3). */
export type CorIndicador = Cor | 'sem_dado';

/** Os 5 indicadores, na ordem da tabela da seção 3 do PDF. */
export type Indicador = 'media_pesquisa' | 'nps' | 'cronograma' | 'ocorrencias' | 'resposta_pesquisa';

/** Ciclo bimestral no formato 'AAAA.N', com N de 1 a 6 (como o semestre '2026.1' do ICA). */
export type Ciclo = string;

/**
 * Coleta 1: a resposta de um articulador à pesquisa de satisfação do ciclo. A pesquisa é por projeto (decisão 51):
 * uma resposta por projeto no ciclo; o articulador de dois projetos responde duas vezes.
 */
export interface RespostaPesquisa {
  id: number;
  municipio: number;
  /** id do projeto do município (`ProjetoMunicipio.id`). */
  projeto: number;
  ciclo: Ciclo;
  /** Data (AAAA-MM-DD) da resposta. */
  respondida_em: string;
  /** Respondeu dentro do prazo de resposta do ciclo. */
  no_prazo: boolean;
  funcao_respondente: string;
  /** Identificação é opcional na pesquisa. */
  identificacao: string | null;
  /** Os 6 itens, de 1 a 5, na ordem do PDF (cronograma, formações, coordenador, avaliações, materiais, avanço). */
  itens: readonly number[];
  /** Nota de 0 a 10. */
  nps: number;
  /** Campo aberto: "O que precisamos melhorar com urgência?". */
  comentario: string;
}

/**
 * Coleta 2: o relatório mensal do coordenador (parte que alimenta o cronograma cumprido). Um por projeto e mês
 * (decisão 46): cada projeto tem o seu cronograma.
 */
export interface RelatorioMensal {
  id: number;
  municipio: number;
  /** id do projeto do município (`ProjetoMunicipio.id`). */
  projeto: number;
  /** O coordenador do projeto. */
  coordenador: number;
  /** Mês de referência (AAAA-MM). */
  mes: string;
  formacoes_previstas: number;
  formacoes_realizadas: number;
  visitas_previstas: number;
  visitas_realizadas: number;
}

/** Ocorrência leve: dúvida, ajuste de agenda, pedido de material. Reclamação: sobre o coordenador ou os projetos. */
export type TipoOcorrencia = 'leve' | 'reclamacao';

/** Coletas 3 (fluxo único), 4 (reunião de escuta) e 5 (momento reservado, confidencial). */
export type OrigemOcorrencia = 'fluxo_unico' | 'reuniao_escuta' | 'momento_reservado';

export interface Ocorrencia {
  id: number;
  municipio: number;
  /** Data (AAAA-MM-DD) do registro: o dia de `registrada_em`. */
  data: string;
  /** Data e hora do registro (AAAA-MM-DDTHH:MM:SS-03:00, hora de Fortaleza). Decisão 50. */
  registrada_em: string;
  /** Data e hora da resposta ao município, no mesmo formato; `null` = ainda sem resposta. Decisão 50. */
  respondida_em: string | null;
  origem: OrigemOcorrencia;
  tipo: TipoOcorrencia;
}

/** Os valores dos 5 indicadores de um município no ciclo. `null` = sem dado. */
export interface ValoresIndicadores {
  /** Média dos 6 itens de todas as respostas do ciclo, de todos os projetos (1 a 5). */
  media_pesquisa: number | null;
  /** Média das notas NPS do ciclo, de todos os projetos (0 a 10). */
  nps: number | null;
  /**
   * Formações e visitas realizadas ÷ previstas, em %, do projeto com o menor número (decisão 46: na cor do
   * município entra o pior projeto). Sem nada previsto em nenhum projeto = sem dado.
   */
  cronograma: number | null;
  /**
   * Ocorrências desde a 1ª formação do ano no município, por tipo (nenhuma é um dado: verde). Decisão 32.
   * `fora_da_contagem`: as do ano registradas antes da 1ª formação (ou sem formação no ano), que ficam guardadas e
   * não contam na cor; a tela diz quantas são.
   */
  ocorrencias: { leves: number; reclamacoes: number; fora_da_contagem?: number };
  /**
   * Se o município respondeu no prazo, olhando o projeto com a pior situação (decisão 51); `null` = pesquisa ainda
   * no prazo ou não enviada.
   */
  resposta_pesquisa: { ciclo_atual: boolean | null; ciclo_anterior: boolean | null };
}

/** Um indicador com a cor e o valor escrito para a tela ("4,2", "78%", "1 leve", "Sem dado"). */
export interface AvaliacaoIndicador {
  indicador: Indicador;
  cor: CorIndicador;
  texto: string;
}

/** Por que o município ficou com a cor. */
export type MotivoCor =
  | 'indicador_vermelho'
  | 'tres_amarelos'
  | 'pior_indicador'
  | 'em_recuperacao'
  | 'ciclo_em_andamento'
  | 'sem_alerta';

/** Um ciclo já publicado pelo Comitê, para as regras que olham para trás. */
export interface CicloPublicado {
  ciclo: Ciclo;
  /** Ciclo fechado sem nenhum indicador em amarelo ou vermelho ("sem dado" não conta). */
  limpo: boolean;
  cor_publicada: Cor;
}

/** A cor que o sistema sugere para o ciclo, com o que a explica. */
export interface ResultadoCor {
  cor: Cor;
  motivo: MotivoCor;
  /** Os indicadores que definiram a cor (os vermelhos, os amarelos); vazio quando não há alerta. */
  decisivos: Indicador[];
  avaliacoes: AvaliacaoIndicador[];
  /** Indicadores sem dado no ciclo, que ficaram fora da regra. */
  sem_dado: Indicador[];
  /** Ciclo sem nenhum indicador amarelo ou vermelho. */
  limpo: boolean;
  /** Ciclos limpos seguidos, contando o atual só se ele já fechou (para o "em recuperação"). */
  ciclos_limpos: number;
  em_recuperacao: boolean;
  /**
   * Um indicador em vermelho (decisão 38) ou três amarelos (decisão 39): a cor oficial vira vermelho na hora, sem
   * esperar o Comitê, que confirma ou desfaz depois.
   */
  vermelho_imediato: boolean;
}

/**
 * De onde veio a cor oficial: o vermelho na hora (decisões 38 e 39, sem reunião) ou o Comitê, no ordinário (data
 * marcada pela SPE, decisão 40) ou no extraordinário (convocado a critério da SPE, decisão 41).
 */
export type OrigemDecisao = 'vermelho_automatico' | 'comite_ordinario' | 'comite_extraordinario';

/**
 * Uma cor oficial publicada para o município no ciclo: pelo Comitê de Satisfação ou, no vermelho na hora, pelo
 * próprio sistema (`origem: 'vermelho_automatico'`, que o Comitê confirma ou desfaz depois).
 */
export interface DecisaoComite {
  municipio: number;
  ciclo: Ciclo;
  cor_sugerida: Cor;
  cor_publicada: Cor;
  /** Obrigatória quando a cor publicada é diferente da sugerida. */
  justificativa: string | null;
  /** Data (AAAA-MM-DD) da publicação; no vermelho automático, a data do dado que o disparou. */
  publicada_em: string;
  origem: OrigemDecisao;
}

export type ChaveTarefa =
  | 'contato_articulador'
  | 'observacao_formacao'
  | 'contato_48h'
  | 'reuniao_secretaria'
  | 'plano_acao'
  | 'devolutiva'
  | 'visita_tecnica';

/**
 * Como o prazo é contado a partir da publicação da cor: dias úteis (segunda a sexta, decisões 33 e 34) ou meses
 * ("no bimestre", "no semestre", decisão 35).
 */
export type Prazo = { tipo: 'dias_uteis'; valor: number } | { tipo: 'meses'; valor: number };

export interface ModeloTarefa {
  chave: ChaveTarefa;
  titulo: string;
  prazo: Prazo;
  /** O prazo escrito para a tela ("em 2 dias úteis", "no bimestre"). */
  prazo_texto: string;
}

/**
 * Por que uma tarefa aberta deixou de valer sem ser feita. Decisão 42: o Comitê desfez a cor (`cancelada_comite`).
 * Decisão 43: a mesma cor publicada de novo reabriu as tarefas da cor (`substituida`). A tarefa fica guardada com
 * o motivo (decisão 57: nada some).
 */
export type MotivoEncerramento = 'cancelada_comite' | 'substituida';

/** Uma tarefa criada quando a cor é publicada. */
export interface TarefaResposta {
  /** Único em `DadosSemaforo.tarefas` (a mesma chave e data podem se repetir quando a cor reabre). */
  id: number;
  chave: ChaveTarefa;
  titulo: string;
  municipio: number;
  cor: Cor;
  /** Data (AAAA-MM-DD) da publicação da cor. */
  criada_em: string;
  /** Data (AAAA-MM-DD) do prazo. */
  prazo_em: string;
  /** Data (AAAA-MM-DD) da conclusão; `null` = não foi feita. */
  concluida_em: string | null;
  /** A tarefa aberta que deixou de valer, com o motivo e a data; `null` = vale. */
  encerramento: { motivo: MotivoEncerramento; em: string } | null;
}

export type EstadoTarefa = 'no_prazo' | 'vence_hoje' | 'vencida' | 'concluida' | MotivoEncerramento;

export type Mudanca = 'piorou' | 'melhorou' | 'igual' | 'sem_anterior';
