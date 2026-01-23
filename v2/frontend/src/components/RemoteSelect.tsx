/**
 * RemoteSelect Component - PR 8/N
 *
 * Select com busca remota, debounce e loading.
 * Reutilizável para municípios, projetos, coordenadores, formadores, etc.
 */

import { Select, Spin } from 'antd';
import { useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import logger from '../utils/logger';
import { TIMING } from '../constants';
import type { ID } from '../types';

const { Option } = Select;

/**
 * Option item interface
 */
export interface OptionItem {
  id: ID;
  [key: string]: unknown;
}

/**
 * Fetch options params
 */
export interface FetchOptionsParams {
  search: string;
  [key: string]: unknown;
}

/**
 * RemoteSelect props interface
 */
export interface RemoteSelectProps<T extends OptionItem = OptionItem> {
  fetchOptions: (params: FetchOptionsParams) => Promise<T[]>;
  renderLabel: (item: T) => ReactNode;
  placeholder?: string;
  disabled?: boolean;
  mode?: 'multiple' | 'tags';
  value?: ID | ID[];
  onChange?: (value: ID | ID[] | undefined) => void;
  debounceMs?: number;
  extraParams?: Record<string, unknown>;
  [key: string]: unknown;
}

export default function RemoteSelect<T extends OptionItem = OptionItem>({
  fetchOptions,
  renderLabel,
  placeholder = 'Buscar...',
  disabled = false,
  mode,
  value,
  onChange,
  debounceMs = TIMING.DEBOUNCE_SEARCH_MS,
  extraParams = {},
  ...restProps
}: RemoteSelectProps<T>): JSX.Element {
  const [options, setOptions] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * Carrega opções do backend com debounce.
   */
  const loadOptions = useCallback(
    async (search: string = ''): Promise<void> => {
      setLoading(true);
      try {
        const results = await fetchOptions({ search, ...extraParams });
        setOptions(results || []);
      } catch (error) {
        logger.error('Erro ao carregar opções:', error);
        setOptions([]);
      } finally {
        setLoading(false);
      }
    },
    [fetchOptions, extraParams]
  );

  /**
   * Handler de busca com debounce.
   */
  const handleSearch = (value: string): void => {
    setSearchValue(value);

    // Limpar timer anterior
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Agendar nova busca
    debounceTimerRef.current = setTimeout(() => {
      loadOptions(value);
    }, debounceMs);
  };

  /**
   * Carrega opções iniciais ao montar ou quando extraParams muda.
   */
  useEffect(() => {
    if (!disabled) {
      loadOptions('');
    }
    // Cleanup do timer ao desmontar
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disabled, JSON.stringify(extraParams)]);

  return (
    <Select
      showSearch
      placeholder={placeholder}
      disabled={disabled}
      mode={mode}
      value={value}
      onChange={onChange}
      onSearch={handleSearch}
      searchValue={searchValue}
      filterOption={false} // Filtro server-side
      loading={loading}
      notFoundContent={loading ? <Spin size="small" /> : 'Nenhum resultado'}
      {...restProps}
    >
      {options.map((item) => (
        <Option key={item.id} value={item.id}>
          {renderLabel(item)}
        </Option>
      ))}
    </Select>
  );
}
