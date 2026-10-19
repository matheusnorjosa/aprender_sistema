/**
 * ApprovalsPage - Página de aprovação/reprovação de solicitações (Superintendência, DAT e Controle)
 *
 * Features:
 * - Filtra solicitações pendentes do fluxo SUPER
 * - Paginação no servidor (20, 50 ou 100 por página), do evento mais próximo de hoje
 *   para o mais distante e depois os passados (`ordering=proximidade`); a seleção em
 *   lote vale para a página visível
 * - Botões para preview, aprovar e reprovar
 * - Modal para preview de payload JSON
 * - Confirmação simples para reprovação (sem justificativa obrigatória)
 * - Erro ao aprovar diz quem está bloqueado e por quê; no lote, a tela lista o evento e o
 *   motivo de cada item que não foi decidido
 *
 * PA-06 (Política de Aprovação Manual):
 * - Botões de aprovar/reprovar aparecem para quem tem a policy `access_solicitation_approvals`:
 *   gerência da Superintendência (vínculo), DAT e Controle (pacote do perfil, PR 10 e PR 11) e
 *   superusuários. Nenhum grupo aprova.
 * - PA-02 (segregação): a própria solicitação sai sem checkbox e sem Aprovar/Reprovar,
 *   com a Tag "Sua solicitação" — outra pessoa aprovadora decide (superusuário pode).
 * - Conformidade ISO 9241-110: Controle explícito (usuário vê apenas ações permitidas)
 */

import { useState, useEffect, useCallback, useMemo, useRef, ChangeEvent, Key, JSX, CSSProperties } from 'react';
import {
  Alert,
  Card,
  Grid,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Typography,
  message,
  Modal,
  Descriptions,
  Divider,
  List,
  Avatar,
  Tooltip,
} from 'antd';
import type { TableRowSelection } from 'antd/es/table/interface';
import {
  CalendarOutlined,
  EnvironmentOutlined,
  TeamOutlined,
  MailOutlined,
  LinkOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import {
  listSolicitacoes,
  approveSolicitacao,
  rejectSolicitacao,
  previewSolicitacao,
  approveSolicitacoesBatch,
  rejectSolicitacoesBatch,
} from '../../api/solicitacoes';
import { getMe } from '../../api/availability';
import { ehSuperusuario, useAcesso } from '../../contexts/AcessoContext';
import { TIMING } from '../../constants/timing';
import { usePolling } from '../../hooks/usePolling';
import { syncChannel } from '../../services/syncChannel';
import { formatFortaleza, FORTALEZA_TZ } from '../../utils/datetime';
import logger from '../../utils/logger';
import type {
  BatchOperationResult,
  BlockedParticipant,
  CurrentUser,
  DecisaoImpedida,
  ID,
  Solicitacao,
  SolicitacaoStatus,
  Participation,
} from '../../types';
import { ListaDeBloqueados } from '../../components/AvailabilityConflictAlert';
import { formadoresLabel } from '../../utils/participants';
import { mesmosDados } from '../../utils/mesmosDados';
import { pausaDo429Ms } from '../../utils/retryAfter';
import AvisoAtualizacaoPausada from '../../components/AvisoAtualizacaoPausada';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha, type AcaoDaLinha } from '../../components/AcoesLinha';

const { Title, Paragraph, Text } = Typography;

/** PA-02: Tag da linha que quem lê não decide (outra pessoa aprovadora decide). */
const TAG_DA_DECISAO_IMPEDIDA: Record<DecisaoImpedida, string> = {
  propria: 'Sua solicitação',
  conta_alterada: 'Você alterou a conta de quem pediu',
  conta_alterada_pelo_autor: 'Quem pediu alterou a sua conta',
  contas_alteradas_pela_mesma_pessoa: 'A mesma pessoa alterou a sua conta e a de quem pediu',
  editada_pelo_ator: 'Você editou esta solicitação',
};

/** Status colors */
const STATUS_COLORS: Record<SolicitacaoStatus, string> = {
  pendente: 'orange',
  aprovado: 'green',
  reprovado: 'red',
};

/** Status labels */
const STATUS_LABELS: Record<SolicitacaoStatus, string> = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
};

