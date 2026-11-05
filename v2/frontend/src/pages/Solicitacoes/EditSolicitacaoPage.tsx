/**
 * Editar Solicitação - Formulário de Edição
 *
 * Permite editar solicitações existentes antes da publicação no Google Calendar.
 *
 * Regras:
 * - Apenas o criador ou usuários privilegiados (Superintendência/DAT) podem editar
 * - Não é possível editar solicitações já publicadas no Google Calendar, nem as que estão no Google
 *   pela planilha ou com a sincronização em andamento (PENDING)
 * - Não é possível editar solicitações reprovadas
 */

import { useState, useEffect, useMemo, useCallback, ChangeEvent, JSX } from 'react';
import { useNavigate, useParams } from 'react-router';
// antd - direct imports for tree-shaking (Issue #424)
import Form from 'antd/es/form';
import Input from 'antd/es/input';
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Alert from 'antd/es/alert';
import message from 'antd/es/message';
import Typography from 'antd/es/typography';
import Spin from 'antd/es/spin';
import Checkbox from 'antd/es/checkbox';
import Result from 'antd/es/result';
import Radio from 'antd/es/radio';
import Select from 'antd/es/select';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
import type { RadioChangeEvent } from 'antd/es/radio';
// icons - direct imports for tree-shaking (Issue #425)
import ArrowLeftOutlined from '@ant-design/icons/ArrowLeftOutlined';
import SaveOutlined from '@ant-design/icons/SaveOutlined';
import CalendarOutlined from '@ant-design/icons/CalendarOutlined';
import StopOutlined from '@ant-design/icons/StopOutlined';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import { getSolicitacao, updateSolicitacao } from '../../api/solicitacoes';
import { useAcesso } from '../../contexts/AcessoContext';
import { optionalText } from './optionalText';
import { AVISO_SEM_COMPRA, MSG_PROJETO_EM_ESPERA, opcaoDoMunicipio } from './evento';
import {
  lookupMunicipiosWithFilters,
  lookupProjetos,
  lookupTiposEvento,
  type LookupItem,
} from '../../api/lookup';
import DateTimeRange from '../../components/DateTimeRange';
import ComboBox from '../../components/ComboBox';
import CoordenadoresPicker, { type CoordenadorItem } from '../../components/CoordenadoresPicker';
import FormadoresPicker from '../../components/FormadoresPicker';
import logger from '../../utils/logger';
import { MOTIVO_NAO_PUBLICAVEL, motivoNaoPublicavel } from '../../utils/gcalRowActions';
import type { ID, Solicitacao, SolicitacaoStatus, GCalStatus, Participation } from '../../types';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { TextArea } = Input;
const { Title, Text } = Typography;

const RANGE_TIMEZONE = 'America/Fortaleza';

/** Opções das perguntas Sim/Não (decisão do dono, 05/10/2026). */
const SIM_NAO = [
  { label: 'Sim', value: true },
  { label: 'Não', value: false },
];

/** ComboBox value type */
interface ComboBoxValue {
  id: ID;
  label: string;
  fluxo?: string;
  /** Projeto: a gerência usa a pergunta "pretende avaliar o formador?". */
  pergunta_avaliar_formador?: boolean;
  /** Município escolhido na lista: sem compra para o projeto (o evento vai para aprovação). */
  sem_compra?: boolean;
  /** Município escolhido na lista: o projeto está em espera (sem compra em município nenhum). */
  projeto_em_espera?: boolean;
}

/** Formador type */
interface FormadorType {
  id: ID;
  label: string;
  email?: string;
  /** Função Formador sem a função Coordenador: pode ser avaliado. */
  avaliavel?: boolean;
}

/** Form data type */
interface FormDataType {
  projeto: ComboBoxValue | null;
  tipoEvento: ComboBoxValue | null;
  municipio: ComboBoxValue | null;
  inicio: string | null;
  fim: string | null;
  tipo: string;
  encontro: string;
  segmento: string;
  observacoes: string;
  local: string;
  is_online: boolean;
  formadores: FormadorType[];
  /** A caixa "Coordenador(es)" (decisões do dono, 03/11/2026): o 1º é o responsável, os demais são COORD_ACOMPANHA. */
  coordenadores: CoordenadorItem[];
  /** null = o responsável mudou e ainda não respondeu. */
  coordenadorAcompanha: boolean | null;
  /** null = não informado (eventos antigos) ou pergunta que não se aplica. */
  pretendeAvaliar: boolean | null;
  formadorAvaliado: ID | null;
}

