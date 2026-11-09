/**
 * CartaoEvento — um evento da Nova Solicitação, com os campos lado a lado (decisão do dono, 28/10/2026).
 *
 * Linha 1: Projeto | Tipo de Evento | Nº da formação | Município. Depois, os horários
 * (`HorarioDoEvento`: Data | Início | Fim; Formadores | Coordenador(es), com "vai
 * acompanhar?"; a pergunta de avaliar o formador) e "+ horário" (decisão do dono, 03/11/2026: cada
 * horário vira um evento separado no Google; o que fica fora dos horários se preenche uma vez). O
 * resto (tipo, segmento, local, observações, online) fica em "Mais detalhes": recolhido, mas montado,
 * para os limites de tamanho valerem mesmo fechado. No celular os campos empilham; nenhuma linha passa
 * da largura da tela.
 *
 * Controlado: os dados vêm da página (`dados`) e cada mudança volta por `onChange` (o que é do
 * evento) ou `onChangeHorario`. O Form do antd do cartão (nome `evento-<chave>`, que prefixa os ids)
 * tem os campos do evento; cada horário tem o seu. A página confere o cartão pelo `ref` (`validar`,
 * `focarTitulo`, `focarData`) e devolve a ele o que o servidor recusou no envio do lote, por horário
 * (`errosDoLote`): erro de campo vai ao campo (do evento ou do horário), conflito de agenda ao alerta
 * do horário e o resto ao topo do cartão. A página tira esse erro quando qualquer evento muda, menos o
 * conflito de agenda, que sai quando muda o horário, o município ou quem participa de algum evento.
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
import Button from 'antd/es/button';
import Form from 'antd/es/form';
import Input from 'antd/es/input';
import Alert from 'antd/es/alert';
import Checkbox from 'antd/es/checkbox';
import type { CheckboxChangeEvent } from 'antd/es/checkbox';
import Collapse from 'antd/es/collapse';
import Modal from 'antd/es/modal';
import Typography from 'antd/es/typography';
// icons - direct imports for tree-shaking (Issue #425)
import ExclamationCircleOutlined from '@ant-design/icons/ExclamationCircleOutlined';
import PlusOutlined from '@ant-design/icons/PlusOutlined';
import RightOutlined from '@ant-design/icons/RightOutlined';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import {
  lookupMunicipiosWithFilters,
  lookupProjetos,
  lookupTiposEvento,
  type LookupItem,
} from '../../api/lookup';
import ComboBox from '../../components/ComboBox';
import logger from '../../utils/logger';
import type { ErroDoEventoNoLote } from '../../api/solicitacoes';
import HorarioDoEvento, { type ErrosDoHorario, type HorarioDoEventoHandle, type Problema } from './HorarioDoEvento';
import {
  AVISO_SEM_COMPRA,
  estaEmBranco,
  eventoDoHorario,
  opcaoDoMunicipio,
  ORDEM_DO_CARTAO,
  ORDEM_DO_HORARIO,
  perguntaAvaliarDo,
  separarErrosDoServidor,
  TEXTO_DO_LIMITE,
  type ComboBoxValue,
  type FormDataType,
  type Horario,
  type QuemCria,
} from './evento';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault('America/Fortaleza');

const { TextArea } = Input;
const { Title, Text } = Typography;

/** Ordem dos campos do evento na tela (a do resumo e a do foco). */
const ORDEM_DA_TELA = ORDEM_DO_CARTAO;

/** Campos dentro de "Mais detalhes": com erro num deles, a seção abre antes do foco. */
const CAMPOS_DOS_DETALHES = new Set(['tipo', 'segmento', 'local', 'observacoes', 'is_online']);

/** Um motivo de o evento não poder ser criado: de um horário (a chave dele) ou do evento (null). */
export interface MotivoDoCartao {
  horario: number | null;
  texto: string;
}

/** O que o servidor recusou no cartão: o que é do evento (campos e topo) e o que é de cada horário. */
interface ErrosDoCartao {
  campos: Record<string, string[]>;
  topo: string[];
  porHorario: Record<number, ErrosDoHorario>;
}

