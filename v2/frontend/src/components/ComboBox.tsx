/**
 * PR16: ComboBox com Autocomplete
 *
 * Componente reutilizável para autocomplete de municípios, projetos, tipos de evento
 * Trabalha com objetos {id, label} e fornece busca via lookup API
 */

import { useState, useEffect } from 'react';
import { AutoComplete, Spin } from 'antd';
import logger from '../utils/logger';
import type { ID } from '../types';

/**
 * Lookup item interface
 */
export interface LookupItem {
  id: ID;
  label: string;
  [key: string]: unknown;
}

/**
 * AutoComplete option interface
 */
interface AutoCompleteOption {
  value: string;
  label: string;
  data: LookupItem;
}

/**
 * ComboBox props interface
 */
export interface ComboBoxProps {
  value?: LookupItem | null;
  onChange?: (item: LookupItem | null) => void;
  lookupFunction: (query: string) => Promise<LookupItem[]>;
  placeholder?: string;
  disabled?: boolean;
}

export default function ComboBox({
  value = null,
  onChange,
  lookupFunction,
  placeholder = 'Digite para buscar...',
  disabled = false,
}: ComboBoxProps): JSX.Element {
  const [options, setOptions] = useState<AutoCompleteOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchValue, setSearchValue] = useState('');

  // Carregar opções iniciais
  useEffect(() => {
    const loadInitial = async (): Promise<void> => {
      try {
        setLoading(true);
        const results = await lookupFunction('');
        setOptions(results.map(item => ({
          value: String(item.id),
          label: item.label,
          data: item
        })));
      } catch (error) {
        logger.error('Erro ao carregar opções iniciais:', error);
      } finally {
        setLoading(false);
      }
    };
    loadInitial();
  }, [lookupFunction]);

  // Atualizar searchValue quando value muda
  useEffect(() => {
    if (value && value.label) {
      setSearchValue(value.label);
    } else {
      setSearchValue('');
    }
  }, [value]);

  const handleSearch = async (query: string): Promise<void> => {
    setSearchValue(query);

    if (!query || query.length < 2) {
      // Recarregar opções iniciais
      try {
        setLoading(true);
        const results = await lookupFunction('');
        setOptions(results.map(item => ({
          value: String(item.id),
          label: item.label,
          data: item
        })));
      } catch (error) {
        logger.error('Erro ao buscar:', error);
      } finally {
        setLoading(false);
      }
      return;
    }

    try {
      setLoading(true);
      const results = await lookupFunction(query);
      setOptions(results.map(item => ({
        value: String(item.id),
        label: item.label,
        data: item
      })));
    } catch (error) {
      logger.error('Erro ao buscar:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (_value: string, option: AutoCompleteOption): void => {
    if (onChange) {
      onChange(option.data);
    }
  };

  const handleChange = (text: string): void => {
    setSearchValue(text);

    // Se o texto está vazio, limpar seleção
    if (!text && onChange) {
      onChange(null);
    }
  };

  return (
    <AutoComplete
      value={searchValue}
      options={options}
      onSearch={handleSearch}
      onSelect={handleSelect}
      onChange={handleChange}
      placeholder={placeholder}
      disabled={disabled}
      style={{ width: '100%' }}
      notFoundContent={loading ? <Spin size="small" /> : 'Nenhum resultado encontrado'}
      allowClear
    />
  );
}
