/**
 * Semáforo — Relatório mensal e formulários (coletas 2 a 5 do PDF do Semáforo): o relatório mensal do
 * coordenador, a ocorrência (Relacionamento, Comercial ou distribuidor) e a reunião de escuta com o
 * momento reservado. A observação de formação só é lida (decisão 94).
 *
 * O relatório, a ocorrência e a reunião entram no estado da sessão (`useSemaforoDemo`): a cor sugerida do
 * município é recalculada na hora e a ficha do município lê de lá. A lista "Registrado nesta sessão" fica no
 * estado da sessão (ir à ficha e voltar não a apaga). DADOS SIMULADOS; nada é gravado.
 *
 * Decisões do dono de 26/11:
 * - 77: o relatório vence no 5º dia útil do mês seguinte; sem o relatório depois disso, atrasado.
 * - 81 e 82: o relatório vem pré-preenchido com as formações do sistema; o coordenador confere e, se mudar um
 *   número, justifica. As visitas vêm da Logística e do pedido de viagem (FRV), só leitura.
 * - 78: o momento reservado é lido pela gestora de referência principal, pela Líder do NFP e pela SPE.
 * - 94: a observação de formação é registrada na DFF, junto do PDI; aqui ela aparece como lida de lá.
 *
 * Decisões do dono de 25/11:
 * - 46: o relatório mensal é de um projeto (cada projeto tem o seu coordenador e o seu cronograma); a tela
 *   mostra o cronograma de cada projeto no ciclo e o do município, que é o do pior projeto.
 * - 50: a ocorrência guarda a hora do registro e quando foi respondida; a resposta pode entrar depois, na
 *   lista das ocorrências sem resposta.
 * - 48: a reunião de escuta é marcada antes (a data pode ser depois de hoje) e a ata é registrada depois, até
 *   5 dias úteis; o momento reservado entra com a ata.
 * - 38: uma reclamação deixa o município vermelho na hora (a cor em vigor muda, e as tarefas começam).
 */
import { useEffect, useState, type FormEvent, type JSX, type MouseEvent, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Button, Typography } from 'antd';

import { BotoesExportar } from '../ica/componentes/c2/BotoesExportar';
import { CLASSE_CAMPO, CLASSE_ROTULO, formatarDia } from '../ica/componentes/estilos';
import { baixarCsv } from '../ica/exportar';
import { nomeDoMunicipio, sugeridaAgora, type Retorno } from './componentes/corEAlerta';
import { CorComNome } from './componentes/PecasDoAcompanhamento';
import { AvisoQuemVe, CampoMunicipio, EtiquetaCor, RetornoDoRegistro } from './componentes/PecasDoRegistro';
import { doSistema, mesesDoCiclo, periodoDoCiclo, valoresPorProjeto, type ReuniaoEscuta } from './dados';
import {
  corCronograma,
  duasCasas,
  horasEntre,
  META_RESPOSTA_HORAS,
  percentualCronograma,
  periodicidadeDaCor,
  prazoDaAta,
  prazoDoRelatorio,
  ROTULO_COR,
  ROTULO_ORIGEM,
  situacaoDaReuniao,
  textoDataHora,
  textoHoras,
} from './regras';
import { useSemaforoDemo, type Resultado } from './SemaforoDemoContext';
import type { OrigemOcorrencia, TipoOcorrencia } from './tipos';
import { useEstadoDaFicha } from './voltarDaFicha';

const { Title } = Typography;

const TIPOS: Record<TipoOcorrencia, string> = {
  leve: 'Leve (dúvida, ajuste de agenda, pedido de material)',
  reclamacao: 'Reclamação (sobre o coordenador ou os projetos)',
};
/** O momento reservado entra pelo formulário da ata da reunião, não por aqui. */
const ORIGENS: readonly OrigemOcorrencia[] = ['fluxo_unico', 'reuniao_escuta'];
const HORA = /^([01]\d|2[0-3]):[0-5]\d$/;

type Formulario = 'relatorio' | 'ocorrencia' | 'marcar' | 'ata';

const CLASSE_MARCA =
  'h-4 w-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark';

/** Número inteiro do campo; vazio vira NaN para o contexto recusar com a mensagem dele. */
const numero = (texto: string): number => (texto.trim() === '' ? Number.NaN : Number(texto));

/** "2026-12" → "12/2026". */
const mesAno = (mes: string): string => mes.split('-').reverse().join('/');

/** A reunião na lista da ata: "27/11/2026 · ata atrasada (o prazo era 04/12/2026)" (decisão 48). */
function opcaoDaReuniao(x: ReuniaoEscuta, hoje: string): string {
  const prazo = formatarDia(prazoDaAta(x.data));
  const situacao = situacaoDaReuniao(x, hoje);
  const texto =
    situacao === 'agendada' ? 'agendada' : situacao === 'ata_atrasada' ? `ata atrasada (o prazo era ${prazo})` : `ata a registrar até ${prazo}`;
  return `${formatarDia(x.data)} · ${texto}`;
}

interface CampoProps {
  id: string;
  rotulo: ReactNode;
  children: ReactNode;
}

