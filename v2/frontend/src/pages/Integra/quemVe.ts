/**
 * Quem vê cada tela da Integra na versão real: a matriz de cargos × telas.
 *
 * Fonte: o mapa dos cargos de 24/11/2026 (documentos de requisitos do ICA e do Semáforo, ata de 23/11) e
 * as decisões do dono 19 a 22 e 29 (as de 25/11, 30 a 57, entram em `DECIDIDO`). No protótipo vale outra
 * regra (decisão Q8): quem entra na Integra vê tudo. Esta matriz alimenta a seção "Quem vê o quê na versão real" da tela "Para validar no dia 7" e o
 * aviso que cada tela pode mostrar no topo (`QUEM_VE[tela].aviso`).
 *
 * Só papéis, nunca nomes de pessoa: a ata veio de transcrição automática e erra os nomes.
 */

export type Papel = 'spe' | 'operacional' | 'pedagogica' | 'lider' | 'coordenador' | 'comercial' | 'diretoria' | 'superusuario';

/** O que o papel faz na tela. */
export type Acao = 've' | 'propoe' | 'aplica' | 'registra' | 'nada';

/** Perguntas do mapa ainda sem resposta do dono. */
export type IdPergunta = 'P1' | 'P2-painel' | 'P3' | 'P6' | 'P8a' | 'P8b' | 'P9' | 'P10';

export interface Celula {
  /** Ausente quando tudo depende da pergunta em aberto. */
  faz?: Acao;
  aberta?: IdPergunta;
  /** Recorte ou detalhe, em linguagem simples. */
  nota?: string;
  /** Número da decisão do dono que fixou esta célula. */
  decisao?: number;
  /**
   * Age por fora, sem abrir esta tela: registra numa tela à parte ou por link, ou vê o mesmo dado em outra tela.
   * Fica fora de "quem vê esta tela".
   */
  foraDaTela?: boolean;
}

export type Modulo = 'ICA' | 'Semáforo' | 'Deslocamento' | 'DFF';

/** ICA: os caminhos de `ica/IcaRoutes.tsx` (`painel` é o índice, `coordenador` a ficha). */
export type ChaveTela =
  | 'painel'
  | 'coordenador'
  | 'simulador'
  | 'pesos'
  | 'gerencias'
  | 'comparativo'
  | 'historico'
  | 'alertas'
  | 'comite'
  | 'municipio'
  | 'gestora'
  | 'pesquisa'
  | 'lider'
  | 'relatorio-mensal'
  | 'deslocamento'
  | 'dff';

export interface TelaQuemVe {
  modulo: Modulo;
  titulo: string;
  quem: Record<Papel, Celula>;
  /** "Na versão real, quem vê esta tela: …" */
  aviso: string;
}

export const PAPEIS: readonly { chave: Papel; nome: string; naFrase: string }[] = [
  { chave: 'spe', nome: 'SPE', naFrase: 'SPE' },
  { chave: 'operacional', nome: 'Gestão Operacional', naFrase: 'Gestão Operacional' },
  { chave: 'pedagogica', nome: 'Gestora pedagógica', naFrase: 'gestoras pedagógicas' },
  { chave: 'lider', nome: 'Líder do NFP', naFrase: 'Líder do NFP' },
  { chave: 'coordenador', nome: 'Coordenador', naFrase: 'coordenadores' },
  { chave: 'comercial', nome: 'Relacionamento e Comercial', naFrase: 'Relacionamento e Comercial' },
  { chave: 'diretoria', nome: 'Diretoria', naFrase: 'Diretoria' },
  { chave: 'superusuario', nome: 'Superusuário', naFrase: 'superusuários' },
];

export const ACOES: Record<Acao, string> = {
  ve: 'Vê',
  propoe: 'Propõe',
  aplica: 'Aplica',
  registra: 'Registra',
  nada: 'Nada',
};

