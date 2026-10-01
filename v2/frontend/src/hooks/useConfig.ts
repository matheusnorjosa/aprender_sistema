/**
 * useConfig Hook — Manage System Configuration
 *
 * Issue #187: UI para Configurações do Sistema
 *
 * Features:
 * - Load config from GET /api/config/
 * - Save config via PUT /api/config/
 * - Loading state management
 * - Error handling with Ant Design message
 *
 * Usage:
 *   const { config, loading, saveConfig, reload } = useConfig();
 *
 *   // Display config in form
 *   if (loading) return <Spin />;
 *
 *   // Save changes
 *   const success = await saveConfig(newValues);
 *   if (success) {
 *     // Handle success
 *   }
 */

import { useState, useEffect } from 'react';
import { message } from 'antd';
import logger from '../utils/logger';
import {
  getSystemConfig,
  updateSystemConfig,
  type ConfigValidationErrors,
  type SystemConfig,
} from '../api/systemConfig';

/**
 * Return type for useConfig hook
 */
export interface UseConfigReturn {
  config: SystemConfig | null;
  loading: boolean;
  /** Motivo da falha ao carregar; null quando carregou. */
  loadError: string | null;
  saveConfig: (values: SystemConfig) => Promise<boolean>;
  reload: () => Promise<void>;
}

/**
 * Hook to manage system configuration
 */
export function useConfig(): UseConfigReturn {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  type ApiClientError = Error & {
    response?: {
      status?: number;
      data?: unknown;
    };
  };

  /**
   * Load config from server
   */
  const loadConfig = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await getSystemConfig();
      setConfig(data);
      setLoadError(null);
    } catch (error) {
      message.error('Erro ao carregar configurações');
      logger.error('useConfig loadConfig error:', error);
      setLoadError(error instanceof Error && error.message ? error.message : 'Erro inesperado do servidor.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Save config to server
   *
   * @param values - Config values to save
   * @returns True if save succeeded, false otherwise
   */
  const saveConfig = async (values: SystemConfig): Promise<boolean> => {
    try {
      const data = await updateSystemConfig(values);
      setConfig(data);
      message.success('Configurações salvas com sucesso!');
      return true;
    } catch (error) {
      const apiError = error as ApiClientError;
      const validationData = apiError.response?.data;
      logger.error('useConfig saveConfig error:', error);

      // Erros por campo só no 400 (o PUT devolve serializer.errors). O resto mostra o motivo
      // real: sem rede, permissão, 5xx (auditoria UX 30/09, rodada 4; antes o corpo
      // `{code, detail}` virava "Erro de validação" e a falha de rede não dizia nada).
      if (apiError.response?.status === 400 && validationData && typeof validationData === 'object' && !Array.isArray(validationData)) {
        const errors = validationData as ConfigValidationErrors;
        const errorMessages = Object.entries(errors)
            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join('\n');
        message.error(`Erro de validação:\n${errorMessages}`, 5);
      } else {
        const motivo = error instanceof Error && error.message ? error.message : 'Erro inesperado do servidor.';
        message.error(`Não foi possível salvar: ${motivo}`);
      }
      return false;
    }
  };

  // Load config on mount
  useEffect(() => {
    void loadConfig();
  }, []);

  return {
    config,
    loading,
    loadError,
    saveConfig,
    reload: loadConfig
  };
}
