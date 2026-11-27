/**
 * ICA — Pesos e faixas (DADOS SIMULADOS).
 *
 * Editar os pesos (a soma tem de dar 100%) com justificativa obrigatória: cada mudança cria uma versão
 * nova (data, autor e justificativa), que passa a valer na sessão. O resultado é recalculado ao vivo
 * enquanto se edita, e a configuração original (proposta v5) fica ao lado para comparar.
 * As faixas ficam fixas, também na versão real (decisão 65). Requisitos: Requisitos_Modulo_ICA.pdf, seções 3 e 4.
 */
import { useEffect, useRef, useState, type JSX } from 'react';
import { Alert, Button, Typography } from 'antd';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { formatFortaleza } from '../../../utils/datetime';
import { useIntegraDemo } from '../dados/IntegraDemoContext';
import type { Componente, Pesos, VersaoPesos } from '../dados/tipos';
import {
  COMPONENTES,
  compararPesos,
  ESTRATOS,
  formatarPercentual,
  PESOS_ORIGINAIS_V5,
  ROTULO_COMPONENTE,
  validarPesos,
  type ResultadoCoordenador,
} from './calculo';
import { textoDoEstrato } from './componentes/EtiquetaEstrato';
import { FaixasLegenda } from './componentes/FaixasLegenda';
import { CLASSE_CAMPO, CLASSE_ROTULO } from './componentes/estilos';

const { Title } = Typography;

const TITULO = { fontSize: 20 } as const;

type Rascunho = Record<Componente, string>;

const paraRascunho = (pesos: Pesos): Rascunho =>
  Object.fromEntries(COMPONENTES.map((c) => [c, String(pesos[c])])) as Rascunho;

/** Campo vazio vira NaN: `validarPesos` acusa "precisa ser um número". */
const paraPesos = (r: Rascunho): Pesos =>
  Object.fromEntries(COMPONENTES.map((c) => [c, r[c].trim() === '' ? Number.NaN : Number(r[c])])) as Pesos;

const iguais = (a: Pesos, b: Pesos): boolean => COMPONENTES.every((c) => a[c] === b[c]);

const etiqueta = (r: ResultadoCoordenador): string => textoDoEstrato(r.conta.estrato, r.conta.icaExibido, r.semMunicipios);

interface LinhaComparacao {
  componente: Componente;
  original: number;
  vigente: number;
  rascunho: number;
}

const porcento = (n: number): string => (Number.isFinite(n) ? formatarPercentual(n) : '—');

const ID_SOMA = 'ica-pesos-soma';
const ID_JUSTIFICATIVA = 'ica-pesos-justificativa';
const ID_ERROS = 'ica-pesos-erros';
const ERRO_JUSTIFICATIVA = 'Escreva a justificativa da mudança.';
const CLASSE_FOCO = 'focus:outline focus:outline-2 focus:outline-offset-2 focus:outline-primary-dark';

/** Peso fora de 0 a 100 (ou vazio). */
const pesoInvalido = (p: number): boolean => !Number.isFinite(p) || p < 0 || p > 100;

