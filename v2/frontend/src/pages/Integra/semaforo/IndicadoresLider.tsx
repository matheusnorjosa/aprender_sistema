/**
 * Semáforo — Indicadores da Líder do NFP (seção 7 do PDF do Semáforo): os indicadores que o PDF lista para a
 * Líder (taxa de resposta à pesquisa, reuniões de escuta no período, satisfação média e NPS, municípios em
 * vermelho com o plano de ação no prazo e a distribuição do ICA), quantos municípios em cada cor, por
 * gerência, a evolução das cores ciclo a ciclo e as tarefas das cores publicadas (vencidas e que vencem hoje
 * ou amanhã, com para quem iria o alerta: seção 8, um dia antes e no vencimento). O que o PDF pede e o
 * protótipo não mede fica escrito na tela ("Ainda não medidos no protótipo").
 *
 * O gráfico é feito à mão (barras em CSS) e sempre escreve os números; a tabela ao lado traz os mesmos. Nada
 * rola para o lado: no celular, a tabela por gerência vira lista e a dos ciclos sai (o gráfico já escreve os
 * números). A gerência é a do coordenador do município (cadastro único com o ICA). DADOS SIMULADOS:
 * `useSemaforoDemo`; nada é enviado.
 */
import type { JSX } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';

import { gerarDadosSimulados } from '../dados/gerador';
import { calcularEquipe, META_ICA } from '../ica/calculo';
import { BotoesExportar } from '../ica/componentes/c2/BotoesExportar';
import { formatarDia } from '../ica/componentes/estilos';
import { baixarCsv } from '../ica/exportar';
import { COR_SEMAFORO, CORES, destinatariosDoPrazo, nomeDoMunicipio } from './componentes/corEAlerta';
import { AvisoQuemVe, EtiquetaCor } from './componentes/PecasDoRegistro';
import { mesesCurtosDoCiclo, mesesDoCiclo, SEMENTE_SEMAFORO, type SituacaoMunicipio } from './dados';
import {
  estadoDaTarefa,
  mediaDaPesquisa,
  mediaNps,
  mudancaEntreCiclos,
  respondeuNoPrazo,
  reuniaoEmDia,
  ROTULO_COR,
  somarDias,
  umaCasa,
} from './regras';
import { useSemaforoDemo } from './SemaforoDemoContext';
import type { Cor, EstadoTarefa, RespostaPesquisa } from './tipos';
import { useEstadoDaFicha } from './voltarDaFicha';

const { Title } = Typography;

/** O ICA da mesma semente: o Semáforo não tem cadastro próprio de gerência e lê a distribuição do ICA de lá. */
const ICA = gerarDadosSimulados(SEMENTE_SEMAFORO);
const GERENCIAS = ICA.gerencias;
const SEM_COORDENADOR = 'Sem coordenador';

/** Distribuição do ICA publicado do semestre (pesos em vigor), entre quem tem carteira. */
const DISTRIBUICAO_ICA = (() => {
  const pesos = (ICA.versoes_pesos.find((v) => v.id === ICA.versao_vigente) ?? ICA.versoes_pesos[0]!).pesos;
  const comCarteira = calcularEquipe(ICA.base, pesos).coordenadores.filter((c) => !c.semMunicipios);
  const icas = comCarteira.map((c) => c.conta.icaExibido);
  return {
    total: comCarteira.length,
    dentro: comCarteira.filter((c) => c.conta.dentroDaMeta).length,
    abaixo: icas.filter((i) => i < META_ICA.minimo).length,
    acima: icas.filter((i) => i > META_ICA.maximo).length,
  };
})();

const percentual = (n: number, total: number): string => (total === 0 ? '—' : `${Math.round((n * 100) / total)}%`);
const municipiosTexto = (n: number): string => (n === 1 ? 'município' : 'municípios');

const BORDA = 'border border-[#8c8c8c]';
const CELULA = `${BORDA} p-2`;

type Contagem = Record<Cor, number>;