export const PERGUNTAS_EM_ABERTO: readonly { id: IdPergunta; rotulo: string; pergunta: string; porque?: string }[] = [
  {
    id: 'P1',
    rotulo: 'P1',
    pergunta:
      'Entre as 5 gerentes da Superintendência, quem é gestora pedagógica e quem é a Líder do NFP? E a Líder ganha uma marca no sistema para ver o que é só dela (histórico do ICA, indicadores da Líder e momento reservado)?',
  },
  {
    id: 'P2-painel',
    rotulo: 'P2 (complemento)',
    pergunta:
      'A Gestão Operacional vê os painéis do ICA e a ficha do município no Semáforo (sem o momento reservado)?',
    porque: 'A decisão 19 separou as gerências, mas não disse se ela vê os painéis.',
  },
  {
    id: 'P3',
    rotulo: 'P3',
    pergunta: 'Quando e como a aprovação das solicitações de evento passa para a Gestão Operacional?',
  },
  {
    id: 'P6',
    rotulo: 'P6',
    pergunta:
      'Onde fica anotado quem é a gestora de referência de cada município e a qual gestora cada coordenador responde? Quem pode trocar? Um coordenador pode ser referência de município?',
  },
  {
    id: 'P8a',
    rotulo: 'P8a',
    pergunta: 'A DFF continua como ferramenta à parte? E de onde vem a lista de quais formadores cada coordenador acompanha?',
  },
  {
    id: 'P8b',
    rotulo: 'P8b',
    pergunta: 'Na versão real, a Diretoria entra na Integra? Se sim, vê só o ICA, ou o ICA e o Semáforo?',
  },
  {
    id: 'P9',
    rotulo: 'P9',
    pergunta: 'Quem aprova as solicitações da Superintendência é sempre quem é gestora na Integra?',
    porque: 'Hoje as duas coisas saem do mesmo vínculo: mudar uma muda a outra.',
  },
  {
    id: 'P10',
    rotulo: 'P10',
    pergunta: 'Na Avaliação do Coordenador, quem vê a avaliação de cada coordenador: só a gestora dele, ou todas as gestoras?',
  },
];

export const DECIDIDO: readonly { numero: number; texto: string }[] = [
  {
    numero: 19,
    texto:
      'SPE e Gestão Operacional são duas gerências, cada uma com direitos próprios. A Gestão Operacional não mexe em pesos nem vê o momento reservado.',
  },
  {
    numero: 20,
    texto:
      'No remanejamento do ICA, a gestora pedagógica propõe e a SPE aplica. O histórico guarda quem propôs e quem aplicou. A Líder do NFP só consulta.',
  },
  {
    numero: 21,
    texto:
      'O coordenador não entra na Integra e não vê o ICA, nem a própria ficha. O relatório mensal e as tarefas dele no amarelo ficam numa tela à parte do sistema.',
  },
  {
    numero: 22,
    texto: 'Relacionamento, Comercial e distribuidores registram ocorrências por link, sem conta. O distribuidor registra pelo Comercial.',
  },
  {
    numero: 29,
    texto: 'Deslocamento e a tela de viagens viram um módulo só, com os tempos de referência no cadastro de municípios.',
  },
  // Respostas do dono de 25/11/2026 às perguntas 28 a 41 do guia (`liberacao/relatorios/integra_decisoes_2026-11-24.md`).
  { numero: 30, texto: 'A cor sai do número exato, não do arredondado: 3,95 é amarelo; 89,5% é amarelo. A tela mostra 2 casas.' },
  { numero: 31, texto: 'Nota de recomendação (NPS): a tela mostra a maior nota, a menor e a média; a cor sai da média.' },
  { numero: 32, texto: 'As ocorrências contam desde a 1ª formação do ano no município e zeram no ano seguinte; o histórico fica.' },
  {
    numero: 33,
    texto: 'Prazos em dias úteis (segunda a sexta): reunião com a Secretaria em 5, plano de ação em 15, devolutiva em 30.',
  },
  { numero: 34, texto: 'O "contato em 48 h" vira 2 dias úteis.' },
  { numero: 35, texto: '"No bimestre" e "no semestre" contam a partir da publicação da cor (2 e 6 meses).' },
  { numero: 36, texto: 'As tarefas do vermelho ficam com as duas gestoras juntas (a de referência e a pedagógica).' },
  { numero: 37, texto: 'O contato inicial do vermelho é com o articulador municipal.' },
  {
    numero: 38,
    texto: 'Vermelho imediato muda a cor oficial na hora, e as tarefas começam; o Comitê confirma ou desfaz depois.',
  },
  { numero: 39, texto: 'Três amarelos no mesmo ciclo também viram vermelho na hora.' },
  { numero: 40, texto: 'O Comitê ordinário se reúne em data marcada pela SPE a cada ciclo.' },
  { numero: 41, texto: 'O Comitê extraordinário é convocado a critério da SPE.' },
  {
    numero: 42,
    texto: 'Se o Comitê desfaz um vermelho, as tarefas abertas dele ficam "canceladas pelo Comitê"; as feitas continuam registradas.',
  },
  { numero: 43, texto: 'A mesma cor confirmada de novo reabre todas as tarefas da cor.' },
  { numero: 44, texto: 'O amarelo "em recuperação" recebe as tarefas do amarelo.' },
  { numero: 45, texto: 'Volta ao verde depois de 2 ciclos fechados seguidos sem alerta, contados da cor publicada.' },
  {
    numero: 46,
    texto:
      'A palavra certa é "projeto": cada projeto da Aprender Editora contratado pelo município tem o seu coordenador, as suas formações e o seu relatório mensal. Cada projeto tem o seu cronograma e a sua cor; na cor do município entra o pior. O critério de cada projeto o dono define depois.',
  },
  { numero: 47, texto: 'Formação adiada de comum acordo é só observação: não muda o número do cronograma.' },
  {
    numero: 48,
    texto: 'A reunião de escuta é marcada antes, e a ata registrada até 5 dias úteis depois; passado o prazo, "ata atrasada".',
  },
  { numero: 49, texto: 'Medir a convergência entre a pesquisa e as ocorrências e listar os municípios em que elas divergem.' },
  { numero: 50, texto: 'Medir o tempo de resposta às ocorrências: a ocorrência guarda quando foi respondida; a meta é 48 h.' },
  {
    numero: 51,
    texto: 'A pesquisa é por projeto: cada projeto pode ter o seu articulador; se for o mesmo, ele responde uma por projeto.',
  },
  { numero: 52, texto: 'Manter o aviso quando o município piora para amarelo.' },
  { numero: 53, texto: 'Valem os 23 municípios por terra da lista do relatório.' },
  { numero: 54, texto: 'Craíbas-AL é "Longo" (18h00, pelo limite do próprio relatório).' },
  { numero: 55, texto: 'O tempo do meio é 17h45, o número do relatório.' },
  {
    numero: 56,
    texto: 'Amigos do Bem segue o sistema: o local é o de cada formação (pode ser em AL, CE ou PE).',
  },
  {
    numero: 57,
    texto: 'Zerar uma contagem nunca apaga dado: todo o histórico de todas as ferramentas e do sistema fica guardado.',
  },
];

