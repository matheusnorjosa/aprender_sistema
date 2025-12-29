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
 * Hook to manage system configuration
 *
 * @returns {Object} Config state and actions
 * @returns {Object|null} config - Current config object or null if loading
 * @returns {boolean} loading - True while fetching config
 * @returns {Function} saveConfig - Async function to save config (returns Promise<boolean>)
 * @returns {Function} reload - Async function to reload config from server
 */
export function useConfig() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  /**
   * Load config from server
   */
  const loadConfig = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/config/', {
        credentials: 'include'
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
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
   * @param {Object} values - Config values to save
   * @returns {Promise<boolean>} True if save succeeded, false otherwise
   */
  const saveConfig = async (values) => {
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
        const errors = await res.json();
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

      const data = await res.json();
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
