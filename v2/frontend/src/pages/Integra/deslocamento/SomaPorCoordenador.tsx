/**
 * Deslocamento — soma por coordenador: o tempo de ida e volta somado na carteira de cada coordenador.
 *
 * Tempos REAIS (relatório) sobre as carteiras FICTÍCIAS do gerador, no estado da sessão (um remanejamento
 * feito no Simulador muda a soma). É o mesmo número do componente "Tempo de deslocamento" do ICA:
 * suspenso fica fora e o município sem localidade entra com a mediana (estimado). Gráfico de barras com
 * o número escrito e a tabela ao lado (`ResponsiveTable`, sem rolagem horizontal).
 */
import { useMemo, type JSX } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import { FAIXAS_DESLOCAMENTO } from '../dados/deslocamento';
import { formatarHoras } from '../ica/calculo';
import { formatarNumero } from '../ica/componentes/estilos';
import { somaPorCoordenador, type SomaDoCoordenador } from './contas';

const { Title } = Typography;

function textoDaSoma(s: SomaDoCoordenador): string {
  if (s.municipios === 0) return 'Sem municípios';
  return `${formatarHoras(s.somaHoras)} em ${formatarNumero(s.municipios)} ${s.municipios === 1 ? 'município' : 'municípios'}`;
}

function textoPorFaixa(s: SomaDoCoordenador): string {
  const partes = FAIXAS_DESLOCAMENTO.filter((f) => s.porFaixa[f.faixa] > 0).map((f) => `${s.porFaixa[f.faixa]} ${f.rotulo}`);
  return partes.length > 0 ? partes.join(' · ') : '—';
}

function observacoes(s: SomaDoCoordenador): string[] {
  return [
    ...s.estimados.map((m) => `${m} com a mediana (estimado)`),
    ...(s.suspensos.length > 0 ? [`Fora da soma (suspenso): ${s.suspensos.join(', ')}`] : []),
  ];
}

const COLUNAS: ColunaResponsiva<SomaDoCoordenador>[] = [
  {
    title: 'Coordenador',
    key: 'coordenador',
    className: 'break-words',
    render: (_v, s) => <Link to={`/integra/ica/coordenador/${s.coordenador.id}`}>{s.coordenador.nome}</Link>,
  },
  { title: 'Soma de ida e volta', key: 'soma', width: 110, render: (_v, s) => formatarHoras(s.somaHoras) },
  { title: 'Municípios ativos', key: 'municipios', width: 100, responsive: VISIVEL_A_PARTIR.sm, render: (_v, s) => formatarNumero(s.municipios) },
  {
    title: 'Média por município',
    key: 'media',
    width: 110,
    responsive: VISIVEL_A_PARTIR.md,
    render: (_v, s) => (s.municipios === 0 ? '—' : formatarHoras(s.mediaHoras)),
  },
  {
    title: 'Maior trajeto',
    key: 'maior',
    className: 'break-words',
    responsive: VISIVEL_A_PARTIR.lg,
    render: (_v, s) => (s.maior ? `${s.maior.municipio.nome}-${s.maior.municipio.uf} (${formatarHoras(s.maior.horas)})` : '—'),
  },
  { title: 'Por faixa', key: 'faixas', className: 'break-words', responsive: VISIVEL_A_PARTIR.xl, render: (_v, s) => textoPorFaixa(s) },
  {
    title: 'Observações',
    key: 'observacoes',
    className: 'break-words',
    responsive: VISIVEL_A_PARTIR.lg,
    render: (_v, s) => {
      const lista = observacoes(s);
      return lista.length === 0 ? '—' : (
        <ul className="m-0 list-none p-0">
          {lista.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      );
    },
  },
];

export default function SomaPorCoordenador(): JSX.Element {
  const { resultado } = useIntegraDemo();
  const somas = useMemo(() => somaPorCoordenador(resultado), [resultado]);
  const maior = Math.max(1, ...somas.map((s) => s.somaHoras));

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Soma por coordenador
      </Title>
      <p className="mb-2">
        Soma do tempo de ida e volta de cada município ativo da carteira. É o mesmo número do componente “Tempo de
        deslocamento” do ICA. Município com ações suspensas fica fora da soma; município sem localidade definida entra
        com a mediana ({formatarHoras(resultado.mediana)}), marcado como estimado.
      </p>
      <p className="mb-6 text-sm">Coordenadores e carteiras fictícios; os tempos de cada município são os do relatório.</p>

      <div className="grid gap-6 xl:grid-cols-2">
        <figure aria-labelledby="deslocamento-soma-grafico" className="m-0">
          <Title level={2} id="deslocamento-soma-grafico" style={{ fontSize: 20 }}>
            Horas de ida e volta somadas
          </Title>
          <figcaption className="mb-3 text-sm">Da maior soma para a menor. A barra é proporcional à soma.</figcaption>
          <ul className="m-0 list-none space-y-3 p-0">
            {somas.map((s) => (
              <li key={s.coordenador.id}>
                <span className="mb-1 flex flex-wrap justify-between gap-x-2">
                  <span className="font-semibold">{s.coordenador.nome}</span>
                  <span>{textoDaSoma(s)}</span>
                </span>
                <span aria-hidden="true" className="block h-3 w-full rounded-sm bg-[#F0F0F0]">
                  <span className="block h-full rounded-sm bg-primary-dark" style={{ width: `${(s.somaHoras / maior) * 100}%` }} />
                </span>
              </li>
            ))}
          </ul>
        </figure>

        <div>
          <Title level={2} id="deslocamento-soma-tabela" style={{ fontSize: 20 }}>
            Soma de ida e volta por coordenador
          </Title>
          <ResponsiveTable<SomaDoCoordenador>
            aria-labelledby="deslocamento-soma-tabela"
            columns={COLUNAS}
            dataSource={somas}
            rowKey={(s) => s.coordenador.id}
            nomeDaLinha={(s) => s.coordenador.nome}
            pagination={false}
          />
        </div>
      </div>
    </section>
  );
}
