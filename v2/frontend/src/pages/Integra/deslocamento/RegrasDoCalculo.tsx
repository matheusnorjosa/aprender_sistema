/**
 * Deslocamento — como o tempo é calculado: as regras do relatório (páginas 2 e 3), as faixas, os limites
 * e observações (seção 4) e o que o dono decidiu onde o relatório se contradiz ou não diz (decisões 53 a 56,
 * 25/11/2026). Listas, não tabela: o texto é longo e cabe no celular.
 */
import type { JSX } from 'react';
import { Typography } from 'antd';

import { FAIXAS_DESLOCAMENTO, OBSERVACOES_DESLOCAMENTO, REGRAS_DO_CALCULO, TEMPO_DO_MEIO_HORAS } from '../dados/deslocamento';
import { formatarHoras } from '../ica/calculo';
import { EtiquetaFaixa } from './componentes';

const { Title } = Typography;

const TITULO = { fontSize: 20 } as const;

/** O que o dono decidiu em 25/11/2026 onde o relatório se contradiz ou não diz. */
const DECIDIDO_PELO_DONO: readonly string[] = [
  'Só por terra: valem os 23 municípios do grupo que o relatório lista (17 do Ceará, 2 da Paraíba e 4 avulsos), não os 16 da página 1 (decisão 53).',
  'Craíbas-AL (18h00 de ida e volta) fica em Longo, pelo limite do próprio relatório, e não em Muito longo, como a tabela escreve (decisão 54).',
  `O tempo do meio é a mediana que o relatório escreve, ${formatarHoras(TEMPO_DO_MEIO_HORAS)}. O ICA usa esse tempo, marcado como estimado, para o município sem localidade definida (decisão 55). O protótipo usa o mesmo tempo para o local de formação que não está no relatório, como Mauriti-CE do Amigos do Bem (ponto em Para validar).`,
  'Amigos do Bem não tem município fixo: o tempo é o do local de cada formação, que pode ser em AL, CE ou PE (decisão 56).',
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

      <section aria-labelledby="deslocamento-decidido">
        <Title level={2} id="deslocamento-decidido" style={TITULO}>
          O que o dono decidiu sobre o relatório
        </Title>
        <ul aria-label="O que o dono decidiu sobre o relatório" className="m-0 list-disc space-y-2 pl-5">
          {DECIDIDO_PELO_DONO.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}
