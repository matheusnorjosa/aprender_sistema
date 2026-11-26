/**
 * Semáforo — Indicadores da Líder do NFP (seção 7 do PDF do Semáforo): os indicadores que o PDF lista para a
 * Líder (taxa de resposta à pesquisa, reuniões de escuta no período, satisfação média e NPS, municípios em
 * vermelho com o plano de ação no prazo e a distribuição do ICA), quantos municípios em cada cor, por
 * gerência, a evolução das cores ciclo a ciclo e as tarefas de cada cor (vencidas e que vencem hoje
 * ou amanhã, com para quem iria o alerta: seção 8, um dia antes e no vencimento).
 *
 * Decisões do dono de 25/11: a nota de recomendação com a maior, a menor e a média (31); a taxa de resposta e a
 * satisfação por projeto (46 e 51); a convergência entre a pesquisa e as ocorrências, com a lista dos que
 * divergem (49); e o tempo médio de resposta às ocorrências contra a meta de 48 h (50). As tarefas canceladas
 * pelo Comitê e as substituídas continuam contadas (57).
 *
 * O gráfico é feito à mão (barras em CSS) e sempre escreve os números; a tabela ao lado traz os mesmos. Nada
 * rola para o lado: no celular, a tabela por gerência vira lista e a dos ciclos sai (o gráfico já escreve os
 * números). A gerência é a do coordenador de cada projeto do município (cadastro único com o ICA): o município
 * com projetos de gerências diferentes conta em cada uma (decisão 46). DADOS SIMULADOS:
 * `useSemaforoDemo`; nada é enviado.
 */
import type { JSX, ReactNode } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';

