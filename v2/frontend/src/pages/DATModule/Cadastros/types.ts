/**
 * Shared types for Cadastros page modules.
 */

import type { ID } from '../../../types';

/**
 * Cadastro record interface.
 * Kept in a dedicated module to avoid circular imports between view helpers.
 */
export interface CadastroRecord {
  id: ID;
  projeto_geral_nome: string;
  municipio_nome: string;
  uf: string;
  quantidade_alunos?: number;
  quantidade_professores?: number;
  quantidade_codigos?: number;
  status_criacao_curso?: string;
  data_criacao_curso?: string;
  status_chaves?: string;
  data_chaves?: string;
  status_instrucoes?: string;
  data_instrucoes?: string;
  status_envio?: string;
  data_envio?: string;
  status_recebidos?: string;
  quantidade_recebidos?: number;
  status_validados?: string;
  quantidade_validados?: number;
  status_importados?: string;
  quantidade_importados?: number;
  link_planilha?: string;
  link_plataforma?: string;
  [key: string]: unknown;
}