function contar(cores: readonly (Cor | undefined)[]): Contagem {
  const c: Contagem = { verde: 0, amarelo: 0, vermelho: 0 };
  for (const cor of cores) if (cor) c[cor]++;
  return c;
}

const ESTADOS: readonly { estado: EstadoTarefa; rotulo: string }[] = [
  { estado: 'vencida', rotulo: 'Vencidas' },
  { estado: 'vence_hoje', rotulo: 'Vencem hoje' },
  { estado: 'no_prazo', rotulo: 'No prazo' },
  { estado: 'concluida', rotulo: 'Concluídas' },
];

interface LinhaPorCor {
  rotulo: string;
  contagem: Contagem;
}

interface TabelaPorCorProps {
  legenda: string;
  linhas: readonly LinhaPorCor[];
  primeira: string;
  /** Com a coluna "Municípios" (a soma das cores). */
  comTotal?: boolean;
  /** Abaixo de `sm`, a mesma informação numa lista (a tabela de 5 colunas não cabe a 400 px); sem ela, a tabela some. */
  listaNoCelular?: boolean;
}

/** Nada rola para o lado: a tabela aparece a partir de `sm`; abaixo, a lista ou nada. */
function TabelaPorCor({ legenda, linhas, primeira, comTotal = false, listaNoCelular = false }: TabelaPorCorProps): JSX.Element {
  return (
    <>
      {listaNoCelular && (
        <ul aria-label={legenda} className="m-0 grid list-none gap-2 p-0 sm:hidden">
          {linhas.map((l) => {
            const total = CORES.reduce((soma, c) => soma + l.contagem[c], 0);
            return (
              <li key={l.rotulo} className="rounded border border-[#8c8c8c] p-2 text-sm">
                <strong>{l.rotulo}</strong>: {comTotal && `${total} ${municipiosTexto(total)} · `}
                {CORES.map((c) => `${ROTULO_COR[c]} ${l.contagem[c]}`).join(' · ')}
              </li>
            );
          })}
        </ul>
      )}
      <div className="hidden sm:block">
        <table className="w-full border-collapse text-left text-sm">
          <caption className="mb-2 text-left text-base font-semibold">
            {legenda}
          </caption>
          <thead>
            <tr>
              <th scope="col" className={`${CELULA} bg-[#f5f5f5]`}>
                {primeira}
              </th>
              {comTotal && (
                <th scope="col" className={`${CELULA} bg-[#f5f5f5]`}>
                  Municípios
                </th>
              )}
              {CORES.map((c) => (
                <th key={c} scope="col" className={`${CELULA} bg-[#f5f5f5]`}>
                  {ROTULO_COR[c]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.rotulo}>
                <th scope="row" className={CELULA}>
                  {l.rotulo}
                </th>
                {comTotal && <td className={CELULA}>{CORES.reduce((soma, c) => soma + l.contagem[c], 0)}</td>}
                {CORES.map((c) => (
                  <td key={c} className={CELULA}>
                    {l.contagem[c]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

interface LinhaSatisfacao {
  rotulo: string;
  respostas: readonly RespostaPesquisa[];
}

/** Satisfação média e NPS por grupo (3 colunas estreitas: cabe a 360 px). */
function TabelaSatisfacao({ legenda, primeira, linhas }: { legenda: string; primeira: string; linhas: readonly LinhaSatisfacao[] }): JSX.Element {
  const valor = (n: number | null): string => (n === null ? 'Sem dado' : umaCasa(n));
  return (
    <table className="w-full table-fixed border-collapse text-left text-sm">
      <caption className="mb-2 text-left text-base font-semibold">{legenda}</caption>
      <thead>
        <tr>
          <th scope="col" className={`${CELULA} break-words bg-[#f5f5f5]`}>
            {primeira}
          </th>
          <th scope="col" className={`${CELULA} w-20 bg-[#f5f5f5]`}>
            Média
          </th>
          <th scope="col" className={`${CELULA} w-20 bg-[#f5f5f5]`}>
            NPS
          </th>
        </tr>
      </thead>
      <tbody>
        {linhas.map((l) => (
          <tr key={l.rotulo}>
            <th scope="row" className={`${CELULA} break-words font-normal`}>
              {l.rotulo}
            </th>
            <td className={CELULA}>{valor(mediaDaPesquisa(l.respostas))}</td>
            <td className={CELULA}>{valor(mediaNps(l.respostas))}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function IndicadoresLider(): JSX.Element {
  const { dados, situacoes } = useSemaforoDemo();
  const estadoDaFicha = useEstadoDaFicha();
  const hoje = dados.data_referencia;
  const fechados = dados.ciclos.slice(0, -1);

  const emVigor = contar(situacoes.map((s) => s.cor_vigente));

  // Ciclo fechado: a cor publicada nele; a última linha é a cor em vigor hoje.
  const evolucao: LinhaPorCor[] = [
    ...fechados.map((ciclo, i) => ({
      rotulo: `${ciclo} (${mesesCurtosDoCiclo(ciclo)})`,
      contagem: contar(situacoes.map((s) => s.ciclos[i]?.decisao?.cor_publicada)),
    })),
    { rotulo: `Hoje (${formatarDia(hoje)})`, contagem: emVigor },
  ];

  const gerenciaDe = (s: SituacaoMunicipio): string => {
    const m = dados.municipios.find((x) => x.id === s.municipio);
    const coordenador = dados.coordenadores.find((c) => c.id === m?.coordenador);
    return GERENCIAS.find((g) => g.id === coordenador?.gerencia)?.nome ?? SEM_COORDENADOR;
  };
  const porGerencia = [...GERENCIAS.map((g) => g.nome), SEM_COORDENADOR]
    .map((nome) => {
      const doGrupo = situacoes.filter((s) => gerenciaDe(s) === nome);
      return { rotulo: nome, total: doGrupo.length, contagem: contar(doGrupo.map((s) => s.cor_vigente)) };
    })
    .filter((g) => g.total > 0 || g.rotulo !== SEM_COORDENADOR);

  const municipio = (id: number) => dados.municipios.find((m) => m.id === id);
  const gestoraDe = (id: number): string =>
    dados.pessoas.find((p) => p.id === municipio(id)?.gestora_referencia)?.nome ?? 'Gestora de referência';
  const coordenadorDe = (id: number): string | null =>
    dados.coordenadores.find((c) => c.id === municipio(id)?.coordenador)?.nome ?? null;

  const tarefas = dados.tarefas.map((t) => ({ tarefa: t, estado: estadoDaTarefa(t, hoje) }));
  // Seção 8 do PDF: o alerta de prazo sai um dia antes e no vencimento.
  const amanha = somarDias(hoje, 1);
  const venceAmanha = (t: (typeof tarefas)[number]): boolean => t.estado === 'no_prazo' && t.tarefa.prazo_em === amanha;
  const atrasadas = tarefas
    .filter((t) => t.estado === 'vencida' || t.estado === 'vence_hoje' || venceAmanha(t))
    .sort((a, b) => a.tarefa.prazo_em.localeCompare(b.tarefa.prazo_em));

  const foraDoVerde = situacoes
    .filter((s) => s.cor_vigente !== 'verde')
    .sort((a, b) => (a.cor_vigente === b.cor_vigente ? 0 : a.cor_vigente === 'vermelho' ? -1 : 1));

  // Seção 7 do PDF, indicadores da Líder. A pesquisa conta no último ciclo fechado: no atual, o prazo ainda corre.
  const fechado = fechados.at(-1) ?? dados.ciclo_atual;
  const respostasDe = (ids: ReadonlySet<number>): RespostaPesquisa[] =>
    dados.respostas.filter((r) => r.ciclo === fechado && ids.has(r.municipio));
  const respondeu = (id: number): boolean => respondeuNoPrazo(respostasDe(new Set([id])), true) === true;
  const reuniaoEmDiaDe = (s: SituacaoMunicipio): boolean =>
    reuniaoEmDia(dados.reunioes.filter((x) => x.municipio === s.municipio).map((x) => x.data), s.cor_vigente, hoje);
  const total = situacoes.length;
  const responderam = situacoes.filter((s) => respondeu(s.municipio)).length;
  const reunioesEmDia = situacoes.filter(reuniaoEmDiaDe).length;
  const todasDoCiclo = respostasDe(new Set(dados.municipios.map((m) => m.id)));
  const vermelhos = situacoes.filter((s) => s.cor_vigente === 'vermelho');
  const planoNoPrazo = vermelhos.filter((s) => {
    const plano = dados.tarefas
      .filter((t) => t.municipio === s.municipio && t.chave === 'plano_acao')
      .sort((a, b) => a.criada_em.localeCompare(b.criada_em))
      .at(-1);
    if (!plano) return false;
    return plano.concluida_em === null ? estadoDaTarefa(plano, hoje) !== 'vencida' : plano.concluida_em <= plano.prazo_em;
  }).length;
  const naMeta = (ok: boolean): string => (ok ? 'na meta' : 'fora da meta');

  const indicadores: { titulo: string; valor: string; meta: string | null }[] = [
    {
      titulo: `Taxa de resposta à pesquisa (ciclo ${fechado}, ${mesesCurtosDoCiclo(fechado)})`,
      valor: `${responderam} de ${total} ${municipiosTexto(total)} (${percentual(responderam, total)}) responderam no prazo`,
      meta: `80% ou mais: ${naMeta(responderam * 100 >= total * 80)}`,
    },
    {
      titulo: 'Reuniões de escuta no período previsto (6 meses no verde, 3 no amarelo e no vermelho)',
      valor: `${reunioesEmDia} de ${total} ${municipiosTexto(total)} (${percentual(reunioesEmDia, total)}) com a reunião em dia`,
      meta: `100%: ${naMeta(reunioesEmDia === total)}`,
    },
    {
      titulo: `Satisfação média e NPS (ciclo ${fechado}, todas as respostas)`,
      valor: `Média ${mediaDaPesquisa(todasDoCiclo) === null ? 'sem dado' : umaCasa(mediaDaPesquisa(todasDoCiclo)!)} · NPS ${mediaNps(todasDoCiclo) === null ? 'sem dado' : umaCasa(mediaNps(todasDoCiclo)!)}`,
      meta: null,
    },
    {
      titulo: 'Municípios em vermelho com o plano de ação no prazo',
      valor:
        vermelhos.length === 0
          ? 'Nenhum município em vermelho'
          : `${planoNoPrazo} de ${vermelhos.length} ${municipiosTexto(vermelhos.length)} em vermelho`,
      meta: vermelhos.length === 0 ? null : `todos: ${naMeta(planoNoPrazo === vermelhos.length)}`,
    },
    {
      titulo: `Distribuição do ICA (semestre ${ICA.semestre_atual}, o ICA publicado)`,
      valor: `${DISTRIBUICAO_ICA.dentro} de ${DISTRIBUICAO_ICA.total} coordenadores entre ${META_ICA.minimo} e ${META_ICA.maximo} · ${DISTRIBUICAO_ICA.abaixo} abaixo de ${META_ICA.minimo} · ${DISTRIBUICAO_ICA.acima} acima de ${META_ICA.maximo}`,
      meta: `entre ${META_ICA.minimo} e ${META_ICA.maximo}: ${naMeta(DISTRIBUICAO_ICA.dentro === DISTRIBUICAO_ICA.total)}`,
    },
  ];

  const grupoDe = (chave: (m: (typeof dados.municipios)[number]) => number | null, id: number): ReadonlySet<number> =>
    new Set(dados.municipios.filter((m) => chave(m) === id).map((m) => m.id));
  const satisfacaoPorCoordenador: LinhaSatisfacao[] = [...dados.coordenadores]
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
    .map((c) => ({ rotulo: c.nome, respostas: respostasDe(grupoDe((m) => m.coordenador, c.id)) }));
  const satisfacaoPorGestora: LinhaSatisfacao[] = [...dados.pessoas]
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
    .map((p) => ({ rotulo: p.nome, respostas: respostasDe(grupoDe((m) => m.gestora_referencia, p.id)) }));

  const baixarPlanilha = (): void =>
    baixarCsv(
      'semaforo_indicadores_lider.csv',
      [
        'Município',
        'UF',
        'Gerência',
        'Coordenador',
        'Gestora de referência',
        'Cor em vigor',
        'Cor sugerida agora',
        ...fechados.map((c) => `Publicada em ${c}`),
        `Média da pesquisa (${fechado})`,
        `NPS (${fechado})`,
        `Respondeu no prazo (${fechado})`,
        'Reunião de escuta em dia',
      ],
      situacoes.map((s) => {
        const m = municipio(s.municipio);
        const publicada = (i: number) => s.ciclos[i]?.decisao?.cor_publicada;
        const respostas = respostasDe(new Set([s.municipio]));
        const media = mediaDaPesquisa(respostas);
        const nps = mediaNps(respostas);
        return [
          m?.nome ?? '',
          m?.uf ?? '',
          gerenciaDe(s),
          dados.coordenadores.find((c) => c.id === m?.coordenador)?.nome ?? 'Sem coordenador',
          gestoraDe(s.municipio),
          ROTULO_COR[s.cor_vigente],
          ROTULO_COR[s.ciclos.at(-1)?.resultado.cor ?? 'verde'],
          ...fechados.map((_c, i) => {
            const cor = publicada(i);
            return cor ? ROTULO_COR[cor] : 'Não publicada';
          }),
          media === null ? 'Sem dado' : umaCasa(media),
          nps === null ? 'Sem dado' : umaCasa(nps),
          respondeu(s.municipio) ? 'Sim' : 'Não',
          reuniaoEmDiaDe(s) ? 'Sim' : 'Não',
        ];
      }),
    );

  return (
    <section aria-labelledby="integra-titulo-tela">
      <Title level={1} id="integra-titulo-tela" style={{ fontSize: 26, marginBottom: 8 }}>
        Indicadores da Líder do NFP
      </Title>
      <AvisoQuemVe tela="lider" />
      <p className="mb-4">
        Retrato de hoje, {formatarDia(hoje)}, com o ciclo {dados.ciclo_atual} ({mesesDoCiclo(dados.ciclo_atual)}) em
        andamento. As cores desta tela são as publicadas pelo Comitê: mudam quando ele publica. Um registro novo nesta
        demonstração muda só a cor sugerida, que aparece na ficha do município e na planilha.
      </p>
      <BotoesExportar aoBaixarPlanilha={baixarPlanilha} />

      <section aria-labelledby="lider-secao-7" className="mb-6">
        <Title level={2} id="lider-secao-7" style={{ fontSize: 20 }}>
          Indicadores e metas do PDF
        </Title>
        <ul aria-label="Indicadores da seção 7 do PDF" className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
          {indicadores.map((i) => (
            <li key={i.titulo} className="rounded border border-[#8c8c8c] p-3">
              <strong className="block">{i.titulo}</strong>
              <span className="block">{i.valor}</span>
              {i.meta && <span className="block text-sm">Meta: {i.meta}</span>}
            </li>
          ))}
        </ul>
      </section>

      <Title level={2} id="lider-em-vigor" style={{ fontSize: 20 }}>
        Cor em vigor hoje
      </Title>
      <ul aria-label="Municípios por cor em vigor" className="mb-4 flex list-none flex-wrap gap-3 p-0">
        {CORES.map((c) => (
          <li key={c} className="rounded border border-[#8c8c8c] px-3 py-2">
            <EtiquetaCor cor={c} />: <strong>{emVigor[c]}</strong> {emVigor[c] === 1 ? 'município' : 'municípios'}
          </li>
        ))}
      </ul>
      {foraDoVerde.length > 0 && (
        <>
          <Title level={3} id="lider-fora-do-verde" style={{ fontSize: 16 }}>
            Em amarelo e vermelho
          </Title>
          <ul aria-labelledby="lider-fora-do-verde" className="mb-6 grid list-none gap-2 p-0 sm:grid-cols-2 xl:grid-cols-3">
            {foraDoVerde.map((s) => {
              const m = municipio(s.municipio);
              const publicadas = s.ciclos.filter((c) => c.decisao !== null);
              const anterior = publicadas.at(-2)?.decisao?.cor_publicada ?? null;
              const seta = mudancaEntreCiclos(anterior, s.cor_vigente);
              return (
                <li key={s.municipio} className="flex flex-wrap items-center gap-2">
                  <EtiquetaCor cor={s.cor_vigente} />
                  <Link to={`/integra/semaforo/municipio/${s.municipio}`} state={estadoDaFicha}>{m ? nomeDoMunicipio(m) : s.municipio}</Link>
                  <span className="text-sm">
                    {seta.seta && <span aria-hidden="true">{seta.seta} </span>}
                    {seta.texto}
                  </span>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        <figure aria-labelledby="lider-evolucao" className="m-0">
          <Title level={2} id="lider-evolucao" style={{ fontSize: 20 }}>
            Evolução das cores por ciclo
          </Title>
          <figcaption className="mb-3 text-sm">
            Quantos municípios o Comitê publicou em cada cor, ciclo a ciclo. A última barra é a cor em vigor hoje.
          </figcaption>
          <ul className="m-0 list-none space-y-3 p-0">
            {evolucao.map((l) => {
              const total = CORES.reduce((s, c) => s + l.contagem[c], 0);
              return (
                <li key={l.rotulo}>
                  <p className="m-0 mb-1 text-sm">
                    <span className="font-semibold">{l.rotulo}</span>: Verde {l.contagem.verde} · Amarelo {l.contagem.amarelo} ·
                    Vermelho {l.contagem.vermelho}
                  </p>
                  <div aria-hidden="true" className="flex h-4 w-full overflow-hidden rounded border border-[#8c8c8c] bg-white">
                    {/* Os tons forte têm quase a mesma luminância (1,05:1 entre vizinhos): a divisória branca separa as cores. */}
                    {CORES.filter((c) => l.contagem[c] > 0).map((c, i) => (
                      <div
                        key={c}
                        style={{
                          width: `${(l.contagem[c] / total) * 100}%`,
                          background: COR_SEMAFORO[c].forte,
                          ...(i > 0 && { borderLeft: '2px solid #ffffff' }),
                        }}
                      />
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
        </figure>
        <div>
          <TabelaPorCor legenda="Cor publicada em cada ciclo" linhas={evolucao} primeira="Ciclo" />
        </div>
      </div>

      <Title level={2} id="lider-gerencias" style={{ fontSize: 20, marginTop: 32 }}>
        Por gerência
      </Title>
      <p className="mb-2 text-sm">A gerência é a do coordenador do município. Município sem coordenador fica à parte.</p>
      <div className="max-w-2xl">
        <TabelaPorCor
          legenda="Municípios por gerência, pela cor em vigor"
          linhas={porGerencia}
          primeira="Gerência"
          comTotal
          listaNoCelular
        />
      </div>

      <section aria-labelledby="lider-satisfacao" className="mt-8">
        <Title level={2} id="lider-satisfacao" style={{ fontSize: 20 }}>
          Satisfação por coordenador e por gestora de referência
        </Title>
        <p className="mb-2 text-sm">
          Média dos 6 itens da pesquisa e média das notas de recomendação (NPS), no ciclo {fechado} (
          {mesesDoCiclo(fechado)}). Por município, a planilha traz os dois números.
        </p>
        <div className="grid gap-6 lg:grid-cols-2">
          <TabelaSatisfacao legenda={`Satisfação por coordenador, ciclo ${fechado}`} primeira="Coordenador" linhas={satisfacaoPorCoordenador} />
          <TabelaSatisfacao
            legenda={`Satisfação por gestora de referência, ciclo ${fechado}`}
            primeira="Gestora de referência"
            linhas={satisfacaoPorGestora}
          />
        </div>
      </section>

      <section aria-labelledby="lider-nao-medidos" className="mt-8">
        <Title level={2} id="lider-nao-medidos" style={{ fontSize: 20 }}>
          Ainda não medidos no protótipo
        </Title>
        <ul aria-label="Ainda não medidos no protótipo" className="m-0 pl-5">
          <li>
            Tempo médio de resposta a ocorrências (meta: 48 h ou menos): as ocorrências do protótipo não guardam quando
            foram respondidas.
          </li>
          <li>Convergência entre a pesquisa e as ocorrências: o PDF não diz como medir.</li>
          <li>Satisfação média e NPS por projeto: a pesquisa do protótipo não diz que projeto o articulador avalia.</li>
        </ul>
        <p className="mt-2 text-sm">Estão também em &ldquo;Para validar no dia 7&rdquo;.</p>
      </section>

      <section aria-labelledby="lider-tarefas" className="mt-8">
        <Title level={2} id="lider-tarefas" style={{ fontSize: 20 }}>
          Tarefas das cores publicadas
        </Title>
        <ul aria-label="Tarefas por situação" className="mb-4 flex list-none flex-wrap gap-x-4 gap-y-1 p-0">
          {ESTADOS.map(({ estado, rotulo }) => (
            <li key={estado}>
              {rotulo}: <strong>{tarefas.filter((t) => t.estado === estado).length}</strong>
            </li>
          ))}
        </ul>
        <p className="mb-4 rounded border-l-4 border-primary-dark bg-[#EEF5F3] p-3">
          <strong>Nada é enviado.</strong> No protótipo, os alertas de prazo só aparecem nesta tela. Na versão real, cada
          um iria para as pessoas em &ldquo;Seria enviado para&rdquo;.
        </p>
        <Title level={3} id="lider-atrasadas" style={{ fontSize: 16 }}>
          Vencidas e que vencem hoje ou amanhã
        </Title>
        {atrasadas.length === 0 ? (
          <p>Nenhuma tarefa vencida ou vencendo hoje ou amanhã.</p>
        ) : (
          <ul aria-labelledby="lider-atrasadas" className="m-0 list-none space-y-3 p-0">
            {atrasadas.map(({ tarefa: t, estado }) => {
              const situacao = estado === 'vencida' ? 'Vencida' : estado === 'vence_hoje' ? 'Vence hoje' : 'Vence amanhã';
              const m = municipio(t.municipio);
              const nome = m ? nomeDoMunicipio(m) : String(t.municipio);
              return (
                <li key={`${t.municipio}-${t.chave}-${t.criada_em}`} className="rounded border border-[#8c8c8c] p-3">
                  <strong className="block">
                    {t.titulo} · {nome}
                  </strong>
                  <dl className="m-0 mt-1 grid gap-x-3 gap-y-1 text-sm sm:grid-cols-[max-content_1fr]">
                    <dt className="font-semibold">Situação:{' '}</dt>
                    <dd className="m-0">{situacao}</dd>
                    <dt className="font-semibold">Prazo:{' '}</dt>
                    <dd className="m-0">{formatarDia(t.prazo_em)}</dd>
                    <dt className="font-semibold">Cor publicada:{' '}</dt>
                    <dd className="m-0">
                      <EtiquetaCor cor={t.cor} /> em {formatarDia(t.criada_em)}
                    </dd>
                    <dt className="font-semibold">Seria enviado para:{' '}</dt>
                    <dd className="m-0">
                      {destinatariosDoPrazo(t.cor, gestoraDe(t.municipio), coordenadorDe(t.municipio)).join(', ')}
                    </dd>
                  </dl>
                  <p className="mb-0 mt-2 text-sm">
                    <Link to={`/integra/semaforo/municipio/${t.municipio}`} state={estadoDaFicha}>Abrir a ficha de {nome}</Link>
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </section>
  );
}
