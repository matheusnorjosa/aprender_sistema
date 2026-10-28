/**
 * Nova Solicitação — página única (decisão do dono, 28/10/2026).
 *
 * Antes era um assistente de 4 passos. Agora cada evento é um cartão (`CartaoEvento`) com os
 * campos lado a lado, e um só botão "Criar solicitação" no fim. O clique confere tudo: com campo
 * faltando, nada é enviado, o resumo do topo diz o que falta e o foco vai ao primeiro campo com
 * problema. Nesta entrega a página tem um cartão e envia pelo POST de um evento
 * (`createSolicitacao`); ela já guarda a lista `eventos` para o "+" de vários eventos.
 */

import { useState, useCallback, useEffect, useRef, JSX } from 'react';
import { useBlocker, useNavigate, type BlockerFunction } from 'react-router';
// antd - direct imports for tree-shaking (Issue #424)
import Button from 'antd/es/button';
import Card from 'antd/es/card';
import Alert from 'antd/es/alert';
import Modal from 'antd/es/modal';
import message from 'antd/es/message';
import Typography from 'antd/es/typography';
// icons - direct imports for tree-shaking (Issue #425)
import ArrowLeftOutlined from '@ant-design/icons/ArrowLeftOutlined';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { createSolicitacao } from '../../api/solicitacoes';
import { optionalText } from './optionalText';
import { getMe } from '../../api/availability';
import { useAcesso } from '../../contexts/AcessoContext';
import logger from '../../utils/logger';
import { lerAvisoDoLogin, storageKeys } from '../../utils/storage';
import type { ID, AvailabilityConflictErrorPayload } from '../../types';
import CartaoEvento, { type CartaoEventoHandle } from './CartaoEvento';
import { FORM_INICIAL, perguntaAvaliarDo, type FormDataType, type QuemCria } from './evento';

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


/** Um evento da página: `chave` é estável (ids e React key); o número visível é a posição + 1. */
interface EventoDaPagina {
  chave: number;
  dados: FormDataType;
}

/** O que falta num evento, para o resumo do topo. */
interface ProblemasDoEvento {
  numero: number;
  motivos: string[];
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

  // Os eventos da página (por ora, um).
  const [eventos, setEventos] = useState<EventoDaPagina[]>([{ chave: 1, dados: FORM_INICIAL }]);
  const cartoes = useRef(new Map<number, CartaoEventoHandle>());
  // O que trava o "Criar", por evento: o id do alerta que diz o motivo.
  const [travas, setTravas] = useState<Record<number, string>>({});
  // Resumo do clique em "Criar" com problema: a única região viva da página.
  const [resumo, setResumo] = useState<ProblemasDoEvento[] | null>(null);

  // Sair da página descarta o que foi preenchido: com algo preenchido, pergunta antes,
  // começando no Cancelar (ação destrutiva, ux-principios). Toda saída para outra página passa
  // pelo `useBlocker` do data router (App.tsx): o botão do topo, o Voltar do navegador e o do
  // Android, o menu lateral e os outros links.
  const preenchido = eventos.some((e) => JSON.stringify(e.dados) !== JSON.stringify(FORM_INICIAL));
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

  // Mexer num evento tira o resumo do último clique (ele já pode não valer); os erros de cada
  // campo continuam junto do campo.
  const mudarEvento = useCallback((chave: number, parcial: Partial<FormDataType>): void => {
    setResumo(null);
    setEventos((atuais) => atuais.map((e) => (e.chave === chave ? { ...e, dados: { ...e.dados, ...parcial } } : e)));
  }, []);

  const marcarTrava = useCallback((chave: number, idDoMotivo: string | null): void => {
    setTravas((atuais) => {
      if ((atuais[chave] ?? null) === idDoMotivo) return atuais;
      const { [chave]: _antiga, ...outras } = atuais;
      return idDoMotivo ? { ...outras, [chave]: idDoMotivo } : outras;
    });
  }, []);
  // #1452: conflito antecipado ou recusado no envio trava o botão; ele aponta o primeiro motivo.
  const motivoDaTrava = eventos.map((e) => travas[e.chave]).find((id): id is string => Boolean(id)) ?? null;

