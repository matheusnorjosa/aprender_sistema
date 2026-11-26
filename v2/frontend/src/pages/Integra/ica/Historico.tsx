/**
 * ICA — Histórico semestral (PDF do ICA, seção 5): evolução semestral do ICA por coordenador e da
 * dispersão da equipe, e o registro dos remanejamentos aplicados.
 *
 * Cada semestre foi calculado com a versão de pesos que valia nele (os resultados antigos ficam
 * preservados). Se a sessão mudou a carteira ou os pesos, entra a coluna "Agora (nesta demonstração)".
 * DADOS SIMULADOS: `useIntegraDemo`.
 */
import { useMemo, type JSX } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { formatFortaleza } from '../../../utils/datetime';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import type { Coordenador, Remanejamento, VersaoPesos } from '../dados/tipos';
import { arredondarIca, nomeDoEstrato, variacaoDoIca, type ResultadoCoordenador, type ResultadoEquipe } from './calculo';
import { escalaDoGrafico } from './componentes/BarraIca';
import { BotoesExportar } from './componentes/c2/BotoesExportar';
import { FaixaDispersao } from './componentes/c2/FaixaDispersao';
import { EtiquetaEstrato } from './componentes/EtiquetaEstrato';
import { FaixasLegendaCurta } from './componentes/FaixasLegenda';
import { formatarDia, formatarNumero, formatarVariacao } from './componentes/estilos';
import { baixarCsv } from './exportar';

const { Title } = Typography;

const AGORA = 'Agora (nesta demonstração)';

interface Retrato {
  chave: string;
  rotulo: string;
  /** Data do cálculo, já formatada. */
  quando: string;
  versao: VersaoPesos;
  resultado: ResultadoEquipe;
}

interface LinhaCoordenador {
  coordenador: Coordenador;
  /** Um por retrato, na mesma ordem; `undefined` = não estava na equipe. */
  resultados: (ResultadoCoordenador | undefined)[];
}

function Ica({ r }: { r: ResultadoCoordenador | undefined }): JSX.Element {
  if (!r) return <span>Não estava na equipe</span>;
  return <EtiquetaEstrato estrato={r.conta.estrato} ica={r.conta.icaExibido} semMunicipios={r.semMunicipios} />;
}

const desvio = (valor: number): string => formatarNumero(valor, 1);

