/**
 * Centralized localStorage helpers.
 *
 * Provides typed get/set with error handling and namespaced keys.
 */

export const storageKeys = {
  gcalErrors: 'gcalAlertsLastErrors',
  notifUnread: (userId: number | string) => `notifLastUnread:${userId}`,
  /** sessionStorage: motivo mostrado na tela de login depois do reload (ex.: sessão expirada). */
  avisoLogin: 'avisoLogin',
  /**
   * Horário (ms) da última resposta do servidor a uma aba logada; comum às abas (monitor de sessão).
   * O "Sair" o apaga: o evento 'storage' avisa as outras abas (App.tsx).
   */
  sessaoUltimaResposta: 'sessaoUltimaResposta',
} as const;

export function getStorageInt(key: string, fallback: number): number {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    const parsed = parseInt(raw, 10);
    return Number.isNaN(parsed) ? fallback : parsed;
  } catch {
    return fallback;
  }
}

export function setStorageInt(key: string, value: number): void {
  try {
    localStorage.setItem(key, value.toString());
  } catch {
    // quota exceeded or private browsing — silently ignore
  }
}

/**
 * A sessão acabou neste navegador ("Sair"): apaga o horário comum às abas. O navegador entrega o
 * evento 'storage' às outras, que perguntam ao servidor na hora. Sem storage, elas descobrem no
 * próximo request ou na pergunta do relógio.
 */
export function avisarSaidaAsOutrasAbas(): void {
  try {
    localStorage.removeItem(storageKeys.sessaoUltimaResposta);
  } catch {
    // storage bloqueado — nada a avisar
  }
}

/** Guarda o motivo para a tela de login mostrar depois do reload. Sem storage, o login só não diz o motivo. */
export function guardarAvisoDoLogin(texto: string): void {
  try {
    sessionStorage.setItem(storageKeys.avisoLogin, texto);
  } catch {
    // storage bloqueado (janela privada, dados do site apagados) — segue sem o motivo
  }
}

export function lerAvisoDoLogin(): string | null {
  try {
    return sessionStorage.getItem(storageKeys.avisoLogin);
  } catch {
    return null;
  }
}

export function apagarAvisoDoLogin(): void {
  try {
    sessionStorage.removeItem(storageKeys.avisoLogin);
  } catch {
    // storage bloqueado — nada a apagar
  }
}
