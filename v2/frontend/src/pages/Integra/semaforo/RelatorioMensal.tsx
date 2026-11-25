/**
 * Semáforo — Relatório mensal e formulários (coletas 2 a 5 do PDF do Semáforo): o relatório mensal do
 * coordenador, a ocorrência (Relacionamento, Comercial ou distribuidor), a reunião de escuta com o
 * momento reservado e a observação de formação.
 *
 * O relatório, a ocorrência e a reunião entram no estado da sessão (`useSemaforoDemo`): a cor sugerida do
 * município é recalculada na hora e a ficha do município lê de lá. A observação de formação não é um dos
 * 5 indicadores e não entra nos dados: fica só na lista "Registrado nesta sessão", que o estado da sessão
 * guarda (ir à ficha e voltar não a apaga). DADOS SIMULADOS; nada é gravado.
 */
import { useState, type FormEvent, type JSX, type MouseEvent, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Button, Typography } from 'antd';

import { BotoesExportar } from '../ica/componentes/c2/BotoesExportar';
import { CLASSE_CAMPO, CLASSE_ROTULO, formatarDia } from '../ica/componentes/estilos';
import { baixarCsv } from '../ica/exportar';
import { nomeDoMunicipio, sugeridaAgora, type Retorno } from './componentes/corEAlerta';
import { AvisoQuemVe, CampoMunicipio, EtiquetaCor, RetornoDoRegistro } from './componentes/PecasDoRegistro';
import { mesesDoCiclo, periodoDoCiclo } from './dados';
import { percentualCronograma, ROTULO_ORIGEM } from './regras';
import { useSemaforoDemo, type Resultado } from './SemaforoDemoContext';
import type { OrigemOcorrencia, TipoOcorrencia } from './tipos';
import { useEstadoDaFicha } from './voltarDaFicha';

const { Title } = Typography;

const TIPOS: Record<TipoOcorrencia, string> = {
  leve: 'Leve (dúvida, ajuste de agenda, pedido de material)',
  reclamacao: 'Reclamação (sobre o coordenador ou os projetos)',
};
/** O momento reservado entra pelo formulário da reunião, não por aqui. */
const ORIGENS: readonly OrigemOcorrencia[] = ['fluxo_unico', 'reuniao_escuta'];
const COMO_FOI = ['Boa', 'Com pontos a melhorar', 'Preocupante'] as const;

type Formulario = 'relatorio' | 'ocorrencia' | 'reuniao' | 'observacao';

const CLASSE_MARCA =
  'h-4 w-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark';

/** Número inteiro do campo; vazio vira NaN para o contexto recusar com a mensagem dele. */
const numero = (texto: string): number => (texto.trim() === '' ? Number.NaN : Number(texto));

/** "2026-12" → "12/2026". */
const mesAno = (mes: string): string => mes.split('-').reverse().join('/');

interface CampoProps {
  id: string;
  rotulo: string;
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
}

/** Leva o foco ao único campo de município da tela, no topo (o formulário não tem um próprio). */
function irAoMunicipio(e: MouseEvent<HTMLAnchorElement>): void {
  e.preventDefault();
  document.getElementById('relatorio-municipio')?.focus();
}

function Secao({ id, titulo, nota, aoEnviar, botao, retorno, para, children }: SecaoProps): JSX.Element {
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
    </section>
  );
}

