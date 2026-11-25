/**
 * Deslocamento — como o tempo é calculado: as regras do relatório (páginas 2 e 3), as faixas, os limites
 * e observações (seção 4) e o que o relatório ainda precisa confirmar (ele diverge de si mesmo em dois
 * pontos; ver o teste de `dados/deslocamento.ts`). Listas, não tabela: o texto é longo e cabe no celular.
 */
import type { JSX } from 'react';
import { Typography } from 'antd';

import { DESLOCAMENTO_MUNICIPIOS, FAIXAS_DESLOCAMENTO, medianaIdaVolta, OBSERVACOES_DESLOCAMENTO, REGRAS_DO_CALCULO } from '../dados/deslocamento';
import { formatarHoras } from '../ica/calculo';
import { EtiquetaFaixa } from './componentes';

const { Title } = Typography;

const TITULO = { fontSize: 20 } as const;

/** Divergências do próprio relatório, para a reunião de validação. */
const PARA_CONFIRMAR: readonly string[] = [
  'O relatório diz que 16 municípios vão só por terra por decisão da gestão, mas o grupo listado soma 23 (17 do Ceará, 2 da Paraíba e 4 avulsos). Aqui, os 23 aparecem marcados. Quais são os 16?',
  'Craíbas-AL tem 18h00 de ida e volta e o relatório a põe em Muito longo. Pelo limite do próprio relatório (Longo até 18h), seria Longo, como Cairu-BA e Indianópolis-MG. Aqui vale a faixa que o relatório escreve.',
  `O relatório calcula a mediana pela coluna Ida e dobra: dá 17h45, o número da página 1. Com a coluna Ida e volta, que o relatório arredondou à parte, a mediana dá ${formatarHoras(medianaIdaVolta(DESLOCAMENTO_MUNICIPIOS))}, e é ela que o ICA usa hoje. Qual coluna o ICA usa para o município sem localidade?`,
];

export default function RegrasDoCalculo(): JSX.Element {
  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Como o tempo é calculado
      </Title>
      <p className="mb-4">As regras são as do relatório da Coordenação Pedagógica. São estimativas, não horários reais.</p>

      <section aria-labelledby="deslocamento-regras" className="mb-6">
        <Title level={2} id="deslocamento-regras" style={TITULO}>
          Regras do cálculo
        </Title>
        <ol aria-label="Regras do cálculo" className="m-0 list-none space-y-3 p-0">
          {REGRAS_DO_CALCULO.map((r) => (
            <li key={r.componente} className="rounded border border-[#d9d9d9] bg-white p-3">
              <strong className="block">{r.componente}</strong>
              <span className="block text-sm">Tempo: {r.tempo}</span>
              <span className="mt-1 block">{r.criterio}</span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="deslocamento-faixas" className="mb-6">
        <Title level={2} id="deslocamento-faixas" style={TITULO}>
          Faixas
        </Title>
        <ul aria-label="Faixas de ida e volta" className="m-0 list-none space-y-2 p-0">
          {FAIXAS_DESLOCAMENTO.map((f) => (
            <li key={f.faixa}>
              <EtiquetaFaixa faixa={f.faixa} />: {f.descricao}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="deslocamento-limites" className="mb-6">
        <Title level={2} id="deslocamento-limites" style={TITULO}>
          Limites e observações
        </Title>
        <ul aria-label="Limites e observações" className="m-0 list-disc space-y-2 pl-5">
          {OBSERVACOES_DESLOCAMENTO.map((o) => (
            <li key={o}>{o}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="deslocamento-confirmar">
        <Title level={2} id="deslocamento-confirmar" style={TITULO}>
          Para confirmar com quem fez o relatório
        </Title>
        <ul aria-label="Para confirmar com quem fez o relatório" className="m-0 list-disc space-y-2 pl-5">
          {PARA_CONFIRMAR.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}
