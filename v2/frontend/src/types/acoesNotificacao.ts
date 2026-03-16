import type { ID, ISODate, ISODateTime, PaginatedResponse } from './common';

export interface CicloAcoes {
  id: ID;
  projeto: ID;
  municipio: ID;
  projeto_nome: string;
  municipio_nome: string;
  semestre: '1S' | '2S';
  ano: number;
  status: string;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface AcaoInstancia {
  id: ID;
  ciclo: ID;
  ordem: number;
  estado: string;
  template: ID;
  template_nome: string;
  projeto_nome: string;
  municipio_nome: string;
  data_ancora: ISODate | null;
  data_vencimento: ISODate | null;
  data_realizacao: ISODate | null;
  observacao_conclusao: string;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface NotificacaoInterna {
  id: ID;
  acao_instancia: ID | null;
  acao_ordem: number | null;
  acao_nome: string | null;
  titulo: string;
  mensagem: string;
  tipo: string;
  nivel: string;
  prioridade: string;
  fase_disparo: string;
  referencia_data: ISODate;
  lida: boolean;
  lida_em: ISODateTime | null;
  created_at: ISODateTime;
}

export type PaginatedCiclos = PaginatedResponse<CicloAcoes>;
export type PaginatedAcoes = PaginatedResponse<AcaoInstancia>;
export type PaginatedNotificacoes = PaginatedResponse<NotificacaoInterna>;

export interface CriarCicloPayload {
  projeto_id: ID;
  municipio_id: ID;
  semestre: '1S' | '2S';
  ano: number;
}

export interface RegistrarAncoraPayload {
  data_ancora: ISODate;
  observacao?: string;
}

export interface ConcluirAcaoPayload {
  data_realizacao: ISODate;
  observacao: string;
}
