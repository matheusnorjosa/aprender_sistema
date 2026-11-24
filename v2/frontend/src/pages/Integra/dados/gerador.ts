/**
 * Gerador dos DADOS SIMULADOS da Integra. Determinístico: a mesma semente dá sempre a mesma
 * demonstração (PRNG mulberry32, nunca Math.random).
 *
 * Pessoas fictícias, municípios reais. A carteira de cada coordenador é escrita à mão (por região);
 * o PRNG só sorteia as coleções extras, as turmas, os professores, os alunos e a gestora de referência.
 * O fator `carga` de cada perfil foi calibrado para a história da ata de 23/11/2026 (o teste do
 * gerador garante: 3 Sobrecarga, uma perto de 170; 2 Atenção; 6 Adequada; 5 Capacidade disponível e
 * 1 sem municípios, que fica fora dos estratos; a ata fala em 6 com capacidade: ver "Para validar").
 */
import { PESOS_ORIGINAIS_V5, PESOS_REVISADOS } from '../ica/calculo';
import { MUNICIPIOS_REAIS } from './municipios';
import type {
  Atendimento,
  Atuacao,
  BaseIca,
  Colecao,
  Coordenador,
  DadosIntegra,
  Gerencia,
  MunicipioIntegra,
  Pessoa,
  Remanejamento,
  SegmentoAtendimento,
  VersaoPesos,
} from './tipos';

export const SEMENTE_DEMO = 20261207;