// ---------------------------------------------------------------- a matriz

const NADA: Celula = { faz: 'nada' };

/** Papel não citado não faz nada na tela. */
function quem(celulas: Partial<Record<Papel, Celula>>): Record<Papel, Celula> {
  return Object.fromEntries(PAPEIS.map((p) => [p.chave, celulas[p.chave] ?? NADA])) as Record<Papel, Celula>;
}

const COORDENADOR_FORA: Celula = { faz: 'nada', decisao: 21 };
const DIRETORIA_EM_ABERTO: Celula = { aberta: 'P8b' };
const OPERACIONAL_EM_ABERTO: Celula = { aberta: 'P2-painel' };
const SUPER_VE: Celula = { faz: 've' };

interface Linha {
  modulo: Modulo;
  titulo: string;
  quem: Record<Papel, Celula>;
  /** Frase que completa o aviso. */
  complemento?: string;
}

const LINHAS: Record<ChaveTela, Linha> = {
  painel: {
    modulo: 'ICA',
    titulo: 'Painel',
    quem: quem({
      spe: { faz: 've' },
      operacional: OPERACIONAL_EM_ABERTO,
      pedagogica: { faz: 've' },
      lider: { faz: 've' },
      coordenador: COORDENADOR_FORA,
      diretoria: DIRETORIA_EM_ABERTO,
      superusuario: SUPER_VE,
    }),
  },
  coordenador: {
    modulo: 'ICA',
    titulo: 'Ficha do coordenador',
    quem: quem({
      spe: { faz: 've' },
      operacional: OPERACIONAL_EM_ABERTO,
      pedagogica: { faz: 've' },
      lider: { faz: 've' },
      coordenador: { faz: 'nada', nota: 'nem a própria ficha', decisao: 21 },
      diretoria: DIRETORIA_EM_ABERTO,
      superusuario: SUPER_VE,
    }),
  },
  simulador: {
    modulo: 'ICA',
    titulo: 'Simulador',
    quem: quem({
      spe: { faz: 'aplica', nota: 'aplica o remanejamento', decisao: 20 },
      operacional: { faz: 'nada', decisao: 19 },
      pedagogica: { faz: 'propoe', nota: 'simula e propõe o remanejamento', decisao: 20 },
      lider: { faz: 've', nota: 'só consulta', decisao: 20 },
      coordenador: COORDENADOR_FORA,
      superusuario: { faz: 'aplica' },
    }),
  },
  pesos: {
    modulo: 'ICA',
    titulo: 'Pesos e faixas',
    quem: quem({
      spe: { faz: 'aplica', nota: 'só a SPE' },
      operacional: { faz: 'nada', decisao: 19 },
      coordenador: COORDENADOR_FORA,
      superusuario: { faz: 'aplica' },
    }),
  },
  gerencias: {
    modulo: 'ICA',
    titulo: 'Por gerência',
    quem: quem({
      spe: { faz: 've' },
      operacional: OPERACIONAL_EM_ABERTO,
      pedagogica: { faz: 've' },
      lider: { faz: 've' },
      coordenador: COORDENADOR_FORA,
      diretoria: DIRETORIA_EM_ABERTO,
      superusuario: SUPER_VE,
    }),
  },
  comparativo: {
    modulo: 'ICA',
    titulo: 'Comparativo',
    quem: quem({
      spe: { faz: 've', nota: 'só a SPE' },
      coordenador: COORDENADOR_FORA,
      superusuario: SUPER_VE,
    }),
  },
  historico: {
    modulo: 'ICA',
    titulo: 'Histórico',
    quem: quem({
      spe: { faz: 've' },
      pedagogica: { aberta: 'P1', nota: 'pelo documento, não vê; sem a marca de Líder, abre para todas ou fica só com a SPE' },
      lider: { faz: 've', aberta: 'P1' },
      coordenador: COORDENADOR_FORA,
      superusuario: SUPER_VE,
    }),
  },
  alertas: {
    modulo: 'ICA',
    titulo: 'Alertas e exportação',
    quem: quem({
      spe: { faz: 've', nota: 'todos os alertas' },
      pedagogica: { faz: 've', aberta: 'P6', nota: 'só a Sobrecarga dos coordenadores que respondem a ela' },
      coordenador: COORDENADOR_FORA,
      superusuario: SUPER_VE,
    }),
  },
  comite: {
    modulo: 'Semáforo',
    titulo: 'Comitê',
    quem: quem({
      spe: {
        faz: 'aplica',
        nota: 'conduz, confirma ou desfaz a cor e publica; marca a data do Comitê ordinário e convoca o extraordinário',
        decisao: 41,
      },
      operacional: { faz: 'aplica', nota: 'conduz com a SPE', decisao: 19 },
      pedagogica: { faz: 've', nota: 'participa do Comitê' },
      lider: { aberta: 'P1', nota: 'o documento não a põe neste painel' },
      coordenador: COORDENADOR_FORA,
      diretoria: DIRETORIA_EM_ABERTO,
      superusuario: { faz: 'aplica' },
    }),
  },
  municipio: {
    modulo: 'Semáforo',
    titulo: 'Ficha do município',
    quem: quem({
      spe: { faz: 've', nota: 'inclusive o momento reservado' },
      operacional: { aberta: 'P2-painel', nota: 'nunca o momento reservado', decisao: 19 },
      pedagogica: {
        faz: 'registra',
        aberta: 'P6',
        nota: 'vê todos os municípios; escuta e momento reservado só na própria carteira',
      },
      lider: { faz: 've', aberta: 'P1', nota: 'o momento reservado depende da marca de Líder' },
      coordenador: COORDENADOR_FORA,
      diretoria: DIRETORIA_EM_ABERTO,
      superusuario: SUPER_VE,
    }),
  },
  gestora: {
    modulo: 'Semáforo',
    titulo: 'Painel da gestora',
    quem: quem({
      spe: { faz: 've' },
      pedagogica: { faz: 'registra', aberta: 'P6', nota: 'tarefas de cada cor na própria carteira' },
      lider: { faz: 've' },
      coordenador: COORDENADOR_FORA,
      superusuario: SUPER_VE,
    }),
  },
  pesquisa: {
    modulo: 'Semáforo',
    titulo: 'Pesquisa do articulador',
    quem: quem({
      spe: { faz: 've' },
      pedagogica: { faz: 'registra', aberta: 'P6', nota: 'envia o link aos municípios da própria carteira' },
      coordenador: { faz: 'nada', nota: 'nunca gera o link', decisao: 21 },
      superusuario: SUPER_VE,
    }),
    complemento: 'O articulador responde por link, sem conta, uma vez por projeto.',
  },
  lider: {
    modulo: 'Semáforo',
    titulo: 'Indicadores da Líder',
    quem: quem({
      spe: { faz: 've' },
      pedagogica: { aberta: 'P1', nota: 'sem a marca de Líder, abre para todas ou fica só com a SPE' },
      lider: { faz: 've', aberta: 'P1' },
      coordenador: COORDENADOR_FORA,
      superusuario: SUPER_VE,
    }),
  },
  'relatorio-mensal': {
    modulo: 'Semáforo',
    titulo: 'Relatório mensal e formulários',
    quem: quem({
      spe: { faz: 've' },
      pedagogica: {
        faz: 'registra',
        aberta: 'P6',
        nota: 'observação de formação (pelo PDF do Semáforo; se ela nasce aqui ou na DFF, decidir no dia 7); lê o relatório dos coordenadores que respondem a ela',
      },
      coordenador: {
        faz: 'registra',
        nota: 'o relatório mensal, numa tela à parte, fora da Integra',
        decisao: 21,
        foraDaTela: true,
      },
      comercial: {
        faz: 'registra',
        nota: 'ocorrência por link, sem conta; o distribuidor registra pelo Comercial',
        decisao: 22,
        foraDaTela: true,
      },
      superusuario: { faz: 'registra' },
    }),
    complemento:
      'O coordenador preenche o relatório mensal numa tela à parte, fora da Integra; o Relacionamento e o Comercial registram a ocorrência por link, sem conta.',
  },
  deslocamento: {
    modulo: 'Deslocamento',
    titulo: 'Tempos de deslocamento',
    quem: quem({
      spe: { faz: 'aplica', nota: 'cuida do tempo de referência de cada município', decisao: 29 },
      pedagogica: { faz: 've', nota: 'o tempo de cada município, pela ficha do ICA', foraDaTela: true },
      lider: { faz: 've', nota: 'o tempo de cada município, pela ficha do ICA', foraDaTela: true },
      coordenador: {
        faz: 'nada',
        nota: 'registra as próprias viagens na tela de viagens do sistema, fora da Integra, com o tempo esperado ao lado do registrado',
        decisao: 21,
      },
      superusuario: { faz: 'aplica' },
    }),
    complemento:
      'Esta tela e a tela de viagens do sistema viram um módulo só. As gestoras pedagógicas e a Líder do NFP veem o tempo de cada município pela ficha do ICA. O coordenador registra as próprias viagens na tela de viagens, fora da Integra.',
  },
  dff: {
    modulo: 'DFF',
    titulo: 'DFF (no link atual)',
    quem: quem({
      pedagogica: { aberta: 'P8a', nota: 'filtrar e mandar o link aos formadores de cada coordenador' },
      coordenador: { faz: 'registra', nota: 'avalia os formadores' },
    }),
    complemento: 'A DFF tem acesso próprio, fora do Aprender Sistema.',
  },
};

