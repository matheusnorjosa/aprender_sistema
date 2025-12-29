/**
 * CoordenadoresPicker - Seleção de Coordenadores Acompanhantes
 *
 * Componente específico para o wizard de nova solicitação.
 * Permite selecionar múltiplos coordenadores acompanhantes.
 */

import { useState } from 'react';
import { Space, Tag, AutoComplete, Spin } from 'antd';
import { CloseCircleOutlined } from '@ant-design/icons';
import { lookupUsuarios } from '../api/lookup';
import logger from '../utils/logger';

export default function CoordenadoresPicker({ value = [], onChange }) {
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
      const results = await lookupUsuarios(query || '', 'Coordenador');
      setOptions(
        results.map(item => ({
          value: item.id,
          label: item.label,
          data: item,
        }))
      );
    } catch (error) {
      logger.error('Erro ao buscar coordenadores:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = (selectedValue, option) => {
    const newCoordenador = {
      id: option.data.id,
      email: option.data.email,
      label: option.data.label,
      name: option.data.label, // Alias para compatibilidade
    };

    // Verificar se já existe
    const exists = value.some(c => c.id === newCoordenador.id || c.email === newCoordenador.email);
    if (exists) {
      return;
    }

    if (onChange) {
      onChange([...value, newCoordenador]);
    }

    // Limpar busca mas manter as opções para próxima seleção
    setSearch('');
  };

  const handleRemove = (id) => {
    if (onChange) {
      onChange(value.filter((c) => c.id !== id));
    }
  };

  return (
    <div>
      {/* Tags dos coordenadores selecionados */}
      {value.length > 0 && (
        <Space wrap style={{ marginBottom: 8 }}>
          {value.map((coord) => (
            <Tag
              key={coord.id}
              closable
              onClose={() => handleRemove(coord.id)}
              color="green"
            >
              {coord.label || coord.name}
            </Tag>
          ))}
        </Space>
      )}

      {/* Autocomplete para adicionar coordenadores */}
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