/** Tamanhos de página: o maior é o limite do lote no servidor (100 ids por requisição). */
const PAGE_SIZE_OPTIONS = [20, 50, 100];
const DEFAULT_PAGE_SIZE = 20;
/** Uma mensagem só para a falha de carga: a atualização automática não empilha erros. */
const LOAD_ERROR_KEY = 'aprovacoes-erro-carga';

/** Corpo do erro 400 da aprovação; no conflito de agenda traz quem está bloqueado. */
interface ConflictErrorData {
  code?: string;
  detail?: string;
  errors?: { blocked_participants?: BlockedParticipant[] };
}

/** Itens que um lote não decidiu, já com o rótulo do evento para a pessoa reconhecer. */
interface BatchErrors {
  acao: 'aprovadas' | 'reprovadas';
  itens: Array<{ id: ID; evento: string; detail: string }>;
}

/** Preview data type */
interface PreviewDataType {
  preview: {
    payload?: {
      summary?: string;
      start?: { dateTime?: string };
      end?: { dateTime?: string };
      location?: string;
      description?: string;
      attendees?: Array<{ email: string }>;
    };
    event_id?: string;
    payload_hash?: string;
    meet_link?: string;
  };
}

// Célula de duas linhas: o `ellipsis` da coluna só corta texto simples, então cada linha corta a si mesma
// e mostra o texto inteiro no title (achado da revisão do PR-2, 05/10/2026).
const UMA_LINHA: CSSProperties = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };

/** O evento como a pessoa o reconhece: "25/08/2026 · Sobral · Projeto X" (botões, confirmações, lote). */
function rotuloDoEvento(row: Solicitacao): string {
  return [formatFortaleza(row.inicio, 'DD/MM/YYYY'), row.municipio_nome, row.projeto_nome].filter(Boolean).join(' · ');
}

/** O vazio da lista diz o que não há (o do AntD, "Não há dados", não diz). */
function textoDoVazio(status: string, busca: string): string {
  if (busca.trim()) return `Nenhuma solicitação encontrada para "${busca.trim()}".`;
  if (status === 'aprovado') return 'Nenhuma solicitação aprovada.';
  if (status === 'reprovado') return 'Nenhuma solicitação reprovada.';
  return 'Nenhuma solicitação aguardando aprovação.';
}

/** Quantos eventos a confirmação do lote lista pelo nome; o resto vai na contagem. */
const EVENTOS_NA_CONFIRMACAO = 10;