/** mulberry32: número em [0, 1) a partir de uma semente de 32 bits. */
export function criarPrng(semente: number): () => number {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const COLECOES: Colecao[] = [
  { id: 1, nome: 'NOVO LENDO' },
  { id: 2, nome: 'TEMA' },
  { id: 3, nome: 'AMMA' },
  { id: 4, nome: 'SUPERATIVAR' },
  { id: 5, nome: 'EI' },
  { id: 6, nome: 'PRIMEIROS PASSOS' },
];

/** [coleção principal, coleção extra] de cada atuação. */
const COLECOES_DA_ATUACAO: Record<Atuacao, readonly [number, number]> = {
  alfabetizacao_ei: [1, 2],
  amma: [3, 4],
  educacao_infantil: [5, 6],
};

const SEGMENTOS_DA_COLECAO: Record<number, readonly string[]> = {
  1: ['Anos Iniciais'],
  2: ['Anos Iniciais', 'Anos Finais'],
  3: ['Anos Iniciais', 'Anos Finais'],
  4: ['Anos Finais'],
  5: ['Educação Infantil'],
  6: ['Educação Infantil'],
};

const PESSOAS: Pessoa[] = [
  // gestoras técnicas
  { id: 201, nome: 'Albaniza Coelho' },
  { id: 202, nome: 'Rejane Tavares' },
  { id: 203, nome: 'Lindalva Moura' },
  // gestoras de referência
  { id: 211, nome: 'Francisca Diógenes' },
  { id: 212, nome: 'Mirtes Araújo' },
  { id: 213, nome: 'Zuleide Paiva' },
  { id: 214, nome: 'Gerlane Siqueira' },
  { id: 215, nome: 'Eliane Saboia' },
];
const GESTORAS_REFERENCIA = [211, 212, 213, 214, 215];

const GERENCIAS: Gerencia[] = [
  { id: 1, nome: 'Gerência 1', gestora_tecnica: 201 },
  { id: 2, nome: 'Gerência 2', gestora_tecnica: 202 },
  { id: 3, nome: 'Gerência 3', gestora_tecnica: 203 },
];

interface Perfil {
  id: number;
  nome: string;
  atuacao: Atuacao;
  gerencia: number;
  /** Carteira atual (2026.2), por nome do município; suspensos entram aqui também. */
  municipios: readonly string[];
  /** Quantos municípios ativos recebem a coleção extra (frentes = municípios + extras). */
  extras: number;
  /** Multiplica a carga de cada frente: turmas e professores (calibração da história). */
  carga: number;
}

const PERFIS: readonly Perfil[] = [
  { id: 101, nome: 'Lucinéia Barreto', atuacao: 'alfabetizacao_ei', gerencia: 1, extras: 6, carga: 0.83,
    municipios: ['Santarém', 'Marabá', 'Parauapebas', 'Manaus', 'Boa Vista', 'Macapá', 'Porto Velho', 'Belém', 'Parintins'] },
  { id: 102, nome: 'Otávio Rangel', atuacao: 'alfabetizacao_ei', gerencia: 2, extras: 4, carga: 0.90,
    municipios: ['Cuiabá', 'Sinop', 'Dourados', 'Goiânia', 'Londrina', 'Santa Maria', 'Uberlândia'] },
  { id: 103, nome: 'Rosimeire Cavalcante', atuacao: 'amma', gerencia: 3, extras: 2, carga: 1.49,
    municipios: ['Belém', 'Manaus', 'Palmas', 'Araguaína', 'São Luís', 'Imperatriz', 'Teresina'] },
  { id: 104, nome: 'Heloísa Pimentel', atuacao: 'alfabetizacao_ei', gerencia: 1, extras: 3, carga: 0.97,
    municipios: ['Salvador', 'Feira de Santana', 'Vitória da Conquista', 'Barreiras', 'Juazeiro', 'Petrolina'] },
  { id: 105, nome: 'Wanderson Brito', atuacao: 'educacao_infantil', gerencia: 3, extras: 1, carga: 1.04,
    municipios: ['Recife', 'Caruaru', 'Garanhuns', 'Salvador', 'Feira de Santana', 'Juazeiro do Norte'] },
  { id: 106, nome: 'Ivonete Sampaio', atuacao: 'alfabetizacao_ei', gerencia: 2, extras: 2, carga: 1.05,
    municipios: ['Recife', 'João Pessoa', 'Campina Grande', 'Patos', 'Natal', 'Caruaru', 'Caicó'] },
  { id: 107, nome: 'Jucélia Montenegro', atuacao: 'amma', gerencia: 1, extras: 2, carga: 1.34,
    municipios: ['Montes Claros', 'Teófilo Otoni', 'Sorocaba', 'Vila Velha', 'Goiânia', 'Ribeirão Preto'] },
  { id: 108, nome: 'Edvaldo Quaresma', atuacao: 'alfabetizacao_ei', gerencia: 3, extras: 2, carga: 1.29,
    municipios: ['Maceió', 'Arapiraca', 'Aracaju', 'Itabaiana', 'Garanhuns'] },
  { id: 109, nome: 'Marlene Fontenele', atuacao: 'educacao_infantil', gerencia: 2, extras: 1, carga: 0.99,
    municipios: ['Teresina', 'Picos', 'Floriano', 'Caxias', 'Parnaíba'] },
  { id: 110, nome: 'Rogério Assunção', atuacao: 'alfabetizacao_ei', gerencia: 1, extras: 2, carga: 1.27,
    municipios: ['São Luís', 'Imperatriz', 'Caxias', 'Teresina', 'Santa Quitéria'] },
  { id: 111, nome: 'Socorro Bezerra Lins', atuacao: 'amma', gerencia: 2, extras: 2, carga: 1.11,
    municipios: ['Recife', 'Natal', 'Mossoró', 'João Pessoa'] },
  { id: 112, nome: 'Taciana Holanda', atuacao: 'alfabetizacao_ei', gerencia: 3, extras: 1, carga: 1.06,
    municipios: ['Sobral', 'Tianguá', 'Crateús', 'Parnaíba'] },
  { id: 113, nome: 'Cleidiane Rocha', atuacao: 'educacao_infantil', gerencia: 1, extras: 0, carga: 1.31,
    municipios: ['Sobral', 'Russas', 'Quixadá', 'Iguatu'] },
  { id: 114, nome: 'Valdir Maciel', atuacao: 'alfabetizacao_ei', gerencia: 2, extras: 1, carga: 1.21,
    municipios: ['Juazeiro do Norte', 'Crato', 'Milagres', 'Iguatu'] },
  { id: 115, nome: 'Joelma Furtado', atuacao: 'amma', gerencia: 3, extras: 1, carga: 1.85,
    municipios: ['Crato', 'Milagres', 'Quixadá'] },
  { id: 116, nome: 'Neide Carvalhedo', atuacao: 'educacao_infantil', gerencia: 2, extras: 0, carga: 2.01,
    municipios: ['Mossoró', 'Tianguá', 'Crateús'] },
  // Recém-chegada (2026.2): ainda sem municípios.
  { id: 117, nome: 'Priscila Vasconcelos', atuacao: 'alfabetizacao_ei', gerencia: 1, extras: 0, carga: 1, municipios: [] },
];

/** Suspensos no semestre atual (estavam ativos antes), com a data da suspensão. */
const SUSPENSOS: Record<string, string> = {
  Parintins: '2026-08-14',
  Caicó: '2026-09-01',
  'Ribeirão Preto': '2026-10-06',
};

/** Novo contrato (2026.2) ainda sem coordenador definido. */
const CONTRATO_SEM_COORDENADOR = 'Rio Branco';
/** Contrato novo de 2026.2 em município sem localidade definida (turmas ainda não informadas). */
const CONTRATO_INCOMPLETO = { municipio: 'Santa Quitéria', coordenador: 110 };
/** Carteira com valor improvável (menos de 1 professor por 100 alunos). */
const COORDENADOR_IMPROVAVEL = 112;
/** Coordenadora que chegou em 2026.2. */
const RECEM_CHEGADA = 117;

const VERSOES: VersaoPesos[] = [
  {
    id: 'v5',
    nome: 'Configuração original (proposta v5)',
    pesos: PESOS_ORIGINAIS_V5,
    criada_em: '2025-06-30T09:00:00-03:00',
    autor: 'SPE',
    justificativa: 'Proposta de Acompanhamento das Gerências Pedagógicas junto aos Municípios (v5).',
  },
  {
    id: 'revisada-2026-11',
    nome: 'Configuração revisada (nov/2026)',
    pesos: PESOS_REVISADOS,
    criada_em: '2026-11-10T09:00:00-03:00',
    autor: 'SPE',
    justificativa: 'Sai Estados (UFs) e entra o tempo de deslocamento; pesos validados pelas gestoras pedagógicas.',
  },
];

function inteiro(rng: () => number, min: number, max: number): number {
  return min + Math.floor(rng() * (max - min + 1));
}

function embaralhar<T>(rng: () => number, lista: readonly T[]): T[] {
  const copia = [...lista];
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    const x = copia[i] as T;
    copia[i] = copia[j] as T;
    copia[j] = x;
  }
  return copia;
}

