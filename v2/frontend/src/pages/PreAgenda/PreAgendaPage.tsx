/**
 * PreAgendaPage - Página de pré-agenda (Controle)
 *
 * Features:
 * - Lista solicitações aprovadas de ambos os fluxos (SUPER + NAO_SUPER)
 * - Filtros por data, gerência (mesmo `gerencia_id` na lista e nos KPIs), busca textual
 * - Exibe resumo de status GCal no topo
 * - Botões para preview e publish
 * - Operações em lote (Reapply/Resync) via seleção múltipla
 */

import { useState, useEffect, useCallback, useContext, useMemo, useRef, ChangeEvent, CSSProperties, Key, JSX } from 'react';
import {
  Card,
  ConfigProvider,
  Grid,
  Input,
  DatePicker,
  Button,
  Space,
  Tag,
  Typography,
  message,
  Modal,
  Statistic,
  Row,
  Col,
  Alert,
  Descriptions,
  Collapse,
  Divider,
  List,
  Avatar,
  Segmented,
  Empty,
  Spin,
  Select,
} from 'antd';
import type { TableRowSelection } from 'antd/es/table/interface';
import dayjs, { type Dayjs } from 'dayjs';
import {
  EyeOutlined,
  CloudUploadOutlined,
  CalendarOutlined,
  VideoCameraOutlined,
  InfoCircleOutlined,
  SyncOutlined,
  StopOutlined,
  EnvironmentOutlined,
  TeamOutlined,
  LinkOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  GlobalOutlined,
  UserOutlined,
  CodeOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';

import { fetchAPI } from '../../api/config';
import {
  listSolicitacoes,
  previewSolicitacao,
  publishSolicitacao,
  resyncSolicitacao,
  cancelSolicitacao,
} from '../../api/solicitacoes';
import { getStatusSummary, reapplyBatch, resyncBatch, type GCalStatusSummary } from '../../api/gcal';
import { MeetLink } from '../../components/MeetLink';
import { getGerencias } from '../../api/availability';
import { useAcesso } from '../../contexts/AcessoContext';
import ThemeContext from '../../contexts/ThemeContext';
import useGoogleIntegration from '../../hooks/useGoogleIntegration';
import useGoogleGuard from '../../hooks/useGoogleGuard';
import GoogleIntegrationCard from '../../components/google/GoogleIntegrationCard';
import { OAuthRetornoAlert } from '../../components/google/OAuthRetornoAlert';
import { lerOAuthRetorno, type OAuthRetorno } from '../../utils/oauthRetorno';
import { TIMING } from '../../constants/timing';
import { usePolling } from '../../hooks/usePolling';
import { syncChannel } from '../../services/syncChannel';
import { FORTALEZA_TZ, formatFortaleza } from '../../utils/datetime';
import { MOTIVO_NAO_PUBLICAVEL, gcalRowActions, motivoNaoPublicavel, type GcalRowTag } from '../../utils/gcalRowActions';
import logger from '../../utils/logger';
import type { ID, Solicitacao, GCalStatus, Gerencia, PaginatedResponse, Participation } from '../../types';
import { formadoresLabel } from '../../utils/participants';
import { mesmosDados } from '../../utils/mesmosDados';
import { pausaDo429Ms } from '../../utils/retryAfter';
import AvisoAtualizacaoPausada from '../../components/AvisoAtualizacaoPausada';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';

// #1668 (M12-19): orçamento de requisições da Pré-agenda.
/** Carrega a pré-agenda inteira como lista única (paginação client-side). */
const PREAGENDA_PAGE_SIZE = 100;
/** Uma mensagem só para a falha de carga: a atualização automática não empilha erros. */
const LOAD_ERROR_KEY = 'preagenda-erro-carga';

const { Title, Text } = Typography;

/** Uma linha da célula, cortada com reticências (o texto inteiro fica no `title`). */
const UMA_LINHA: CSSProperties = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };

// Contraste AA (4,5:1) do estado no Google: o preset do AntD pinta a cor 6 sobre a cor 1 (success 2,21,
// processing 3,66, error 2,99:1) e o Text danger, a 12 px no branco, dá 3,27:1. Mesmo padrão de
// TEXTO_DA_TAG (components/textoDaTag.ts), que só cobre green, orange e gold.
const TEXTO_DA_TAG_GCAL: Partial<Record<GcalRowTag['color'], string>> = {
  success: '#237804', // green-8: 5,44:1
  processing: '#0958d9', // blue-7: 5,50:1
  error: '#b32430', // red-8: 5,98:1
};
const COR_DO_MOTIVO_DO_ERRO = '#b32430'; // red-8: 6,54:1 no branco
// Linha marcada para o lote (tema claro): o AntD tira o fundo do colorPrimary (o verde da marca clareado para #9aaba4;
// com o mouse, #659e89) e o motivo do erro caía para 2,72 e 2,12:1. Mesmo verde claro da tela Aprovações.
const FUNDO_DA_LINHA_MARCADA = '#f4faf7';
const TEMA_DA_TABELA = {
  components: { Table: { rowSelectedBg: FUNDO_DA_LINHA_MARCADA, rowSelectedHoverBg: FUNDO_DA_LINHA_MARCADA } },
};
// Pendente e reenviar: o gold-6 (#faad14) dá 1,90:1 no branco; publicado: o green-6 (#52c41a), 2,27:1.
const COR_PENDENTE = '#ad4e00'; // orange-8: 5,43:1 no branco, 4,99:1 no bg-blue-50 da barra do lote
const COR_PUBLICADO = '#237804'; // green-8: 5,59:1

/**
 * Junta as listas dos fluxos na ordem de `?ordering=proximidade` do servidor: de hoje em diante, do
 * mais próximo ao mais distante; depois os passados, do mais recente ao mais antigo. "Hoje" é o
 * início do dia em Fortaleza.
 *
 * Cada fluxo é cortado no servidor de forma independente. Se um veio cortado, a lista juntada para
 * no último evento dele (o mais cedo, se os dois vieram cortados); eventos no mesmo horário ficam,
 * porque estão à mesma distância de hoje. Sem o corte, eventos do outro fluxo depois desse ponto
 * entravam e os do fluxo cortado sumiam no meio da lista.
 */
