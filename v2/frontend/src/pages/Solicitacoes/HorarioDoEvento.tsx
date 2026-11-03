/**
 * HorarioDoEvento — um horário do cartão da Nova Solicitação (decisão do dono, 03/11/2026).
 *
 * Linha 2 do cartão (Data | Início | Fim), linha 3 (Formadores | Coordenador responsável, com "vai
 * acompanhar?") e a pergunta de avaliar o formador. Cada horário vira um evento separado no lote, e a
 * prévia de agenda roda aqui, só com as pessoas deste horário. Com mais de um horário, o bloco é um
 * grupo nomeado pelo subtítulo "Horário N" e, do 2º em diante, tem "Remover horário". Com um só, nada
 * disso aparece e os ids são os de sempre (`evento-<chave>_…`): o 1º horário nunca sai do cartão.
 *
 * O Form do antd é do horário, sem `<form>` próprio (`component={false}`, dentro do Form do cartão). O
 * cartão confere o horário pelo `ref` e devolve a ele o que o servidor recusou neste item do lote.
 */

import { useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState, type JSX, type ReactNode, type Ref } from 'react';
// antd - direct imports for tree-shaking (Issue #424)
import Alert from 'antd/es/alert';
import Button from 'antd/es/button';
import Form from 'antd/es/form';
import Modal from 'antd/es/modal';
import Radio from 'antd/es/radio';
import type { RadioChangeEvent } from 'antd/es/radio';
import Select from 'antd/es/select';
import Typography from 'antd/es/typography';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import { lookupUsuarios, type LookupItem } from '../../api/lookup';
import { useAvailabilityPreview } from '../../hooks/useAvailabilityPreview';
import DateTimeRange, { type DateTimeRangeValue } from '../../components/DateTimeRange';
import ComboBox from '../../components/ComboBox';
import FormadoresPicker from '../../components/FormadoresPicker';
import AvailabilityConflictAlert, { AvisosDeAgenda } from '../../components/AvailabilityConflictAlert';
import logger from '../../utils/logger';
import type { BlockedParticipant } from '../../types';
import {
  eventoDoHorario,
  formadoresAvaliaveisDo,
  horarioEstaEmBranco,
  ORDEM_DO_HORARIO,
  participantesDo,
  perguntaAvaliarDo,
  type ComboBoxValue,
  type FormDataType,
  type Horario,
  type ParticipantType,
  type QuemCria,
} from './evento';

dayjs.extend(utc);
dayjs.extend(timezone);

const { Title } = Typography;

const RANGE_TIMEZONE = 'America/Fortaleza';

/** Opções das perguntas Sim/Não (decisão do dono, 05/10/2026). */
const SIM_NAO = [
  { label: 'Sim', value: true },
  { label: 'Não', value: false },
];

/** Lista vazia estável (sem conflito recusado no envio). */
const SEM_BLOQUEADOS: BlockedParticipant[] = [];

/** Um campo com problema e os motivos. */
export interface Problema {
  campo: string;
  motivos: string[];
}

/** O que o servidor recusou neste horário (o item dele no lote), sem o que é do evento. */
export interface ErrosDoHorario {
  /** Campo do Form do horário → mensagens. */
  campos: Record<string, string[]>;
  /** Mensagens do horário (`inicio`/`fim`). */
  horario: string[];
  /** Conflito de agenda (`availability_conflict`). */
  bloqueados: BlockedParticipant[];
}

/** O que o cartão pede ao horário. */
export interface HorarioDoEventoHandle {
  /** Confere os campos e o horário (marca o erro do horário). Devolve os problemas na ordem da tela. */
  validar: () => Promise<Problema[]>;
  /** Leva a tela e o foco ao campo. */
  focar: (campo: string) => void;
  /** Leva o foco ao campo Data (depois do "+ horário"). */
  focarData: () => void;
  /** Leva o foco ao subtítulo "Horário N" (só existe com mais de um horário). */
  focarTitulo: () => void;
  /** O projeto mudou: o Form esquece as pessoas e a resposta de avaliar. */
  limparPessoas: () => void;
}

