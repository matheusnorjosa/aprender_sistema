/**
 * FormadoresPicker - Seleção de Formadores para Nova Solicitação
 *
 * Componente específico para o wizard de nova solicitação.
 * Permite selecionar múltiplos formadores.
 */

import { useState } from 'react';
import { Tag, AutoComplete, Spin } from 'antd';
import { lookupUsuarios } from '../api/lookup';
import logger from '../utils/logger';
import type { ID } from '../types';

/**
 * Formador item interface
 */
export interface FormadorItem {
  id: ID;
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
    label: string;
  };
}

/**
 * FormadoresPicker props interface
 */
export interface FormadoresPickerProps {
  value?: FormadorItem[];
  onChange?: (value: FormadorItem[]) => void;
}

export default function FormadoresPicker({ value = [], onChange }: FormadoresPickerProps): JSX.Element {
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
      const results = await lookupUsuarios(query || '', 'Formador');
      setOptions(
        results.map(item => ({
          value: String(item.id),
          label: item.label,
          data: item,
        }))
      );
    } catch (error) {
      logger.error('Erro ao buscar formadores:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = (_selectedValue: string, option: UserOption): void => {
    const newFormador: FormadorItem = {
      id: option.data.id,
      label: option.data.label,
      name: option.data.label, // Alias para compatibilidade
    };

    // Verificar se já existe (by ID only — SEC-ENUM-01)
    const exists = value.some(f => f.id === newFormador.id);
    if (exists) {
      return;
    }

    if (onChange) {
      onChange([...value, newFormador]);
    }

    // Limpar busca mas manter as opções para próxima seleção
    setSearch('');
  };

  const handleRemove = (id: ID): void => {
    if (onChange) {
      onChange(value.filter((f) => f.id !== id));
    }
  };

  return (
    <div>
      {/* Tags dos formadores selecionados */}
      {value.length > 0 && (
        <ul style={{ display: 'flex', flexWrap: 'wrap', gap: 8, listStyle: 'none', padding: 0, margin: '0 0 8px 0' }} aria-label="Formadores selecionados">
          {value.map((formador) => (
            <li key={formador.id}>
              <Tag
                closable
                onClose={() => handleRemove(formador.id)}
                color="blue"
              >
                {formador.label || formador.name}
              </Tag>
            </li>
          ))}
        </ul>
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