function segmentos(rng: () => number, colecao: number, carga: number): SegmentoAtendimento[] {
  const nomes = SEGMENTOS_DA_COLECAO[colecao] ?? ['Anos Iniciais'];
  // Carga contínua da frente; turmas arredondam (mínimo 1) e professores seguem a carga.
  const cargaDaFrente = (1 + rng() * 2) * carga;
  return nomes.map((segmento) => {
    const parte = cargaDaFrente / nomes.length;
    const professores = Math.max(1, Math.round(parte * inteiro(rng, 34, 50)));
    return {
      segmento,
      turmas_qtde: Math.max(1, Math.round(parte)),
      professor_qtde: professores,
      aluno_qtde: professores * inteiro(rng, 18, 26),
    };
  });
}

function idDoMunicipio(municipios: readonly MunicipioIntegra[], nome: string): number {
  const m = municipios.find((x) => x.nome === nome);
  if (!m) throw new Error(`Município fora da lista: ${nome}`);
  return m.id;
}

function copiarBase(base: BaseIca): BaseIca {
  return {
    coordenadores: base.coordenadores.map((c) => ({ ...c })),
    municipios: base.municipios.map((m) => ({ ...m })),
    atendimentos: base.atendimentos.map((a) => ({ ...a, segmentos: a.segmentos.map((s) => ({ ...s })) })),
  };
}

/** Professores de um semestre anterior: a equipe cresceu um pouco desde então. */
function comProfessores(base: BaseIca, fator: number): BaseIca {
  for (const a of base.atendimentos) {
    for (const s of a.segmentos) {
      if (s.professor_qtde !== null) s.professor_qtde = Math.round(s.professor_qtde * fator);
      if (s.aluno_qtde !== null) s.aluno_qtde = Math.round(s.aluno_qtde * fator);
    }
  }
  return base;
}

