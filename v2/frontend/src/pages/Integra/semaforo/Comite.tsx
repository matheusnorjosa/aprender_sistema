/**
 * Semáforo — Comitê de Satisfação (DADOS SIMULADOS).
 *
 * Um cartão por município com a cor que a regra sugere para o ciclo atual (com os dados até "hoje"), o
 * motivo, o que ficou sem dado e a seta de mudança desde a cor publicada no ciclo anterior. O Comitê
 * confirma a cor sugerida ou a altera; alterar exige a justificativa escrita. O pior vem primeiro, e o
 * filtro mostra só uma cor. Requisitos: Requisitos_Modulo_Semaforo_Risco_Municipal.pdf, seções 3, 4 e 7.
 *
 * Decisões do dono de 25/11: um vermelho (um indicador ou três amarelos) muda a cor em vigor na hora, e o
 * Comitê confirma ou desfaz depois (38, 39 e 42); a SPE marca a data do Comitê ordinário (40) e convoca o
 * extraordinário a critério dela (41). As duas coisas ficam na seção "Datas do Comitê".
 */
import { useEffect, useState, type FormEvent, type JSX } from 'react';
import { Link } from 'react-router';
import { Typography } from 'antd';

import { CLASSE_CAMPO, CLASSE_ROTULO, formatarDia } from '../ica/componentes/estilos';
import { AvisoQuemVe } from './componentes/PecasDoRegistro';
import { CorComNome, Mudanca } from './componentes/PecasDoAcompanhamento';
import {
  cicloAnterior,
  mesesDoCiclo,
  periodoDoCiclo,
  type CicloAvaliado,
  type MunicipioSemaforo,
  type SituacaoMunicipio,
} from './dados';
import { explicarCor, lista, ROTULO_COR, tarefaAberta, textoSemDado } from './regras';
import { useSemaforoDemo } from './SemaforoDemoContext';
import type { Cor, DecisaoComite, OrigemDecisao } from './tipos';
import { useEstadoDaFicha } from './voltarDaFicha';

const { Title } = Typography;

const CORES: readonly Cor[] = ['vermelho', 'amarelo', 'verde'];
const GRAVIDADE: Record<Cor, number> = { vermelho: 0, amarelo: 1, verde: 2 };

const CLASSE_FOCO = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark';
const CLASSE_BOTAO = `rounded border px-3 py-1 text-sm font-semibold ${CLASSE_FOCO}`;
const BOTAO_PRINCIPAL = `${CLASSE_BOTAO} border-primary-dark bg-primary-dark text-white hover:bg-primary`;
const BOTAO_SECUNDARIO = `${CLASSE_BOTAO} border-[#8c8c8c] bg-white text-[#1f1f1f] hover:border-primary-dark`;

interface Linha {
  m: MunicipioSemaforo;
  s: SituacaoMunicipio;
  atual: CicloAvaliado;
  /** Cor publicada no ciclo anterior (base da seta). */
  anterior: Cor | null;
}

/**
 * O formulário aberto no cartão: alterar a cor sugerida; ou, com o vermelho na hora em vigor (decisão 38), desfazer o
 * vermelho (verde ou amarelo) ou confirmar o vermelho quando a sugerida já é outra (a justificativa é obrigatória).
 */
type Modo = 'alterar' | 'desfazer' | 'confirmar';

interface Alteracao {
  municipio: number;
  modo: Modo;
  cor: Cor | null;
  justificativa: string;
  erros: string[];
}

type Filtro = Cor | 'todas';

const nomeDe = (m: MunicipioSemaforo): string => `${m.nome}-${m.uf}`;

/** Quem publicou a decisão, para o fim da frase "publicada em 02/12/2026 pelo Comitê extraordinário". */
const POR_QUEM: Record<OrigemDecisao, string> = {
  vermelho_automatico: ', na hora',
  comite_ordinario: ' pelo Comitê ordinário',
  comite_extraordinario: ' pelo Comitê extraordinário',
};

/**
 * O que acontece com as tarefas quando o Comitê publica `cor` sobre a decisão em vigor (decisões 42 e 43).
 * `abertasDaCor`: o município tem tarefas abertas de `cor` de antes, que ficam substituídas.
 */
