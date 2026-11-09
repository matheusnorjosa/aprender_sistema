/**
 * Dados de um evento da Nova Solicitação (um cartão da página) e as regras puras sobre eles.
 *
 * Fica fora do componente para a página e o cartão lerem a mesma coisa: o que é um evento em
 * branco, quando a pergunta de avaliar o formador vale e quem entra na checagem de agenda.
 */

import type { LookupItem } from '../../components/ComboBox';
import type { CoordenadorItem } from '../../components/CoordenadoresPicker';
import type { FormadorItem } from '../../components/FormadoresPicker';
import type { PreviewParticipant } from '../../hooks/useAvailabilityPreview';
import type { FluxoType, ID } from '../../types';

/** Item escolhido num ComboBox; o projeto traz também o que o lookup de projetos devolve. */
export type ComboBoxValue = LookupItem & {
  fluxo?: FluxoType;
  /** Projeto: a gerência usa a pergunta "pretende avaliar o formador?" (lookup de projetos). */
  pergunta_avaliar_formador?: boolean;
  /** Projeto: com o responsável vazio, quem cria é a responsável (lookup de projetos; regra do backend, PR 9). */
  responsavel_padrao?: boolean;
  /** Município: sem compra para o projeto (lookup com `marcar_sem_compra`); o evento vai para aprovação. */
  sem_compra?: boolean;
  /** Município (lookup com `marcar_sem_compra`): o projeto não tem compra em município nenhum e não recebe evento. */
  projeto_em_espera?: boolean;
};

/** Pedido do dono (03/11/2026): município sem compra pode, e o evento vai para aprovação. */
export const AVISO_SEM_COMPRA = 'Sem compra neste município para este projeto. O evento vai para aprovação.';

/** O mesmo texto do servidor (`compra_elegibilidade.MSG_PROJETO_EM_ESPERA`): esse par ele recusa. */
export const MSG_PROJETO_EM_ESPERA = 'Este projeto não tem compra em município nenhum: fica em espera até a compra entrar.';

/** A opção do município sem compra leva a marca na lista; o campo, depois de escolher, mostra só o nome. */
export function opcaoDoMunicipio(item: LookupItem): string {
  return item['sem_compra'] === true ? `${item.label} · sem compra` : item.label;
}

/** Formador escolhido (o `avaliavel` vem do lookup: função Formador sem a função Coordenador). */
export type ParticipantType = FormadorItem;

/** Quem cria (do /me): é o responsável quando nenhum outro é escolhido e o projeto aceita o vazio. */
export interface QuemCria {
  id: ID;
  nome: string;
}

/** Limite de eventos por envio (o mesmo `MAX_EVENTOS_LOTE` do servidor). Cada horário é um evento. */
export const MAX_EVENTOS = 10;
/** O texto dos botões de adicionar (evento e horário) quando o envio chega ao limite. */
export const TEXTO_DO_LIMITE = `Limite de ${MAX_EVENTOS} eventos por vez`;

/**
 * Um horário do evento (decisão do dono, 03/11/2026): cada um tem o seu dia, início, fim e pessoas, e
 * vira um evento separado no Google, como a planilha faz com manhã e tarde.
 */
export interface Horario {
  /** Identidade estável do horário na página (ids, React key e o item do lote); não se repete. */
  chave: number;
  inicio: string | null;
  fim: string | null;
  formadores: ParticipantType[];
  // A caixa "Coordenador(es)" (decisão do dono, 03/11/2026), na ordem de escolha: o 1º é o RESPONSÁVEL
  // (FK, #1666), os demais vão em `coord_acompanha_ids`. Vazia: o backend usa quem cria, se for coordenador.
  coordenadores: CoordenadorItem[];
  // Decisão do dono (05/10/2026): respostas Sim/Não; null = ainda não respondida.
  coordenadorAcompanha: boolean | null;
  pretendeAvaliar: boolean | null;
  formadorAvaliado: ID | null;
}

