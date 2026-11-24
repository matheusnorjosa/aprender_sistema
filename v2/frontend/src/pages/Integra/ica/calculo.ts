/**
 * Contas do ICA (Índice de Carga de Acompanhamento). Funções puras.
 *
 * Regras: Requisitos_Modulo_ICA.pdf (NFP, nov/2026).
 * - ICA = Σ peso × (valor do coordenador ÷ média da equipe) × 100.
 * - A média conta só coordenadores com pelo menos um município ativo; quem não tem fica com ICA 0
 *   e aparece como "sem municípios".
 * - A conta usa os valores exatos; o ICA é exibido inteiro e o estrato sai do número exibido.
 */
import type {
  Atendimento,
  BaseIca,
  Colecao,
  Componente,
  Coordenador,
  Gerencia,
  MunicipioIntegra,
  Movimento,
  Pesos,
  Pessoa,
  Valores,
} from '../dados/tipos';

export const COMPONENTES: readonly Componente[] = [
  'municipios',
  'frentes',
  'turmas',
  'professores',
  'deslocamento',
  'estados',
];

export const ROTULO_COMPONENTE: Record<Componente, string> = {
  municipios: 'Municípios ativos',
  frentes: 'Frentes (município × coleção)',
  turmas: 'Turmas de formação',
  professores: 'Professores em formação',
  deslocamento: 'Tempo de deslocamento (ida e volta)',
  estados: 'Estados (UFs)',
};

/** Configuração revisada (nov/2026). */
export const PESOS_REVISADOS: Pesos = {
  municipios: 25,
  frentes: 25,
  turmas: 20,
  professores: 20,
  deslocamento: 10,
  estados: 0,
};

/** Configuração original (proposta v5): sem deslocamento, com estados. */
export const PESOS_ORIGINAIS_V5: Pesos = {
  municipios: 20,
  frentes: 20,
  turmas: 25,
  professores: 25,
  deslocamento: 0,
  estados: 10,
};

export function zerados(): Valores {
  return { municipios: 0, frentes: 0, turmas: 0, professores: 0, deslocamento: 0, estados: 0 };
}

export interface ValidacaoPesos {
  valido: boolean;
  soma: number;
  erros: string[];
}

/** Percentual em português com as casas que o número tiver (até 2): "100%", "99,6%". */
export function formatarPercentual(valor: number): string {
  return `${valor.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`;
}

/** A soma conta todo número digitado (negativo também), para a tela mostrar a soma real. */
export function validarPesos(pesos: Pesos): ValidacaoPesos {
  const erros: string[] = [];
  let soma = 0;
  for (const c of COMPONENTES) {
    const p = pesos[c];
    if (!Number.isFinite(p) || p < 0 || p > 100) {
      erros.push(`O peso de "${ROTULO_COMPONENTE[c]}" precisa ser um número de 0 a 100.`);
    }
    if (Number.isFinite(p)) soma += p;
  }
  soma = Math.round(soma * 1e6) / 1e6;
  if (soma !== 100) erros.push(`Os pesos precisam somar 100%. Hoje somam ${formatarPercentual(soma)}.`);
  return { valido: erros.length === 0, soma, erros };
}

// ---------------------------------------------------------------- estratos e meta

export type Estrato = 'sobrecarga' | 'atencao' | 'adequada' | 'capacidade';

export interface InfoEstrato {
  chave: Estrato;
  nome: string;
  faixa: string;
  orientacao: string;
}

/** Do mais carregado para o menos carregado. */
export const ESTRATOS: readonly InfoEstrato[] = [
  { chave: 'sobrecarga', nome: 'Sobrecarga', faixa: '130 ou mais', orientacao: 'Prioridade para redistribuir ou reforçar a equipe.' },
  { chave: 'atencao', nome: 'Atenção', faixa: '110 a 129', orientacao: 'Não receber novos municípios sem rever a carteira.' },
  { chave: 'adequada', nome: 'Adequada', faixa: '80 a 109', orientacao: 'Carga próxima da média da equipe.' },
  { chave: 'capacidade', nome: 'Capacidade disponível', faixa: 'abaixo de 80', orientacao: 'Primeiros nomes para novos contratos ou retomadas.' },
];