/** "a", "a e b", "a, b e c". */
function juntar(itens: string[]): string {
  return itens.length <= 1 ? itens.join('') : `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`;
}

function montarAviso({ quem: celulas, complemento }: Linha): string {
  const fazAlgo = PAPEIS.filter((p) => (celulas[p.chave].faz ?? 'nada') !== 'nada' && !celulas[p.chave].foraDaTela).map(
    (p) => p.naFrase,
  );
  const emAberto = PAPEIS.filter((p) => celulas[p.chave].faz === undefined).map((p) => p.naFrase);
  const partes = [`Na versão real, quem vê esta tela: ${juntar(fazAlgo)}.`];
  if (emAberto.length > 0) partes.push(`Em aberto, para decidir no dia 7: ${juntar(emAberto)}.`);
  if (complemento) partes.push(complemento);
  return partes.join(' ');
}

export const TELAS = Object.keys(LINHAS) as ChaveTela[];

export const QUEM_VE: Record<ChaveTela, TelaQuemVe> = Object.fromEntries(
  TELAS.map((t) => [t, { modulo: LINHAS[t].modulo, titulo: LINHAS[t].titulo, quem: LINHAS[t].quem, aviso: montarAviso(LINHAS[t]) }]),
) as Record<ChaveTela, TelaQuemVe>;
