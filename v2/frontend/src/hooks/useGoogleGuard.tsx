/**
 * useGoogleGuard - §4 Epic #459
 *
 * Hook for Google OAuth connection checks before GCal operations.
 * Deduplicates Modal.confirm patterns found in PreAgendaPage.tsx and others.
 *
 * Usage:
 *   const { requireGoogleConnection, handleGoogleError } = useGoogleGuard({
 *     googleStatus,
 *     returnTo: '/pre-agenda',
 *   });
 *
 *   // Before an action:
 *   if (!requireGoogleConnection('publicar eventos')) return;
 *
 *   // In catch block:
 *   if (handleGoogleError(error)) return;
 */

import { Modal } from 'antd';
import { useCallback } from 'react';

/**
 * Google connection status interface
 */
export interface GoogleStatus {
  connected: boolean;
  email?: string;
}

/**
 * Hook options interface
 */
export interface UseGoogleGuardOptions {
  googleStatus: GoogleStatus | null;
  returnTo: string;
}

/**
 * Hook return interface
 */
export interface UseGoogleGuardReturn {
  requireGoogleConnection: (actionDescription?: string) => boolean;
  handleGoogleError: (error: unknown) => boolean;
  isConnected: boolean;
}

/**
 * API error with response interface
 */
interface ApiError {
  response?: {
    status?: number;
    data?: {
      code?: string;
      detail?: string;
    };
  };
}

/**
 * Hook for Google OAuth connection checks.
 *
 * @param options - Hook options
 * @returns Hook return object
 */
export default function useGoogleGuard({ googleStatus, returnTo }: UseGoogleGuardOptions): UseGoogleGuardReturn {
  const isConnected = googleStatus?.connected ?? false;

  /**
   * Shows the "Connect Google" modal and redirects to OAuth flow.
   * @param actionDescription - What the user was trying to do (e.g., "publicar eventos")
   */
  const showConnectModal = useCallback(
    (actionDescription = 'realizar esta ação') => {
      Modal.confirm({
        title: 'Conectar conta Google',
        content: (
          <div>
            <p>
              Para {actionDescription} no Google Calendar, você precisa conectar
              sua conta corporativa do Google.
            </p>
          </div>
        ),
        okText: 'Conectar agora',
        okType: 'primary',
        cancelText: 'Cancelar',
        onOk: () => {
          window.location.href = `/api/oauth/google/start/?return_to=${returnTo}`;
        },
      });
    },
    [returnTo]
  );

  /**
   * Check if Google is connected. If not, shows connection modal.
   *
   * @param actionDescription - What the user is trying to do
   * @returns true if connected (proceed), false if not (modal shown)
   *
   * @example
   * const handlePublish = (id) => {
   *   if (!requireGoogleConnection('publicar eventos')) return;
   *   // ... rest of publish logic
   * };
   */
  const requireGoogleConnection = useCallback(
    (actionDescription = 'realizar esta ação'): boolean => {
      if (googleStatus && !googleStatus.connected) {
        showConnectModal(actionDescription);
        return false;
      }
      return true;
    },
    [googleStatus, showConnectModal]
  );

  /**
   * Handle API errors. If it's a 403 with code='google_not_connected', shows modal.
   *
   * @param error - Axios error or similar
   * @returns true if error was handled (Google not connected), false otherwise
   *
   * @example
   * try {
   *   await publishSolicitacao(id);
   * } catch (error) {
   *   if (handleGoogleError(error)) return;
   *   message.error('Erro ao publicar: ' + error.message);
   * }
   */
  const handleGoogleError = useCallback(
    (error: unknown): boolean => {
      const apiError = error as ApiError;
      const data = apiError.response?.data;
      const status = apiError.response?.status;

      if (status === 403 && data?.code === 'google_not_connected') {
        Modal.confirm({
          title: 'Conectar conta Google',
          content: (
            <div>
              <p>
                {data?.detail ||
                  'Conecte sua conta Google para realizar esta operação.'}
              </p>
            </div>
          ),
          okText: 'Conectar agora',
          okType: 'primary',
          cancelText: 'Cancelar',
          onOk: () => {
            window.location.href = `/api/oauth/google/start/?return_to=${returnTo}`;
          },
        });
        return true;
      }

      return false;
    },
    [returnTo]
  );

  return {
    requireGoogleConnection,
    handleGoogleError,
    isConnected,
  };
}
