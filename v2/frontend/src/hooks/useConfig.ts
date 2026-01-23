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

/**
 * System configuration object
 */
export interface SystemConfig {
  buffer_deslocamento_minutos?: number;
  session_cookie_age?: number;
  batch_size?: number;
  [key: string]: unknown;
}

/**
 * Validation errors from backend
 */
type ValidationErrors = Record<string, string | string[]>;

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

  /**
   * Load config from server
   */
  const loadConfig = async (): Promise<void> => {
    setLoading(true);
    try {
      const res = await fetch('/api/config/', {
        credentials: 'include'
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data: SystemConfig = await res.json();
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
      const res = await fetch('/api/config/', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(values)
      });

      if (!res.ok) {
        const errors: ValidationErrors = await res.json();
        logger.error('useConfig saveConfig validation errors:', errors);

        // Display validation errors
        if (typeof errors === 'object' && !Array.isArray(errors)) {
          const errorMessages = Object.entries(errors)
            .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join('\n');
          message.error(`Erro de validação:\n${errorMessages}`, 5);
        } else {
          message.error('Erro ao salvar configurações');
        }

        return false;
      }

      const data: SystemConfig = await res.json();
      setConfig(data);
      message.success('Configurações salvas com sucesso!');
      return true;
    } catch (error) {
      message.error('Erro ao salvar configurações');
      logger.error('useConfig saveConfig error:', error);
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
