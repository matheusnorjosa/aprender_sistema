/**
 * FormadoresPicker - Seleção de Formadores para Nova Solicitação
 *
 * Componente específico para o wizard de nova solicitação.
 * Permite selecionar múltiplos formadores.
 */

import { useState } from 'react';
import { Space, Tag, AutoComplete, Spin } from 'antd';
import { lookupUsuarios } from '../api/lookup';

export default function FormadoresPicker({ value = [], onChange }) {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  const handleSearch = async (query) => {
    setSearch(query);

    // Permitir busca vazia (mostra lista inicial) ou com 2+ caracteres
    if (query && query.length > 0 && query.length < 2) {
      setOptions([]);
      return;
    }

    try {
      setLoading(true);
      const results = await lookupUsuarios(query || '', 'Formador');
      setOptions(
        results.map(item => ({
          value: item.id,
          label: item.label,
          data: item,
        }))
      );
    } catch (error) {
      console.error('Erro ao buscar formadores:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = (selectedValue, option) => {
    const newFormador = {
      id: option.data.id,
      email: option.data.email,
      label: option.data.label,
      name: option.data.label, // Alias para compatibilidade
    };

    // Verificar se já existe
    const exists = value.some(f => f.id === newFormador.id || f.email === newFormador.email);
    if (exists) {
      return;
    }

    if (onChange) {
      onChange([...value, newFormador]);
    }

    // Limpar busca mas manter as opções para próxima seleção
    setSearch('');
  };

  const handleRemove = (id) => {
    if (onChange) {
      onChange(value.filter((f) => f.id !== id));
    }
  };

  return (
    <div>
      {/* Tags dos formadores selecionados */}
      {value.length > 0 && (
        <Space wrap style={{ marginBottom: 8 }}>
          {value.map((formador) => (
            <Tag
              key={formador.id}
              closable
              onClose={() => handleRemove(formador.id)}
              color="blue"
            >
              {formador.label || formador.name}
            </Tag>
          ))}
        </Space>
      )}

      {/* Autocomplete para adicionar formadores */}
      <AutoComplete
        value={search}
        options={options}
        onSearch={handleSearch}
        onFocus={() => {
          // Carregar lista inicial ao focar no campo (se ainda não carregou)
          if (options.length === 0 && !loading) {
            handleSearch('');
          }
        }}
        onSelect={handleAdd}
        onChange={setSearch}
        placeholder="Clique para ver lista ou digite para buscar..."
        style={{ width: '100%' }}
        notFoundContent={loading ? <Spin size="small" /> : null}
      />
    </div>
  );
}
