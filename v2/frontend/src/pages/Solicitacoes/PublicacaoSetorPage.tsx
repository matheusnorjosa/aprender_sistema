/**
 * PublicacaoSetorPage — "Publicar na agenda" (#1656).
 *
 * A Apoio de Coordenação (policy `publish_setor_solicitacao`, NÃO `use_gcal`) conecta
 * a PRÓPRIA conta Google e publica, atualiza ou remove, no calendário oficial da
 * organização, os eventos APROVADOS do próprio setor.
 *
 * - Lista: `GET /solicitacoes/?status=aprovado&publishable=true&date_from=<hoje em
 *   Fortaleza>&ordering=inicio`, paginada no servidor. O backend só devolve linhas que
 *   ela pode publicar. Nunca manda `mine` (pularia o escopo) nem `sector` (lê gerência).
 * - Prontidão: `status.publishReady`/`publishBlockReason`; sem prontidão as ações ficam
 *   desabilitadas, com o motivo visível.
 * - Polling só enquanto alguma linha está PENDING; `seqRef` descarta resposta obsoleta.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type JSX } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { Alert, Button, Card, Empty, Popconfirm, Space, Table, Tag, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import {
  cancelSolicitacao,
  listSolicitacoes,
  publishSolicitacao,
  resyncSolicitacao,
} from '../../api/solicitacoes';
import { MeetLink } from '../../components/MeetLink';
import GoogleIntegrationCard from '../../components/google/GoogleIntegrationCard';
import { TIMING } from '../../constants/timing';
import useGoogleIntegration from '../../hooks/useGoogleIntegration';
import { usePolling } from '../../hooks/usePolling';
import { syncChannel } from '../../services/syncChannel';
import type { ID, Solicitacao } from '../../types';
import type { PublishBlockReason } from '../../types/gcal';
import { formatFortaleza } from '../../utils/datetime';
import { gcalRowActions, type GcalRowAction } from '../../utils/gcalRowActions';

const { Title, Text } = Typography;

const TITLE_ID = 'publicacao-setor-title';
const PAGE_SIZE = 20;
/** O OAuth volta para esta página (o backend valida o `return_to`). */
const GOOGLE_CONNECT_URL = `/api/oauth/google/start/?return_to=${encodeURIComponent('/solicitacoes/publicacao')}`;
/** Uma só mensagem de erro de carga na tela (o polling não empilha toasts). */
const LOAD_ERROR_KEY = 'publicacao-setor-load';

const BLOCK_REASON_TEXT: Record<PublishBlockReason, string> = {
  no_setor_scope:
    'Seu cadastro não tem setor vigente. Peça à DAT para cadastrar seu vínculo de gerência.',
  google_not_connected: 'Conecte sua conta Google para publicar os eventos.',
  google_calendar_not_configured:
    'A agenda da organização ainda não foi configurada no sistema. Avise o Controle.',
};

const OAUTH_SUCCESS_TEXT = 'Conta Google conectada. Você já pode publicar os eventos do seu setor.';
const OAUTH_ERROR_TEXT: Record<string, string> = {
  access_denied:
    'Você não autorizou o acesso à sua conta Google. Para publicar, conecte de novo e aceite as permissões.',
  validation:
    'Não foi possível validar essa conta Google. Conecte com a sua conta corporativa (e-mail de trabalho).',
  invalid_state: 'A conexão com o Google expirou ou foi interrompida. Tente conectar de novo.',
};
const OAUTH_ERROR_FALLBACK =
  'Não foi possível conectar sua conta Google. Tente de novo; se o erro continuar, avise o Controle.';

interface ActionConfig {
  /** Texto do botão; também abre o aria-label (nome acessível contém o visível). */
  label: string;
  confirmTitle: string;
  confirmDescription: string;
  okText: string;
  danger: boolean;
  successText: string;
  run: (id: ID) => Promise<unknown>;
}

// Endpoints aceitos pelo backend: publish/resync exigem aprovado; cancel exige o
// evento no Google. Corpo sempre vazio (nunca dry_run/apply_blocked).
const ACTIONS: Record<GcalRowAction, ActionConfig> = {
  publicar: {
    label: 'Publicar',
    confirmTitle: 'Publicar este evento na agenda da organização?',
    confirmDescription: 'O evento é criado no calendário oficial da organização.',
    okText: 'Publicar',
    danger: false,
    successText: 'Publicação enviada; o status muda em alguns segundos.',
    run: (id) => publishSolicitacao(id),
  },
  tentar: {
    label: 'Tentar de novo',
    confirmTitle: 'Tentar publicar este evento de novo?',
    confirmDescription: 'O sistema envia o evento outra vez para o Google Agenda.',
    okText: 'Tentar de novo',
    danger: false,
    successText: 'Publicação enviada; o status muda em alguns segundos.',
    run: (id) => publishSolicitacao(id),
  },
  atualizar: {
    label: 'Atualizar no Google',
    confirmTitle: 'Atualizar este evento no Google Agenda?',
    confirmDescription: 'O evento no Google passa a ter os dados atuais do sistema.',
    okText: 'Atualizar',
    danger: false,
    successText: 'Atualização enviada; o status muda em alguns segundos.',
    run: (id) => resyncSolicitacao(id),
  },
  remover: {
    label: 'Remover do Google',
    confirmTitle: 'Remover este evento do Google Agenda?',
    confirmDescription:
      'O evento sai da agenda da organização; a solicitação continua aprovada no sistema.',
    okText: 'Remover',
    danger: true,
    successText: 'Remoção enviada; o status muda em alguns segundos.',
    run: (id) => cancelSolicitacao(id),
  },
};

