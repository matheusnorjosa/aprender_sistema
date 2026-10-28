/**
 * Nova Solicitação — página única, com vários eventos (decisões do dono, 28/10/2026).
 *
 * Cada evento é um cartão (`CartaoEvento`) com os campos lado a lado. A página começa com 1 evento;
 * "+ Adicionar outro evento" acrescenta um em branco (até 10) e cada evento extra tem "Remover".
 * Nada é comum entre os eventos. Um só botão no fim ("Criar solicitação" com 1 evento, "Criar N
 * eventos" com mais): o clique confere todos, na ordem; com campo faltando, nada é enviado, o
 * resumo do topo diz o que falta e o foco vai ao primeiro campo com problema. O envio é sempre o
 * lote (`createSolicitacoesEmLote`, tudo ou nada): no 400 `lote_invalido` cada item volta ao
 * cartão que estava naquela posição, e o choque entre os eventos quem confere é o servidor.
 */

import { useState, useCallback, useEffect, useRef, JSX } from 'react';
import { useBlocker, useNavigate, type BlockerFunction } from 'react-router';
// antd - direct imports for tree-shaking (Issue #424)
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Alert from 'antd/es/alert';
import PlusOutlined from '@ant-design/icons/PlusOutlined';
import Modal from 'antd/es/modal';
import message from 'antd/es/message';
import Typography from 'antd/es/typography';
// icons - direct imports for tree-shaking (Issue #425)
import ArrowLeftOutlined from '@ant-design/icons/ArrowLeftOutlined';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { createSolicitacoesEmLote, type ErroDoEventoNoLote } from '../../api/solicitacoes';
import { optionalText } from './optionalText';
import { getMe } from '../../api/availability';
import { useAcesso } from '../../contexts/AcessoContext';
import logger from '../../utils/logger';
import { lerAvisoDoLogin, storageKeys } from '../../utils/storage';
import type { ID, SolicitacaoPayload } from '../../types';
import CartaoEvento, { type CartaoEventoHandle } from './CartaoEvento';
import {
  estaEmBranco,
  FORM_INICIAL,
  mensagensDe,
  perguntaAvaliarDo,
  type FormDataType,
  type QuemCria,
} from './evento';

dayjs.extend(utc);

const { Title } = Typography;

/** Entrada achatada p/ montar o payload de criação de solicitação (validada em handleSubmit). */
export interface SolicitacaoWizardPayloadInput {
  municipioId: ID;
  projetoId: ID;
  tipoEventoId: ID;
  inicio: string;
  fim: string;
  tipo: string;
  encontro: string;
  segmento: string;
  observacoes: string;
  local: string;
  isOnline: boolean;
  formadorIds: ID[];
  /** #1666: FK do coordenador RESPONSÁVEL. null → backend usa quem cria, se for coordenador. */
  coordenadorResponsavelId: ID | null;
  /** "O coordenador responsável vai acompanhar o evento?" */
  coordenadorAcompanha: boolean;
  /** "Você pretende avaliar o formador nesse evento?" — null quando a pergunta não foi feita. */
  avaliar: { pretende: boolean; formadorAvaliadoId: ID | null } | null;
}

/**
 * Monta o payload de criação de solicitação (co-locado + exportado p/ teste, como buildCompraPayload).
 * A lista de coordenadores acompanhantes saiu (05/10/2026): só formadores em extra_participants.
 */
export function buildSolicitacaoPayload(input: SolicitacaoWizardPayloadInput): Record<string, unknown> {
  return {
    municipio: input.municipioId,
    projeto: input.projetoId,
    tipo_evento: input.tipoEventoId,
    inicio: dayjs(input.inicio).utc().format(),
    fim: dayjs(input.fim).utc().format(),
    tipo: input.tipo || null,
    encontro: input.encontro || null,
    segmento: input.segmento || null,
    observacoes: optionalText(input.observacoes),
    local: input.local || '',
    is_online: input.isOnline,
    // #1666: FK do coordenador RESPONSÁVEL. Antes ausente → backend usava o criador.
    coordenador: input.coordenadorResponsavelId,
    coordenador_acompanha: input.coordenadorAcompanha,
    ...(input.avaliar
      ? {
          pretende_avaliar_formador: input.avaliar.pretende,
          formador_avaliado: input.avaliar.pretende ? input.avaliar.formadorAvaliadoId : null,
        }
      : {}),
    extra_participants: {
      formador_ids: input.formadorIds,
    },
  };
}