  const handleSubmit = async (): Promise<void> => {
    setResumo(null);
    // Confere os eventos na ordem da tela; o foco vai ao primeiro problema do primeiro evento.
    const problemas: ProblemasDoEvento[] = [];
    for (const [indice, evento] of eventos.entries()) {
      const motivos = (await cartoes.current.get(evento.chave)?.validar({ focar: problemas.length === 0 })) ?? [];
      if (motivos.length > 0) problemas.push({ numero: indice + 1, motivos });
    }
    if (problemas.length > 0) {
      setResumo(problemas);
      return;
    }

    // Por ora a página tem um evento e envia pelo POST de um evento.
    const evento = eventos[0];
    if (!evento) return;
    const { chave, dados } = evento;
    // A conferência acima já garante cada um destes; aqui só estreita o tipo.
    if (
      !dados.projeto || !dados.tipoEvento || !dados.municipio || !dados.inicio || !dados.fim ||
      dados.coordenadorAcompanha === null
    ) {
      return;
    }

    setLoading(true);
    try {
      const payload = buildSolicitacaoPayload({
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

      await createSolicitacao(payload);
      message.success('Solicitação criada com sucesso!');
      saidaLiberada.current = true;
      void navigate('/solicitacoes/minhas');
    } catch (error) {
      logger.error('Erro ao criar solicitação:', error);

      // #1452: o backend recusa o double-booking com 400 `availability_conflict` e a
      // mensagem nomeando o formador. Antes o catch engolia isso e mostrava um genérico.
      const data = (error as { response?: { data?: unknown } })?.response?.data;
      const payloadErro = data as Partial<AvailabilityConflictErrorPayload> | undefined;

      if (payloadErro?.code === 'availability_conflict') {
        const bloqueados = payloadErro.errors?.blocked_participants ?? [];
        cartoes.current.get(chave)?.marcarConflitoDoEnvio(bloqueados);
        message.error(payloadErro.detail || 'Um participante já está alocado neste horário.');
      } else {
        // Recusa por campo (400): o motivo vem em `errors.<campo>`; o `detail` é o genérico
        // "Erro de validação.". Sem resposta (rede), a mensagem do próprio erro diz o que houve.
        const motivoDoCampo = Object.values((data as { errors?: Record<string, unknown> })?.errors ?? {})
          .flat()
          .find((texto): texto is string => typeof texto === 'string');
        const detail = (data as { detail?: string })?.detail;
        const semResposta = !(error as { response?: unknown })?.response ? (error as Error)?.message : undefined;
        message.error(
          motivoDoCampo || detail || semResposta || 'Erro ao criar solicitação. Verifique os dados e tente novamente.'
        );
      }
    } finally {
      setLoading(false);
    }
  };

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
            tela anunciar o resumo quando ele entrar. */}
        <div role="alert">
          {resumo && (
            <Alert
              type="error"
              showIcon
              role="none"
              className="mt-4"
              message="Corrija antes de criar a solicitação"
              description={
                <ul className="mb-0 pl-5">
                  {resumo.flatMap((p) =>
                    p.motivos.map((motivo, i) => (
                      <li key={`${p.numero}-${i}`}>
                        Evento {p.numero}: {motivo}
                      </li>
                    ))
                  )}
                </ul>
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
          />
        ))}

        <footer className="mt-6 flex justify-end">
          <Button
            type="primary"
            onClick={() => void handleSubmit()}
            loading={loading}
            // #1452: não deixa criar com conflito antecipado nem após o 400 do backend.
            disabled={motivoDaTrava !== null}
            aria-describedby={motivoDaTrava ?? undefined}
          >
            Criar solicitação
          </Button>
        </footer>
      </Card>
    </section>
  );
}