export const META_ICA = { minimo: 70, maximo: 130 } as const;

/** Arredonda para inteiro (meio para cima), sem cair no ruído do ponto flutuante. */
export function arredondarIca(valor: number): number {
  return Math.round(Math.round(valor * 1e6) / 1e6);
}

/**
 * ICA exato com uma casa, para mostrar ao lado do exibido (como o PDF: "169,8 → 170").
 * Arredonda a casa, menos quando isso apontaria outro inteiro: 148,4758 viraria "148,5" e quem lê
 * esperaria 149, não 148. Só nesse caso (x,45 a x,4999) a casa é cortada: "148,4".
 */
export function icaExatoComUmaCasa(valor: number): number {
  const umaCasa = Math.round(Math.round(valor * 1e6) / 1e5) / 10;
  if (arredondarIca(umaCasa) === arredondarIca(valor)) return umaCasa;
  return Math.floor(Math.round(valor * 1e6) / 1e5) / 10;
}

/** Estrato a partir do ICA EXIBIDO (inteiro). */
export function estratoDoIca(icaExibido: number): Estrato {
  if (icaExibido >= 130) return 'sobrecarga';
  if (icaExibido >= 110) return 'atencao';
  if (icaExibido >= 80) return 'adequada';
  return 'capacidade';
}

export function nomeDoEstrato(estrato: Estrato): string {
  return ESTRATOS.find((e) => e.chave === estrato)?.nome ?? estrato;
}

/** Meta de gestão: ICA exibido entre 70 e 130 (pontas incluídas). */
export function dentroDaMeta(icaExibido: number): boolean {
  return icaExibido >= META_ICA.minimo && icaExibido <= META_ICA.maximo;
}

// ---------------------------------------------------------------- a conta

/** valor ÷ média × 100; com média 0 o índice é 0. */
export function indiceDoComponente(valor: number, media: number): number {
  return media > 0 ? (valor * 100) / media : 0;
}

export interface ContaIca {
  indices: Valores;
  /** peso × índice, em pontos de ICA. */
  contribuicoes: Valores;
  icaExato: number;
  icaExibido: number;
  estrato: Estrato;
  dentroDaMeta: boolean;
}

export function calcularIca(valores: Valores, medias: Valores, pesos: Pesos): ContaIca {
  const indices = zerados();
  const contribuicoes = zerados();
  let icaExato = 0;
  for (const c of COMPONENTES) {
    indices[c] = indiceDoComponente(valores[c], medias[c]);
    contribuicoes[c] = (pesos[c] * indices[c]) / 100;
    icaExato += contribuicoes[c];
  }
  const icaExibido = arredondarIca(icaExato);
  return { indices, contribuicoes, icaExato, icaExibido, estrato: estratoDoIca(icaExibido), dentroDaMeta: dentroDaMeta(icaExibido) };
}

/**
 * Variação do ICA exibido entre dois cálculos do mesmo coordenador. Sem comparação (`null`) quando falta
 * um dos dois ou quando um deles está sem municípios: o ICA 0 de quem está fora da média não é um ICA.
 */
export function variacaoDoIca(
  atual: { semMunicipios: boolean; conta: { icaExibido: number } } | undefined,
  anterior: { semMunicipios: boolean; conta: { icaExibido: number } } | undefined,
): number | null {
  if (!atual || !anterior || atual.semMunicipios || anterior.semMunicipios) return null;
  return atual.conta.icaExibido - anterior.conta.icaExibido;
}

/** Horas decimais → "139h00". */
export function formatarHoras(horas: number): string {
  const minutosTotais = Math.round(horas * 60);
  const h = Math.floor(minutosTotais / 60);
  const m = minutosTotais % 60;
  return `${h}h${String(m).padStart(2, '0')}`;
}

