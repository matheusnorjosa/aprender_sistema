/**
 * Quem vê cada tela da Integra na versão real: a matriz de cargos × telas.
 *
 * Fonte: o mapa dos cargos de 24/11/2026 (documentos de requisitos do ICA e do Semáforo, ata de 23/11) e
 * as decisões do dono 19 a 22 e 29 (as de 25/11 e 26/11, 30 a 94, entram em `DECIDIDO`). No protótipo vale outra
 * regra (decisão Q8): quem entra na Integra vê tudo. Esta matriz alimenta a seção "Quem vê o quê na versão real" da tela "Para validar no dia 7" e o
 * aviso que cada tela pode mostrar no topo (`QUEM_VE[tela].aviso`).
 *
 * Só papéis, nunca nomes de pessoa: a ata veio de transcrição automática e erra os nomes.
 */

export type Papel = 'spe' | 'operacional' | 'pedagogica' | 'lider' | 'coordenador' | 'comercial' | 'diretoria' | 'superusuario';

/** O que o papel faz na tela. */
export type Acao = 've' | 'propoe' | 'aplica' | 'registra' | 'nada';

/** Perguntas do mapa ainda sem resposta do dono (as outras foram respondidas em 26/11). */
export type IdPergunta = 'P1' | 'P11' | 'P12' | 'P13' | 'P14';

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
  // Decisão 87: os cargos na Integra se chamam Gerente Operacional e Gerente Pedagógica.
  { chave: 'operacional', nome: 'Gerente Operacional', naFrase: 'Gerente Operacional' },
  { chave: 'pedagogica', nome: 'Gerente Pedagógica', naFrase: 'Gerentes Pedagógicas' },
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
    pergunta: 'Entre as 5 gerentes da Superintendência, quem é gestora pedagógica e quem é a Líder do NFP?',
    porque: 'A marca de cargo na Integra já foi decidida (decisão 87); falta dizer quem fica com cada marca.',
  },
  {
    id: 'P11',
    rotulo: 'P11',
    pergunta: 'A Líder do NFP vê o Comitê?',
    porque: 'O documento de 24/11 não a põe neste painel, e nenhuma decisão de 26/11 falou do Comitê.',
  },
  {
    id: 'P12',
    rotulo: 'P12',
    pergunta: 'A gestora pedagógica vê o Histórico do ICA e os Indicadores da Líder?',
    porque:
      'Pelo documento de 24/11, essas duas telas são da SPE e da Líder do NFP. A decisão 87 deu a marca de cargo, mas não disse o que cada marca vê nelas. O histórico semestral do ICA também aparece na Ficha do coordenador e no Painel, que a gestora pedagógica vê.',
  },
  {
    id: 'P13',
    rotulo: 'P13',
    pergunta: 'O superusuário (acesso técnico do sistema) lê o momento reservado?',
    porque:
      'A decisão 78 diz que leem a gestora de referência principal, a Líder do NFP e a SPE, e ninguém mais. O superusuário vê a Ficha do município.',
  },
  {
    id: 'P14',
    rotulo: 'P14',
    pergunta: 'Quem faz a observação de formação do amarelo, e quem recebe o alerta do prazo dela?',
    porque:
      'O PDF do Semáforo põe a observação entre as tarefas do amarelo, com a gestora de referência e os coordenadores (seção 5), e na coleta 6 diz que quem registra é a gestora pedagógica. A decisão 94 só diz que a observação fica na DFF. É o mesmo ponto do cartão "Observação de formação do amarelo", acima.',
  },
];

