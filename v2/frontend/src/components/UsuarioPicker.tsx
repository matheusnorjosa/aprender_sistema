/**
 * UsuarioPicker - Seleção múltipla de usuários por papel (autocomplete).
 *
 * Implementação compartilhada de FormadoresPicker/CoordenadoresPicker, que eram
 * ~95% idênticos. Parametrizado por papel do lookup, cor da Tag e aria-label;
 * cada picker de domínio vira um wrapper fino sobre este.
 */

import { useState, type JSX } from 'react';
import { Tag, AutoComplete, Spin } from 'antd';
import { lookupUsuarios } from '../api/lookup';
import logger from '../utils/logger';
import type { ID } from '../types';

/** Item de usuário selecionado. */
export interface UsuarioItem {
  id: ID;
  label: string;
  name?: string;
}

/** Opção do AutoComplete. */
interface UserOption {
  value: string;
  label: string;
  data: {
    id: ID;
    label: string;
  };
}

export interface UsuarioPickerProps {
  value?: UsuarioItem[];
  onChange?: (value: UsuarioItem[]) => void;
  /** Papel para filtrar o lookup (ex.: 'Formador', 'Coordenador'). */
  role: string;
  /** Cor da Tag dos selecionados. */
  tagColor?: string;
  /** aria-label da lista de selecionados. */
  ariaLabel?: string;
}

export default function UsuarioPicker({
  value = [],
  onChange,
  role,
  tagColor = 'blue',
  ariaLabel,
}: UsuarioPickerProps): JSX.Element {
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
      const results = await lookupUsuarios(query || '', role);
      setOptions(
        results.map(item => ({
          value: String(item.id),
          label: item.label,
          data: item,
        }))
      );
    } catch (error) {
      logger.error(`Erro ao buscar ${role}:`, error);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = (_selectedValue: string, option: UserOption): void => {
    const novo: UsuarioItem = {
      id: option.data.id,
      label: option.data.label,
      name: option.data.label, // Alias para compatibilidade
    };

    // Verificar se já existe (by ID only — SEC-ENUM-01)
    const exists = value.some(u => u.id === novo.id);
    if (exists) {
      return;
    }

    if (onChange) {
      onChange([...value, novo]);
    }

    // Limpar busca mas manter as opções para próxima seleção
    setSearch('');
  };

  const handleRemove = (id: ID): void => {
    if (onChange) {
      onChange(value.filter((u) => u.id !== id));
    }
  };

  return (
    <div>
      {/* Tags dos usuários selecionados */}
      {value.length > 0 && (
        <ul style={{ display: 'flex', flexWrap: 'wrap', gap: 8, listStyle: 'none', padding: 0, margin: '0 0 8px 0' }} aria-label={ariaLabel}>
          {value.map((usuario) => (
            <li key={usuario.id}>
              <Tag
                closable
                onClose={() => handleRemove(usuario.id)}
                color={tagColor}
              >
                {usuario.label || usuario.name}
              </Tag>
            </li>
          ))}
        </ul>
      )}

      {/* Autocomplete para adicionar */}
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