export default function ApprovalsPage(): JSX.Element {
  const [loading, setLoading] = useState<boolean>(false);
  const [rows, setRows] = useState<Solicitacao[]>([]);
  const [total, setTotal] = useState<number>(0);
  // Uma carga pedida pela pessoa recebeu 429: a tela pode não corresponder ao pedido.
  const [cargaFalhou, setCargaFalhou] = useState<boolean>(false);
  // A carga pedida pela pessoa falhou (fora o 429): o motivo vai no lugar das linhas, não o vazio.
  const [erroCarga, setErroCarga] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<SolicitacaoStatus | (string & {})>('pendente');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);

  const [previewVisible, setPreviewVisible] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<PreviewDataType | null>(null);

  // PA-06: permissão de aprovar (policy `access_solicitation_approvals`), do acesso da sessão:
  // a mesma policy que abriu a rota. Uma 2ª busca aqui podia falhar sozinha e sumir com os
  // botões sem aviso (achado do item 36, 19/10/2026).
  const canApprove = useAcesso().caps.canAccessApprovals;
  // PA-02 (segregação): usuário logado, para reconhecer a própria solicitação
  const [me, setMe] = useState<CurrentUser | null>(null);

  // Estados para seleção em lote
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([]);
  const [batchLoading, setBatchLoading] = useState<boolean>(false);
  const [batchErrors, setBatchErrors] = useState<BatchErrors | null>(null);

  // Latest-wins: polling, paginação, filtros e ações disparam cargas concorrentes; só a
  // mais recente grava na tela.
  const seqRef = useRef(0);
  // Cargas em voo: o tick do polling espera a resposta em vez de abrir outra carga, senão
  // em rede lenta (resposta > intervalo) cada tick descartaria a anterior e nada apareceria.
  // (O usePolling tem a mesma guarda, mas só enxerga as cargas que ele abriu; esta cobre
  // também a carga do mount, de filtro e de ação.)
  const emVooRef = useRef(0);

  // RT-02: polling para sincronizar entre dispositivos (#1032); intervalo em constants/timing.ts.
  // immediate:false: a carga inicial é do efeito abaixo (sem busca dupla no mount).
  const loadDataRef = useRef<(silencioso?: boolean) => Promise<void>>(() => Promise.resolve());
  const { pausado: pollingPausado, pausar: pausarPolling } = usePolling(
    () => (emVooRef.current > 0 ? undefined : loadDataRef.current(true)),
    {
      enabled: true,
      intervalMs: TIMING.LIST_POLL_INTERVAL_MS,
      immediate: false,
      events: ['solicitacoes:refresh', 'aprovacoes:refresh'],
    },
  );

  /**
   * `silencioso`: atualização em segundo plano (polling, outra aba). Não liga o
   * carregamento da tabela; os dados antigos ficam na tela até chegarem os novos.
   */
  const loadData = useCallback(async (silencioso = false): Promise<void> => {
    const seq = ++seqRef.current;
    emVooRef.current += 1;
    try {
      if (!silencioso) setLoading(true);
      const data = await listSolicitacoes({
        flow: 'SUPER',
        status: (statusFilter || 'pendente') as SolicitacaoStatus,
        q: searchTerm,
        ordering: 'proximidade',
        page,
        page_size: pageSize,
      });
      if (seq !== seqRef.current) return;
      const results = data.results ?? [];
      // Só troca a lista se algo mudou: resposta igual não redesenha a tabela.
      setRows((atuais) => (mesmosDados(atuais, results) ? atuais : results));
      setTotal(data.count ?? 0);
      // Item que saiu da lista (outra pessoa decidiu) não fica selecionado às cegas.
      const visiveis = new Set<Key>(results.map((r) => r.id));
      setSelectedRowKeys((keys) => (keys.every((k) => visiveis.has(k)) ? keys : keys.filter((k) => visiveis.has(k))));
      setCargaFalhou(false);
      setErroCarga(null);
    } catch (error) {
      if (seq !== seqRef.current) return;
      // A página deixou de existir (os últimos itens dela foram decididos): volta uma.
      if ((error as { status?: number }).status === 404 && page > 1) {
        setPage((p) => Math.max(1, p - 1));
        return;
      }
      // 429 (muitas requisições): pausa o polling pelo tempo pedido e mostra um aviso só.
      // Se a carga foi pedida pela pessoa, o aviso diz que a lista não carregou.
      const pausa = pausaDo429Ms(error);
      if (pausa !== null) {
        pausarPolling(pausa);
        if (!silencioso) setCargaFalhou(true);
        return;
      }
      // Pedida pela pessoa: o motivo e "Tentar de novo" no lugar das linhas (um toast some em 3 s e
      // a tabela ficava em "Não há dados", como se nada esperasse aprovação). No segundo plano, a
      // lista que já estava na tela fica, com o toast.
      if (!silencioso) {
        setErroCarga((error as Error).message || 'Erro desconhecido.');
        return;
      }
      message.error({
        key: LOAD_ERROR_KEY,
        content: 'Erro ao carregar solicitações: ' + (error as Error).message,
      });
    } finally {
      emVooRef.current -= 1;
      if (seq === seqRef.current) setLoading(false);
    }
  }, [statusFilter, searchTerm, page, pageSize, pausarPolling]);
  loadDataRef.current = loadData;

  // Trocar filtro, busca, página ou tamanho muda o que está na tela: a seleção recomeça.
  const handleStatusChange = (value: SolicitacaoStatus | (string & {})): void => {
    setStatusFilter(value);
    setPage(1);
    setSelectedRowKeys([]);
  };
  const handleSearchChange = (value: string): void => {
    setSearchTerm(value);
    setPage(1);
    setSelectedRowKeys([]);
  };
  const handlePageChange = (nextPage: number, nextPageSize: number): void => {
    setPage(nextPageSize === pageSize ? nextPage : 1);
    setPageSize(nextPageSize);
    setSelectedRowKeys([]);
  };

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // RT-02: BroadcastChannel for instant cross-tab sync
  useEffect(() => {
    const unsub1 = syncChannel.subscribe('solicitacoes', () => { void loadData(true); });
    const unsub2 = syncChannel.subscribe('aprovacoes', () => { void loadData(true); });
    return () => { unsub1(); unsub2(); };
  }, [loadData]);

  // PA-02 (segregação): o usuário logado, para reconhecer a própria solicitação na tabela.
  // A permissão de aprovar não sai daqui: vem do AcessoContext (acima).
  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((error: unknown) => logger.error('Erro ao carregar o usuário:', error));
  }, []);

  // PA-02 (segregação): quem criou não decide a própria; superusuário pode (fica no AuditLog).
  // PR 10: o backend também diz quando quem lê alterou a conta de quem pediu ou editou o evento
  // (`decisao_impedida`); o 403 do servidor fica só como defesa.
  const impedimento = useCallback(
    (record: Solicitacao): DecisaoImpedida | null => {
      if (record.decisao_impedida) return record.decisao_impedida;
      return me !== null && !ehSuperusuario(me) && record.usuario === me.id ? 'propria' : null;
    },
    [me],
  );

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

  // A decisão não se desfaz: a confirmação cita o evento e abre com o foco no Cancelar.
  const handleApprove = useCallback((row: Solicitacao): void => {
    const id = row.id;
    Modal.confirm({
      title: 'Confirmar aprovação',
      content: `Aprovar o evento ${rotuloDoEvento(row)}?`,
      okText: 'Aprovar',
      okType: 'primary',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await approveSolicitacao(id);
          message.success('Solicitação aprovada com sucesso!');
          void loadData();
        } catch (error) {
          // Conflito de agenda: o servidor diz quem está bloqueado e por quê.
          const payload = (error as { response?: { data?: ConflictErrorData } }).response?.data;
          if (payload?.code === 'availability_conflict') {
            Modal.error({
              title: 'Não foi possível aprovar',
              content: (
                <>
                  <Paragraph>{payload.detail || (error as Error).message}</Paragraph>
                  <ListaDeBloqueados
                    bloqueados={payload.errors?.blocked_participants ?? []}
                    orientacao="Reprove a solicitação ou peça a quem criou para ajustar data, horário ou participantes."
                  />
                </>
              ),
            });
            return;
          }
          message.error('Erro ao aprovar: ' + (error as Error).message);
        }
      },
    });
  }, [loadData]);

  const handleReject = useCallback((row: Solicitacao): void => {
    const id = row.id;
    Modal.confirm({
      title: 'Confirmar reprovação',
      content: `Reprovar o evento ${rotuloDoEvento(row)}? Esta ação não pode ser desfeita.`,
      okText: 'Reprovar',
      okType: 'danger',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await rejectSolicitacao(id);
          message.success('Solicitação reprovada.');
          void loadData();
        } catch (error) {
          message.error('Erro ao reprovar: ' + (error as Error).message);
        }
      },
    });
  }, [loadData]);

  // Lote: cada item não decidido vira uma linha "evento — motivo" acima da tabela. O rótulo
  // do evento sai das linhas visíveis ANTES da recarga (o lote só tem itens da página atual).
  const reportBatchErrors = (acao: BatchErrors['acao'], errors: BatchOperationResult['errors'] | undefined): void => {
    if (!errors?.length) {
      setBatchErrors(null);
      return;
    }
    const porId = new Map(rows.map((r) => [r.id, r]));
    setBatchErrors({
      acao,
      itens: errors.map((e) => {
        const row = porId.get(e.id);
        const evento = row ? rotuloDoEvento(row) : `Solicitação #${e.id}`;
        return { id: e.id, evento, detail: e.detail };
      }),
    });
  };

  // Lote: a confirmação lista os eventos selecionados (os da página visível).
  const conteudoDoLote = (): JSX.Element => {
    const selecionadas = new Set<Key>(selectedRowKeys);
    const eventos = rows.filter((r) => selecionadas.has(r.id)).map(rotuloDoEvento);
    const resto = selectedRowKeys.length - Math.min(eventos.length, EVENTOS_NA_CONFIRMACAO);
    return (
      <>
        <ul className="pl-5 my-2">
          {eventos.slice(0, EVENTOS_NA_CONFIRMACAO).map((evento) => (
            <li key={evento} className="break-words">{evento}</li>
          ))}
        </ul>
        {resto > 0 && <Paragraph className="mb-2">e mais {resto}.</Paragraph>}
        <Paragraph className="mb-0">Esta ação não pode ser desfeita.</Paragraph>
      </>
    );
  };

  // Handlers de operações em lote
  const handleBatchApprove = (): void => {
    Modal.confirm({
      title: `Aprovar ${selectedRowKeys.length} solicitação(ões)?`,
      content: conteudoDoLote(),
      okText: 'Aprovar Todas',
      okType: 'primary',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const result = await approveSolicitacoesBatch(selectedRowKeys as ID[]);

          if (result.approved && result.approved > 0) {
            message.success(`${result.approved} solicitação(ões) aprovada(s)!`);
          }
          reportBatchErrors('aprovadas', result.errors);

          setSelectedRowKeys([]);
          void loadData();
        } catch (error) {
          message.error('Erro ao aprovar em lote: ' + (error as Error).message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  const handleBatchReject = (): void => {
    Modal.confirm({
      title: `Reprovar ${selectedRowKeys.length} solicitação(ões)?`,
      content: conteudoDoLote(),
      okText: 'Reprovar Todas',
      okType: 'danger',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          setBatchLoading(true);
          const result = await rejectSolicitacoesBatch(selectedRowKeys as ID[]);

          if (result.rejected && result.rejected > 0) {
            message.success(`${result.rejected} solicitação(ões) reprovada(s)!`);
          }
          reportBatchErrors('reprovadas', result.errors);

          setSelectedRowKeys([]);
          void loadData();
        } catch (error) {
          message.error('Erro ao reprovar em lote: ' + (error as Error).message);
        } finally {
          setBatchLoading(false);
        }
      },
    });
  };

  // Configuração de seleção de linhas
  const rowSelection: TableRowSelection<Solicitacao> | undefined = canApprove ? {
    selectedRowKeys,
    onChange: (keys: Key[]) => setSelectedRowKeys(keys),
    getCheckboxProps: (record: Solicitacao) => ({
      // Só pendentes; a impedida (própria, conta alterada, editada) nunca entra no lote (PA-02)
      disabled: record.status !== 'pendente' || impedimento(record) !== null,
      // Sem nome, o leitor de tela ouvia só "caixa de seleção" em toda linha (axe: label).
      'aria-label': `Selecionar: ${rotuloDoEvento(record)}`,
    }),
    // A impedida sai sem checkbox (não só desabilitado): não há ação possível nela.
    renderCell: (_checked, record, _index, originNode) => (impedimento(record) !== null ? null : originNode),
    // `true`: os atalhos padrão do AntD (tudo, inverter, nada) sem importar o `Table` cru.
    selections: true,
  } : undefined;

  // Celular: as ações vão para o menu "Mais ações" (AcoesLinha) e a página perde padding.
  const telas = Grid.useBreakpoint();
  const acoesCompactas = !telas.sm;

  // Sem rolagem horizontal (achado do item 36): no celular a coluna fixa Ações cobria a tabela e
  // a pessoa aprovava sem ver o evento. Sempre na linha: o Evento (data, município, projeto) e as
  // ações; o resto sobe por largura e, escondido, vai para a linha expandida.
  // Issue #260: Memoizar columns para evitar re-renderização desnecessária da tabela
  const columns: ColunaResponsiva<Solicitacao>[] = useMemo(() => [
    {
      title: 'Evento',
      key: 'evento',
      render: (_, record) => {
        const motivo = record.status === 'pendente' && canApprove ? impedimento(record) : null;
        return (
          <div style={{ lineHeight: 1.3 }}>
            <div style={UMA_LINHA}>
              {formatFortaleza(record.inicio, 'DD/MM/YYYY')}{' '}
              <small className="text-gray-500">
                {formatFortaleza(record.inicio, 'HH:mm')} - {formatFortaleza(record.fim, 'HH:mm')}
              </small>
            </div>
            <div style={UMA_LINHA} title={record.municipio_nome || undefined}>{record.municipio_nome || '-'}</div>
            <small className="text-gray-500" style={{ ...UMA_LINHA, display: 'block' }} title={record.projeto_nome || undefined}>
              {record.projeto_nome || '-'}
            </small>
            {/* PA-02: quem lê não decide esta; outra pessoa aprovadora decide */}
            {motivo !== null && (
              <Tooltip title="Outra pessoa aprovadora precisa decidir">
                <Tag color="blue" className="mt-1" style={{ whiteSpace: 'normal' }}>{TAG_DA_DECISAO_IMPEDIDA[motivo]}</Tag>
              </Tooltip>
            )}
          </div>
        );
      },
    },
    {
      title: 'Coordenador',
      dataIndex: 'coordenador_nome',
      key: 'coordenador_nome',
      responsive: VISIVEL_A_PARTIR.md,
      // 05/10/2026: a resposta "acompanha?" vai numa 2ª linha da mesma célula, sem coluna nova.
      render: (valor, record) => {
        const nome = valor as string | null;
        return (
          <div style={{ lineHeight: 1.3 }}>
            <div style={UMA_LINHA} title={nome || undefined}>{nome || '-'}</div>
            <small className="text-gray-500">{record.coordenador_acompanha ? 'Acompanha' : 'Não acompanha'}</small>
          </div>
        );
      },
    },
    {
      title: 'Tipo/Enc./Seg.',
      key: 'tipo_encontro_segmento',
      responsive: VISIVEL_A_PARTIR.lg,
      width: 110,
      render: (_, record) => (
        <div style={{ lineHeight: 1.3 }}>
          {record.tipo && <div style={UMA_LINHA} title={record.tipo}>{record.tipo}</div>}
          {record.encontro && <small className="text-gray-500">{record.encontro}</small>}
          {record.segmento && <div><small className="text-gray-500">{record.segmento}</small></div>}
          {!record.tipo && !record.encontro && !record.segmento && '-'}
        </div>
      ),
    },
    {
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      responsive: VISIVEL_A_PARTIR.lg,
      // Nome do formador (inclui convidados "que saíram" via guest_nome — sem FK). Ver utils/participants.
      // 2ª linha: "pretende avaliar o formador?" (05/10/2026); sem resposta (antigas), nada.
      render: (valor, record) => {
        const participations = valor as Participation[] | undefined;
        return (
          <div style={{ lineHeight: 1.3 }}>
            <div style={UMA_LINHA} title={formadoresLabel(participations) || undefined}>
              {formadoresLabel(participations) || '-'}
            </div>
            {record.pretende_avaliar_formador === true && (
              <small className="text-gray-500" style={{ ...UMA_LINHA, display: 'block' }} title={record.formador_avaliado_nome || undefined}>
                Pretende avaliar: {record.formador_avaliado_nome || '-'}
              </small>
            )}
            {record.pretende_avaliar_formador === false && <small className="text-gray-500">Não pretende avaliar</small>}
          </div>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      responsive: VISIVEL_A_PARTIR.sm,
      width: 100,
      render: (valor) => {
        const status = valor as SolicitacaoStatus;
        // TEXTO_DA_TAG: o laranja e o verde do AntD não passam de 4,5:1.
        return <Tag color={STATUS_COLORS[status]} style={{ color: TEXTO_DA_TAG[STATUS_COLORS[status]] }}>{STATUS_LABELS[status] || status}</Tag>;
      },
    },
    {
      title: 'Ações',
      key: 'actions',
      width: larguraAcoesLinha(3, acoesCompactas),
      render: (_, record) => {
        const acoes: AcaoDaLinha[] = [
          { chave: 'ver', rotulo: 'Ver prévia do evento', icone: <EyeOutlined />, onClick: () => void handlePreview(record.id) },
        ];
        // PA-06: Aprovar/Reprovar para quem tem a policy; PA-02: nunca na impedida
        if (record.status === 'pendente' && canApprove && impedimento(record) === null) {
          acoes.push(
            { chave: 'aprovar', rotulo: 'Aprovar', icone: <CheckOutlined />, onClick: () => handleApprove(record) },
            { chave: 'reprovar', rotulo: 'Reprovar', icone: <CloseOutlined />, onClick: () => handleReject(record), perigo: true },
          );
        }
        return <AcoesLinha acoes={acoes} alvo={rotuloDoEvento(record)} compacto={acoesCompactas} />;
      },
    },
  ], [handlePreview, handleApprove, handleReject, canApprove, impedimento, acoesCompactas]);

  return (
    <section className="p-3 sm:p-6" aria-labelledby="aprovacoes-title">
      <Card {...(!telas.sm && { styles: { body: { padding: 12 } } })}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Header semantico */}
          <header>
            <Title level={2} id="aprovacoes-title">Aprovações</Title>
          </header>

          {/* Filtros */}
          <nav aria-label="Filtros de busca">
            <Space wrap className="w-full">
              <Select
                value={statusFilter}
                onChange={handleStatusChange}
                style={{ width: '100%', maxWidth: 200 }}
                placeholder="Status"
                aria-label="Filtrar por status"
              >
                <Select.Option value="pendente">Pendentes</Select.Option>
                <Select.Option value="aprovado">Aprovadas</Select.Option>
                <Select.Option value="reprovado">Reprovadas</Select.Option>
              </Select>

              <Input.Search
                placeholder="Buscar por município, projeto, autor..."
                value={searchTerm}
                onChange={(e: ChangeEvent<HTMLInputElement>) => handleSearchChange(e.target.value)}
                onSearch={() => { void loadData(); }}
                style={{ width: '100%', maxWidth: 400 }}
                allowClear
                aria-label="Buscar solicitacoes"
              />
            </Space>
          </nav>

          {(pollingPausado || cargaFalhou) && <AvisoAtualizacaoPausada cargaFalhou={cargaFalhou} />}

          {/* Contagem de pendentes */}
          {statusFilter === 'pendente' && total > 0 && !erroCarga && (
            <aside aria-label="Contador de pendentes">
              <Paragraph>
                <Tag color="orange" style={{ color: TEXTO_DA_TAG['orange'] }}>{total}</Tag> solicitações aguardando aprovação
              </Paragraph>
            </aside>
          )}

          {/* Toolbar de ações em lote (PA-06: apenas para usuários com permissão) */}
          {selectedRowKeys.length > 0 && canApprove && (
            <nav aria-label="Acoes em lote" className="mb-4 p-3 bg-blue-50 rounded border border-blue-200">
              <Space wrap>
                <Text strong aria-live="polite">
                  {selectedRowKeys.length} solicitação(ões) selecionada(s)
                </Text>
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  onClick={handleBatchApprove}
                  loading={batchLoading}
                >
                  Aprovar Selecionadas
                </Button>
                <Button
                  danger
                  icon={<CloseOutlined />}
                  onClick={handleBatchReject}
                  loading={batchLoading}
                >
                  Reprovar Selecionadas
                </Button>
                <Button type="link" onClick={() => setSelectedRowKeys([])}>
                  Limpar Seleção
                </Button>
              </Space>
            </nav>
          )}

          {/* Itens que o último lote não decidiu: evento + motivo de cada um */}
          {batchErrors && (
            <Alert
              type="warning"
              showIcon
              closable
              role="status"
              onClose={() => setBatchErrors(null)}
              message={`${batchErrors.itens.length} solicitação(ões) não foram ${batchErrors.acao}`}
              description={
                <ul className="pl-5 m-0">
                  {batchErrors.itens.map((item) => (
                    <li key={item.id} className="break-words">
                      <strong>{item.evento}</strong> — {item.detail}
                    </li>
                  ))}
                </ul>
              }
            />
          )}

          {/* Tabela */}
          <section aria-label="Lista de solicitacoes para aprovacao">
            <ResponsiveTable<Solicitacao>
              {...(rowSelection !== undefined && { rowSelection })}
              columns={columns}
              dataSource={rows}
              loading={loading}
              rowKey="id"
              nomeDaLinha={rotuloDoEvento}
              erro={erroCarga}
              onTentarDeNovo={() => { void loadData(); }}
              locale={{ emptyText: textoDoVazio(statusFilter, searchTerm) }}
              pagination={{
                current: page,
                pageSize,
                total,
                showSizeChanger: true,
                pageSizeOptions: PAGE_SIZE_OPTIONS,
                showTotal: (count) => `Total: ${count} solicitações`,
                onChange: handlePageChange,
              }}
            />
          </section>
        </Space>
      </Card>

      {/* Modal Preview - Visualização Amigável */}
      <Modal
        title={
          <Space>
            <CalendarOutlined />
            <span>Preview do Evento no Google Calendar</span>
          </Space>
        }
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Fechar
          </Button>,
        ]}
        width={700}
      >
        {previewData?.preview?.payload && (() => {
          const payload = previewData.preview.payload;
          const start = payload.start?.dateTime ? dayjs(payload.start.dateTime).tz(FORTALEZA_TZ) : null;
          const end = payload.end?.dateTime ? dayjs(payload.end.dateTime).tz(FORTALEZA_TZ) : null;

          return (
            <div style={{ maxHeight: 500, overflow: 'auto' }}>
              {/* Título do Evento */}
              <Card size="small" className="mb-4" style={{ background: '#f0f5ff' }}>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {payload.summary}
                </Typography.Title>
              </Card>

              {/* Informações Principais */}
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item
                  label={<><CalendarOutlined /> Data/Horário</>}
                >
                  {start && end ? (
                    <>
                      <Tag color="blue">{start.format('DD/MM/YYYY')}</Tag>
                      <span style={{ marginLeft: 8 }}>
                        {start.format('HH:mm')} às {end.format('HH:mm')}
                      </span>
                    </>
                  ) : '-'}
                </Descriptions.Item>

                <Descriptions.Item
                  label={<><EnvironmentOutlined /> Local</>}
                >
                  {payload.location || '-'}
                </Descriptions.Item>

                {previewData.preview.meet_link && (
                  <Descriptions.Item
                    label={<><VideoCameraOutlined /> Google Meet</>}
                  >
                    <a href={previewData.preview.meet_link} target="_blank" rel="noopener noreferrer">
                      <LinkOutlined /> {previewData.preview.meet_link}
                    </a>
                  </Descriptions.Item>
                )}
              </Descriptions>

              {/* Descrição */}
              {payload.description && (
                <>
                  <Divider orientation="left" className="mt-4">Descrição</Divider>
                  <Card size="small" className="bg-gray-50">
                    <pre style={{
                      whiteSpace: 'pre-wrap',
                      margin: 0,
                      fontFamily: 'inherit',
                      fontSize: 13
                    }}>
                      {payload.description}
                    </pre>
                  </Card>
                </>
              )}

              {/* Participantes */}
              {payload.attendees && payload.attendees.length > 0 && (
                <>
                  <Divider orientation="left" className="mt-4">
                    <TeamOutlined /> Participantes ({payload.attendees.length})
                  </Divider>
                  <List
                    size="small"
                    dataSource={payload.attendees}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={<Avatar size="small" icon={<MailOutlined />} />}
                          title={item.email}
                        />
                      </List.Item>
                    )}
                  />
                </>
              )}

              {/* Metadados (colapsável) */}
              <Divider orientation="left" className="mt-4">Metadados</Divider>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="ID Evento">
                  <Tag>{previewData.preview.event_id}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Hash Payload">
                  <Tag color="default" style={{ fontSize: 10 }}>
                    {previewData.preview.payload_hash?.substring(0, 12)}...
                  </Tag>
                </Descriptions.Item>
              </Descriptions>
            </div>
          );
        })()}

        {/* Fallback para JSON se não tiver payload */}
        {!previewData?.preview?.payload && (
          <pre style={{ maxHeight: 500, overflow: 'auto', backgroundColor: '#f5f5f5', padding: 12 }}>
            {JSON.stringify(previewData, null, 2)}
          </pre>
        )}
      </Modal>

    </section>
  );
}