export default function RelatorioMensal(): JSX.Element {
  const { dados, situacoes, registrarRelatorio, registrarOcorrencia, registrarReuniao, anotacoes, anotar } = useSemaforoDemo();
  const estadoDaFicha = useEstadoDaFicha();
  const hoje = dados.data_referencia;
  const periodo = periodoDoCiclo(dados.ciclo_atual);
  const meses = [...periodo.meses].reverse();

  const [municipio, setMunicipio] = useState('');
  const [retornos, setRetornos] = useState<Partial<Record<Formulario, Retorno | null>>>({});

  const [mes, setMes] = useState(meses[0]!);
  const [formacoesPrevistas, setFormacoesPrevistas] = useState('');
  const [formacoesRealizadas, setFormacoesRealizadas] = useState('');
  const [visitasPrevistas, setVisitasPrevistas] = useState('');
  const [visitasRealizadas, setVisitasRealizadas] = useState('');

  const [tipo, setTipo] = useState<TipoOcorrencia>('leve');
  const [origem, setOrigem] = useState<OrigemOcorrencia>('fluxo_unico');
  const [dataOcorrencia, setDataOcorrencia] = useState(hoje);

  const [dataReuniao, setDataReuniao] = useState(hoje);
  const [periodicidade, setPeriodicidade] = useState<'semestral' | 'trimestral'>('semestral');
  const [cronogramaConfirmado, setCronogramaConfirmado] = useState(true);
  const [encaminhamentos, setEncaminhamentos] = useState('');
  const [reservado, setReservado] = useState<TipoOcorrencia | ''>('');

  const [dataObservacao, setDataObservacao] = useState(hoje);
  const [comoFoi, setComoFoi] = useState<(typeof COMO_FOI)[number]>(COMO_FOI[0]);
  const [observado, setObservado] = useState('');

  const id = Number(municipio);
  const escolhido = dados.municipios.find((m) => m.id === id);
  const nome = escolhido ? nomeDoMunicipio(escolhido) : '';
  const situacao = situacoes.find((s) => s.municipio === id);
  const coordenador = dados.coordenadores.find((c) => c.id === escolhido?.coordenador);
  const gestora = dados.pessoas.find((p) => p.id === escolhido?.gestora_referencia);
  const relatorioDoMes = dados.relatorios.find((r) => r.municipio === id && r.mes === mes);

  const mostrar = (form: Formulario, retorno: Retorno): void => setRetornos((atuais) => ({ ...atuais, [form]: retorno }));

  /** Registra no estado da sessão guardando a cor de antes, para a tela mostrar "antes → agora". */
  const registrar = (form: Formulario, acao: () => Resultado, titulo: string, reservadoNaReuniao = false): boolean => {
    const antes = sugeridaAgora(situacoes, id);
    const r = acao();
    if (!r.ok) {
      mostrar(form, { ok: false, erros: r.erros });
      return false;
    }
    if (antes) mostrar(form, { ok: true, municipio: id, titulo, antes, reservado: reservadoNaReuniao });
    return true;
  };

  const enviarRelatorio = (e: FormEvent): void => {
    e.preventDefault();
    const titulo = `Relatório de ${mesAno(mes)} registrado para ${nome}.`;
    const ok = registrar(
      'relatorio',
      () =>
        registrarRelatorio({
          municipio: id,
          mes,
          formacoes_previstas: numero(formacoesPrevistas),
          formacoes_realizadas: numero(formacoesRealizadas),
          visitas_previstas: numero(visitasPrevistas),
          visitas_realizadas: numero(visitasRealizadas),
        }),
      titulo,
    );
    if (!ok) return;
    anotar(`${formatarDia(hoje)} · Relatório mensal de ${mesAno(mes)} · ${nome}`);
    for (const limpar of [setFormacoesPrevistas, setFormacoesRealizadas, setVisitasPrevistas, setVisitasRealizadas]) limpar('');
  };

  const enviarOcorrencia = (e: FormEvent): void => {
    e.preventDefault();
    const ok = registrar(
      'ocorrencia',
      () => registrarOcorrencia({ municipio: id, origem, tipo, data: dataOcorrencia }),
      `Ocorrência registrada para ${nome}.`,
    );
    if (ok) anotar(`${formatarDia(dataOcorrencia)} · Ocorrência ${tipo === 'leve' ? 'leve' : '(reclamação)'} · ${nome}`);
  };

  const enviarReuniao = (e: FormEvent): void => {
    e.preventDefault();
    if (encaminhamentos.trim() === '') {
      mostrar('reuniao', { ok: false, erros: ['Escreva o que ficou combinado.'] });
      return;
    }
    const ok = registrar(
      'reuniao',
      () => {
        const r = registrarReuniao({
          municipio: id,
          data: dataReuniao,
          periodicidade,
          cronograma_confirmado: cronogramaConfirmado,
          encaminhamentos: encaminhamentos.trim(),
        });
        // A queixa do momento reservado é uma ocorrência própria (coleta 5), com a data da reunião.
        if (!r.ok || reservado === '') return r;
        return registrarOcorrencia({ municipio: id, origem: 'momento_reservado', tipo: reservado, data: dataReuniao });
      },
      `Reunião de escuta registrada para ${nome}.`,
      reservado !== '',
    );
    if (!ok) return;
    anotar(
      `${formatarDia(dataReuniao)} · Reunião de escuta ${periodicidade} · ${nome}${reservado === '' ? '' : ' · com queixa no momento reservado'}`,
    );
    setEncaminhamentos('');
    setReservado('');
  };

  const enviarObservacao = (e: FormEvent): void => {
    e.preventDefault();
    const erros: string[] = [];
    if (!escolhido) erros.push('Escolha um município da lista.');
    if (observado.trim() === '') erros.push('Escreva o que foi observado.');
    if (dataObservacao === '' || dataObservacao > hoje) erros.push(`Informe uma data até hoje (${formatarDia(hoje)}).`);
    else if (dataObservacao < periodo.inicio) {
      erros.push(`A data precisa ser do ciclo atual: de ${formatarDia(periodo.inicio)} até hoje (${formatarDia(hoje)}).`);
    }
    if (erros.length > 0) {
      mostrar('observacao', { ok: false, erros });
      return;
    }
    setRetornos((atuais) => ({ ...atuais, observacao: null }));
    anotar(`${formatarDia(dataObservacao)} · Observação de formação · ${nome} · ${comoFoi}: ${observado.trim()}`);
    setObservado('');
  };

  const relatoriosDoCiclo = dados.relatorios
    .filter((r) => periodo.meses.includes(r.mes))
    .sort((a, b) => a.mes.localeCompare(b.mes) || a.municipio - b.municipio);
  const baixarPlanilha = (): void =>
    baixarCsv(
      `semaforo_relatorios_${dados.ciclo_atual}.csv`,
      [
        'Mês',
        'Município',
        'UF',
        'Coordenador',
        'Formações previstas',
        'Formações realizadas',
        'Visitas previstas',
        'Visitas realizadas',
        'Cumprido (%)',
      ],
      relatoriosDoCiclo.map((r) => {
        const m = dados.municipios.find((x) => x.id === r.municipio);
        const cumprido = percentualCronograma([r]);
        return [
          mesAno(r.mes),
          m?.nome ?? '',
          m?.uf ?? '',
          dados.coordenadores.find((c) => c.id === r.coordenador)?.nome ?? '',
          r.formacoes_previstas,
          r.formacoes_realizadas,
          r.visitas_previstas,
          r.visitas_realizadas,
          cumprido === null ? '' : Math.round(cumprido),
        ];
      }),
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
        formação fica só na lista &ldquo;Registrado nesta sessão&rdquo;. As datas ficam no ciclo atual, de{' '}
        {formatarDia(periodo.inicio)} até hoje. Sair do Semáforo ou recarregar a página apaga tudo.
      </p>
      <BotoesExportar aoBaixarPlanilha={baixarPlanilha} />
      <p className="mb-4 text-sm">
        A planilha traz os {relatoriosDoCiclo.length} relatórios mensais do ciclo{' '}
        {dados.ciclo_atual} ({mesesDoCiclo(dados.ciclo_atual)}), com os desta sessão.
      </p>

      <div className="mb-6 max-w-xl">
        <CampoMunicipio id="relatorio-municipio" valor={municipio} aoMudar={setMunicipio} />
        {escolhido && situacao && (
          <div className="mt-2 space-y-1 text-sm">
            <p className="m-0">{coordenador ? `Coordenador: ${coordenador.nome}` : 'Sem coordenador: não há relatório mensal.'}</p>
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
          nota="Na versão real, o coordenador preenche numa tela à parte, fora da Integra. Formações e visitas realizadas sobre as previstas dão o cronograma cumprido. Registrar o mesmo mês de novo substitui o anterior."
          aoEnviar={enviarRelatorio}
          botao="Registrar relatório"
          retorno={retornos.relatorio ?? null}
          para={nome}
        >
          <Campo id="relatorio-mes" rotulo="Mês">
            <select id="relatorio-mes" className={CLASSE_CAMPO} value={mes} onChange={(e) => setMes(e.target.value)}>
              {meses.map((m) => (
                <option key={m} value={m}>
                  {mesAno(m)}
                </option>
              ))}
            </select>
          </Campo>
          {relatorioDoMes && (
            <p className="m-0 text-sm">
              Já entregue para {mesAno(mes)}: {relatorioDoMes.formacoes_realizadas} de {relatorioDoMes.formacoes_previstas}{' '}
              formações e {relatorioDoMes.visitas_realizadas} de {relatorioDoMes.visitas_previstas} visitas.
            </p>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            {(
              [
                ['relatorio-fp', 'Formações previstas', formacoesPrevistas, setFormacoesPrevistas],
                ['relatorio-fr', 'Formações realizadas', formacoesRealizadas, setFormacoesRealizadas],
                ['relatorio-vp', 'Visitas previstas', visitasPrevistas, setVisitasPrevistas],
                ['relatorio-vr', 'Visitas realizadas', visitasRealizadas, setVisitasRealizadas],
              ] as const
            ).map(([campo, rotulo, valor, mudar]) => (
              <Campo key={campo} id={campo} rotulo={rotulo}>
                <input
                  id={campo}
                  type="number"
                  min={0}
                  step={1}
                  inputMode="numeric"
                  className={CLASSE_CAMPO}
                  value={valor}
                  onChange={(e) => mudar(e.target.value)}
                />
              </Campo>
            ))}
          </div>
        </Secao>

        <Secao
          id="form-ocorrencia"
          titulo="Ocorrência"
          nota="Na versão real, Relacionamento, Comercial e distribuidores registram por link, sem conta (o distribuidor registra pelo Comercial). Uma reclamação deixa a cor sugerida em vermelho na hora; a cor em vigor muda quando o Comitê publicar (ver Para validar no dia 7)."
          aoEnviar={enviarOcorrencia}
          botao="Registrar ocorrência"
          retorno={retornos.ocorrencia ?? null}
          para={nome}
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
        </Secao>

        <Secao
          id="form-reuniao"
          titulo="Reunião de escuta"
          nota="A cada 6 meses no verde e a cada 3 meses no amarelo e no vermelho."
          aoEnviar={enviarReuniao}
          botao="Registrar reunião"
          retorno={retornos.reuniao ?? null}
          para={nome}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo id="reuniao-data" rotulo="Data">
              <input
                id="reuniao-data"
                type="date"
                min={periodo.inicio}
                max={hoje}
                className={CLASSE_CAMPO}
                value={dataReuniao}
                onChange={(e) => setDataReuniao(e.target.value)}
              />
            </Campo>
            <Campo id="reuniao-periodicidade" rotulo="Periodicidade">
              <select
                id="reuniao-periodicidade"
                className={CLASSE_CAMPO}
                value={periodicidade}
                onChange={(e) => setPeriodicidade(e.target.value as 'semestral' | 'trimestral')}
              >
                <option value="semestral">Semestral (verde)</option>
                <option value="trimestral">Trimestral (amarelo ou vermelho)</option>
              </select>
            </Campo>
          </div>
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
              Na versão real, o momento reservado é confidencial: o coordenador do município e a Gestão Operacional nunca
              veem o que for registrado aqui. Quem vê está em &ldquo;Quem vê o quê&rdquo;, na página Para validar no dia 7.
              No protótipo, quem entra na Integra vê tudo.
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
          </fieldset>
        </Secao>

        <Secao
          id="form-observacao"
          titulo="Observação de formação"
          nota="A gestora observa uma formação (tarefa do amarelo). Não é um dos 5 indicadores e não muda a cor; na demonstração, fica só na lista do que foi registrado nesta sessão. Na versão real, vai para o PDI do coordenador na Plataforma DFF; se ela nasce aqui ou na DFF está em Para validar no dia 7."
          aoEnviar={enviarObservacao}
          botao="Registrar observação"
          retorno={retornos.observacao ?? null}
          para={nome}
        >
          <Campo id="observacao-data" rotulo="Data">
            <input
              id="observacao-data"
              type="date"
              min={periodo.inicio}
              max={hoje}
              className={CLASSE_CAMPO}
              value={dataObservacao}
              onChange={(e) => setDataObservacao(e.target.value)}
            />
          </Campo>
          <fieldset className="m-0 rounded border border-[#d9d9d9] p-3">
            <legend className="px-1 font-semibold">Como foi a formação</legend>
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {COMO_FOI.map((c) => (
                <label key={c} className="flex items-center gap-1">
                  <input
                    type="radio"
                    name="observacao-como-foi"
                    className={CLASSE_MARCA}
                    checked={comoFoi === c}
                    onChange={() => setComoFoi(c)}
                  />
                  {c}
                </label>
              ))}
            </div>
          </fieldset>
          <Campo id="observacao-texto" rotulo="O que foi observado">
            <textarea
              id="observacao-texto"
              rows={2}
              className={CLASSE_CAMPO}
              value={observado}
              onChange={(e) => setObservado(e.target.value)}
            />
          </Campo>
        </Secao>
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