function porProximidade(listas: Array<PaginatedResponse<Solicitacao> | Solicitacao[]>): Solicitacao[] {
  const hoje = dayjs().tz(FORTALEZA_TZ).startOf('day').valueOf();
  const distancia = (r: Solicitacao): [number, number] => {
    const t = Date.parse(r.inicio);
    return t >= hoje ? [0, t] : [1, -t];
  };
  const compararDistancia = (a: Solicitacao, b: Solicitacao): number => {
    const [ga, ta] = distancia(a);
    const [gb, tb] = distancia(b);
    return ga - gb || ta - tb;
  };
  const comparar = (a: Solicitacao, b: Solicitacao): number => compararDistancia(a, b) || Number(a.id) - Number(b.id);

  const ultimosDosCortados = listas
    .filter((d): d is PaginatedResponse<Solicitacao> => 'results' in d && d.results.length > 0 && d.results.length < d.count)
    .map((d) => [...d.results].sort(comparar)[d.results.length - 1] as Solicitacao)
    .sort(comparar);
  const juntas = listas.flatMap((d) => ('results' in d ? d.results : d)).sort(comparar);
  const horizonte = ultimosDosCortados[0];
  return horizonte ? juntas.filter((r) => compararDistancia(r, horizonte) <= 0) : juntas;
}

/** O evento como a pessoa o reconhece: "05/11/2026 09:00 · Sobral · Projeto X" (botões e confirmações). */
function rotuloDoEvento(row: Solicitacao): string {
  return [formatFortaleza(row.inicio), row.municipio_nome, row.projeto_nome].filter(Boolean).join(' · ');
}
const { RangePicker } = DatePicker;

/** Google Calendar event from API */
interface GoogleCalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  status: string;
  htmlLink: string;
  location: string;
  creator: string;
}

type ViewMode = 'preagenda' | 'gcal-events';

/** Preview data type */
interface PreviewDataType {
  preview: {
    payload?: {
      summary?: string;
      start?: { dateTime?: string };
      end?: { dateTime?: string };
      location?: string;
      description?: string;
      conferenceData?: unknown;
      attendees?: Array<{ email: string; responseStatus?: string }>;
    };
    event_id?: string;
    payload_hash?: string;
    meet_link?: string;
  };
}

