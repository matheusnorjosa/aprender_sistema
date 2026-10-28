/**
 * CartaoEvento — um evento da Nova Solicitação, com os campos lado a lado (decisão do dono, 28/10/2026).
 *
 * Linha 1: Projeto | Tipo de Evento | Município. Linha 2: Data | Início | Fim. Linha 3: Formadores |
 * Coordenador responsável, com a pergunta "vai acompanhar?" junto dele. A pergunta de avaliar o
 * formador fica à vista quando se aplica (é obrigatória). O resto (tipo, encontro, segmento, local,
 * observações, online) fica em "Mais detalhes": recolhido, mas montado, para os limites de tamanho
 * valerem mesmo fechado. No celular os campos empilham; nenhuma linha passa da largura da tela.
 *
 * Controlado: os dados vêm da página (`dados`) e cada mudança volta por `onChange`. O Form do antd é
 * do cartão (nome `evento-<chave>`, que prefixa os ids). A página confere o cartão pelo `ref`
 * (`validar`) e devolve a ele o conflito recusado no envio (`marcarConflitoDoEnvio`).
 */

import {
  Fragment,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type JSX,
  type ReactNode,
  type Ref,
} from 'react';
import { flushSync } from 'react-dom';
// antd - direct imports for tree-shaking (Issue #424)
import Form from 'antd/es/form';
import Input from 'antd/es/input';
import Alert from 'antd/es/alert';
import Checkbox from 'antd/es/checkbox';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
import Collapse from 'antd/es/collapse';
import Radio from 'antd/es/radio';
import type { RadioChangeEvent } from 'antd/es/radio';
import Select from 'antd/es/select';
import Typography from 'antd/es/typography';
// icons - direct imports for tree-shaking (Issue #425)
import RightOutlined from '@ant-design/icons/RightOutlined';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import {
  lookupMunicipiosWithFilters,
  lookupProjetos,
  lookupTiposEvento,
  lookupUsuarios,
  type LookupItem,
} from '../../api/lookup';
import { useAvailabilityPreview } from '../../hooks/useAvailabilityPreview';
import DateTimeRange, { type DateTimeRangeValue } from '../../components/DateTimeRange';
import ComboBox from '../../components/ComboBox';
import FormadoresPicker from '../../components/FormadoresPicker';
import AvailabilityConflictAlert, { AvisosDeAgenda } from '../../components/AvailabilityConflictAlert';
import logger from '../../utils/logger';
import type { BlockedParticipant } from '../../types';
import {
  formadoresAvaliaveisDo,
  participantesDo,
  perguntaAvaliarDo,
  type ComboBoxValue,
  type FormDataType,
  type ParticipantType,
  type QuemCria,
} from './evento';

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

/** Lista vazia estável (o conflito do envio volta a ela quando deixa de valer). */
const SEM_BLOQUEADOS: BlockedParticipant[] = [];

/** Ordem dos campos na tela: a do resumo de erros e a do foco. `horario` é o DateTimeRange (fora do Form). */
const ORDEM_DA_TELA = [
  'projeto',
  'tipoEvento',
  'municipio',
  'horario',
  'formadores',
  'coordenadorResponsavel',
  'coordenadorAcompanha',
  'pretendeAvaliar',
  'formadorAvaliado',
  'tipo',
  'encontro',
  'segmento',
  'local',
  'observacoes',
  'is_online',
];

/** Campos dentro de "Mais detalhes": com erro num deles, a seção abre antes do foco. */
const CAMPOS_DOS_DETALHES = new Set(['tipo', 'encontro', 'segmento', 'local', 'observacoes', 'is_online']);

interface Problema {
  campo: string;
  motivos: string[];
}

/** O que a página pede ao cartão. */
export interface CartaoEventoHandle {
  /**
   * Confere os campos e o horário. Com `focar`, leva o foco ao primeiro problema (abrindo "Mais
   * detalhes" se ele estiver lá). Devolve os motivos na ordem da tela; vazio = pode enviar.
   */
  validar: (opcoes: { focar: boolean }) => Promise<string[]>;
  /** #1452: conflito recusado no envio; vale enquanto horário, município e participantes forem os enviados. */
  marcarConflitoDoEnvio: (bloqueados: BlockedParticipant[]) => void;
}

