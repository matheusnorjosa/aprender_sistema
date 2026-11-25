/**
 * Deslocamento — tempos por município (dados REAIS do relatório de nov/2026).
 *
 * No topo, os números da página 1 do relatório; depois, as faixas (gráfico de barras com o número
 * escrito e a tabela ao lado) e a tabela dos 92 municípios com filtro por estado, faixa e meio de
 * transporte. A tabela é o `ResponsiveTable`: no celular, as colunas que não cabem vão para a linha
 * expandida, sem rolagem horizontal.
 */
import { useMemo, useState, type JSX } from 'react';
import { Typography } from 'antd';
import type { UFCode } from '@/types/organizacao';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import {
  DESLOCAMENTO_MUNICIPIOS,
  FAIXAS_DESLOCAMENTO,
  filtrarDeslocamento,
  type FaixaDeslocamento,
  type MunicipioDeslocamento,
} from '../dados/deslocamento';
import type { MeioDeslocamento } from '../dados/tipos';
import { formatarHoras } from '../ica/calculo';
import { CLASSE_CAMPO, CLASSE_ROTULO } from '../ica/componentes/estilos';
import { EtiquetaFaixa } from './componentes';
import { COR_FAIXA, ROTULO_MEIO } from './estilos';
import { resumoDoRelatorio, ufsNaOrdemDoRelatorio } from './contas';

const { Title } = Typography;

const RESUMO = resumoDoRelatorio(DESLOCAMENTO_MUNICIPIOS);
const UFS = ufsNaOrdemDoRelatorio(DESLOCAMENTO_MUNICIPIOS);
const MAIOR_FAIXA = Math.max(...FAIXAS_DESLOCAMENTO.map((f) => RESUMO.porFaixa[f.faixa]));

const nomeUf = (m: MunicipioDeslocamento): string => `${m.nome}-${m.uf}`;

/** As marcas que o relatório dá ao município, em palavras. */
function marcas(m: MunicipioDeslocamento): string[] {
  const lista: string[] = [];
  if (m.acoes_suspensas) lista.push('Ações suspensas');
  if (m.travessia_maritima) lista.push('Travessia de barco');
  if (m.terrestre_por_decisao_da_gestao) lista.push('Só por terra, por decisão da gestão');
  return lista;
}

