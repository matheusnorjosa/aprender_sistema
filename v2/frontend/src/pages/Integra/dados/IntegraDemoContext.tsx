/**
 * Estado da sessão da demonstração da Integra (DADOS SIMULADOS).
 *
 * Fica só na memória da aba: trocar pesos cria uma versão nova, remanejamentos passam por
 * propor → aprovar → aplicar, e os alertas são recalculados. Recarregar a página volta ao original.
 * Nada é gravado no banco.
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useReducer, useRef, type JSX, type ReactNode } from 'react';
import {
  aplicarMovimentos,
  calcularEquipe,
  gerarAlertas,
  validarPesos,
  type Alerta,
  type ResultadoEquipe,
} from '../ica/calculo';
import { carregarDadosIntegra } from './fonte';
import type { BaseIca, DadosIntegra, Movimento, Pesos, Remanejamento, VersaoPesos } from './tipos';

/** Autor fictício das ações feitas na demonstração. */
export const AUTOR_DEMO = 'Você (demonstração)';

export interface EstadoIntegraDemo {
  /** Os dados como vieram da fonte (não mudam na sessão). */
  dados: DadosIntegra;
  /** A carteira vigente na sessão (muda quando um remanejamento é aplicado). */
  base: BaseIca;
  versoesPesos: VersaoPesos[];
  versaoVigenteId: string;
  /** Os já aplicados nos semestres anteriores e os da sessão. */
  remanejamentos: Remanejamento[];
}

export type AcaoIntegraDemo =
  | { tipo: 'trocar_pesos'; pesos: Pesos; justificativa: string; em: string }
  | { tipo: 'propor_remanejamento'; id: string; movimentos: Movimento[]; justificativa: string; em: string }
  | { tipo: 'aprovar_remanejamento'; id: string; em: string }
  | { tipo: 'aplicar_remanejamento'; id: string; em: string }
  | { tipo: 'restaurar' };

export function estadoInicial(dados: DadosIntegra): EstadoIntegraDemo {
  return {
    dados,
    base: dados.base,
    versoesPesos: dados.versoes_pesos,
    versaoVigenteId: dados.versao_vigente,
    remanejamentos: dados.remanejamentos,
  };
}

export function reducerIntegraDemo(estado: EstadoIntegraDemo, acao: AcaoIntegraDemo): EstadoIntegraDemo {
  switch (acao.tipo) {
    case 'trocar_pesos': {
      const numero = estado.versoesPesos.length + 1;
      const versao: VersaoPesos = {
        id: `sessao-${numero}`,
        nome: `Versão ${numero} (demonstração)`,
        pesos: { ...acao.pesos },
        criada_em: acao.em,
        autor: AUTOR_DEMO,
        justificativa: acao.justificativa,
      };
      return { ...estado, versoesPesos: [...estado.versoesPesos, versao], versaoVigenteId: versao.id };
    }
    case 'propor_remanejamento': {
      // Guarda o que cada movimento leva hoje: aplicar depois move só isso (ou recusa, se a carteira mudou).
      const novo: Remanejamento = {
        id: acao.id,
        movimentos: acao.movimentos.map((m) => ({
          ...m,
          atendimentos: estado.base.atendimentos
            .filter((a) => a.municipio === m.municipioId && a.coordenador === m.deCoordenadorId)
            .map((a) => a.id),
        })),
        justificativa: acao.justificativa,
        status: 'proposto',
        proposto_por: AUTOR_DEMO,
        proposto_em: acao.em,
        aprovado_por: null,
        aprovado_em: null,
        aplicado_em: null,
        semestre: null,
      };
      return { ...estado, remanejamentos: [...estado.remanejamentos, novo] };
    }
    case 'aprovar_remanejamento':
      return {
        ...estado,
        remanejamentos: estado.remanejamentos.map((r) =>
          r.id === acao.id && r.status === 'proposto'
            ? { ...r, status: 'aprovado', aprovado_por: AUTOR_DEMO, aprovado_em: acao.em }
            : r,
        ),
      };
    case 'aplicar_remanejamento': {
      const r = estado.remanejamentos.find((x) => x.id === acao.id);
      if (!r || r.status !== 'aprovado') return estado;
      // Proposta velha (outra já mexeu no município): aplicar pela metade daria um registro falso.
      const { base, invalidos } = aplicarMovimentos(estado.base, r.movimentos);
      if (invalidos.length > 0) return estado;
      return {
        ...estado,
        base,
        remanejamentos: estado.remanejamentos.map((x) =>
          x.id === acao.id
            ? { ...x, status: 'aplicado', aplicado_em: acao.em, semestre: estado.dados.semestre_atual }
            : x,
        ),
      };
    }
    case 'restaurar':
      return estadoInicial(estado.dados);
  }
}