export default function PreAgendaPage(): JSX.Element {
  const [loading, setLoading] = useState<boolean>(false);
  const [rows, setRows] = useState<Solicitacao[]>([]);
  const [total, setTotal] = useState<number>(0);
  // Quantos aprovados o servidor tem com estes filtros (os dois fluxos): mais que `total` = lista cortada.
  const [noServidor, setNoServidor] = useState<number>(0);
  // Uma carga pedida pela pessoa recebeu 429: a tela pode não corresponder ao pedido.
  const [cargaFalhou, setCargaFalhou] = useState<boolean>(false);
  // A carga pedida pela pessoa falhou (fora o 429): o motivo vai no lugar das linhas, não o vazio.
  const [erroCarga, setErroCarga] = useState<string | null>(null);

  const [summary, setSummary] = useState<GCalStatusSummary>({
    counts: { NONE: 0, PENDING: 0, PUBLISHED: 0, ERROR: 0 },
    total: 0,
  });

  const [searchTerm, setSearchTerm] = useState<string>('');
  // PR A: filtro por gerência (id) — o mesmo na lista e nos KPIs. Só gerências ativas.
  const [gerenciaFilter, setGerenciaFilter] = useState<ID | null>(null);
  const [gerencias, setGerencias] = useState<Gerencia[]>([]);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);

  const [previewVisible, setPreviewVisible] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<PreviewDataType | null>(null);

  // Issue #95: Batch operations - Row selection
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [batchLoading, setBatchLoading] = useState<boolean>(false);

  // View mode: pré-agenda (solicitações) ou eventos Google Calendar
  const [viewMode, setViewMode] = useState<ViewMode>('preagenda');
  const [gcalEvents, setGcalEvents] = useState<GoogleCalendarEvent[]>([]);
  const [loadingGcalEvents, setLoadingGcalEvents] = useState(false);
  // #1294: filtro de datas próprio do modo gcal-events, isolado do `dateRange`
  // das Solicitações. Sem isso, um período escolhido em "Solicitações" vazava
  // como time_min/time_max na request de eventos (falso-vazio) e mexer no
  // RangePicker de eventos recriava `loadData` (refetch cruzado de Solicitações).
  const [gcalDateRange, setGcalDateRange] = useState<[Dayjs | null, Dayjs | null]>([null, null]);
  const [gcalCalendarId, setGcalCalendarId] = useState<string | null>(null);
  // A carga dos eventos falhou: o motivo fica no lugar dos eventos, não o vazio "calendário sem eventos".
  const [gcalErro, setGcalErro] = useState<string | null>(null);
  const gcalHasDateFilter = !!(gcalDateRange[0] || gcalDateRange[1]);

  // OAuth Phase 5: acesso (AcessoContext) e integração Google
  const { caps, ehSuperusuario } = useAcesso();
  const temaEscuro = useContext(ThemeContext)?.isDark === true; // o escuro tem fundo próprio (App.css)
  const { status: googleStatus, disconnect: googleDisconnect, fetchStatus: googleFetchStatus } = useGoogleIntegration();

  // Volta do OAuth (?google=connected | ?google=error&reason=…): mostra o resultado, tira os parâmetros
  // da URL e recarrega o status. A tela não usa o roteador, então lê e limpa a URL do navegador
  // (mantendo o history.state do roteador).
  const [oauthRetorno, setOauthRetorno] = useState<OAuthRetorno | null>(null);
  useEffect(() => {
    const retorno = lerOAuthRetorno(window.location.search);
    if (!retorno) return;
    setOauthRetorno(retorno);
    window.history.replaceState(window.history.state, '', window.location.pathname);
    void googleFetchStatus();
  }, [googleFetchStatus]);

  // Section 4 Epic #459: Consolidated Google OAuth guard
  const { requireGoogleConnection, handleGoogleError } = useGoogleGuard({
    googleStatus,
    returnTo: '/pre-agenda',
  });

  // Gerências do filtro
  useEffect(() => {
    getGerencias({ ativo: true })
      .then((data) => setGerencias([...data].sort((a, b) => a.rotulo.localeCompare(b.rotulo, 'pt-BR'))))
      .catch((error: unknown) => logger.error('Erro ao carregar gerências:', error));
  }, []);

  // #1668 (M12-19): controle do ciclo de requisições.
  // - seqRef: guarda de sequência (latest-wins) — descarta resposta obsoleta.
  // - 429: o polling é pausado pelo tempo do Retry-After (usePolling.pausar).
  // - filtersRef: mantém loadData estável (não recria a cada tecla).
  const seqRef = useRef(0);
  const filtersRef = useRef({ searchTerm, gerenciaFilter, dateRange });
  filtersRef.current = { searchTerm, gerenciaFilter, dateRange };

  // RT-02: polling para sync cross-device (#1032; intervalo em constants/timing.ts).
  // immediate:false → a carga inicial é do efeito de filtro (sem carga dupla).
  const loadDataRef = useRef<(silencioso?: boolean) => Promise<void>>(() => Promise.resolve());
  const { pausado: pollingPausado, pausar: pausarPolling } = usePolling(() => loadDataRef.current(true), {
    enabled: true,
    intervalMs: TIMING.LIST_POLL_INTERVAL_MS,
    immediate: false,
    events: ['preagenda:refresh', 'solicitacoes:refresh'],
  });

  /**
   * `silencioso`: atualização em segundo plano (polling, outra aba). Não liga o
   * carregamento da tabela; os dados antigos ficam na tela até chegarem os novos.
   */
  const loadData = useCallback(async (silencioso = false): Promise<void> => {
    const seq = ++seqRef.current;
    try {
      if (!silencioso) setLoading(true);

      const { searchTerm, gerenciaFilter, dateRange } = filtersRef.current;
      const filters: Record<string, string> = {};
      if (searchTerm) filters['q'] = searchTerm;
      if (gerenciaFilter) filters['gerencia_id'] = String(gerenciaFilter);
      if (dateRange[0]) filters['date_from'] = dateRange[0].format('YYYY-MM-DD');
      if (dateRange[1]) filters['date_to'] = dateRange[1].format('YYYY-MM-DD');

      // page_size alto: a pré-agenda é uma lista única (paginação client-side),
      // então carrega o conjunto de aprovados de uma vez, não só a 1ª página.
      // `status` vai SÓ na lista: no resumo GCal, `status` é o gcal_status (o resumo já
      // conta só aprovados) — mandar `approved` lá zerava os KPIs.
      // `proximidade`: os 100 mais próximos de hoje. Sem ordem, o padrão do servidor (-inicio) trazia os
      // 100 mais distantes no futuro, e os eventos desta semana sumiam (achado do item 36).
      const listParams = { ...filters, status: 'approved' as const, page_size: PREAGENDA_PAGE_SIZE, ordering: 'proximidade' };
      const [superData, naoSuperData, summaryData] = await Promise.all([
        listSolicitacoes({ ...listParams, flow: 'SUPER' }) as Promise<PaginatedResponse<Solicitacao> | Solicitacao[]>,
        listSolicitacoes({ ...listParams, flow: 'NAO_SUPER' }) as Promise<PaginatedResponse<Solicitacao> | Solicitacao[]>,
        getStatusSummary(filters),
      ]);

      if (seq !== seqRef.current) return; // carga obsoleta: uma mais nova venceu

      const loadedRows = porProximidade([superData, naoSuperData]);
      const contagem = (dados: PaginatedResponse<Solicitacao> | Solicitacao[]): number =>
        'results' in dados ? dados.count : dados.length;

      // Só troca o estado se algo mudou: resposta igual não redesenha a tabela.
      setRows((atuais) => (mesmosDados(atuais, loadedRows) ? atuais : loadedRows));
      // Contador honesto: exibe o total efetivamente carregado, nunca o count do
      // servidor sobre uma lista de 1 página (total inalcançável).
      setTotal(loadedRows.length);
      setNoServidor(contagem(superData) + contagem(naoSuperData));
      setSummary((atual) => (mesmosDados(atual, summaryData) ? atual : summaryData));
      setCargaFalhou(false);
      setErroCarga(null);
    } catch (error) {
      if (seq !== seqRef.current) return; // erro de carga obsoleta: não polui a UI
      // 429 (muitas requisições): pausa o polling pelo tempo pedido e mostra um aviso só.
      // Se a carga foi pedida pela pessoa, o aviso diz que a lista não carregou.
      const pausa = pausaDo429Ms(error);
      if (pausa !== null) {
        pausarPolling(pausa);
        if (!silencioso) setCargaFalhou(true);
        return;
      }
      // Pedida pela pessoa: o motivo e "Tentar de novo" no lugar das linhas (um toast some em 3 s e a
      // tabela ficava vazia). No segundo plano, a lista que já estava na tela fica, com o toast.
      if (!silencioso) {
        setErroCarga((error as Error).message || 'Erro desconhecido.');
        return;
      }
      message.error({
        key: LOAD_ERROR_KEY,
        content: 'Erro ao carregar pré-agenda: ' + (error as Error).message,
      });
    } finally {
      if (seq === seqRef.current) setLoading(false);
    }
  }, [pausarPolling]);
  loadDataRef.current = loadData;

  // Carga inicial imediata no mount + recargas por filtro com debounce: o valor
  // digitado nunca dispara um request por tecla, e não há carga dupla (o polling
  // roda com immediate:false).
  const firstRunRef = useRef(true);
  useEffect(() => {
    if (firstRunRef.current) {
      firstRunRef.current = false;
      void loadData();
      return;
    }
    const timer = setTimeout(() => {
      void loadData();
    }, TIMING.DEBOUNCE_SEARCH_MS);
    return () => clearTimeout(timer);
  }, [searchTerm, gerenciaFilter, dateRange, loadData]);

  // RT-02: BroadcastChannel for instant cross-tab sync
  useEffect(() => {
    const unsub1 = syncChannel.subscribe('preagenda', () => { void loadData(true); });
    const unsub2 = syncChannel.subscribe('solicitacoes', () => { void loadData(true); });
    return () => { unsub1(); unsub2(); };
  }, [loadData]);

  // Issue #260: Memoizar handlers para evitar re-renderização desnecessária
  const handlePreview = useCallback(async (id: ID): Promise<void> => {
    try {
      const data = await previewSolicitacao(id) as unknown as PreviewDataType;
      setPreviewData(data);
      setPreviewVisible(true);
    } catch (error) {
      message.error('Erro ao visualizar payload: ' + (error as Error).message);
    }
  }, []);

  const handlePublish = useCallback((id: ID): void => {
    // Section 4 Epic #459: Use consolidated Google guard
    if (!requireGoogleConnection('publicar eventos')) return;

    Modal.confirm({
      title: 'Confirmar Publicação',
      content: 'Deseja publicar este evento no Google Calendar?',
      okText: 'Publicar',
      okType: 'primary',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          // O backend enfileira a publicação (sempre 202 Accepted) — a
          // sincronização com o Google Calendar é assíncrona. Não anunciar
          // "publicado" (isso implicaria conclusão); sinalizar o enfileiramento.
          await publishSolicitacao(id, { dry_run: false });
          message.info(
            'Publicação enfileirada no Google Calendar — o evento aparecerá como publicado em instantes.',
          );
          void loadData();
        } catch (error) {
          // Section 4 Epic #459: Use consolidated error handler
          if (handleGoogleError(error)) return;
          message.error('Erro ao publicar: ' + (error as Error).message);
        }
      },
    });
  }, [requireGoogleConnection, handleGoogleError, loadData]);

  const handleResync = useCallback((id: ID): void => {
    // Section 4 Epic #459: Use consolidated Google guard
    if (!requireGoogleConnection('reenviar eventos')) return;

    Modal.confirm({
      title: 'Confirmar Reenvio',
      icon: <SyncOutlined className="text-yellow-500" />,
      content: (
        <div>
          <p>Deseja reenviar (forçar UPDATE) este evento no Google Calendar?</p>
          <p className="text-gray-500 text-xs">
            Esta ação irá sobrescrever o evento existente com os dados atualizados.
          </p>
        </div>
      ),
      okText: 'Reenviar',
      okType: 'default',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await resyncSolicitacao(id);
          message.success('Reenvio solicitado! O evento será atualizado em instantes.');
          void loadData();
        } catch (error) {
          // Section 4 Epic #459: Use consolidated error handler
          if (handleGoogleError(error)) return;
          message.error('Erro ao reenviar: ' + (error as Error).message);
        }
      },
    });
  }, [requireGoogleConnection, handleGoogleError, loadData]);

  // Remover do Google tira o convite e o link do Meet de todos: a confirmação abre no Cancelar,
  // cita o evento e diz que a solicitação continua aprovada ("Cancelar Evento" sugeria cancelá-la).
  const handleCancel = useCallback((record: Solicitacao): void => {
    const id = record.id;
    Modal.confirm({
      title: `Remover do Google Agenda: ${rotuloDoEvento(record)}?`,
      icon: <StopOutlined className="text-red-500" />,
      content: (
        <div>
          <p>O evento e o link do Meet saem do Google Agenda.</p>
          <p>A solicitação continua aprovada no sistema e pode ser publicada de novo.</p>
        </div>
      ),
      okText: 'Remover do Google',
      okType: 'danger',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await cancelSolicitacao(id);
          message.success('Cancelamento solicitado! O evento será removido em instantes.');
          void loadData();
        } catch (error) {
          message.error('Erro ao cancelar: ' + (error as Error).message);
        }
      },
    });
  }, [loadData]);

  // Issue #95: Batch Reapply
  const handleBatchReapply = (): void => {
    // Section 4 Epic #459: Use consolidated Google guard
    if (!requireGoogleConnection('realizar ações em massa')) return;

    if (selectedRowKeys.length === 0) {
      message.warning('Selecione ao menos um evento para reaplica');
      return;
    }

    Modal.confirm({
      title: `Confirmar Reapply em Massa (${selectedRowKeys.length} eventos)`,
      icon: <SyncOutlined className="text-yellow-500" />,
      content: (
        <div>
          <p>Deseja reenviar (forçar UPDATE) estes {selectedRowKeys.length} eventos no Google Calendar?</p>
          <p className="text-gray-500 text-xs">
            Esta ação irá sobrescrever os eventos existentes com os dados atualizados.
          </p>
        </div>
      ),
      okText: 'Reenviar',
      okType: 'default',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const data = await reapplyBatch({
            ids: selectedRowKeys as ID[],
            dry_run: false,
            apply_blocked: true,
          });

          message.success(`${data.queued} eventos enfileirados para reapply!`);
          if (data.errors && data.errors.length > 0) {
            message.warning(
              `${data.errors.length} erros: ${data.errors.map((e) => e.detail || e.error || 'erro').join(', ')}`
            );
          }
          setSelectedRowKeys([]);
          void loadData();
        } catch (error) {
          if (handleGoogleError(error)) return;
          message.error('Erro ao reenviar em massa: ' + (error as Error).message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // Issue #95: Batch Resync
  const handleBatchResync = (): void => {
    // Section 4 Epic #459: Use consolidated Google guard
    if (!requireGoogleConnection('realizar ações em massa')) return;

    if (selectedRowKeys.length === 0) {
      message.warning('Selecione ao menos um evento para resync');
      return;
    }

    Modal.confirm({
      title: `Confirmar Resync em Massa (${selectedRowKeys.length} eventos)`,
      icon: <SyncOutlined className="text-red-500" />,
      content: (
        <div>
          <p>Deseja forçar resync (resetar hash + PENDING) destes {selectedRowKeys.length} eventos?</p>
          <p className="text-gray-500 text-xs">
            Útil para corrigir drift ou reprocessar eventos com erros.
          </p>
        </div>
      ),
      okText: 'Resync',
      okType: 'danger',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const data = await resyncBatch({
            ids: selectedRowKeys as ID[],
            dry_run: false,
            apply_blocked: true,
          });

          message.success(`${data.queued} eventos enfileirados para resync!`);
          if (data.errors && data.errors.length > 0) {
            message.warning(
              `${data.errors.length} erros: ${data.errors.map((e) => e.detail || e.error || 'erro').join(', ')}`
            );
          }
          setSelectedRowKeys([]);
          void loadData();
        } catch (error) {
          if (handleGoogleError(error)) return;
          message.error('Erro ao resync em massa: ' + (error as Error).message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // Celular: os ícones das ações quebram em duas por linha e a página perde padding.
  const celular = !Grid.useBreakpoint().sm;

  // Sem rolagem horizontal (achado do item 36): sempre na linha, o Evento (data/hora, município,
  // projeto e o estado no Google, com o motivo do erro) e as ações; o resto sobe por largura e,
  // escondido, vai para a linha expandida.
  // Issue #260: Memoizar columns para evitar re-renderização desnecessária da tabela
  const columns: ColunaResponsiva<Solicitacao>[] = useMemo(() => [
    {
      title: 'Evento',
      key: 'evento',
      render: (_, record) => {
        // Rótulo em pt-BR (o mesmo de Publicar na agenda) e, em ERROR, o motivo que o backend gravou
        // (`gcal_last_error`, que diz o que fazer): antes só o código cru, e o Controle reenviava às cegas.
        const { tag } = gcalRowActions(record, { ready: true });
        return (
          <Space direction="vertical" size={2} className="w-full">
            <div style={UMA_LINHA}>{formatFortaleza(record.inicio)}</div>
            <div style={UMA_LINHA} title={record.municipio_nome || undefined}>{record.municipio_nome || '-'}</div>
            <div style={UMA_LINHA} title={record.projeto_nome || undefined}>{record.projeto_nome || '-'}</div>
            <Tag color={tag.color} style={{ whiteSpace: 'normal', color: TEXTO_DA_TAG_GCAL[tag.color] }}>{tag.label}</Tag>
            {record.gcal_status === 'ERROR' && record.gcal_last_error && (
              <Text type="danger" style={{ color: COR_DO_MOTIVO_DO_ERRO, fontSize: 12, whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
                {record.gcal_last_error}
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      responsive: VISIVEL_A_PARTIR.lg,
      ellipsis: true,
      render: (tipo) => (tipo as string | null) || '-',
    },
    {
      // Nome do formador (inclui convidados "que saíram" via guest_nome — sem FK). Ver utils/participants.
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      responsive: VISIVEL_A_PARTIR.lg,
      ellipsis: true,
      render: (participations) => formadoresLabel(participations as Participation[] | undefined) || '-',
    },
    {
      title: 'Meet',
      dataIndex: 'meet_link',
      key: 'meet',
      responsive: VISIVEL_A_PARTIR.xl,
      width: 170,
      // Os dois botões do MeetLink quebram linha em vez de passar da célula.
      render: (href) => (
        <div className="[&_.ant-space]:flex-wrap">
          <MeetLink href={href as string | null} />
        </div>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      // Até 4 ícones; no celular, dois por linha.
      width: celular ? 76 : 128,
      render: (_, record) => {
        const isPublished = record.gcal_status === ('PUBLISHED' as GCalStatus);
        // PENDING = publicação já enfileirada (task Celery em voo). Bloquear o
        // botão evita reenfileirar em cima de uma publicação em andamento.
        const isPending = record.gcal_status === ('PENDING' as GCalStatus);
        const hasError = record.gcal_status === ('ERROR' as GCalStatus);
        const hasEventId = !!record.external_event_id;

        // Resync: mostrar quando PUBLISHED ou ERROR
        const showResync = isPublished || hasError;

        // Cancel: mostrar apenas quando PUBLISHED e tem event_id
        const showCancel = isPublished && hasEventId;

        // Virada: evento que já terminou, ou que está no Google pela planilha, não se publica
        // (o backend recusa com o mesmo motivo). O motivo vai no nome acessível do botão.
        const motivo = motivoNaoPublicavel(record);
        const publicarLabel = motivo
          ? `Publicar evento no Google Calendar: ${MOTIVO_NAO_PUBLICAVEL[motivo]}`
          : 'Publicar evento no Google Calendar';

        return (
          <Space size={4} wrap>
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handlePreview(record.id)}
              aria-label="Visualizar preview do evento"
            />
            <Button
              size="small"
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={() => handlePublish(record.id)}
              aria-label={publicarLabel}
              title={motivo ? MOTIVO_NAO_PUBLICAVEL[motivo] : undefined}
              disabled={isPublished || isPending || motivo !== null}
            />
            {showResync && (
              <Button
                size="small"
                type="default"
                icon={<SyncOutlined />}
                onClick={() => handleResync(record.id)}
                aria-label="Reenviar evento (forçar atualização)"
                style={{ color: COR_PENDENTE, borderColor: COR_PENDENTE }}
              />
            )}
            {showCancel && (
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => handleCancel(record)}
                aria-label={`Remover do Google Agenda: ${rotuloDoEvento(record)}`}
              />
            )}
          </Space>
        );
      },
    },
  ], [handlePreview, handlePublish, handleResync, handleCancel, celular]);

  // Google Calendar events loader
  const loadGcalEvents = useCallback(async (): Promise<void> => {
    try {
      setLoadingGcalEvents(true);
      const params = new URLSearchParams();
      if (gcalDateRange[0]) params.set('time_min', gcalDateRange[0].format('YYYY-MM-DD'));
      if (gcalDateRange[1]) params.set('time_max', gcalDateRange[1].format('YYYY-MM-DD'));
      params.set('max_results', '250');

      const data = await fetchAPI<{ events: GoogleCalendarEvent[]; calendar_id: string; count: number }>(
        `/integrations/google/events/?${params.toString()}`
      );
      setGcalEvents(data.events || []);
      setGcalCalendarId(data.calendar_id ?? null);
      setGcalErro(null);
    } catch (error) {
      // O motivo vai no lugar dos eventos (um toast some em 3 s e deixava o vazio "calendário sem eventos").
      const resposta = (error as { response?: { status?: number; data?: { code?: string } } }).response;
      if (resposta?.data?.code === 'google_calendar_not_configured') {
        // Servidor sem a configuração OAuth do Google: a mensagem do 409 diz o que fazer (ensaio r3).
        setGcalErro((error as Error).message);
      } else if (resposta?.status === 503) {
        setGcalErro('O Google Calendar demorou a responder. Tente novamente em instantes.');
      } else {
        setGcalErro('Erro ao carregar eventos do Google Calendar');
      }
      logger.error('Erro ao carregar eventos GCal:', error);
    } finally {
      setLoadingGcalEvents(false);
    }
  }, [gcalDateRange]);

  // Carregar eventos GCal quando mudar para a aba
  useEffect(() => {
    if (viewMode === 'gcal-events' && googleStatus?.connected) {
      void loadGcalEvents();
    }
  }, [viewMode, googleStatus?.connected, loadGcalEvents]);

  const formatGcalDate = (dateStr: string): string => {
    if (!dateStr) return '-';
    try {
      return formatFortaleza(dateStr);
    } catch {
      return dateStr;
    }
  };

  const gcalEventsColumns: ColunaResponsiva<GoogleCalendarEvent>[] = [
    {
      title: 'Evento',
      dataIndex: 'summary',
      key: 'summary',
      // No celular o nome quebra linha: cortado, ficaria só no `title`, que o toque não mostra.
      ellipsis: !celular,
    },
    {
      title: 'Início',
      dataIndex: 'start',
      key: 'start',
      width: 150,
      render: (val) => formatGcalDate(val as string),
      sorter: (a: GoogleCalendarEvent, b: GoogleCalendarEvent) => a.start.localeCompare(b.start),
      defaultSortOrder: 'ascend',
    },
    {
      title: 'Fim',
      dataIndex: 'end',
      key: 'end',
      width: 150,
      responsive: VISIVEL_A_PARTIR.lg,
      render: (val) => formatGcalDate(val as string),
    },
    {
      title: 'Local',
      dataIndex: 'location',
      key: 'location',
      ellipsis: true,
      responsive: VISIVEL_A_PARTIR.md,
      render: (val) => (val as string) || '-',
    },
    {
      title: 'Criador',
      dataIndex: 'creator',
      key: 'creator',
      ellipsis: true,
      responsive: VISIVEL_A_PARTIR.xl,
    },
    {
      title: 'Link',
      dataIndex: 'htmlLink',
      key: 'htmlLink',
      width: 70,
      // Abaixo de md, na linha expandida: os 70 px ficam para o nome do evento.
      responsive: VISIVEL_A_PARTIR.md,
      render: (val) =>
        val ? (
          <a href={val as string} target="_blank" rel="noopener noreferrer" aria-label="Abrir no Google Agenda">
            <LinkOutlined />
          </a>
        ) : '-',
    },
  ];

  // OAuth Phase 5: o cartão do Google é de quem opera o Controle (a mesma policy da rota).
  const showGoogleCard = caps.canAccessControleSection;

  // Handlers para o card Google
  const handleGoogleConnect = (): void => {
    window.location.href = `/api/oauth/google/start/?return_to=/pre-agenda`;
  };

  const handleGoogleDisconnect = async (): Promise<void> => {
    try {
      const result = await googleDisconnect();

      if (result.success) {
        message.success('Conta Google desconectada com sucesso');
      } else {
        message.error(result.error || 'Erro ao desconectar conta Google');
      }
    } catch (error) {
      message.error('Erro ao desconectar: ' + (error as Error).message);
    }
  };

  // Row selection config
  const rowSelection: TableRowSelection<Solicitacao> = {
    selectedRowKeys,
    onChange: (keys: Key[]) => setSelectedRowKeys(keys),
    // A seleção alimenta Reaplicar/Reenviar: só o que já foi ao Google e não terminou (o backend
    // recusa o resto, e no `NONE` o reenvio criaria um evento). O motivo fica no nome acessível.
    getCheckboxProps: (record: Solicitacao) => {
      const motivo = motivoNaoPublicavel(record, { reenvio: true });
      return {
        disabled: motivo !== null,
        'aria-label': motivo ? `Selecionar evento: ${MOTIVO_NAO_PUBLICAVEL[motivo]}` : 'Selecionar evento',
      };
    },
    // `true`: os atalhos padrão do AntD (tudo, inverter, nada) sem importar o `Table` cru.
    selections: true,
  };

  return (
    <div className="p-3 sm:p-6">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Header */}
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Title level={2} className="m-0">
              Pré-agenda
            </Title>
            {googleStatus?.connected && (
              <Segmented
                value={viewMode}
                onChange={(val) => setViewMode(val as ViewMode)}
                options={[
                  { label: 'Solicitações', value: 'preagenda', icon: <UnorderedListOutlined /> },
                  { label: 'Eventos Google Calendar', value: 'gcal-events', icon: <CalendarOutlined /> },
                ]}
              />
            )}
          </div>
        </Card>

        {oauthRetorno && <OAuthRetornoAlert retorno={oauthRetorno} textoSucesso="Conta Google conectada." />}

        {/* OAuth Phase 5: Google Integration Card (Controle/Super apenas) */}
        {showGoogleCard && (
          <GoogleIntegrationCard
            status={googleStatus}
            onConnect={handleGoogleConnect}
            onDisconnect={handleGoogleDisconnect}
          />
        )}

        {/* View: Solicitações (Pré-agenda) */}
        {viewMode === 'preagenda' && (
          <>
            {(pollingPausado || cargaFalhou) && <AvisoAtualizacaoPausada cargaFalhou={cargaFalhou} />}

            {/* Resumo GCal */}
            <Card title="Resumo de Status GCal" size="small">
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic title="Não Publicados" value={summary.counts?.NONE || 0} />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="Pendentes"
                    value={summary.counts?.PENDING || 0}
                    valueStyle={{ color: COR_PENDENTE }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="Publicados"
                    value={summary.counts?.PUBLISHED || 0}
                    valueStyle={{ color: COR_PUBLICADO }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="Erros"
                    value={summary.counts?.ERROR || 0}
                    valueStyle={{ color: '#ff4d4f' }}
                  />
                </Col>
              </Row>
            </Card>

            {/* Filtros */}
            <Card size="small">
              <Space direction="vertical" style={{ width: '100%' }}>
                {/* wrap: em tela estreita os filtros quebram linha (sem rolagem horizontal). */}
                <Space wrap>
                  <Input.Search
                    placeholder="Buscar por município, projeto..."
                    value={searchTerm}
                    onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
                    onSearch={() => { void loadData(); }}
                    style={{ width: '100%', maxWidth: 300 }}
                    allowClear
                  />
                  <Select
                    aria-label="Filtrar por gerência"
                    placeholder="Filtrar por gerência"
                    value={gerenciaFilter ?? undefined}
                    onChange={(value?: ID) => setGerenciaFilter(value ?? null)}
                    options={gerencias.map((g) => ({ label: g.rotulo, value: g.id }))}
                    showSearch
                    optionFilterProp="label"
                    className="w-full sm:w-[200px]"
                    allowClear
                  />
                  <RangePicker
                    value={dateRange}
                    onChange={(dates) => setDateRange(dates || [null, null])}
                    format="DD/MM/YYYY"
                    placeholder={['Data inicial', 'Data final']}
                  />
                </Space>
              </Space>
            </Card>

            {/* Tabela */}
            <Card {...(celular && { styles: { body: { padding: 12 } } })}>
              {/* Issue #95: Toolbar de Ações em Massa */}
              {selectedRowKeys.length > 0 && (
                <div className="mb-4 p-3 bg-blue-50 rounded">
                  <Space wrap>
                    <Text strong>{selectedRowKeys.length} evento(s) selecionado(s)</Text>
                    <Button
                      type="default"
                      icon={<SyncOutlined />}
                      onClick={handleBatchReapply}
                      loading={batchLoading}
                      style={{ color: COR_PENDENTE, borderColor: COR_PENDENTE }}
                    >
                      Reapply Selecionados
                    </Button>
                    <Button
                      danger
                      icon={<SyncOutlined />}
                      onClick={handleBatchResync}
                      loading={batchLoading}
                    >
                      Resync Selecionados
                    </Button>
                    <Button
                      type="link"
                      onClick={() => setSelectedRowKeys([])}
                    >
                      Limpar Seleção
                    </Button>
                  </Space>
                </div>
              )}
              {noServidor > total && !erroCarga && (
                <Alert
                  className="mb-4"
                  type="info"
                  showIcon
                  role="status"
                  message={
                    `Mostrando ${total} de ${noServidor} eventos aprovados, os mais próximos de hoje. ` +
                    'Para ver os demais, filtre por data, gerência ou busca.'
                  }
                />
              )}
              <ConfigProvider {...(!temaEscuro && { theme: TEMA_DA_TABELA })}>
                <ResponsiveTable<Solicitacao>
                  columns={columns}
                  dataSource={rows}
                  loading={loading}
                  rowKey="id"
                  rowSelection={rowSelection}
                  nomeDaLinha={rotuloDoEvento}
                  erro={erroCarga}
                  onTentarDeNovo={() => { void loadData(); }}
                  pagination={{
                    total,
                    pageSize: 20,
                    showTotal: (total) => `Total: ${total} ${total === 1 ? 'evento aprovado' : 'eventos aprovados'}`,
                  }}
                />
              </ConfigProvider>
            </Card>

            {/* Rodapé */}
            <Alert
              message="Operações em Lote"
              description={
                <Text>
                  Selecione múltiplos eventos na tabela para atualizar ou republicar no Google Calendar.
                </Text>
              }
              type="info"
              icon={<InfoCircleOutlined />}
              showIcon
            />
          </>
        )}

        {/* View: Eventos Google Calendar */}
        {viewMode === 'gcal-events' && (
          <>
            <Card size="small">
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Space wrap>
                  <RangePicker
                    value={gcalDateRange}
                    onChange={(dates) => setGcalDateRange(dates || [null, null])}
                    format="DD/MM/YYYY"
                    placeholder={['Data inicial', 'Data final']}
                  />
                  <Button
                    type="primary"
                    icon={<SyncOutlined />}
                    onClick={loadGcalEvents}
                    loading={loadingGcalEvents}
                  >
                    Atualizar
                  </Button>
                  {!gcalErro && (
                    <Tag color="blue">{gcalEvents.length} {gcalEvents.length === 1 ? 'evento' : 'eventos'}</Tag>
                  )}
                </Space>
                {/* #1295: contexto do que está sendo exibido (calendário + janela); sem carga, sem calendário lido */}
                <Space size="middle" wrap>
                  {!gcalErro && (
                    <Text type="secondary">
                      <CalendarOutlined /> Calendário:{' '}
                      <Text strong>{gcalCalendarId ?? googleStatus?.googleEmail ?? '—'}</Text>
                    </Text>
                  )}
                  <Text type="secondary">
                    <ClockCircleOutlined /> Período:{' '}
                    <Text strong>
                      {gcalHasDateFilter
                        ? `${gcalDateRange[0]?.format('DD/MM/YYYY') ?? '…'} – ${gcalDateRange[1]?.format('DD/MM/YYYY') ?? '…'}`
                        : 'todas as datas'}
                    </Text>
                  </Text>
                </Space>
              </Space>
            </Card>

            <Card>
              {loadingGcalEvents ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" />
                  <div style={{ marginTop: 16 }}>
                    <Text type="secondary">Carregando eventos do Google Calendar...</Text>
                  </div>
                </div>
              ) : gcalEvents.length === 0 && !gcalErro ? (
                gcalHasDateFilter ? (
                  // #1295: vazio COM filtro de data → orienta a ajustar a janela,
                  // em vez de sugerir que o calendário está vazio.
                  <Empty
                    description={
                      <span>
                        Nenhum evento no período selecionado. Ajuste o filtro de datas
                        (ou limpe-o) para ver todos os eventos do calendário.
                      </span>
                    }
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                ) : (
                  <Empty
                    description="Nenhum evento encontrado neste calendário"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                )
              ) : (
                <ResponsiveTable<GoogleCalendarEvent>
                  columns={gcalEventsColumns}
                  dataSource={gcalEvents}
                  rowKey="id"
                  size="small"
                  nomeDaLinha={(evento) => evento.summary || 'evento'}
                  erro={gcalErro}
                  onTentarDeNovo={() => { void loadGcalEvents(); }}
                  pagination={{
                    pageSize: 20,
                    showSizeChanger: true,
                    showTotal: (total) => `${total} ${total === 1 ? 'evento' : 'eventos'}`,
                  }}
                />
              )}
            </Card>
          </>
        )}
      </Space>

      {/* Modal Preview */}
      <Modal
        title={
          <Space>
            <CalendarOutlined />
            <span>Preview do Evento Google Calendar</span>
          </Space>
        }
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Fechar
          </Button>,
        ]}
        width={800}
      >
        {previewData?.preview && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* Título do Evento */}
            <Card size="small">
              <Title level={4} className="m-0">
                {previewData.preview.payload?.summary || 'Sem título'}
              </Title>
            </Card>

            {/* Informações Principais */}
            <Descriptions bordered size="small" column={2}>
              {/* Data e Hora */}
              <Descriptions.Item
                label={<><ClockCircleOutlined /> Data/Hora</>}
                span={2}
              >
                {previewData.preview.payload?.start?.dateTime && (
                  <Space>
                    <Tag color="blue">
                      {formatFortaleza(previewData.preview.payload.start.dateTime, 'DD/MM/YYYY')}
                    </Tag>
                    <Text>
                      {formatFortaleza(previewData.preview.payload.start.dateTime, 'HH:mm')}
                      {' - '}
                      {previewData.preview.payload?.end?.dateTime &&
                        formatFortaleza(previewData.preview.payload.end.dateTime, 'HH:mm')}
                    </Text>
                  </Space>
                )}
              </Descriptions.Item>

              {/* Localização */}
              <Descriptions.Item
                label={<><EnvironmentOutlined /> Local</>}
              >
                {previewData.preview.payload?.location || <Text type="secondary">Não informado</Text>}
              </Descriptions.Item>

              {/* Modalidade */}
              <Descriptions.Item
                label={<><GlobalOutlined /> Modalidade</>}
              >
                {previewData.preview.payload?.conferenceData ? (
                  <Tag color="green" icon={<VideoCameraOutlined />}>Online</Tag>
                ) : (
                  <Tag color="orange">Presencial</Tag>
                )}
              </Descriptions.Item>

              {/* Event ID */}
              <Descriptions.Item
                label={<><LinkOutlined /> Event ID</>}
              >
                <Text code copyable>{previewData.preview.event_id}</Text>
              </Descriptions.Item>

              {/* Meet Link */}
              <Descriptions.Item
                label={<><VideoCameraOutlined /> Meet Link</>}
              >
                {previewData.preview.meet_link ? (
                  <Text copyable={{ text: previewData.preview.meet_link }}>
                    <a href={previewData.preview.meet_link} target="_blank" rel="noopener noreferrer">
                      {previewData.preview.meet_link}
                    </a>
                  </Text>
                ) : (
                  <Text type="secondary">Não aplicável (presencial)</Text>
                )}
              </Descriptions.Item>
            </Descriptions>

            {/* Participantes */}
            {previewData.preview.payload?.attendees && previewData.preview.payload.attendees.length > 0 && (
              <Card
                size="small"
                title={<><TeamOutlined /> Participantes ({previewData.preview.payload.attendees.length})</>}
              >
                <List
                  size="small"
                  dataSource={previewData.preview.payload.attendees}
                  renderItem={(attendee) => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<Avatar size="small" icon={<UserOutlined />} />}
                        title={attendee.email}
                        description={attendee.responseStatus === 'needsAction' ? 'Aguardando resposta' : attendee.responseStatus}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {/* Descrição */}
            {previewData.preview.payload?.description && (
              <Card
                size="small"
                title={<><FileTextOutlined /> Descrição</>}
              >
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  margin: 0,
                  fontSize: '13px',
                  fontFamily: 'inherit',
                  maxHeight: '200px',
                  overflow: 'auto'
                }}>
                  {previewData.preview.payload.description}
                </pre>
              </Card>
            )}

            {/* Informações Técnicas (Colapsável) — apenas superuser (debug widget). */}
            {ehSuperusuario && (
              <Collapse
                size="small"
                items={[
                  {
                    key: 'technical',
                    label: (
                      <Space>
                        <CodeOutlined />
                        <span>Informações Técnicas (JSON)</span>
                      </Space>
                    ),
                    children: (
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Descriptions size="small" column={1}>
                          <Descriptions.Item label="Payload Hash">
                            <Text code copyable style={{ fontSize: '12px' }}>
                              {previewData.preview.payload_hash}
                            </Text>
                          </Descriptions.Item>
                        </Descriptions>
                        <Divider style={{ margin: '8px 0' }} />
                        <pre style={{
                          maxHeight: 300,
                          overflow: 'auto',
                          backgroundColor: '#f5f5f5',
                          padding: 12,
                          fontSize: '12px',
                          borderRadius: '4px'
                        }}>
                          {JSON.stringify(previewData, null, 2)}
                        </pre>
                      </Space>
                    ),
                  },
                ]}
              />
            )}
          </Space>
        )}
      </Modal>
    </div>
  );
}
