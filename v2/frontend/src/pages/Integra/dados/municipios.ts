/**
 * Municípios REAIS usados na demonstração da Integra: os 92 do relatório de tempos de deslocamento da
 * Coordenação Pedagógica (nov/2026, `deslocamento.ts`), com os tempos REAIS a partir de Fortaleza.
 *
 * Medida do ICA: as horas de IDA E VOLTA (`ida_volta_horas` do relatório), a mesma das faixas do
 * relatório (Próximo até 3h, Médio até 10h, Longo até 18h, Muito longo acima). Pernoite e tempo de
 * trabalho no município não entram (regra "Ida e volta" do relatório).
 *
 * Os 4 municípios com ações suspensas no relatório ficam com status "suspenso".
 *
 * Amigos do Bem (decisão 56): não tem município fixo; o local é o de cada formação (AL, CE ou PE). Como no
 * Aprender Sistema, cada localidade é uma linha de município ("Amigos do Bem (Localidade)"). O tempo é o da
 * localidade no relatório; a localidade que não está nele fica sem tempo, e o ICA usa o tempo do meio (17h45,
 * decisão 55), marcado como estimado. As localidades são simuladas.
 */
import type { UFCode } from '@/types/organizacao';
import { DESLOCAMENTO_MUNICIPIOS } from './deslocamento';
import type { MeioDeslocamento } from './tipos';

export interface MunicipioReal {
  nome: string;
  uf: UFCode;
  meio: MeioDeslocamento | null;
  /** Horas de ida e volta; `null` = sem tempo no relatório. */
  horas: number | null;
  acoes_suspensas: boolean;
}

/** Localidades (simuladas) das formações do Amigos do Bem: uma em cada estado (decisão 56). */
const LOCALIDADES_AMIGOS_DO_BEM: readonly { localidade: string; uf: UFCode }[] = [
  { localidade: 'Mauriti', uf: 'CE' },
  { localidade: 'Santana do Ipanema', uf: 'AL' },
  { localidade: 'Petrolina', uf: 'PE' },
];

const nomeAmigosDoBem = (localidade: string): string => `Amigos do Bem (${localidade})`;

/** A localidade do relatório para o nome de um município do ICA: a da linha do Amigos do Bem, ou o próprio nome. */
export function localidadeDoMunicipio(nome: string): string {
  return LOCALIDADES_AMIGOS_DO_BEM.find((l) => nomeAmigosDoBem(l.localidade) === nome)?.localidade ?? nome;
}

/** Uma linha por localidade, com o tempo do relatório; fora dele, sem tempo (o ICA usa o tempo do meio). */
export const AMIGOS_DO_BEM: readonly MunicipioReal[] = LOCALIDADES_AMIGOS_DO_BEM.map(({ localidade, uf }) => {
  const doRelatorio = DESLOCAMENTO_MUNICIPIOS.find((m) => m.nome === localidade && m.uf === uf);
  return {
    nome: nomeAmigosDoBem(localidade),
    uf,
    meio: doRelatorio?.meio ?? null,
    horas: doRelatorio?.ida_volta_horas ?? null,
    acoes_suspensas: false,
  };
});

/**
 * Os 92 do relatório e a 1ª linha do Amigos do Bem, na posição que ele tinha antes (o gerador sorteia por
 * posição). As outras linhas do Amigos do Bem o gerador põe no fim, sem sorteio.
 */
export const MUNICIPIOS_REAIS: readonly MunicipioReal[] = [
  ...DESLOCAMENTO_MUNICIPIOS.map((m) => ({
    nome: m.nome,
    uf: m.uf,
    meio: m.meio,
    horas: m.ida_volta_horas,
    acoes_suspensas: m.acoes_suspensas,
  })),
  AMIGOS_DO_BEM[0] as MunicipioReal,
];