/** O que a página pede ao cartão. */
export interface CartaoEventoHandle {
  /**
   * Confere os campos do evento e os de cada horário. Com `focar`, leva o foco ao primeiro problema
   * (abrindo "Mais detalhes" se ele estiver lá). Devolve os motivos na ordem da tela; vazio = pode enviar.
   */
  validar: (opcoes: { focar: boolean }) => Promise<MotivoDoCartao[]>;
  /**
   * Leva o foco ao título do cartão ("Evento N") ou, com `horario` e mais de um horário no cartão, ao
   * subtítulo dele ("Horário 2").
   */
  focarTitulo: (horario?: number | null) => void;
  /** Leva o foco ao campo Data do horário (depois do "+ horário"). */
  focarData: (horario: number) => void;
}

export interface CartaoEventoProps {
  /** Identidade estável do evento na página (ids e React key). */
  chave: number;
  /** Número visível ("Evento 1"). */
  numero: number;
  dados: FormDataType;
  onChange: (chave: number, parcial: Partial<FormDataType>) => void;
  onChangeHorario: (chave: number, chaveDoHorario: number, parcial: Partial<Horario>) => void;
  /** "+ horário" e "Remover horário": a página guarda as chaves e o limite de eventos por envio. */
  onAdicionarHorario: (chave: number) => void;
  onRemoverHorario: (chave: number, chaveDoHorario: number) => void;
  /** O envio chegou ao limite de eventos (cada horário conta um): "+ horário" desabilita e diz o porquê. */
  noLimite: boolean;
  /** Quem cria (do /me): é o responsável quando o projeto aceita o vazio. */
  me: QuemCria | null;
  /** Regra da compra: quem tem create_solicitation_without_purchase escolhe projeto e município sem compra. */
  dispensaCompra: boolean;
  /** O que trava o "Criar", por horário: o id do alerta que diz o motivo (para o `aria-describedby`), ou null. */
  onTrava: (chaveDoHorario: number, idDoMotivo: string | null) => void;
  /** O que o servidor recusou no último envio do lote, por chave do horário (null: nada). */
  errosDoLote: Record<number, ErroDoEventoNoLote> | null;
  /** O evento está no resumo de problemas do topo: o cartão fica vermelho e o título diz "com problema". */
  comProblema: boolean;
  /** Evento extra: "Remover". O primeiro evento não tem. */
  onRemover?: ((chave: number) => void) | undefined;
  ref?: Ref<CartaoEventoHandle>;
}