export type Resultado<T extends object = object> = ({ ok: true } & T) | { ok: false; erros: string[] };

export interface SemestreCalculado {
  semestre: string;
  calculado_em: string;
  versao: VersaoPesos;
  resultado: ResultadoEquipe;
}

export interface ValorIntegraDemo {
  dados: DadosIntegra;
  base: BaseIca;
  versoesPesos: VersaoPesos[];
  versaoVigente: VersaoPesos;
  pesos: Pesos;
  /** ICA de todos com a carteira e os pesos vigentes na sessão. */
  resultado: ResultadoEquipe;
  /** Cada semestre calculado com a versão de pesos que valia nele. */
  historico: SemestreCalculado[];
  /** A sessão aplicou remanejamento ou trocou os pesos: `resultado` já não é o retrato publicado. */
  mudouNaSessao: boolean;
  alertas: Alerta[];
  remanejamentos: Remanejamento[];
  trocarPesos: (pesos: Pesos, justificativa: string) => Resultado;
  proporRemanejamento: (movimentos: Movimento[], justificativa: string) => Resultado<{ id: string }>;
  aprovarRemanejamento: (id: string) => void;
  /** Recusa a proposta que ficou velha (o município já não está com quem ia ceder). */
  aplicarRemanejamento: (id: string) => Resultado;
  restaurar: () => void;
}

const IntegraDemoContext = createContext<ValorIntegraDemo | undefined>(undefined);

const agora = (): string => new Date().toISOString();

function versaoPorId(versoes: readonly VersaoPesos[], id: string): VersaoPesos {
  const versao = versoes.find((v) => v.id === id) ?? versoes[0];
  if (!versao) throw new Error('Nenhuma versão de pesos cadastrada.');
  return versao;
}

interface IntegraDemoProviderProps {
  children: ReactNode;
  /** Para testes; por padrão, `carregarDadosIntegra()`. */
  dados?: DadosIntegra;
}

