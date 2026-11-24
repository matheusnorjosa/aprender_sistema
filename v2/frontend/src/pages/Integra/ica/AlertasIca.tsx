/**
 * ICA — Alertas (PDF do ICA, seção 6): cada alerta com a data, a situação e para quem seria enviado.
 *
 * Decisão do dono Q12 (24/11/2026): no protótipo, os alertas só aparecem aqui; nada é enviado.
 * Os alertas são recalculados na sessão (`useIntegraDemo`) quando a carteira ou os pesos mudam.
 */
import { useState, type JSX } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';

import { formatFortaleza } from '../../../utils/datetime';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import type { Alerta, TipoAlerta } from './calculo';
import { BotoesExportar } from './componentes/c2/BotoesExportar';
import { dataDoUltimoRecalculo, NOME_DO_ALERTA, situacaoDoAlerta } from './componentes/c2/contas';
import { CLASSE_CAMPO, CLASSE_ROTULO, COR_ESTRATO, formatarDia } from './componentes/estilos';
import { baixarCsv } from './exportar';

const { Title } = Typography;

const TIPOS = Object.keys(NOME_DO_ALERTA) as TipoAlerta[];
const TODOS = 'todos';

/** Fundo e texto da etiqueta do tipo (4,5:1): Sobrecarga na cor do estrato, o resto em cinza. */
function corDoTipo(tipo: TipoAlerta): { fundo: string; texto: string } {
  if (tipo === 'sobrecarga') return COR_ESTRATO.sobrecarga;
  return { fundo: '#F0F0F0', texto: '#3D3D3D' };
}

export default function AlertasIca(): JSX.Element {
  const { alertas, base, historico, versaoVigente, remanejamentos } = useIntegraDemo();
  const [tipo, setTipo] = useState<TipoAlerta | typeof TODOS>(TODOS);

  const ultimoSemestre = historico.at(-1)?.calculado_em ?? versaoVigente.criada_em;
  const quando = dataDoUltimoRecalculo(ultimoSemestre, versaoVigente, remanejamentos);
  const data = quando.length === 10 ? formatarDia(quando) : formatFortaleza(quando, 'DD/MM/YYYY');

  const mostrados = tipo === TODOS ? alertas : alertas.filter((a) => a.tipo === tipo);
  const contagem = (t: TipoAlerta): number => alertas.filter((a) => a.tipo === t).length;

  const baixarPlanilha = (): void =>
    baixarCsv(
      'ica_alertas.csv',
      ['Tipo', 'Alerta', 'Detalhe', 'Data', 'Quando', 'Situação', 'Seria enviado para'],
      mostrados.map((a: Alerta) => [
        NOME_DO_ALERTA[a.tipo],
        a.titulo,
        a.detalhe,
        data,
        a.quando,
        situacaoDoAlerta(a.tipo),
        a.quemReceberia.join(', '),
      ]),
    );

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Alertas
      </Title>
      <p className="mb-4 rounded border-l-4 border-[#004B3D] bg-[#EEF5F3] p-3">
        <strong>Nada é enviado.</strong> No protótipo, os alertas só aparecem nesta tela. Na versão real, cada um iria
        para as pessoas em &ldquo;Seria enviado para&rdquo;. Eles mudam sozinhos quando a carteira ou os pesos mudam
        nesta demonstração.
      </p>

      <Title level={2} id="alertas-resumo" style={{ fontSize: 20 }}>
        {alertas.length === 1 ? '1 alerta' : `${alertas.length} alertas`}
      </Title>
      <ul aria-labelledby="alertas-resumo" className="mb-4 flex list-none flex-wrap gap-x-4 gap-y-1 p-0">
        {TIPOS.map((t) => (
          <li key={t}>
            {NOME_DO_ALERTA[t]}: <strong>{contagem(t)}</strong>
          </li>
        ))}
      </ul>
      <p className="mb-4 text-sm">
        &ldquo;{NOME_DO_ALERTA.sobrecarga}&rdquo; só aparece para quem chegou a 130 ou mais agora. Quem já estava em
        Sobrecarga no cálculo anterior não recebe o aviso de novo e continua em &ldquo;{NOME_DO_ALERTA.fora_da_meta}
        &rdquo; quando passa de 130 (a meta vai até 130). Com 130 exato, fica dentro da meta e sem alerta. O cálculo anterior é o do semestre anterior{historico.at(-2) ? ` (${historico.at(-2)?.semestre})` : ''};
        depois de um remanejamento ou de uma troca de pesos nesta demonstração, é o cálculo publicado
        {historico.at(-1) ? ` de ${historico.at(-1)?.semestre}` : ''}.
      </p>

      <div className="mb-4 max-w-sm print:hidden">
        <label htmlFor="alertas-tipo" className={CLASSE_ROTULO}>
          Mostrar
        </label>
        <select
          id="alertas-tipo"
          className={CLASSE_CAMPO}
          value={tipo}
          onChange={(e) => setTipo(e.target.value as TipoAlerta | typeof TODOS)}
        >
          <option value={TODOS}>Todos os tipos ({alertas.length})</option>
          {TIPOS.map((t) => (
            <option key={t} value={t}>
              {NOME_DO_ALERTA[t]} ({contagem(t)})
            </option>
          ))}
        </select>
      </div>
      {/* O campo "Mostrar" não sai no papel: esta linha diz o que a lista impressa traz. */}
      {tipo !== TODOS && (
        <p className="mb-4 hidden text-sm print:block">
          Mostrando: {NOME_DO_ALERTA[tipo]}, {mostrados.length} de {alertas.length}
        </p>
      )}
      <BotoesExportar aoBaixarPlanilha={baixarPlanilha} />

      {mostrados.length === 0 && <p>Nenhum alerta deste tipo agora.</p>}
      <ul aria-label="Lista de alertas" className="m-0 list-none space-y-3 p-0">
        {mostrados.map((a) => {
          const cor = corDoTipo(a.tipo);
          return (
            <li key={a.id} className="rounded border border-[#8c8c8c] p-3">
              <span
                className="mb-1 inline-block rounded px-2 py-0.5 text-sm font-semibold"
                style={{ background: cor.fundo, color: cor.texto }}
              >
                {NOME_DO_ALERTA[a.tipo]}
              </span>
              <Title level={3} style={{ fontSize: 16, margin: '4px 0' }}>
                {a.titulo}
              </Title>
              <p className="mb-2">{a.detalhe}</p>
              <dl className="m-0 grid gap-x-3 gap-y-1 text-sm sm:grid-cols-[max-content_1fr]">
                <dt className="font-semibold">Data:{' '}</dt>
                <dd className="m-0">{data}</dd>
                <dt className="font-semibold">Quando dispara:{' '}</dt>
                <dd className="m-0">{a.quando}</dd>
                <dt className="font-semibold">Situação:{' '}</dt>
                <dd className="m-0">{situacaoDoAlerta(a.tipo)}</dd>
                <dt className="font-semibold">Seria enviado para:{' '}</dt>
                <dd className="m-0">{a.quemReceberia.join(', ')}</dd>
              </dl>
              {a.coordenadorId !== null && (
                <p className="mb-0 mt-2 text-sm print:hidden">
                  <Link to={`/integra/ica/coordenador/${a.coordenadorId}`}>
                    Ver a ficha de {base.coordenadores.find((c) => c.id === a.coordenadorId)?.nome ?? 'quem recebeu o alerta'}
                  </Link>
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
