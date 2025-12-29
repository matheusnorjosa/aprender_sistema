/**
 * RemoteSelect Component - PR 8/N
 *
 * Select com busca remota, debounce e loading.
 * Reutilizável para municípios, projetos, coordenadores, formadores, etc.
 */

import { Select, Spin } from 'antd';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import logger from '../utils/logger';

const { Option } = Select;

/**
 * @param {object} props
 * @param {Function} props.fetchOptions - Função async que recebe {search} e retorna Promise<Array>
 * @param {Function} props.renderLabel - Função que recebe item e retorna string do label
 * @param {string} props.placeholder - Placeholder do select
 * @param {boolean} props.disabled - Se o select está desabilitado
 * @param {boolean} props.mode - Mode do select (undefined, 'multiple', 'tags')
 * @param {any} props.value - Valor selecionado
 * @param {Function} props.onChange - Callback quando o valor muda
 * @param {number} props.debounceMs - Delay do debounce em ms (default: 400)
 * @param {object} props.extraParams - Parâmetros extras para fetchOptions (ex: {municipioId})
 */
export default function RemoteSelect({
  fetchOptions,
  renderLabel,
  placeholder = 'Buscar...',
  disabled = false,
  mode,
  value,
  onChange,
  debounceMs = 400,
  extraParams = {},
  ...restProps
}) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const debounceTimerRef = useRef(null);

  /**
   * Carrega opções do backend com debounce.
   */
  const loadOptions = useCallback(
    async (search = '') => {
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
  const handleSearch = (value) => {
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