/** Range value type */
interface RangeValueType {
  date: string;
  start: string;
  end: string;
}

/** API error response type */
interface ApiErrorResponse {
  response?: {
    status?: number;
    data?: {
      non_field_errors?: string[];
      detail?: string;
      code?: string;
      errors?: Record<string, unknown>;
    };
  };
}

/** O responsável para o backend: `coordenador`; sem ele (evento antigo), quem criou. */
function responsavelEfetivoDe(s: Solicitacao): ID {
  return s.coordenador ?? s.usuario;
}

/** Nome na tela (D15): nome e sobrenome que existirem; sem nenhum, o número. Nunca o login (o servidor nem o manda). */
function nomeDe(u: { id: ID; first_name?: string; last_name?: string }): string {
  return [u.first_name, u.last_name].filter(Boolean).join(' ') || `#${u.id}`;
}

const ROTULO_DO_STATUS: Record<SolicitacaoStatus, string> = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
};

const ROTULO_DO_GCAL: Record<GCalStatus, string> = {
  NONE: 'Não publicado',
  PENDING: 'Aguardando publicação',
  PUBLISHED: 'Publicado',
  ERROR: 'Erro ao publicar',
};

/**
 * Por que a tela não abre o formulário, ou null. Os mesmos travamentos do servidor (o salvar daria 400)
 * e os textos de Minhas Solicitações (D25, D27): o caminho que existe, não "cancele o evento".
 */
function travaDaEdicao(s: Solicitacao): { titulo: string; texto: string; publicado: boolean } | null {
  if (s.publicado_fora_do_sistema === true) {
    return {
      titulo: 'Evento na agenda pela planilha',
      texto: `Este evento ${MOTIVO_NAO_PUBLICAVEL.publicado_fora_do_sistema}; mudar aqui não muda a agenda. Para mudar, peça ao Apoio de Coordenação da sua gerência ou ao Controle.`,
      publicado: true,
    };
  }
  if (s.gcal_status === 'PUBLISHED') {
    // Publicar na agenda (Apoio) e a Pré-agenda (Controle) só tiram do Google o aprovado com id, de hoje em diante.
    const consegueTirar =
      s.status === 'aprovado' && Boolean(s.external_event_id) && motivoNaoPublicavel(s) !== 'evento_passado';
    return {
      titulo: 'Solicitação já publicada',
      texto: consegueTirar
        ? 'Este evento já está no Google Agenda. Para editar, peça ao Apoio de Coordenação da sua gerência, na tela Publicar na agenda, ou ao Controle, na Pré-agenda, que tire o evento só do Google; depois disso, você consegue editar aqui.'
        : 'Este evento já está no Google Agenda e não dá para editá-lo aqui. Para mudar, fale com a administração do sistema.',
      publicado: true,
    };
  }
  if (s.gcal_status === 'PENDING') {
    return {
      titulo: 'Sincronização em andamento',
      texto: 'A sincronização com o Google Agenda está em andamento. Aguarde e recarregue a página para editar.',
      publicado: true,
    };
  }
  if (s.status === 'reprovado') {
    return {
      titulo: 'Solicitação reprovada',
      texto: 'Solicitações reprovadas não podem ser editadas. Crie uma nova solicitação se necessário.',
      publicado: false,
    };
  }
  return null;
}

/**
 * O que a aprovação SUPER aprovou (`_campos_materiais` do backend): projeto, município, início e fim
 * (como instante), formadores, os coordenadores além do responsável e o responsável que acompanha.
 */
function camposMateriais(d: FormDataType): string {
  const ids = (lista: Array<{ id: ID }>): string => lista.map(p => String(p.id)).sort().join(',');
  const instante = (iso: string | null): number | null => (iso ? dayjs(iso).valueOf() : null);
  return JSON.stringify([
    d.projeto?.id ?? null,
    d.municipio?.id ?? null,
    instante(d.inicio),
    instante(d.fim),
    ids(d.formadores),
    ids(d.coordenadores.slice(1)),
    d.coordenadorAcompanha ? (d.coordenadores[0]?.id ?? null) : null,
  ]);
}