/** Limite de eventos por envio (o mesmo `MAX_EVENTOS_LOTE` do servidor). */
const MAX_EVENTOS = 10;

/** Sem resposta (rede, ou 5xx do proxy): o servidor pode ter criado. A pessoa confere antes de reenviar. */
const FALHA_DE_REDE = 'Não foi possível falar com o servidor. Confira em Minhas Solicitações antes de enviar de novo.';

/** Um evento da página: `chave` é estável (ids e React key); o número visível é a posição + 1. */
interface EventoDaPagina {
  chave: number;
  dados: FormDataType;
}

/** Uma linha do resumo do topo: um problema de um evento. */
interface LinhaDoResumo {
  chave: number;
  texto: string;
}

/** O resumo do clique em "Criar" com problema (da conferência da tela ou do servidor). */
interface Resumo {
  titulo: string;
  linhas: LinhaDoResumo[];
}

/** O payload de um evento conferido; null se faltar o que a conferência já exige (só estreita o tipo). */
function payloadDo(dados: FormDataType): SolicitacaoPayload | null {
  if (
    !dados.projeto || !dados.tipoEvento || !dados.municipio || !dados.inicio || !dados.fim ||
    dados.coordenadorAcompanha === null
  ) {
    return null;
  }
  return buildSolicitacaoPayload({
    municipioId: dados.municipio.id,
    projetoId: dados.projeto.id,
    tipoEventoId: dados.tipoEvento.id,
    inicio: dados.inicio,
    fim: dados.fim,
    tipo: dados.tipo,
    encontro: dados.encontro,
    segmento: dados.segmento,
    observacoes: dados.observacoes,
    local: dados.local,
    // PR19: modalidade online/presencial
    isOnline: !!dados.is_online,
    formadorIds: dados.formadores.map((f) => f.id),
    // #1666: FK do coordenador responsável escolhido (null → quem cria, se coordenador).
    coordenadorResponsavelId: dados.coordenadorResponsavel?.id ?? null,
    coordenadorAcompanha: dados.coordenadorAcompanha,
    avaliar: perguntaAvaliarDo(dados)
      ? { pretende: dados.pretendeAvaliar === true, formadorAvaliadoId: dados.formadorAvaliado }
      : null,
  });
}

/** "2 eventos criados (1 vai para aprovação)"; no singular com 1. */
function mensagemDeSucesso(status: string[]): string {
  const criados = status.length === 1 ? '1 evento criado' : `${status.length} eventos criados`;
  const pendentes = status.filter((s) => s === 'pendente').length;
  if (pendentes === 0) return criados;
  return `${criados} (${pendentes} ${pendentes === 1 ? 'vai' : 'vão'} para aprovação)`;
}

/** As linhas do resumo para um evento recusado pelo servidor: uma por mensagem. */
function textosDoErro(item: ErroDoEventoNoLote): string[] {
  if (item.code === 'availability_conflict') return [item.detail];
  const textos = [...new Set(mensagensDe(item.errors ?? {}))];
  return textos.length > 0 ? textos : [item.detail];
}