export function gerarDadosSimulados(semente: number = SEMENTE_DEMO): DadosIntegra {
  const rng = criarPrng(semente);

  const municipios: MunicipioIntegra[] = MUNICIPIOS_REAIS.map((m, i) => ({
    id: i + 1,
    nome: m.nome,
    uf: m.uf,
    status: SUSPENSOS[m.nome] ? 'suspenso' : 'ativo',
    status_desde: SUSPENSOS[m.nome] ?? '2025-02-03',
    gestora_referencia: GESTORAS_REFERENCIA[Math.floor(rng() * GESTORAS_REFERENCIA.length)] ?? null,
    deslocamento_horas: m.horas,
    deslocamento_meio: m.meio,
  }));

  const coordenadores: Coordenador[] = PERFIS.map((p) => ({ id: p.id, nome: p.nome, atuacao: p.atuacao, gerencia: p.gerencia }));

  const atendimentos: Atendimento[] = [];
  const novo = (municipio: number, projeto_geral: number, coordenador: number | null, segs: SegmentoAtendimento[]) =>
    atendimentos.push({ id: atendimentos.length + 1, municipio, projeto_geral, coordenador, segmentos: segs });

  for (const p of PERFIS) {
    const [principal, extra] = COLECOES_DA_ATUACAO[p.atuacao];
    const ids = p.municipios.map((n) => idDoMunicipio(municipios, n));
    const ativos = ids.filter((id) => municipios.find((m) => m.id === id)?.status === 'ativo');
    const comExtra = new Set(embaralhar(rng, ativos).slice(0, p.extras));
    for (const id of ids) {
      novo(id, principal, p.id, segmentos(rng, principal, p.carga));
      if (comExtra.has(id)) novo(id, extra, p.id, segmentos(rng, extra, p.carga));
    }
  }

  // Histórias pontuais.
  novo(idDoMunicipio(municipios, CONTRATO_SEM_COORDENADOR), 1, null, segmentos(rng, 1, 1));
  const idIncompleto = idDoMunicipio(municipios, CONTRATO_INCOMPLETO.municipio);
  for (const a of atendimentos) {
    if (a.municipio === idIncompleto && a.coordenador === CONTRATO_INCOMPLETO.coordenador) {
      for (const s of a.segmentos) s.turmas_qtde = null;
    }
  }
  const improvavel = atendimentos.find((a) => a.coordenador === COORDENADOR_IMPROVAVEL)?.segmentos[0];
  if (improvavel && improvavel.professor_qtde !== null) improvavel.aluno_qtde = improvavel.professor_qtde * 130;

  const base: BaseIca = { coordenadores, municipios, atendimentos };

  // Remanejamentos aplicados nos semestres anteriores.
  const campinaGrande = idDoMunicipio(municipios, 'Campina Grande');
  const imperatriz = idDoMunicipio(municipios, 'Imperatriz');
  const remanejamentos: Remanejamento[] = [
    {
      id: 'rem-2026-1-01',
      movimentos: [{ municipioId: campinaGrande, deCoordenadorId: 108, paraCoordenadorId: 106 }],
      justificativa: 'Juntar Campina Grande à carteira da Paraíba.',
      status: 'aplicado',
      proposto_por: 'Lindalva Moura (gestora técnica)',
      proposto_em: '2026-01-19T10:00:00-03:00',
      aprovado_por: 'Líder do NFP',
      aprovado_em: '2026-01-26T15:00:00-03:00',
      aplicado_em: '2026-02-02T08:00:00-03:00',
      semestre: '2026.1',
    },
    {
      id: 'rem-2026-2-01',
      movimentos: [{ municipioId: imperatriz, deCoordenadorId: 101, paraCoordenadorId: 110 }],
      justificativa: 'Aliviar a carteira mais pesada da equipe, em Sobrecarga desde 2025.2.',
      status: 'aplicado',
      proposto_por: 'Albaniza Coelho (gestora técnica)',
      proposto_em: '2026-07-06T10:00:00-03:00',
      aprovado_por: 'Líder do NFP',
      aprovado_em: '2026-07-13T15:00:00-03:00',
      aplicado_em: '2026-08-03T08:00:00-03:00',
      semestre: '2026.2',
    },
  ];

  // 2026.1: antes das suspensões, do contrato novo sem coordenador, de Santa Quitéria, da recém-chegada
  // e do remanejamento de 2026.2.
  const novosDe2026_2 = new Set([idDoMunicipio(municipios, CONTRATO_SEM_COORDENADOR), idIncompleto]);
  const base2026_1 = comProfessores(copiarBase(base), 0.96);
  base2026_1.coordenadores = base2026_1.coordenadores.filter((c) => c.id !== RECEM_CHEGADA);
  base2026_1.atendimentos = base2026_1.atendimentos.filter((a) => !novosDe2026_2.has(a.municipio));
  for (const m of base2026_1.municipios) {
    if (m.status === 'suspenso') {
      m.status = 'ativo';
      m.status_desde = '2025-02-03';
    }
  }
  for (const a of base2026_1.atendimentos) {
    if (a.municipio === imperatriz && a.coordenador === 110) a.coordenador = 101;
  }

  // 2025.2: antes do remanejamento de 2026.1.
  const base2025_2 = comProfessores(copiarBase(base2026_1), 0.95);
  for (const a of base2025_2.atendimentos) {
    if (a.municipio === campinaGrande && a.coordenador === 106) a.coordenador = 108;
  }

  return {
    origem: 'simulado',
    semestre_atual: '2026.2',
    gerencias: GERENCIAS.map((g) => ({ ...g })),
    pessoas: PESSOAS.map((p) => ({ ...p })),
    colecoes: COLECOES.map((c) => ({ ...c })),
    base,
    versoes_pesos: VERSOES.map((v) => ({ ...v, pesos: { ...v.pesos } })),
    versao_vigente: 'revisada-2026-11',
    historico: [
      { semestre: '2025.2', calculado_em: '2025-12-15', versao_pesos: 'v5', base: base2025_2 },
      { semestre: '2026.1', calculado_em: '2026-06-15', versao_pesos: 'v5', base: base2026_1 },
      { semestre: '2026.2', calculado_em: '2026-11-17', versao_pesos: 'revisada-2026-11', base: copiarBase(base) },
    ],
    remanejamentos,
  };
}