export default function PesosFaixas(): JSX.Element {
  const { base, pesos, versaoVigente, versoesPesos, trocarPesos } = useIntegraDemo();
  const [rascunho, setRascunho] = useState<Rascunho>(() => paraRascunho(pesos));
  const [justificativa, setJustificativa] = useState('');
  const [erros, setErros] = useState<string[]>([]);
  const [salvou, setSalvou] = useState(false);
  // Depois de "Salvar" com erro, o foco vai para onde a pessoa conserta (como no Simulador, WCAG 3.3.1).
  const focarDepois = useRef<string | null>(null);
  useEffect(() => {
    if (focarDepois.current === null) return;
    document.getElementById(focarDepois.current)?.focus();
    focarDepois.current = null;
  });

  const novos = paraPesos(rascunho);
  const validacao = validarPesos(novos);
  const algumVazio = COMPONENTES.some((c) => !Number.isFinite(novos[c]));
  const algumForaDaFaixa = COMPONENTES.some((c) => pesoInvalido(novos[c]));
  const somaTexto = algumVazio ? '—' : formatarPercentual(validacao.soma);
  let motivo = ' (certo)';
  if (algumVazio) motivo = ' (preencha todos os pesos)';
  else if (algumForaDaFaixa) motivo = ' (há peso fora de 0 a 100)';
  else if (!validacao.valido) motivo = ' (precisa dar 100%)';
  const justificativaInvalida = erros.includes(ERRO_JUSTIFICATIVA);
  // Depois de um "Salvar" recusado pelos pesos, os seis campos ficam marcados até a soma ficar certa.
  const pesosInvalidosAoSalvar = !validacao.valido && erros.some((e) => e !== ERRO_JUSTIFICATIVA);
  const previa = validacao.valido && !iguais(novos, pesos) ? compararPesos(base, pesos, novos) : undefined;

  const editar = (proximo: Rascunho): void => {
    setRascunho(proximo);
    setSalvou(false);
  };

  const salvar = (): void => {
    const r = trocarPesos(novos, justificativa);
    if (!r.ok) {
      setErros(r.erros);
      setSalvou(false);
      focarDepois.current = r.erros.includes(ERRO_JUSTIFICATIVA) ? ID_JUSTIFICATIVA : ID_ERROS;
      return;
    }
    setErros([]);
    setJustificativa('');
    setSalvou(true);
  };

  const linhasComparacao: LinhaComparacao[] = COMPONENTES.map((c) => ({
    componente: c,
    original: PESOS_ORIGINAIS_V5[c],
    vigente: pesos[c],
    rascunho: novos[c],
  }));
  const colunasComparacao: ColunaResponsiva<LinhaComparacao>[] = [
    { title: 'Componente', key: 'componente', className: 'break-words', render: (_v, l) => ROTULO_COMPONENTE[l.componente] },
    { title: 'Original (v5)', key: 'original', width: 95, render: (_v, l) => porcento(l.original) },
    { title: 'Em vigor', key: 'vigente', width: 90, render: (_v, l) => porcento(l.vigente) },
    { title: 'Rascunho', key: 'rascunho', width: 95, responsive: VISIVEL_A_PARTIR.sm, render: (_v, l) => porcento(l.rascunho) },
  ];

  const colunasVersoes: ColunaResponsiva<VersaoPesos>[] = [
    {
      title: 'Versão',
      key: 'nome',
      className: 'break-words',
      render: (_v, v) => (
        <>
          {v.nome}
          {v.id === versaoVigente.id && (
            <span className="ml-2 inline-block rounded bg-[#E8F5EB] px-1.5 text-xs font-semibold text-[#1E7B3A]">Em vigor</span>
          )}
        </>
      ),
    },
    { title: 'Criada em', key: 'criada_em', width: 140, responsive: VISIVEL_A_PARTIR.sm, render: (_v, v) => formatFortaleza(v.criada_em) },
    { title: 'Autor', key: 'autor', width: 170, className: 'break-words', responsive: VISIVEL_A_PARTIR.md, render: (_v, v) => v.autor },
    { title: 'Justificativa', key: 'justificativa', className: 'break-words', responsive: VISIVEL_A_PARTIR.md, render: (_v, v) => v.justificativa },
    {
      title: 'Pesos',
      key: 'pesos',
      className: 'break-words',
      responsive: VISIVEL_A_PARTIR.detalhe,
      render: (_v, v) => COMPONENTES.map((c) => `${ROTULO_COMPONENTE[c]} ${v.pesos[c]}%`).join(' · '),
    },
  ];

  return (
    <section aria-labelledby="ica-pesos-titulo">
      <Title level={1} id="ica-pesos-titulo" style={{ fontSize: 26, marginBottom: 8 }}>
        Pesos e faixas
      </Title>
      <p className="mb-4">
        Os pesos dizem quanto cada componente conta no ICA e somam 100%. Pelo PDF, só a SPE muda os pesos; no protótipo,
        quem tem acesso pode testar. Cada mudança cria uma versão nova, com data, autor e justificativa, e os semestres já
        calculados guardam a versão que usaram.
      </p>

      <section aria-labelledby="ica-pesos-vigente" className="mb-6 rounded border border-[#d9d9d9] bg-white p-3">
        <Title level={2} id="ica-pesos-vigente" style={{ ...TITULO, marginTop: 0 }}>
          Versão em vigor
        </Title>
        <p className="mb-1 font-semibold">{versaoVigente.nome}</p>
        <p className="mb-1 text-sm">
          Criada em {formatFortaleza(versaoVigente.criada_em)} por {versaoVigente.autor}.
        </p>
        <p className="m-0 text-sm">Justificativa: {versaoVigente.justificativa}</p>
      </section>

      <section aria-labelledby="ica-pesos-editar" className="mb-6">
        <Title level={2} id="ica-pesos-editar" style={TITULO}>
          Mudar os pesos
        </Title>
        <div className="mb-3 flex flex-wrap gap-2">
          <Button onClick={() => editar(paraRascunho(PESOS_ORIGINAIS_V5))}>Usar a configuração original (v5)</Button>
          <Button onClick={() => editar(paraRascunho(pesos))}>Voltar à versão em vigor</Button>
        </div>
        <div className="grid max-w-3xl gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {COMPONENTES.map((c) => (
            <div key={c}>
              <label htmlFor={`ica-peso-${c}`} className={CLASSE_ROTULO}>
                {ROTULO_COMPONENTE[c]}: peso em %
              </label>
              <input
                id={`ica-peso-${c}`}
                type="number"
                min={0}
                max={100}
                step={1}
                inputMode="numeric"
                className={CLASSE_CAMPO}
                value={rascunho[c]}
                aria-invalid={pesoInvalido(novos[c]) || pesosInvalidosAoSalvar || undefined}
                aria-describedby={ID_SOMA}
                onChange={(e) => editar({ ...rascunho, [c]: e.target.value })}
              />
            </div>
          ))}
        </div>
        <p
          id={ID_SOMA}
          role="status"
          aria-label="Soma dos pesos"
          className={`mt-3 inline-block rounded px-2 py-1 font-semibold ${
            validacao.valido ? 'bg-[#E8F5EB] text-[#1E7B3A]' : 'bg-[#FBE6E5] text-[#C0392B]'
          }`}
        >
          Soma: {somaTexto}
          {motivo}
        </p>
        <div className="mt-3 max-w-2xl">
          <label htmlFor={ID_JUSTIFICATIVA} className={CLASSE_ROTULO}>
            Justificativa da mudança
          </label>
          <textarea
            id={ID_JUSTIFICATIVA}
            className={CLASSE_CAMPO}
            rows={3}
            value={justificativa}
            aria-invalid={justificativaInvalida || undefined}
            aria-describedby={justificativaInvalida ? ID_ERROS : undefined}
            onChange={(e) => setJustificativa(e.target.value)}
          />
          {/* Os erros ficam junto do campo e do botão, ligados ao campo (WCAG 3.3.1). */}
          {erros.length > 0 && (
            <div id={ID_ERROS} tabIndex={-1} className={`mt-2 ${CLASSE_FOCO}`}>
              <Alert
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
            </div>
          )}
          <Button type="primary" className="mt-2" onClick={salvar}>
            Salvar como nova versão
          </Button>
        </div>
        {/* Região viva sempre montada: só o texto muda, para o leitor de tela anunciar (WCAG 4.1.3). */}
        <p role="status" className={salvou ? 'mt-3 rounded bg-[#E8F5EB] p-2 text-[#1E7B3A]' : 'sr-only'}>
          {salvou ? `${versaoVigente.nome} criada e em vigor. O ICA de todos foi recalculado com ela.` : ''}
        </p>
      </section>

      <section aria-labelledby="ica-pesos-previa" className="mb-6">
        <Title level={2} id="ica-pesos-previa" style={TITULO}>
          Como fica com estes pesos
        </Title>
        {!validacao.valido && <p>Ajuste os pesos para somarem 100% e veja aqui o resultado.</p>}
        {validacao.valido && !previa && <p>Os pesos são os da versão em vigor: nada muda.</p>}
        {previa && (
          <>
            <ul aria-label="Quantos em cada estrato" className="m-0 mb-3 grid list-none gap-1 p-0 sm:grid-cols-2">
              {ESTRATOS.map((e) => (
                <li key={e.chave}>
                  {e.nome}: {previa.a.porEstrato[e.chave]} → {previa.b.porEstrato[e.chave]}
                </li>
              ))}
              <li>
                Sem municípios: {previa.a.semMunicipios} → {previa.b.semMunicipios}
              </li>
            </ul>
            {previa.mudaramDeEstrato.length === 0 ? (
              <p>Ninguém muda de estrato.</p>
            ) : (
              <>
                <p className="mb-1">Mudam de estrato (em vigor → rascunho):</p>
                <ul className="pl-5">
                  {previa.mudaramDeEstrato.map((l) => (
                    <li key={l.coordenadorId}>
                      {l.nome}: {etiqueta(l.antes)} → {etiqueta(l.depois)}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </section>

      <section aria-labelledby="ica-pesos-v5" className="mb-6">
        <Title level={2} id="ica-pesos-v5" style={TITULO}>
          Comparação com a configuração original (v5)
        </Title>
        <p className="text-sm">
          A revisada (nov/2026) tirou Estados (UFs) e pôs o tempo de deslocamento. O Comparativo mostra quem muda de
          estrato entre duas versões.
        </p>
        <ResponsiveTable<LinhaComparacao>
          rowKey="componente"
          columns={colunasComparacao}
          dataSource={linhasComparacao}
          pagination={false}
          nomeDaLinha={(l) => ROTULO_COMPONENTE[l.componente]}
        />
      </section>

      <section aria-labelledby="ica-pesos-versoes" className="mb-6">
        <Title level={2} id="ica-pesos-versoes" style={TITULO}>
          Versões
        </Title>
        <ResponsiveTable<VersaoPesos>
          rowKey="id"
          columns={colunasVersoes}
          dataSource={[...versoesPesos].reverse()}
          pagination={false}
          nomeDaLinha={(v) => v.nome}
        />
      </section>

      <section aria-labelledby="ica-pesos-faixas">
        <Title level={2} id="ica-pesos-faixas" style={TITULO}>
          Faixas
        </Title>
        <FaixasLegenda />
        <p className="mt-2 text-sm">
          Como no protótipo, as faixas ficam fixas também na versão real (decisão 65). Só os pesos mudam.
        </p>
      </section>
    </section>
  );
}
