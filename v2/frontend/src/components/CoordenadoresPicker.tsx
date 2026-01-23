/**
 * CoordenadoresPicker - Seleção de Coordenadores Acompanhantes
 *
 * Componente específico para o wizard de nova solicitação.
 * Permite selecionar múltiplos coordenadores acompanhantes.
 */

import { useState } from 'react';
import { Space, Tag, AutoComplete, Spin } from 'antd';
import { lookupUsuarios } from '../api/lookup';
import logger from '../utils/logger';
import type { ID } from '../types';

/**
 * Coordenador item interface
 */
export interface CoordenadorItem {
  id: ID;
  email: string;
  label: string;
  name?: string;
}

/**
 * AutoComplete option interface
 */
interface UserOption {
  value: string;
  label: string;
  data: {
    id: ID;
    email: string;
    label: string;
  };
}

/**
 * CoordenadoresPicker props interface
 */
export interface CoordenadoresPickerProps {
  value?: CoordenadorItem[];
  onChange?: (value: CoordenadorItem[]) => void;
}

export default function CoordenadoresPicker({ value = [], onChange }: CoordenadoresPickerProps): JSX.Element {
  const [options, setOptions] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  const handleSearch = async (query: string): Promise<void> => {
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
          value: String(item.id),
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

  const handleAdd = (_selectedValue: string, option: UserOption): void => {
    const newCoordenador: CoordenadorItem = {
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

  const handleRemove = (id: ID): void => {
    if (onChange) {
      onChange(value.filter((c) => c.id !== id));
    }
  };

  return (
    <div>
      {/* Tags dos coordenadores selecionados */}
      {value.length > 0 && (
        <Space wrap className="mb-2">
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
