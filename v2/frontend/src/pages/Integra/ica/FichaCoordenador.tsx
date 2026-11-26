/**
 * ICA — Ficha do coordenador (DADOS SIMULADOS).
 *
 * ICA atual, estrato e variação desde o semestre anterior; contribuição de cada componente (barra
 * empilhada, com a legenda em texto e a tabela da conta); a carteira (municípios com coleções, turmas,
 * professores e deslocamento, "estimado" quando o município não tem localidade) e o histórico
 * semestral. Requisitos: Requisitos_Modulo_ICA.pdf, seção 5 ("Ficha do coordenador").
 */
import type { JSX } from 'react';
import { Link, useLocation, useParams } from 'react-router';
import { Alert, Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import { ROTULO_ATUACAO } from '../dados/tipos';
import {
  COMPONENTES,
  formatarHoras,
  META_ICA,
  ROTULO_COMPONENTE,
  variacaoDoIca,
  type ContaIca,
  type LinhaCarteira,
  type ResultadoCoordenador,
} from './calculo';
import { BarraIca, escalaDoGrafico } from './componentes/BarraIca';
import { EtiquetaEstrato, textoDoEstrato } from './componentes/EtiquetaEstrato';
import { FaixasLegendaCurta } from './componentes/FaixasLegenda';
import { TabelaComponentes } from './componentes/TabelaComponentes';
import { COR_COMPONENTE, formatarDia, formatarNumero, formatarVariacao } from './componentes/estilos';

const { Title } = Typography;

const TITULO = { fontSize: 20 } as const;

const AGORA = 'Agora (nesta demonstração)';

interface LinhaHistorico {
  semestre: string;
  /** Data do cálculo (AAAA-MM-DD); `null` = cálculo desta sessão. */
  calculadoEm: string | null;
  versao: string;
  r: ResultadoCoordenador | undefined;
}

/**
 * Barra empilhada: um pedaço por componente, do tamanho da contribuição (decorativa; a legenda e a
 * tabela dão os números). Os pedaços são mais baixos que a faixa, como na BarraIca: a linha da média
 * aparece acima e abaixo deles, no cinza claro, mesmo quando cai dentro de um pedaço escuro.
 */
function BarraEmpilhada({ conta }: { conta: ContaIca }): JSX.Element {
  const escala = escalaDoGrafico([conta.icaExibido]);
  return (
    <div aria-hidden="true" className="relative mb-2 h-8 w-full overflow-hidden rounded-sm bg-[#F0F0F0]">
      <div data-parte="pedacos" className="absolute inset-x-0 inset-y-1.5 flex">
        {COMPONENTES.filter((c) => conta.contribuicoes[c] > 0).map((c) => (
          <div
            key={c}
            className="h-full border-r-2 border-white"
            style={{ width: `${(conta.contribuicoes[c] / escala) * 100}%`, background: COR_COMPONENTE[c] }}
          />
        ))}
      </div>
      <div data-parte="media" className="absolute inset-y-0 w-0.5 bg-[#1f1f1f]" style={{ left: `${(100 / escala) * 100}%` }} />
    </div>
  );
}

/** Volta ao Painel com os filtros de onde a pessoa veio (o Painel passa a busca no `state` do link). */
function Voltar(): JSX.Element {
  const estado: unknown = useLocation().state;
  const busca = (estado as { buscaDoPainel?: unknown } | null)?.buscaDoPainel;
  const destino = typeof busca === 'string' && busca.startsWith('?') ? `/integra/ica${busca}` : '/integra/ica';
  return (
    <p className="mt-4">
      <Link to={destino}>Voltar ao painel</Link>
    </p>
  );
}

export default function FichaCoordenador(): JSX.Element {
  const { id } = useParams();
  const { dados, resultado, historico, mudouNaSessao, pesos, versaoVigente } = useIntegraDemo();
  const r = resultado.coordenadores.find((x) => String(x.coordenador.id) === id);

  const cabecalho = (
    <Title level={1} id="ica-ficha-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
      Ficha do coordenador
    </Title>
  );

  if (!r) {
    return (
      <section aria-labelledby="ica-ficha-titulo">
        {cabecalho}
        <Alert type="warning" showIcon message="Coordenador não encontrado." />
        <Voltar />
      </section>
    );
  }

  const c = r.coordenador;
  const gerencia = dados.gerencias.find((g) => g.id === c.gerencia);
  const gestora = gerencia ? dados.pessoas.find((p) => p.id === gerencia.gestora_tecnica) : undefined;
  const nomeDoCoordenador = (cid: number): string => resultado.coordenadores.find((x) => x.coordenador.id === cid)?.coordenador.nome ?? `Coordenador ${cid}`;
  const nomeDaColecao = (pid: number): string => dados.colecoes.find((x) => x.id === pid)?.nome ?? `Coleção ${pid}`;

  // Como no Histórico: cada semestre fica com o retrato publicado. Se a sessão mudou a carteira ou os
  // pesos, o cálculo dela entra numa linha própria ("Agora") e a variação compara com o último publicado.
  const linhasHistorico: LinhaHistorico[] = historico.map((h) => ({
    semestre: h.semestre,
    calculadoEm: h.calculado_em,
    versao: h.versao.nome,
    r: mudouNaSessao || h.semestre !== dados.semestre_atual ? h.resultado.coordenadores.find((x) => x.coordenador.id === c.id) : r,
  }));
  if (mudouNaSessao) linhasHistorico.push({ semestre: AGORA, calculadoEm: null, versao: versaoVigente.nome, r });

  const anterior = linhasHistorico.at(-2);
  const delta = variacaoDoIca(r, anterior?.r);
  let variacao = 'Sem semestre anterior para comparar';
  if (anterior) {
    variacao =
      delta !== null && anterior.r
        ? `Variação desde ${anterior.semestre}: ${formatarVariacao(delta)} (era ${textoDoEstrato(anterior.r.conta.estrato, anterior.r.conta.icaExibido)})`
        : `Sem cálculo em ${anterior.semestre} para comparar`;
  }

  const colunasCarteira: ColunaResponsiva<LinhaCarteira>[] = [
    {
      title: 'Município',
      key: 'municipio',
      className: 'break-words',
      render: (_v, l) => (
        <>
          {l.municipio.nome}-{l.municipio.uf}
          {!l.ativo && <span className="ml-2 inline-block rounded bg-[#F0F0F0] px-1.5 text-xs font-semibold text-[#3D3D3D]">Suspenso</span>}
        </>
      ),
    },
    {
      title: 'Deslocamento (ida e volta)',
      key: 'horas',
      width: 150,
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_v, l) => `${formatarHoras(l.horas)}${l.estimado ? ' (estimado)' : ''}`,
    },
    {
      title: 'Coleções',
      key: 'colecoes',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_v, l) => l.colecoes.map(nomeDaColecao).join(', '),
    },
    { title: 'Turmas', key: 'turmas', width: 80, responsive: VISIVEL_A_PARTIR.lg, render: (_v, l) => formatarNumero(l.turmas) },
    { title: 'Professores', key: 'professores', width: 105, responsive: VISIVEL_A_PARTIR.lg, render: (_v, l) => formatarNumero(l.professores) },
    {
      title: 'Divide com',
      key: 'compartilhado',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.xl,
      render: (_v, l) => (l.compartilhadoCom.length > 0 ? l.compartilhadoCom.map(nomeDoCoordenador).join(', ') : '—'),
    },
  ];

  const escalaHistorico = escalaDoGrafico(linhasHistorico.map((l) => l.r?.conta.icaExibido ?? 0));
  const colunasHistorico: ColunaResponsiva<LinhaHistorico>[] = [
    { title: 'Semestre', key: 'semestre', width: 100, render: (_v, l) => l.semestre },
    {
      title: 'ICA',
      key: 'ica',
      width: 160,
      render: (_v, l) =>
        l.r ? <EtiquetaEstrato estrato={l.r.conta.estrato} ica={l.r.conta.icaExibido} semMunicipios={l.r.semMunicipios} /> : 'Não estava na equipe',
    },
    {
      title: 'Gráfico',
      key: 'grafico',
      responsive: VISIVEL_A_PARTIR.md,
      render: (_v, l) => (l.r ? <BarraIca ica={l.r.conta.icaExibido} estrato={l.r.conta.estrato} escalaMax={escalaHistorico} fina /> : null),
    },
    {
      title: 'Versão de pesos',
      key: 'versao',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_v, l) => `${l.versao} (${l.calculadoEm === null ? 'nesta sessão' : `calculado em ${formatarDia(l.calculadoEm)}`})`,
    },
  ];

  const ativos = r.carteira.filter((l) => l.ativo);
  const estimados = ativos.filter((l) => l.estimado).map((l) => `${l.municipio.nome}-${l.municipio.uf}`);

  return (
    <section aria-labelledby="ica-ficha-titulo">
      {cabecalho}
      <Title level={2} style={{ fontSize: 22, marginTop: 0 }}>
        {c.nome}
      </Title>
      <p>
        Atuação: {ROTULO_ATUACAO[c.atuacao]} · {gerencia?.nome ?? `Gerência ${c.gerencia}`}
        {gestora ? ` (gestora técnica: ${gestora.nome})` : ''}
      </p>

      <ul aria-label="Situação atual" className="m-0 mb-4 grid list-none gap-2 p-0 md:grid-cols-3">
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          ICA atual: <EtiquetaEstrato estrato={r.conta.estrato} ica={r.conta.icaExibido} semMunicipios={r.semMunicipios} />
        </li>
        <li className="rounded border border-[#d9d9d9] bg-white p-3">{variacao}</li>
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          {r.semMunicipios
            ? 'Sem municípios: fora da média da equipe'
            : `${r.conta.dentroDaMeta ? 'Dentro da meta' : 'Fora da meta'} (${META_ICA.minimo} a ${META_ICA.maximo})`}
        </li>
      </ul>

      {r.dadoIncompleto && (
        <Alert className="mb-3" type="warning" showIcon message={`Dado incompleto: ${r.motivosIncompleto.join(' ')} O ICA fica menor do que deveria.`} />
      )}
      {r.valoresImprovaveis.length > 0 && (
        <Alert className="mb-3" type="warning" showIcon message={`Valor improvável: ${r.valoresImprovaveis.join(' ')} Conferir antes da publicação.`} />
      )}
      {estimados.length > 0 && (
        <Alert
          className="mb-3"
          type="info"
          showIcon
          message={`Deslocamento estimado: ${estimados.join(', ')} ${estimados.length === 1 ? 'não está' : 'não estão'} no relatório de tempos; a conta usa o tempo do meio do relatório (${formatarHoras(resultado.mediana)}).`}
        />
      )}

      <section aria-labelledby="ica-ficha-contribuicao" className="mb-6">
        <Title level={3} id="ica-ficha-contribuicao" style={TITULO}>
          Contribuição de cada componente
        </Title>
        <p className="text-sm">
          Cada pedaço da barra é quanto o componente soma ao ICA, em pontos. Linha vertical = média da equipe (100).
        </p>
        <BarraEmpilhada conta={r.conta} />
        <ul aria-label="Contribuição por componente" className="m-0 mb-4 grid list-none gap-1 p-0 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {COMPONENTES.map((comp) => (
            <li key={comp} className="flex items-center gap-2">
              <span aria-hidden="true" className="inline-block h-3 w-3 shrink-0 rounded-sm" style={{ background: COR_COMPONENTE[comp] }} />
              {ROTULO_COMPONENTE[comp]}: {pesos[comp] === 0 ? 'fora da conta' : `${formatarNumero(r.conta.contribuicoes[comp], 1)} pontos`}
            </li>
          ))}
        </ul>
        <TabelaComponentes valores={r.valores} medias={resultado.medias} pesos={pesos} conta={r.conta} semMunicipios={r.semMunicipios} />
      </section>

      <section aria-labelledby="ica-ficha-carteira" className="mb-6">
        <Title level={3} id="ica-ficha-carteira" style={TITULO}>
          Carteira
        </Title>
        {r.carteira.length === 0 ? (
          <p>Nenhum município na carteira. ICA 0, fora da média da equipe.</p>
        ) : (
          <ResponsiveTable<LinhaCarteira>
            rowKey={(l) => l.municipio.id}
            columns={colunasCarteira}
            dataSource={r.carteira}
            pagination={false}
            nomeDaLinha={(l) => `${l.municipio.nome}-${l.municipio.uf}`}
          />
        )}
      </section>

      <section aria-labelledby="ica-ficha-historico">
        <Title level={3} id="ica-ficha-historico" style={TITULO}>
          Histórico semestral
        </Title>
        <FaixasLegendaCurta />
        <ResponsiveTable<LinhaHistorico>
          rowKey="semestre"
          columns={colunasHistorico}
          dataSource={linhasHistorico}
          pagination={false}
          nomeDaLinha={(l) => l.semestre}
        />
      </section>

      <Voltar />
    </section>
  );
}
