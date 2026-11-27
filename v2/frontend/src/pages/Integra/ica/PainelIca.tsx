/**
 * ICA — Painel geral (DADOS SIMULADOS).
 *
 * Leitura rápida no topo (cartões por estrato, média e dispersão), o detalhe logo abaixo (barras por
 * coordenador sobre as faixas, com a linha da média 100) e a tabela com todos os componentes.
 * Filtros: gerência, atuação, estrato e semestre (o semestre anterior usa a versão de pesos que valia
 * nele). Os filtros ficam no endereço (?gerencia=2&estrato=sobrecarga): o "Voltar ao painel" da ficha
 * devolve a tela como estava. O nome abre a ficha do coordenador. Exporta o que está filtrado em
 * planilha e imprime em PDF, com uma linha só do papel que diz os filtros aplicados.
 * Depois de um remanejamento ou de uma troca de pesos na sessão, a mesma regra da Ficha e do Histórico:
 * o semestre atual mostra o retrato publicado, e o recálculo fica em "Agora (nesta demonstração)", que
 * passa a ser o padrão do filtro.
 * Requisitos: Requisitos_Modulo_ICA.pdf, seção 5 ("Painel geral").
 */
import { useMemo, type JSX } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Alert, Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import { ROTULO_ATUACAO, type Atuacao } from '../dados/tipos';
import {
  arredondarIca,
  calcularDispersao,
  ESTRATOS,
  formatarHoras,
  type Estrato,
  type ResultadoCoordenador,
} from './calculo';
import { BarraIca, escalaDoGrafico } from './componentes/BarraIca';
import { EtiquetaEstrato, textoDoEstrato } from './componentes/EtiquetaEstrato';
import { BotoesExportar } from './componentes/c2/BotoesExportar';
import { FaixasLegenda } from './componentes/FaixasLegenda';
import { CLASSE_CAMPO, CLASSE_ROTULO, COR_ESTRATO, formatarDia, formatarNumero } from './componentes/estilos';
import { baixarCsv } from './exportar';

const { Title } = Typography;

/** Aviso curto ao lado do nome (texto 4,5:1 no fundo). */
function Aviso({ texto }: { texto: string }): JSX.Element {
  return <span className="mr-1 mt-1 inline-block rounded bg-[#FDF4E3] px-1.5 text-xs font-semibold text-[#8A5A00]">{texto}</span>;
}

function avisosDe(r: ResultadoCoordenador): string[] {
  const avisos: string[] = [];
  if (r.dadoIncompleto) avisos.push('Dado incompleto');
  if (r.valoresImprovaveis.length > 0) avisos.push('Valor improvável');
  if (r.deslocamentoEstimado) avisos.push('Deslocamento estimado');
  return avisos;
}

/** Valor do filtro de estrato para quem está sem municípios (fora dos estratos, PDF seção 3). */
const SEM_MUNICIPIOS = 'sem_municipios';

/** Valor do filtro de semestre para o recálculo da sessão (só existe depois de uma mudança). */
const AGORA = 'agora';
const ROTULO_AGORA = 'Agora (nesta demonstração)';

const ordenarPorIca = (lista: ResultadoCoordenador[]): ResultadoCoordenador[] =>
  [...lista].sort((a, b) => b.conta.icaExato - a.conta.icaExato || a.coordenador.nome.localeCompare(b.coordenador.nome, 'pt-BR'));