function Campo({ id, rotulo, children }: CampoProps): JSX.Element {
  return (
    <div>
      <label htmlFor={id} className={CLASSE_ROTULO}>
        {rotulo}
      </label>
      {children}
    </div>
  );
}

interface SecaoProps {
  id: string;
  titulo: string;
  nota: string;
  aoEnviar: (e: FormEvent) => void;
  botao: string;
  retorno: Retorno | null;
  /** Nome do município escolhido no topo da página ('' sem escolha): o formulário diz para quem registra. */
  para: string;
  children: ReactNode;
  /** O que vem depois do formulário e do retorno (ex.: o cronograma de cada projeto). */
  depois?: ReactNode;
}

/** Leva o foco ao único campo de município da tela, no topo (o formulário não tem um próprio). */
function irAoMunicipio(e: MouseEvent<HTMLAnchorElement>): void {
  e.preventDefault();
  document.getElementById('relatorio-municipio')?.focus();
}

function Secao({ id, titulo, nota, aoEnviar, botao, retorno, para, children, depois }: SecaoProps): JSX.Element {
  return (
    <section aria-labelledby={id} className="rounded border border-[#8c8c8c] bg-white p-4">
      <Title level={2} id={id} style={{ fontSize: 20 }}>
        {titulo}
      </Title>
      <p className="mb-3 text-sm">{nota}</p>
      <form onSubmit={aoEnviar} noValidate className="space-y-3">
        {children}
        <p className="m-0 text-sm">
          {para ? (
            `Para: ${para}`
          ) : (
            <a href="#relatorio-municipio" onClick={irAoMunicipio}>
              Escolha o município no topo da página
            </a>
          )}
        </p>
        <Button htmlType="submit">{botao}</Button>
      </form>
      <RetornoDoRegistro retorno={retorno} />
      {depois}
    </section>
  );
}