export interface CartaoEventoProps {
  /** Identidade estável do evento na página (ids e React key). */
  chave: number;
  /** Número visível ("Evento 1"). */
  numero: number;
  dados: FormDataType;
  onChange: (chave: number, parcial: Partial<FormDataType>) => void;
  /** Quem cria (do /me): é o responsável quando o projeto aceita o vazio. */
  me: QuemCria | null;
  /** Regra da compra: quem tem create_solicitation_without_purchase escolhe projeto e município sem compra. */
  dispensaCompra: boolean;
  /** O que trava o "Criar": o id do alerta que diz o motivo (para o `aria-describedby`), ou null. */
  onTrava: (chave: number, idDoMotivo: string | null) => void;
  ref?: Ref<CartaoEventoHandle>;
}

export default function CartaoEvento({
  chave,
  numero,
  dados,
  onChange,
  me,
  dispensaCompra,
  onTrava,
  ref,
}: CartaoEventoProps): JSX.Element {
  const [form] = Form.useForm();
  const cartaoRef = useRef<HTMLElement>(null);
  const [municipioLookupHasResults, setMunicipioLookupHasResults] = useState<boolean | null>(null);
  // #1452: conflito devolvido pelo backend no envio (fecha o TOCTOU / cache). Vale para a
  // `chave` (horário, município e participantes) com que foi enviado: mudou um deles, o
  // conflito antigo deixa de valer e o Criar volta (o backend confere de novo no envio).
  const [conflitoDoEnvio, setConflitoDoEnvio] = useState<{ chave: string; bloqueados: BlockedParticipant[] } | null>(null);
  // Motivo de o horário não valer (faltando, ou fim antes do início), junto dos campos.
  const [erroHorario, setErroHorario] = useState<string | null>(null);
  const [detalhesAbertos, setDetalhesAbertos] = useState(false);

  const mudar = useCallback((parcial: Partial<FormDataType>): void => onChange(chave, parcial), [chave, onChange]);

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
    if (!dados.inicio || !dados.fim) {
      return { date: '', start: '', end: '' };
    }
    return {
      date: dayjs(dados.inicio).tz(RANGE_TIMEZONE).format('YYYY-MM-DD'),
      start: dayjs(dados.inicio).tz(RANGE_TIMEZONE).format('HH:mm'),
      end: dayjs(dados.fim).tz(RANGE_TIMEZONE).format('HH:mm'),
    };
  }, [dados.inicio, dados.fim]);

  const handleProjetoChange = (value: ComboBoxValue | null): void => {
    const projetoChanged = dados.projeto?.id !== value?.id;
    // Trocar o projeto pode trocar a gerência (PR 9, P9-5: só entram pessoas da gerência do projeto):
    // formadores, responsável e a resposta de avaliar escolhidos para o projeto anterior saem.
    mudar({
      projeto: value,
      ...(projetoChanged
        ? { municipio: null, formadores: [], coordenadorResponsavel: null, pretendeAvaliar: null, formadorAvaliado: null }
        : {}),
    });
    if (projetoChanged) {
      form.setFieldsValue({
        municipio: null,
        formadores: [],
        coordenadorResponsavel: null,
        pretendeAvaliar: undefined,
        formadorAvaliado: undefined,
      });
      setMunicipioLookupHasResults(null);
    }
  };

  const projetoId = dados.projeto?.id;
  const lookupMunicipiosElegiveis = useCallback(async (q: string): Promise<LookupItem[]> => {
    // Para usuário comum, exige projeto para aplicar filtro município+projeto.
    if (!dispensaCompra && !projetoId) {
      setMunicipioLookupHasResults(false);
      return [];
    }
    const results = await lookupMunicipiosWithFilters({
      q,
      com_compra: dispensaCompra ? undefined : true,
      projeto_id: !dispensaCompra ? projetoId : undefined,
    });
    if (!q.trim()) {
      setMunicipioLookupHasResults(results.length > 0);
    }
    return results;
  }, [projetoId, dispensaCompra]);

  // ComboBox "Coordenador responsável" (#1666): papel Coordenador vigente na gerência do projeto
  // escolhido (PR 9, P9-5: num evento da gerência A só entram pessoas da A).
  const lookupCoordenadores = useCallback(
    (q: string): Promise<LookupItem[]> => lookupUsuarios(q, 'Coordenador', projetoId),
    [projetoId],
  );

  // Regra da compra: projeto sem compra que o libere ("em espera") some da lista.
  const lookupProjetosElegiveis = useCallback(
    (q: string): Promise<LookupItem[]> => lookupProjetos(q, dispensaCompra ? {} : { com_compra: true }),
    [dispensaCompra],
  );

  // DateTimeRange fica fora de Form.Item, então validateFields() não o vê. O gatilho da checagem
  // (#1452) depende dele. O backend recusa fim igual ou antes do início (`errors.fim`); aqui a
  // pessoa vê antes.
  const motivoDoHorario = (): string | null => {
    if (!dados.inicio || !dados.fim) return 'Escolha a data e os horários de início e de fim do evento.';
    if (!dayjs(dados.fim).isAfter(dayjs(dados.inicio))) return 'O horário de fim precisa ser depois do início.';
    return null;
  };

  const validar = async ({ focar }: { focar: boolean }): Promise<string[]> => {
    const motivoHorario = motivoDoHorario();
    setErroHorario(motivoHorario);
    let errorFields: Array<{ name: Array<string | number>; errors: string[] }> = [];
    try {
      await form.validateFields();
    } catch (err) {
      logger.debug('Validação falhou:', err);
      errorFields = (err as { errorFields?: typeof errorFields }).errorFields ?? [];
    }
    const problemas: Problema[] = [
      ...errorFields.map((f) => ({ campo: String(f.name[0]), motivos: f.errors })),
      ...(motivoHorario ? [{ campo: 'horario', motivos: [motivoHorario] }] : []),
    ].sort((a, b) => ORDEM_DA_TELA.indexOf(a.campo) - ORDEM_DA_TELA.indexOf(b.campo));

    const primeiro = problemas[0];
    if (focar && primeiro) {
      // Nada de clique mudo: leva a tela e o foco ao primeiro problema.
      if (primeiro.campo === 'horario') {
        setTimeout(() => cartaoRef.current?.querySelector<HTMLElement>('[data-campo-horario][aria-invalid="true"]')?.focus());
      } else {
        // Campo escondido não recebe foco: abre "Mais detalhes" antes de focar.
        if (CAMPOS_DOS_DETALHES.has(primeiro.campo)) flushSync(() => setDetalhesAbertos(true));
        form.scrollToField(primeiro.campo, { block: 'center', focus: true });
        // O antd não foca um Radio.Group (o id fica no <div> do grupo): o foco vai à primeira
        // opção da pergunta Sim/Não (ou à caixa de marcar) que faltou.
        const campo = document.getElementById(`evento-${chave}_${primeiro.campo}`);
        if (campo && !campo.matches('input, textarea, select, button')) {
          campo.querySelector<HTMLElement>('input[type="radio"], input[type="checkbox"]')?.focus();
        }
      }
    }
    return problemas.flatMap((p) => p.motivos);
  };

  // Coordenador responsável: o escolhido; sem escolha, quem cria (se o backend aceita o vazio no projeto).
  const vazioEhQuemCria = dados.projeto?.responsavel_padrao === true;
  const formadoresAvaliaveis = formadoresAvaliaveisDo(dados);
  const perguntaAvaliar = perguntaAvaliarDo(dados);
  const participantes = useMemo(() => participantesDo(dados, me), [dados, me]);

  // Trocar a lista de formadores: se o escolhido para avaliação saiu, a escolha é limpa.
  const handleFormadoresChange = (value: ParticipantType[]): void => {
    const aindaAvaliavel = value.some((f) => f.avaliavel && f.id === dados.formadorAvaliado);
    mudar({ formadores: value, formadorAvaliado: aindaAvaliavel ? dados.formadorAvaliado : null });
    if (!value.some((f) => f.avaliavel && f.id === form.getFieldValue('formadorAvaliado'))) {
      form.setFieldsValue({ formadorAvaliado: undefined });
    }
  };

  // O que o conflito do envio confere: se mudar, ele já não descreve o evento da tela.
  const chaveDoEnvio = [
    dados.inicio,
    dados.fim,
    dados.municipio?.id,
    participantes.map((p) => p.id).sort((a, b) => Number(a) - Number(b)).join(','),
  ].join('|');
  const submitConflito = conflitoDoEnvio?.chave === chaveDoEnvio ? conflitoDoEnvio.bloqueados : SEM_BLOQUEADOS;

  useImperativeHandle(ref, () => ({
    validar,
    marcarConflitoDoEnvio: (bloqueados) => setConflitoDoEnvio({ chave: chaveDoEnvio, bloqueados }),
  }));

  const preview = useAvailabilityPreview({
    inicio: dados.inicio,
    fim: dados.fim,
    municipioId: dados.municipio?.id ?? null,
    participantes,
  });

  // #1452: conflito antecipado ou recusado no envio trava o "Criar"; o botão aponta o alerta.
  const idPreviewConflito = `preview-conflito-${chave}`;
  const idSubmitConflito = `submit-conflito-${chave}`;
  const idDaTrava =
    preview.status === 'conflito' ? idPreviewConflito : submitConflito.length > 0 ? idSubmitConflito : null;
  useEffect(() => {
    onTrava(chave, idDaTrava);
    return () => onTrava(chave, null);
  }, [chave, idDaTrava, onTrava]);

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

  // Situação do evento, em texto fixo (sem região viva por cartão): o fluxo de aprovação e a compra.
  const situacao: string[] = [
    ...(dados.projeto?.fluxo === 'SUPER' ? ['Vai para aprovação'] : []),
    ...(dados.projeto?.fluxo === 'NAO_SUPER' ? ['Aprovado na hora'] : []),
    ...(!dispensaCompra && dados.projeto && municipioLookupHasResults === false
      ? ['Sem municípios com compra para este projeto']
      : []),
    ...(dispensaCompra ? ['Compra dispensada'] : []),
  ];

  const idTitulo = `evento-${chave}-titulo`;
  const idPerguntaAcompanha = `pergunta-acompanha-${chave}`;
  const idPerguntaAvaliar = `pergunta-avaliar-${chave}`;

  return (
    <section ref={cartaoRef} aria-labelledby={idTitulo} className="mt-6 rounded-lg border border-solid border-gray-200 p-4">
      {/* Menor que o título da página (h2) em qualquer largura. */}
      <Title level={3} id={idTitulo} style={{ marginTop: 0, fontSize: '1.125rem' }}>
        Evento {numero}
      </Title>

      <Form form={form} name={`evento-${chave}`} layout="vertical" autoComplete="off">
        {/* Linha 1: Projeto | Tipo de Evento | Município */}
        <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
          <div className="min-w-0">
            <Form.Item
              label="Projeto"
              name="projeto"
              rules={[{ required: true, message: 'Por favor selecione um projeto' }]}
              extra={dispensaCompra ? undefined : 'Projetos sem compra não aparecem.'}
            >
              <ComboBox
                lookupFunction={lookupProjetosElegiveis}
                onChange={handleProjetoChange}
                value={dados.projeto}
                placeholder="Busque ou selecione um projeto"
                oQueCarrega="os projetos"
              />
            </Form.Item>
          </div>
          <div className="min-w-0">
            <Form.Item
              label="Tipo de Evento"
              name="tipoEvento"
              rules={[{ required: true, message: 'Por favor selecione um tipo de evento' }]}
            >
              <ComboBox
                lookupFunction={lookupTiposEvento}
                onChange={(value: ComboBoxValue | null) => mudar({ tipoEvento: value })}
                value={dados.tipoEvento}
                placeholder="Busque ou selecione um tipo de evento"
                oQueCarrega="os tipos de evento"
              />
            </Form.Item>
          </div>
          <div className="min-w-0">
            <Form.Item
              label="Município"
              name="municipio"
              rules={[{ required: true, message: 'Por favor selecione um município' }]}
            >
              <ComboBox
                lookupFunction={lookupMunicipiosElegiveis}
                onChange={(value: ComboBoxValue | null) => mudar({ municipio: value })}
                value={dados.municipio}
                placeholder={
                  !dispensaCompra && !dados.projeto
                    ? 'Selecione um projeto para carregar municípios elegíveis'
                    : 'Busque ou selecione um município'
                }
                disabled={!dispensaCompra && !dados.projeto}
                oQueCarrega="os municípios"
                notFoundContent={
                  !dispensaCompra && dados.projeto
                    ? 'Nenhum município elegível para o projeto selecionado'
                    : 'Nenhum resultado encontrado'
                }
              />
            </Form.Item>
          </div>
        </div>

        {/* Linha 2: Data | Início | Fim */}
        <div className="mb-6">
          <DateTimeRange
            layout="linha"
            idPrefix={`evento-${chave}-`}
            erro={erroHorario}
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
              extra="Coordenador que vai atuar no evento entra na lista de formadores."
              rules={[{ required: true, message: 'Por favor selecione pelo menos um formador' }]}
            >
              <FormadoresPicker
                value={dados.formadores}
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
                value={dados.coordenadorResponsavel}
                placeholder={vazioEhQuemCria ? 'Busque o coordenador responsável (opcional)' : 'Busque o coordenador responsável'}
                oQueCarrega="os coordenadores"
              />
            </Form.Item>
            <Form.Item
              label={<span id={idPerguntaAcompanha}>O coordenador responsável vai acompanhar o evento?</span>}
              name="coordenadorAcompanha"
              extra="Se Sim, a agenda do coordenador responsável é conferida como a dos formadores."
              rules={[{ required: true, message: 'Responda se o coordenador responsável vai acompanhar o evento.' }]}
            >
              <Radio.Group
                // role e aria-* vão ao <div> do grupo (o tipo do antd não declara role)
                {...{ role: 'radiogroup' }}
                aria-labelledby={idPerguntaAcompanha}
                name={`coordenador_acompanha_${chave}`}
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
                  name={`pretende_avaliar_formador_${chave}`}
                  options={SIM_NAO}
                  onChange={(e: RadioChangeEvent) => mudar({ pretendeAvaliar: e.target.value as boolean })}
                />
              </Form.Item>
            </div>
            {dados.pretendeAvaliar === true && (
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

        <Collapse
          className="mb-4"
          activeKey={detalhesAbertos ? ['detalhes'] : []}
          onChange={(chaves: string | string[]) =>
            setDetalhesAbertos((Array.isArray(chaves) ? chaves : [chaves]).includes('detalhes'))
          }
          expandIcon={({ isActive }) => <RightOutlined aria-hidden rotate={isActive ? 90 : 0} />}
          items={[
            {
              key: 'detalhes',
              label: 'Mais detalhes (opcional)',
              // Montado mesmo recolhido: os limites de tamanho valem com a seção fechada.
              forceRender: true,
              children: (
                <>
                  <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
                    <div className="min-w-0">
                      <Form.Item label="Tipo" name="tipo" rules={[{ max: 50, message: 'Máximo 50 caracteres' }]}>
                        <Input
                          placeholder="Ex: evento, reunião"
                          value={dados.tipo}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => mudar({ tipo: e.target.value })}
                        />
                      </Form.Item>
                    </div>
                    <div className="min-w-0">
                      <Form.Item label="Encontro" name="encontro" rules={[{ max: 100, message: 'Máximo 100 caracteres' }]}>
                        <Input
                          placeholder="Ex: Encontro 1"
                          value={dados.encontro}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => mudar({ encontro: e.target.value })}
                        />
                      </Form.Item>
                    </div>
                    <div className="min-w-0">
                      <Form.Item label="Segmento" name="segmento" rules={[{ max: 100, message: 'Máximo 100 caracteres' }]}>
                        <Input
                          placeholder="Ex: Fundamental I, Fundamental II"
                          value={dados.segmento}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => mudar({ segmento: e.target.value })}
                        />
                      </Form.Item>
                    </div>
                  </div>

                  <Form.Item label="Local do Evento" name="local" rules={[{ max: 300, message: 'Máximo 300 caracteres' }]}>
                    <Input
                      placeholder="Ex: Escola Municipal X, Sala 5 / Secretaria de Educação"
                      value={dados.local}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => mudar({ local: e.target.value })}
                    />
                  </Form.Item>

                  <Form.Item label="Observações" name="observacoes" rules={[{ max: 5000, message: 'Máximo 5000 caracteres' }]}>
                    <TextArea
                      rows={4}
                      placeholder="Observações adicionais sobre o evento"
                      value={dados.observacoes}
                      onChange={(e: ChangeEvent<HTMLTextAreaElement>) => mudar({ observacoes: e.target.value })}
                    />
                  </Form.Item>

                  {/* PR19: Modalidade online/presencial. A explicação é texto fixo, não alerta. */}
                  <Form.Item
                    name="is_online"
                    valuePropName="checked"
                    extra={
                      dados.is_online
                        ? 'Link do Google Meet será gerado automaticamente após publicação do evento no calendário.'
                        : 'Evento presencial: nenhum link de reunião será gerado.'
                    }
                  >
                    <Checkbox
                      checked={dados.is_online}
                      onChange={(e: CheckboxChangeEvent) => mudar({ is_online: e.target.checked })}
                    >
                      Evento online (Google Meet)
                    </Checkbox>
                  </Form.Item>
                </>
              ),
            },
          ]}
        />
      </Form>

      {/* #1452: aviso antecipado de conflito e o conflito recusado no envio, no próprio cartão. */}
      {renderPreviewEstado()}
      {submitConflito.length > 0 && <AvailabilityConflictAlert bloqueados={submitConflito} id={idSubmitConflito} />}
      <AvisosDeAgenda avisos={avisosDaPrevia} />

      {situacao.length > 0 && (
        <p className="mb-0">
          <Text strong>Situação: </Text>
          {situacao.map((texto, i) => (
            <Fragment key={texto}>
              {i > 0 && ' · '}
              <span>{texto}</span>
            </Fragment>
          ))}
        </p>
      )}
    </section>
  );
}