/** Mediana das horas de ida e volta de todos os municípios com localidade definida. */
export function medianaDeslocamento(municipios: readonly MunicipioIntegra[]): number {
  const horas = municipios
    .map((m) => m.deslocamento_horas)
    .filter((h): h is number => h !== null)
    .sort((a, b) => a - b);
  if (horas.length === 0) return 0;
  const meio = Math.floor(horas.length / 2);
  const centro = horas[meio] ?? 0;
  return horas.length % 2 === 1 ? centro : ((horas[meio - 1] ?? 0) + centro) / 2;
}

// ---------------------------------------------------------------- carteira

export interface LinhaCarteira {
  municipio: MunicipioIntegra;
  ativo: boolean;
  /** ids das coleções (`projeto_geral`) deste coordenador neste município. */
  colecoes: number[];
  turmas: number;
  professores: number;
  /** Horas de ida e volta usadas na conta (a mediana, quando sem localidade). */
  horas: number;
  estimado: boolean;
  /** Outros coordenadores que atendem o mesmo município. */
  compartilhadoCom: number[];
  /** Avisos de campo vazio (ex.: turmas não informadas). */
  incompleto: string[];
  /** Avisos de valor improvável. */
  improvavel: string[];
}

/** Os municípios da carteira do coordenador, um por linha (ativos e suspensos). */
export function carteiraDoCoordenador(base: BaseIca, coordenadorId: number, mediana: number): LinhaCarteira[] {
  const porMunicipio = new Map<number, Atendimento[]>();
  for (const a of base.atendimentos) {
    if (a.coordenador !== coordenadorId) continue;
    const lista = porMunicipio.get(a.municipio) ?? [];
    lista.push(a);
    porMunicipio.set(a.municipio, lista);
  }
  const linhas: LinhaCarteira[] = [];
  for (const [municipioId, atendimentos] of porMunicipio) {
    const municipio = base.municipios.find((m) => m.id === municipioId);
    if (!municipio) continue;
    let turmas = 0;
    let professores = 0;
    const incompleto: string[] = [];
    const improvavel: string[] = [];
    for (const a of atendimentos) {
      for (const s of a.segmentos) {
        const onde = `${municipio.nome}-${municipio.uf} (${s.segmento})`;
        if (s.turmas_qtde === null) incompleto.push(`Turmas não informadas em ${onde}.`);
        if (s.professor_qtde === null) incompleto.push(`Professores não informados em ${onde}.`);
        const t = s.turmas_qtde ?? 0;
        const p = s.professor_qtde ?? 0;
        turmas += t;
        professores += p;
        if (t > 0 && s.professor_qtde === 0) improvavel.push(`Turma sem professor em ${onde}.`);
        if (s.aluno_qtde !== null && s.professor_qtde !== null && s.professor_qtde * 100 < s.aluno_qtde) {
          improvavel.push(`Menos de 1 professor por 100 alunos em ${onde}.`);
        }
      }
    }
    const compartilhadoCom = [
      ...new Set(
        base.atendimentos
          .filter((a) => a.municipio === municipioId && a.coordenador !== null && a.coordenador !== coordenadorId)
          .map((a) => a.coordenador as number),
      ),
    ].sort((x, y) => x - y);
    const estimado = municipio.deslocamento_horas === null;
    linhas.push({
      municipio,
      ativo: municipio.status === 'ativo',
      colecoes: [...new Set(atendimentos.map((a) => a.projeto_geral))].sort((x, y) => x - y),
      turmas,
      professores,
      horas: municipio.deslocamento_horas ?? mediana,
      estimado,
      compartilhadoCom,
      incompleto,
      improvavel,
    });
  }
  return linhas.sort((a, b) => a.municipio.nome.localeCompare(b.municipio.nome, 'pt-BR'));
}

// ---------------------------------------------------------------- equipe