export const DECIDIDO: readonly { numero: number; texto: string }[] = [
  {
    numero: 19,
    texto:
      'A SPE e a Gestão Operacional são duas gerências, cada uma com direitos próprios. A Gerente Operacional não mexe em pesos nem vê o momento reservado.',
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
  // Respostas do dono de 26/11/2026 às perguntas 4 a 8, 10 a 18, 20 a 27, 36 e 37 do guia (mesmo arquivo).
  { numero: 58, texto: 'A Gerente Operacional mantém a carteira; na ausência dela, a SPE registra.' },
  {
    numero: 59,
    texto:
      'Frente é cada ano (segmento) de cada coleção no município, como foi dito na reunião de 23/11 (Novo Lendo 1º e 2º ano, Tema 1º e 2º ano e Infantil 1, 2 e 3 = 7 frentes), e não município × coleção, como no PDF.',
  },
  {
    numero: 60,
    texto: 'O calendário da carteira de 2027 (quando fecha e quando começa o 2027.1) é definido pela SPE dentro do sistema.',
  },
  {
    numero: 61,
    texto: 'A lista de gestora de referência de cada município: a Gerente Operacional monta e propõe a troca; a SPE aprova.',
  },
  { numero: 62, texto: 'No município com gestora principal e compartilhada, só a principal lê o momento reservado.' },
  { numero: 63, texto: 'Coordenador não pode ser referência de município: a referência é sempre uma gestora.' },
  {
    numero: 64,
    texto: 'O vínculo de cada coordenador com a sua gestora pedagógica é mantido pela Gerente Operacional, como diz o PDF do ICA.',
  },
  { numero: 65, texto: 'As faixas do ICA são fixas, como no protótipo.' },
  { numero: 66, texto: 'A gestora da gerência AMMA fica com os 29 municípios sozinha.' },
  { numero: 67, texto: 'A Diretoria não entra na Integra com login próprio (como hoje, decisão 17).' },
  {
    numero: 68,
    texto:
      'Depois da remodelagem das gerências, só a Gerente Operacional aprova os eventos da Superintendência. Isso muda o poder de aprovar no sistema inteiro: plano próprio, com a medição de quem perde, depois de 07/12.',
  },
  {
    numero: 69,
    texto:
      'O alerta de Sobrecarga sai a cada recálculo enquanto o coordenador continuar na faixa, para a SPE, a gestora pedagógica dele e a Líder do NFP.',
  },
  { numero: 70, texto: 'Coordenador sem municípios fica à parte, fora das faixas e da média, como no protótipo.' },
  { numero: 71, texto: 'Ao aplicar um remanejamento, a SPE escolhe a data em que ele passa a valer.' },
  { numero: 72, texto: 'A SPE confere o cálculo, e o ICA é publicado em até 5 dias úteis depois da conferência.' },
  { numero: 73, texto: 'A gestora de referência manda o link da pesquisa ao articulador, sem o coordenador, como no PDF.' },
  { numero: 74, texto: 'A identificação do articulador na pesquisa é opcional.' },
  {
    numero: 75,
    texto: '"Não respondeu": 1 ciclo sem resposta deixa o indicador amarelo; 2 seguidos, vermelho, como no PDF.',
  },
  { numero: 76, texto: 'O articulador responde a pesquisa em até 10 dias úteis.' },
  { numero: 77, texto: 'O relatório mensal vence no 5º dia útil do mês seguinte.' },
  {
    numero: 78,
    texto: 'O momento reservado é lido pela gestora de referência principal, pela Líder do NFP e pela SPE; ninguém mais.',
  },
  { numero: 79, texto: 'Indicador sem dado fica fora da conta da cor, como no protótipo.' },
  {
    numero: 80,
    texto:
      'A tela à parte do coordenador mostra o resultado juntado da pesquisa dos seus projetos, sem o momento reservado e sem saber quem respondeu.',
  },
  {
    numero: 81,
    texto: 'O relatório mensal vem pré-preenchido com as formações do sistema; o coordenador confere e justifica.',
  },
  { numero: 82, texto: 'As visitas do relatório mensal vêm da Logística e do pedido de viagem (FRV).' },
  {
    numero: 83,
    texto: 'Os alertas chegam dentro do sistema e por e-mail institucional (o e-mail depende da TI da empresa).',
  },
  {
    numero: 84,
    texto:
      'Outras ferramentas entram só como botões de atalho para as plataformas delas, como a DFF. Por agora, Formar e Avaliar.',
  },
  { numero: 85, texto: 'O nome "Integra" e o item próprio no menu ficam.' },
  { numero: 86, texto: 'A Avaliação do Coordenador se chama "Tríade".' },
  {
    numero: 87,
    texto:
      'Cargo na Integra: as gerentes continuam com a mesma conta e a mesma gerência e ganham uma marca de cargo na Integra (Gerente Operacional, Gerente Pedagógica, Líder do NFP). A marca abre a Integra e define o que cada uma vê; aprovar eventos fica separado (decisão 68).',
  },
  { numero: 88, texto: 'A parte subjetiva da gerência na Tríade usa só os 4 níveis: a marcação de cada indicador.' },
  { numero: 89, texto: 'Na Tríade, a avaliação completa de um coordenador é vista pela gestora dele e pela SPE.' },
  {
    numero: 90,
    texto:
      'A Gerente Operacional vê os painéis (Painel e Ficha do ICA, Por gerência e ficha do município), sem o momento reservado e sem mexer em pesos.',
  },
  {
    numero: 91,
    texto:
      'As Gerentes Pedagógicas e a Líder do NFP veem o tempo de deslocamento só pela ficha do ICA; a tela do Deslocamento fica com a SPE.',
  },
  { numero: 92, texto: 'A DFF fica à parte, com um botão na Integra, até migrar para dentro do sistema.' },
  {
    numero: 93,
    texto: 'A lista de formadores de cada coordenador vem da DFF, e a gerente confirma, acrescenta ou tira, com registro de quem mudou.',
  },
  {
    numero: 94,
    texto: 'A observação de formação é registrada na DFF, junto do PDI; o Aprender Sistema lê de lá para o Semáforo.',
  },
];

// ---------------------------------------------------------------- a matriz

const NADA: Celula = { faz: 'nada' };

/** Papel não citado não faz nada na tela. */
function quem(celulas: Partial<Record<Papel, Celula>>): Record<Papel, Celula> {
  return Object.fromEntries(PAPEIS.map((p) => [p.chave, celulas[p.chave] ?? NADA])) as Record<Papel, Celula>;
}

const COORDENADOR_FORA: Celula = { faz: 'nada', decisao: 21 };
const DIRETORIA_FORA: Celula = { faz: 'nada', decisao: 67 };
const OPERACIONAL_VE: Celula = { faz: 've', decisao: 90 };
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
      operacional: OPERACIONAL_VE,
      pedagogica: { faz: 've' },
      lider: { faz: 've' },
      coordenador: COORDENADOR_FORA,
      diretoria: DIRETORIA_FORA,
      superusuario: SUPER_VE,
    }),
  },
  coordenador: {
    modulo: 'ICA',
    titulo: 'Ficha do coordenador',
    quem: quem({
      spe: { faz: 've' },
      operacional: OPERACIONAL_VE,
      pedagogica: { faz: 've' },
      lider: { faz: 've' },
      coordenador: { faz: 'nada', nota: 'nem a própria ficha', decisao: 21 },
      diretoria: DIRETORIA_FORA,
      superusuario: SUPER_VE,
    }),
  },
  simulador: {
    modulo: 'ICA',
    titulo: 'Simulador',
    quem: quem({
      spe: { faz: 'aplica', nota: 'aplica o remanejamento', decisao: 20 },
      operacional: { faz: 'nada', nota: 'se é ela quem grava na carteira: em aberto (cartão "Quem grava na carteira o remanejamento aplicado?")' },
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
      operacional: OPERACIONAL_VE,
      pedagogica: { faz: 've' },
      lider: { faz: 've' },
      coordenador: COORDENADOR_FORA,
      diretoria: DIRETORIA_FORA,
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
      pedagogica: { aberta: 'P12', nota: 'pelo documento de 24/11, não vê; confirmar no dia 7' },
      lider: { faz: 've', nota: 'pelo documento de 24/11' },
      coordenador: COORDENADOR_FORA,
      superusuario: SUPER_VE,
    }),
  },
  alertas: {
    modulo: 'ICA',
    titulo: 'Alertas e exportação',
    quem: quem({
      spe: { faz: 've', nota: 'todos os alertas' },
      pedagogica: { faz: 've', nota: 'só a Sobrecarga dos coordenadores que respondem a ela', decisao: 69 },
      operacional: { faz: 've', nota: 'recebe os alertas de dado incompleto, dado improvável e projeto sem coordenador' },
      lider: { faz: 've', nota: 'recebe o alerta de Sobrecarga (decisão 69) e o de coordenador sem municípios' },
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
      lider: { aberta: 'P11', nota: 'o documento não a põe neste painel' },
      coordenador: COORDENADOR_FORA,
      diretoria: DIRETORIA_FORA,
      superusuario: { faz: 'aplica' },
    }),
  },
  municipio: {
    modulo: 'Semáforo',
    titulo: 'Ficha do município',
    quem: quem({
      spe: { faz: 've', nota: 'inclusive o momento reservado' },
      operacional: { faz: 've', nota: 'nunca o momento reservado', decisao: 90 },
      pedagogica: {
        faz: 'registra',
        nota: 'vê todos os municípios; escuta só na própria carteira; o momento reservado, só a gestora de referência principal',
        decisao: 62,
      },
      lider: { faz: 've', nota: 'inclusive o momento reservado', decisao: 78 },
      coordenador: COORDENADOR_FORA,
      diretoria: DIRETORIA_FORA,
      superusuario: { faz: 've', aberta: 'P13', nota: 'o momento reservado: decidir no dia 7' },
    }),
    complemento:
      'O momento reservado só é lido pela gestora de referência principal do município, pela Líder do NFP e pela SPE (decisões 62 e 78).',
  },
  gestora: {
    modulo: 'Semáforo',
    titulo: 'Painel da gestora',
    quem: quem({
      spe: { faz: 've' },
      pedagogica: { faz: 'registra', nota: 'tarefas de cada cor na própria carteira' },
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
      pedagogica: { faz: 'registra', nota: 'a gestora de referência manda o link, sem o coordenador', decisao: 73 },
      coordenador: { faz: 'nada', nota: 'nunca gera o link', decisao: 73 },
      superusuario: SUPER_VE,
    }),
    complemento: 'O articulador responde por link, sem conta, uma vez por projeto.',
  },
  lider: {
    modulo: 'Semáforo',
    titulo: 'Indicadores da Líder',
    quem: quem({
      spe: { faz: 've' },
      pedagogica: { aberta: 'P12', nota: 'pelo documento de 24/11, não vê; confirmar no dia 7' },
      lider: { faz: 've', nota: 'pelo documento de 24/11' },
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
        nota: 'a reunião de escuta e a ata na própria carteira; lê o relatório dos coordenadores que respondem a ela; a observação de formação fica na DFF (decisão 94)',
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
      pedagogica: { faz: 've', nota: 'o tempo de cada município, pela ficha do ICA', decisao: 91, foraDaTela: true },
      lider: { faz: 've', nota: 'o tempo de cada município, pela ficha do ICA', decisao: 91, foraDaTela: true },
      coordenador: {
        faz: 'nada',
        nota: 'registra as próprias viagens na tela de viagens do sistema, fora da Integra, com o tempo esperado ao lado do registrado',
        decisao: 21,
      },
      superusuario: { faz: 'aplica' },
    }),
    complemento:
      'Esta tela e a tela de viagens do sistema viram um módulo só. As Gerentes Pedagógicas e a Líder do NFP veem o tempo de cada município pela ficha do ICA. O coordenador registra as próprias viagens na tela de viagens, fora da Integra.',
  },
  dff: {
    modulo: 'DFF',
    titulo: 'DFF (no link atual)',
    quem: quem({
      pedagogica: {
        aberta: 'P14',
        nota: 'pelo PDF do Semáforo (coleta 6), registra a observação de formação; a observação fica na DFF (decisão 94)',
      },
      coordenador: { faz: 'registra', nota: 'avalia os formadores' },
    }),
    complemento:
      'A DFF tem acesso próprio, fora do Aprender Sistema, até migrar para dentro dele (decisão 92). A lista de formadores de cada coordenador vem da DFF, e a gerente confirma, acrescenta ou tira (decisão 93).',
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
