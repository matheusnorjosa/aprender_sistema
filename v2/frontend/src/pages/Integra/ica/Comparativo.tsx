/**
 * ICA — Comparativo de pesos (PDF do ICA, seção 5): o ICA de cada coordenador calculado com duas
 * versões de pesos, a mesma carteira, e o destaque de quem muda de estrato (como na nota técnica do
 * ICA revisado).
 *
 * As versões são as da sessão: a original (v5), a revisada (nov/2026) e as criadas em "Pesos e
 * faixas". Por padrão, A é a primeira que não é a vigente e B é a vigente.
 * DADOS SIMULADOS: lê a carteira vigente na sessão (`useIntegraDemo`).
 */
import { useMemo, useState, type JSX } from 'react';
import { Link } from 'react-router';
import { Alert, Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import type { Componente } from '../dados/tipos';
import { COMPONENTES, compararPesos, nomeDoEstrato, ROTULO_COMPONENTE, type ComparacaoCoordenador } from './calculo';
import { BarraIca, escalaDoGrafico } from './componentes/BarraIca';
import { FaixasLegendaCurta } from './componentes/FaixasLegenda';
import { BotoesExportar } from './componentes/c2/BotoesExportar';
import { EtiquetaEstrato } from './componentes/EtiquetaEstrato';
import { CLASSE_CAMPO, CLASSE_ROTULO, formatarVariacao } from './componentes/estilos';
import { baixarCsv } from './exportar';

const { Title } = Typography;

function Etiqueta({ r }: { r: ComparacaoCoordenador['antes'] }): JSX.Element {
  return <EtiquetaEstrato estrato={r.conta.estrato} ica={r.conta.icaExibido} semMunicipios={r.semMunicipios} />;
}

function textoDoEstrato(l: ComparacaoCoordenador): string {
  return l.mudouEstrato
    ? `Muda de estrato: ${nomeDoEstrato(l.antes.conta.estrato)} → ${nomeDoEstrato(l.depois.conta.estrato)}`
    : 'Mesmo estrato';
}

const COLUNAS: ColunaResponsiva<ComparacaoCoordenador>[] = [
  {
    title: 'Coordenador',
    key: 'nome',
    render: (_v, l) => <Link to={`/integra/ica/coordenador/${l.coordenadorId}`}>{l.nome}</Link>,
  },
  {
    title: 'ICA com a versão A',
    key: 'a',
    responsive: VISIVEL_A_PARTIR.md,
    render: (_v, l) => <Etiqueta r={l.antes} />,
  },
  {
    title: 'ICA com a versão B',
    key: 'b',
    render: (_v, l) => <Etiqueta r={l.depois} />,
  },
  { title: 'Variação', key: 'variacao', width: 96, responsive: VISIVEL_A_PARTIR.lg, render: (_v, l) => formatarVariacao(l.variacao) },
  {
    title: 'Estrato',
    key: 'estrato',
    responsive: VISIVEL_A_PARTIR.md,
    render: (_v, l) => (l.mudouEstrato ? <strong>{textoDoEstrato(l)}</strong> : textoDoEstrato(l)),
  },
];

interface LinhaPeso {
  componente: Componente;
  a: number;
  b: number;
}

const COLUNAS_PESOS: ColunaResponsiva<LinhaPeso>[] = [
  { title: 'Componente', key: 'componente', render: (_v, l) => ROTULO_COMPONENTE[l.componente] },
  { title: 'Versão A', key: 'a', width: 96, render: (_v, l) => `${l.a}%` },
  { title: 'Versão B', key: 'b', width: 96, render: (_v, l) => `${l.b}%` },
];

export default function Comparativo(): JSX.Element {
  const { base, versoesPesos, versaoVigente } = useIntegraDemo();
  const [escolhaA, setEscolhaA] = useState<string | null>(null);
  const [escolhaB, setEscolhaB] = useState<string | null>(null);

  const idB = escolhaB ?? versaoVigente.id;
  const idA = escolhaA ?? versoesPesos.find((v) => v.id !== idB)?.id ?? idB;
  const versaoA = versoesPesos.find((v) => v.id === idA) ?? versaoVigente;
  const versaoB = versoesPesos.find((v) => v.id === idB) ?? versaoVigente;

  const comparacao = useMemo(() => compararPesos(base, versaoA.pesos, versaoB.pesos), [base, versaoA, versaoB]);
  const linhas = useMemo(
    () => [...comparacao.linhas].sort((x, y) => y.depois.conta.icaExato - x.depois.conta.icaExato),
    [comparacao],
  );
  const mudam = comparacao.mudaramDeEstrato;
  const escala = escalaDoGrafico(mudam.flatMap((l) => [l.antes.conta.icaExibido, l.depois.conta.icaExibido]));
  const pesos: LinhaPeso[] = COMPONENTES.map((c) => ({ componente: c, a: versaoA.pesos[c], b: versaoB.pesos[c] }));

  const baixarPlanilha = (): void =>
    baixarCsv(
      'ica_comparativo_de_pesos.csv',
      [
        'Coordenador',
        `ICA (A: ${versaoA.nome})`,
        'Estrato (A)',
        `ICA (B: ${versaoB.nome})`,
        'Estrato (B)',
        'Variação',
        'Muda de estrato',
      ],
      linhas.map((l) => [
        l.nome,
        l.antes.conta.icaExibido,
        l.antes.semMunicipios ? 'Sem municípios' : nomeDoEstrato(l.antes.conta.estrato),
        l.depois.conta.icaExibido,
        l.depois.semMunicipios ? 'Sem municípios' : nomeDoEstrato(l.depois.conta.estrato),
        l.variacao,
        l.mudouEstrato ? 'Sim' : 'Não',
      ]),
    );

  const seletor = (rotulo: string, id: string, valor: string, mudar: (v: string) => void): JSX.Element => (
    <div className="min-w-0 flex-1 basis-64">
      <label htmlFor={id} className={CLASSE_ROTULO}>
        {rotulo}
      </label>
      <select id={id} className={CLASSE_CAMPO} value={valor} onChange={(e) => mudar(e.target.value)}>
        {versoesPesos.map((v) => (
          <option key={v.id} value={v.id}>
            {v.nome}
            {v.id === versaoVigente.id ? ' — vigente' : ''}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Comparativo de pesos
      </Title>
      <p className="mb-4">
        O ICA de cada coordenador calculado com duas versões de pesos, com a mesma carteira. Quem muda de estrato
        aparece primeiro, em destaque.
      </p>

      <div className="mb-4 flex flex-wrap gap-4 print:hidden">
        {seletor('Versão A', 'comparativo-versao-a', idA, setEscolhaA)}
        {seletor('Versão B', 'comparativo-versao-b', idB, setEscolhaB)}
      </div>
      <p className="mb-4">
        <strong>A:</strong> {versaoA.nome} · <strong>B:</strong> {versaoB.nome}
      </p>
      {idA === idB && (
        <Alert className="mb-4" type="info" showIcon message="As duas versões são a mesma: escolha versões diferentes para comparar." />
      )}
      <BotoesExportar aoBaixarPlanilha={baixarPlanilha} />

      <div className="grid gap-6 xl:grid-cols-2">
        <section aria-labelledby="comparativo-mudam-titulo">
          <Title level={2} id="comparativo-mudam-titulo" style={{ fontSize: 20 }}>
            Quem muda de estrato
          </Title>
          <p className="mb-3">
            {mudam.length === 0
              ? 'Nenhum coordenador muda de estrato entre as duas versões.'
              : `${mudam.length} ${mudam.length === 1 ? 'coordenador muda' : 'coordenadores mudam'} de estrato entre as duas versões.`}
          </p>
          {mudam.length > 0 && <FaixasLegendaCurta />}
          <ul className="m-0 list-none space-y-4 p-0">
            {mudam.map((l) => (
              <li key={l.coordenadorId} className="rounded border border-[#8c8c8c] p-3">
                <strong className="block">{l.nome}</strong>
                <span className="mt-1 flex flex-wrap items-center gap-2 text-sm">
                  <span>Com A:</span>
                  <Etiqueta r={l.antes} />
                  <span>com B:</span>
                  <Etiqueta r={l.depois} />
                </span>
                <div className="mt-2 grid grid-cols-[1.5rem_1fr] items-center gap-x-2 gap-y-1 text-sm">
                  <span aria-hidden="true">A</span>
                  <BarraIca ica={l.antes.conta.icaExibido} estrato={l.antes.conta.estrato} escalaMax={escala} fina />
                  <span aria-hidden="true">B</span>
                  <BarraIca ica={l.depois.conta.icaExibido} estrato={l.depois.conta.estrato} escalaMax={escala} fina />
                </div>
              </li>
            ))}
          </ul>
        </section>

        <div>
          <Title level={2} id="comparativo-pesos-titulo" style={{ fontSize: 20 }}>
            Pesos das duas versões
          </Title>
          <ResponsiveTable<LinhaPeso>
            aria-labelledby="comparativo-pesos-titulo"
            columns={COLUNAS_PESOS}
            dataSource={pesos}
            rowKey={(l) => l.componente}
            nomeDaLinha={(l) => ROTULO_COMPONENTE[l.componente]}
            pagination={false}
          />
        </div>
      </div>

      <Title level={2} id="comparativo-tabela-titulo" style={{ fontSize: 20, marginTop: 32 }}>
        ICA de cada coordenador
      </Title>
      <ResponsiveTable<ComparacaoCoordenador>
        aria-labelledby="comparativo-tabela-titulo"
        columns={COLUNAS}
        dataSource={linhas}
        rowKey={(l) => l.coordenadorId}
        nomeDaLinha={(l) => l.nome}
        pagination={false}
      />
    </section>
  );
}