export interface ResultadoCoordenador {
  coordenador: Coordenador;
  carteira: LinhaCarteira[];
  valores: Valores;
  conta: ContaIca;
  semMunicipios: boolean;
  dadoIncompleto: boolean;
  motivosIncompleto: string[];
  valoresImprovaveis: string[];
  /** Algum município ativo usou a mediana (sem localidade). */
  deslocamentoEstimado: boolean;
}

export interface Dispersao {
  media: number;
  /** Desvio padrão populacional do ICA exato. */
  desvioPadrao: number;
  menor: number;
  maior: number;
  /** Quantos coordenadores com carteira entraram na conta. */
  quantidade: number;
}

export interface ResultadoEquipe {
  coordenadores: ResultadoCoordenador[];
  medias: Valores;
  /** Mediana de deslocamento usada para municípios sem localidade. */
  mediana: number;
  dispersao: Dispersao;
  /** Só quem tem carteira: quem está sem municípios não entra em estrato nenhum (PDF, seção 3). */
  porEstrato: Record<Estrato, number>;
  /** Quantos estão sem municípios (ICA 0, fora da média e dos estratos). */
  semMunicipios: number;
  /** Contratos de município ativo sem coordenador definido. */
  contratosSemCoordenador: Atendimento[];
}

function valoresDaCarteira(carteira: readonly LinhaCarteira[], base: BaseIca, coordenadorId: number): Valores {
  const ativas = carteira.filter((l) => l.ativo);
  const ativos = new Set(ativas.map((l) => l.municipio.id));
  const frentes = new Set(
    base.atendimentos
      .filter((a) => a.coordenador === coordenadorId && ativos.has(a.municipio))
      .map((a) => `${a.municipio}×${a.projeto_geral}`),
  );
  return {
    municipios: ativas.length,
    frentes: frentes.size,
    turmas: ativas.reduce((s, l) => s + l.turmas, 0),
    professores: ativas.reduce((s, l) => s + l.professores, 0),
    deslocamento: ativas.reduce((s, l) => s + l.horas, 0),
    estados: new Set(ativas.map((l) => l.municipio.uf)).size,
  };
}

/** Desvio, menor e maior ICA entre quem tem carteira. */
export function calcularDispersao(
  resultados: ReadonlyArray<{ semMunicipios: boolean; conta: { icaExato: number } }>,
): Dispersao {
  const icas = resultados.filter((r) => !r.semMunicipios).map((r) => r.conta.icaExato);
  if (icas.length === 0) return { media: 0, desvioPadrao: 0, menor: 0, maior: 0, quantidade: 0 };
  const media = icas.reduce((s, v) => s + v, 0) / icas.length;
  const variancia = icas.reduce((s, v) => s + (v - media) ** 2, 0) / icas.length;
  return {
    media,
    desvioPadrao: Math.sqrt(variancia),
    menor: Math.min(...icas),
    maior: Math.max(...icas),
    quantidade: icas.length,
  };
}

