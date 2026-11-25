/**
 * Municípios REAIS usados na demonstração da Integra: os 92 do relatório de tempos de deslocamento da
 * Coordenação Pedagógica (nov/2026, `deslocamento.ts`), com os tempos REAIS a partir de Fortaleza.
 *
 * Medida do ICA: as horas de IDA E VOLTA (`ida_volta_horas` do relatório), a mesma das faixas do
 * relatório (Próximo até 3h, Médio até 10h, Longo até 18h, Muito longo acima). Pernoite e tempo de
 * trabalho no município não entram (regra "Ida e volta" do relatório).
 *
 * Os 4 municípios com ações suspensas no relatório ficam com status "suspenso". O contrato do Amigos do
 * Bem (ONG, sem município definido) fica sem localidade: o ICA usa a mediana como valor estimado.
 * A UF dele é só para o formato do cadastro (o relatório não dá município): ver "Para validar".
 */
import type { UFCode } from '@/types/organizacao';
import { DESLOCAMENTO_MUNICIPIOS } from './deslocamento';
import type { MeioDeslocamento } from './tipos';

export interface MunicipioReal {
  nome: string;
  uf: UFCode;
  meio: MeioDeslocamento | null;
  /** Horas de ida e volta; `null` = sem localidade definida. */
  horas: number | null;
  acoes_suspensas: boolean;
}

/** Contrato sem município definido: usa a mediana de ida e volta (valor estimado). */
export const SEM_LOCALIDADE: MunicipioReal = {
  nome: 'Amigos do Bem',
  uf: 'CE',
  meio: null,
  horas: null,
  acoes_suspensas: false,
};

export const MUNICIPIOS_REAIS: readonly MunicipioReal[] = [
  ...DESLOCAMENTO_MUNICIPIOS.map((m) => ({
    nome: m.nome,
    uf: m.uf,
    meio: m.meio,
    horas: m.ida_volta_horas,
    acoes_suspensas: m.acoes_suspensas,
  })),
  SEM_LOCALIDADE,
];