export function IntegraDemoProvider({ children, dados }: IntegraDemoProviderProps): JSX.Element {
  const [estado, dispatch] = useReducer(reducerIntegraDemo, dados, (d) => estadoInicial(d ?? carregarDadosIntegra()));
  const propostas = useRef(0);

  const versaoVigente = versaoPorId(estado.versoesPesos, estado.versaoVigenteId);
  const pesos = versaoVigente.pesos;

  const resultado = useMemo(() => calcularEquipe(estado.base, pesos), [estado.base, pesos]);

  const historico = useMemo<SemestreCalculado[]>(
    () =>
      estado.dados.historico.map((h) => {
        const versao = versaoPorId(estado.dados.versoes_pesos, h.versao_pesos);
        return { semestre: h.semestre, calculado_em: h.calculado_em, versao, resultado: calcularEquipe(h.base, versao.pesos) };
      }),
    [estado.dados],
  );

  // "Entra em Sobrecarga" (PDF, seção 6) compara com o cálculo imediatamente anterior ao atual: quem já
  // estava lá não recebe o aviso de novo (continua no "fora da meta"). Sem mudança na sessão, o atual é
  // o retrato publicado do semestre (último do histórico) e o anterior é o semestre de antes. Depois de
  // aplicar um remanejamento ou trocar os pesos, o atual é um recálculo e o anterior é o retrato publicado.
  const mudouNaSessao = estado.base !== estado.dados.base || estado.versaoVigenteId !== estado.dados.versao_vigente;
  const anterior = historico.at(mudouNaSessao ? -1 : -2)?.resultado;
  const alertas = useMemo(
    () =>
      gerarAlertas(estado.base, resultado, {
        gerencias: estado.dados.gerencias,
        pessoas: estado.dados.pessoas,
        colecoes: estado.dados.colecoes,
        anterior,
      }),
    [estado.base, estado.dados, resultado, anterior],
  );

  const trocarPesos = useCallback((novos: Pesos, justificativa: string): Resultado => {
    const erros = [...validarPesos(novos).erros];
    if (justificativa.trim() === '') erros.push('Escreva a justificativa da mudança.');
    if (erros.length > 0) return { ok: false, erros };
    dispatch({ tipo: 'trocar_pesos', pesos: novos, justificativa: justificativa.trim(), em: agora() });
    return { ok: true };
  }, []);

  const proporRemanejamento = useCallback(
    (movimentos: Movimento[], justificativa: string): Resultado<{ id: string }> => {
      const erros: string[] = [];
      if (movimentos.length === 0) erros.push('Escolha pelo menos um município para mover.');
      else if (aplicarMovimentos(estado.base, movimentos).invalidos.length > 0) {
        erros.push('Algum município escolhido não está na carteira de origem.');
      }
      if (justificativa.trim() === '') erros.push('Escreva a justificativa do remanejamento.');
      if (erros.length > 0) return { ok: false, erros };
      propostas.current += 1;
      const id = `sessao-rem-${propostas.current}`;
      dispatch({ tipo: 'propor_remanejamento', id, movimentos, justificativa: justificativa.trim(), em: agora() });
      return { ok: true, id };
    },
    [estado.base],
  );

  const aprovarRemanejamento = useCallback((id: string) => dispatch({ tipo: 'aprovar_remanejamento', id, em: agora() }), []);
  const aplicarRemanejamento = useCallback(
    (id: string): Resultado => {
      const proposta = estado.remanejamentos.find((r) => r.id === id);
      const invalidos = proposta ? aplicarMovimentos(estado.base, proposta.movimentos).invalidos : [];
      if (invalidos.length > 0) {
        const nome = (cid: number): string => estado.base.coordenadores.find((c) => c.id === cid)?.nome ?? `coordenador ${cid}`;
        const onde = (mid: number): string => {
          const m = estado.base.municipios.find((x) => x.id === mid);
          return m ? `${m.nome}-${m.uf}` : `município ${mid}`;
        };
        const quais = invalidos
          .map((m) =>
            estado.base.atendimentos.some((a) => a.municipio === m.municipioId && a.coordenador === m.deCoordenadorId)
              ? `a carteira de ${nome(m.deCoordenadorId)} em ${onde(m.municipioId)} mudou depois da proposta`
              : `${onde(m.municipioId)} já não está com ${nome(m.deCoordenadorId)}`,
          )
          .join('; ');
        return { ok: false, erros: [`Esta proposta ficou velha: ${quais}. Proponha de novo a partir da carteira de agora.`] };
      }
      dispatch({ tipo: 'aplicar_remanejamento', id, em: agora() });
      return { ok: true };
    },
    [estado.base, estado.remanejamentos],
  );
  const restaurar = useCallback(() => dispatch({ tipo: 'restaurar' }), []);

  const valor = useMemo<ValorIntegraDemo>(
    () => ({
      dados: estado.dados,
      base: estado.base,
      versoesPesos: estado.versoesPesos,
      versaoVigente,
      pesos,
      resultado,
      historico,
      mudouNaSessao,
      alertas,
      remanejamentos: estado.remanejamentos,
      trocarPesos,
      proporRemanejamento,
      aprovarRemanejamento,
      aplicarRemanejamento,
      restaurar,
    }),
    [estado, versaoVigente, pesos, resultado, historico, mudouNaSessao, alertas, trocarPesos, proporRemanejamento, aprovarRemanejamento, aplicarRemanejamento, restaurar],
  );

  return <IntegraDemoContext.Provider value={valor}>{children}</IntegraDemoContext.Provider>;
}

export function useIntegraDemo(): ValorIntegraDemo {
  const valor = useContext(IntegraDemoContext);
  if (!valor) throw new Error('useIntegraDemo precisa estar dentro de <IntegraDemoProvider>.');
  return valor;
}
