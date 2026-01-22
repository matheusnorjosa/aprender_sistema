/**
 * useGoogleGuard - §4 Epic #459
 *
 * Hook for Google OAuth connection checks before GCal operations.
 * Deduplicates Modal.confirm patterns found in PreAgendaPage.jsx and others.
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
 * @typedef {Object} GoogleStatus
 * @property {boolean} connected - Whether Google account is connected
 * @property {string} [email] - Connected Google email
 */

/**
 * @typedef {Object} UseGoogleGuardOptions
 * @property {GoogleStatus|null} googleStatus - Google connection status from useGoogleIntegration
 * @property {string} returnTo - Return URL after OAuth flow (e.g., '/pre-agenda')
 */

/**
 * @typedef {Object} UseGoogleGuardReturn
 * @property {(actionDescription: string) => boolean} requireGoogleConnection - Check if connected, show modal if not
 * @property {(error: Error) => boolean} handleGoogleError - Handle 403 google_not_connected errors
 * @property {boolean} isConnected - Current connection status
 */

/**
 * Hook for Google OAuth connection checks.
 *
 * @param {UseGoogleGuardOptions} options
 * @returns {UseGoogleGuardReturn}
 */
export default function useGoogleGuard({ googleStatus, returnTo }) {
  const isConnected = googleStatus?.connected ?? false;

  /**
   * Shows the "Connect Google" modal and redirects to OAuth flow.
   * @param {string} actionDescription - What the user was trying to do (e.g., "publicar eventos")
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
   * @param {string} actionDescription - What the user is trying to do
   * @returns {boolean} true if connected (proceed), false if not (modal shown)
   *
   * @example
   * const handlePublish = (id) => {
   *   if (!requireGoogleConnection('publicar eventos')) return;
   *   // ... rest of publish logic
   * };
   */
  const requireGoogleConnection = useCallback(
    (actionDescription = 'realizar esta ação') => {
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
   * @param {Error} error - Axios error or similar
   * @returns {boolean} true if error was handled (Google not connected), false otherwise
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
    (error) => {
      const data = error.response?.data;
      const status = error.response?.status;

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
