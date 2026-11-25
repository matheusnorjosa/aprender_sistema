/**
 * Semáforo — Ficha do município (DADOS SIMULADOS).
 *
 * Quem responde pelo município, a cor em vigor e a sugerida agora; os 5 indicadores do ciclo atual com
 * valor, cor e limites; o histórico dos 6 ciclos fechados (linha do tempo e tabela); as tarefas com o
 * prazo (vence hoje e vencidas primeiro); as ocorrências e as reuniões de escuta.
 * Requisitos: Requisitos_Modulo_Semaforo_Risco_Municipal.pdf, seções 3 a 7.
 */
import type { JSX, ReactNode } from 'react';
import { Link, useLocation, useParams } from 'react-router';
import { Alert, Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { formatarDia } from '../ica/componentes/estilos';
import { AvisoQuemVe } from './componentes/PecasDoRegistro';
import { CorComNome, EtiquetaPrazo, Mudanca } from './componentes/PecasDoAcompanhamento';
import { cicloAnterior, mesesCurtosDoCiclo, mesesDoCiclo, type CicloAvaliado, type ReuniaoEscuta } from './dados';
import {
  estadoDaTarefa,
  explicarCor,
  LIMITES,
  RESPOSTA_POR_COR,
  ROTULO_COR,
  ROTULO_INDICADOR,
  ROTULO_ORIGEM,
  textoSemDado,
} from './regras';
import { useSemaforoDemo } from './SemaforoDemoContext';
import type { AvaliacaoIndicador, Cor, EstadoTarefa, Ocorrencia, TarefaResposta } from './tipos';
import { voltarDaFicha } from './voltarDaFicha';

const { Title } = Typography;

const TITULO = { fontSize: 20 } as const;

const ORDEM_ESTADO: Record<EstadoTarefa, number> = { vence_hoje: 0, vencida: 1, no_prazo: 2, concluida: 3 };

interface LinhaHistorico {
  c: CicloAvaliado;
  anterior: Cor | null;
}

/** Nome visível da tabela fica no título da seção; a legenda da tabela diz o mesmo para o leitor de tela. */
function Legenda({ children }: { children: ReactNode }): JSX.Element {
  return <span className="sr-only">{children}</span>;
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
  const coordenador = dados.coordenadores.find((c) => c.id === m.coordenador);
  const gestora = dados.pessoas.find((p) => p.id === m.gestora_referencia);
  const atual = s.ciclos.at(-1)!;
  const r = atual.resultado;
  const anteriorPublicada = s.ciclos.at(-2)?.decisao?.cor_publicada ?? null;
  const resposta = RESPOSTA_POR_COR[s.cor_vigente];
  const semDado = textoSemDado(r);

  const fechados: LinhaHistorico[] = s.ciclos
    .slice(0, -1)
    .map((c, i, todos) => ({ c, anterior: todos[i - 1]?.decisao?.cor_publicada ?? null }));

  const tarefas = dados.tarefas
    .filter((t) => t.municipio === m.id)
    .map((t) => ({ t, estado: estadoDaTarefa(t, hoje) }))
    .sort(
      (a, b) =>
        ORDEM_ESTADO[a.estado] - ORDEM_ESTADO[b.estado] ||
        (a.estado === 'concluida' ? b.t.prazo_em.localeCompare(a.t.prazo_em) : a.t.prazo_em.localeCompare(b.t.prazo_em)),
    )
    .map(({ t }) => t);
  const ocorrencias = dados.ocorrencias.filter((o) => o.municipio === m.id).sort((a, b) => b.data.localeCompare(a.data));
  const reunioes = dados.reunioes.filter((x) => x.municipio === m.id).sort((a, b) => b.data.localeCompare(a.data));

  const colunasIndicadores: ColunaResponsiva<AvaliacaoIndicador>[] = [
    { title: 'Indicador', key: 'indicador', className: 'break-words', render: (_v, a) => ROTULO_INDICADOR[a.indicador] },
    { title: 'Valor', key: 'valor', className: 'break-words', render: (_v, a) => a.texto },
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
    { title: 'Tarefa', key: 'tarefa', className: 'break-words', render: (_v, t) => t.titulo },
    { title: 'Prazo', key: 'prazo', width: 105, render: (_v, t) => formatarDia(t.prazo_em) },
    { title: 'Situação', key: 'situacao', className: 'break-words', render: (_v, t) => <EtiquetaPrazo tarefa={t} hoje={hoje} /> },
    { title: 'Da cor', key: 'cor', width: 110, responsive: VISIVEL_A_PARTIR.sm, render: (_v, t) => <CorComNome cor={t.cor} /> },
    { title: 'Criada em', key: 'criada', width: 105, responsive: VISIVEL_A_PARTIR.md, render: (_v, t) => formatarDia(t.criada_em) },
  ];

  const colunasOcorrencias: ColunaResponsiva<Ocorrencia>[] = [
    { title: 'Data', key: 'data', width: 105, render: (_v, o) => formatarDia(o.data) },
    { title: 'Tipo', key: 'tipo', width: 110, render: (_v, o) => (o.tipo === 'reclamacao' ? 'Reclamação' : 'Leve') },
    { title: 'Origem', key: 'origem', className: 'break-words', render: (_v, o) => ROTULO_ORIGEM[o.origem] },
  ];

  const colunasReunioes: ColunaResponsiva<ReuniaoEscuta>[] = [
    { title: 'Data', key: 'data', width: 105, render: (_v, x) => formatarDia(x.data) },
    { title: 'Periodicidade', key: 'periodicidade', render: (_v, x) => (x.periodicidade === 'semestral' ? 'Semestral' : 'Trimestral') },
    {
      title: 'Cronograma confirmado',
      key: 'cronograma',
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_v, x) => (x.cronograma_confirmado ? 'Sim' : 'Não'),
    },
    { title: 'Encaminhamentos', key: 'encaminhamentos', className: 'break-words', responsive: VISIVEL_A_PARTIR.md, render: (_v, x) => x.encaminhamentos },
  ];

  return (
    <section aria-labelledby="semaforo-ficha-titulo">
      {cabecalho}
      <Title level={2} style={{ fontSize: 22, marginTop: 0 }}>
        {m.nome}-{m.uf}
      </Title>
      <p className="m-0">
        {coordenador
          ? `Coordenador: ${coordenador.nome}`
          : 'Sem coordenador: o relatório mensal não chega e o cronograma fica sem dado.'}
      </p>
      <p>Gestora de referência: {gestora?.nome ?? 'não definida'}</p>

      <ul aria-label="Situação atual" className="m-0 mb-4 grid list-none gap-2 p-0 md:grid-cols-3">
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          <CorComNome cor={s.cor_vigente} rotulo="Em vigor" />
          {s.decisao_vigente &&
            ` publicada em ${formatarDia(s.decisao_vigente.publicada_em)} (ciclo ${s.decisao_vigente.ciclo}, ${mesesDoCiclo(s.decisao_vigente.ciclo)})`}
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
      </section>

      <section aria-labelledby="semaforo-ficha-tarefas" className="mb-6">
        <Title level={3} id="semaforo-ficha-tarefas" style={TITULO}>
          Tarefas e prazos
        </Title>
        <ResponsiveTable<TarefaResposta>
          caption={<Legenda>Tarefas e prazos, o que vence hoje primeiro</Legenda>}
          rowKey={(t) => `${t.chave}-${t.criada_em}`}
          columns={colunasTarefas}
          dataSource={tarefas}
          pagination={false}
          locale={{ emptyText: 'Nenhuma tarefa: o município nunca saiu do verde.' }}
          nomeDaLinha={(t) => t.titulo}
        />
      </section>

      <section aria-labelledby="semaforo-ficha-ocorrencias" className="mb-6">
        <Title level={3} id="semaforo-ficha-ocorrencias" style={TITULO}>
          Ocorrências
        </Title>
        <ResponsiveTable<Ocorrencia>
          caption={<Legenda>Ocorrências registradas</Legenda>}
          rowKey="id"
          columns={colunasOcorrencias}
          dataSource={ocorrencias}
          pagination={false}
          locale={{ emptyText: 'Nenhuma ocorrência registrada.' }}
          nomeDaLinha={(o) => `ocorrência de ${formatarDia(o.data)}`}
        />
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
