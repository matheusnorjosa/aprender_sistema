/**
 * ICA — Simulador de remanejamento (DADOS SIMULADOS).
 *
 * Mover um ou mais municípios entre coordenadores e ver, lado a lado, o ICA antes e depois de cada
 * envolvido, a mudança de estrato e a nova dispersão da equipe. A proposta passa por
 * propor → aprovar → aplicar (com data de vigência) no estado da sessão (IntegraDemoContext);
 * recarregar a página volta ao original. Requisitos: Requisitos_Modulo_ICA.pdf, seções 4 e 5.
 *
 * Aprovação: o PDF dizia que a Líder do NFP aprova; a decisão 20 do dono (`quemVe.ts`) diz que a gestora
 * pedagógica propõe e a SPE aplica, e a Líder do NFP só consulta. A tela segue a decisão 20.
 */
import { useEffect, useRef, useState, type JSX } from 'react';
import { Link } from 'react-router';
import { Alert, Button, Typography } from 'antd';

import { formatFortaleza } from '../../../utils/datetime';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import type { Movimento, Remanejamento, StatusRemanejamento } from '../dados/tipos';
import { arredondarIca, nomeDoEstrato, simularRemanejamento, type ComparacaoCoordenador, type ResultadoCoordenador } from './calculo';
import { BarraIca, escalaDoGrafico } from './componentes/BarraIca';
import { textoDoEstrato } from './componentes/EtiquetaEstrato';
import { FaixasLegendaCurta } from './componentes/FaixasLegenda';
import { CLASSE_CAMPO, CLASSE_ROTULO, formatarNumero, formatarVariacao } from './componentes/estilos';

const { Title } = Typography;

const TITULO = { fontSize: 20 } as const;

const ID_AVISO = 'ica-sim-aviso';
const ID_JUSTIFICATIVA = 'ica-sim-justificativa';
const ID_ERROS_PROPOSTA = 'ica-sim-erros-proposta';
const ERRO_JUSTIFICATIVA = 'Escreva a justificativa do remanejamento.';
const CLASSE_FOCO = 'focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-primary-dark';
const LISTA = new Intl.ListFormat('pt-BR', { type: 'conjunction' });

const chaveDoMovimento = (m: Movimento): string => `${m.municipioId}-${m.deCoordenadorId}`;
const idDoTirar = (m: Movimento): string => `ica-sim-tirar-${chaveDoMovimento(m)}`;
const idDaProposta = (id: string): string => `ica-sim-proposta-${id}`;
const idDoAplicar = (id: string): string => `ica-sim-aplicar-${id}`;
const idDoErroAplicar = (id: string): string => `ica-sim-erro-aplicar-${id}`;

const ROTULO_STATUS: Record<StatusRemanejamento, string> = {
  proposto: 'Proposta',
  aprovado: 'Aprovada',
  aplicado: 'Aplicada',
};

const COR_STATUS: Record<StatusRemanejamento, string> = {
  proposto: 'bg-[#FFF0C2] text-[#6B4A00]',
  aprovado: 'bg-[#DCEBFA] text-[#0B4A80]',
  aplicado: 'bg-[#DDF3E4] text-[#0F5A2E]',
};

function etiqueta(r: ResultadoCoordenador): string {
  return textoDoEstrato(r.conta.estrato, r.conta.icaExibido, r.semMunicipios);
}

function mudanca(l: ComparacaoCoordenador): string {
  if (l.antes.semMunicipios && !l.depois.semMunicipios) return 'Passa a ter carteira e entra na média da equipe.';
  if (!l.antes.semMunicipios && l.depois.semMunicipios) return 'Fica sem municípios: ICA 0, fora da média da equipe.';
  if (l.mudouEstrato) {
    return `Muda de estrato: de ${nomeDoEstrato(l.antes.conta.estrato)} para ${nomeDoEstrato(l.depois.conta.estrato)}.`;
  }
  return `Continua em ${nomeDoEstrato(l.depois.conta.estrato)}.`;
}