function efeitoNasTarefas(anterior: DecisaoComite | null, ciclo: string, cor: Cor, abertasDaCor: boolean): string {
  const nome = (c: Cor): string => ROTULO_COR[c].toLowerCase();
  const novas = cor === 'verde' ? '' : ` As tarefas do ${nome(cor)} começam hoje.`;
  if (anterior?.ciclo === ciclo) {
    if (anterior.cor_publicada === cor) {
      return anterior.origem === 'vermelho_automatico'
        ? ' O Comitê confirmou o vermelho na hora: as tarefas seguem.'
        : ' A mesma cor já valia neste ciclo: as tarefas seguem.';
    }
    // Decisão 42: só o vermelho desfeito cancela as tarefas abertas; as do amarelo seguem (aviso `textoContinuam`).
    const canceladas =
      anterior.cor_publicada === 'vermelho'
        ? ' As tarefas abertas do vermelho ficam canceladas pelo Comitê; as feitas continuam registradas.'
        : '';
    const substituidas =
      cor !== 'verde' && abertasDaCor
        ? ` As tarefas do ${nome(cor)} começam hoje; as que estavam abertas do ${nome(cor)} ficam substituídas.`
        : novas;
    return `${canceladas}${substituidas}`;
  }
  if (cor !== 'verde' && anterior?.cor_publicada === cor) {
    return ` As tarefas do ${nome(cor)} abrem de novo; as que estavam abertas ficam substituídas.`;
  }
  return novas;
}