import { gerarDadosSimulados } from '../dados/gerador';
import { calcularEquipe, META_ICA } from '../ica/calculo';
import { BotoesExportar } from '../ica/componentes/c2/BotoesExportar';
import { formatarDia } from '../ica/componentes/estilos';
import { baixarCsv } from '../ica/exportar';
import { COR_SEMAFORO, coordenadoresDoMunicipio, CORES, destinatariosDoPrazo, nasceuNaHora, nomeDoMunicipio } from './componentes/corEAlerta';
import { AvisoQuemVe, EtiquetaCor } from './componentes/PecasDoRegistro';
import { convergencia, mesesCurtosDoCiclo, mesesDoCiclo, SEMENTE_SEMAFORO, type SituacaoMunicipio } from './dados';
import {
  duasCasas,
  estadoDaTarefa,
  horasEntre,
  lista,
  mediaDaPesquisa,
  META_RESPOSTA_HORAS,
  mudancaEntreCiclos,
  respondeuNoPrazo,
  resumoNps,
  reuniaoEmDia,
  ROTULO_COR,
  somarDias,
  somarDiasUteis,
  tempoDeResposta,
  textoHoras,
  textoResumoNps,
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
  // Decisão 57: a tarefa que deixou de valer continua guardada e contada.
  { estado: 'cancelada_comite', rotulo: 'Canceladas pelo Comitê' },
  { estado: 'substituida', rotulo: 'Substituídas' },
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

/** A nota de recomendação: a média (que dá a cor) e, embaixo, a maior e a menor (decisão 31). */
function CelulaNps({ respostas }: { respostas: readonly RespostaPesquisa[] }): JSX.Element {
  const nps = resumoNps(respostas);
  if (!nps) return <>Sem dado</>;
  return (
    <>
      {duasCasas(nps.media)}{' '}
      <span className="block text-xs">
        maior {nps.maior}, menor {nps.menor}
      </span>
    </>
  );
}

/** Satisfação média e NPS por grupo (3 colunas estreitas: cabe a 360 px). */
function TabelaSatisfacao({ legenda, primeira, linhas }: { legenda: string; primeira: string; linhas: readonly LinhaSatisfacao[] }): JSX.Element {
  const valor = (n: number | null): string => (n === null ? 'Sem dado' : duasCasas(n));
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
          <th scope="col" className={`${CELULA} w-28 bg-[#f5f5f5]`}>
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
            <td className={CELULA}>
              <CelulaNps respostas={l.respostas} />
            </td>
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

  // Decisão 46: cada projeto tem o seu coordenador; o município conta na gerência de cada um deles.
  const gerenciasDe = (s: SituacaoMunicipio): string[] => {
    const m = dados.municipios.find((x) => x.id === s.municipio);
    const nomes = coordenadoresDoMunicipio(m, dados.coordenadores).flatMap(
      (c) => GERENCIAS.filter((g) => g.id === c.gerencia).map((g) => g.nome),
    );
    return nomes.length === 0 ? [SEM_COORDENADOR] : [...new Set(nomes)];
  };
  const porGerencia = [...GERENCIAS.map((g) => g.nome), SEM_COORDENADOR]
    .map((nome) => {
      const doGrupo = situacoes.filter((s) => gerenciasDe(s).includes(nome));
      return { rotulo: nome, total: doGrupo.length, contagem: contar(doGrupo.map((s) => s.cor_vigente)) };
    })
    .filter((g) => g.total > 0 || g.rotulo !== SEM_COORDENADOR);

  const municipio = (id: number) => dados.municipios.find((m) => m.id === id);
  const gestoraDe = (id: number): string =>
    dados.pessoas.find((p) => p.id === municipio(id)?.gestora_referencia)?.nome ?? 'Gestora de referência';
  const coordenadoresDe = (id: number): string[] => coordenadoresDoMunicipio(municipio(id), dados.coordenadores).map((c) => c.nome);

  const tarefas = dados.tarefas.map((t) => ({ tarefa: t, estado: estadoDaTarefa(t, hoje) }));
  // Seção 8 do PDF: o alerta de prazo sai um dia antes e no vencimento. Rodada 4 (leitura em Para validar): com os
  // prazos em dias úteis (decisões 33 e 34), "um dia antes" é o dia útil anterior; na sexta, avisa o que vence na segunda.
  const amanha = somarDiasUteis(hoje, 1);
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
  const respostasDosProjetos = (ids: ReadonlySet<number>): RespostaPesquisa[] =>
    dados.respostas.filter((r) => r.ciclo === fechado && ids.has(r.projeto));
  // Decisão 51: a pesquisa é por projeto; o município respondeu quando todos os projetos dele responderam no prazo.
  const respondeu = (id: number): boolean =>
    (municipio(id)?.projetos ?? []).every((p) => respondeuNoPrazo(respostasDosProjetos(new Set([p.id])), true) === true);
  const reuniaoEmDiaDe = (s: SituacaoMunicipio): boolean =>
    reuniaoEmDia(dados.reunioes.filter((x) => x.municipio === s.municipio).map((x) => x.data), s.cor_vigente, hoje);
  const total = situacoes.length;
  const responderam = situacoes.filter((s) => respondeu(s.municipio)).length;
  const reunioesEmDia = situacoes.filter(reuniaoEmDiaDe).length;
  const todasDoCiclo = respostasDe(new Set(dados.municipios.map((m) => m.id)));
  const vermelhos = situacoes.filter((s) => s.cor_vigente === 'vermelho');
  const planoNoPrazo = vermelhos.filter((s) => {
    // A tarefa cancelada ou substituída deixou de valer (decisões 42 e 43): vale o plano em aberto ou feito.
    const plano = dados.tarefas
      .filter((t) => t.municipio === s.municipio && t.chave === 'plano_acao' && t.encerramento === null)
      .sort((a, b) => a.criada_em.localeCompare(b.criada_em))
      .at(-1);
    if (!plano) return false;
    return plano.concluida_em === null ? estadoDaTarefa(plano, hoje) !== 'vencida' : plano.concluida_em <= plano.prazo_em;
  }).length;
  const naMeta = (ok: boolean): string => (ok ? 'na meta' : 'fora da meta');

  // Decisão 50: as ocorrências do ano do calendário, de 1º de janeiro até hoje, inclusive as de antes da 1ª formação
  // (que não contam na cor): a resposta ao município vale para todas. A Para validar diz isso.
  const ano = hoje.slice(0, 4);
  const ocorrenciasDoAno = dados.ocorrencias.filter((o) => o.data.startsWith(`${ano}-`));
  const tempo = tempoDeResposta(ocorrenciasDoAno);
  const foraDaMeta = ocorrenciasDoAno
    .flatMap((o) => (o.respondida_em === null ? [] : [{ o, horas: horasEntre(o.registrada_em, o.respondida_em) }]))
    .filter(({ horas }) => horas > META_RESPOSTA_HORAS)
    .map(({ o, horas }) => {
      const m = municipio(o.municipio);
      return `${m ? nomeDoMunicipio(m) : o.municipio} (${textoHoras(horas)})`;
    });
  // Decisão 49: no último ciclo fechado, a cor da pesquisa contra a cor das ocorrências.
  const conv = convergencia(dados, situacoes);
  const satisfacaoGeral = resumoNps(todasDoCiclo);

  const indicadores: { titulo: string; valor: string; meta: string | null; extra?: ReactNode }[] = [
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
      valor: `Média ${mediaDaPesquisa(todasDoCiclo) === null ? 'sem dado' : duasCasas(mediaDaPesquisa(todasDoCiclo)!)} · NPS: ${satisfacaoGeral ? textoResumoNps(satisfacaoGeral) : 'sem dado'}`,
      meta: null,
    },
    {
      titulo: `Tempo médio de resposta a ocorrências (${ano})`,
      valor:
        tempo.media_horas === null
          ? `Nenhuma ocorrência respondida em ${ano}; ${tempo.sem_resposta} sem resposta`
          : `${textoHoras(tempo.media_horas)} em média (${tempo.respondidas} respondidas: ${tempo.dentro_da_meta} em até ${META_RESPOSTA_HORAS} h e ${tempo.fora_da_meta} fora da meta; ${tempo.sem_resposta} sem resposta)`,
      meta:
        tempo.media_horas === null
          ? null
          : `${META_RESPOSTA_HORAS} h corridas ou menos em média: ${naMeta(tempo.media_horas <= META_RESPOSTA_HORAS)}`,
      extra: foraDaMeta.length > 0 && <span className="block text-sm">Fora da meta: {foraDaMeta.join(', ')}</span>,
    },
    {
      titulo: `Convergência entre a pesquisa e as ocorrências (ciclo ${conv.ciclo}, ${mesesCurtosDoCiclo(conv.ciclo)})`,
      valor:
        conv.percentual === null
          ? 'Nenhum município com pesquisa no ciclo'
          : `${conv.concordam} de ${conv.comparados} ${municipiosTexto(conv.comparados)} (${percentual(conv.concordam, conv.comparados)}) com a pesquisa e as ocorrências de acordo`,
      meta: null,
      extra: (
        <>
          <span className="block text-sm">
            Divergem quando uma está verde e a outra vermelha. Quem não respondeu a pesquisa fica fora da conta.
          </span>
          {conv.divergentes.length === 0 ? (
            <span className="block text-sm">Nenhum município diverge.</span>
          ) : (
            <ul aria-label="Municípios em que a pesquisa e as ocorrências divergem" className="m-0 mt-1 pl-5 text-sm">
              {conv.divergentes.map((d) => {
                const m = municipio(d.municipio);
                return (
                  <li key={d.municipio}>
                    <Link to={`/integra/semaforo/municipio/${d.municipio}`} state={estadoDaFicha}>
                      {m ? nomeDoMunicipio(m) : d.municipio}
                    </Link>
                    : pesquisa <EtiquetaCor cor={d.pesquisa} />, ocorrências <EtiquetaCor cor={d.ocorrencias} />
                  </li>
                );
              })}
            </ul>
          )}
        </>
      ),
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
  // Decisão 46: a resposta é de um projeto, e o projeto é que tem o coordenador.
  const todosOsProjetos = dados.municipios.flatMap((m) => m.projetos);
  const projetosDe = (filtro: (p: (typeof todosOsProjetos)[number]) => boolean): ReadonlySet<number> =>
    new Set(todosOsProjetos.filter(filtro).map((p) => p.id));
  const satisfacaoPorCoordenador: LinhaSatisfacao[] = [...dados.coordenadores]
    .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
    .map((c) => ({ rotulo: c.nome, respostas: respostasDosProjetos(projetosDe((p) => p.coordenador === c.id)) }));
  // Decisão 51: a satisfação por projeto junta as respostas dos projetos com o mesmo nome (a mesma coleção).
  const satisfacaoPorProjeto: LinhaSatisfacao[] = [...new Set(todosOsProjetos.map((p) => p.nome))]
    .sort((a, b) => a.localeCompare(b, 'pt-BR'))
    .map((nome) => ({ rotulo: nome, respostas: respostasDosProjetos(projetosDe((p) => p.nome === nome)) }));
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
        `NPS maior (${fechado})`,
        `NPS menor (${fechado})`,
        `Respondeu no prazo (${fechado})`,
        'Reunião de escuta em dia',
      ],
      situacoes.map((s) => {
        const m = municipio(s.municipio);
        const publicada = (i: number) => s.ciclos[i]?.decisao?.cor_publicada;
        const respostas = respostasDe(new Set([s.municipio]));
        const media = mediaDaPesquisa(respostas);
        const nps = resumoNps(respostas);
        return [
          m?.nome ?? '',
          m?.uf ?? '',
          lista(gerenciasDe(s)),
          lista(coordenadoresDe(s.municipio)) || 'Sem coordenador',
          gestoraDe(s.municipio),
          ROTULO_COR[s.cor_vigente],
          ROTULO_COR[s.ciclos.at(-1)?.resultado.cor ?? 'verde'],
          ...fechados.map((_c, i) => {
            const cor = publicada(i);
            return cor ? ROTULO_COR[cor] : 'Não publicada';
          }),
          media === null ? 'Sem dado' : duasCasas(media),
          nps === null ? 'Sem dado' : duasCasas(nps.media),
          nps === null ? 'Sem dado' : nps.maior,
          nps === null ? 'Sem dado' : nps.menor,
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
        andamento. As cores desta tela são as em vigor: as publicadas pelo Comitê e o vermelho na hora, porque um
        indicador em vermelho ou três amarelos mudam a cor em vigor assim que o dado chega. As outras mudanças
        aparecem como cor sugerida, na ficha do município e na planilha, até o Comitê publicar.
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
              {i.extra}
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
              // Rodada 3: a mesma referência da ficha (a decisão do ciclo anterior × a cor deste ciclo), e a tela diz qual.
              const atual = s.ciclos.at(-1)!;
              const anterior = s.ciclos.at(-2) ?? null;
              const seta = mudancaEntreCiclos(anterior?.decisao?.cor_publicada ?? null, atual.decisao?.cor_publicada ?? atual.resultado.cor);
              return (
                <li key={s.municipio} className="flex flex-wrap items-center gap-2">
                  <EtiquetaCor cor={s.cor_vigente} />
                  <Link to={`/integra/semaforo/municipio/${s.municipio}`} state={estadoDaFicha}>{m ? nomeDoMunicipio(m) : s.municipio}</Link>
                  <span className="text-sm">
                    {seta.seta && <span aria-hidden="true">{seta.seta} </span>}
                    {seta.texto}
                    {anterior && ` desde o ciclo ${anterior.ciclo}`}
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
            Quantos municípios ficaram em cada cor, ciclo a ciclo: a última decisão de cada ciclo, do Comitê ou o
            vermelho na hora. A última barra é a cor em vigor hoje.
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
      <p className="mb-2 text-sm">
        Cada projeto tem o seu coordenador: o município conta na gerência de cada coordenador dos seus projetos (com
        projetos de gerências diferentes, aparece em cada uma). Município sem coordenador fica à parte.
      </p>
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
          Satisfação por projeto, por coordenador e por gestora de referência
        </Title>
        <p className="mb-2 text-sm">
          Média dos 6 itens da pesquisa e nota de recomendação (NPS: a média, que dá a cor, com a maior e a menor
          nota), no ciclo {fechado} ({mesesDoCiclo(fechado)}). A pesquisa é por projeto: cada projeto do município
          tem a sua resposta. Por município, a planilha traz os números.
        </p>
        <div className="grid gap-6 lg:grid-cols-2">
          <TabelaSatisfacao legenda={`Satisfação por projeto, ciclo ${fechado}`} primeira="Projeto" linhas={satisfacaoPorProjeto} />
          <TabelaSatisfacao legenda={`Satisfação por coordenador, ciclo ${fechado}`} primeira="Coordenador" linhas={satisfacaoPorCoordenador} />
          <TabelaSatisfacao
            legenda={`Satisfação por gestora de referência, ciclo ${fechado}`}
            primeira="Gestora de referência"
            linhas={satisfacaoPorGestora}
          />
        </div>
      </section>

      <section aria-labelledby="lider-tarefas" className="mt-8">
        <Title level={2} id="lider-tarefas" style={{ fontSize: 20 }}>
          Tarefas de cada cor
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
              const situacao =
                estado === 'vencida'
                  ? 'Vencida'
                  : estado === 'vence_hoje'
                    ? 'Vence hoje'
                    : t.prazo_em === somarDias(hoje, 1)
                      ? 'Vence amanhã'
                      : 'Vence no próximo dia útil';
              const m = municipio(t.municipio);
              const nome = m ? nomeDoMunicipio(m) : String(t.municipio);
              return (
                <li key={t.id} className="rounded border border-[#8c8c8c] p-3">
                  <strong className="block">
                    {t.titulo} · {nome}
                  </strong>
                  <dl className="m-0 mt-1 grid gap-x-3 gap-y-1 text-sm sm:grid-cols-[max-content_1fr]">
                    <dt className="font-semibold">Situação:{' '}</dt>
                    <dd className="m-0">{situacao}</dd>
                    <dt className="font-semibold">Prazo:{' '}</dt>
                    <dd className="m-0">{formatarDia(t.prazo_em)}</dd>
                    <dt className="font-semibold">Cor da tarefa:{' '}</dt>
                    <dd className="m-0">
                      <EtiquetaCor cor={t.cor} /> · criada em {formatarDia(t.criada_em)}
                      {nasceuNaHora(t, dados.decisoes) && ', quando a cor mudou na hora'}
                    </dd>
                    <dt className="font-semibold">Seria enviado para:{' '}</dt>
                    <dd className="m-0">
                      {destinatariosDoPrazo(t.cor, gestoraDe(t.municipio), coordenadoresDe(t.municipio)).join(', ')}
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
