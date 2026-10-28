/**
 * PublicacaoSetorPage — "Publicar na agenda" (#1656).
 *
 * A Apoio de Coordenação (policy `publish_setor_solicitacao`, NÃO `use_gcal`) conecta
 * a PRÓPRIA conta Google e publica, atualiza ou tira só do Google, no calendário oficial da
 * organização, os eventos APROVADOS do próprio setor (tirar do Google não apaga do sistema).
 * Excluir (decisão do dono, 27/10/2026) tira dos dois lados, só na linha que está no Google e que o
 * servidor diz que ela pode excluir (`pode_excluir`; o evento de outra pessoa só quando está no Google).
 *
 * - Lista: `GET /solicitacoes/?status=aprovado&publishable=true&date_from=<hoje em
 *   Fortaleza>&ordering=inicio`, paginada no servidor. O backend só devolve linhas que
 *   ela pode publicar. Nunca manda `mine` (pularia o escopo) nem `sector` (lê gerência).
 * - Prontidão: `status.publishReady`/`publishBlockReason`; sem prontidão as ações ficam
 *   desabilitadas, com o motivo visível.
 * - Polling só enquanto alguma linha está PENDING; `seqRef` descarta resposta obsoleta.
 */
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type JSX } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { Alert, Button, Card, Empty, Grid, Modal, Space, Tag, Typography, message } from 'antd';

import {
  cancelSolicitacao,
  deleteSolicitacao,
  listSolicitacoes,
  publishSolicitacao,
  resyncSolicitacao,
} from '../../api/solicitacoes';
import { MeetLink } from '../../components/MeetLink';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import GoogleIntegrationCard from '../../components/google/GoogleIntegrationCard';
import { OAuthRetornoAlert } from '../../components/google/OAuthRetornoAlert';
import { lerOAuthRetorno, type OAuthRetorno } from '../../utils/oauthRetorno';
import { TIMING } from '../../constants/timing';
import useGoogleIntegration from '../../hooks/useGoogleIntegration';
import { usePolling } from '../../hooks/usePolling';
import { syncChannel } from '../../services/syncChannel';
import type { ID, Solicitacao } from '../../types';
import type { PublishBlockReason } from '../../types/gcal';
import { formatFortaleza } from '../../utils/datetime';
import {
  confirmacaoDeExcluirNoGoogle,
  estaNoGoogle,
  gcalRowActions,
  type GcalRowAction,
  type GcalRowTag,
} from '../../utils/gcalRowActions';

const { Title, Text } = Typography;

const TITLE_ID = 'publicacao-setor-title';
const PAGE_SIZE = 20;
/** O OAuth volta para esta página (o backend valida o `return_to`). */
const GOOGLE_CONNECT_URL = `/api/oauth/google/start/?return_to=${encodeURIComponent('/solicitacoes/publicacao')}`;
/** Uma só mensagem de erro de carga em segundo plano (o polling não empilha toasts). */
const LOAD_ERROR_KEY = 'publicacao-setor-load';
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

const BLOCK_REASON_TEXT: Record<PublishBlockReason, string> = {
  no_setor_scope:
    'Seu cadastro não tem setor vigente. Peça à DAT para cadastrar seu vínculo de gerência.',
  google_not_connected: 'Conecte sua conta Google para publicar os eventos.',
  google_calendar_not_configured:
    'A agenda da organização ainda não foi configurada no sistema. Avise o Controle.',
};

