/**
 * Tipos dos dados da Integra (protótipo com DADOS SIMULADOS).
 *
 * O formato segue as entidades que já existem no Aprender Sistema, com os nomes de campo do
 * backend (snake_case), para que trocar o simulado pelo real seja só trocar `fonte.ts`:
 * - `MunicipioIntegra` = `Municipio` (id, nome, uf) + o que ainda falta no cadastro real;
 * - `Colecao` = `ProjetoGeral` (a coleção, ex.: NOVO LENDO);
 * - `Atendimento.coordenador` = `PlanoFormacoes.coordenadores` / `EquipeGerencia` COORDENADOR;
 * - `SegmentoAtendimento.professor_qtde` / `aluno_qtde` = `DATRegistro.professor_qtde` / `aluno_qtde`.
 *
 * Campos marcados "FALTA NO CADASTRO REAL" não existem hoje no sistema.
 */
import type { UFCode } from '@/types/organizacao';

export type StatusMunicipio = 'ativo' | 'suspenso';
export type MeioDeslocamento = 'aviao' | 'carro';

/** Município (`Municipio`: id, nome, uf) com os campos que o ICA e o Semáforo precisam. */
export interface MunicipioIntegra {
  id: number;
  nome: string;
  uf: UFCode;
  /** FALTA NO CADASTRO REAL: ativo ou suspenso (suspenso não conta no ICA). */
  status: StatusMunicipio;
  /** Data (AAAA-MM-DD) da última mudança de status. */
  status_desde: string;
  /** FALTA NO CADASTRO REAL: id da gestora de referência (`Pessoa`). */
  gestora_referencia: number | null;
  /** FALTA NO CADASTRO REAL: horas de ida e volta a partir de Fortaleza; `null` = sem localidade definida. */
  deslocamento_horas: number | null;
  deslocamento_meio: MeioDeslocamento | null;
}

/** Coleção = `ProjetoGeral`. */
export interface Colecao {
  id: number;
  nome: string;
}

/** Pessoa da gestão (gestora técnica, gestora de referência). */
export interface Pessoa {
  id: number;
  nome: string;
}

/** Gerência (`Gerencia`), liderada por uma gestora técnica. */
export interface Gerencia {
  id: number;
  nome: string;
  /** id da gestora técnica (`Pessoa`). */
  gestora_tecnica: number;
}

export type Atuacao = 'alfabetizacao_ei' | 'amma' | 'educacao_infantil';

export const ROTULO_ATUACAO: Record<Atuacao, string> = {
  alfabetizacao_ei: 'Alfabetização + EI',
  amma: 'AMMA',
  educacao_infantil: 'Educação Infantil',
};

export interface Coordenador {
  id: number;
  nome: string;
  atuacao: Atuacao;
  /** id da `Gerencia`. */
  gerencia: number;
}

/** Números de um segmento atendido (ex.: Anos Iniciais). `null` = não informado. */
export interface SegmentoAtendimento {
  segmento: string;
  /** FALTA NO CADASTRO REAL: quantos anos (séries) do segmento a coleção atende. Cada ano é uma frente (decisão 59). */
  anos: number;
  /** FALTA NO CADASTRO REAL: turmas de formação. */
  turmas_qtde: number | null;
  /** `DATRegistro.professor_qtde`. */
  professor_qtde: number | null;
  /** `DATRegistro.aluno_qtde`. */
  aluno_qtde: number | null;
}

/**
 * Um contrato atendido: município × coleção, com o coordenador responsável
 * (`PlanoFormacoes`: municipio, projeto, coordenadores). `coordenador: null` = contrato sem coordenador.
 */
export interface Atendimento {
  id: number;
  municipio: number;
  /** id da `Colecao` (`ProjetoGeral`). */
  projeto_geral: number;
  coordenador: number | null;
  segmentos: SegmentoAtendimento[];
}

/** O que as contas do ICA precisam: coordenadores, municípios e atendimentos. */
export interface BaseIca {
  coordenadores: Coordenador[];
  municipios: MunicipioIntegra[];
  atendimentos: Atendimento[];
}

export type Componente = 'municipios' | 'frentes' | 'turmas' | 'professores' | 'deslocamento' | 'estados';

/** Um número por componente (valores, médias, índices ou contribuições). */
export type Valores = Record<Componente, number>;

/** Pesos em pontos percentuais; somam 100. */
export type Pesos = Record<Componente, number>;

/** Uma versão da configuração de pesos (com autor, data e justificativa). */
export interface VersaoPesos {
  id: string;
  nome: string;
  pesos: Pesos;
  /** Data e hora ISO (America/Fortaleza na exibição). */
  criada_em: string;
  autor: string;
  justificativa: string;
}

/** Mover um município de um coordenador para outro (todas as coleções que eram do primeiro). */
export interface Movimento {
  municipioId: number;
  deCoordenadorId: number;
  paraCoordenadorId: number;
  /**
   * Ids dos `Atendimento` que a origem tinha no município quando a proposta foi feita (o que foi
   * simulado e aprovado). Ausente na simulação, que usa a carteira do momento.
   */
  atendimentos?: number[];
}

export type StatusRemanejamento = 'proposto' | 'aprovado' | 'aplicado';

export interface Remanejamento {
  id: string;
  movimentos: Movimento[];
  justificativa: string;
  status: StatusRemanejamento;
  proposto_por: string;
  proposto_em: string;
  aprovado_por: string | null;
  aprovado_em: string | null;
  aplicado_em: string | null;
  /** Semestre em que passou a valer (ex.: '2026.1'); `null` enquanto não aplicado. */
  semestre: string | null;
  /** Data (AAAA-MM-DD) em que passa a valer, escolhida pela SPE ao aplicar (decisão 71); `null` enquanto não aplicado. */
  vigencia_em: string | null;
}

/** O retrato de um semestre: a carteira daquele momento e a versão de pesos usada. */
export interface SemestreHistorico {
  semestre: string;
  /** Data (AAAA-MM-DD) do recálculo semestral. */
  calculado_em: string;
  versao_pesos: string;
  base: BaseIca;
}

/** Tudo o que a Integra lê. Hoje vem do gerador; na versão real, da API do Aprender Sistema. */
export interface DadosIntegra {
  origem: 'simulado' | 'aprender_sistema';
  semestre_atual: string;
  gerencias: Gerencia[];
  /** Gestoras técnicas e gestoras de referência. */
  pessoas: Pessoa[];
  colecoes: Colecao[];
  base: BaseIca;
  versoes_pesos: VersaoPesos[];
  versao_vigente: string;
  /** Do mais antigo para o atual (o último é o retrato do semestre atual). */
  historico: SemestreHistorico[];
  /** Remanejamentos já aplicados em semestres anteriores. */
  remanejamentos: Remanejamento[];
}