export default function Comite(): JSX.Element {
  const { dados, situacoes, decidir, marcarComite, convocarExtraordinario } = useSemaforoDemo();
  const estadoDaFicha = useEstadoDaFicha();
  const [filtro, setFiltro] = useState<Filtro>('todas');
  const [alteracao, setAlteracao] = useState<Alteracao | null>(null);
  const [aviso, setAviso] = useState('');
  const hoje = dados.data_referencia;
  const ordinario = dados.comites.filter((c) => c.ciclo === dados.ciclo_atual && c.tipo === 'ordinario').at(-1) ?? null;
  const extraordinarios = dados.comites
    .filter((c) => c.ciclo === dados.ciclo_atual && c.tipo === 'extraordinario')
    .map((c) => c.data)
    .sort();
  const [dataComite, setDataComite] = useState(ordinario?.data ?? '');
  const [errosData, setErrosData] = useState<string[]>([]);
  // Id do elemento que recebe o foco depois da próxima pintura (o formulário que abriu, o botão que ficou).
  const [foco, setFoco] = useState<string | null>(null);

  useEffect(() => {
    if (foco === null) return;
    document.getElementById(foco)?.focus();
    setFoco(null);
  }, [foco]);

  const ciclo = dados.ciclo_atual;
  const linhas: Linha[] = situacoes
    .map((s, i) => {
      const n = s.ciclos.length;
      return { m: dados.municipios[i]!, s, atual: s.ciclos[n - 1]!, anterior: s.ciclos[n - 2]?.decisao?.cor_publicada ?? null };
    })
    .sort((a, b) => GRAVIDADE[a.atual.resultado.cor] - GRAVIDADE[b.atual.resultado.cor] || a.m.nome.localeCompare(b.m.nome, 'pt-BR'));
  const porCor = (cor: Cor): number => linhas.filter((l) => l.atual.resultado.cor === cor).length;
  const visiveis = filtro === 'todas' ? linhas : linhas.filter((l) => l.atual.resultado.cor === filtro);

  function publicar(l: Linha, cor: Cor, justificativa: string | null): boolean {
    const r = decidir(l.m.id, cor, justificativa);
    if (!r.ok) {
      setAlteracao((a) => (a ? { ...a, erros: r.erros } : a));
      return false;
    }
    const abertas = dados.tarefas.filter((t) => t.municipio === l.m.id && tarefaAberta(t));
    const abertasDaCor = abertas.some((t) => t.cor === cor);
    // Leitura do protótipo (Para validar): as tarefas abertas de outra cor seguem abertas, salvo as do vermelho que o
    // Comitê desfez no mesmo ciclo (decisão 42, `tarefasDepoisDaPublicacao`). O aviso diz quais.
    const anterior = l.s.decisao_vigente;
    const desfeita = anterior?.ciclo === ciclo && anterior.cor_publicada === 'vermelho' ? 'vermelho' : null;
    const continuam = abertas.filter((t) => t.cor !== cor && t.cor !== desfeita);
    const textoContinuam = (['vermelho', 'amarelo'] as const)
      .map((c) => [c, continuam.filter((t) => t.cor === c).map((t) => t.titulo)] as const)
      .filter(([, titulos]) => titulos.length > 0)
      .map(([c, titulos]) => ` As tarefas abertas do ${ROTULO_COR[c].toLowerCase()} que vinham de antes continuam abertas: ${lista(titulos)}.`)
      .join('');
    setAviso(`Publicado: ${nomeDe(l.m)} em ${ROTULO_COR[cor]}.${efeitoNasTarefas(anterior, ciclo, cor, abertasDaCor)}${textoContinuam}`);
    return true;
  }

  function enviarData(evento: FormEvent): void {
    evento.preventDefault();
    const r = marcarComite(dataComite);
    if (!r.ok) {
      setErrosData(r.erros);
      return;
    }
    setErrosData([]);
    setAviso(`Comitê ordinário marcado para ${formatarDia(dataComite)}.`);
  }

  function convocar(): void {
    convocarExtraordinario();
    setAviso(
      `Comitê extraordinário convocado para hoje (${formatarDia(hoje)}). As decisões registradas hoje valem como dele.`,
    );
  }

  function enviarAlteracao(evento: FormEvent, l: Linha): void {
    evento.preventDefault();
    if (!alteracao) return;
    if (alteracao.cor === null) {
      setAlteracao({ ...alteracao, erros: ['Escolha a nova cor.'] });
      return;
    }
    if (publicar(l, alteracao.cor, alteracao.justificativa)) {
      setAlteracao(null);
      setFoco(`comite-alterar-${l.m.id}`);
    }
  }

  function cartao(l: Linha): JSX.Element {
    const { m, s, atual, anterior } = l;
    const r = atual.resultado;
    const semDado = textoSemDado(r);
    const decisao = atual.decisao;
    // Decisão 38: o vermelho na hora já vale como cor em vigor e espera o Comitê confirmar ou desfazer.
    const automatico = s.aguardando_comite ? s.decisao_vigente : null;
    const aberta = alteracao?.municipio === m.id ? alteracao : null;
    const sugerida = ROTULO_COR[r.cor];
    // Com o vermelho na hora, as ações partem do vermelho em vigor, e não da sugerida (que pode já ter mudado).
    const opcoes = aberta?.modo === 'desfazer' ? CORES.filter((c) => c !== 'vermelho') : CORES.filter((c) => c !== r.cor);
    const legenda = aberta?.modo === 'desfazer' ? `Nova cor (a sugerida agora é ${sugerida})` : `Nova cor (a sugerida é ${sugerida})`;
    const dica =
      aberta?.modo === 'desfazer' && r.cor !== 'vermelho'
        ? `Obrigatória se a nova cor for diferente da sugerida (${sugerida}).`
        : 'Obrigatória: a cor publicada fica diferente da sugerida.';
    const abrir = (modo: Modo): void => {
      setAlteracao({ municipio: m.id, modo, cor: modo === 'confirmar' ? 'vermelho' : null, justificativa: '', erros: [] });
      setFoco(modo === 'confirmar' ? `comite-just-${m.id}` : `comite-cor-${m.id}`);
    };
    const idTitulo = `comite-m-${m.id}`;
    return (
      <article aria-labelledby={idTitulo} className="h-full rounded border border-[#d9d9d9] bg-white p-3">
        <h3 id={idTitulo} className="m-0 mb-2 text-base font-semibold">
          <Link to={`/integra/semaforo/municipio/${m.id}`} state={estadoDaFicha} className={CLASSE_FOCO}>
            {nomeDe(m)}
          </Link>
        </h3>
        <p className="m-0 mb-1 flex flex-wrap items-center gap-x-3 gap-y-1">
          <CorComNome cor={r.cor} rotulo="Sugerida" />
          <Mudanca anterior={anterior} atual={decisao?.cor_publicada ?? r.cor} />
        </p>
        <p className="m-0 mb-1 text-sm">{explicarCor(r)}</p>
        {semDado && <p className="m-0 mb-1 text-sm text-[#3D3D3D]">{semDado}</p>}
        <p className="m-0 mb-2 text-sm">
          {automatico ? (
            <>
              <CorComNome cor={automatico.cor_publicada} rotulo="Em vigor" />{' '}
              {`Vermelho na hora em ${formatarDia(automatico.publicada_em)}: a cor em vigor mudou e as tarefas do vermelho começaram. O Comitê confirma ou desfaz.`}
              {r.cor !== 'vermelho' && ` A cor sugerida agora é ${sugerida}.`}
            </>
          ) : decisao ? (
            <>
              <CorComNome cor={decisao.cor_publicada} rotulo="Decisão deste ciclo" />, publicada em {formatarDia(decisao.publicada_em)}
              {POR_QUEM[decisao.origem]}
            </>
          ) : (
            <>
              Ainda sem decisão neste ciclo. <CorComNome cor={s.cor_vigente} rotulo="Em vigor" />
            </>
          )}
        </p>
        {decisao?.justificativa && <p className="m-0 mb-2 text-sm">Justificativa: {decisao.justificativa}</p>}

        {aberta ? (
          <form noValidate onSubmit={(e) => enviarAlteracao(e, l)} className="mt-2 border-t border-[#d9d9d9] pt-2">
            {aberta.modo === 'confirmar' ? (
              <p className="m-0 mb-2 text-sm">
                Confirmar o vermelho na hora. A cor sugerida agora é {sugerida}: escreva a justificativa do Comitê.
              </p>
            ) : (
              <fieldset className="m-0 mb-2 border-0 p-0">
                <legend className={CLASSE_ROTULO}>{legenda}</legend>
                <div className="flex flex-wrap gap-3">
                  {opcoes.map((c, i) => (
                    <label key={c} className="flex items-center gap-1 text-sm">
                      <input
                        type="radio"
                        id={i === 0 ? `comite-cor-${m.id}` : undefined}
                        name={`comite-cor-${m.id}`}
                        value={c}
                        checked={aberta.cor === c}
                        onChange={() => setAlteracao({ ...aberta, cor: c })}
                        className={CLASSE_FOCO}
                      />
                      {ROTULO_COR[c]}
                    </label>
                  ))}
                </div>
              </fieldset>
            )}
            <label htmlFor={`comite-just-${m.id}`} className={CLASSE_ROTULO}>
              Justificativa do Comitê
            </label>
            <textarea
              id={`comite-just-${m.id}`}
              rows={3}
              aria-describedby={`comite-just-dica-${m.id}`}
              value={aberta.justificativa}
              onChange={(e) => setAlteracao({ ...aberta, justificativa: e.target.value })}
              className={CLASSE_CAMPO}
            />
            <p id={`comite-just-dica-${m.id}`} className="m-0 mb-2 text-xs text-[#3D3D3D]">
              {dica}
            </p>
            {aberta.erros.length > 0 && (
              <div role="alert" className="mb-2 rounded border border-[#C0392B] bg-[#FBE6E5] p-2 text-sm text-[#C0392B]">
                {aberta.erros.map((e) => (
                  <p key={e} className="m-0">
                    {e}
                  </p>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <button type="submit" className={BOTAO_PRINCIPAL}>
                {aberta.modo === 'confirmar' ? 'Publicar o vermelho' : 'Publicar a cor alterada'}
              </button>
              <button
                type="button"
                className={BOTAO_SECUNDARIO}
                onClick={() => {
                  setAlteracao(null);
                  setFoco(`comite-alterar-${m.id}`);
                }}
              >
                Cancelar
              </button>
            </div>
          </form>
        ) : (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={BOTAO_PRINCIPAL}
              onClick={() => {
                // Confirmar o vermelho na hora com a sugerida já diferente exige a justificativa: abre o formulário.
                if (automatico && r.cor !== 'vermelho') abrir('confirmar');
                else publicar(l, automatico ? 'vermelho' : r.cor, null);
              }}
            >
              {/* O espaço fica fora do trecho só para leitor de tela: dentro dele, o nome acessível colava as palavras. */}
              {automatico ? 'Confirmar o vermelho' : `Confirmar ${sugerida}`}{' '}
              <span className="sr-only">para {nomeDe(m)}</span>
            </button>
            <button
              type="button"
              id={`comite-alterar-${m.id}`}
              className={BOTAO_SECUNDARIO}
              onClick={() => abrir(automatico ? 'desfazer' : 'alterar')}
            >
              {automatico ? 'Desfazer o vermelho' : 'Alterar a cor'}{' '}
              <span className="sr-only">de {nomeDe(m)}</span>
            </button>
          </div>
        )}
      </article>
    );
  }

  return (
    <section aria-labelledby="semaforo-comite-titulo">
      <Title level={1} id="semaforo-comite-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
        Comitê de Satisfação
      </Title>
      <AvisoQuemVe tela="comite" />

      <p>
        A cor sugerida sai da regra do Semáforo, com os dados do ciclo {ciclo} ({mesesDoCiclo(ciclo)}) até hoje
        ({formatarDia(dados.data_referencia)}). Um indicador em vermelho ou três amarelos mudam a cor em vigor para
        vermelho na hora, e as tarefas do vermelho começam; o Comitê confirma ou desfaz depois. Nas outras cores, o
        Comitê confirma a cor ou a altera. Para alterar ou desfazer, escreve a justificativa. ▲ piorou e ▼ melhorou
        comparam com a cor publicada no ciclo {cicloAnterior(ciclo)} ({mesesDoCiclo(cicloAnterior(ciclo))}).
      </p>
      <p className="text-sm">
        Sem dado: o indicador ainda não tem informação neste ciclo (a pesquisa fica aberta até{' '}
        {formatarDia(periodoDoCiclo(ciclo).prazo_pesquisa)}; sem relatório mensal, o cronograma fica sem dado). Ele fica fora da
        regra: a cor sai só dos indicadores que têm dado.
      </p>

      <section aria-labelledby="comite-datas" className="mb-4 rounded border border-[#d9d9d9] bg-white p-3">
        <Title level={2} id="comite-datas" style={{ fontSize: 20 }}>
          Datas do Comitê
        </Title>
        <p className="m-0 mb-1">
          Próximo Comitê ordinário, na data marcada pela SPE: {ordinario ? formatarDia(ordinario.data) : 'ainda sem data'}.
        </p>
        <p className="m-0 mb-3">
          Comitê extraordinário deste ciclo, convocado pela SPE:{' '}
          {extraordinarios.length === 0 ? 'nenhum' : lista(extraordinarios.map(formatarDia))}.
        </p>
        <form noValidate onSubmit={enviarData} className="mb-3 max-w-sm">
          <label htmlFor="comite-data" className={CLASSE_ROTULO}>
            Data do próximo Comitê ordinário
          </label>
          <input
            id="comite-data"
            type="date"
            min={hoje}
            value={dataComite}
            onChange={(e) => setDataComite(e.target.value)}
            aria-invalid={errosData.length > 0 || undefined}
            aria-describedby={errosData.length > 0 ? 'comite-data-erro' : undefined}
            className={`${CLASSE_CAMPO} mb-2`}
          />
          {errosData.length > 0 && (
            <div id="comite-data-erro" role="alert" className="mb-2 rounded border border-[#C0392B] bg-[#FBE6E5] p-2 text-sm text-[#C0392B]">
              {errosData.map((e) => (
                <p key={e} className="m-0">
                  {e}
                </p>
              ))}
            </div>
          )}
          <button type="submit" className={BOTAO_PRINCIPAL}>
            Marcar a data
          </button>
        </form>
        <p className="m-0 mb-2 text-sm">
          O Comitê extraordinário é convocado a critério da SPE, por exemplo depois de um vermelho na hora. Na
          demonstração, a decisão registrada no dia do extraordinário vale como dele.
        </p>
        <button type="button" className={BOTAO_SECUNDARIO} onClick={convocar}>
          Convocar o Comitê extraordinário para hoje
        </button>
      </section>

      <ul aria-label={`Cores sugeridas no ciclo ${ciclo}`} className="m-0 mb-4 flex list-none flex-wrap gap-3 p-0">
        {CORES.map((c) => (
          <li key={c}>
            <CorComNome cor={c} />: {porCor(c)} {porCor(c) === 1 ? 'município' : 'municípios'}
          </li>
        ))}
      </ul>

      <fieldset className="m-0 mb-4 border-0 p-0">
        <legend className={CLASSE_ROTULO}>Mostrar pela cor sugerida</legend>
        <div className="flex flex-wrap gap-3">
          {(['todas', ...CORES] as const).map((f) => (
            <label key={f} className="flex items-center gap-1 text-sm">
              <input
                type="radio"
                name="comite-filtro"
                value={f}
                checked={filtro === f}
                onChange={() => setFiltro(f)}
                className={CLASSE_FOCO}
              />
              {f === 'todas' ? `Todas (${linhas.length})` : `${ROTULO_COR[f]} (${porCor(f)})`}
            </label>
          ))}
        </div>
      </fieldset>

      <p role="status" className={aviso ? 'mb-3 rounded bg-[#E8F5EB] p-2 text-[#1E7B3A]' : 'sr-only'}>
        {aviso}
      </p>

      <Title level={2} style={{ fontSize: 20 }}>
        Municípios
      </Title>
      <ul
        aria-label={`Municípios do ciclo ${ciclo}: ${visiveis.length} na lista`}
        className="m-0 grid list-none gap-3 p-0 md:grid-cols-2 xl:grid-cols-3"
      >
        {visiveis.map((l) => (
          <li key={l.m.id}>{cartao(l)}</li>
        ))}
      </ul>
    </section>
  );
}