/** O que a pessoa preenche num evento: o que vale para todos os horários e os horários (pelo menos 1). */
export interface FormDataType {
  projeto: ComboBoxValue | null;
  /** O outro projeto do combo (#2036): sem principal; mesma gerência e mesmo fluxo do 1º. */
  projeto_2: ComboBoxValue | null;
  tipoEvento: ComboBoxValue | null;
  municipio: ComboBoxValue | null;
  horarios: Horario[];
  // Mais detalhes (opcionais)
  tipo: string;
  encontro: string;
  segmento: string;
  observacoes: string;
  local: string;
  // PR19: Modalidade online/presencial
  is_online: boolean;
}

/**
 * Ordem dos campos do cartão (os que valem para todos os horários) na tela: a do resumo e a do foco.
 * `horarios` é o lugar dos horários (cada um com a sua ordem, `ORDEM_DO_HORARIO`).
 */
export const ORDEM_DO_CARTAO = [
  'projeto',
  'projeto_2',
  'tipoEvento',
  // "Nº da formação" fica na 1ª linha do cartão, antes do Município (03/11/2026).
  'encontro',
  'municipio',
  'horarios',
  'tipo',
  'segmento',
  'local',
  'observacoes',
  'is_online',
];

/** Ordem dos campos de um horário na tela (a do resumo e a do foco). `horario` é o DateTimeRange (fora do Form). */
export const ORDEM_DO_HORARIO = [
  'horario',
  'formadores',
  'coordenadores',
  'coordenadorAcompanha',
  'pretendeAvaliar',
  'formadorAvaliado',
];

/** Um horário com o que é do evento: o que vai num item do lote (um evento no Google). */
export type EventoDeUmHorario = Omit<FormDataType, 'horarios'> & Omit<Horario, 'chave'>;

/** Horário em branco: o do evento novo e o do "+ horário". */
export function horarioEmBranco(chave: number): Horario {
  return {
    chave,
    inicio: null,
    fim: null,
    formadores: [],
    coordenadores: [],
    coordenadorAcompanha: null,
    pretendeAvaliar: null,
    formadorAvaliado: null,
  };
}

/** Evento em branco (com o horário de chave 1): o estado inicial da página e a régua do `estaEmBranco`. */
export const FORM_INICIAL: FormDataType = {
  projeto: null,
  projeto_2: null,
  tipoEvento: null,
  municipio: null,
  horarios: [horarioEmBranco(1)],
  tipo: '',
  encontro: '',
  segmento: '',
  observacoes: '',
  local: '',
  is_online: false,
};

/** O evento visto de um horário: o que é do evento mais o que é daquele horário. */
export function eventoDoHorario(dados: FormDataType, horario: Horario): EventoDeUmHorario {
  const { horarios: _horarios, ...doEvento } = dados;
  const { chave: _chave, ...doHorario } = horario;
  return { ...doEvento, ...doHorario };
}

/** Formadores que podem ser avaliados (função Formador sem a função Coordenador). */
export function formadoresAvaliaveisDo(dados: EventoDeUmHorario): ParticipantType[] {
  return dados.formadores.filter((f) => f.avaliavel);
}

/**
 * "Você pretende avaliar o formador?" só quando a gerência do projeto pergunta e há formador
 * avaliável. Mesma regra do backend.
 */
export function perguntaAvaliarDo(dados: EventoDeUmHorario): boolean {
  return dados.projeto?.pergunta_avaliar_formador !== false && formadoresAvaliaveisDo(dados).length > 0;
}

/** Coordenador responsável: o 1º escolhido; sem escolha, quem cria (se o backend aceita o vazio no projeto). */
export function responsavelDo(dados: EventoDeUmHorario, me: QuemCria | null): QuemCria | null {
  const [primeiro] = dados.coordenadores;
  if (primeiro) {
    return { id: primeiro.id, nome: primeiro.label };
  }
  return dados.projeto?.responsavel_padrao === true && me ? me : null;
}

/** Os coordenadores além do responsável (do 2º em diante), na ordem de escolha. */
export function coordenadoresExtrasDo(dados: EventoDeUmHorario): CoordenadorItem[] {
  return dados.coordenadores.slice(1);
}

/**
 * Quem entra na checagem de disponibilidade. Espelha o backend: todos os formadores e os
 * coordenadores além do responsável (decisão do dono, 03/11/2026); o responsável só se vai
 * acompanhar (05/10/2026). Deduplicado por id (o responsável pode estar também na lista de
 * formadores; sem dedup a mesma pessoa seria checada 2x).
 */