export default function Simulador(): JSX.Element {
  const { dados, base, pesos, resultado, remanejamentos, proporRemanejamento, aprovarRemanejamento, aplicarRemanejamento } =
    useIntegraDemo();
  const [origem, setOrigem] = useState('');
  const [destino, setDestino] = useState('');
  const [marcados, setMarcados] = useState<number[]>([]);
  const [movimentos, setMovimentos] = useState<Movimento[]>([]);
  const [justificativa, setJustificativa] = useState('');
  const [erros, setErros] = useState<string[]>([]);
  const [errosProposta, setErrosProposta] = useState<string[]>([]);
  const [aviso, setAviso] = useState('');
  const [erroAplicar, setErroAplicar] = useState<{ id: string; texto: string } | null>(null);
  // O botão clicado pode sair da tela (Propor, Aprovar, Aplicar, Tirar): depois do render, o foco vai
  // para onde a pessoa continua (WCAG 2.4.3), em vez de cair no começo da página.
  const focarDepois = useRef<string | null>(null);
  useEffect(() => {
    if (focarDepois.current === null) return;
    document.getElementById(focarDepois.current)?.focus();
    focarDepois.current = null;
  });
  const justificativaInvalida = errosProposta.includes(ERRO_JUSTIFICATIVA);

  const nomeDoCoordenador = (id: number): string => base.coordenadores.find((c) => c.id === id)?.nome ?? `Coordenador ${id}`;
  const nomeDoMunicipio = (id: number): string => {
    const m = base.municipios.find((x) => x.id === id);
    return m ? `${m.nome}-${m.uf}` : `Município ${id}`;
  };
  const descrever = (m: Movimento): string =>
    `${nomeDoMunicipio(m.municipioId)}: de ${nomeDoCoordenador(m.deCoordenadorId)} para ${nomeDoCoordenador(m.paraCoordenadorId)}`;

  const comCarteira = resultado.coordenadores.filter((r) => r.carteira.length > 0);
  const daOrigem = resultado.coordenadores.find((r) => String(r.coordenador.id) === origem);
  const jaMovidos = new Set(movimentos.filter((m) => String(m.deCoordenadorId) === origem).map((m) => m.municipioId));
  const disponiveis = daOrigem ? daOrigem.carteira.filter((l) => !jaMovidos.has(l.municipio.id)) : [];

  const simulacao = movimentos.length > 0 ? simularRemanejamento(base, pesos, movimentos) : undefined;
  const idsEnvolvidos = new Set(simulacao?.envolvidos.map((l) => l.coordenadorId));
  const outrasMudancas = simulacao?.mudancasDeEstrato.filter((l) => !idsEnvolvidos.has(l.coordenadorId)) ?? [];
  const escala = simulacao
    ? escalaDoGrafico(simulacao.envolvidos.flatMap((l) => [l.antes.conta.icaExibido, l.depois.conta.icaExibido]))
    : 200;

  const daSessao = remanejamentos.filter((r) => !dados.remanejamentos.some((x) => x.id === r.id)).reverse();

  const trocarOrigem = (valor: string): void => {
    setOrigem(valor);
    setMarcados([]);
    if (valor === destino) setDestino('');
  };

  const adicionar = (): void => {
    const faltas: string[] = [];
    if (origem === '') faltas.push('Escolha o coordenador de origem.');
    if (marcados.length === 0) faltas.push('Escolha pelo menos um município para mover.');
    if (destino === '') faltas.push('Escolha o coordenador de destino.');
    setErros(faltas);
    setAviso('');
    if (faltas.length > 0) return;
    setMovimentos((atuais) => [
      ...atuais,
      ...marcados.map((municipioId) => ({ municipioId, deCoordenadorId: Number(origem), paraCoordenadorId: Number(destino) })),
    ]);
    setMarcados([]);
    // "Antes e depois" aparece mais abaixo e o foco fica no botão (para adicionar mais): o aviso conta o
    // que entrou e onde ver (WCAG 4.1.3).
    const nomes = LISTA.format(marcados.map(nomeDoMunicipio));
    const verbo = marcados.length === 1 ? 'adicionado' : 'adicionados';
    setAviso(
      `${nomes} ${verbo} à simulação, de ${nomeDoCoordenador(Number(origem))} para ${nomeDoCoordenador(Number(destino))}. Veja o resultado em "Antes e depois", logo abaixo.`,
    );
  };

  const propor = (): void => {
    const r = proporRemanejamento(movimentos, justificativa);
    if (!r.ok) {
      setErrosProposta(r.erros);
      setAviso('');
      focarDepois.current = r.erros.includes(ERRO_JUSTIFICATIVA) ? ID_JUSTIFICATIVA : ID_ERROS_PROPOSTA;
      return;
    }
    setErros([]);
    setErrosProposta([]);
    setMovimentos([]);
    setJustificativa('');
    setAviso('Proposta registrada. Ela aparece em "Propostas desta sessão", esperando aprovação.');
    focarDepois.current = ID_AVISO;
  };

  const tirar = (m: Movimento): void => {
    const restantes = movimentos.filter((x) => x !== m);
    const posicao = movimentos.indexOf(m);
    const proximo = restantes[Math.min(posicao, restantes.length - 1)];
    setMovimentos(restantes);
    if (proximo) {
      focarDepois.current = idDoTirar(proximo);
    } else {
      setErrosProposta([]);
      setAviso('Movimento retirado. A simulação ficou vazia.');
      focarDepois.current = ID_AVISO;
    }
  };

  const aprovar = (id: string): void => {
    aprovarRemanejamento(id);
    setAviso('Proposta aprovada. Falta aplicar.');
    focarDepois.current = idDoAplicar(id);
  };

  const aplicar = (id: string): void => {
    const r = aplicarRemanejamento(id);
    if (!r.ok) {
      setErroAplicar({ id, texto: r.erros.join(' ') });
      setAviso('');
      focarDepois.current = idDoErroAplicar(id);
      return;
    }
    setErroAplicar(null);
    setAviso('Remanejamento aplicado. O ICA da equipe foi recalculado.');
    focarDepois.current = idDaProposta(id);
  };

  const hoje = formatFortaleza(new Date(), 'DD/MM/YYYY');

  const renderProposta = (r: Remanejamento): JSX.Element => (
    <li key={r.id} id={idDaProposta(r.id)} tabIndex={-1} className={`mb-3 rounded border border-[#d9d9d9] bg-white p-3 ${CLASSE_FOCO}`}>
      <p className="m-0 flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-sm font-semibold ${COR_STATUS[r.status]}`}>{ROTULO_STATUS[r.status]}</span>
        <span className="text-sm">
          Proposta por {r.proposto_por} em {formatFortaleza(r.proposto_em)}
        </span>
      </p>
      <ul className="my-2 pl-5">
        {r.movimentos.map((m) => (
          <li key={`${m.municipioId}-${m.deCoordenadorId}`}>{descrever(m)}</li>
        ))}
      </ul>
      <p className="mb-2">Justificativa: {r.justificativa}</p>
      {r.aprovado_por && r.aprovado_em && (
        <p className="mb-2">
          Aprovada por {r.aprovado_por} em {formatFortaleza(r.aprovado_em)}
        </p>
      )}
      {r.status === 'proposto' && (
        <Button type="primary" onClick={() => aprovar(r.id)}>
          Aprovar (SPE)
        </Button>
      )}
      {r.status === 'aprovado' && (
        <>
          <p className="mb-2">
            Data de vigência: semestre {dados.semestre_atual}, a partir da aplicação (hoje, {hoje}).
          </p>
          <Button id={idDoAplicar(r.id)} type="primary" onClick={() => aplicar(r.id)}>
            Aplicar
          </Button>
          {erroAplicar?.id === r.id && (
            <div id={idDoErroAplicar(r.id)} tabIndex={-1} className={`mt-2 ${CLASSE_FOCO}`}>
              <Alert type="error" showIcon message={erroAplicar.texto} />
            </div>
          )}
        </>
      )}
      {r.status === 'aplicado' && r.aplicado_em && (
        <p className="m-0">
          Aplicada em {formatFortaleza(r.aplicado_em)} · vale a partir do semestre {r.semestre}. O ICA da equipe já foi
          recalculado.
        </p>
      )}
    </li>
  );

  return (
    <section aria-labelledby="ica-simulador-titulo">
      <Title level={1} id="ica-simulador-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
        Simulador de remanejamento
      </Title>
      <p className="mb-4">
        Escolha os municípios que mudariam de coordenador e veja o ICA de cada envolvido antes e depois. Nada muda de
        verdade até a proposta ser aprovada e aplicada.
      </p>

      <section aria-labelledby="ica-simulador-montar" className="mb-6">
        <Title level={2} id="ica-simulador-montar" style={TITULO}>
          Montar a simulação
        </Title>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label htmlFor="ica-sim-origem" className={CLASSE_ROTULO}>
              Coordenador de origem
            </label>
            <select id="ica-sim-origem" className={CLASSE_CAMPO} value={origem} onChange={(e) => trocarOrigem(e.target.value)}>
              <option value="">Escolha…</option>
              {comCarteira.map((r) => (
                <option key={r.coordenador.id} value={String(r.coordenador.id)}>
                  {r.coordenador.nome} ({etiqueta(r)})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="ica-sim-destino" className={CLASSE_ROTULO}>
              Coordenador de destino
            </label>
            <select id="ica-sim-destino" className={CLASSE_CAMPO} value={destino} onChange={(e) => setDestino(e.target.value)}>
              <option value="">Escolha…</option>
              {resultado.coordenadores
                .filter((r) => String(r.coordenador.id) !== origem)
                .map((r) => (
                  <option key={r.coordenador.id} value={String(r.coordenador.id)}>
                    {r.coordenador.nome} ({etiqueta(r)})
                  </option>
                ))}
            </select>
          </div>
        </div>
        {daOrigem && (
          <fieldset className="mt-3 rounded border border-[#d9d9d9] p-3">
            <legend className="px-1 text-sm font-semibold">Municípios para mover</legend>
            {disponiveis.length === 0 ? (
              <p className="m-0">Todos os municípios desta carteira já estão na simulação.</p>
            ) : (
              <ul className="m-0 grid list-none gap-1 p-0 sm:grid-cols-2 lg:grid-cols-3">
                {disponiveis.map((l) => {
                  const nome = `${l.municipio.nome}-${l.municipio.uf}`;
                  return (
                    <li key={l.municipio.id}>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="h-4 w-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-dark"
                          checked={marcados.includes(l.municipio.id)}
                          onChange={(e) =>
                            setMarcados((atuais) =>
                              e.target.checked ? [...atuais, l.municipio.id] : atuais.filter((x) => x !== l.municipio.id),
                            )
                          }
                        />
                        {nome}
                        {!l.ativo && <span className="text-sm text-[#595959]">(suspenso: não conta no ICA)</span>}
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
          </fieldset>
        )}
        <div className="mt-3">
          <Button onClick={adicionar}>Adicionar à simulação</Button>
        </div>
        {erros.length > 0 && (
          <Alert
            className="mt-3"
            type="error"
            showIcon
            message={
              <ul className="m-0 list-none p-0">
                {erros.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            }
          />
        )}
        {/* Região viva sempre montada: só o texto muda, para o leitor de tela anunciar (WCAG 4.1.3). */}
        <p
          id={ID_AVISO}
          role="status"
          tabIndex={-1}
          className={aviso ? `mt-3 rounded bg-[#DDF3E4] p-2 text-[#0F5A2E] ${CLASSE_FOCO}` : 'sr-only'}
        >
          {aviso}
        </p>
      </section>

      {simulacao && (
        <section aria-labelledby="ica-simulador-resultado" className="mb-6">
          <Title level={2} id="ica-simulador-resultado" style={TITULO}>
            Antes e depois
          </Title>
          <ul aria-label="Movimentos da simulação" className="m-0 mb-3 list-none p-0">
            {movimentos.map((m) => (
              <li key={chaveDoMovimento(m)} className="mb-1 flex flex-wrap items-center gap-2">
                <span>{descrever(m)}</span>
                <Button id={idDoTirar(m)} size="small" onClick={() => tirar(m)}>
                  <span aria-hidden="true">Tirar</span>
                  <span className="sr-only">Tirar {nomeDoMunicipio(m.municipioId)} da simulação</span>
                </Button>
              </li>
            ))}
          </ul>
          {simulacao.movimentosInvalidos.length > 0 && (
            <Alert
              className="mb-3"
              type="warning"
              showIcon
              message={`Fora da conta (o município já não está com o coordenador de origem): ${simulacao.movimentosInvalidos.map(descrever).join('; ')}.`}
            />
          )}
          <FaixasLegendaCurta />
          <ul aria-label="Antes e depois de cada envolvido" className="m-0 mb-3 grid list-none gap-3 p-0 lg:grid-cols-2">
            {simulacao.envolvidos.map((l) => (
              <li key={l.coordenadorId} className="rounded border border-[#d9d9d9] bg-white p-3">
                <p className="mb-2 font-semibold">
                  <Link to={`/integra/ica/coordenador/${l.coordenadorId}`}>{l.nome}</Link>
                </p>
                <p className="mb-1">Antes: {etiqueta(l.antes)}</p>
                <BarraIca ica={l.antes.conta.icaExibido} estrato={l.antes.conta.estrato} escalaMax={escala} fina />
                <p className="mb-1 mt-2">Depois: {etiqueta(l.depois)}</p>
                <BarraIca ica={l.depois.conta.icaExibido} estrato={l.depois.conta.estrato} escalaMax={escala} fina />
                <p className="mb-0 mt-2">
                  Variação: {formatarVariacao(l.variacao)}. {mudanca(l)}
                </p>
              </li>
            ))}
          </ul>
          {outrasMudancas.length > 0 && (
            <>
              <p className="mb-1">Também mudam de estrato, porque a média da equipe mudou:</p>
              <ul className="mb-3 pl-5">
                {outrasMudancas.map((l) => (
                  <li key={l.coordenadorId}>
                    {l.nome}: {etiqueta(l.antes)} → {etiqueta(l.depois)}
                  </li>
                ))}
              </ul>
            </>
          )}
          <p>
            Dispersão da equipe: desvio {formatarNumero(simulacao.dispersaoAntes.desvioPadrao, 1)} →{' '}
            {formatarNumero(simulacao.dispersaoDepois.desvioPadrao, 1)} · menor {arredondarIca(simulacao.dispersaoAntes.menor)} →{' '}
            {arredondarIca(simulacao.dispersaoDepois.menor)} · maior {arredondarIca(simulacao.dispersaoAntes.maior)} →{' '}
            {arredondarIca(simulacao.dispersaoDepois.maior)}
          </p>

          <div className="mt-4 max-w-2xl">
            <label htmlFor={ID_JUSTIFICATIVA} className={CLASSE_ROTULO}>
              Justificativa
            </label>
            <textarea
              id={ID_JUSTIFICATIVA}
              className={CLASSE_CAMPO}
              rows={3}
              value={justificativa}
              aria-invalid={justificativaInvalida || undefined}
              aria-describedby={justificativaInvalida ? ID_ERROS_PROPOSTA : undefined}
              onChange={(e) => setJustificativa(e.target.value)}
            />
            {errosProposta.length > 0 && (
              <div id={ID_ERROS_PROPOSTA} tabIndex={-1} className={`mt-2 ${CLASSE_FOCO}`}>
                <Alert
                  type="error"
                  showIcon
                  message={
                    <ul className="m-0 list-none p-0">
                      {errosProposta.map((e) => (
                        <li key={e}>{e}</li>
                      ))}
                    </ul>
                  }
                />
              </div>
            )}
            <Button type="primary" className="mt-2" onClick={propor}>
              Propor remanejamento
            </Button>
          </div>
        </section>
      )}

      <section aria-labelledby="ica-simulador-propostas">
        <Title level={2} id="ica-simulador-propostas" style={TITULO}>
          Propostas desta sessão
        </Title>
        <Alert
          className="mb-3"
          type="info"
          showIcon
          message="Como na decisão 20: a gestora pedagógica propõe, a SPE aprova e aplica, com data de vigência. A Líder do NFP só consulta. O PDF dizia que a Líder aprovava."
        />
        {daSessao.length === 0 ? (
          <p>
            Nenhuma proposta nesta sessão. Os remanejamentos já aplicados ficam no{' '}
            <Link to="/integra/ica/historico">Histórico</Link>.
          </p>
        ) : (
          <ol aria-label="Propostas desta sessão" className="m-0 list-none p-0">
            {daSessao.map(renderProposta)}
          </ol>
        )}
      </section>
    </section>
  );
}