export function calcularEquipe(base: BaseIca, pesos: Pesos): ResultadoEquipe {
  const mediana = medianaDeslocamento(base.municipios);
  const parciais = base.coordenadores.map((coordenador) => {
    const carteira = carteiraDoCoordenador(base, coordenador.id, mediana);
    const ativas = carteira.filter((l) => l.ativo);
    const motivosIncompleto = ativas.flatMap((l) => l.incompleto);
    return {
      coordenador,
      carteira,
      valores: valoresDaCarteira(carteira, base, coordenador.id),
      semMunicipios: ativas.length === 0,
      dadoIncompleto: motivosIncompleto.length > 0,
      motivosIncompleto,
      valoresImprovaveis: ativas.flatMap((l) => l.improvavel),
      deslocamentoEstimado: ativas.some((l) => l.estimado),
    };
  });

  const comCarteira = parciais.filter((p) => !p.semMunicipios);
  const medias = zerados();
  for (const c of COMPONENTES) {
    medias[c] = comCarteira.length > 0 ? comCarteira.reduce((s, p) => s + p.valores[c], 0) / comCarteira.length : 0;
  }

  const coordenadores: ResultadoCoordenador[] = parciais.map((p) => ({
    ...p,
    conta: p.semMunicipios ? calcularIca(zerados(), medias, pesos) : calcularIca(p.valores, medias, pesos),
  }));

  const porEstrato: Record<Estrato, number> = { sobrecarga: 0, atencao: 0, adequada: 0, capacidade: 0 };
  for (const r of coordenadores) if (!r.semMunicipios) porEstrato[r.conta.estrato] += 1;

  const ativos = new Set(base.municipios.filter((m) => m.status === 'ativo').map((m) => m.id));
  return {
    coordenadores,
    medias,
    mediana,
    dispersao: calcularDispersao(coordenadores),
    porEstrato,
    semMunicipios: coordenadores.filter((r) => r.semMunicipios).length,
    contratosSemCoordenador: base.atendimentos.filter((a) => a.coordenador === null && ativos.has(a.municipio)),
  };
}

// ---------------------------------------------------------------- simulador e comparativo

/**
 * Move, numa CÓPIA da base, as coleções que o coordenador de origem atende no município para o
 * coordenador de destino. Movimento sem nada a mover volta em `invalidos`.
 *
 * Cada movimento escolhe as coleções na base RECEBIDA, não no resultado dos anteriores: a troca
 * "Recife de A para B" + "Recife de B para A" troca as carteiras, em qualquer ordem.
 *
 * Movimento com `atendimentos` (guardados ao propor) só vale se a origem tem no município exatamente
 * esses atendimentos: se outra proposta já mexeu ali, ele volta em `invalidos` em vez de mover mais
 * (ou menos) do que foi simulado e aprovado.
 */
export function aplicarMovimentos(
  base: BaseIca,
  movimentos: readonly Movimento[],
): { base: BaseIca; invalidos: Movimento[] } {
  let atendimentos = base.atendimentos.map((a) => ({ ...a }));
  const invalidos: Movimento[] = [];
  for (const m of movimentos) {
    const ids = new Set(
      base.atendimentos
        .filter((a) => a.municipio === m.municipioId && a.coordenador === m.deCoordenadorId)
        .map((a) => a.id),
    );
    const mudouDesdeAProposta =
      m.atendimentos !== undefined && (new Set(m.atendimentos).size !== ids.size ||m.atendimentos.some((id) => !ids.has(id)));
    const existeDestino = base.coordenadores.some((c) => c.id === m.paraCoordenadorId);
    if (!existeDestino || m.deCoordenadorId === m.paraCoordenadorId || ids.size === 0 || mudouDesdeAProposta) {
      invalidos.push(m);
      continue;
    }
    atendimentos = atendimentos.map((a) => (ids.has(a.id) ? { ...a, coordenador: m.paraCoordenadorId } : a));
  }
  return { base: { ...base, atendimentos }, invalidos };
}

export interface ComparacaoCoordenador {
  coordenadorId: number;
  nome: string;
  antes: ResultadoCoordenador;
  depois: ResultadoCoordenador;
  /** Diferença do ICA exibido (depois − antes). */
  variacao: number;
  mudouEstrato: boolean;
}

function comparar(antes: ResultadoEquipe, depois: ResultadoEquipe): ComparacaoCoordenador[] {
  const linhas: ComparacaoCoordenador[] = [];
  for (const a of antes.coordenadores) {
    const d = depois.coordenadores.find((x) => x.coordenador.id === a.coordenador.id);
    if (!d) continue;
    linhas.push({
      coordenadorId: a.coordenador.id,
      nome: a.coordenador.nome,
      antes: a,
      depois: d,
      variacao: d.conta.icaExibido - a.conta.icaExibido,
      mudouEstrato: a.conta.estrato !== d.conta.estrato,
    });
  }
  return linhas;
}