export interface HorarioDoEventoProps {
  chaveDoEvento: number;
  numeroDoEvento: number;
  /** O evento inteiro: projeto e município valem para todos os horários. */
  dados: FormDataType;
  horario: Horario;
  /** Posição no cartão (0 = o 1º) e quantos horários o cartão tem. */
  indice: number;
  total: number;
  onChange: (chaveDoHorario: number, parcial: Partial<Horario>) => void;
  /** Quem cria (do /me): é o responsável quando o projeto aceita o vazio. */
  me: QuemCria | null;
  /** O que trava o "Criar": o id do alerta que diz o motivo, por horário (cada um é um evento). */
  onTrava: (chaveDoHorario: number, idDoMotivo: string | null) => void;
  erroDoEnvio: ErrosDoHorario | null;
  /** Do 2º horário em diante: "Remover horário". */
  onRemover?: ((chaveDoHorario: number) => void) | undefined;
  ref?: Ref<HorarioDoEventoHandle>;
}

export default function HorarioDoEvento({
  chaveDoEvento,
  numeroDoEvento,
  dados,
  horario,
  indice,
  total,
  onChange,
  me,
  onTrava,
  erroDoEnvio,
  onRemover,
  ref,
}: HorarioDoEventoProps): JSX.Element {
  const [form] = Form.useForm();
  const blocoRef = useRef<HTMLDivElement>(null);
  // Motivo de o horário não valer (faltando, ou fim antes do início), junto dos campos.
  const [erroHorario, setErroHorario] = useState<string | null>(null);

  const varios = total > 1;
  // O 1º horário fica com os ids do cartão de sempre; os outros levam também a chave do horário.
  const sufixo = indice === 0 ? `${chaveDoEvento}` : `${chaveDoEvento}-h${horario.chave}`;
  const nomeDoForm = `evento-${sufixo}`;
  const idTitulo = `evento-${chaveDoEvento}-horario-${horario.chave}-titulo`;
  const numero = indice + 1;

  const chaveDoHorario = horario.chave;
  const mudar = useCallback(
    (parcial: Partial<Horario>): void => onChange(chaveDoHorario, parcial),
    [chaveDoHorario, onChange],
  );

  // Handler para DateTimeRange: converte {date, start, end} para ISO UTC (Issue #428)
  const handleRangeChange = useCallback((range: DateTimeRangeValue): void => {
    setErroHorario(null);
    if (!range.date || !range.start || !range.end) {
      mudar({ inicio: null, fim: null });
      return;
    }
    try {
      const inicioLocal = dayjs.tz(`${range.date} ${range.start}`, RANGE_TIMEZONE);
      const fimLocal = dayjs.tz(`${range.date} ${range.end}`, RANGE_TIMEZONE);
      mudar({ inicio: inicioLocal.utc().format(), fim: fimLocal.utc().format() });
    } catch (error) {
      logger.error('Erro ao converter data/hora:', error);
      mudar({ inicio: null, fim: null });
    }
  }, [mudar]);

  // Derivar rangeValue memoizado (Issue #428)
  const rangeValue = useMemo((): DateTimeRangeValue => {
    if (!horario.inicio || !horario.fim) {
      return { date: '', start: '', end: '' };
    }
    return {
      date: dayjs(horario.inicio).tz(RANGE_TIMEZONE).format('YYYY-MM-DD'),
      start: dayjs(horario.inicio).tz(RANGE_TIMEZONE).format('HH:mm'),
      end: dayjs(horario.fim).tz(RANGE_TIMEZONE).format('HH:mm'),
    };
  }, [horario.inicio, horario.fim]);

  // ComboBox "Coordenador responsável" (#1666): papel Coordenador vigente na gerência do projeto
  // escolhido (PR 9, P9-5: num evento da gerência A só entram pessoas da A).
  const projetoId = dados.projeto?.id;
  const lookupCoordenadores = useCallback(
    (q: string): Promise<LookupItem[]> => lookupUsuarios(q, 'Coordenador', projetoId),
    [projetoId],
  );

  // DateTimeRange fica fora de Form.Item, então validateFields() não o vê. O gatilho da checagem
  // (#1452) depende dele. O backend recusa fim igual ou antes do início (`errors.fim`); aqui a
  // pessoa vê antes.
  const motivoDoHorario = (): string | null => {
    if (!horario.inicio || !horario.fim) return 'Escolha a data e os horários de início e de fim do evento.';
    if (!dayjs(horario.fim).isAfter(dayjs(horario.inicio))) return 'O horário de fim precisa ser depois do início.';
    return null;
  };

  const validar = async (): Promise<Problema[]> => {
    const motivoHorario = motivoDoHorario();
    setErroHorario(motivoHorario);
    let errorFields: Array<{ name: Array<string | number>; errors: string[] }> = [];
    try {
      await form.validateFields();
    } catch (err) {
      logger.debug('Validação falhou:', err);
      errorFields = (err as { errorFields?: typeof errorFields }).errorFields ?? [];
    }
    return [
      ...errorFields.map((f) => ({ campo: String(f.name[0]), motivos: f.errors })),
      ...(motivoHorario ? [{ campo: 'horario', motivos: [motivoHorario] }] : []),
    ].sort((a, b) => ORDEM_DO_HORARIO.indexOf(a.campo) - ORDEM_DO_HORARIO.indexOf(b.campo));
  };

  const focar = (campo: string): void => {
    // Nada de clique mudo: leva a tela e o foco ao problema.
    if (campo === 'horario') {
      setTimeout(() => blocoRef.current?.querySelector<HTMLElement>('[data-campo-horario][aria-invalid="true"]')?.focus());
      return;
    }
    form.scrollToField(campo, { block: 'center', focus: true });
    // O antd não foca um Radio.Group (o id fica no <div> do grupo): o foco vai à primeira opção.
    const elemento = document.getElementById(`${nomeDoForm}_${campo}`);
    if (elemento && !elemento.matches('input, textarea, select, button')) {
      elemento.querySelector<HTMLElement>('input[type="radio"], input[type="checkbox"]')?.focus();
    }
  };

  // Coordenador responsável: o escolhido; sem escolha, quem cria (se o backend aceita o vazio no projeto).
  const vazioEhQuemCria = dados.projeto?.responsavel_padrao === true;
  const evento = useMemo(() => eventoDoHorario(dados, horario), [dados, horario]);
  const formadoresAvaliaveis = formadoresAvaliaveisDo(evento);
  const perguntaAvaliar = perguntaAvaliarDo(evento);
  // A agenda de cada pessoa é conferida só no horário dela (decisão do dono, 03/11/2026).
  const participantes = useMemo(() => participantesDo(evento, me), [evento, me]);

  // Trocar a lista de formadores: se o escolhido para avaliação saiu, a escolha é limpa.
  const handleFormadoresChange = (value: ParticipantType[]): void => {
    const aindaAvaliavel = value.some((f) => f.avaliavel && f.id === horario.formadorAvaliado);
    mudar({ formadores: value, formadorAvaliado: aindaAvaliavel ? horario.formadorAvaliado : null });
    if (!value.some((f) => f.avaliavel && f.id === form.getFieldValue('formadorAvaliado'))) {
      form.setFieldsValue({ formadorAvaliado: undefined });
    }
  };

  // #1452: conflito recusado pelo servidor no envio (fecha o TOCTOU / cache).
  const submitConflito = erroDoEnvio && erroDoEnvio.bloqueados.length > 0 ? erroDoEnvio.bloqueados : SEM_BLOQUEADOS;

  // Os erros de campo do envio entram no Form; quando saem (a página os tira ao mexer em qualquer
  // evento), saem do campo, a menos que a validação da tela já tenha posto outro no lugar.
  const marcadosPeloEnvio = useRef<Record<string, string[]>>({});
  useEffect(() => {
    const campos = erroDoEnvio?.campos ?? {};
    const sair = Object.entries(marcadosPeloEnvio.current)
      .filter(([nome, erros]) => !(nome in campos) && JSON.stringify(form.getFieldError(nome)) === JSON.stringify(erros))
      .map(([nome]) => ({ name: nome, errors: [] }));
    const entrar = Object.entries(campos).map(([nome, erros]) => ({ name: nome, errors: erros }));
    if (sair.length + entrar.length > 0) form.setFields([...sair, ...entrar]);
    marcadosPeloEnvio.current = campos;
  }, [erroDoEnvio, form]);
  const erroDoHorario = erroHorario ?? (erroDoEnvio?.horario.length ? erroDoEnvio.horario.join(' ') : null);

  useImperativeHandle(ref, () => ({
    validar,
    focar,
    focarData: () => document.getElementById(`${nomeDoForm}-date-picker`)?.focus(),
    focarTitulo: () => document.getElementById(idTitulo)?.focus(),
    limparPessoas: () =>
      form.setFieldsValue({
        formadores: [],
        coordenadorResponsavel: null,
        pretendeAvaliar: undefined,
        formadorAvaliado: undefined,
      }),
  }));

  const preview = useAvailabilityPreview({
    inicio: horario.inicio,
    fim: horario.fim,
    municipioId: dados.municipio?.id ?? null,
    participantes,
  });

  // #1452: conflito antecipado ou recusado no envio trava o "Criar"; o botão aponta o alerta.
  const idPreviewConflito = `preview-conflito-${sufixo}`;
  const idSubmitConflito = `submit-conflito-${sufixo}`;
  const idDaTrava =
    preview.status === 'conflito' ? idPreviewConflito : submitConflito.length > 0 ? idSubmitConflito : null;
  useEffect(() => {
    onTrava(chaveDoHorario, idDaTrava);
    return () => onTrava(chaveDoHorario, null);
  }, [chaveDoHorario, idDaTrava, onTrava]);

  // Bloco de UX da checagem (aviso antecipado). Só render — o gate real é o backend.
  const renderPreviewEstado = (): ReactNode => {
    if (preview.status === 'conflito') {
      return <AvailabilityConflictAlert bloqueados={preview.bloqueados} id={idPreviewConflito} />;
    }
    if (preview.status === 'checking') {
      return (
        <Alert
          type="info"
          showIcon
          className="mb-4"
          message="Verificando disponibilidade dos participantes…"
        />
      );
    }
    if (preview.status === 'indisponivel') {
      return (
        <Alert
          type="warning"
          showIcon
          className="mb-4"
          message="Não foi possível verificar a disponibilidade agora"
          description={
            preview.motivo === 'throttled'
              ? 'Muitas verificações em sequência. Aguarde alguns segundos. Você pode continuar; o sistema recusa o evento na criação se houver conflito.'
              : 'Você pode continuar; o sistema recusa o evento na criação se houver conflito.'
          }
        />
      );
    }
    return null;
  };

  // Limite diário (RD-05): só avisa, o botão continua liberado. A região do aviso fica
  // sempre montada (vazia sem aviso) para o leitor de tela anunciar quando o texto entrar.
  const avisosDaPrevia =
    preview.status === 'ok' || preview.status === 'conflito' ? (preview.avisos ?? []) : [];

  const idPerguntaAcompanha = `pergunta-acompanha-${sufixo}`;
  const idPerguntaAvaliar = `pergunta-avaliar-${sufixo}`;

  // "Remover horário": em branco sai direto; preenchido pergunta antes, como o "Remover" do evento
  // (diálogo de verdade, aberto no Cancelar, com o foco de volta ao botão ao fechar).
  const [modal, contextoDoModal] = Modal.useModal();
  const botaoRemover = useRef<HTMLButtonElement>(null);
  const idAvisoRemocao = `remover-aviso-${sufixo}`;
  const perguntarRemocao = (remover: (chave: number) => void): void => {
    void modal.confirm({
      title: `Remover o horário ${numero} do evento ${numeroDoEvento}?`,
      content: <p id={idAvisoRemocao} className="mb-0">O que você preencheu nele será perdido.</p>,
      okText: 'Remover',
      okButtonProps: { danger: true },
      cancelText: 'Cancelar',
      cancelButtonProps: { 'aria-describedby': idAvisoRemocao },
      autoFocusButton: 'cancel',
      onOk: () => remover(chaveDoHorario),
      afterClose: () => botaoRemover.current?.focus(),
    });
  };

  return (
    <div
      ref={blocoRef}
      // Com mais de um horário, o bloco é um grupo nomeado pelo subtítulo ("Horário 2"): o leitor de
      // tela diz de qual horário é o campo. Com um só, a tela é a de sempre.
      {...(varios ? { role: 'group', 'aria-labelledby': idTitulo } : {})}
      className={varios && indice > 0 ? 'border-0 border-t border-solid border-gray-200 pt-4' : undefined}
    >
      {varios && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          {/* Abaixo do título do cartão (h3). Focável pelo código (resumo do topo, remover), fora do Tab. */}
          <Title level={4} id={idTitulo} tabIndex={-1} style={{ marginTop: 0, marginBottom: 0, fontSize: '1rem' }}>
            {`Horário ${numero}`}
          </Title>
          {onRemover && (
            <Button
              ref={botaoRemover}
              aria-label={`Remover horário ${numero} do evento ${numeroDoEvento}`}
              onClick={() => (horarioEstaEmBranco(horario) ? onRemover(chaveDoHorario) : perguntarRemocao(onRemover))}
            >
              Remover horário
            </Button>
          )}
        </div>
      )}

      <Form form={form} name={nomeDoForm} layout="vertical" component={false}>
        {/* Linha 2: Data | Início | Fim */}
        <div className="mb-6">
          <DateTimeRange
            layout="linha"
            idPrefix={`${nomeDoForm}-`}
            erro={erroDoHorario}
            value={rangeValue}
            onChange={handleRangeChange}
          />
        </div>

        {/* Linha 3: Formadores | Coordenador responsável (e se ele acompanha) */}
        <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2">
          <div className="min-w-0">
            <Form.Item
              label="Formadores"
              name="formadores"
              rules={[{ required: true, message: 'Por favor selecione pelo menos um formador' }]}
            >
              <FormadoresPicker
                value={horario.formadores}
                onChange={handleFormadoresChange}
                projetoId={projetoId}
              />
            </Form.Item>
          </div>
          <div className="min-w-0">
            <Form.Item
              label="Coordenador responsável"
              name="coordenadorResponsavel"
              extra={vazioEhQuemCria ? 'Vazio: você é o coordenador responsável.' : undefined}
              rules={vazioEhQuemCria ? [] : [{ required: true, message: 'Escolha o coordenador responsável pelo evento.' }]}
            >
              <ComboBox
                lookupFunction={lookupCoordenadores}
                onChange={(value: ComboBoxValue | null) => mudar({ coordenadorResponsavel: value })}
                value={horario.coordenadorResponsavel}
                placeholder={vazioEhQuemCria ? 'Busque o coordenador responsável (opcional)' : 'Busque o coordenador responsável'}
                oQueCarrega="os coordenadores"
              />
            </Form.Item>
            <Form.Item
              label={<span id={idPerguntaAcompanha}>O coordenador responsável vai acompanhar o evento?</span>}
              name="coordenadorAcompanha"
              rules={[{ required: true, message: 'Responda se o coordenador responsável vai acompanhar o evento.' }]}
            >
              <Radio.Group
                // role e aria-* vão ao <div> do grupo (o tipo do antd não declara role)
                {...{ role: 'radiogroup' }}
                aria-labelledby={idPerguntaAcompanha}
                name={`coordenador_acompanha_${sufixo}`}
                options={SIM_NAO}
                onChange={(e: RadioChangeEvent) => mudar({ coordenadorAcompanha: e.target.value as boolean })}
              />
            </Form.Item>
          </div>
        </div>

        {/* Avaliar o formador: obrigatória quando se aplica, então fica à vista (fora de "Mais detalhes"). */}
        {perguntaAvaliar && (
          <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2">
            <div className="min-w-0">
              <Form.Item
                label={<span id={idPerguntaAvaliar}>Você pretende avaliar o formador nesse evento?</span>}
                name="pretendeAvaliar"
                rules={[{ required: true, message: 'Responda se você pretende avaliar o formador.' }]}
              >
                <Radio.Group
                  {...{ role: 'radiogroup' }}
                  aria-labelledby={idPerguntaAvaliar}
                  name={`pretende_avaliar_formador_${sufixo}`}
                  options={SIM_NAO}
                  onChange={(e: RadioChangeEvent) => mudar({ pretendeAvaliar: e.target.value as boolean })}
                />
              </Form.Item>
            </div>
            {horario.pretendeAvaliar === true && (
              <div className="min-w-0">
                <Form.Item
                  label="Qual formador você pretende avaliar?"
                  name="formadorAvaliado"
                  rules={[{ required: true, message: 'Escolha qual formador você pretende avaliar.' }]}
                >
                  <Select
                    placeholder="Escolha um formador"
                    options={formadoresAvaliaveis.map((f) => ({ value: f.id, label: f.label || f.name || `#${f.id}` }))}
                    onChange={(value: ParticipantType['id']) => mudar({ formadorAvaliado: value })}
                  />
                </Form.Item>
              </div>
            )}
          </div>
        )}
      </Form>

      {/* #1452: aviso antecipado de conflito e o conflito recusado no envio, no próprio horário. */}
      {renderPreviewEstado()}
      {/* Sem região viva: no envio, quem anuncia é o resumo do topo. */}
      {submitConflito.length > 0 && (
        <AvailabilityConflictAlert bloqueados={submitConflito} id={idSubmitConflito} regiaoViva={false} />
      )}
      <AvisosDeAgenda avisos={avisosDaPrevia} />
      {contextoDoModal}
    </div>
  );
}
