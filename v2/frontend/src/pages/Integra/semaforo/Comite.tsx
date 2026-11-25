/**
 * Semáforo — Comitê de Satisfação (DADOS SIMULADOS).
 *
 * Um cartão por município com a cor que a regra sugere para o ciclo atual (com os dados até "hoje"), o
 * motivo, o que ficou sem dado e a seta de mudança desde a cor publicada no ciclo anterior. O Comitê
 * confirma a cor sugerida ou a altera; alterar exige a justificativa escrita. O pior vem primeiro, e o
 * filtro mostra só uma cor. Requisitos: Requisitos_Modulo_Semaforo_Risco_Municipal.pdf, seções 3, 4 e 7.
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
import { explicarCor, ROTULO_COR, textoSemDado } from './regras';
import { useSemaforoDemo } from './SemaforoDemoContext';
import type { Cor } from './tipos';
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

interface Alteracao {
  municipio: number;
  cor: Cor | null;
  justificativa: string;
  erros: string[];
}

type Filtro = Cor | 'todas';

const nomeDe = (m: MunicipioSemaforo): string => `${m.nome}-${m.uf}`;

export default function Comite(): JSX.Element {
  const { dados, situacoes, decidir } = useSemaforoDemo();
  const estadoDaFicha = useEstadoDaFicha();
  const [filtro, setFiltro] = useState<Filtro>('todas');
  const [alteracao, setAlteracao] = useState<Alteracao | null>(null);
  const [aviso, setAviso] = useState('');
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
    setAviso(`Publicado: ${nomeDe(l.m)} em ${ROTULO_COR[cor]}.`);
    return true;
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
    const aberta = alteracao?.municipio === m.id ? alteracao : null;
    const outras = CORES.filter((c) => c !== r.cor);
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
          {decisao ? (
            <>
              <CorComNome cor={decisao.cor_publicada} rotulo="Decisão deste ciclo" />, publicada em {formatarDia(decisao.publicada_em)}
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
            <fieldset className="m-0 mb-2 border-0 p-0">
              <legend className={CLASSE_ROTULO}>Nova cor (a sugerida é {ROTULO_COR[r.cor]})</legend>
              <div className="flex flex-wrap gap-3">
                {outras.map((c, i) => (
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
              Obrigatória: a cor publicada fica diferente da sugerida.
            </p>
            {aberta.erros.length > 0 && (
              <div role="alert" className="mb-2 rounded border border-[#8A1C14] bg-[#FCE4E2] p-2 text-sm text-[#8A1C14]">
                {aberta.erros.map((e) => (
                  <p key={e} className="m-0">
                    {e}
                  </p>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <button type="submit" className={BOTAO_PRINCIPAL}>
                Publicar a cor alterada
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
            <button type="button" className={BOTAO_PRINCIPAL} onClick={() => publicar(l, r.cor, null)}>
              Confirmar {ROTULO_COR[r.cor]}
              <span className="sr-only"> para {nomeDe(m)}</span>
            </button>
            <button
              type="button"
              id={`comite-alterar-${m.id}`}
              className={BOTAO_SECUNDARIO}
              onClick={() => {
                setAlteracao({ municipio: m.id, cor: null, justificativa: '', erros: [] });
                setFoco(`comite-cor-${m.id}`);
              }}
            >
              Alterar a cor
              <span className="sr-only"> de {nomeDe(m)}</span>
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
        ({formatarDia(dados.data_referencia)}). O Comitê confirma a cor ou a altera; para alterar, escreve a
        justificativa. ▲ piorou e ▼ melhorou comparam com a cor publicada no ciclo{' '}
        {cicloAnterior(ciclo)} ({mesesDoCiclo(cicloAnterior(ciclo))}).
      </p>
      <p className="text-sm">
        Sem dado: o indicador ainda não tem informação neste ciclo (a pesquisa fica aberta até{' '}
        {formatarDia(periodoDoCiclo(ciclo).prazo_pesquisa)}; sem relatório mensal, o cronograma fica sem dado). Ele fica fora da
        regra: a cor sai só dos indicadores que têm dado.
      </p>

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

      <p role="status" className={aviso ? 'mb-3 rounded bg-[#DDF3E4] p-2 text-[#0F5A2E]' : 'sr-only'}>
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
