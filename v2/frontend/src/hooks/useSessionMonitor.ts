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
 * Comportamento:
 * - Monitora tempo de sessão a cada 60s
 * - Mostra aviso quando faltam < 5 min (300s)
 * - Permite renovação manual via botão "Continuar logado"
 *
 * Refs:
 * - CP5 (Issue #164): Monitor de sessão
 * - CP2: SESSION_COOKIE_AGE=7200 (2 horas)
 * - PA-06: Controle explícito (ISO 9241-110)
 */

import { useState, useEffect, useCallback } from 'react';
import api from '../api';

const WARNING_THRESHOLD = 300; // 5 minutos em segundos
const CHECK_INTERVAL = 60000; // Verificar a cada 60 segundos

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
  renewSession: () => Promise<boolean>;
}

const useSessionMonitor = (): UseSessionMonitorReturn => {
  const [sessionAge, setSessionAge] = useState<number>(7200); // Default: 2 horas
  const [lastActivity, setLastActivity] = useState<number>(Date.now());
  const [showWarning, setShowWarning] = useState<boolean>(false);

  /**
   * Calcula tempo restante de sessão.
   */
  const getTimeLeft = useCallback((): number => {
    const elapsed = Math.floor((Date.now() - lastActivity) / 1000);
    const timeLeft = sessionAge - elapsed;
    return Math.max(0, timeLeft);
  }, [lastActivity, sessionAge]);

  /**
   * Renova sessão chamando /api/auth/ping/.
   */
  const renewSession = useCallback(async (): Promise<boolean> => {
    try {
      const response = await api.post<PingResponse>('/auth/ping/');
      const { session_age } = response.data;

      setSessionAge(session_age);
      setLastActivity(Date.now());
      setShowWarning(false);

      return true;
    } catch (err) {
      // Erro ao renovar sessão - pode ser 401/403 (sessão expirada)
      const axiosError = err as { response?: { status?: number } };

      // Se retornar 401/403, sessão expirou
      if (axiosError.response?.status === 401 || axiosError.response?.status === 403) {
        window.location.href = '/login'; // Redirecionar para login
      }

      return false;
    }
  }, []);

  /**
   * Atualiza lastActivity em qualquer interação do usuário.
   */
  useEffect(() => {
    const handleActivity = (): void => {
      // SESSION_SAVE_EVERY_REQUEST=True renova automaticamente
      // Apenas atualizamos o timestamp local
      setLastActivity(Date.now());
      setShowWarning(false);
    };

    // Eventos de atividade do usuário
    const events: Array<keyof WindowEventMap> = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach((event) => window.addEventListener(event, handleActivity));

    return () => {
      events.forEach((event) => window.removeEventListener(event, handleActivity));
    };
  }, []);

  /**
   * Timer para verificar tempo restante periodicamente.
   */
  useEffect(() => {
    const intervalId = setInterval(() => {
      const timeLeft = getTimeLeft();

      // Mostrar aviso se faltam menos de 5 min
      if (timeLeft <= WARNING_THRESHOLD && timeLeft > 0) {
        setShowWarning(true);
      } else if (timeLeft === 0) {
        // Sessão expirou - redirecionar para login
        setShowWarning(false);
        window.location.href = '/login';
      }
    }, CHECK_INTERVAL);

    return () => clearInterval(intervalId);
  }, [getTimeLeft]);

  return {
    timeLeft: getTimeLeft(),
    showWarning,
    sessionAge,
    renewSession,
  };
};

export default useSessionMonitor;