export default function Historico(): JSX.Element {
  const { base, historico, mudouNaSessao, resultado, versaoVigente, remanejamentos } = useIntegraDemo();

  const retratos = useMemo<Retrato[]>(() => {
    const lista: Retrato[] = historico.map((h) => ({
      chave: h.semestre,
      rotulo: h.semestre,
      quando: formatarDia(h.calculado_em),
      versao: h.versao,
      resultado: h.resultado,
    }));
    if (mudouNaSessao) lista.push({ chave: 'agora', rotulo: AGORA, quando: 'nesta sessão', versao: versaoVigente, resultado });
    return lista;
  }, [historico, mudouNaSessao, versaoVigente, resultado]);

  const linhas = useMemo<LinhaCoordenador[]>(() => {
    const ordem: Coordenador[] = [];
    for (const retrato of [...retratos].reverse()) {
      const porIca = [...retrato.resultado.coordenadores].sort((a, b) => b.conta.icaExato - a.conta.icaExato);
      for (const r of porIca) if (!ordem.some((c) => c.id === r.coordenador.id)) ordem.push(r.coordenador);
    }
    return ordem.map((coordenador) => ({
      coordenador,
      resultados: retratos.map((rt) => rt.resultado.coordenadores.find((r) => r.coordenador.id === coordenador.id)),
    }));
  }, [retratos]);

  const ultimo = retratos.length - 1;
  const colunas: ColunaResponsiva<LinhaCoordenador>[] = [
    {
      title: 'Coordenador',
      key: 'nome',
      render: (_v, l) => <Link to={`/integra/ica/coordenador/${l.coordenador.id}`}>{l.coordenador.nome}</Link>,
    },
    ...retratos.map(
      (rt, i): ColunaResponsiva<LinhaCoordenador> => ({
        title: rt.rotulo,
        key: rt.chave,
        ...(i < ultimo && { responsive: i === ultimo - 1 ? VISIVEL_A_PARTIR.md : VISIVEL_A_PARTIR.lg }),
        render: (_v, l) => <Ica r={l.resultados[i]} />,
      }),
    ),
    {
      title: 'Variação desde o anterior',
      key: 'variacao',
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_v, l) => {
        // A mesma regra da Ficha: o ICA 0 de quem está sem municípios não entra na comparação.
        const delta = variacaoDoIca(l.resultados[ultimo], l.resultados[ultimo - 1]);
        return delta === null ? '—' : formatarVariacao(delta);
      },
    },
  ];

  const colunasDispersao: ColunaResponsiva<Retrato>[] = [
    { title: 'Semestre', key: 'semestre', render: (_v, rt) => <strong>{rt.rotulo}</strong> },
    { title: 'Pesos usados', key: 'versao', responsive: VISIVEL_A_PARTIR.md, render: (_v, rt) => rt.versao.nome },
    { title: 'Calculado em', key: 'quando', responsive: VISIVEL_A_PARTIR.xl, render: (_v, rt) => rt.quando },
    {
      title: 'Com municípios',
      key: 'quantidade',
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_v, rt) => formatarNumero(rt.resultado.dispersao.quantidade),
    },
    { title: 'Desvio', key: 'desvio', width: 80, render: (_v, rt) => desvio(rt.resultado.dispersao.desvioPadrao) },
    {
      title: 'Menor',
      key: 'menor',
      width: 72,
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_v, rt) => arredondarIca(rt.resultado.dispersao.menor),
    },
    {
      title: 'Maior',
      key: 'maior',
      width: 72,
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_v, rt) => arredondarIca(rt.resultado.dispersao.maior),
    },
  ];

  const escala = escalaDoGrafico(retratos.map((rt) => rt.resultado.dispersao.maior));

  const nomeDoCoordenador = (id: number): string =>
    base.coordenadores.find((c) => c.id === id)?.nome ?? `coordenador ${id}`;
  const nomeDoMunicipio = (id: number): string => {
    const m = base.municipios.find((x) => x.id === id);
    return m ? `${m.nome}-${m.uf}` : `município ${id}`;
  };
  const aplicados = remanejamentos
    .filter((r): r is Remanejamento & { aplicado_em: string } => r.status === 'aplicado' && r.aplicado_em !== null)
    .sort((a, b) => new Date(b.aplicado_em).getTime() - new Date(a.aplicado_em).getTime());
  const pendentes = remanejamentos.filter((r) => r.status !== 'aplicado').length;

  const baixarPlanilha = (): void =>
    baixarCsv(
      'ica_historico.csv',
      ['Coordenador', ...retratos.flatMap((rt) => [`ICA ${rt.rotulo}`, `Estrato ${rt.rotulo}`])],
      linhas.map((l) => [
        l.coordenador.nome,
        ...l.resultados.flatMap((r) =>
          r ? [r.conta.icaExibido, r.semMunicipios ? 'Sem municípios' : nomeDoEstrato(r.conta.estrato)] : ['', 'Não estava na equipe'],
        ),
      ]),
    );

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Histórico semestral
      </Title>
      <p className="mb-4">
        O ICA de cada semestre foi calculado com a versão de pesos que valia na época. No protótipo, os semestres
        anteriores foram refeitos com a regra de frentes da decisão 59 (cada ano de cada coleção); na versão real, o
        resultado antigo fica guardado como foi publicado, e a SPE confere o cálculo e o ICA é publicado em até 5 dias
        úteis depois da conferência (decisão 72).
      </p>
      <BotoesExportar aoBaixarPlanilha={baixarPlanilha} />

      <div className="grid gap-6 xl:grid-cols-2">
        <figure aria-labelledby="historico-dispersao-grafico" className="m-0">
          <Title level={2} id="historico-dispersao-grafico" style={{ fontSize: 20 }}>
            Dispersão da equipe
          </Title>
          <figcaption className="mb-3 text-sm">
            O traço vai do menor ao maior ICA da equipe; a bolinha marca a média. Quanto menor o desvio, mais
            equilibrada a carga.
          </figcaption>
          <FaixasLegendaCurta grafico="dispersao" />
          <ul className="m-0 list-none space-y-3 p-0">
            {retratos.map((rt) => {
              const d = rt.resultado.dispersao;
              return (
                <li key={rt.chave}>
                  <div className="mb-1 flex flex-wrap justify-between gap-x-2">
                    <span className="font-semibold">{rt.rotulo}</span>
                    <span className="text-sm">
                      de {arredondarIca(d.menor)} a {arredondarIca(d.maior)} · média {arredondarIca(d.media)} · desvio{' '}
                      {desvio(d.desvioPadrao)}
                    </span>
                  </div>
                  <FaixaDispersao menor={d.menor} maior={d.maior} media={d.media} escalaMax={escala} />
                </li>
              );
            })}
          </ul>
        </figure>

        <div>
          <Title level={2} id="historico-dispersao-tabela" style={{ fontSize: 20 }}>
            Dispersão da equipe por semestre
          </Title>
          <ResponsiveTable<Retrato>
            aria-labelledby="historico-dispersao-tabela"
            columns={colunasDispersao}
            dataSource={retratos}
            rowKey={(rt) => rt.chave}
            nomeDaLinha={(rt) => rt.rotulo}
            pagination={false}
          />
        </div>
      </div>

      <Title level={2} id="historico-coordenadores" style={{ fontSize: 20, marginTop: 32 }}>
        ICA por coordenador
      </Title>
      <ResponsiveTable<LinhaCoordenador>
        aria-labelledby="historico-coordenadores"
        columns={colunas}
        dataSource={linhas}
        rowKey={(l) => l.coordenador.id}
        nomeDaLinha={(l) => l.coordenador.nome}
        pagination={false}
      />

      <section aria-labelledby="historico-remanejamentos" className="mt-8">
        <Title level={2} id="historico-remanejamentos" style={{ fontSize: 20 }}>
          Remanejamentos aplicados
        </Title>
        {pendentes > 0 && (
          <p>
            {pendentes === 1 ? '1 remanejamento aguarda' : `${pendentes} remanejamentos aguardam`} aprovação ou
            aplicação no <Link to="/integra/ica/simulador">Simulador</Link>.
          </p>
        )}
        <ul aria-label="Remanejamentos aplicados" className="m-0 list-none space-y-3 p-0">
          {aplicados.map((r) => (
            <li key={r.id} className="rounded border border-[#8c8c8c] p-3">
              <strong className="block">
                {r.semestre ? `Semestre ${r.semestre}` : 'Semestre não informado'} · aplicado em{' '}
                {formatFortaleza(r.aplicado_em, 'DD/MM/YYYY')}
                {r.vigencia_em && ` · vale a partir de ${formatarDia(r.vigencia_em)}`}
              </strong>
              <ul className="my-1 pl-5">
                {r.movimentos.map((m) => (
                  <li key={`${m.municipioId}-${m.deCoordenadorId}-${m.paraCoordenadorId}`}>
                    {nomeDoMunicipio(m.municipioId)}: de {nomeDoCoordenador(m.deCoordenadorId)} para{' '}
                    {nomeDoCoordenador(m.paraCoordenadorId)}
                  </li>
                ))}
              </ul>
              <span className="block">Justificativa: {r.justificativa}</span>
              <span className="block text-sm">
                Proposto por {r.proposto_por} em {formatFortaleza(r.proposto_em, 'DD/MM/YYYY')}.
                {r.aprovado_por && r.aprovado_em
                  ? ` Aprovado por ${r.aprovado_por} em ${formatFortaleza(r.aprovado_em, 'DD/MM/YYYY')}.`
                  : ''}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </section>
  );
}
