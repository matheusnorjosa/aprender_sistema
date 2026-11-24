/**
 * ICA — Visão por gerência (PDF do ICA, seção 5): municípios, coordenadores e professores de cada
 * gerência e o ICA médio dos coordenadores dela. Gráfico de barras com a tabela ao lado.
 *
 * DADOS SIMULADOS: lê a carteira e os pesos vigentes na sessão (`useIntegraDemo`).
 */
import { useMemo, type JSX } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import { nomeDoEstrato } from './calculo';
import { BarraIca, escalaDoGrafico } from './componentes/BarraIca';
import { BotoesExportar } from './componentes/c2/BotoesExportar';
import { resumoPorGerencia, type ResumoGerencia } from './componentes/c2/contas';
import { EtiquetaEstrato } from './componentes/EtiquetaEstrato';
import { FaixasLegendaCurta } from './componentes/FaixasLegenda';
import { formatarNumero } from './componentes/estilos';
import { baixarCsv } from './exportar';

const { Title } = Typography;

function IcaMedio({ resumo }: { resumo: ResumoGerencia }): JSX.Element {
  if (resumo.icaMedio === null || resumo.estrato === null) return <span>Sem coordenadores com municípios</span>;
  return <EtiquetaEstrato estrato={resumo.estrato} ica={resumo.icaMedio} />;
}

const COLUNAS: ColunaResponsiva<ResumoGerencia>[] = [
  { title: 'Gerência', key: 'gerencia', render: (_v, r) => <strong>{r.gerencia.nome}</strong> },
  { title: 'Gestora técnica', key: 'gestora', responsive: VISIVEL_A_PARTIR.md, render: (_v, r) => r.gestoraTecnica },
  {
    title: 'Coordenadores',
    key: 'coordenadores',
    responsive: VISIVEL_A_PARTIR.lg,
    render: (_v, r) => `${r.coordenadores.length} (${r.comCarteira} com municípios)`,
  },
  {
    title: 'Municípios ativos',
    key: 'municipios',
    responsive: VISIVEL_A_PARTIR.lg,
    render: (_v, r) => formatarNumero(r.municipiosAtivos),
  },
  {
    title: 'Professores em formação',
    key: 'professores',
    responsive: VISIVEL_A_PARTIR.lg,
    render: (_v, r) => formatarNumero(r.professores),
  },
  {
    title: 'ICA médio',
    key: 'ica',
    render: (_v, r) => <IcaMedio resumo={r} />,
  },
];

export default function VisaoGerencia(): JSX.Element {
  const { dados, resultado, versaoVigente } = useIntegraDemo();
  const resumos = useMemo(
    () => resumoPorGerencia(resultado, dados.gerencias, dados.pessoas),
    [resultado, dados.gerencias, dados.pessoas],
  );
  const escala = escalaDoGrafico(resumos.map((r) => r.icaMedio ?? 0));

  const baixarPlanilha = (): void =>
    baixarCsv(
      'ica_por_gerencia.csv',
      [
        'Gerência',
        'Gestora técnica',
        'Coordenadores',
        'Coordenadores com municípios',
        'Municípios ativos',
        'Professores em formação',
        'ICA médio',
        'Estrato',
      ],
      resumos.map((r) => [
        r.gerencia.nome,
        r.gestoraTecnica,
        r.coordenadores.length,
        r.comCarteira,
        r.municipiosAtivos,
        r.professores,
        r.icaMedio,
        r.estrato === null ? '' : nomeDoEstrato(r.estrato),
      ]),
    );

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Visão por gerência
      </Title>
      <p className="mb-4">
        Municípios, coordenadores e professores de cada gerência, e o ICA médio dos coordenadores dela. Só entra na
        média quem tem pelo menos um município ativo. Pesos usados: <strong>{versaoVigente.nome}</strong>.
      </p>
      <BotoesExportar aoBaixarPlanilha={baixarPlanilha} />

      <div className="grid gap-6 xl:grid-cols-2">
        <figure aria-labelledby="gerencias-grafico-titulo" className="m-0">
          <Title level={2} id="gerencias-grafico-titulo" style={{ fontSize: 20 }}>
            ICA médio por gerência
          </Title>
          <figcaption className="mb-3 text-sm">
            Barra sobre as faixas do ICA; a linha preta marca 100, a carga média da equipe.
          </figcaption>
          <FaixasLegendaCurta />
          <ul className="m-0 list-none space-y-3 p-0">
            {resumos.map((r) => (
              <li key={r.gerencia.id}>
                <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">{r.gerencia.nome}</span>
                  <IcaMedio resumo={r} />
                </div>
                {r.icaMedio !== null && r.estrato !== null && (
                  <BarraIca ica={r.icaMedio} estrato={r.estrato} escalaMax={escala} />
                )}
              </li>
            ))}
          </ul>
        </figure>

        <div>
          <Title level={2} id="gerencias-tabela-titulo" style={{ fontSize: 20 }}>
            Resumo por gerência
          </Title>
          <ResponsiveTable<ResumoGerencia>
            aria-labelledby="gerencias-tabela-titulo"
            columns={COLUNAS}
            dataSource={resumos}
            rowKey={(r) => r.gerencia.id}
            nomeDaLinha={(r) => r.gerencia.nome}
            pagination={false}
          />
        </div>
      </div>

      {resumos.map((r) => {
        const idTitulo = `gerencia-${r.gerencia.id}-titulo`;
        const ordenados = [...r.coordenadores].sort((a, b) => b.conta.icaExato - a.conta.icaExato);
        return (
          <section key={r.gerencia.id} aria-labelledby={idTitulo} className="mt-8">
            <Title level={2} id={idTitulo} style={{ fontSize: 20 }}>
              {r.gerencia.nome}
            </Title>
            <p className="mb-2 text-sm">Gestora técnica: {r.gestoraTecnica}</p>
            <ul aria-label={`Coordenadores da ${r.gerencia.nome}`} className="m-0 list-none divide-y p-0">
              {ordenados.map((c) => (
                <li key={c.coordenador.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span className="min-w-0">
                    <Link to={`/integra/ica/coordenador/${c.coordenador.id}`}>{c.coordenador.nome}</Link>
                    <span className="block text-sm">
                      {formatarNumero(c.valores.municipios)} {c.valores.municipios === 1 ? 'município ativo' : 'municípios ativos'} ·{' '}
                      {formatarNumero(c.valores.professores)} {c.valores.professores === 1 ? 'professor' : 'professores'}
                    </span>
                  </span>
                  <EtiquetaEstrato estrato={c.conta.estrato} ica={c.conta.icaExibido} semMunicipios={c.semMunicipios} />
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </section>
  );
}