export default function EditSolicitacaoPage(): JSX.Element {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [form] = Form.useForm();

  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [solicitacao, setSolicitacao] = useState<Solicitacao | null>(null);
  const [error, setError] = useState<string | null>(null);
  // O formulário como veio do servidor: a régua do aviso "volta para aprovação".
  const [carregado, setCarregado] = useState<FormDataType | null>(null);

  // Estado do formulário
  const [formData, setFormData] = useState<FormDataType>({
    projeto: null,
    tipoEvento: null,
    municipio: null,
    inicio: null,
    fim: null,
    tipo: '',
    encontro: '',
    segmento: '',
    observacoes: '',
    local: '',
    is_online: false,
    formadores: [],
    coordenadores: [],
    coordenadorAcompanha: false,
    pretendeAvaliar: null,
    formadorAvaliado: null,
  });

  // Carregar dados da solicitação
  useEffect(() => {
    const fetchSolicitacao = async (): Promise<void> => {
      try {
        setLoading(true);
        const data = await getSolicitacao(Number(id));
        setSolicitacao(data);

        // Extrair formadores e os coordenadores além do responsável das participations
        // (avaliável = está em `avaliaveis_ids` do detalhe)
        const avaliaveis = new Set(data.avaliaveis_ids ?? []);
        const pessoasDoPapel = (papel: Participation['role']): FormadorType[] =>
          (data.participations || [])
            .filter((p: Participation) => p.role === papel && p.usuario)
            .map((p: Participation) => ({
              id: p.usuario!.id,
              label: nomeDe(p.usuario!),
              avaliavel: avaliaveis.has(p.usuario!.id),
            }));
        const formadores = pessoasDoPapel('FORMADOR');
        // A caixa "Coordenador(es)": o responsável EFETIVO em 1º e os demais depois. Sem `coordenador`
        // gravado (evento antigo), o responsável para o backend é quem criou (`coordenador_id or
        // usuario_id`); o nome vem de `coordenador_nome`, que o detalhe já preenche com quem criou
        // quando não há `coordenador` (sem o login, que é o CPF), ou da linha COORDENADOR dele. A linha
        // COORD_ACOMPANHA que repete o responsável não vira outra tag (nem vai em `coord_acompanha_ids`).
        const efetivoId = responsavelEfetivoDe(data);
        const linhaDoResponsavel = (data.participations || []).find(
          (p: Participation) => p.role === 'COORDENADOR' && p.usuario?.id === efetivoId,
        );
        const nomeDaLinha = linhaDoResponsavel?.usuario ? nomeDe(linhaDoResponsavel.usuario) : '';
        const responsavelEfetivo: CoordenadorItem = {
          id: efetivoId,
          label: data.coordenador_nome || nomeDaLinha || `#${efetivoId}`,
        };
        const coordenadores: CoordenadorItem[] = [
          responsavelEfetivo,
          ...pessoasDoPapel('COORD_ACOMPANHA').filter(c => c.id !== efetivoId),
        ];

        // Preencher o formData com os dados existentes
        const inicial: FormDataType = {
          projeto: data.projeto
            ? {
                id: data.projeto,
                label: data.projeto_nome || '',
                pergunta_avaliar_formador: data.projeto_pergunta_avaliar_formador ?? true,
              }
            : null,
          tipoEvento: data.tipo_evento ? { id: data.tipo_evento, label: data.tipo_evento_nome || '' } : null,
          municipio: data.municipio ? { id: data.municipio, label: data.municipio_nome || '' } : null,
          inicio: data.inicio,
          fim: data.fim,
          tipo: data.tipo || '',
          encontro: data.encontro || '',
          segmento: data.segmento || '',
          observacoes: data.observacoes || '',
          local: data.local || '',
          is_online: data.is_online || false,
          formadores,
          coordenadores,
          coordenadorAcompanha: data.coordenador_acompanha,
          pretendeAvaliar: data.pretende_avaliar_formador ?? null,
          formadorAvaliado: data.formador_avaliado ?? null,
        };
        setFormData(inicial);
        setCarregado(inicial);

        // Preencher o form do Ant Design
        form.setFieldsValue({
          tipo: data.tipo || '',
          encontro: data.encontro || '',
          segmento: data.segmento || '',
          observacoes: data.observacoes || '',
          local: data.local || '',
          is_online: data.is_online || false,
        });
      } catch (err) {
        logger.error('Erro ao carregar solicitação:', err);
        const apiErr = err as ApiErrorResponse;
        if (apiErr.response?.status === 404) {
          setError('Solicitação não encontrada.');
        } else if (apiErr.response?.status === 403) {
          setError('Você não tem permissão para editar esta solicitação.');
        } else {
          setError('Erro ao carregar solicitação. Tente novamente.');
        }
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      void fetchSolicitacao();
    }
  }, [id, form]);

  // Handler para DateTimeRange (Issue #428)
  const handleRangeChange = useCallback((range: RangeValueType | null): void => {
    if (!range || !range.date || !range.start || !range.end) {
      setFormData(prev => ({ ...prev, inicio: null, fim: null }));
      return;
    }

    try {
      const dateStr = range.date;
      const startTime = range.start;
      const endTime = range.end;

      const inicioLocal = dayjs.tz(`${dateStr} ${startTime}`, RANGE_TIMEZONE);
      const fimLocal = dayjs.tz(`${dateStr} ${endTime}`, RANGE_TIMEZONE);

      const isoInicio = inicioLocal.utc().format();
      const isoFim = fimLocal.utc().format();

      setFormData(prev => ({ ...prev, inicio: isoInicio, fim: isoFim }));
    } catch (error) {
      logger.error('Erro ao converter data/hora:', error);
      setFormData(prev => ({ ...prev, inicio: null, fim: null }));
    }
  }, []);

  // Derivar rangeValue memoizado (Issue #428)
  const rangeValue = useMemo((): RangeValueType => {
    if (!formData.inicio || !formData.fim) {
      return { date: '', start: '', end: '' };
    }
    return {
      date: dayjs(formData.inicio).tz(RANGE_TIMEZONE).format('YYYY-MM-DD'),
      start: dayjs(formData.inicio).tz(RANGE_TIMEZONE).format('HH:mm'),
      end: dayjs(formData.fim).tz(RANGE_TIMEZONE).format('HH:mm'),
    };
  }, [formData.inicio, formData.fim]);

  // Regra da compra: o projeto "em espera" some da lista. A de municípios traz também os sem compra
  // para o projeto, marcados (pedido do dono, 03/11/2026: o evento ali vai para aprovação). Quem é
  // isento (superusuário ou a capacidade) recebe tudo do servidor, sem marca. O par já gravado
  // continua como valor, e salvar com o mesmo par segue livre.
  const lookupProjetosElegiveis = useCallback(
    (q: string): Promise<LookupItem[]> => lookupProjetos(q, { com_compra: true }),
    [],
  );
  const projetoId = formData.projeto?.id;
  const lookupMunicipiosElegiveis = useCallback(
    (q: string): Promise<LookupItem[]> =>
      lookupMunicipiosWithFilters({ q, com_compra: true, marcar_sem_compra: true, projeto_id: projetoId }),
    [projetoId],
  );
  // A marca vem do município escolhido na lista, ou da reconferência ao trocar o projeto. Só avisa
  // quando o par difere do gravado: salvar com o mesmo par não muda o status.
  const dispensaCompra = useAcesso().caps.canCreateSolicitationWithoutPurchase;
  const parDiferente =
    solicitacao !== null &&
    (formData.municipio?.id !== solicitacao.municipio || formData.projeto?.id !== solicitacao.projeto);
  // Projeto em espera: o servidor recusa o par novo (não vai para aprovação), e a tela diz isso.
  const emEspera = parDiferente && formData.municipio?.projeto_em_espera === true;
  const semCompra = parDiferente && !emEspera && formData.municipio?.sem_compra === true;
  // SUPER aprovada: mudar o que a aprovação aprovou a devolve para aprovação (decisões do dono de 14/10,
  // 03/11 e 04/11/2026). A tela avisa antes do Salvar; o par sem compra ou em espera já tem o aviso dele.
  const voltaParaAprovacao =
    solicitacao?.status === 'aprovado' &&
    (formData.projeto?.fluxo ?? solicitacao.fluxo) === 'SUPER' &&
    !semCompra &&
    !emEspera &&
    carregado !== null &&
    camposMateriais(formData) !== camposMateriais(carregado);

  // Trocar o projeto: a marca era do par antigo. Com município escolhido, reconfere o par novo pelo
  // mesmo lookup (só esse município); a resposta só vale se o par ainda é o mesmo.
  const handleProjetoChange = (value: ComboBoxValue | null): void => {
    const municipioId = formData.municipio?.id;
    setFormData({
      ...formData,
      projeto: value,
      municipio: formData.municipio && { ...formData.municipio, sem_compra: false, projeto_em_espera: false },
    });
    if (!value || municipioId == null) return;
    lookupMunicipiosWithFilters({
      q: '',
      com_compra: true,
      marcar_sem_compra: true,
      projeto_id: value.id,
      municipio_id: municipioId,
    })
      .then(([item]) => {
        setFormData(prev =>
          prev.projeto?.id === value.id && prev.municipio?.id === municipioId
            ? {
                ...prev,
                municipio: {
                  ...prev.municipio,
                  sem_compra: item?.['sem_compra'] === true,
                  projeto_em_espera: item?.['projeto_em_espera'] === true,
                },
              }
            : prev,
        );
      })
      .catch((err: unknown) => logger.warn('Não foi possível reconferir a compra do par:', err));
  };

  // "Você pretende avaliar o formador?" só quando a gerência do projeto pergunta e há formador
  // avaliável na lista (mesma regra do backend, decisão do dono de 05/10/2026).
  const formadoresAvaliaveis = formData.formadores.filter(f => f.avaliavel);
  const perguntaAvaliar = formData.projeto?.pergunta_avaliar_formador !== false && formadoresAvaliaveis.length > 0;
  // Resposta obrigatória (mesma regra do backend): quem já respondeu, ou evento em que a pergunta
  // passa a valer agora. Só o evento antigo (pergunta já valia, sem resposta) segue "Não informado".
  const avaliarAplicavaAoCarregar =
    solicitacao !== null &&
    solicitacao.projeto_pergunta_avaliar_formador !== false &&
    (solicitacao.avaliaveis_ids ?? []).length > 0;
  const avaliarObrigatoria =
    perguntaAvaliar && (solicitacao?.pretende_avaliar_formador != null || !avaliarAplicavaAoCarregar);

  // Trocar o 1º coordenador troca o responsável: a resposta de acompanhar era do anterior e é apagada.
  const handleCoordenadoresChange = (value: CoordenadorItem[]): void => {
    setFormData(prev => ({
      ...prev,
      coordenadores: value,
      coordenadorAcompanha: value[0]?.id === prev.coordenadores[0]?.id ? prev.coordenadorAcompanha : null,
    }));
  };

  // Trocar a lista de formadores: se o escolhido para avaliação saiu, a escolha é limpa.
  const handleFormadoresChange = (value: FormadorType[]): void => {
    setFormData(prev => ({
      ...prev,
      formadores: value,
      formadorAvaliado: value.some(f => f.avaliavel && f.id === prev.formadorAvaliado) ? prev.formadorAvaliado : null,
    }));
  };

  // Submit
  const handleSubmit = async (): Promise<void> => {
    setSaving(true);
    try {
      // Validações
      if (!formData.inicio || !formData.fim) {
        message.error('Por favor, selecione data/hora de início e fim');
        setSaving(false);
        return;
      }

      if (!formData.municipio) {
        message.error('Por favor, selecione um município');
        setSaving(false);
        return;
      }

      if (!formData.projeto) {
        message.error('Por favor, selecione um projeto');
        setSaving(false);
        return;
      }

      if (!formData.tipoEvento) {
        message.error('Por favor, selecione um tipo de evento');
        setSaving(false);
        return;
      }

      // Garantir que formadores é um array
      const formadores = Array.isArray(formData.formadores) ? formData.formadores : [];

      if (formadores.length === 0) {
        message.error('Por favor, selecione pelo menos um formador');
        setSaving(false);
        return;
      }

      // A API não deixa esvaziar o responsável (no evento antigo sem `coordenador`, é quem criou).
      const [responsavel, ...demaisCoordenadores] = formData.coordenadores;
      if (!responsavel) {
        message.error('Escolha o coordenador responsável pelo evento.');
        setSaving(false);
        return;
      }

      if (formData.coordenadorAcompanha === null) {
        message.error('Responda se o coordenador responsável vai acompanhar o evento.');
        setSaving(false);
        return;
      }

      if (avaliarObrigatoria && formData.pretendeAvaliar === null) {
        message.error('Informe se você pretende avaliar o formador neste evento.');
        setSaving(false);
        return;
      }

      if (perguntaAvaliar && formData.pretendeAvaliar === true && formData.formadorAvaliado === null) {
        message.error('Escolha qual formador você pretende avaliar.');
        setSaving(false);
        return;
      }

      const payload = {
        municipio: formData.municipio.id,
        projeto: formData.projeto.id,
        tipo_evento: formData.tipoEvento.id,
        inicio: dayjs(formData.inicio).utc().format(),
        fim: dayjs(formData.fim).utc().format(),
        tipo: formData.tipo || null,
        encontro: formData.encontro || null,
        segmento: formData.segmento || null,
        observacoes: optionalText(formData.observacoes),
        local: formData.local || '',
        is_online: !!formData.is_online,
        // O 1º da caixa é o responsável (trocar o 1º troca o responsável; a API confere a gerência). O
        // evento antigo sem `coordenador` salvo sem trocar o 1º segue sem (o backend já usa quem criou).
        ...((solicitacao?.coordenador || (solicitacao && responsavel.id !== responsavelEfetivoDe(solicitacao))) && {
          coordenador: responsavel.id,
        }),
        coordenador_acompanha: formData.coordenadorAcompanha,
        // Pergunta que não se aplica: a resposta não vai (a gravada fica; o backend recusa
        // apagá-la e recusa tirar da lista o formador escolhido).
        ...(perguntaAvaliar && {
          pretende_avaliar_formador: formData.pretendeAvaliar,
          formador_avaliado: formData.pretendeAvaliar === true ? formData.formadorAvaliado : null,
        }),
        extra_participants: {
          formador_ids: formadores.map(f => f.id),
          coord_acompanha_ids: demaisCoordenadores.map(c => c.id),
        },
      };

      const atualizada = await updateSolicitacao(Number(id), payload);
      // Decisão do dono (14/10/2026): o backend devolve a SUPER aprovada para pendente quando
      // muda data, horário, município, projeto, formadores, coordenadores (03/11/2026) ou o responsável que acompanha (04/11/2026). A tela só
      // avisa o que a API fez.
      // Par novo sem compra (pedido do dono, 03/11/2026): volta para aprovação em qualquer fluxo. A
      // mensagem segue a marca do par escolhido na tela (`semCompra`: par diferente do gravado e marcado).
      if (solicitacao?.status === 'aprovado' && atualizada.status === 'pendente') {
        message.warning(
          !dispensaCompra && semCompra
            ? 'Solicitação atualizada. Sem compra neste município para este projeto: o evento voltou para aprovação.'
            : 'Solicitação atualizada. A mudança de data, horário, município, projeto, formadores, coordenadores ou da resposta "vai acompanhar?" voltou o evento para aprovação.',
        );
      } else {
        message.success('Solicitação atualizada com sucesso!');
      }
      void navigate('/solicitacoes/minhas');
    } catch (err) {
      logger.error('Erro ao atualizar solicitação:', err);
      const apiErr = err as ApiErrorResponse;

      // Tratar erros específicos do backend. O motivo vem no `detail` (403) ou no campo (400,
      // ex.: `errors.projeto` ao mover para fora do escopo da aprovadora — regra do dono, 30/09).
      const data = apiErr.response?.data;
      const motivoDoCampo = Object.values(data?.errors ?? {})
        .flat()
        .find((texto): texto is string => typeof texto === 'string');
      if (data?.code === 'availability_conflict' && data.detail) {
        // Conflito de agenda: o motivo está no `detail`. `errors` traz objetos e os e-mails dos
        // convidados externos (`skipped_guests`), que não são a mensagem.
        message.error(data.detail);
      } else if (data?.non_field_errors) {
        message.error(data.non_field_errors[0]);
      } else if (apiErr.response?.status === 403) {
        message.error(data?.detail || 'Você não tem permissão para editar esta solicitação.');
      } else if (apiErr.response?.status === 400 && motivoDoCampo) {
        message.error(motivoDoCampo);
      } else {
        message.error('Erro ao atualizar solicitação. Verifique os dados e tente novamente.');
      }
    } finally {
      setSaving(false);
    }
  };

  // Estados de loading e erro
  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto flex justify-center items-center min-h-96">
        <Spin size="large" tip="Carregando solicitação..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Result
          status="error"
          title="Erro ao carregar"
          subTitle={error}
          extra={[
            <Button key="back" onClick={() => navigate('/solicitacoes/minhas')}>
              Voltar para Solicitações
            </Button>,
          ]}
        />
      </div>
    );
  }

  // Verificar se pode editar
  const trava = solicitacao && travaDaEdicao(solicitacao);

  if (trava) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/solicitacoes/minhas')}
            className="mb-4"
          >
            Voltar
          </Button>

          <Result
            status="warning"
            icon={trava.publicado ? <CalendarOutlined /> : <StopOutlined />}
            title={trava.titulo}
            subTitle={trava.texto}
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/solicitacoes/minhas')}
          className="mb-4"
        >
          Voltar
        </Button>

        <Title level={2} className="mb-2">Editar Solicitação #{id}</Title>
        <Text type="secondary">
          Status: <strong>{solicitacao && (ROTULO_DO_STATUS[solicitacao.status] ?? solicitacao.status)}</strong>
          {solicitacao?.gcal_status && solicitacao.gcal_status !== ('NONE' as GCalStatus) && (
            <> | Google Agenda: <strong>{ROTULO_DO_GCAL[solicitacao.gcal_status] ?? solicitacao.gcal_status}</strong></>
          )}
        </Text>

        <Alert
          message="Editando solicitação"
          description="Você está editando uma solicitação existente. Após salvar, as alterações serão registradas no histórico de auditoria."
          type="info"
          showIcon
          className="mt-4 mb-6"
        />

        <Form form={form} layout="vertical" autoComplete="off">
          <Form.Item
            label="Projeto"
            rules={[{ required: true, message: 'Por favor selecione um projeto' }]}
          >
            <ComboBox
              lookupFunction={lookupProjetosElegiveis}
              onChange={handleProjetoChange}
              value={formData.projeto as unknown as { id: ID; label: string; [key: string]: unknown } | null}
              placeholder="Busque ou selecione um projeto"
            />
          </Form.Item>

          <Form.Item
            label="Tipo de Evento"
            rules={[{ required: true, message: 'Por favor selecione um tipo de evento' }]}
          >
            <ComboBox
              lookupFunction={lookupTiposEvento}
              onChange={(value: ComboBoxValue | null) => setFormData({ ...formData, tipoEvento: value })}
              value={formData.tipoEvento as unknown as { id: ID; label: string; [key: string]: unknown } | null}
              placeholder="Busque ou selecione um tipo de evento"
            />
          </Form.Item>

          <Form.Item
            label="Município"
            rules={[{ required: true, message: 'Por favor selecione um município' }]}
            extra={
              emEspera ? (
                <Alert id="edit-municipio-sem-compra" type="error" showIcon role="none" message={MSG_PROJETO_EM_ESPERA} />
              ) : semCompra ? (
                <Alert id="edit-municipio-sem-compra" type="warning" showIcon role="none" message={AVISO_SEM_COMPRA} />
              ) : undefined
            }
          >
            <ComboBox
              lookupFunction={lookupMunicipiosElegiveis}
              renderOption={opcaoDoMunicipio}
              aria-describedby={semCompra || emEspera ? 'edit-municipio-sem-compra' : undefined}
              onChange={(value: ComboBoxValue | null) => setFormData({ ...formData, municipio: value })}
              value={formData.municipio as unknown as { id: ID; label: string; [key: string]: unknown } | null}
              placeholder="Busque ou selecione um município"
            />
          </Form.Item>

          <Form.Item
            label="Formadores"
            rules={[{ required: true, message: 'Por favor selecione pelo menos um formador' }]}
          >
            <FormadoresPicker
              value={formData.formadores}
              onChange={handleFormadoresChange}
              projetoId={projetoId}
            />
          </Form.Item>

          {/* Decisões do dono (03/11/2026): a caixa única da criação. O 1º é o responsável; os demais ocupam
              a agenda e recebem o convite. */}
          <Form.Item
            label="Coordenador(es)"
            htmlFor="edit-coordenadores"
            extra={<span id="edit-coordenadores-explica">O 1º escolhido é o coordenador responsável.</span>}
          >
            <CoordenadoresPicker
              id="edit-coordenadores"
              aria-describedby="edit-coordenadores-explica"
              value={formData.coordenadores}
              onChange={handleCoordenadoresChange}
              projetoId={projetoId}
            />
          </Form.Item>

          <Form.Item
            label={<span id="edit-pergunta-acompanha">O coordenador responsável vai acompanhar o evento?</span>}
          >
            <Radio.Group
              // role e aria-* vão ao <div> do grupo (o tipo do antd não declara role)
              {...{ role: 'radiogroup' }}
              aria-labelledby="edit-pergunta-acompanha"
              name="coordenador_acompanha"
              options={SIM_NAO}
              value={formData.coordenadorAcompanha}
              onChange={(e: RadioChangeEvent) =>
                setFormData(prev => ({ ...prev, coordenadorAcompanha: e.target.value as boolean }))
              }
            />
          </Form.Item>

          {perguntaAvaliar && (
            <Form.Item
              label={<span id="edit-pergunta-avaliar">Você pretende avaliar o formador nesse evento?</span>}
              required={avaliarObrigatoria}
              extra={formData.pretendeAvaliar === null && !avaliarObrigatoria ? 'Não informado' : undefined}
            >
              <Radio.Group
                {...{ role: 'radiogroup' }}
                aria-labelledby="edit-pergunta-avaliar"
                name="pretende_avaliar_formador"
                options={SIM_NAO}
                value={formData.pretendeAvaliar}
                onChange={(e: RadioChangeEvent) =>
                  setFormData(prev => ({ ...prev, pretendeAvaliar: e.target.value as boolean }))
                }
              />
            </Form.Item>
          )}

          {perguntaAvaliar && formData.pretendeAvaliar === true && (
            <Form.Item label="Qual formador você pretende avaliar?" htmlFor="edit-formador-avaliado">
              <Select
                id="edit-formador-avaliado"
                placeholder="Escolha um formador"
                {...(formData.formadorAvaliado !== null && { value: formData.formadorAvaliado })}
                options={formadoresAvaliaveis.map(f => ({ value: f.id, label: f.label }))}
                onChange={(value: ID) => setFormData(prev => ({ ...prev, formadorAvaliado: value }))}
              />
            </Form.Item>
          )}

          <DateTimeRange
            value={rangeValue}
            onChange={handleRangeChange as unknown as (value: { date?: string | null; start?: string | null; end?: string | null }) => void}
          />

          <Form.Item
            label="Tipo"
            name="tipo"
            rules={[{ max: 50, message: 'Máximo 50 caracteres' }]}
          >
            <Input
              placeholder="Ex: evento, reunião"
              value={formData.tipo}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, tipo: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            label="Nº da formação"
            name="encontro"
            rules={[{ max: 100, message: 'Máximo 100 caracteres' }]}
          >
            <Input
              placeholder="Ex: 4"
              value={formData.encontro}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, encontro: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            label="Segmento"
            name="segmento"
            rules={[{ max: 100, message: 'Máximo 100 caracteres' }]}
          >
            <Input
              placeholder="Ex: Fundamental I, Fundamental II"
              value={formData.segmento}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, segmento: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            label="Local do Evento"
            name="local"
            rules={[{ max: 300, message: 'Máximo 300 caracteres' }]}
          >
            <Input
              placeholder="Ex: Escola Municipal X, Sala 5 / Secretaria de Educação"
              value={formData.local}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData({ ...formData, local: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            label="Observações"
            name="observacoes"
            rules={[{ max: 5000, message: 'Máximo 5000 caracteres' }]}
          >
            <TextArea
              rows={4}
              placeholder="Observações adicionais sobre o evento"
              value={formData.observacoes}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setFormData({ ...formData, observacoes: e.target.value })}
            />
          </Form.Item>

          <Form.Item name="is_online" valuePropName="checked">
            <Checkbox
              checked={formData.is_online}
              onChange={(e: CheckboxChangeEvent) => setFormData({ ...formData, is_online: e.target.checked })}
            >
              Evento online (Google Meet)
            </Checkbox>
          </Form.Item>

          <Alert
            message="Modalidade do evento"
            description={
              formData.is_online
                ? 'Link do Google Meet será gerado automaticamente após publicação do evento no calendário.'
                : 'Evento presencial - nenhum link de reunião será gerado.'
            }
            type={formData.is_online ? 'info' : 'warning'}
            showIcon
            className="mb-6"
          />

          {voltaParaAprovacao && (
            <Alert
              id="edit-volta-aprovacao"
              type="warning"
              showIcon
              role="status"
              message="Esta mudança volta o evento para aprovação."
              className="mb-4"
            />
          )}

          <div className="flex gap-2 justify-end">
            <Button onClick={() => navigate('/solicitacoes/minhas')}>
              Cancelar
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSubmit}
              loading={saving}
              aria-describedby={voltaParaAprovacao ? 'edit-volta-aprovacao' : undefined}
            >
              Salvar Alterações
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
}