export default function RelatorioMensal(): JSX.Element {
  const {
    dados,
    situacoes,
    registrarRelatorio,
    registrarOcorrencia,
    responderOcorrencia,
    agendarReuniao,
    registrarAta,
    anotacoes,
    anotar,
  } = useSemaforoDemo();
  const estadoDaFicha = useEstadoDaFicha();
  const hoje = dados.data_referencia;
  const periodo = periodoDoCiclo(dados.ciclo_atual);
  const meses = [...periodo.meses].reverse();

  const [municipio, setMunicipio] = useState('');
  const [retornos, setRetornos] = useState<Partial<Record<Formulario, Retorno | null>>>({});

  const [projetoEscolhido, setProjetoEscolhido] = useState('');
  const [mes, setMes] = useState(meses[0]!);
  /** Decisão 81: o que o coordenador mudou no relatório do projeto e mês (`chave`); em outro, vale o do sistema. */
  const [edicao, setEdicao] = useState<{ chave: string; previstas: string; realizadas: string; justificativa: string } | null>(null);

  const [tipo, setTipo] = useState<TipoOcorrencia>('leve');
  const [origem, setOrigem] = useState<OrigemOcorrencia>('fluxo_unico');
  const [dataOcorrencia, setDataOcorrencia] = useState(hoje);
  // Rodada 3: a hora do registro começa vazia, como a da resposta; quem registra informa (decisão 50).
  const [horaOcorrencia, setHoraOcorrencia] = useState('');
  const [respondida, setRespondida] = useState(false);
  const [diaResposta, setDiaResposta] = useState(hoje);
  const [horaResposta, setHoraResposta] = useState('');
  /** A resposta que entra depois, por ocorrência sem resposta: o dia e a hora de cada uma. */
  const [respostas, setRespostas] = useState<Record<number, { dia: string; hora: string }>>({});
  const [avisoResposta, setAvisoResposta] = useState('');
  /** Os erros ficam na ocorrência que os gerou, perto do botão clicado. */
  const [errosResposta, setErrosResposta] = useState<{ ocorrencia: number; erros: string[] } | null>(null);
  // A ocorrência respondida sai da lista e leva junto o botão focado: o foco vai para o aviso, depois da pintura.
  const [focarAviso, setFocarAviso] = useState(false);
  useEffect(() => {
    if (!focarAviso) return;
    document.getElementById('ocorrencia-resposta-aviso')?.focus();
    setFocarAviso(false);
  }, [focarAviso]);

  const [dataReuniao, setDataReuniao] = useState(hoje);

  const [reuniaoDaAta, setReuniaoDaAta] = useState('');
  const [cronogramaConfirmado, setCronogramaConfirmado] = useState(true);
  const [encaminhamentos, setEncaminhamentos] = useState('');
  const [reservado, setReservado] = useState<TipoOcorrencia | ''>('');
  /** A hora em que a ata com a queixa é registrada: o tempo de resposta da queixa conta daqui (decisão 50). */
  const [horaReservado, setHoraReservado] = useState('');

  const id = Number(municipio);
  const escolhido = dados.municipios.find((m) => m.id === id);
  const nome = escolhido ? nomeDoMunicipio(escolhido) : '';
  const situacao = situacoes.find((s) => s.municipio === id);
  const periodicidade = situacao ? periodicidadeDaCor(situacao.cor_vigente) : null;
  const gestora = dados.pessoas.find((p) => p.id === escolhido?.gestora_referencia);
  const coordenadorDe = (coordenador: number | null): string | null =>
    dados.coordenadores.find((c) => c.id === coordenador)?.nome ?? null;

  const projetos = escolhido?.projetos ?? [];
  // Com um projeto só, ele já vem escolhido.
  const projetoId = projetos.some((p) => String(p.id) === projetoEscolhido)
    ? Number(projetoEscolhido)
    : projetos.length === 1
      ? projetos[0]!.id
      : 0;
  const projeto = projetos.find((p) => p.id === projetoId);
  const relatorioDoMes = dados.relatorios.find((r) => r.municipio === id && r.projeto === projetoId && r.mes === mes);
  const prazoDoMes = prazoDoRelatorio(mes);
  // Decisões 81 e 82: as formações vêm do sistema e o coordenador confere; as visitas, da Logística e do FRV.
  const sistema = doSistema(dados, projetoId, mes);
  const chave = `${projetoId}-${mes}`;
  // Mês já entregue: o formulário parte do que foi entregue (e da justificativa), não volta aos números do sistema.
  const base = relatorioDoMes ?? sistema;
  const campos =
    edicao?.chave === chave
      ? edicao
      : {
          chave,
          previstas: base ? String(base.formacoes_previstas) : '',
          realizadas: base ? String(base.formacoes_realizadas) : '',
          justificativa: relatorioDoMes?.justificativa ?? '',
        };
  const editar = (parte: Partial<typeof campos>): void => setEdicao({ ...campos, ...parte });
  // Decisão 94: as observações de formação simuladas são as tarefas do amarelo já feitas, lidas da DFF.
  const observacoes = dados.tarefas
    .filter((t) => t.municipio === id && t.chave === 'observacao_formacao' && t.concluida_em !== null)
    .sort((a, b) => (a.concluida_em ?? '').localeCompare(b.concluida_em ?? ''));
  const cronogramas = escolhido ? valoresPorProjeto(dados, id, dados.ciclo_atual, hoje) : [];
  const cronogramasComDado = cronogramas.flatMap((c) => (c.cronograma === null ? [] : [c.cronograma]));
  const cronogramaDoMunicipio = cronogramasComDado.length === 0 ? null : Math.min(...cronogramasComDado);

  const semResposta = dados.ocorrencias
    .filter((o) => o.municipio === id && o.respondida_em === null)
    .sort((a, b) => a.registrada_em.localeCompare(b.registrada_em));
  const reunioesSemAta = dados.reunioes
    .filter((x) => x.municipio === id && x.ata_em === null)
    .sort((a, b) => a.data.localeCompare(b.data));
  const reuniaoEscolhida = reunioesSemAta.find((x) => String(x.id) === reuniaoDaAta);

  // Rodada 5: fica só o retorno do último registro. O "antes → agora" é calculado na hora; um retorno antigo
  // passaria a mostrar a piora causada por outro registro, como se fosse dele.
  const mostrar = (form: Formulario, retorno: Retorno): void => setRetornos({ [form]: retorno });

  const escolherMunicipio = (valor: string): void => {
    setMunicipio(valor);
    // Rodada 5: o retorno era do município anterior (ou um erro que a escolha já resolveu).
    setRetornos({});
    setProjetoEscolhido('');
    setReuniaoDaAta('');
    setAvisoResposta('');
    setErrosResposta(null);
  };

  /** Registra no estado da sessão guardando a cor de antes, para a tela mostrar "antes → agora". */
  const registrar = (form: Formulario, acao: () => Resultado, titulo: string, reservadoNaReuniao = false): boolean => {
    const antes = sugeridaAgora(situacoes, id);
    const aguardandoAntes = situacao?.aguardando_comite ?? false;
    const r = acao();
    if (!r.ok) {
      mostrar(form, { ok: false, erros: r.erros });
      return false;
    }
    if (antes) mostrar(form, { ok: true, municipio: id, titulo, antes, reservado: reservadoNaReuniao, aguardandoAntes });
    return true;
  };

  const enviarRelatorio = (e: FormEvent): void => {
    e.preventDefault();
    const titulo = `Relatório de ${mesAno(mes)} registrado para ${nome}, projeto ${projeto?.nome ?? ''}.`;
    const ok = registrar(
      'relatorio',
      () =>
        registrarRelatorio({
          municipio: id,
          projeto: projetoId,
          mes,
          formacoes_previstas: numero(campos.previstas),
          formacoes_realizadas: numero(campos.realizadas),
          visitas_previstas: sistema?.visitas_previstas ?? 0,
          visitas_realizadas: sistema?.visitas_realizadas ?? 0,
          justificativa: campos.justificativa,
        }),
      titulo,
    );
    if (!ok) return;
    anotar(`${formatarDia(hoje)} · Relatório mensal de ${mesAno(mes)} · ${nome} · projeto ${projeto?.nome ?? ''}`);
    setEdicao(null);
  };

  const enviarOcorrencia = (e: FormEvent): void => {
    e.preventDefault();
    const ok = registrar(
      'ocorrencia',
      () =>
        registrarOcorrencia({
          municipio: id,
          origem,
          tipo,
          data: dataOcorrencia,
          hora: horaOcorrencia,
          respondida_em: respondida ? `${diaResposta}T${horaResposta}` : null,
        }),
      `Ocorrência registrada para ${nome}.`,
    );
    if (!ok) return;
    anotar(`${formatarDia(dataOcorrencia)} · Ocorrência ${tipo === 'leve' ? 'leve' : '(reclamação)'} · ${nome}`);
    setRespondida(false);
    setHoraResposta('');
  };

  const enviarResposta = (ocorrencia: number, registradaEm: string): void => {
    const { dia, hora } = respostas[ocorrencia] ?? { dia: hoje, hora: '' };
    const r = responderOcorrencia(ocorrencia, `${dia}T${hora}`);
    if (!r.ok) {
      setErrosResposta({ ocorrencia, erros: r.erros });
      setAvisoResposta('');
      return;
    }
    const horas = horasEntre(registradaEm, `${dia}T${hora}:00-03:00`);
    const meta = horas <= META_RESPOSTA_HORAS ? 'dentro' : 'fora';
    setErrosResposta(null);
    setAvisoResposta(`Resposta registrada: em ${textoHoras(horas)}, ${meta} da meta de ${META_RESPOSTA_HORAS} h.`);
    setFocarAviso(true);
    anotar(`${formatarDia(dia)} · Resposta a uma ocorrência · ${nome}`);
  };

  const enviarMarcacao = (e: FormEvent): void => {
    e.preventDefault();
    const r = agendarReuniao({ municipio: id, data: dataReuniao });
    if (!r.ok) {
      mostrar('marcar', { ok: false, erros: r.erros });
      return;
    }
    mostrar('marcar', {
      ok: true,
      municipio: id,
      titulo: `Reunião de escuta marcada para ${formatarDia(dataReuniao)} (${nome}). A ata vai até 5 dias úteis depois.`,
    });
    anotar(`${formatarDia(hoje)} · Reunião de escuta ${periodicidade} marcada para ${formatarDia(dataReuniao)} · ${nome}`);
  };

  const enviarAta = (e: FormEvent): void => {
    e.preventDefault();
    const reuniao = reuniaoEscolhida;
    const ok = registrar(
      'ata',
      () => {
        // A hora vem antes da ata: sem ela, nada entra (nem a ata sem a queixa).
        if (reservado !== '' && !HORA.test(horaReservado)) {
          return { ok: false, erros: ['Informe a hora deste registro (horas e minutos).'] };
        }
        const r = registrarAta(reuniao?.id ?? 0, { cronograma_confirmado: cronogramaConfirmado, encaminhamentos });
        // A queixa do momento reservado é uma ocorrência própria (coleta 5): a data é a da reunião, quando foi
        // feita; o registro é hoje, na hora informada, quando chega a quem responde (Para validar).
        if (!r.ok || reservado === '' || !reuniao) return r;
        return registrarOcorrencia({
          municipio: id,
          origem: 'momento_reservado',
          tipo: reservado,
          data: reuniao.data,
          registrada_no_dia: hoje,
          hora: horaReservado,
        });
      },
      `Ata da reunião de ${reuniao ? formatarDia(reuniao.data) : ''} registrada para ${nome}.`,
      reservado !== '',
    );
    if (!ok || !reuniao) return;
    anotar(
      `${formatarDia(hoje)} · Ata da reunião de escuta de ${formatarDia(reuniao.data)} · ${nome}${reservado === '' ? '' : ' · com queixa no momento reservado'}`,
    );
    setReuniaoDaAta('');
    setEncaminhamentos('');
    setReservado('');
    setHoraReservado('');
  };

  const relatoriosDoCiclo = dados.relatorios
    .filter((r) => periodo.meses.includes(r.mes))
    .sort((a, b) => a.mes.localeCompare(b.mes) || a.municipio - b.municipio || a.projeto - b.projeto);
  const baixarPlanilha = (): void =>
    baixarCsv(
      `semaforo_relatorios_${dados.ciclo_atual}.csv`,
      [
        'Mês',
        'Município',
        'UF',
        'Projeto',
        'Coordenador',
        'Formações previstas',
        'Formações realizadas',
        'Visitas previstas',
        'Visitas realizadas',
        'Cumprido (%)',
        'Justificativa',
      ],
      relatoriosDoCiclo.map((r) => {
        const m = dados.municipios.find((x) => x.id === r.municipio);
        const cumprido = percentualCronograma([r]);
        return [
          mesAno(r.mes),
          m?.nome ?? '',
          m?.uf ?? '',
          m?.projetos.find((p) => p.id === r.projeto)?.nome ?? '',
          coordenadorDe(r.coordenador) ?? '',
          r.formacoes_previstas,
          r.formacoes_realizadas,
          r.visitas_previstas,
          r.visitas_realizadas,
          // Decisão 30: 2 casas, como a tela.
          cumprido === null ? '' : duasCasas(cumprido),
          r.justificativa ?? '',
        ];
      }),
    );

  const cronogramaDoCiclo = escolhido && (
    <div className="mt-4 border-t border-[#d9d9d9] pt-3 text-sm">
      <ul aria-label={`Cronograma do ciclo ${dados.ciclo_atual} por projeto`} className="m-0 mb-2 grid list-none gap-1 p-0">
        {projetos.map((p) => {
          const v = cronogramas.find((c) => c.projeto === p.id);
          const doProjeto = dados.relatorios.filter((r) => r.municipio === id && r.projeto === p.id && periodo.meses.includes(r.mes));
          const previstas = doProjeto.reduce((s, r) => s + r.formacoes_previstas + r.visitas_previstas, 0);
          const realizadas = doProjeto.reduce((s, r) => s + r.formacoes_realizadas + r.visitas_realizadas, 0);
          const coordenador = coordenadorDe(p.coordenador);
          return (
            <li key={p.id}>
              {p.nome} ({coordenador ? `coordenador ${coordenador}` : 'sem coordenador'}):{' '}
              {v?.cronograma == null ? (
                'sem dado neste ciclo'
              ) : (
                <>
                  {realizadas} de {previstas} formações e visitas, {duasCasas(v.cronograma)}% ·{' '}
                  <CorComNome cor={corCronograma(v.cronograma)} />
                </>
              )}
            </li>
          );
        })}
      </ul>
      <p className="m-0">
        Cronograma do município (o pior projeto):{' '}
        {cronogramaDoMunicipio === null ? (
          'sem dado neste ciclo'
        ) : (
          <>
            {duasCasas(cronogramaDoMunicipio)}% · <CorComNome cor={corCronograma(cronogramaDoMunicipio)} />
          </>
        )}
      </p>
    </div>
  );

  const respostasPendentes = escolhido && (
    <div className="mt-4 border-t border-[#d9d9d9] pt-3">
      <Title level={3} id="ocorrencias-sem-resposta" style={{ fontSize: 16 }}>
        Ocorrências sem resposta
      </Title>
      {semResposta.length === 0 ? (
        <p className="text-sm">Nenhuma ocorrência de {nome} está sem resposta.</p>
      ) : (
        <ul aria-label={`Ocorrências sem resposta de ${nome}`} className="m-0 grid list-none gap-3 p-0">
          {semResposta.map((o) => {
            const valor = respostas[o.id] ?? { dia: hoje, hora: '' };
            const mudar = (parte: Partial<typeof valor>) => setRespostas((atuais) => ({ ...atuais, [o.id]: { ...valor, ...parte } }));
            const quando = textoDataHora(o.registrada_em);
            const erros = errosResposta?.ocorrencia === o.id ? errosResposta.erros : [];
            const idErro = `resposta-${o.id}-erro`;
            const marcarErro = erros.length > 0 ? { 'aria-invalid': true, 'aria-describedby': idErro } : {};
            // O nome do campo diz de qual ocorrência é a resposta (os campos se repetem a cada ocorrência).
            const deQual = <span className="sr-only"> à ocorrência de {quando}</span>;
            return (
              <li key={o.id} className="rounded border border-[#d9d9d9] p-2 text-sm">
                <p className="m-0 mb-2 font-semibold">
                  {quando} · {o.tipo === 'reclamacao' ? 'Reclamação' : 'Leve'}
                </p>
                <div className="mb-2 grid gap-2 sm:grid-cols-2">
                  <Campo id={`resposta-${o.id}-dia`} rotulo={<>Dia da resposta{deQual}</>}>
                    <input
                      id={`resposta-${o.id}-dia`}
                      type="date"
                      max={hoje}
                      className={CLASSE_CAMPO}
                      value={valor.dia}
                      onChange={(e) => mudar({ dia: e.target.value })}
                      {...marcarErro}
                    />
                  </Campo>
                  <Campo id={`resposta-${o.id}-hora`} rotulo={<>Hora da resposta{deQual}</>}>
                    <input
                      id={`resposta-${o.id}-hora`}
                      type="time"
                      className={CLASSE_CAMPO}
                      value={valor.hora}
                      onChange={(e) => mudar({ hora: e.target.value })}
                      {...marcarErro}
                    />
                  </Campo>
                </div>
                {erros.length > 0 && (
                  <div id={idErro} role="alert" className="mb-2 rounded border border-[#A8251B] bg-[#FCE4E2] p-2 text-sm text-[#8A1C14]">
                    {erros.map((e) => (
                      <p key={e} className="m-0">
                        {e}
                      </p>
                    ))}
                  </div>
                )}
                <Button onClick={() => enviarResposta(o.id, o.registrada_em)}>
                  Registrar a resposta{' '}
                  <span className="sr-only">da ocorrência de {quando}</span>
                </Button>
              </li>
            );
          })}
        </ul>
      )}
      <p id="ocorrencia-resposta-aviso" tabIndex={-1} aria-live="polite" className="m-0 mt-2 text-sm font-semibold">
        {avisoResposta}
      </p>
    </div>
  );

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Relatório mensal e formulários
      </Title>
      <AvisoQuemVe tela="relatorio-mensal" />
      <p className="mb-4">
        Os formulários que alimentam o Semáforo. O que você registrar entra na demonstração na hora: a cor sugerida do
        município é recalculada, e o relatório, a ocorrência e a reunião aparecem na ficha do município. A observação de
        formação vem da DFF, só para leitura. As datas ficam no ciclo atual, de{' '}
        {formatarDia(periodo.inicio)} até hoje; só a reunião de escuta pode ser marcada para depois de hoje. Sair do Semáforo ou recarregar a página apaga tudo.
      </p>
      <BotoesExportar aoBaixarPlanilha={baixarPlanilha} />
      <p className="mb-4 text-sm">
        A planilha traz os {relatoriosDoCiclo.length} relatórios mensais do ciclo{' '}
        {dados.ciclo_atual} ({mesesDoCiclo(dados.ciclo_atual)}), um por projeto e mês, com os desta sessão.
      </p>

      <div className="mb-6 max-w-xl">
        <CampoMunicipio id="relatorio-municipio" valor={municipio} aoMudar={escolherMunicipio} />
        {escolhido && situacao && (
          <div className="mt-2 space-y-1 text-sm">
            <ul aria-label={`Projetos de ${nome}`} className="m-0 pl-5">
              {projetos.map((p) => {
                const coordenador = coordenadorDe(p.coordenador);
                return (
                  <li key={p.id}>
                    {p.nome}: {coordenador ? `coordenador ${coordenador}` : 'sem coordenador (não há relatório mensal)'}
                  </li>
                );
              })}
            </ul>
            <p className="m-0">Gestora de referência: {gestora?.nome ?? 'não informada'}</p>
            <p className="m-0">
              Cor sugerida agora: <EtiquetaCor cor={situacao.ciclos.at(-1)?.resultado.cor ?? 'verde'} /> · Cor em vigor:{' '}
              <EtiquetaCor cor={situacao.cor_vigente} />
            </p>
            <p className="m-0">
              <Link to={`/integra/semaforo/municipio/${id}`} state={estadoDaFicha}>Abrir a ficha de {nome}</Link>
            </p>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Secao
          id="form-relatorio"
          titulo="Relatório mensal do coordenador"
          nota="Na versão real, o coordenador preenche numa tela à parte, fora da Integra; ali ele vê também o resultado juntado da pesquisa dos projetos dele, sem o momento reservado e sem saber quem respondeu. O relatório vem pré-preenchido com as formações do sistema: o coordenador confere e, se mudar um número, escreve a justificativa. As visitas vêm da Logística e do pedido de viagem (FRV). Cada projeto tem o seu relatório e o seu cronograma: formações e visitas realizadas sobre as previstas. Na cor do município entra o pior projeto. Registrar o mesmo projeto e mês de novo substitui o anterior."
          aoEnviar={enviarRelatorio}
          botao="Registrar relatório"
          retorno={retornos.relatorio ?? null}
          para={nome}
          depois={cronogramaDoCiclo}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo id="relatorio-projeto" rotulo="Projeto">
              <select
                id="relatorio-projeto"
                className={CLASSE_CAMPO}
                value={projetoId === 0 ? '' : String(projetoId)}
                onChange={(e) => setProjetoEscolhido(e.target.value)}
              >
                <option value="">{escolhido ? 'Escolha o projeto' : 'Escolha antes o município'}</option>
                {projetos.map((p) => (
                  <option key={p.id} value={String(p.id)}>
                    {p.nome}
                    {p.coordenador === null ? ' (sem coordenador)' : ''}
                  </option>
                ))}
              </select>
            </Campo>
            <Campo id="relatorio-mes" rotulo="Mês">
              <select id="relatorio-mes" className={CLASSE_CAMPO} value={mes} onChange={(e) => setMes(e.target.value)}>
                {meses.map((m) => (
                  <option key={m} value={m}>
                    {mesAno(m)}
                  </option>
                ))}
              </select>
            </Campo>
          </div>
          <p className="m-0 text-sm">
            Prazo do relatório de {mesAno(mes)}: vence em {formatarDia(prazoDoMes)} (5º dia útil do mês seguinte).
            {projeto && !relatorioDoMes && hoje > prazoDoMes && ' Atrasado: ainda não foi entregue.'}
          </p>
          {relatorioDoMes && (
            <p className="m-0 text-sm">
              Já entregue para {mesAno(mes)} neste projeto: {relatorioDoMes.formacoes_realizadas} de{' '}
              {relatorioDoMes.formacoes_previstas} formações e {relatorioDoMes.visitas_realizadas} de{' '}
              {relatorioDoMes.visitas_previstas} visitas. Mandar de novo corrige o relatório: vale o novo, e o anterior fica
              guardado.
              {relatorioDoMes.justificativa && ` Justificativa: ${relatorioDoMes.justificativa}`}
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            {(
              [
                ['relatorio-fp', 'Formações previstas', 'previstas'],
                ['relatorio-fr', 'Formações realizadas', 'realizadas'],
              ] as const
            ).map(([campo, rotulo, parte]) => (
              <Campo key={campo} id={campo} rotulo={rotulo}>
                <input
                  id={campo}
                  type="number"
                  min={0}
                  step={1}
                  inputMode="numeric"
                  className={CLASSE_CAMPO}
                  value={campos[parte]}
                  onChange={(e) => editar({ [parte]: e.target.value })}
                />
              </Campo>
            ))}
          </div>
          <p className="m-0 text-sm">
            Visitas, da Logística e do pedido de viagem (FRV), só leitura:{' '}
            {sistema ? `${sistema.visitas_realizadas} de ${sistema.visitas_previstas} realizadas.` : 'sem dado para este projeto e mês.'}
          </p>
          <Campo id="relatorio-justificativa" rotulo="Justificativa">
            <textarea
              id="relatorio-justificativa"
              rows={2}
              aria-describedby="relatorio-justificativa-nota"
              className={CLASSE_CAMPO}
              value={campos.justificativa}
              onChange={(e) => editar({ justificativa: e.target.value })}
            />
            <span id="relatorio-justificativa-nota" className="mt-1 block text-sm">
              {sistema
                ? `Veio do sistema: ${sistema.formacoes_previstas} formações previstas e ${sistema.formacoes_realizadas} realizadas. A justificativa é obrigatória só se você mudar um número que veio do sistema.`
                : 'A justificativa é obrigatória só se você mudar um número que veio do sistema.'}
            </span>
          </Campo>
        </Secao>

        <Secao
          id="form-ocorrencia"
          titulo="Ocorrência"
          nota={`Na versão real, Relacionamento, Comercial e distribuidores registram por link, sem conta (o distribuidor registra pelo Comercial). Uma reclamação deixa o município vermelho na hora: a cor em vigor muda e as tarefas do vermelho começam, salvo se o Comitê já desfez o vermelho por esse mesmo motivo; o Comitê confirma ou desfaz depois. Registre também quando a ocorrência foi respondida ao município (meta de ${META_RESPOSTA_HORAS} h corridas); a resposta pode entrar depois, na lista abaixo.`}
          aoEnviar={enviarOcorrencia}
          botao="Registrar ocorrência"
          retorno={retornos.ocorrencia ?? null}
          para={nome}
          depois={respostasPendentes}
        >
          <Campo id="ocorrencia-tipo" rotulo="Tipo">
            <select id="ocorrencia-tipo" className={CLASSE_CAMPO} value={tipo} onChange={(e) => setTipo(e.target.value as TipoOcorrencia)}>
              {(Object.keys(TIPOS) as TipoOcorrencia[]).map((t) => (
                <option key={t} value={t}>
                  {TIPOS[t]}
                </option>
              ))}
            </select>
          </Campo>
          <Campo id="ocorrencia-origem" rotulo="Por onde chegou">
            <select
              id="ocorrencia-origem"
              className={CLASSE_CAMPO}
              value={origem}
              onChange={(e) => setOrigem(e.target.value as OrigemOcorrencia)}
            >
              {ORIGENS.map((o) => (
                <option key={o} value={o}>
                  {ROTULO_ORIGEM[o]}
                </option>
              ))}
            </select>
          </Campo>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo id="ocorrencia-data" rotulo="Data">
              <input
                id="ocorrencia-data"
                type="date"
                min={periodo.inicio}
                max={hoje}
                className={CLASSE_CAMPO}
                value={dataOcorrencia}
                onChange={(e) => setDataOcorrencia(e.target.value)}
              />
            </Campo>
            <Campo id="ocorrencia-hora" rotulo="Hora">
              <input
                id="ocorrencia-hora"
                type="time"
                className={CLASSE_CAMPO}
                value={horaOcorrencia}
                onChange={(e) => setHoraOcorrencia(e.target.value)}
              />
            </Campo>
          </div>
          <label className="flex items-center gap-2">
            <input type="checkbox" className={CLASSE_MARCA} checked={respondida} onChange={(e) => setRespondida(e.target.checked)} />
            Já foi respondida
          </label>
          {respondida && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Campo id="ocorrencia-resposta-dia" rotulo="Dia da resposta">
                <input
                  id="ocorrencia-resposta-dia"
                  type="date"
                  min={periodo.inicio}
                  max={hoje}
                  className={CLASSE_CAMPO}
                  value={diaResposta}
                  onChange={(e) => setDiaResposta(e.target.value)}
                />
              </Campo>
              <Campo id="ocorrencia-resposta-hora" rotulo="Hora da resposta">
                <input
                  id="ocorrencia-resposta-hora"
                  type="time"
                  className={CLASSE_CAMPO}
                  value={horaResposta}
                  onChange={(e) => setHoraResposta(e.target.value)}
                />
              </Campo>
            </div>
          )}
        </Secao>

        <Secao
          id="form-reuniao-marcar"
          titulo="Marcar a reunião de escuta"
          nota="A cada 6 meses no verde e a cada 3 meses no amarelo e no vermelho. A reunião é marcada antes (a data pode ser depois de hoje); a ata é registrada depois, até 5 dias úteis após a reunião."
          aoEnviar={enviarMarcacao}
          botao="Marcar a reunião"
          retorno={retornos.marcar ?? null}
          para={nome}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo id="reuniao-data" rotulo="Data da reunião">
              <input
                id="reuniao-data"
                type="date"
                min={periodo.inicio}
                className={CLASSE_CAMPO}
                value={dataReuniao}
                onChange={(e) => setDataReuniao(e.target.value)}
              />
            </Campo>
          </div>
          {/* Rodada 5: a periodicidade sai da cor em vigor, como nos dados simulados (seção 5 do PDF). */}
          <p className="m-0 mt-2 text-sm">
            {situacao
              ? `Periodicidade: ${periodicidade}, pela cor em vigor (${ROTULO_COR[situacao.cor_vigente]}).`
              : 'Periodicidade: sai da cor em vigor do município (semestral no verde; trimestral no amarelo e no vermelho).'}
          </p>
        </Secao>

        <Secao
          id="form-reuniao-ata"
          titulo="Ata da reunião de escuta"
          nota="A ata entra no dia da reunião ou depois, até 5 dias úteis; passado o prazo, a reunião aparece como ata atrasada no painel da gestora. O momento reservado entra junto com a ata."
          aoEnviar={enviarAta}
          botao="Registrar a ata"
          retorno={retornos.ata ?? null}
          para={nome}
        >
          <Campo id="ata-reuniao" rotulo="Reunião">
            <select id="ata-reuniao" className={CLASSE_CAMPO} value={reuniaoDaAta} onChange={(e) => setReuniaoDaAta(e.target.value)}>
              <option value="">
                {!escolhido
                  ? 'Escolha antes o município'
                  : reunioesSemAta.length === 0
                    ? 'Nenhuma reunião sem ata: marque uma acima'
                    : 'Escolha a reunião'}
              </option>
              {reunioesSemAta.map((x) => (
                <option key={x.id} value={String(x.id)}>
                  {opcaoDaReuniao(x, hoje)}
                </option>
              ))}
            </select>
          </Campo>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className={CLASSE_MARCA}
              checked={cronogramaConfirmado}
              onChange={(e) => setCronogramaConfirmado(e.target.checked)}
            />
            O município confirmou o cronograma
          </label>
          <Campo id="reuniao-combinado" rotulo="O que ficou combinado">
            <textarea
              id="reuniao-combinado"
              rows={2}
              className={CLASSE_CAMPO}
              value={encaminhamentos}
              onChange={(e) => setEncaminhamentos(e.target.value)}
            />
          </Campo>
          <fieldset className="m-0 rounded border border-[#d9d9d9] p-3">
            <legend className="px-1 font-semibold">Momento reservado</legend>
            <p className="mb-2 mt-0 text-sm">
              Na versão real, o momento reservado é confidencial: só a gestora de referência principal do município, a Líder
              do NFP e a SPE leem o que for registrado aqui; ninguém mais. No protótipo, quem entra na Integra vê tudo.
            </p>
            <Campo id="reuniao-reservado" rotulo="Queixa no momento reservado">
              <select
                id="reuniao-reservado"
                className={CLASSE_CAMPO}
                value={reservado}
                onChange={(e) => setReservado(e.target.value as TipoOcorrencia | '')}
              >
                <option value="">Nenhuma</option>
                {(Object.keys(TIPOS) as TipoOcorrencia[]).map((t) => (
                  <option key={t} value={t}>
                    {TIPOS[t]}
                  </option>
                ))}
              </select>
            </Campo>
            {reservado !== '' && (
              <Campo id="reuniao-reservado-hora" rotulo="Hora deste registro">
                <input
                  id="reuniao-reservado-hora"
                  type="time"
                  aria-describedby="reuniao-reservado-hora-nota"
                  className={CLASSE_CAMPO}
                  value={horaReservado}
                  onChange={(e) => setHoraReservado(e.target.value)}
                />
                <span id="reuniao-reservado-hora-nota" className="mt-1 block text-sm">
                  A queixa fica com a data da reunião. O tempo de resposta conta de hoje, nesta hora, quando ela chega a
                  quem responde.
                </span>
              </Campo>
            )}
          </fieldset>
        </Secao>

        <section aria-labelledby="observacao-titulo" className="rounded border border-[#8c8c8c] bg-white p-4">
          <Title level={2} id="observacao-titulo" style={{ fontSize: 20 }}>
            Observação de formação
          </Title>
          <p className="mb-3 text-sm">A observação de formação é registrada na DFF, junto do PDI; o sistema lê de lá.</p>
          {escolhido &&
            (observacoes.length === 0 ? (
              <p className="m-0 text-sm">Nenhuma observação de formação de {nome} lida da DFF.</p>
            ) : (
              <ul aria-label={`Observações de formação de ${nome}, lidas da DFF`} className="m-0 pl-5 text-sm">
                {observacoes.map((t) => (
                  <li key={t.id}>Registrada na DFF em {formatarDia(t.concluida_em ?? '')} (lida da DFF)</li>
                ))}
              </ul>
            ))}
        </section>
      </div>

      <section aria-labelledby="relatorio-sessao" className="mt-8">
        <Title level={2} id="relatorio-sessao" style={{ fontSize: 20 }}>
          Registrado nesta sessão
        </Title>
        <div aria-live="polite">
          {anotacoes.length === 0 ? (
            <p>Nada registrado ainda.</p>
          ) : (
            <ul aria-label="Registrado nesta sessão" className="m-0 pl-5">
              {anotacoes.map((texto, i) => (
                <li key={anotacoes.length - i}>{texto}</li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </section>
  );
}