export default function CartaoEvento({
  chave,
  numero,
  dados,
  onChange,
  onChangeHorario,
  onAdicionarHorario,
  onRemoverHorario,
  noLimite,
  me,
  dispensaCompra,
  onTrava,
  errosDoLote,
  comProblema,
  onRemover,
  ref,
}: CartaoEventoProps): JSX.Element {
  const [form] = Form.useForm();
  const [municipioLookupHasResults, setMunicipioLookupHasResults] = useState<boolean | null>(null);
  const [detalhesAbertos, setDetalhesAbertos] = useState(false);
  const horarios = useRef(new Map<number, HorarioDoEventoHandle>());

  const mudar = useCallback((parcial: Partial<FormDataType>): void => onChange(chave, parcial), [chave, onChange]);
  const mudarHorario = useCallback(
    (chaveDoHorario: number, parcial: Partial<Horario>): void => onChangeHorario(chave, chaveDoHorario, parcial),
    [chave, onChangeHorario],
  );
  const removerHorario = useCallback(
    (chaveDoHorario: number): void => onRemoverHorario(chave, chaveDoHorario),
    [chave, onRemoverHorario],
  );

  // A marca "sem compra" do município escolhido é dos projetos de antes: com os projetos novos, reconfere
  // só esse município. A resposta só vale se ninguém mexeu em projeto ou município no meio.
  const reconferencia = useRef(0);
  const reconferirMunicipio = (projeto: ComboBoxValue, projeto2: ComboBoxValue | null): void => {
    const vez = ++reconferencia.current;
    const municipio = dados.municipio;
    if (dispensaCompra || !municipio) return;
    lookupMunicipiosWithFilters({
      q: '',
      marcar_sem_compra: true,
      projeto_id: projeto.id,
      ...(projeto2 ? { projeto_2_id: projeto2.id } : {}),
      municipio_id: municipio.id,
    })
      .then(([item]) => {
        if (vez === reconferencia.current) mudar({ municipio: { ...municipio, sem_compra: item?.['sem_compra'] === true } });
      })
      .catch((err: unknown) => logger.warn('Não foi possível reconferir a compra do município:', err));
  };

  const handleProjetoChange = (value: ComboBoxValue | null): void => {
    reconferencia.current += 1;
    // Combo (#2036): tirar o 1º sobe o 2º. É da mesma gerência, então pessoas e município ficam.
    if (!value && dados.projeto_2) {
      const sobe = dados.projeto_2;
      mudar({ projeto: sobe, projeto_2: null });
      form.setFieldsValue({ projeto: sobe, projeto_2: null });
      reconferirMunicipio(sobe, null);
      return;
    }
    const projetoChanged = dados.projeto?.id !== value?.id;
    // Trocar o projeto pode trocar a gerência (PR 9, P9-5: só entram pessoas da gerência do projeto):
    // formadores, coordenadores e a resposta de avaliar escolhidos para o projeto anterior saem, em
    // todos os horários.
    mudar({
      projeto: value,
      ...(projetoChanged
        ? {
            // O 2º só vale com o 1º que o escolheu (mesma gerência e mesmo fluxo).
            projeto_2: null,
            municipio: null,
            horarios: dados.horarios.map((h) => ({
              ...h,
              formadores: [],
              coordenadores: [],
              // A caixa ficou vazia: a resposta era do responsável que saiu.
              coordenadorAcompanha: null,
              pretendeAvaliar: null,
              formadorAvaliado: null,
            })),
          }
        : {}),
    });
    if (projetoChanged) {
      form.setFieldsValue({ municipio: null, projeto_2: null });
      horarios.current.forEach((h) => h.limparPessoas());
      setMunicipioLookupHasResults(null);
    }
  };

  const handleProjeto2Change = (value: ComboBoxValue | null): void => {
    mudar({ projeto_2: value });
    if (dados.projeto) reconferirMunicipio(dados.projeto, value);
  };

  const projetoId = dados.projeto?.id;
  const projeto2Id = dados.projeto_2?.id;
  const lookupMunicipiosElegiveis = useCallback(async (q: string): Promise<LookupItem[]> => {
    // Para usuário comum, exige projeto: a lista marca os municípios sem compra para ele.
    if (!dispensaCompra && !projetoId) {
      setMunicipioLookupHasResults(false);
      return [];
    }
    // Pedido do dono (03/11/2026): o município sem compra também vem (com compra primeiro), marcado.
    const results = await lookupMunicipiosWithFilters(
      dispensaCompra
        ? { q }
        : { q, marcar_sem_compra: true, projeto_id: projetoId, ...(projeto2Id ? { projeto_2_id: projeto2Id } : {}) },
    );
    if (!q.trim()) {
      // Com compra primeiro: se nenhum da lista sem busca tem compra, nenhum tem.
      setMunicipioLookupHasResults(results.some((r) => r['sem_compra'] !== true));
    }
    return results;
  }, [projetoId, projeto2Id, dispensaCompra]);
  const semCompra = !dispensaCompra && dados.municipio?.sem_compra === true;

  // Regra da compra: projeto sem compra que o libere ("em espera") some da lista.
  const lookupProjetosElegiveis = useCallback(
    (q: string): Promise<LookupItem[]> => lookupProjetos(q, dispensaCompra ? {} : { com_compra: true }),
    [dispensaCompra],
  );
  // Combo: o 2º só pode ser da mesma gerência e do mesmo fluxo do 1º (o servidor filtra).
  const lookupProjetosCompativeis = useCallback(
    (q: string): Promise<LookupItem[]> =>
      lookupProjetos(q, dispensaCompra ? { mesmo_grupo_de: projetoId } : { com_compra: true, mesmo_grupo_de: projetoId }),
    [dispensaCompra, projetoId],
  );

  // Confere o evento e os horários; a ordem é a da tela (os campos do evento antes e depois dos horários).
  const validar = async ({ focar }: { focar: boolean }): Promise<MotivoDoCartao[]> => {
    let errorFields: Array<{ name: Array<string | number>; errors: string[] }> = [];
    try {
      await form.validateFields();
    } catch (err) {
      logger.debug('Validação falhou:', err);
      errorFields = (err as { errorFields?: typeof errorFields }).errorFields ?? [];
    }
    const lugar = (p: Problema): number => ORDEM_DA_TELA.indexOf(p.campo);
    const doEvento: Problema[] = errorFields
      .map((f) => ({ campo: String(f.name[0]), motivos: f.errors }))
      .sort((a, b) => lugar(a) - lugar(b));
    const dosHorarios = await Promise.all(
      dados.horarios.map(async (h) => ({ chave: h.chave, problemas: (await horarios.current.get(h.chave)?.validar()) ?? [] })),
    );
    const meio = ORDEM_DA_TELA.indexOf('horarios');
    const problemas: Array<{ horario: number | null; problema: Problema }> = [
      ...doEvento.filter((p) => lugar(p) < meio).map((problema) => ({ horario: null, problema })),
      ...dosHorarios.flatMap(({ chave: horario, problemas: lista }) => lista.map((problema) => ({ horario, problema }))),
      ...doEvento.filter((p) => lugar(p) > meio).map((problema) => ({ horario: null, problema })),
    ];

    const primeiro = problemas[0];
    if (focar && primeiro) {
      // Nada de clique mudo: leva a tela e o foco ao primeiro problema.
      const { campo } = primeiro.problema;
      if (primeiro.horario !== null) {
        horarios.current.get(primeiro.horario)?.focar(campo);
      } else {
        // Campo escondido não recebe foco: abre "Mais detalhes" antes de focar.
        if (CAMPOS_DOS_DETALHES.has(campo)) flushSync(() => setDetalhesAbertos(true));
        form.scrollToField(campo, { block: 'center', focus: true });
        // O antd não foca a caixa de marcar pelo id do Form.Item: o foco vai a ela.
        const elemento = document.getElementById(`evento-${chave}_${campo}`);
        if (elemento && !elemento.matches('input, textarea, select, button')) {
          elemento.querySelector<HTMLElement>('input[type="radio"], input[type="checkbox"]')?.focus();
        }
      }
    }
    return problemas.flatMap(({ horario, problema }) => problema.motivos.map((texto) => ({ horario, texto })));
  };

  // O que o servidor recusou, por horário (cada horário é um item do lote): o que é do horário vai ao
  // horário; o que é do evento, ao campo do cartão; o que não é de um campo à vista, ao topo do cartão
  // (com "Horário N:" quando há mais de um). Sem nada por campo, o `detail` do item vai ao topo.
  const errosDoEnvio = useMemo((): ErrosDoCartao => {
    const separados: ErrosDoCartao = { campos: {}, topo: [], porHorario: {} };
    dados.horarios.forEach((horario, indice) => {
      const item = errosDoLote?.[horario.chave];
      if (!item) return;
      // #1452: conflito recusado pelo servidor no envio (fecha o TOCTOU / cache). No lote,
      // `blocked_participants` vem no topo do item (formato do batch-approve).
      const bloqueados = item.code === 'availability_conflict' ? (item.blocked_participants ?? []) : [];
      if (bloqueados.length > 0) {
        separados.porHorario[horario.chave] = { campos: {}, horario: [], bloqueados };
        return;
      }
      const perguntaAvaliar = perguntaAvaliarDo(eventoDoHorario(dados, horario));
      const campoNaTela = (campo: string): boolean => {
        if (campo === 'pretendeAvaliar') return perguntaAvaliar;
        if (campo === 'formadorAvaliado') return perguntaAvaliar && horario.pretendeAvaliar === true;
        return (campo !== 'horarios' && ORDEM_DA_TELA.includes(campo)) || (campo !== 'horario' && ORDEM_DO_HORARIO.includes(campo));
      };
      const doItem = separarErrosDoServidor(item.errors ?? {}, campoNaTela);
      if (doItem.topo.length + doItem.horario.length + Object.keys(doItem.campos).length === 0) doItem.topo.push(item.detail);
      const prefixo = dados.horarios.length > 1 ? `Horário ${indice + 1}: ` : '';
      separados.topo.push(...doItem.topo.map((texto) => `${prefixo}${texto}`).filter((t) => !separados.topo.includes(t)));
      const doHorario: Record<string, string[]> = {};
      for (const [campo, mensagens] of Object.entries(doItem.campos)) {
        if (ORDEM_DO_HORARIO.includes(campo)) doHorario[campo] = mensagens;
        else separados.campos[campo] = [...new Set([...(separados.campos[campo] ?? []), ...mensagens])];
      }
      separados.porHorario[horario.chave] = { campos: doHorario, horario: doItem.horario, bloqueados: [] };
    });
    return separados;
  }, [errosDoLote, dados]);

  // Os erros de campo do envio entram no Form; quando saem (a página os tira ao mexer em qualquer
  // evento), saem do campo, a menos que a validação da tela já tenha posto outro no lugar.
  const marcadosPeloEnvio = useRef<Record<string, string[]>>({});
  useEffect(() => {
    const campos = errosDoEnvio.campos;
    const sair = Object.entries(marcadosPeloEnvio.current)
      .filter(([nome, erros]) => !(nome in campos) && JSON.stringify(form.getFieldError(nome)) === JSON.stringify(erros))
      .map(([nome]) => ({ name: nome, errors: [] }));
    const entrar = Object.entries(campos).map(([nome, erros]) => ({ name: nome, errors: erros }));
    if (sair.length + entrar.length > 0) form.setFields([...sair, ...entrar]);
    marcadosPeloEnvio.current = campos;
  }, [errosDoEnvio, form]);

  const idTitulo = `evento-${chave}-titulo`;
  const variosHorarios = dados.horarios.length > 1;
  useImperativeHandle(ref, () => ({
    validar,
    focarTitulo: (horario?: number | null) => {
      if (horario != null && variosHorarios && horarios.current.has(horario)) horarios.current.get(horario)?.focarTitulo();
      else document.getElementById(idTitulo)?.focus();
    },
    focarData: (horario: number) => horarios.current.get(horario)?.focarData(),
  }));

  // Situação do evento, em texto fixo (sem região viva por cartão): o fluxo de aprovação e a compra.
  // Sem compra no município, vai para aprovação em qualquer fluxo (pedido do dono, 03/11/2026).
  const situacao: string[] = [
    ...(dados.projeto?.fluxo === 'SUPER' || semCompra ? ['Vai para aprovação'] : []),
    ...(dados.projeto?.fluxo === 'NAO_SUPER' && !semCompra ? ['Aprovado na hora'] : []),
    ...(!dispensaCompra && dados.projeto && municipioLookupHasResults === false
      ? ['Sem municípios com compra para este projeto']
      : []),
  ];

  // "Remover": evento em branco sai direto; preenchido pergunta antes num diálogo de verdade
  // (role=dialog, foco preso, Esc em qualquer ponto e o foco de volta ao "Remover" ao fechar), que
  // abre no Cancelar. O balão do Popconfirm (role=tooltip) deixava o Tab sair com ele aberto.
  const [modal, contextoDoModal] = Modal.useModal();
  const botaoRemover = useRef<HTMLButtonElement>(null);
  const idAvisoRemocao = `remover-aviso-${chave}`;
  const perguntarRemocao = (remover: (chave: number) => void): void => {
    void modal.confirm({
      title: `Remover o evento ${numero}?`,
      content: <p id={idAvisoRemocao} className="mb-0">O que você preencheu nele será perdido.</p>,
      okText: 'Remover',
      okButtonProps: { danger: true },
      cancelText: 'Cancelar',
      // O foco começa no Cancelar: o leitor de tela lê com ele o que se perde.
      cancelButtonProps: { 'aria-describedby': idAvisoRemocao },
      autoFocusButton: 'cancel',
      onOk: () => remover(chave),
      // O antd devolve o foco a quem o tinha ao abrir, que nem sempre é o botão (o clique do mouse
      // não foca botão em todo navegador). Removido o evento, o botão sai e a página foca o anterior.
      afterClose: () => botaoRemover.current?.focus(),
    });
  };
  const renderRemover = (): ReactNode => {
    if (!onRemover) return null;
    return (
      <Button
        ref={botaoRemover}
        aria-label={`Remover evento ${numero}`}
        onClick={() => (estaEmBranco(dados) ? onRemover(chave) : perguntarRemocao(onRemover))}
      >
        Remover
      </Button>
    );
  };

  return (
    <section
      aria-labelledby={idTitulo}
      className={`mt-6 rounded-lg border-solid p-4 ${comProblema ? 'border-2 border-red-600' : 'border border-gray-200'}`}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          {/* O ícone fica fora do título: o nome do cartão é "Evento N com problema", sem o nome do ícone. */}
          {comProblema && <ExclamationCircleOutlined aria-hidden className="text-red-700" />}
          {/* Menor que o título da página (h2) em qualquer largura. Focável pelo código (adicionar,
              remover, linha do resumo), fora do Tab. "com problema" escrito: a cor não é o único sinal. */}
          <Title level={3} id={idTitulo} tabIndex={-1} style={{ marginTop: 0, marginBottom: 0, fontSize: '1.125rem' }}>
            {comProblema ? `Evento ${numero} ` : `Evento ${numero}`}
            {comProblema && <span className="text-base font-normal text-red-700">com problema</span>}
          </Title>
        </div>
        {renderRemover()}
      </div>

      {/* O que o servidor recusou e não é de um campo à vista. Sem região viva: quem anuncia é o resumo do topo. */}
      {errosDoEnvio.topo.length > 0 && (
        <Alert
          type="error"
          showIcon
          role="none"
          className="mb-4"
          message="Este evento não pode ser criado assim"
          description={
            <ul className="mb-0 pl-5">
              {errosDoEnvio.topo.map((texto) => (
                <li key={texto}>{texto}</li>
              ))}
            </ul>
          }
        />
      )}

      <Form form={form} name={`evento-${chave}`} layout="vertical" autoComplete="off">
        {/* Linha 1: Projeto | Tipo de Evento | Nº da formação | Município */}
        <div className="grid grid-cols-1 gap-x-4 md:grid-cols-2 xl:grid-cols-4">
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
            {/* Combo (#2036, decisões do dono de 07/11/2026): os dois projetos juntos, sem principal. */}
            {dados.projeto && (
              <Form.Item
                label="2º projeto (combo)"
                name="projeto_2"
                extra="Só quando os dois projetos acontecem juntos. Aparecem os da mesma gerência e do mesmo fluxo."
              >
                <ComboBox
                  lookupFunction={lookupProjetosCompativeis}
                  onChange={handleProjeto2Change}
                  value={dados.projeto_2}
                  placeholder="Opcional: o outro projeto do combo"
                  oQueCarrega="os projetos"
                />
              </Form.Item>
            )}
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
            {/* O número da formação vai para o título do evento no Google ("4º EF", "2º Acompanhamento"). */}
            <Form.Item label="Nº da formação" name="encontro" rules={[{ max: 100, message: 'Máximo 100 caracteres' }]}>
              <Input
                placeholder="Ex: 4"
                value={dados.encontro}
                onChange={(e: ChangeEvent<HTMLInputElement>) => mudar({ encontro: e.target.value })}
              />
            </Form.Item>
          </div>
          <div className="min-w-0">
            {/* O aviso vai no `extra`: o antd o liga ao campo por aria-describedby. Sem região viva por cartão. */}
            <Form.Item
              label="Município"
              name="municipio"
              rules={[{ required: true, message: 'Por favor selecione um município' }]}
              extra={semCompra ? <Alert type="warning" showIcon role="none" message={AVISO_SEM_COMPRA} /> : undefined}
            >
              <ComboBox
                lookupFunction={lookupMunicipiosElegiveis}
                renderOption={dispensaCompra ? undefined : opcaoDoMunicipio}
                onChange={(value: ComboBoxValue | null) => mudar({ municipio: value })}
                value={dados.municipio}
                placeholder={
                  !dispensaCompra && !dados.projeto
                    ? 'Selecione um projeto para carregar os municípios'
                    : 'Busque ou selecione um município'
                }
                disabled={!dispensaCompra && !dados.projeto}
                oQueCarrega="os municípios"
                notFoundContent={
                  !dispensaCompra && dados.projeto
                    ? 'Nenhum município encontrado'
                    : 'Nenhum resultado encontrado'
                }
              />
            </Form.Item>
          </div>
        </div>

        {/* Os horários: cada um vira um evento no Google, com o seu dia e as suas pessoas. */}
        {dados.horarios.map((horario, indice) => (
          <HorarioDoEvento
            key={horario.chave}
            ref={(h: HorarioDoEventoHandle | null) => {
              if (h) horarios.current.set(horario.chave, h);
              else horarios.current.delete(horario.chave);
            }}
            chaveDoEvento={chave}
            numeroDoEvento={numero}
            dados={dados}
            horario={horario}
            indice={indice}
            total={dados.horarios.length}
            onChange={mudarHorario}
            me={me}
            onTrava={onTrava}
            erroDoEnvio={errosDoEnvio.porHorario[horario.chave] ?? null}
            onRemover={indice > 0 ? removerHorario : undefined}
          />
        ))}

        {/* "+ horário": o nome acessível diz de qual evento (e contém o texto à vista). No limite, o
            mesmo texto do "+ evento". */}
        <div className="mb-4">
          <Button
            icon={<PlusOutlined aria-hidden />}
            onClick={() => onAdicionarHorario(chave)}
            disabled={noLimite}
            aria-label={
              noLimite
                ? `Adicionar horário ao evento ${numero}: ${TEXTO_DO_LIMITE.toLowerCase()}`
                : `Adicionar horário ao evento ${numero}`
            }
          >
            {noLimite ? TEXTO_DO_LIMITE : 'Adicionar horário'}
          </Button>
        </div>

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
              label: 'Mais detalhes',
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
      {contextoDoModal}
    </section>
  );
}
