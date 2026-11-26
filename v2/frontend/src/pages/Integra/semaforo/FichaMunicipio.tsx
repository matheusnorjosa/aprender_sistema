/**
 * Semáforo — Ficha do município (DADOS SIMULADOS).
 *
 * Quem responde pelo município, a cor em vigor e a sugerida agora; os projetos do município, cada um com o
 * seu coordenador, articulador, cronograma e pesquisa (decisões 46 e 51); os 5 indicadores do ciclo atual com
 * valor, cor e limites (a nota de recomendação com a maior, a menor e a média: decisão 31); o histórico dos 6
 * ciclos fechados (linha do tempo e tabela) e todas as decisões em ordem, inclusive o vermelho na hora que o Comitê
 * confirmou ou desfez (decisão 57); as tarefas com o prazo (vence hoje e vencidas primeiro; as
 * canceladas e as substituídas ficam na lista com o estado: decisões 42, 43 e 57); as ocorrências por ano, com
 * a hora e a resposta (decisões 32, 50 e 57); e as reuniões de escuta com a situação da ata (decisão 48).
 * Requisitos: Requisitos_Modulo_Semaforo_Risco_Municipal.pdf, seções 3 a 7.
 */
import type { JSX, ReactNode } from 'react';
import { Link, useLocation, useParams } from 'react-router';
import { Alert, Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { formatarDia } from '../ica/componentes/estilos';
import { AvisoQuemVe } from './componentes/PecasDoRegistro';
import { CorComNome, EtiquetaPrazo, Mudanca } from './componentes/PecasDoAcompanhamento';
import {
  cicloAnterior,
  mesesCurtosDoCiclo,
  mesesDoCiclo,
  periodoDoCiclo,
  valoresPorProjeto,
  type CicloAvaliado,
  type ReuniaoEscuta,
} from './dados';
import {
  corCronograma,
  duasCasas,
  estadoDaTarefa,
  explicarCor,
  horasEntre,
  inicioDasFormacoesNoAno,
  LIMITES,
  META_RESPOSTA_HORAS,
  ocorrenciasDoAno,
  RESPOSTA_POR_COR,
  resumoNps,
  ROTULO_COR,
  ROTULO_INDICADOR,
  ROTULO_ORIGEM,
  textoDaReuniao,
  textoDataHora,
  textoHoras,
  textoResumoNps,
  textoSemDado,
} from './regras';
import { useSemaforoDemo } from './SemaforoDemoContext';
import type { AvaliacaoIndicador, Cor, DecisaoComite, EstadoTarefa, Ocorrencia, OrigemDecisao, TarefaResposta } from './tipos';
import { voltarDaFicha } from './voltarDaFicha';

const { Title } = Typography;

const TITULO = { fontSize: 20 } as const;

const ORDEM_ESTADO: Record<EstadoTarefa, number> = {
  vence_hoje: 0,
  vencida: 1,
  no_prazo: 2,
  concluida: 3,
  cancelada_comite: 4,
  substituida: 5,
};

interface LinhaHistorico {
  c: CicloAvaliado;
  anterior: Cor | null;
}

/** Quem publicou a decisão, na lista de todas as decisões. */
const POR_QUEM: Record<OrigemDecisao, string> = {
  vermelho_automatico: 'vermelho na hora',
  comite_ordinario: 'Comitê ordinário',
  comite_extraordinario: 'Comitê extraordinário',
};

/** Depois de um vermelho na hora no mesmo ciclo, a decisão do Comitê o confirmou ou o desfez (decisões 38 e 42). */
function relacaoComAnterior(d: DecisaoComite, anterior: DecisaoComite | undefined): string {
  if (anterior?.origem !== 'vermelho_automatico' || anterior.ciclo !== d.ciclo || d.origem === 'vermelho_automatico') return '';
  return d.cor_publicada === 'vermelho' ? ', confirmou o vermelho na hora' : ', desfez o vermelho na hora';
}

/** Nome visível da tabela fica no título da seção; a legenda da tabela diz o mesmo para o leitor de tela. */
function Legenda({ children }: { children: ReactNode }): JSX.Element {
  return <span className="sr-only">{children}</span>;
}

/** "02/12/2026 às 16:15, em 54 h: fora da meta de 48 h" (decisão 50); sem resposta, "Sem resposta". */
function textoResposta(o: Ocorrencia): string {
  if (o.respondida_em === null) return 'Sem resposta';
  const horas = horasEntre(o.registrada_em, o.respondida_em);
  const meta = horas <= META_RESPOSTA_HORAS ? 'dentro da meta' : 'fora da meta';
  return `${textoDataHora(o.respondida_em)}, em ${textoHoras(horas)}: ${meta} de ${META_RESPOSTA_HORAS} h`;
}

/** Volta para a tela de onde a ficha foi aberta (`voltarDaFicha.ts`); sem origem, para o Comitê. */
function Voltar(): JSX.Element {
  const { para, rotulo } = voltarDaFicha(useLocation().state);
  return (
    <p className="mt-4">
      <Link to={para}>{rotulo}</Link>
    </p>
  );
}

export default function FichaMunicipio(): JSX.Element {
  const { id } = useParams();
  const { dados, situacoes } = useSemaforoDemo();
  const s = situacoes.find((x) => String(x.municipio) === id);
  const m = dados.municipios.find((x) => String(x.id) === id);

  const cabecalho = (
    <>
      <Title level={1} id="semaforo-ficha-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
        Ficha do município
      </Title>
      <AvisoQuemVe tela="municipio" />
    </>
  );

  if (!s || !m) {
    return (
      <section aria-labelledby="semaforo-ficha-titulo">
        {cabecalho}
        <Alert type="warning" showIcon message="Município não encontrado." />
        <Voltar />
      </section>
    );
  }

  const hoje = dados.data_referencia;
  const nome = `${m.nome}-${m.uf}`;
  const gestora = dados.pessoas.find((p) => p.id === m.gestora_referencia);
  const atual = s.ciclos.at(-1)!;
  const { prazo_pesquisa } = periodoDoCiclo(atual.ciclo);
  const respostasDoCiclo = dados.respostas.filter((x) => x.municipio === m.id && x.ciclo === atual.ciclo && x.respondida_em <= hoje);
  const npsDoMunicipio = resumoNps(respostasDoCiclo);
  const porProjeto = valoresPorProjeto(dados, m.id, atual.ciclo, hoje);
  const r = atual.resultado;
  const anteriorPublicada = s.ciclos.at(-2)?.decisao?.cor_publicada ?? null;
  const resposta = RESPOSTA_POR_COR[s.cor_vigente];
  const semDado = textoSemDado(r);

  // Rodada 4: o ciclo de antes do primeiro projeto do município não tem coleta nem cor, e fica fora do histórico.
  const antesDoProjeto = s.ciclos.filter((c) => c.antes_do_projeto);
  const fechados: LinhaHistorico[] = s.ciclos
    .slice(0, -1)
    .filter((c) => !c.antes_do_projeto)
    .map((c, i, todos) => ({ c, anterior: todos[i - 1]?.decisao?.cor_publicada ?? null }));
  const primeiroCiclo = s.ciclos.find((c) => !c.antes_do_projeto)?.ciclo;

  const tarefas = dados.tarefas
    .filter((t) => t.municipio === m.id)
    .map((t) => ({ t, estado: estadoDaTarefa(t, hoje) }))
    .sort(
      (a, b) =>
        ORDEM_ESTADO[a.estado] - ORDEM_ESTADO[b.estado] ||
        (a.estado === 'concluida' ? b.t.prazo_em.localeCompare(a.t.prazo_em) : a.t.prazo_em.localeCompare(b.t.prazo_em)),
    )
    .map(({ t }) => t);
  // Decisões 32 e 57: as ocorrências contam desde a 1ª formação do ano; as de antes e as dos anos anteriores ficam na
  // ficha, só não contam na cor.
  const ocorrencias = dados.ocorrencias
    .filter((o) => o.municipio === m.id)
    .sort((a, b) => b.registrada_em.localeCompare(a.registrada_em));
  const relatoriosDoMunicipio = dados.relatorios.filter((x) => x.municipio === m.id);
  const contamNaCor = new Set(ocorrenciasDoAno(ocorrencias, relatoriosDoMunicipio, hoje).map((o) => o.id));
  const anoAtual = hoje.slice(0, 4);
  const inicioDoAno = inicioDasFormacoesNoAno(relatoriosDoMunicipio, Number(anoAtual));
  const anos = [...new Set([anoAtual, ...ocorrencias.map((o) => o.data.slice(0, 4))])].sort().reverse();
  const reunioes = dados.reunioes.filter((x) => x.municipio === m.id).sort((a, b) => b.data.localeCompare(a.data));
  // Decisão 57: a tabela dos ciclos mostra a última decisão de cada ciclo; esta lista guarda todas, em ordem.
  const decisoes = dados.decisoes.filter((d) => d.municipio === m.id);

  // Decisão 31: a nota de recomendação mostra a maior, a menor e a média; a cor sai da média.
  const valorDo = (a: AvaliacaoIndicador): string => (a.indicador === 'nps' && npsDoMunicipio ? textoResumoNps(npsDoMunicipio) : a.texto);
  const colunasIndicadores: ColunaResponsiva<AvaliacaoIndicador>[] = [
    // Rodada 4: abaixo de 576 px, o Valor vai para a célula do nome, que fica com a linha quase toda: a 360 px,
    // "Relacionamento" quebrava no meio da palavra.
    {
      title: 'Indicador',
      key: 'indicador',
      className: 'break-words',
      render: (_v, a) => (
        <>
          <span className="block">{ROTULO_INDICADOR[a.indicador]}</span>
          <span className="block text-sm sm:hidden">Valor: {valorDo(a)}</span>
        </>
      ),
    },
    { title: 'Valor', key: 'valor', className: 'break-words', responsive: VISIVEL_A_PARTIR.sm, render: (_v, a) => valorDo(a) },
    { title: 'Cor', key: 'cor', width: 110, render: (_v, a) => <CorComNome cor={a.cor} /> },
    {
      title: 'Limites',
      key: 'limites',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_v, a) => (
        <ul className="m-0 list-none p-0 text-sm">
          {(['verde', 'amarelo', 'vermelho'] as const).map((c) => (
            <li key={c}>
              {ROTULO_COR[c]}: {LIMITES[a.indicador][c]}
            </li>
          ))}
        </ul>
      ),
    },
  ];

  const colunasHistorico: ColunaResponsiva<LinhaHistorico>[] = [
    // A 360 px sobram 312 px: Ciclo sem largura fixa (quebra a linha) e 40 + 96 + 96 px para o resto.
    { title: 'Ciclo', key: 'ciclo', className: 'break-words', render: (_v, l) => `${l.c.ciclo} (${mesesCurtosDoCiclo(l.c.ciclo)})` },
    { title: 'Sugerida', key: 'sugerida', width: 96, render: (_v, l) => <CorComNome cor={l.c.resultado.cor} /> },
    {
      title: 'Publicada',
      key: 'publicada',
      width: 96,
      render: (_v, l) => (l.c.decisao ? <CorComNome cor={l.c.decisao.cor_publicada} /> : 'Não publicada'),
    },
    {
      title: 'Mudança',
      key: 'mudanca',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_v, l) => (l.c.decisao ? <Mudanca anterior={l.anterior} atual={l.c.decisao.cor_publicada} /> : '—'),
    },
    {
      title: 'Justificativa do Comitê',
      key: 'justificativa',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_v, l) => l.c.decisao?.justificativa ?? '—',
    },
  ];

  const colunasTarefas: ColunaResponsiva<TarefaResposta>[] = [
    // Rodada 4: abaixo de 576 px, o Prazo vai para a célula da tarefa, que fica com o espaço dele: com 56 px de texto,
    // "articulador" e "Observação" quebravam no meio da palavra.
    {
      title: 'Tarefa',
      key: 'tarefa',
      className: 'break-words',
      render: (_v, t) => (
        <>
          <span className="block">{t.titulo}</span>
          <span className="block text-sm sm:hidden">Prazo: {formatarDia(t.prazo_em)}</span>
        </>
      ),
    },
    // Rodada 3, medido a 360 px: a etiqueta com a data ("Substituída em 06/03/2026") pede 88 px e vazava a coluna
    // automática; Situação fica com 104 px e o Prazo (só a data) com 96 px, e a Tarefa fica com o resto.
    { title: 'Prazo', key: 'prazo', width: 96, responsive: VISIVEL_A_PARTIR.sm, render: (_v, t) => formatarDia(t.prazo_em) },
    { title: 'Situação', key: 'situacao', width: 104, render: (_v, t) => <EtiquetaPrazo tarefa={t} hoje={hoje} /> },
    { title: 'Da cor', key: 'cor', width: 110, responsive: VISIVEL_A_PARTIR.sm, render: (_v, t) => <CorComNome cor={t.cor} /> },
    { title: 'Criada em', key: 'criada', width: 105, responsive: VISIVEL_A_PARTIR.md, render: (_v, t) => formatarDia(t.criada_em) },
  ];

  const colunasOcorrencias: ColunaResponsiva<Ocorrencia>[] = [
    // A 360 px, o dia e a hora em linhas separadas, e 'Tipo' com 96 px: a data cabe inteira, sem quebrar no meio.
    {
      title: 'Registrada em',
      key: 'data',
      className: 'break-words',
      // A queixa do momento reservado chega com a ata: o registro pode ser dias depois da reunião (rodada 3).
      render: (_v, o) => (
        <>
          <span className="block">{formatarDia(o.registrada_em.slice(0, 10))}</span>{' '}
          <span className="block">às {o.registrada_em.slice(11, 16)}</span>
          {o.data !== o.registrada_em.slice(0, 10) && <span className="block text-sm"> feita em {formatarDia(o.data)}</span>}
        </>
      ),
    },
    { title: 'Tipo', key: 'tipo', width: 96, render: (_v, o) => (o.tipo === 'reclamacao' ? 'Reclamação' : 'Leve') },
    { title: 'Origem', key: 'origem', className: 'break-words', responsive: VISIVEL_A_PARTIR.md, render: (_v, o) => ROTULO_ORIGEM[o.origem] },
    { title: 'Respondida em', key: 'resposta', className: 'break-words', responsive: VISIVEL_A_PARTIR.sm, render: (_v, o) => textoResposta(o) },
    { title: 'Conta na cor', key: 'conta', width: 80, render: (_v, o) => (contamNaCor.has(o.id) ? 'Sim' : 'Não') },
  ];

  const colunasReunioes: ColunaResponsiva<ReuniaoEscuta>[] = [
    { title: 'Data', key: 'data', width: 105, render: (_v, x) => formatarDia(x.data) },
    {
      title: 'Periodicidade',
      key: 'periodicidade',
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_v, x) => (x.periodicidade === 'semestral' ? 'Semestral' : 'Trimestral'),
    },
    // Decisão 48: marcada antes, ata até 5 dias úteis depois.
    { title: 'Ata', key: 'ata', className: 'break-words', render: (_v, x) => textoDaReuniao(x, hoje) },
    {
      title: 'Cronograma confirmado',
      key: 'cronograma',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_v, x) => (x.ata_em === null ? '—' : x.cronograma_confirmado ? 'Sim' : 'Não'),
    },
    {
      title: 'Encaminhamentos',
      key: 'encaminhamentos',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_v, x) => (x.encaminhamentos === '' ? '—' : x.encaminhamentos),
    },
  ];

  return (
    <section aria-labelledby="semaforo-ficha-titulo">
      {cabecalho}
      <Title level={2} style={{ fontSize: 22, marginTop: 0 }}>
        {nome}
      </Title>
      <p>Gestora de referência: {gestora?.nome ?? 'não definida'}</p>

      <ul aria-label="Situação atual" className="m-0 mb-4 grid list-none gap-2 p-0 md:grid-cols-3">
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          <CorComNome cor={s.cor_vigente} rotulo="Em vigor" />
          {/* Decisão 38: o vermelho na hora já vale, mas o Comitê ainda confirma ou desfaz. */}
          {s.decisao_vigente &&
            `${s.aguardando_comite ? ' na hora desde' : ' publicada em'} ${formatarDia(s.decisao_vigente.publicada_em)} (ciclo ${s.decisao_vigente.ciclo}, ${mesesDoCiclo(s.decisao_vigente.ciclo)})`}
          {s.aguardando_comite && ': as tarefas do vermelho começaram; o Comitê confirma ou desfaz.'}
        </li>
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          <CorComNome cor={r.cor} rotulo="Sugerida agora" /> (ciclo {atual.ciclo}, {mesesDoCiclo(atual.ciclo)}). {explicarCor(r)}
        </li>
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          Desde o ciclo {cicloAnterior(atual.ciclo)} ({mesesDoCiclo(cicloAnterior(atual.ciclo))}):{' '}
          <Mudanca anterior={anteriorPublicada} atual={atual.decisao?.cor_publicada ?? r.cor} />
        </li>
      </ul>
      <p className="text-sm">
        Com a cor em vigor, quem age: {resposta.quem_age}. O que fazer: {resposta.o_que_fazer}.
      </p>

      <section aria-labelledby="semaforo-ficha-projetos" className="mb-6">
        <Title level={3} id="semaforo-ficha-projetos" style={TITULO}>
          Projetos
        </Title>
        <p className="text-sm">
          Cada projeto da Aprender Editora contratado pelo município tem o seu coordenador, o seu relatório mensal e a
          sua pesquisa. Ciclo {atual.ciclo}, com os dados até hoje.
          {m.projetos.length > 1 &&
            ' Com mais de um projeto, a média e o NPS do município juntam as respostas de todos; no cronograma e na resposta à pesquisa, na cor do município entra o pior projeto.'}
        </p>
        <ul aria-label={`Projetos de ${nome}`} className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
          {m.projetos.map((p) => {
            const v = porProjeto.find((x) => x.projeto === p.id);
            const coordenador = dados.coordenadores.find((c) => c.id === p.coordenador);
            const nps = resumoNps(respostasDoCiclo.filter((x) => x.projeto === p.id));
            const respondeu = v?.resposta_pesquisa.ciclo_atual ?? null;
            return (
              <li key={p.id} className="rounded border border-[#d9d9d9] bg-white p-3 text-sm">
                <strong className="block text-base">{p.nome}</strong>
                <span className="block">
                  {coordenador
                    ? `Coordenador: ${coordenador.nome}`
                    : 'Sem coordenador: o relatório mensal deste projeto não chega e o cronograma dele fica sem dado.'}
                </span>
                <span className="block">Quem responde a pesquisa: {p.articulador}</span>
                <span className="block">
                  Cronograma cumprido:{' '}
                  {v?.cronograma == null ? (
                    'Sem dado'
                  ) : (
                    <>
                      {duasCasas(v.cronograma)}% · <CorComNome cor={corCronograma(v.cronograma)} />
                    </>
                  )}
                </span>
                <span className="block">
                  Pesquisa:{' '}
                  {v?.media_pesquisa == null || !nps
                    ? `sem resposta neste ciclo${respondeu === false ? ' (não respondeu no prazo)' : ` (prazo até ${formatarDia(prazo_pesquisa)})`}`
                    : `média ${duasCasas(v.media_pesquisa)} · NPS: ${textoResumoNps(nps)}`}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="semaforo-ficha-indicadores" className="mb-6">
        <Title level={3} id="semaforo-ficha-indicadores" style={TITULO}>
          Indicadores do ciclo {atual.ciclo} ({mesesDoCiclo(atual.ciclo)})
        </Title>
        <p className="text-sm">Com os dados até hoje ({formatarDia(hoje)}).</p>
        <ResponsiveTable<AvaliacaoIndicador>
          caption={
            <Legenda>
              Indicadores do ciclo {atual.ciclo} ({mesesDoCiclo(atual.ciclo)}), com os dados até {formatarDia(hoje)}
            </Legenda>
          }
          rowKey="indicador"
          columns={colunasIndicadores}
          dataSource={r.avaliacoes}
          pagination={false}
          nomeDaLinha={(a) => ROTULO_INDICADOR[a.indicador]}
        />
        {semDado && <p className="mt-2 text-sm">{semDado}</p>}
      </section>

      <section aria-labelledby="semaforo-ficha-historico" className="mb-6">
        <Title level={3} id="semaforo-ficha-historico" style={TITULO}>
          Histórico dos {fechados.length} ciclos
        </Title>
        {antesDoProjeto.length > 0 && primeiroCiclo && (
          <p className="text-sm">
            O projeto do município começou no ciclo {primeiroCiclo} ({mesesDoCiclo(primeiroCiclo)}): os {antesDoProjeto.length} ciclos
            de antes não têm coleta nem cor.
          </p>
        )}
        <ol aria-hidden="true" className="m-0 mb-3 grid list-none grid-cols-3 gap-1 p-0 sm:grid-cols-6">
          {fechados.map(({ c }) => (
            <li key={c.ciclo} className="rounded border border-[#d9d9d9] bg-white p-1 text-center text-xs">
              <span className="block">{c.ciclo}</span>
              <span className="mb-1 block">{mesesCurtosDoCiclo(c.ciclo)}</span>
              <CorComNome cor={c.decisao?.cor_publicada ?? c.resultado.cor} />
            </li>
          ))}
        </ol>
        <ResponsiveTable<LinhaHistorico>
          caption={<Legenda>Histórico dos {fechados.length} ciclos fechados: cor sugerida e cor publicada pelo Comitê</Legenda>}
          rowKey={(l) => l.c.ciclo}
          columns={colunasHistorico}
          dataSource={fechados}
          pagination={false}
          nomeDaLinha={(l) => `ciclo ${l.c.ciclo}`}
        />
        {decisoes.length > 0 && (
          <>
            <Title level={4} id="semaforo-ficha-decisoes" style={{ fontSize: 16, marginTop: 16 }}>
              Todas as decisões, em ordem
            </Title>
            <ol aria-labelledby="semaforo-ficha-decisoes" className="m-0 grid list-none gap-1 p-0 text-sm">
              {decisoes.map((d, i) => (
                <li key={`${d.publicada_em}-${d.origem}-${i}`}>
                  {formatarDia(d.publicada_em)} · ciclo {d.ciclo} ({mesesCurtosDoCiclo(d.ciclo)}) · <CorComNome cor={d.cor_publicada} /> ·{' '}
                  {POR_QUEM[d.origem]}
                  {relacaoComAnterior(d, decisoes[i - 1])}
                  {d.justificativa && ` · Justificativa: ${d.justificativa}`}
                </li>
              ))}
            </ol>
          </>
        )}
      </section>

      <section aria-labelledby="semaforo-ficha-tarefas" className="mb-6">
        <Title level={3} id="semaforo-ficha-tarefas" style={TITULO}>
          Tarefas e prazos
        </Title>
        <ResponsiveTable<TarefaResposta>
          caption={<Legenda>Tarefas e prazos, o que vence hoje primeiro</Legenda>}
          rowKey={(t) => t.id}
          columns={colunasTarefas}
          dataSource={tarefas}
          pagination={false}
          locale={{ emptyText: 'Nenhuma tarefa: o município nunca saiu do verde.' }}
          // As tarefas substituídas e canceladas ficam ao lado das novas, com o mesmo título (decisões 43 e 57).
          nomeDaLinha={(t) => `${t.titulo}, prazo ${formatarDia(t.prazo_em)}`}
        />
      </section>

      <section aria-labelledby="semaforo-ficha-ocorrencias" className="mb-6">
        <Title level={3} id="semaforo-ficha-ocorrencias" style={TITULO}>
          Ocorrências
        </Title>
        <p className="text-sm">
          A contagem zera em janeiro, mas nada é apagado: as ocorrências de todos os anos ficam aqui. A resposta ao
          município tem a meta de {META_RESPOSTA_HORAS} h corridas (sábado e domingo contam).
        </p>
        {anos.map((ano) => {
          const doAno = ocorrencias.filter((o) => o.data.startsWith(`${ano}-`));
          return (
            <section key={ano} aria-labelledby={`semaforo-ficha-ocorrencias-${ano}`} className="mb-4">
              {/* Rodada 4 (WCAG 2.4.6): quem salta pelos títulos ou pelas regiões ouve "Ocorrências de 2026", não só "2026". */}
              <Title level={4} id={`semaforo-ficha-ocorrencias-${ano}`} style={{ fontSize: 16 }}>
                <span className="sr-only">Ocorrências de</span> {ano}
              </Title>
              <p className="text-sm">
                {ano !== anoAtual
                  ? 'Ano anterior: não conta mais na cor; fica guardado no histórico.'
                  : inicioDoAno
                    ? `Contam na cor desde ${formatarDia(inicioDoAno)}, o mês da 1ª formação do ano no município.`
                    : 'Ainda não houve formação neste ano: nenhuma ocorrência conta na cor.'}
              </p>
              <ResponsiveTable<Ocorrencia>
                caption={<Legenda>Ocorrências de {ano}</Legenda>}
                rowKey="id"
                columns={colunasOcorrencias}
                dataSource={doAno}
                pagination={false}
                locale={{ emptyText: `Nenhuma ocorrência registrada em ${ano}.` }}
                nomeDaLinha={(o) => `ocorrência de ${textoDataHora(o.registrada_em)}`}
              />
            </section>
          );
        })}
      </section>

      <section aria-labelledby="semaforo-ficha-reunioes">
        <Title level={3} id="semaforo-ficha-reunioes" style={TITULO}>
          Reuniões de escuta
        </Title>
        <ResponsiveTable<ReuniaoEscuta>
          caption={<Legenda>Reuniões de escuta</Legenda>}
          rowKey="id"
          columns={colunasReunioes}
          dataSource={reunioes}
          pagination={false}
          locale={{ emptyText: 'Nenhuma reunião de escuta registrada.' }}
          nomeDaLinha={(x) => `reunião de ${formatarDia(x.data)}`}
        />
      </section>

      <Voltar />
    </section>
  );
}
