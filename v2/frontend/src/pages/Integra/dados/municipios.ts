/**
 * Municípios REAIS (nome e UF) usados na demonstração da Integra.
 *
 * O tempo de deslocamento (ida e volta, a partir de Fortaleza) é SIMULADO: a ordem de grandeza segue
 * a ata de 23/11/2026 (12 por terra, 47 de avião, mediana perto de 16 h). Petrolina-PE e Milagres-CE
 * vão de carro, como a ata pediu para corrigir. Santa Quitéria-CE fica sem localidade definida e usa a
 * mediana (valor estimado).
 */
import type { UFCode } from '@/types/organizacao';
import type { MeioDeslocamento } from './tipos';

export interface MunicipioReal {
  nome: string;
  uf: UFCode;
  meio: MeioDeslocamento | null;
  /** Horas de ida e volta; `null` = sem localidade definida. */
  horas: number | null;
}

const carro = (nome: string, uf: UFCode, horas: number): MunicipioReal => ({ nome, uf, meio: 'carro', horas });
const aviao = (nome: string, uf: UFCode, horas: number): MunicipioReal => ({ nome, uf, meio: 'aviao', horas });

export const MUNICIPIOS_REAIS: readonly MunicipioReal[] = [
  // Norte
  aviao('Belém', 'PA', 12),
  aviao('Santarém', 'PA', 22),
  aviao('Marabá', 'PA', 18),
  aviao('Parauapebas', 'PA', 20),
  aviao('Manaus', 'AM', 16),
  aviao('Parintins', 'AM', 28),
  aviao('Palmas', 'TO', 16),
  aviao('Araguaína', 'TO', 20),
  aviao('Porto Velho', 'RO', 24),
  aviao('Rio Branco', 'AC', 30),
  aviao('Macapá', 'AP', 18),
  aviao('Boa Vista', 'RR', 26),
  // Centro-Oeste, Sudeste e Sul
  aviao('Goiânia', 'GO', 16),
  aviao('Cuiabá', 'MT', 20),
  aviao('Sinop', 'MT', 28),
  aviao('Dourados', 'MS', 26),
  aviao('Montes Claros', 'MG', 19),
  aviao('Uberlândia', 'MG', 20),
  aviao('Teófilo Otoni', 'MG', 24),
  aviao('Sorocaba', 'SP', 18),
  aviao('Ribeirão Preto', 'SP', 18),
  aviao('Vila Velha', 'ES', 17),
  aviao('Londrina', 'PR', 22),
  aviao('Santa Maria', 'RS', 30),
  // Nordeste, de avião
  aviao('Teresina', 'PI', 10),
  aviao('Picos', 'PI', 16),
  aviao('Floriano', 'PI', 18),
  aviao('São Luís', 'MA', 10),
  aviao('Imperatriz', 'MA', 16),
  aviao('Caxias', 'MA', 15),
  aviao('Recife', 'PE', 8),
  aviao('Caruaru', 'PE', 12),
  aviao('Garanhuns', 'PE', 15),
  aviao('João Pessoa', 'PB', 9),
  aviao('Campina Grande', 'PB', 12),
  aviao('Patos', 'PB', 15),
  aviao('Natal', 'RN', 8),
  aviao('Caicó', 'RN', 15),
  aviao('Maceió', 'AL', 10),
  aviao('Arapiraca', 'AL', 14),
  aviao('Aracaju', 'SE', 11),
  aviao('Itabaiana', 'SE', 14),
  aviao('Salvador', 'BA', 10),
  aviao('Feira de Santana', 'BA', 13),
  aviao('Vitória da Conquista', 'BA', 18),
  aviao('Barreiras', 'BA', 22),
  aviao('Juazeiro', 'BA', 19),
  // Por terra
  carro('Russas', 'CE', 5),
  carro('Quixadá', 'CE', 6),
  carro('Sobral', 'CE', 8),
  carro('Mossoró', 'RN', 9),
  carro('Tianguá', 'CE', 10),
  carro('Iguatu', 'CE', 12),
  carro('Crateús', 'CE', 12),
  carro('Parnaíba', 'PI', 13),
  carro('Milagres', 'CE', 14),
  carro('Juazeiro do Norte', 'CE', 17),
  carro('Crato', 'CE', 17),
  carro('Petrolina', 'PE', 24),
  // Sem localidade definida: usa a mediana
  { nome: 'Santa Quitéria', uf: 'CE', meio: null, horas: null },
];