const COLUNAS: ColunaResponsiva<MunicipioDeslocamento>[] = [
  { title: 'Município', key: 'municipio', className: 'break-words', render: (_v, m) => nomeUf(m) },
  { title: 'Ida e volta', key: 'ida_volta', width: 100, render: (_v, m) => m.ida_volta_texto },
  { title: 'Faixa', key: 'faixa', width: 120, responsive: VISIVEL_A_PARTIR.sm, render: (_v, m) => <EtiquetaFaixa faixa={m.faixa} /> },
  { title: 'Meio', key: 'meio', width: 80, responsive: VISIVEL_A_PARTIR.md, render: (_v, m) => ROTULO_MEIO[m.meio] },
  { title: 'Ida', key: 'ida', width: 80, responsive: VISIVEL_A_PARTIR.lg, render: (_v, m) => m.ida_texto },
  {
    title: 'Rota',
    key: 'rota',
    className: 'break-words',
    responsive: VISIVEL_A_PARTIR.xl,
    render: (_v, m) => (
      <>
        {m.rota}
        {m.detalhe_rota && <span className="block text-sm text-[#3D3D3D]">{m.detalhe_rota}</span>}
      </>
    ),
  },
  {
    title: 'Observações',
    key: 'marcas',
    className: 'break-words',
    responsive: VISIVEL_A_PARTIR.lg,
    render: (_v, m) => {
      const lista = marcas(m);
      return lista.length === 0 ? '—' : (
        <ul className="m-0 list-none p-0">
          {lista.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      );
    },
  },
  {
    title: 'O outro meio, para comparar',
    key: 'alternativa',
    responsive: VISIVEL_A_PARTIR.detalhe,
    render: (_v, m) => m.alternativa ?? '—',
  },
];

const TODOS = '';

export default function TemposPorMunicipio(): JSX.Element {
  const [uf, setUf] = useState<UFCode | typeof TODOS>(TODOS);
  const [faixa, setFaixa] = useState<FaixaDeslocamento | typeof TODOS>(TODOS);
  const [meio, setMeio] = useState<MeioDeslocamento | typeof TODOS>(TODOS);

  const mostrados = useMemo(
    () =>
      filtrarDeslocamento(DESLOCAMENTO_MUNICIPIOS, {
        ...(uf === TODOS ? {} : { uf }),
        ...(faixa === TODOS ? {} : { faixa }),
        ...(meio === TODOS ? {} : { meio }),
      }),
    [uf, faixa, meio],
  );

  const limpar = (): void => {
    setUf(TODOS);
    setFaixa(TODOS);
    setMeio(TODOS);
  };

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Tempos de deslocamento
      </Title>
      <p className="mb-4">
        Quanto tempo leva ir de Fortaleza a cada município atendido e voltar. A conta não inclui pernoite nem o tempo
        de trabalho no município.
      </p>

      <ul aria-label="Resumo do relatório" className="m-0 mb-3 grid list-none gap-2 p-0 sm:grid-cols-2 lg:grid-cols-3">
        {[
          `${RESUMO.total} municípios`,
          `${RESUMO.porMeio.carro} por terra (carro)`,
          `${RESUMO.porMeio.aviao} de avião (${RESUMO.comConexao} com conexão)`,
          `Mediana: ${RESUMO.medianaDoRelatorio} de ida e volta`,
          `Menor: ${RESUMO.menor.ida_volta_texto} (${nomeUf(RESUMO.menor)})`,
          `Maior: ${RESUMO.maior.ida_volta_texto} (${nomeUf(RESUMO.maior)})`,
        ].map((texto) => (
          <li key={texto} className="rounded border border-[#d9d9d9] bg-white p-3 font-semibold">
            {texto}
          </li>
        ))}
      </ul>
      <p className="mb-6 text-sm">
        O relatório calcula a mediana pela coluna Ida e dobra: dá {RESUMO.medianaDoRelatorio}. Com a coluna Ida e volta,
        que o relatório arredondou à parte, a mediana dá {formatarHoras(RESUMO.medianaCalculada)}.
      </p>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <figure aria-labelledby="deslocamento-faixas-grafico" className="m-0">
          <Title level={2} id="deslocamento-faixas-grafico" style={{ fontSize: 20 }}>
            Municípios por faixa
          </Title>
          <figcaption className="mb-3 text-sm">A faixa considera o tempo de ida e volta.</figcaption>
          <ul className="m-0 list-none space-y-3 p-0">
            {FAIXAS_DESLOCAMENTO.map((f) => (
              <li key={f.faixa}>
                <span className="mb-1 block">
                  {f.rotulo} ({f.descricao}): {RESUMO.porFaixa[f.faixa]}
                </span>
                <span aria-hidden="true" className="block h-4 w-full rounded-sm bg-[#F0F0F0]">
                  <span
                    className="block h-full rounded-sm"
                    style={{ width: `${(RESUMO.porFaixa[f.faixa] / MAIOR_FAIXA) * 100}%`, background: COR_FAIXA[f.faixa].forte }}
                  />
                </span>
              </li>
            ))}
          </ul>
        </figure>

        <table className="w-full border-collapse text-left text-sm">
          <caption className="mb-2 text-left text-xl font-semibold">Municípios por faixa</caption>
          <thead>
            <tr className="border-b border-[#8c8c8c]">
              <th scope="col" className="py-1 pr-2">
                Faixa
              </th>
              <th scope="col" className="py-1 pr-2">
                Limite
              </th>
              <th scope="col" className="py-1 text-right">
                Municípios
              </th>
            </tr>
          </thead>
          <tbody>
            {FAIXAS_DESLOCAMENTO.map((f) => (
              <tr key={f.faixa} className="border-b border-[#d9d9d9]">
                <th scope="row" className="py-1 pr-2 font-normal">
                  <EtiquetaFaixa faixa={f.faixa} />
                </th>
                <td className="py-1 pr-2">{f.descricao}</td>
                <td className="py-1 text-right">{RESUMO.porFaixa[f.faixa]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Title level={2} id="deslocamento-tabela-titulo" style={{ fontSize: 20 }}>
        Tempo de cada município
      </Title>
      <div className="mb-3 grid gap-3 sm:grid-cols-3 print:hidden">
        <div>
          <label htmlFor="deslocamento-uf" className={CLASSE_ROTULO}>
            Estado
          </label>
          <select id="deslocamento-uf" className={CLASSE_CAMPO} value={uf} onChange={(e) => setUf(e.target.value as UFCode | typeof TODOS)}>
            <option value={TODOS}>Todos os estados</option>
            {UFS.map((u) => (
              <option key={u.uf} value={u.uf}>
                {u.uf} ({u.quantidade})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="deslocamento-faixa" className={CLASSE_ROTULO}>
            Faixa
          </label>
          <select
            id="deslocamento-faixa"
            className={CLASSE_CAMPO}
            value={faixa}
            onChange={(e) => setFaixa(e.target.value as FaixaDeslocamento | typeof TODOS)}
          >
            <option value={TODOS}>Todas as faixas</option>
            {FAIXAS_DESLOCAMENTO.map((f) => (
              <option key={f.faixa} value={f.faixa}>
                {f.rotulo} ({f.descricao})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="deslocamento-meio" className={CLASSE_ROTULO}>
            Meio de transporte
          </label>
          <select
            id="deslocamento-meio"
            className={CLASSE_CAMPO}
            value={meio}
            onChange={(e) => setMeio(e.target.value as MeioDeslocamento | typeof TODOS)}
          >
            <option value={TODOS}>Todos</option>
            <option value="carro">{ROTULO_MEIO.carro} (só por terra)</option>
            <option value="aviao">{ROTULO_MEIO.aviao}</option>
          </select>
        </div>
      </div>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <p role="status" className="m-0">
          {mostrados.length === 0
            ? 'Nenhum município com estes filtros.'
            : `Mostrando ${mostrados.length} de ${DESLOCAMENTO_MUNICIPIOS.length} municípios.`}
        </p>
        <button
          type="button"
          onClick={limpar}
          className="rounded border border-[#8c8c8c] bg-white px-3 py-1 text-sm text-[#1f1f1f] hover:border-primary-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark print:hidden"
        >
          Limpar filtros
        </button>
      </div>
      <ResponsiveTable<MunicipioDeslocamento>
        aria-labelledby="deslocamento-tabela-titulo"
        columns={COLUNAS}
        dataSource={mostrados}
        rowKey={nomeUf}
        nomeDaLinha={nomeUf}
        pagination={false}
      />
    </section>
  );
}
