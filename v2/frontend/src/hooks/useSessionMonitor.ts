/**
 * AS v2 — useSessionMonitor Hook (CP5 - Issue #164)
 *
 * Hook para monitorar tempo de sessão e avisar antes da expiração.
 *
 * State:
 * - timeLeft: number (segundos restantes de sessão)
 * - showWarning: bool (exibir aviso quando < 5 min)
 * - sessionAge: number (duração total da sessão em segundos, do backend)
 *
 * Methods:
 * - renewSession(): Chama /api/auth/ping/ para renovar sessão
 *
 * Parâmetro:
 * - onExpired: o servidor disse que não há sessão. O App leva ao login com o motivo, SEM
 *   POST de logout (auditoria UX 30/09, rodada 2). Chamado quando a pergunta ao servidor
 *   ou o ping voltam 401/403.
 *
 * Comportamento:
 * - O relógio local conta da última resposta do servidor a um request de QUALQUER aba logada
 *   deste navegador: o Django renova a sessão em todo request que atende
 *   (SESSION_SAVE_EVERY_REQUEST) e a vence 2 h depois do último. O fetchNaRede avisa cada resposta
 *   desta aba (SERVIDOR_RESPONDEU) e o monitor guarda o horário no localStorage, comum às abas (ao
 *   montar, vale a resposta do boot). Assim a pergunta do zero chega depois do vencimento: as abas
 *   paradas vão ao login 120-122 min depois do último request de qualquer uma, sem esticar a
 *   sessão (auditoria UX 30/09, rodadas 4 e 5). Antes cada aba contava só dos próprios requests, e
 *   a pergunta de uma renovava a sessão para a outra: duas abas largadas a mantinham viva sem
 *   limite. Quem grava é o monitor, que só existe com usuário logado: os requests da tela de login
 *   (o /api/csrf/ responde 200 sem sessão) não contam. Sem storage, cada aba conta só dos próprios
 *   requests, e a pergunta ao servidor decide
 * - Atividade (mousedown/keydown/scroll/touchstart) renova em segundo plano com GET /api/me/, no
 *   máximo a cada 10 min: quem só digita não perde a sessão (rodada 3)
 * - Monitora tempo de sessão a cada 60s
 * - Mostra aviso quando faltam < 5 min (300s), com a contagem andando a cada segundo
 * - Permite renovação manual via botão "Continuar logado"; falha de rede/5xx fica em
 *   renewError (o aviso mostra o motivo)
 * - Relógio zerado NÃO encerra a sessão: o relógio é desta aba, a sessão é do navegador.
 *   Pergunta ao servidor (GET /api/me/): viva (outra aba em uso) → recomeça o relógio;
 *   401/403 → onExpired; rede/5xx → pergunta de novo no minuto seguinte
 * - Com o aviso aberto, a atividade não mexe no relógio nem fecha o aviso; uma resposta do
 *   servidor a um request de qualquer aba logada fecha, na conferência seguinte (a sessão foi
 *   renovada lá)
 *
 * Refs:
 * - CP5 (Issue #164): Monitor de sessão
 * - CP2: SESSION_COOKIE_AGE=7200 (2 horas)
 * - PA-06: Controle explícito (ISO 9241-110)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { fetchAPI, SEM_CONEXAO, SERVIDOR_RESPONDEU } from '../api/config';
import { isAuthError } from '../utils/errors';
import { getStorageInt, setStorageInt, storageKeys } from '../utils/storage';

const WARNING_THRESHOLD = 300; // 5 minutos em segundos
const CHECK_INTERVAL = 60000; // Verificar a cada 60 segundos
/**
 * Espera depois do zero local antes de perguntar ao servidor. A pergunta renova a sessão lá
 * (SESSION_SAVE_EVERY_REQUEST): no zero exato, a sessão de uma aba sozinha pode ainda não ter
 * vencido no servidor (latência, ou TTL arredondado) e seria esticada por mais 2 h.
 */
const FOLGA_PARA_PERGUNTAR = CHECK_INTERVAL;
/** Intervalo mínimo entre as renovações disparadas pela atividade. */
const RENOVAR_POR_ATIVIDADE_A_CADA = 10 * 60 * 1000;