export interface ResultadoSimulacao {
  antes: ResultadoEquipe;
  depois: ResultadoEquipe;
  /** Os coordenadores de origem e de destino dos movimentos, na ordem em que aparecem. */
  envolvidos: ComparacaoCoordenador[];
  /** Todos que mudam de estrato (a média da equipe pode mexer com quem não foi movido). */
  mudancasDeEstrato: ComparacaoCoordenador[];
  dispersaoAntes: Dispersao;
  dispersaoDepois: Dispersao;
  movimentosInvalidos: Movimento[];
  baseDepois: BaseIca;
}

export function simularRemanejamento(base: BaseIca, pesos: Pesos, movimentos: readonly Movimento[]): ResultadoSimulacao {
  const antes = calcularEquipe(base, pesos);
  const { base: baseDepois, invalidos } = aplicarMovimentos(base, movimentos);
  const depois = calcularEquipe(baseDepois, pesos);
  const linhas = comparar(antes, depois);
  const ids: number[] = [];
  for (const m of movimentos) {
    if (invalidos.includes(m)) continue;
    for (const id of [m.deCoordenadorId, m.paraCoordenadorId]) if (!ids.includes(id)) ids.push(id);
  }
  return {
    antes,
    depois,
    envolvidos: ids.flatMap((id) => linhas.filter((l) => l.coordenadorId === id)),
    mudancasDeEstrato: linhas.filter((l) => l.mudouEstrato),
    dispersaoAntes: antes.dispersao,
    dispersaoDepois: depois.dispersao,
    movimentosInvalidos: invalidos,
    baseDepois,
  };
}

export interface ComparativoPesos {
  a: ResultadoEquipe;
  b: ResultadoEquipe;
  /** `antes` = versão A, `depois` = versão B. */
  linhas: ComparacaoCoordenador[];
  mudaramDeEstrato: ComparacaoCoordenador[];
}

export function compararPesos(base: BaseIca, pesosA: Pesos, pesosB: Pesos): ComparativoPesos {
  const a = calcularEquipe(base, pesosA);
  const b = calcularEquipe(base, pesosB);
  const linhas = comparar(a, b);
  return { a, b, linhas, mudaramDeEstrato: linhas.filter((l) => l.mudouEstrato) };
}

// ---------------------------------------------------------------- alertas (PDF, seção 6)

export type TipoAlerta =
  | 'sobrecarga'
  | 'sem_municipios'
  | 'contrato_sem_coordenador'
  | 'dado_incompleto'
  | 'dado_improvavel'
  | 'fora_da_meta';

export interface Alerta {
  id: string;
  tipo: TipoAlerta;
  titulo: string;
  detalhe: string;
  /** Quem receberia o aviso na versão real (no protótipo, nada é enviado). */
  quemReceberia: string[];
  quando: string;
  coordenadorId: number | null;
  municipioId: number | null;
}

export interface OpcoesAlertas {
  gerencias: readonly Gerencia[];
  pessoas: readonly Pessoa[];
  /** Para pôr a coleção no título do "contrato sem coordenador" (dois no mesmo município não ficam iguais). */
  colecoes?: readonly Colecao[];
  /** Retrato anterior: com ele, "entra em Sobrecarga" só para quem não estava. */
  anterior?: ResultadoEquipe | undefined;
}