export default function NewSolicitacaoWizard(): JSX.Element {
  const navigate = useNavigate();

  const [loading, setLoading] = useState<boolean>(false);
  // Regra da compra: quem tem create_solicitation_without_purchase (o superusuário e, desde o PR 10, o DAT)
  // escolhe projeto e município sem compra. A mesma capacidade que o backend aceita.
  const dispensaCompra = useAcesso().caps.canCreateSolicitationWithoutPurchase;
  // Quem cria: é o responsável quando nenhum outro é escolhido (decisão do dono, 05/10/2026) se o
  // backend aceita o vazio para o projeto escolhido (`responsavel_padrao` do lookup de projetos: papel
  // COORDENADOR na gerência do projeto, PR 9). Só entra na checagem de agenda se acompanhar.
  const [me, setMe] = useState<QuemCria | null>(null);

  // Os eventos da página: começa com 1. A chave nunca se repete (nem depois de remover).
  const [eventos, setEventos] = useState<EventoDaPagina[]>([{ chave: 1, dados: FORM_INICIAL }]);
  const proximaChave = useRef(2);
  const cartoes = useRef(new Map<number, CartaoEventoHandle>());
  // O que trava o "Criar", por evento: o id do alerta que diz o motivo.
  const [travas, setTravas] = useState<Record<number, string>>({});
  // Resumo do clique em "Criar" com problema e o anúncio de adicionar/remover: a única região viva.
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [anuncio, setAnuncio] = useState<{ texto: string; vez: number } | null>(null);
  // O que o servidor recusou no último envio, por chave do evento. Vale até qualquer evento mudar
  // (o choque entre eventos depende do outro) ou até um evento entrar ou sair.
  const [errosDoLote, setErrosDoLote] = useState<Record<number, ErroDoEventoNoLote> | null>(null);
  // Título que recebe o foco depois de o cartão entrar ou sair da tela.
  const focarDepois = useRef<number | null>(null);

  // Sair da página descarta o que foi preenchido: com algo preenchido, pergunta antes,
  // começando no Cancelar (ação destrutiva, ux-principios). Toda saída para outra página passa
  // pelo `useBlocker` do data router (App.tsx): o botão do topo, o Voltar do navegador e o do
  // Android, o menu lateral e os outros links.
  // Um evento extra em branco não conta.
  const preenchido = eventos.some((e) => !estaEmBranco(e.dados));
  // Depois do envio com sucesso, sai sem perguntar: o que foi preenchido virou a solicitação.
  const saidaLiberada = useRef(false);
  const deveSegurar = useCallback<BlockerFunction>(
    ({ currentLocation, nextLocation }) =>
      preenchido && !saidaLiberada.current && currentLocation.pathname !== nextLocation.pathname,
    [preenchido],
  );
  const bloqueio = useBlocker(deveSegurar);
  // O bloqueio da hora: outro Voltar com o aviso aberto bloqueia de novo, e "Sair" segue o último.
  const bloqueioAtual = useRef(bloqueio);
  // O aviso aberto: o `Modal.confirm` não é ligado ao componente, então ele é fechado à mão
  // quando a página sai da tela (não fica aberto sobre outra).
  const aviso = useRef<ReturnType<typeof Modal.confirm> | null>(null);
  useEffect(() => {
    bloqueioAtual.current = bloqueio;
    if (bloqueio.state !== 'blocked' || aviso.current) return;
    aviso.current = Modal.confirm({
      title: 'Sair sem criar a solicitação?',
      content: 'O que você preencheu será perdido.',
      okText: 'Sair e descartar',
      okType: 'danger',
      cancelText: 'Continuar preenchendo',
      autoFocusButton: 'cancel',
      onOk: () => {
        aviso.current = null;
        if (bloqueioAtual.current.state === 'blocked') bloqueioAtual.current.proceed();
      },
      onCancel: () => {
        aviso.current = null;
        if (bloqueioAtual.current.state === 'blocked') bloqueioAtual.current.reset();
      },
    });
  }, [bloqueio]);
  useEffect(() => () => aviso.current?.destroy(), []);
  const sairDoAssistente = (): void => {
    void navigate('/solicitacoes/minhas');
  };

  // Recarregar ou fechar a aba não passa pelo roteador: com algo preenchido, o aviso do próprio
  // navegador (`beforeunload`).
  useEffect(() => {
    if (!preenchido) return undefined;
    const aoDescarregar = (e: BeforeUnloadEvent): void => {
      // O reload do próprio app leva ao login e não é segurado: a sessão encerrada guarda o
      // motivo para o login; o "Sair" apaga o horário comum às abas (App.tsx). Com Cancelar, a
      // aba ficaria na página sem sessão e o app não a levaria mais ao login.
      if (lerAvisoDoLogin() !== null) return;
      try {
        if (localStorage.getItem(storageKeys.sessaoUltimaResposta) === null) return;
      } catch {
        // storage bloqueado: sem como saber, segue perguntando
      }
      e.preventDefault();
    };
    window.addEventListener('beforeunload', aoDescarregar);
    return () => window.removeEventListener('beforeunload', aoDescarregar);
  }, [preenchido]);

  useEffect(() => {
    let mounted = true;
    const loadUserRole = async (): Promise<void> => {
      try {
        const me = await getMe();
        if (mounted) {
          setMe({ id: me.id, nome: me.name || me.username || 'Você' });
        }
      } catch (error) {
        logger.warn('Falha ao carregar perfil do usuário na Nova Solicitação:', error);
      }
    };

    void loadUserRole();
    return () => {
      mounted = false;
    };
  }, []);

  // Mexer em qualquer evento tira o resumo do último clique e o que o servidor recusou (já pode não
  // valer); os erros de cada campo da conferência da tela continuam junto do campo.
  const mudarEvento = useCallback((chave: number, parcial: Partial<FormDataType>): void => {
    setResumo(null);
    setErrosDoLote(null);
    setEventos((atuais) => atuais.map((e) => (e.chave === chave ? { ...e, dados: { ...e.dados, ...parcial } } : e)));
  }, []);

  const anunciar = (texto: string): void => setAnuncio((atual) => ({ texto, vez: (atual?.vez ?? 0) + 1 }));

  // O foco vai ao título do cartão depois de a lista mudar na tela.
  useEffect(() => {
    if (focarDepois.current === null) return;
    cartoes.current.get(focarDepois.current)?.focarTitulo();
    focarDepois.current = null;
  }, [eventos]);

  const adicionarEvento = (): void => {
    if (eventos.length >= MAX_EVENTOS) return;
    const chave = proximaChave.current;
    proximaChave.current += 1;
    setResumo(null);
    setErrosDoLote(null);
    setEventos([...eventos, { chave, dados: FORM_INICIAL }]);
    focarDepois.current = chave;
    anunciar(`Evento ${eventos.length + 1} adicionado`);
  };

  const removerEvento = (chave: number): void => {
    const posicao = eventos.findIndex((e) => e.chave === chave);
    if (posicao <= 0) return;
    setResumo(null);
    setErrosDoLote(null);
    setEventos(eventos.filter((e) => e.chave !== chave));
    focarDepois.current = eventos[posicao - 1]?.chave ?? null;
    anunciar(`Evento ${posicao + 1} removido`);
  };

  const marcarTrava = useCallback((chave: number, idDoMotivo: string | null): void => {
    setTravas((atuais) => {
      if ((atuais[chave] ?? null) === idDoMotivo) return atuais;
      const { [chave]: _antiga, ...outras } = atuais;
      return idDoMotivo ? { ...outras, [chave]: idDoMotivo } : outras;
    });
  }, []);
  // #1452: conflito antecipado ou recusado no envio trava o botão; ele aponta o primeiro motivo.
  const motivoDaTrava = eventos.map((e) => travas[e.chave]).find((id): id is string => Boolean(id)) ?? null;

  // O servidor recusou o lote (tudo ou nada): cada item volta ao evento que estava naquela posição
  // no envio (`indice` conta do 0). Fora do lote, sem resposta ou 5xx: só o aviso de rede.
  const tratarRecusa = (error: unknown, enviados: EventoDaPagina[]): void => {
    logger.error('Erro ao criar os eventos:', error);
    const resposta = (error as { response?: { status?: number; data?: unknown } } | null)?.response;
    if (!resposta || (resposta.status ?? 0) >= 500) {
      message.error(FALHA_DE_REDE);
      return;
    }
    const data = resposta.data as { detail?: string; code?: string; errors?: { itens?: unknown } } | null | undefined;
    const itens = Array.isArray(data?.errors?.itens) ? (data.errors.itens as ErroDoEventoNoLote[]) : null;
    if (data?.code !== 'lote_invalido' || !itens) {
      // Recusa do envio inteiro (permissão, limite de envios): o motivo no resumo do topo.
      setResumo({ titulo: data?.detail || 'Não foi possível criar. Tente de novo.', linhas: [] });
      return;
    }
    const porChave: Record<number, ErroDoEventoNoLote> = {};
    const linhas: LinhaDoResumo[] = [];
    for (const item of itens) {
      const evento = enviados[item.indice];
      if (!evento) continue;
      porChave[evento.chave] = item;
      linhas.push(...textosDoErro(item).map((texto) => ({ chave: evento.chave, texto })));
    }
    setErrosDoLote(porChave);
    setResumo({ titulo: data.detail || 'Nada foi criado.', linhas });
    const primeiro = linhas[0];
    if (primeiro) cartoes.current.get(primeiro.chave)?.focarTitulo();
  };

  const conferirEEnviar = async (): Promise<void> => {
    setResumo(null);
    setErrosDoLote(null);
    // A região viva lê tudo o que tem (role=alert é atômica): o anúncio velho sai antes do resumo.
    setAnuncio(null);
    // Confere os eventos na ordem da tela; o foco vai ao primeiro problema do primeiro evento.
    const linhas: LinhaDoResumo[] = [];
    for (const evento of eventos) {
      const motivos = (await cartoes.current.get(evento.chave)?.validar({ focar: linhas.length === 0 })) ?? [];
      linhas.push(...motivos.map((texto) => ({ chave: evento.chave, texto })));
    }
    if (linhas.length > 0) {
      const titulo = eventos.length === 1 ? 'Corrija antes de criar a solicitação' : 'Corrija antes de criar os eventos';
      setResumo({ titulo, linhas });
      return;
    }

    // Sempre o lote, também com 1 evento: tudo ou nada.
    const enviados = eventos;
    const payloads = enviados.map((e) => payloadDo(e.dados));
    if (payloads.some((p) => p === null)) return;
    try {
      const criados = await createSolicitacoesEmLote(payloads.filter((p): p is SolicitacaoPayload => p !== null));
      message.success(mensagemDeSucesso(criados.eventos.map((e) => e.status)));
      saidaLiberada.current = true;
      void navigate('/solicitacoes/minhas');
    } catch (error) {
      tratarRecusa(error, enviados);
    }
  };

  // Um clique por vez: a conferência é assíncrona, e um segundo clique antes de ela (e o envio)
  // acabar mandaria o evento de novo.
  const enviando = useRef(false);
  const handleSubmit = async (): Promise<void> => {
    if (enviando.current) return;
    enviando.current = true;
    setLoading(true);
    try {
      await conferirEEnviar();
    } finally {
      enviando.current = false;
      setLoading(false);
    }
  };

  // Número visível de cada evento: a posição + 1 (muda quando um evento sai).
  const numeroDe = (chave: number): number => eventos.findIndex((e) => e.chave === chave) + 1;
  const linhasDoResumo = (resumo?.linhas ?? []).filter((l) => numeroDe(l.chave) > 0);
  const comProblema = new Set(linhasDoResumo.map((l) => l.chave));
  const noLimite = eventos.length >= MAX_EVENTOS;

  return (
    <section className="p-6 max-w-4xl mx-auto" aria-labelledby="nova-solicitacao-title">
      <Card>
        <header>
          {/* Sai da página: o texto diz para onde. */}
          <Button icon={<ArrowLeftOutlined />} onClick={sairDoAssistente} className="mb-4">
            Voltar para Minhas Solicitações
          </Button>

          <Title level={2} className="mb-2" id="nova-solicitacao-title">Nova Solicitação</Title>
        </header>

        {/* A única região viva da página: sempre montada (vazia sem problema), para o leitor de
            tela anunciar o resumo e o "Evento N adicionado/removido" quando eles entram. */}
        <div role="alert">
          {anuncio && (
            <span key={anuncio.vez} className="sr-only">
              {anuncio.texto}
            </span>
          )}
          {resumo && (
            <Alert
              type="error"
              showIcon
              role="none"
              className="mt-4"
              message={resumo.titulo}
              description={
                linhasDoResumo.length > 0 ? (
                  <ul className="mb-0 pl-5">
                    {linhasDoResumo.map((linha, i) => (
                      <li key={`${linha.chave}-${i}`}>
                        {/* Cada linha leva ao evento. Quebra linha: nada passa da largura da tela. */}
                        <button
                          type="button"
                          className="cursor-pointer border-0 bg-transparent p-0 text-left underline break-words"
                          onClick={() => cartoes.current.get(linha.chave)?.focarTitulo()}
                        >
                          Evento {numeroDe(linha.chave)}: {linha.texto}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : undefined
              }
            />
          )}
        </div>

        {eventos.map((evento, indice) => (
          <CartaoEvento
            key={evento.chave}
            ref={(cartao: CartaoEventoHandle | null) => {
              if (cartao) cartoes.current.set(evento.chave, cartao);
              else cartoes.current.delete(evento.chave);
            }}
            chave={evento.chave}
            numero={indice + 1}
            dados={evento.dados}
            onChange={mudarEvento}
            me={me}
            dispensaCompra={dispensaCompra}
            onTrava={marcarTrava}
            erroDoEnvio={errosDoLote?.[evento.chave] ?? null}
            comProblema={comProblema.has(evento.chave)}
            onRemover={indice > 0 ? removerEvento : undefined}
          />
        ))}

        <div className="mt-4">
          <Button icon={<PlusOutlined aria-hidden />} onClick={adicionarEvento} disabled={noLimite}>
            {noLimite ? `Limite de ${MAX_EVENTOS} eventos por vez` : 'Adicionar outro evento'}
          </Button>
        </div>

        <footer className="mt-6 flex justify-end">
          <Button
            type="primary"
            onClick={() => void handleSubmit()}
            loading={loading}
            // #1452: não deixa criar com conflito antecipado nem após o 400 do backend.
            disabled={motivoDaTrava !== null}
            aria-describedby={motivoDaTrava ?? undefined}
          >
            {eventos.length === 1 ? 'Criar solicitação' : `Criar ${eventos.length} eventos`}
          </Button>
        </footer>
      </Card>
    </section>
  );
}