const OAUTH_SUCCESS_TEXT = 'Conta Google conectada. Você já pode publicar os eventos do seu setor.';
interface ActionConfig {
  /** Texto do botão; também abre o aria-label (nome acessível contém o visível). */
  label: string;
  /** Texto do botão no celular (abaixo de `sm`); o nome acessível continua com o `label`. */
  labelCurto: string;
  /** Início do título da confirmação; o evento vem depois: "Tirar do Google Agenda: <evento>?". */
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
    labelCurto: 'Publicar',
    confirmTitle: 'Publicar na agenda da organização',
    confirmDescription: 'O evento é criado no calendário oficial da organização.',
    okText: 'Publicar',
    danger: false,
    successText: 'Publicação enviada; o status muda em alguns segundos.',
    run: (id) => publishSolicitacao(id),
  },
  tentar: {
    label: 'Tentar de novo',
    labelCurto: 'Tentar de novo',
    confirmTitle: 'Tentar publicar de novo',
    confirmDescription: 'O sistema envia o evento outra vez para o Google Agenda.',
    okText: 'Tentar de novo',
    danger: false,
    successText: 'Publicação enviada; o status muda em alguns segundos.',
    run: (id) => publishSolicitacao(id),
  },
  atualizar: {
    label: 'Atualizar no Google',
    labelCurto: 'Atualizar',
    confirmTitle: 'Atualizar no Google Agenda',
    confirmDescription: 'O evento no Google passa a ter os dados atuais do sistema.',
    okText: 'Atualizar',
    danger: false,
    successText: 'Atualização enviada; o status muda em alguns segundos.',
    run: (id) => resyncSolicitacao(id),
  },
  // "Remover" sozinho parecia apagar o evento: o rótulo diz, também no celular, que só sai do Google.
  remover: {
    label: 'Tirar só do Google',
    labelCurto: 'Tirar só do Google',
    confirmTitle: 'Tirar do Google Agenda',
    // Sem apontar Minhas Solicitações: ela só lista os eventos de quem está logado.
    confirmDescription: 'O evento sai só da agenda da organização e continua no sistema.',
    okText: 'Tirar do Google',
    danger: true,
    successText: 'Pedido enviado: o evento sai do Google Agenda em alguns segundos e continua no sistema.',
    run: (id) => cancelSolicitacao(id),
  },
};