export default function PainelIca(): JSX.Element {
  const { dados, resultado, historico, mudouNaSessao, versaoVigente } = useIntegraDemo();
  const [busca, setBusca] = useSearchParams();
  const gerencia = busca.get('gerencia') ?? '';
  const atuacao = busca.get('atuacao') ?? '';
  const estrato = busca.get('estrato') ?? '';
  const pedido = busca.get('semestre');
  const semestrePadrao = mudouNaSessao ? AGORA : dados.semestre_atual;
  const pedidoValido = pedido !== null && ((mudouNaSessao && pedido === AGORA) || historico.some((h) => h.semestre === pedido));
  const semestre = pedidoValido ? pedido : semestrePadrao;
  /** Troca um filtro no endereço, sem empilhar uma entrada no histórico do navegador por clique. */
  const filtrar = (chave: 'gerencia' | 'atuacao' | 'estrato' | 'semestre', valor: string): void => {
    const proxima = new URLSearchParams(busca);
    if (valor === '' || (chave === 'semestre' && valor === semestrePadrao)) proxima.delete(chave);
    else proxima.set(chave, valor);
    setBusca(proxima, { replace: true });
  };

  // Sem mudança na sessão, o cálculo atual é o próprio retrato publicado do semestre atual.
  const nestaDemonstracao = semestre === AGORA;
  const atual = !mudouNaSessao && semestre === dados.semestre_atual;
  const retrato = atual || nestaDemonstracao ? undefined : historico.find((h) => h.semestre === semestre);
  const resultadoDoSemestre = retrato?.resultado ?? resultado;

  const nomeDaGerencia = (id: number): string => {
    const g = dados.gerencias.find((x) => x.id === id);
    const gestora = g ? dados.pessoas.find((p) => p.id === g.gestora_tecnica) : undefined;
    return g ? `${g.nome}${gestora ? ` (${gestora.nome})` : ''}` : `Gerência ${id}`;
  };

  const filtrados = useMemo(
    () =>
      ordenarPorIca(
        resultadoDoSemestre.coordenadores.filter(
          (r) =>
            (gerencia === '' || String(r.coordenador.gerencia) === gerencia) &&
            (atuacao === '' || r.coordenador.atuacao === atuacao) &&
            (estrato === '' ||
              (estrato === SEM_MUNICIPIOS ? r.semMunicipios : !r.semMunicipios && r.conta.estrato === estrato)),
        ),
      ),
    [resultadoDoSemestre, gerencia, atuacao, estrato],
  );

  const dispersao = calcularDispersao(filtrados);
  const porEstrato = (e: Estrato): number => filtrados.filter((r) => !r.semMunicipios && r.conta.estrato === e).length;
  const escala = escalaDoGrafico(filtrados.map((r) => r.conta.icaExibido));
  const incompletos = filtrados.filter((r) => r.dadoIncompleto).map((r) => r.coordenador.nome);
  const semMunicipios = filtrados.filter((r) => r.semMunicipios).map((r) => r.coordenador.nome);
  const linkDaFicha = (r: ResultadoCoordenador): string => `/integra/ica/coordenador/${r.coordenador.id}`;
  /** A ficha usa a busca para o "Voltar ao painel" levar de volta aos mesmos filtros. */
  const textoDaBusca = busca.toString();
  const estadoDoLink = { buscaDoPainel: textoDaBusca === '' ? '' : `?${textoDaBusca}` };
  const nomeDoEstratoFiltrado =
    estrato === '' ? 'todos' : estrato === SEM_MUNICIPIOS ? 'Sem municípios' : (ESTRATOS.find((e) => e.chave === estrato)?.nome ?? estrato);
  const filtrosAplicados = [
    `Gerência: ${gerencia === '' ? 'todas' : nomeDaGerencia(Number(gerencia))}`,
    `Atuação: ${atuacao === '' ? 'todas' : (ROTULO_ATUACAO[atuacao as Atuacao] ?? atuacao)}`,
    `Estrato: ${nomeDoEstratoFiltrado}`,
    `Semestre: ${nestaDemonstracao ? ROTULO_AGORA : `${semestre}${atual ? ' (atual)' : ''}`}`,
  ].join(' · ');

  const colunas: ColunaResponsiva<ResultadoCoordenador>[] = [
    {
      title: 'Coordenador',
      key: 'coordenador',
      className: 'break-words',
      render: (_v, r) => (
        <>
          <Link to={linkDaFicha(r)} state={estadoDoLink}>
            {r.coordenador.nome}
          </Link>
          {avisosDe(r).length > 0 && (
            <span className="block">
              {avisosDe(r).map((a) => (
                <Aviso key={a} texto={a} />
              ))}
            </span>
          )}
        </>
      ),
    },
    {
      title: 'ICA',
      key: 'ica',
      width: 150,
      render: (_v, r) => <EtiquetaEstrato estrato={r.conta.estrato} ica={r.conta.icaExibido} semMunicipios={r.semMunicipios} />,
    },
    { title: 'Municípios', key: 'municipios', width: 100, responsive: VISIVEL_A_PARTIR.sm, render: (_v, r) => r.valores.municipios },
    { title: 'Frentes', key: 'frentes', width: 80, responsive: VISIVEL_A_PARTIR.md, render: (_v, r) => r.valores.frentes },
    { title: 'Turmas', key: 'turmas', width: 80, responsive: VISIVEL_A_PARTIR.lg, render: (_v, r) => formatarNumero(r.valores.turmas) },
    {
      title: 'Professores',
      key: 'professores',
      width: 105,
      responsive: VISIVEL_A_PARTIR.xl,
      render: (_v, r) => formatarNumero(r.valores.professores),
    },
    {
      title: 'Deslocamento',
      key: 'deslocamento',
      width: 120,
      responsive: VISIVEL_A_PARTIR.xl,
      render: (_v, r) => formatarHoras(r.valores.deslocamento),
    },
    { title: 'Estados', key: 'estados', width: 80, responsive: VISIVEL_A_PARTIR.xxl, render: (_v, r) => r.valores.estados },
    { title: 'Gerência', key: 'gerencia', responsive: VISIVEL_A_PARTIR.xxl, render: (_v, r) => nomeDaGerencia(r.coordenador.gerencia) },
    { title: 'Atuação', key: 'atuacao', responsive: VISIVEL_A_PARTIR.xxl, render: (_v, r) => ROTULO_ATUACAO[r.coordenador.atuacao] },
  ];

  const exportar = (): void => {
    baixarCsv(
      `ica_painel_${(nestaDemonstracao ? dados.semestre_atual : semestre).replace('.', '-')}${nestaDemonstracao ? '_nesta-demonstracao' : ''}.csv`,
      [
        'Coordenador',
        'Gerência',
        'Atuação',
        'ICA',
        'Estrato',
        'Municípios ativos',
        'Frentes',
        'Turmas',
        'Professores',
        'Deslocamento (horas)',
        'Estados',
        'Avisos',
      ],
      filtrados.map((r) => [
        r.coordenador.nome,
        nomeDaGerencia(r.coordenador.gerencia),
        ROTULO_ATUACAO[r.coordenador.atuacao],
        r.conta.icaExibido,
        textoDoEstrato(r.conta.estrato, undefined, r.semMunicipios),
        r.valores.municipios,
        r.valores.frentes,
        r.valores.turmas,
        r.valores.professores,
        Math.round(r.valores.deslocamento * 100) / 100,
        r.valores.estados,
        avisosDe(r).join(', '),
      ]),
    );
  };

  return (
    <section aria-labelledby="ica-painel-titulo">
      <Title level={1} id="ica-painel-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
        Painel do ICA
      </Title>
      <p className="mb-4">
        {retrato
          ? `Retrato de ${retrato.semestre}, calculado em ${formatarDia(retrato.calculado_em)} com a ${retrato.versao.nome}.`
          : nestaDemonstracao
            ? `Agora, nesta demonstração: semestre ${dados.semestre_atual} recalculado com as mudanças desta sessão e a ${versaoVigente.nome}.`
            : `Semestre ${dados.semestre_atual} (atual), com a ${versaoVigente.nome}.`}{' '}
        O ICA compara a carga de cada coordenador com a média da equipe: 100 é a carga média.
      </p>

      <form role="search" aria-label="Filtros do painel" className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4 print:hidden" onSubmit={(e) => e.preventDefault()}>
        <div>
          <label htmlFor="ica-filtro-gerencia" className={CLASSE_ROTULO}>
            Gerência
          </label>
          <select id="ica-filtro-gerencia" className={CLASSE_CAMPO} value={gerencia} onChange={(e) => filtrar('gerencia', e.target.value)}>
            <option value="">Todas</option>
            {dados.gerencias.map((g) => (
              <option key={g.id} value={String(g.id)}>
                {nomeDaGerencia(g.id)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="ica-filtro-atuacao" className={CLASSE_ROTULO}>
            Atuação
          </label>
          <select id="ica-filtro-atuacao" className={CLASSE_CAMPO} value={atuacao} onChange={(e) => filtrar('atuacao', e.target.value)}>
            <option value="">Todas</option>
            {(Object.keys(ROTULO_ATUACAO) as Atuacao[]).map((a) => (
              <option key={a} value={a}>
                {ROTULO_ATUACAO[a]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="ica-filtro-estrato" className={CLASSE_ROTULO}>
            Estrato
          </label>
          <select id="ica-filtro-estrato" className={CLASSE_CAMPO} value={estrato} onChange={(e) => filtrar('estrato', e.target.value)}>
            <option value="">Todos</option>
            {ESTRATOS.map((e) => (
              <option key={e.chave} value={e.chave}>
                {e.nome}
              </option>
            ))}
            <option value={SEM_MUNICIPIOS}>Sem municípios</option>
          </select>
        </div>
        <div>
          <label htmlFor="ica-filtro-semestre" className={CLASSE_ROTULO}>
            Semestre
          </label>
          <select id="ica-filtro-semestre" className={CLASSE_CAMPO} value={semestre} onChange={(e) => filtrar('semestre', e.target.value)}>
            {mudouNaSessao && <option value={AGORA}>{ROTULO_AGORA}</option>}
            {[...historico].reverse().map((h) => (
              <option key={h.semestre} value={h.semestre}>
                {!mudouNaSessao && h.semestre === dados.semestre_atual ? `${h.semestre} (atual)` : h.semestre}
              </option>
            ))}
          </select>
        </div>
      </form>
      {/* Os campos não saem no papel: sem esta linha, o PDF filtrado parece a equipe toda. */}
      <p className="mb-4 hidden text-sm print:block">Filtros: {filtrosAplicados}</p>

      <ul aria-label="Resumo do ICA" className="m-0 mb-4 grid list-none gap-2 p-0 sm:grid-cols-2 lg:grid-cols-4">
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          <strong className="text-2xl">{filtrados.length}</strong> {filtrados.length === 1 ? 'coordenador' : 'coordenadores'}
        </li>
        {ESTRATOS.map((e) => (
          <li key={e.chave} className="rounded p-3" style={{ background: COR_ESTRATO[e.chave].fundo, color: COR_ESTRATO[e.chave].texto }}>
            <strong className="text-2xl">{porEstrato(e.chave)}</strong> em {e.nome}
          </li>
        ))}
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          <strong className="text-2xl">{semMunicipios.length}</strong> sem municípios
        </li>
        <li className="rounded border border-[#d9d9d9] bg-white p-3">
          Média: <strong>{dispersao.quantidade > 0 ? formatarNumero(arredondarIca(dispersao.media)) : '—'}</strong>
        </li>
        <li className="rounded border border-[#d9d9d9] bg-white p-3 break-words">
          {dispersao.quantidade > 0
            ? `Dispersão: desvio ${formatarNumero(dispersao.desvioPadrao, 1)} · menor ${arredondarIca(dispersao.menor)} · maior ${arredondarIca(dispersao.maior)}`
            : 'Dispersão: —'}
        </li>
      </ul>

      {incompletos.length > 0 && (
        <Alert
          className="mb-3"
          type="warning"
          showIcon
          message={`Dado incompleto: ${incompletos.join(', ')}. Falta algum número na carteira, e o ICA fica menor do que deveria.`}
        />
      )}
      {semMunicipios.length > 0 && (
        <Alert
          className="mb-3"
          type="info"
          showIcon
          message={`Sem municípios: ${semMunicipios.join(', ')}. ICA 0, fora da média da equipe.`}
        />
      )}

      <BotoesExportar aoBaixarPlanilha={exportar} />

      <section aria-labelledby="ica-painel-barras" className="mb-6">
        <Title level={2} id="ica-painel-barras" style={{ fontSize: 20 }}>
          ICA por coordenador
        </Title>
        <p className="text-sm">Linha vertical = média da equipe (100). Clique no nome para abrir a ficha.</p>
        {filtrados.length === 0 ? (
          <p>Nenhum coordenador com estes filtros.</p>
        ) : (
          <ol aria-label="ICA por coordenador" className="m-0 mb-4 list-none p-0">
            {filtrados.map((r) => (
              <li key={r.coordenador.id} className="mb-2 grid items-center gap-x-3 gap-y-1 md:grid-cols-[13rem_13rem_1fr]">
                <span className="flex flex-wrap items-center justify-between gap-2 md:contents">
                  <Link to={linkDaFicha(r)} state={estadoDoLink} className="break-words">
                    {r.coordenador.nome}
                  </Link>
                  <EtiquetaEstrato estrato={r.conta.estrato} ica={r.conta.icaExibido} semMunicipios={r.semMunicipios} />
                </span>
                <BarraIca ica={r.conta.icaExibido} estrato={r.conta.estrato} escalaMax={escala} />
              </li>
            ))}
          </ol>
        )}
        <FaixasLegenda />
      </section>

      <section aria-labelledby="ica-painel-tabela">
        <Title level={2} id="ica-painel-tabela" style={{ fontSize: 20 }}>
          Tabela com todos os componentes
        </Title>
        <ResponsiveTable<ResultadoCoordenador>
          className="print:hidden"
          rowKey={(r) => r.coordenador.id}
          columns={colunas}
          dataSource={filtrados}
          pagination={false}
          nomeDaLinha={(r) => r.coordenador.nome}
          locale={{ emptyText: 'Nenhum coordenador com estes filtros.' }}
        />
        {/* No papel, a tabela escolheria as colunas pela largura da tela (no notebook, sem Gerência e
            Atuação) e levaria o botão de expandir. Esta lista, só da impressão, tem tudo e cabe na folha. */}
        <div className="hidden print:block">
          {filtrados.length === 0 ? (
            <p>Nenhum coordenador com estes filtros.</p>
          ) : (
            <ul aria-label="Todos os componentes, por coordenador" className="m-0 list-none p-0">
              {filtrados.map((r, indice) => (
                <li key={r.coordenador.id} className="mb-3 border-0 border-b border-solid border-[#d9d9d9] pb-2">
                  <p className="m-0 font-semibold">{r.coordenador.nome}</p>
                  {avisosDe(r).map((a) => (
                    <Aviso key={a} texto={a} />
                  ))}
                  <dl className="m-0 mt-1 grid grid-cols-2 gap-x-6 text-sm">
                    {colunas
                      .filter((c) => c.key !== 'coordenador')
                      .map((c) => (
                        <div key={String(c.key)} className="flex flex-wrap gap-x-1">
                          <dt className="font-semibold after:content-[':']">{c.title}</dt>
                          <dd className="m-0">{c.render?.(undefined, r, indice)}</dd>
                        </div>
                      ))}
                  </dl>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </section>
  );
}
