/**
 * Organization-related TypeScript types for AS v2 Frontend
 *
 * Maps to backend serializers:
 * - MunicipioSerializer, MunicipioOptionSerializer
 * - ProjetoSerializer, ProjetoOptionSerializer
 * - TipoEventoOptionSerializer
 * - GerenciaSerializer
 */

import type { ID, ISODateTime } from './common';

/**
 * Brazilian state codes
 */
export type UFCode =
  | 'AC' | 'AL' | 'AP' | 'AM' | 'BA' | 'CE' | 'DF' | 'ES' | 'GO'
  | 'MA' | 'MT' | 'MS' | 'MG' | 'PA' | 'PB' | 'PR' | 'PE' | 'PI'
  | 'RJ' | 'RN' | 'RS' | 'RO' | 'RR' | 'SC' | 'SP' | 'SE' | 'TO';

/**
 * Municipio (city) representation
 */
export interface Municipio {
  id: ID;
  nome: string;
  uf: UFCode;
  codigo_ibge?: string;
  latitude?: number;
  longitude?: number;
}

/**
 * Municipio option for dropdowns
 */
export interface MunicipioOption {
  id: ID;
  nome: string;
  uf: UFCode;
}

/**
 * Projeto workflow types
 */
export type ProjetoFluxo = 'SUPER' | 'NAO_SUPER';

/**
 * Projeto (project) representation
 */
export interface Projeto {
  id: ID;
  nome: string;
  codigo: string;
  fluxo: ProjetoFluxo;
  is_test: boolean;
  is_active: boolean;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

/**
 * Projeto option for dropdowns
 */
export interface ProjetoOption {
  id: ID;
  nome: string;
  codigo: string;
  fluxo: ProjetoFluxo;
}

/**
 * TipoEvento (event type) option
 */
export interface TipoEventoOption {
  id: ID;
  nome: string;
  codigo?: string;
}

/**
 * Gerencia (management unit)
 *
 * `rotulo` é o nome que a tela mostra (`nome_exibicao` ou, vazio, `nome_setor`).
 * `nome` é código interno (ex.: "GERENCIA 4") e não deve ser exibido como setor.
 */
export interface Gerencia {
  id: ID;
  nome: string;
  nome_setor: string;
  nome_exibicao: string;
  rotulo: string;
  ativo: boolean;
}

/**
 * Produto (product) representation
 */
export interface Produto {
  id: ID;
  nome: string;
  codigo: string;
  is_active: boolean;
}

/**
 * Produto option for dropdowns
 */
export interface ProdutoOption {
  id: ID;
  nome: string;
  codigo: string;
}