/** Formato do erro lançado por `fetchAPI` (status + corpo JSON do backend). */
interface ApiErrorLike {
  message?: string;
  status?: number;
  response?: { status?: number; data?: { code?: string; detail?: string } };
}

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
  // A lista não carregou: o motivo vai no lugar das linhas. Antes só um toast de 3 s, e a tabela
  // ficava no vazio "Nenhum evento aprovado do seu setor", como se não houvesse o que publicar.
  const [erroCarga, setErroCarga] = useState<string | null>(null);
  const [oauthReturn, setOauthReturn] = useState<OAuthRetorno | null>(null);

  // Latest-wins: polling, paginação e ações disparam cargas concorrentes; só a
  // mais recente grava na tela.
  const seqRef = useRef(0);

  /**
   * `silencioso`: carga em segundo plano (polling, outra aba). Se falhar, a lista que estava na tela
   * fica, com um toast; o aviso no lugar das linhas é só para a carga pedida pela pessoa.
   */
  const load = useCallback(async (silencioso = false): Promise<void> => {
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
      setErroCarga(null);
    } catch (error) {
      if (seq !== seqRef.current) return;
      // A página deixou de existir (a lista encolheu): volta uma. Sem isso, o erro tirava a
      // paginação e o "Tentar de novo" repetia o mesmo 404.
      if ((error as ApiErrorLike).status === 404 && page > 1) {
        setPage((p) => Math.max(1, p - 1));
        return;
      }
      if (!silencioso) {
        setErroCarga((error as Error).message || 'Erro desconhecido.');
        return;
      }
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
  usePolling(() => load(true), {
    enabled: rows.some((row) => row.gcal_status === 'PENDING'),
    intervalMs: TIMING.PUBLICACAO_PENDENTE_POLL_MS,
    immediate: false,
  });

  // Mudança de solicitação em outra aba → recarrega.
  useEffect(() => syncChannel.subscribe('solicitacoes', () => { void load(true); }), [load]);

  // Volta do OAuth (?google=connected | ?google=error&reason=…): mostra o resultado,
  // tira os parâmetros da URL e recarrega o status da integração.
  useEffect(() => {
    const retorno = lerOAuthRetorno(location.search);
    if (!retorno) return;
    setOauthReturn(retorno);
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
    // Com await, o diálogo só fecha com a linha já recarregada: o afterClose sabe se o botão sobrou.
    await load();
  }, [handleActionError, load]);

  // Alvo do foco quando o botão da linha some com a recarga; fora do Tab.
  const listaRef = useRef<HTMLDivElement>(null);
  const focarLista = useCallback((): void => {
    const alvo = listaRef.current;
    if (!alvo) return;
    // Focável só neste instante (mesmo padrão do "Tentar de novo" da ResponsiveTable).
    alvo.setAttribute('tabindex', '-1');
    alvo.addEventListener('blur', () => alvo.removeAttribute('tabindex'), { once: true });
    alvo.focus();
  }, []);

  // Confirmação num diálogo de verdade (role=dialog, foco preso e devolvido ao botão da linha, Esc):
  // o Popconfirm não recebia o foco e, pelo teclado, a confirmação ficava fora de alcance (item 36).
  // Abre no Cancelar e cita o evento; só o OK dispara a ação, nunca a tela sozinha.
  // Publicar, Atualizar e Remover trocam ou tiram o botão da linha: sem ele, o foco vai para a lista,
  // não para o body (o Tab recomeçaria do topo da página a cada evento).
  const [modal, contextoDoModal] = Modal.useModal();
  const confirmar = useCallback((row: Solicitacao, action: GcalRowAction, evento: string): void => {
    const config = ACTIONS[action];
    const gatilho = document.activeElement;
    void modal.confirm({
      afterClose: () => {
        if (!gatilho?.isConnected) focarLista();
      },
      title: `${config.confirmTitle}: ${evento}?`,
      content: config.confirmDescription,
      okText: config.okText,
      okButtonProps: { danger: config.danger },
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: () => runAction(row, action),
    });
  }, [modal, runAction, focarLista]);

  // Excluir tira dos dois lados (mesmo DELETE e mesma confirmação de Minhas Solicitações). O 400 traz o
  // motivo legível do servidor (Google fora, já aprovada…): ele vai inteiro para a pessoa.
  const confirmarExclusao = useCallback((row: Solicitacao): void => {
    const gatilho = document.activeElement;
    void modal.confirm({
      ...confirmacaoDeExcluirNoGoogle(row),
      afterClose: () => {
        if (!gatilho?.isConnected) focarLista();
      },
      okText: 'Sim, excluir',
      okButtonProps: { danger: true },
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: async () => {
        try {
          await deleteSolicitacao(row.id);
        } catch (error) {
          const err = error as ApiErrorLike;
          const httpStatus = err.response?.status ?? err.status;
          const code = err.response?.data?.code;
          // Conexão com o Google, 404, 409 e 429: o mesmo tratamento das outras ações (recarrega o status).
          if (httpStatus === 404 || httpStatus === 409 || httpStatus === 429 || code === 'google_not_connected') {
            handleActionError(error);
          } else {
            message.error(err.response?.data?.detail || `Não foi possível excluir: ${err.message ?? 'erro desconhecido'}`);
          }
          // A recusa pode chegar depois de o Google já ter sido limpo: recarrega para a linha dizer a verdade.
          if (httpStatus !== 404) void load();
          return;
        }
        message.success(
          row.gcal_status === 'ERROR' && !row.external_event_id
            ? 'Evento excluído do sistema e do Google Agenda, se estava lá.'
            : 'Evento excluído do sistema e do Google Agenda.',
        );
        await load();
      },
    });
  }, [modal, focarLista, handleActionError, load]);

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

  // Sem rolagem horizontal (achado do item 36): sempre na linha, o Evento (data/hora, projeto,
  // município e o estado no Google, com o motivo do erro quebrando linha) e as ações; o resto sobe por largura e,
  // escondido, vai para a linha expandida. No celular os botões usam o rótulo curto.
  const celular = !Grid.useBreakpoint().sm;
  const columns: ColunaResponsiva<Solicitacao>[] = useMemo(() => [
    {
      title: 'Evento',
      key: 'evento',
      render: (_, row) => {
        const { tag } = gcalRowActions(row, { ready });
        return (
          <Space direction="vertical" size={2} className="w-full">
            <div style={UMA_LINHA}>{formatFortaleza(row.inicio)}</div>
            <div style={UMA_LINHA} title={row.projeto_nome || undefined}>{row.projeto_nome || '-'}</div>
            <div style={UMA_LINHA} title={row.municipio_nome || undefined}>{row.municipio_nome || '-'}</div>
            <Tag color={tag.color} style={{ whiteSpace: 'normal', color: TEXTO_DA_TAG_GCAL[tag.color] }}>{tag.label}</Tag>
            {row.gcal_status === 'ERROR' && row.gcal_last_error && (
              // O motivo do Google tem até 500 caracteres: quebra linha na célula em vez de esticar a tabela.
              <Text type="danger" style={{ color: COR_DO_MOTIVO_DO_ERRO, fontSize: 12, whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
                {row.gcal_last_error}
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_evento_nome',
      key: 'tipo_evento',
      responsive: VISIVEL_A_PARTIR.lg,
      ellipsis: true,
      render: (nome) => (nome as string | null) || '-',
    },
    {
      // Nome, não username: o username de login pode ser o CPF (LGPD).
      title: 'Coordenador',
      dataIndex: 'coordenador_nome',
      key: 'coordenador',
      responsive: VISIVEL_A_PARTIR.lg,
      ellipsis: true,
      render: (nome) => (nome as string | null) || '-',
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
      key: 'acoes',
      // Folga para a fonte mais larga do Linux da CI: "Atualizar no Google" com +1,5 px por letra.
      width: celular ? 116 : 190,
      render: (_, row) => {
        const { actions, disabled } = gcalRowActions(row, { ready });
        const evento = `${row.projeto_nome ?? 'Evento'}, ${formatFortaleza(row.inicio)}`;
        const podeExcluir = row.pode_excluir === true && estaNoGoogle(row);
        return (
          <Space wrap size="small">
            {actions.map((action) => {
              const config = ACTIONS[action];
              return (
                <Button
                  key={action}
                  size="small"
                  danger={config.danger}
                  disabled={disabled}
                  aria-label={`${config.label}: ${evento}`}
                  // No celular, "Tirar só do Google" quebra linha no botão em vez de alargar a coluna.
                  style={celular ? { height: 'auto', whiteSpace: 'normal' } : undefined}
                  onClick={() => confirmar(row, action, evento)}
                >
                  {celular ? config.labelCurto : config.label}
                </Button>
              );
            })}
            {podeExcluir && (
              <Button
                size="small"
                danger
                disabled={disabled}
                aria-label={`Excluir: ${evento}`}
                style={celular ? { height: 'auto', whiteSpace: 'normal' } : undefined}
                onClick={() => confirmarExclusao(row)}
              >
                Excluir
              </Button>
            )}
          </Space>
        );
      },
    },
  ], [ready, confirmar, confirmarExclusao, celular]);

  return (
    <section className="p-3 sm:p-6" aria-labelledby={TITLE_ID}>
      {contextoDoModal}
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <header>
            <Title level={2} id={TITLE_ID} className="m-0">
              Publicar na agenda do Google
            </Title>
            <Text type="secondary">
              Eventos aprovados do seu setor, a partir de hoje. Publique ou atualize cada um na agenda
              oficial da organização. Tirar só do Google deixa o evento no sistema; Excluir tira dos dois lados.
            </Text>
          </header>
        </Card>

        {oauthReturn && <OAuthRetornoAlert retorno={oauthReturn} textoSucesso={OAUTH_SUCCESS_TEXT} />}

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

        <Card ref={listaRef} {...(celular && { styles: { body: { padding: 12 } } })}>
          <ResponsiveTable<Solicitacao>
            rowKey="id"
            columns={columns}
            dataSource={rows}
            loading={loading}
            nomeDaLinha={(row) => `${row.projeto_nome ?? 'Evento'}, ${formatFortaleza(row.inicio)}`}
            erro={erroCarga}
            onTentarDeNovo={() => { void load(); }}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total,
              showSizeChanger: false,
              showTotal: (count) => `Total: ${count} ${count === 1 ? 'evento' : 'eventos'}`,
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
