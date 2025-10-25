/**
 * PR16: ComboBox com Autocomplete
 *
 * Componente reutilizável para autocomplete de municípios, projetos, tipos de evento
 * Trabalha com objetos {id, label} e fornece busca via lookup API
 */

import { useState, useEffect } from 'react';
import { AutoComplete, Spin } from 'antd';

export default function ComboBox({
  value = null,
  onChange,
  lookupFunction,
  placeholder = 'Digite para buscar...',
  disabled = false,
}) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchValue, setSearchValue] = useState('');

  // Carregar opções iniciais
  useEffect(() => {
    const loadInitial = async () => {
      try {
        setLoading(true);
        const results = await lookupFunction('');
        console.log(`ComboBox: Carregadas ${results.length} opções iniciais`, results.slice(0, 3));
        setOptions(results.map(item => ({
          value: String(item.id),
          label: item.label,
          data: item
        })));
      } catch (error) {
        console.error('Erro ao carregar opções iniciais:', error);
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

  const handleSearch = async (query) => {
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
        console.error('Erro ao buscar:', error);
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
      console.error('Erro ao buscar:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (value, option) => {
    if (onChange) {
      onChange(option.data);
    }
  };

  const handleChange = (text) => {
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