export function gerarAlertas(base: BaseIca, resultado: ResultadoEquipe, opcoes: OpcoesAlertas): Alerta[] {
  const alertas: Alerta[] = [];
  const gestoraTecnica = (c: Coordenador): string => {
    const g = opcoes.gerencias.find((x) => x.id === c.gerencia);
    const p = g ? opcoes.pessoas.find((x) => x.id === g.gestora_tecnica) : undefined;
    return p ? `Gestora técnica (${p.nome})` : 'Gestora técnica';
  };
  const estavaEmSobrecarga = (id: number): boolean =>
    opcoes.anterior?.coordenadores.find((r) => r.coordenador.id === id)?.conta.estrato === 'sobrecarga';

  for (const r of resultado.coordenadores) {
    const c = r.coordenador;
    const ica = r.conta.icaExibido;
    if (r.conta.estrato === 'sobrecarga' && !estavaEmSobrecarga(c.id)) {
      alertas.push({
        id: `sobrecarga-${c.id}`,
        tipo: 'sobrecarga',
        titulo: opcoes.anterior ? `${c.nome} entrou em Sobrecarga (${ica})` : `${c.nome} está em Sobrecarga (${ica})`,
        detalhe: 'ICA de 130 ou mais: prioridade para redistribuir ou reforçar a equipe.',
        quemReceberia: ['SPE', gestoraTecnica(c), 'Líder do NFP'],
        quando: 'No recálculo',
        coordenadorId: c.id,
        municipioId: null,
      });
    }
    if (r.semMunicipios) {
      alertas.push({
        id: `sem-municipios-${c.id}`,
        tipo: 'sem_municipios',
        titulo: `${c.nome} está sem municípios`,
        detalhe: 'Nenhum município ativo na carteira: ICA 0, fora da média da equipe.',
        quemReceberia: ['SPE', 'Líder do NFP'],
        quando: 'No recálculo',
        coordenadorId: c.id,
        municipioId: null,
      });
    } else if (!r.conta.dentroDaMeta) {
      alertas.push({
        id: `fora-da-meta-${c.id}`,
        tipo: 'fora_da_meta',
        titulo: `${c.nome} está fora da meta (${ica})`,
        detalhe: `A meta é ICA entre ${META_ICA.minimo} e ${META_ICA.maximo}.`,
        quemReceberia: ['SPE'],
        quando: 'No recálculo semestral',
        coordenadorId: c.id,
        municipioId: null,
      });
    }
    if (r.dadoIncompleto) {
      alertas.push({
        id: `dado-incompleto-${c.id}`,
        tipo: 'dado_incompleto',
        titulo: `Dado incompleto na carteira de ${c.nome}`,
        detalhe: `${r.motivosIncompleto.join(' ')} O ICA fica subestimado.`,
        quemReceberia: ['Gestora operacional'],
        quando: 'No cadastro e antes da publicação',
        coordenadorId: c.id,
        municipioId: null,
      });
    }
    if (r.valoresImprovaveis.length > 0) {
      alertas.push({
        id: `dado-improvavel-${c.id}`,
        tipo: 'dado_improvavel',
        titulo: `Valor improvável na carteira de ${c.nome}`,
        detalhe: `${r.valoresImprovaveis.join(' ')} Conferir antes da publicação.`,
        quemReceberia: ['Gestora operacional'],
        quando: 'No cadastro e antes da publicação',
        coordenadorId: c.id,
        municipioId: null,
      });
    }
  }

  for (const a of resultado.contratosSemCoordenador) {
    const m = base.municipios.find((x) => x.id === a.municipio);
    const colecao = opcoes.colecoes?.find((x) => x.id === a.projeto_geral)?.nome ?? `coleção ${a.projeto_geral}`;
    alertas.push({
      id: `sem-coordenador-${a.id}`,
      tipo: 'contrato_sem_coordenador',
      titulo: `Contrato sem coordenador em ${m ? `${m.nome}-${m.uf}` : `município ${a.municipio}`} (${colecao})`,
      detalhe: 'Novo contrato sem coordenador definido.',
      quemReceberia: ['Gestora operacional', 'SPE'],
      quando: 'No cadastro',
      coordenadorId: null,
      municipioId: a.municipio,
    });
  }

  const ordem: TipoAlerta[] = [
    'sobrecarga',
    'sem_municipios',
    'contrato_sem_coordenador',
    'dado_incompleto',
    'dado_improvavel',
    'fora_da_meta',
  ];
  return alertas.sort((x, y) => ordem.indexOf(x.tipo) - ordem.indexOf(y.tipo));
}
