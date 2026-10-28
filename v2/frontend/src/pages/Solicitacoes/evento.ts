/**
 * Dados de um evento da Nova Solicitação (um cartão da página) e as regras puras sobre eles.
 *
 * Fica fora do componente para a página e o cartão lerem a mesma coisa: o que é um evento em
 * branco, quando a pergunta de avaliar o formador vale e quem entra na checagem de agenda.
 */

import type { LookupItem } from '../../components/ComboBox';
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
};

/** Formador escolhido (o `avaliavel` vem do lookup: função Formador sem a função Coordenador). */
export type ParticipantType = FormadorItem;

/** Quem cria (do /me): é o responsável quando nenhum outro é escolhido e o projeto aceita o vazio. */
export interface QuemCria {
  id: ID;
  nome: string;
}

/** O que a pessoa preenche num evento. */
export interface FormDataType {
  projeto: ComboBoxValue | null;
  tipoEvento: ComboBoxValue | null;
  municipio: ComboBoxValue | null;
  inicio: string | null;
  fim: string | null;
  formadores: ParticipantType[];
  // #1666: coordenador RESPONSÁVEL (FK). Vazio: o backend usa quem cria, se for coordenador.
  coordenadorResponsavel: ComboBoxValue | null;
  // Decisão do dono (05/10/2026): respostas Sim/Não; null = ainda não respondida.
  coordenadorAcompanha: boolean | null;
  pretendeAvaliar: boolean | null;
  formadorAvaliado: ID | null;
  // Mais detalhes (opcionais)
  tipo: string;
  encontro: string;
  segmento: string;
  observacoes: string;
  local: string;
  // PR19: Modalidade online/presencial
  is_online: boolean;
}

/** Evento em branco: o estado inicial do cartão e a régua de "tem algo preenchido" ao sair. */
export const FORM_INICIAL: FormDataType = {
  projeto: null,
  tipoEvento: null,
  municipio: null,
  inicio: null,
  fim: null,
  formadores: [],
  coordenadorResponsavel: null,
  coordenadorAcompanha: null,
  pretendeAvaliar: null,
  formadorAvaliado: null,
  tipo: '',
  encontro: '',
  segmento: '',
  observacoes: '',
  local: '',
  is_online: false,
};

/** Formadores que podem ser avaliados (função Formador sem a função Coordenador). */
export function formadoresAvaliaveisDo(dados: FormDataType): ParticipantType[] {
  return dados.formadores.filter((f) => f.avaliavel);
}

/**
 * "Você pretende avaliar o formador?" só quando a gerência do projeto pergunta e há formador
 * avaliável. Mesma regra do backend.
 */
export function perguntaAvaliarDo(dados: FormDataType): boolean {
  return dados.projeto?.pergunta_avaliar_formador !== false && formadoresAvaliaveisDo(dados).length > 0;
}

/** Coordenador responsável: o escolhido; sem escolha, quem cria (se o backend aceita o vazio no projeto). */
export function responsavelDo(dados: FormDataType, me: QuemCria | null): QuemCria | null {
  if (dados.coordenadorResponsavel) {
    return { id: dados.coordenadorResponsavel.id, nome: dados.coordenadorResponsavel.label };
  }
  return dados.projeto?.responsavel_padrao === true && me ? me : null;
}

/**
 * Quem entra na checagem de disponibilidade. Espelha o backend (decisão do dono, 05/10/2026):
 * todos os formadores; o coordenador responsável só se vai acompanhar. Deduplicado por id
 * (o responsável pode estar também na lista de formadores; sem dedup contaria 2x no RD-05).
 */
export function participantesDo(dados: FormDataType, me: QuemCria | null): PreviewParticipant[] {
  const responsavel = responsavelDo(dados, me);
  const lista: PreviewParticipant[] = [
    ...(dados.coordenadorAcompanha === true && responsavel
      ? [{ id: responsavel.id, nome: responsavel.nome, criador: false }]
      : []),
    ...dados.formadores.map((f) => ({ id: f.id, nome: f.label || f.name || `#${f.id}`, criador: false })),
  ];
  const vistos = new Set<ID>();
  return lista.filter((p) => (vistos.has(p.id) ? false : (vistos.add(p.id), true)));
}

/** O evento continua como nasceu (nada preenchido): "Remover" não pergunta e sair não conta ele. */
export function estaEmBranco(dados: FormDataType): boolean {
  return JSON.stringify(dados) === JSON.stringify(FORM_INICIAL);
}

/** Chave do erro no servidor → campo do Form do cartão, quando o nome não é o mesmo. */
const CAMPO_DO_SERVIDOR: Record<string, string> = {
  tipo_evento: 'tipoEvento',
  coordenador: 'coordenadorResponsavel',
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