/** Última resposta do servidor a qualquer aba logada deste navegador (localStorage, comum às abas). */
const lerDeTodasAsAbas = (): number => getStorageInt(storageKeys.sessaoUltimaResposta, 0);
const gravarParaTodasAsAbas = (quando: number): void => setStorageInt(storageKeys.sessaoUltimaResposta, quando);

/** Motivo legível de uma falha ao renovar (o aviso mostra). */
function motivoDoErro(err: unknown): string {
  if (err instanceof TypeError) return SEM_CONEXAO;
  if (err instanceof Error && err.message) return err.message;
  return 'Erro inesperado do servidor.';
}

/**
 * Ping response from backend
 */
interface PingResponse {
  session_age: number;
}

/**
 * Return type for useSessionMonitor
 */
export interface UseSessionMonitorReturn {
  timeLeft: number;
  showWarning: boolean;
  sessionAge: number;
  /** Motivo da última falha ao renovar (rede/5xx); null quando não há. */
  renewError: string | null;
  renewSession: () => Promise<boolean>;
}

const useSessionMonitor = (onExpired: () => void | Promise<void>): UseSessionMonitorReturn => {
  const [sessionAge, setSessionAge] = useState<number>(7200); // Default: 2 horas
  // Última renovação da sessão no servidor vista por esta aba: a última resposta dele a um
  // request daqui (o boot acabou de chamar /api/me/). O ref recebe cada resposta; o estado só
  // acompanha na conferência de 60 s, para a renderização, com a mais recente entre o ref e a
  // de todas as abas.
  const ultimaRespostaRef = useRef(Date.now());
  const [ultimaRenovacao, setUltimaRenovacao] = useState<number>(ultimaRespostaRef.current);
  const [showWarning, setShowWarning] = useState<boolean>(false);
  const [renewError, setRenewError] = useState<string | null>(null);
  // Espelho do aviso para o listener de atividade, registrado uma vez só.
  const avisoAbertoRef = useRef(false);
  const perguntandoRef = useRef(false);
  const ultimaTentativaRef = useRef(Date.now());
  // Só re-renderiza a cada segundo com o aviso aberto: a contagem anda.
  const [, setTique] = useState(0);

  const mostrarAviso = useCallback((aberto: boolean): void => {
    avisoAbertoRef.current = aberto;
    setShowWarning(aberto);
  }, []);

  /** O servidor acabou de renovar a sessão: recomeça o relógio local e fecha o aviso. */
  const recomecar = useCallback((): void => {
    const agora = Date.now();
    ultimaTentativaRef.current = agora;
    ultimaRespostaRef.current = agora;
    gravarParaTodasAsAbas(agora);
    setUltimaRenovacao(agora);
    mostrarAviso(false);
    setRenewError(null);
  }, [mostrarAviso]);

  // Cada resposta do servidor a um request desta aba renova a sessão lá (o fetchNaRede avisa), e a
  // sessão é de todas as abas: o horário vai também para elas. Ao montar, vale o do boot.
  useEffect(() => {
    const anotar = (): void => {
      ultimaRespostaRef.current = Date.now();
      gravarParaTodasAsAbas(ultimaRespostaRef.current);
    };
    gravarParaTodasAsAbas(ultimaRespostaRef.current);
    window.addEventListener(SERVIDOR_RESPONDEU, anotar);
    return () => window.removeEventListener(SERVIDOR_RESPONDEU, anotar);
  }, []);

  /**
   * Calcula tempo restante de sessão.
   */
  const getTimeLeft = useCallback((): number => {
    const elapsed = Math.floor((Date.now() - ultimaRenovacao) / 1000);
    const timeLeft = sessionAge - elapsed;
    return Math.max(0, timeLeft);
  }, [ultimaRenovacao, sessionAge]);

  /**
   * Renova sessão chamando /api/auth/ping/ ("Continuar logado").
   */
  const renewSession = useCallback(async (): Promise<boolean> => {
    try {
      const data = await fetchAPI<PingResponse>('/auth/ping/', { method: 'POST' });
      setSessionAge(data.session_age);
      recomecar();
      return true;
    } catch (err) {
      if (isAuthError(err)) {
        // O servidor disse que não há sessão: o App leva ao login.
        void onExpired();
      } else {
        // Rede/5xx: a sessão pode estar viva; o aviso continua e mostra o motivo.
        setRenewError(motivoDoErro(err));
      }
      return false;
    }
  }, [onExpired, recomecar]);

  /**
   * Relógio local zerado: pergunta ao servidor em vez de encerrar. O relógio é desta aba; a
   * sessão é do navegador, e outra aba pode estar em uso (auditoria UX 30/09, rodada 2).
   */
  const perguntarAoServidor = useCallback(async (): Promise<void> => {
    if (perguntandoRef.current) return;
    perguntandoRef.current = true;
    try {
      await fetchAPI('/me/');
      recomecar(); // sessão viva: recomeça o relógio, sem logout
    } catch (err) {
      if (isAuthError(err)) void onExpired();
      // Rede/5xx: sem resposta do servidor; pergunta de novo no próximo minuto.
    } finally {
      perguntandoRef.current = false;
    }
  }, [onExpired, recomecar]);

  /**
   * Atividade renova a sessão no servidor, em segundo plano e sem nada visível, no máximo a
   * cada 10 min. Digitar e rolar não fazem request: sem isso a sessão vencia no servidor de
   * quem estava usando, e o próximo salvar caía no login (auditoria UX 30/09, rodada 3).
   * 401/403 aqui o fetchAPI já avisa o App (auth:expired); rede/5xx: o relógio segue contando
   * da última resposta do servidor, e o aviso aparece se nenhuma outra vier.
   */
  const renovarPorAtividade = useCallback(async (): Promise<void> => {
    const agora = Date.now();
    if (perguntandoRef.current || agora - ultimaTentativaRef.current < RENOVAR_POR_ATIVIDADE_A_CADA) return;
    perguntandoRef.current = true;
    ultimaTentativaRef.current = agora;
    try {
      await fetchAPI('/me/');
      recomecar();
    } catch {
      // Sem nada visível: ver acima.
    } finally {
      perguntandoRef.current = false;
    }
  }, [recomecar]);

  useEffect(() => {
    const handleActivity = (): void => {
      // Com o aviso aberto, só "Continuar logado" ou "Sair agora" decidem: a atividade não
      // fecha o aviso (o mousedown do "Sair agora" sumia com o botão antes do click) nem
      // mexe no relógio (um Tab até o botão fazia o aviso mostrar 120:00).
      if (avisoAbertoRef.current) return;
      void renovarPorAtividade();
    };

    // Eventos de atividade do usuário
    const events: Array<keyof WindowEventMap> = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach((event) => window.addEventListener(event, handleActivity));

    return () => {
      events.forEach((event) => window.removeEventListener(event, handleActivity));
    };
  }, [renovarPorAtividade]);

  useEffect(() => {
    if (!showWarning) return undefined;
    const id = setInterval(() => setTique((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [showWarning]);

  /**
   * Timer para verificar tempo restante periodicamente, contando da última resposta do servidor.
   */
  useEffect(() => {
    const intervalId = setInterval(() => {
      const ultima = Math.max(ultimaRespostaRef.current, lerDeTodasAsAbas());
      if (ultima !== ultimaRenovacao) setUltimaRenovacao(ultima);
      const decorrido = Date.now() - ultima;
      if (decorrido >= sessionAge * 1000 + FOLGA_PARA_PERGUNTAR) {
        void perguntarAoServidor();
      } else {
        // Abre faltando ≤ 5 min; fecha se um request desta aba renovou a sessão nesse meio-tempo.
        mostrarAviso(sessionAge - Math.floor(decorrido / 1000) <= WARNING_THRESHOLD);
      }
    }, CHECK_INTERVAL);

    return () => clearInterval(intervalId);
  }, [ultimaRenovacao, sessionAge, perguntarAoServidor, mostrarAviso]);

  return {
    timeLeft: getTimeLeft(),
    showWarning,
    sessionAge,
    renewError,
    renewSession,
  };
};

export default useSessionMonitor;
