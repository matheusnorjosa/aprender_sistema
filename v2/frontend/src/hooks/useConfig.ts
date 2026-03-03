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
  saveConfig: (values: SystemConfig) => Promise<boolean>;
  reload: () => Promise<void>;
}

/**
 * Hook to manage system configuration
 */
export function useConfig(): UseConfigReturn {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

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
    } catch (error) {
      message.error('Erro ao carregar configurações');
      logger.error('useConfig loadConfig error:', error);
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

      // Display backend validation errors when available.
      if (validationData && typeof validationData === 'object' && !Array.isArray(validationData)) {
        const errors = validationData as ConfigValidationErrors;
        const errorMessages = Object.entries(errors)
            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join('\n');
        message.error(`Erro de validação:\n${errorMessages}`, 5);
      } else {
        message.error('Erro ao salvar configurações');
      }
      return false;
    }
  };

  // Load config on mount
  useEffect(() => {
    loadConfig();
  }, []);

  return {
    config,
    loading,
    saveConfig,
    reload: loadConfig
  };
}