/** Formato do erro lançado por `fetchAPI` (status + corpo JSON do backend). */
interface ApiErrorLike {
  message?: string;
  status?: number;
  response?: { status?: number; data?: { code?: string; detail?: string } };
}

type OAuthReturn = { ok: true } | { ok: false; reason: string | null };

/** Motivo visível de as ações estarem desabilitadas (null = pode publicar). */
function blockedMessage(
  ready: boolean,
  reason: PublishBlockReason | null,
  statusError: string | null,
): string | null {
  if (ready) return null;
  if (reason) return BLOCK_REASON_TEXT[reason];
  if (statusError) return 'Não foi possível verificar sua conexão com o Google. Recarregue a página.';
  return 'Verificando sua conexão com o Google…';
}

export default function PublicacaoSetorPage(): JSX.Element {
  const location = useLocation();
  const navigate = useNavigate();
  const { status, error: statusError, fetchStatus, disconnect } = useGoogleIntegration();

  const [rows, setRows] = useState<Solicitacao[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [oauthReturn, setOauthReturn] = useState<OAuthReturn | null>(null);

  // Latest-wins: polling, paginação e ações disparam cargas concorrentes; só a
  // mais recente grava na tela.
  const seqRef = useRef(0);

  const load = useCallback(async (): Promise<void> => {
    const seq = ++seqRef.current;
    setLoading(true);
    try {
      const data = await listSolicitacoes({
        status: 'aprovado',
        publishable: 'true',
        date_from: formatFortaleza(new Date(), 'YYYY-MM-DD'),
        ordering: 'inicio',
        page,
        page_size: PAGE_SIZE,
      });
      if (seq !== seqRef.current) return;
      setRows(data.results);
      setTotal(data.count);
    } catch (error) {
      if (seq !== seqRef.current) return;
      message.error({
        key: LOAD_ERROR_KEY,
        content: `Erro ao carregar os eventos: ${(error as Error).message}`,
      });
    } finally {
      if (seq === seqRef.current) setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    void load();
  }, [load]);

  // Só há o que acompanhar enquanto alguma publicação está em voo (PENDING).
  usePolling(load, {
    enabled: rows.some((row) => row.gcal_status === 'PENDING'),
    intervalMs: TIMING.SYNC_POLL_INTERVAL_MS,
    immediate: false,
  });

  // Mudança de solicitação em outra aba → recarrega.
  useEffect(() => syncChannel.subscribe('solicitacoes', () => { void load(); }), [load]);

  // Volta do OAuth (?google=connected | ?google=error&reason=…): mostra o resultado,
  // tira os parâmetros da URL e recarrega o status da integração.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const google = params.get('google');
    if (!google) return;
    setOauthReturn(google === 'connected' ? { ok: true } : { ok: false, reason: params.get('reason') });
    void navigate(location.pathname, { replace: true });
    void fetchStatus();
  }, [location.search, location.pathname, navigate, fetchStatus]);

  const handleActionError = useCallback((error: unknown): void => {
    const err = error as ApiErrorLike;
    const httpStatus = err.response?.status ?? err.status;
    const code = err.response?.data?.code;
    if (httpStatus === 403 && code === 'google_not_connected') {
      message.warning('Sua conta Google não está conectada. Conecte-a para publicar.');
      void fetchStatus();
    } else if (httpStatus === 404) {
      message.error('Este evento não está mais disponível para você.');
      void load();
    } else if (httpStatus === 409) {
      message.error(err.response?.data?.detail || err.message || 'Não foi possível concluir a ação.');
      if (code === 'google_calendar_not_configured') void fetchStatus();
    } else if (httpStatus === 429) {
      message.error('Muitas ações seguidas; aguarde um minuto.');
    } else {
      message.error(`Não foi possível concluir a ação: ${err.message ?? 'erro desconhecido'}`);
    }
  }, [fetchStatus, load]);

  const runAction = useCallback(async (row: Solicitacao, action: GcalRowAction): Promise<void> => {
    const config = ACTIONS[action];
    try {
      await config.run(row.id);
    } catch (error) {
      handleActionError(error);
      return;
    }
    message.success(config.successText);
    void load();
  }, [handleActionError, load]);

  const handleConnect = (): void => {
    window.location.href = GOOGLE_CONNECT_URL;
  };

  const handleDisconnect = async (): Promise<void> => {
    const result = await disconnect();
    if (result.success) {
      message.success('Conta Google desconectada.');
      void fetchStatus(); // o novo motivo de bloqueio vem do servidor
    } else {
      message.error(result.error ?? 'Erro ao desconectar a conta Google.');
    }
  };

  const ready = status.publishReady;
  const reason = status.publishBlockReason;
  // Conexão removida pelo sistema: o card já explica a revogação e oferece Conectar — não repetir.
  // Só nesse motivo: sem setor, o card nem aparece e o alerta da DAT é a única explicação.
  const cardExplica = status.reconnectRequired && reason === 'google_not_connected';
  const blocked = cardExplica ? null : blockedMessage(ready, reason, statusError);
  const blockedIsWarning =
    reason === 'no_setor_scope' || reason === 'google_calendar_not_configured' || (!reason && !!statusError);

  const columns: ColumnsType<Solicitacao> = useMemo(() => [
    {
      title: 'Data/hora',
      dataIndex: 'inicio',
      key: 'inicio',
      width: 150,
      render: (inicio: string) => formatFortaleza(inicio),
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_evento_nome',
      key: 'tipo_evento',
      render: (nome: string | null) => nome || '-',
    },
    {
      // Nome, não username: o username de login pode ser o CPF (LGPD).
      title: 'Coordenador',
      dataIndex: 'coordenador_nome',
      key: 'coordenador',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Google Agenda',
      key: 'gcal',
      render: (_, row) => {
        const { tag } = gcalRowActions(row, { ready });
        return (
          <Space direction="vertical" size={2}>
            <Tag color={tag.color}>{tag.label}</Tag>
            {row.gcal_status === 'ERROR' && row.gcal_last_error && (
              <Text type="danger" style={{ fontSize: 12 }}>{row.gcal_last_error}</Text>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Meet',
      dataIndex: 'meet_link',
      key: 'meet',
      render: (href: string | null) => <MeetLink href={href} />,
    },
    {
      title: 'Ações',
      key: 'acoes',
      render: (_, row) => {
        const { actions, disabled } = gcalRowActions(row, { ready });
        const evento = `${row.projeto_nome ?? 'Evento'}, ${formatFortaleza(row.inicio)}`;
        return (
          <Space wrap size="small">
            {actions.map((action) => {
              const config = ACTIONS[action];
              return (
                <Popconfirm
                  key={action}
                  title={config.confirmTitle}
                  description={config.confirmDescription}
                  okText={config.okText}
                  cancelText="Cancelar"
                  okButtonProps={{ danger: config.danger }}
                  onConfirm={() => runAction(row, action)}
                  disabled={disabled}
                >
                  <Button
                    size="small"
                    danger={config.danger}
                    disabled={disabled}
                    aria-label={`${config.label}: ${evento}`}
                  >
                    {config.label}
                  </Button>
                </Popconfirm>
              );
            })}
          </Space>
        );
      },
    },
  ], [ready, runAction]);

  return (
    <section className="p-6" aria-labelledby={TITLE_ID}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <header>
            <Title level={2} id={TITLE_ID} className="m-0">
              Publicar na agenda do Google
            </Title>
            <Text type="secondary">
              Eventos aprovados do seu setor, a partir de hoje. Publique, atualize ou remova cada um
              na agenda oficial da organização.
            </Text>
          </header>
        </Card>

        {oauthReturn &&
          (oauthReturn.ok ? (
            <Alert type="success" role="status" showIcon message={OAUTH_SUCCESS_TEXT} />
          ) : (
            <Alert
              type="error"
              showIcon
              message={(oauthReturn.reason && OAUTH_ERROR_TEXT[oauthReturn.reason]) || OAUTH_ERROR_FALLBACK}
            />
          ))}

        {blocked && (
          <Alert
            type={blockedIsWarning ? 'warning' : 'info'}
            role={blockedIsWarning ? 'alert' : 'status'}
            showIcon
            message={blocked}
          />
        )}

        {/* Sem setor vigente não há o que publicar: nada de conectar conta. */}
        {reason !== 'no_setor_scope' && (
          <GoogleIntegrationCard
            status={status}
            fixedCalendar
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
          />
        )}

        <Card>
          <Table
            rowKey="id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            scroll={{ x: 'max-content' }}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total,
              showSizeChanger: false,
              showTotal: (count) => `Total: ${count} eventos`,
              onChange: (nextPage) => setPage(nextPage),
            }}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <span>
                      Nenhum evento aprovado do seu setor a partir de hoje. Eventos criados em{' '}
                      <Link to="/solicitacoes/nova">Nova Solicitação</Link> aparecem aqui depois de
                      aprovados.
                    </span>
                  }
                />
              ),
            }}
          />
        </Card>
      </Space>
    </section>
  );
}