export function participantesDo(dados: EventoDeUmHorario, me: QuemCria | null): PreviewParticipant[] {
  const responsavel = responsavelDo(dados, me);
  const nome = (p: ParticipantType): string => p.label || p.name || `#${p.id}`;
  const lista: PreviewParticipant[] = [
    ...(dados.coordenadorAcompanha === true && responsavel
      ? [{ id: responsavel.id, nome: responsavel.nome, criador: false }]
      : []),
    ...dados.formadores.map((f) => ({ id: f.id, nome: nome(f), criador: false })),
    ...coordenadoresExtrasDo(dados).map((c) => ({ id: c.id, nome: nome(c), criador: false })),
  ];
  const vistos = new Set<ID>();
  return lista.filter((p) => (vistos.has(p.id) ? false : (vistos.add(p.id), true)));
}

/** O horário continua como nasceu (nada preenchido): "Remover horário" não pergunta. */
export function horarioEstaEmBranco(horario: Horario): boolean {
  return JSON.stringify(horario) === JSON.stringify(horarioEmBranco(horario.chave));
}

/**
 * O evento continua como nasceu (nada preenchido, em nenhum horário): "Remover" não pergunta e sair
 * não conta ele.
 */
export function estaEmBranco(dados: FormDataType): boolean {
  const { horarios, ...doEvento } = dados;
  const { horarios: _horarios, ...doEventoEmBranco } = FORM_INICIAL;
  return JSON.stringify(doEvento) === JSON.stringify(doEventoEmBranco) && horarios.every(horarioEstaEmBranco);
}

/** Chave do erro no servidor → campo do Form do cartão, quando o nome não é o mesmo. */
const CAMPO_DO_SERVIDOR: Record<string, string> = {
  tipo_evento: 'tipoEvento',
  coordenador: 'coordenadores',
  coord_acompanha_ids: 'coordenadores',
  coord_acompanha_emails: 'coordenadores',
  extra_participants: 'formadores',
  formador_ids: 'formadores',
  coordenador_acompanha: 'coordenadorAcompanha',
  pretende_avaliar_formador: 'pretendeAvaliar',
  formador_avaliado: 'formadorAvaliado',
};

/** Erro do horário: vai ao DateTimeRange (fora do Form). */
const CHAVES_DO_HORARIO = new Set(['inicio', 'fim']);

/** As mensagens de um valor de `errors` (texto, lista ou dicionário aninhado), na ordem. */
export function mensagensDe(valor: unknown): string[] {
  if (typeof valor === 'string') return [valor];
  if (Array.isArray(valor)) return valor.flatMap(mensagensDe);
  if (valor && typeof valor === 'object') return Object.values(valor).flatMap(mensagensDe);
  return [];
}

/** O erro de um evento recusado pelo servidor, já repartido por onde a tela o mostra. */
export interface ErrosDoServidor {
  /** Campo do Form → mensagens. */
  campos: Record<string, string[]>;
  /** Mensagens do horário (`inicio`/`fim`). */
  horario: string[];
  /** O que não é de um campo à vista (`non_field_errors` e o que não casa): vai ao topo do cartão. */
  topo: string[];
}

/**
 * Reparte o `errors` de um evento do 400 do lote. `campoNaTela` diz se o campo do Form está à vista
 * agora (a pergunta de avaliar só aparece quando se aplica); campo escondido vai para o topo.
 */
export function separarErrosDoServidor(
  errors: Record<string, unknown>,
  campoNaTela: (campo: string) => boolean,
): ErrosDoServidor {
  const separados: ErrosDoServidor = { campos: {}, horario: [], topo: [] };
  for (const [chave, valor] of Object.entries(errors)) {
    const mensagens = mensagensDe(valor);
    if (mensagens.length === 0) continue;
    if (CHAVES_DO_HORARIO.has(chave)) {
      separados.horario.push(...mensagens);
      continue;
    }
    const campo = CAMPO_DO_SERVIDOR[chave] ?? chave;
    if (chave !== 'non_field_errors' && campoNaTela(campo)) {
      separados.campos[campo] = [...(separados.campos[campo] ?? []), ...mensagens];
    } else {
      separados.topo.push(...mensagens);
    }
  }
  return separados;
}
