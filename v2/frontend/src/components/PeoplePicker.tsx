/**
 * PR16: PeoplePicker
 *
 * Componente para selecionar formadores e coordenadores acompanhantes
 * Usa lookup de usuários e armazena como array de {id, email, label}
 */

import { useState } from 'react';
import { Card, Space, Tag, AutoComplete, Spin } from 'antd';
import { lookupUsuarios } from '../api/lookup';
import logger from '../utils/logger';
import type { ID } from '../types';

/**
 * Person item interface
 */
export interface PersonItem {
  id: ID;
  email: string;
  label: string;
}

/**
 * PeoplePicker value interface
 */
export interface PeoplePickerValue {
  formadores: PersonItem[];
  coordAcompanha: PersonItem[];
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
 * PeoplePicker props interface
 */
export interface PeoplePickerProps {
  value?: PeoplePickerValue;
  onChange?: (value: PeoplePickerValue) => void;
}

export default function PeoplePicker({
  value = { formadores: [], coordAcompanha: [] },
  onChange,
}: PeoplePickerProps): JSX.Element {
  const [formadoresOptions, setFormadoresOptions] = useState<UserOption[]>([]);
  const [coordOptions, setCoordOptions] = useState<UserOption[]>([]);
  const [loadingFormadores, setLoadingFormadores] = useState(false);
  const [loadingCoord, setLoadingCoord] = useState(false);
  const [formadorSearch, setFormadorSearch] = useState('');
  const [coordSearch, setCoordSearch] = useState('');

  const handleSearchFormadores = async (query: string): Promise<void> => {
    setFormadorSearch(query);

    // Permitir busca vazia (mostra lista inicial) ou com 2+ caracteres
    if (query && query.length > 0 && query.length < 2) {
      setFormadoresOptions([]);
      return;
    }

    try {
      setLoadingFormadores(true);
      const results = await lookupUsuarios(query || '', 'Formador');
      setFormadoresOptions(
        results.map(item => ({
          value: String(item.id),
          label: item.label,
          data: item,
        }))
      );
    } catch (error) {
      logger.error('Erro ao buscar formadores:', error);
    } finally {
      setLoadingFormadores(false);
    }
  };

  const handleSearchCoord = async (query: string): Promise<void> => {
    setCoordSearch(query);

    // Permitir busca vazia (mostra lista inicial) ou com 2+ caracteres
    if (query && query.length > 0 && query.length < 2) {
      setCoordOptions([]);
      return;
    }

    try {
      setLoadingCoord(true);
      const results = await lookupUsuarios(query || '', 'Coordenador');
      setCoordOptions(
        results.map(item => ({
          value: String(item.id),
          label: item.label,
          data: item,
        }))
      );
    } catch (error) {
      logger.error('Erro ao buscar coordenadores:', error);
    } finally {
      setLoadingCoord(false);
    }
  };

  const handleAddFormador = (_selectedValue: string, option: UserOption): void => {
    const newFormador: PersonItem = {
      id: option.data.id,
      email: option.data.email,
      label: option.data.label,
    };

    // Verificar se já existe
    const exists = value.formadores.some(f => f.id === newFormador.id || f.email === newFormador.email);
    if (exists) {
      return;
    }

    const updated: PeoplePickerValue = {
      ...value,
      formadores: [...value.formadores, newFormador],
    };

    if (onChange) {
      onChange(updated);
    }

    // Limpar busca mas manter as opções para próxima seleção
    setFormadorSearch('');
    // Não limpar formadoresOptions para permitir múltiplas seleções
  };

  const handleAddCoord = (_selectedValue: string, option: UserOption): void => {
    const newCoord: PersonItem = {
      id: option.data.id,
      email: option.data.email,
      label: option.data.label,
    };

    // Verificar se já existe
    const exists = value.coordAcompanha.some(c => c.id === newCoord.id || c.email === newCoord.email);
    if (exists) {
      return;
    }

    const updated: PeoplePickerValue = {
      ...value,
      coordAcompanha: [...value.coordAcompanha, newCoord],
    };

    if (onChange) {
      onChange(updated);
    }

    // Limpar busca mas manter as opções para próxima seleção
    setCoordSearch('');
    // Não limpar coordOptions para permitir múltiplas seleções
  };

  const handleRemoveFormador = (id: ID): void => {
    const updated: PeoplePickerValue = {
      ...value,
      formadores: value.formadores.filter((f) => f.id !== id),
    };

    if (onChange) {
      onChange(updated);
    }
  };

  const handleRemoveCoord = (id: ID): void => {
    const updated: PeoplePickerValue = {
      ...value,
      coordAcompanha: value.coordAcompanha.filter((c) => c.id !== id),
    };

    if (onChange) {
      onChange(updated);
    }
  };

  return (
    <Card title="Participantes" size="small">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Formadores */}
        <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
          <legend className="mb-2 font-medium">Formadores:</legend>
          <ul style={{ display: 'flex', flexWrap: 'wrap', gap: 8, listStyle: 'none', padding: 0, margin: 0 }} aria-label="Formadores selecionados">
            {value.formadores.map((formador) => (
              <li key={formador.id}>
                <Tag
                  closable
                  onClose={() => handleRemoveFormador(formador.id)}
                  color="blue"
                >
                  {formador.label || formador.email}
                </Tag>
              </li>
            ))}
          </ul>
          <div className="mt-2">
            <AutoComplete
              value={formadorSearch}
              options={formadoresOptions}
              onSearch={handleSearchFormadores}
              onFocus={() => {
                // Carregar lista inicial ao focar no campo (se ainda não carregou)
                if (formadoresOptions.length === 0 && !loadingFormadores) {
                  handleSearchFormadores('');
                }
              }}
              onSelect={handleAddFormador}
              onChange={setFormadorSearch}
              placeholder="Clique para ver lista ou digite para buscar..."
              style={{ width: '100%' }}
              notFoundContent={loadingFormadores ? <Spin size="small" /> : null}
            />
          </div>
        </fieldset>

        {/* Coordenadores Acompanhantes */}
        <fieldset style={{ border: 'none', padding: 0, margin: 0 }}>
          <legend className="mb-2 font-medium">Coordenadores Acompanhantes:</legend>
          <ul style={{ display: 'flex', flexWrap: 'wrap', gap: 8, listStyle: 'none', padding: 0, margin: 0 }} aria-label="Coordenadores selecionados">
            {value.coordAcompanha.map((coord) => (
              <li key={coord.id}>
                <Tag
                  closable
                  onClose={() => handleRemoveCoord(coord.id)}
                  color="green"
                >
                  {coord.label || coord.email}
                </Tag>
              </li>
            ))}
          </ul>
          <div className="mt-2">
            <AutoComplete
              value={coordSearch}
              options={coordOptions}
              onSearch={handleSearchCoord}
              onFocus={() => {
                // Carregar lista inicial ao focar no campo (se ainda não carregou)
                if (coordOptions.length === 0 && !loadingCoord) {
                  handleSearchCoord('');
                }
              }}
              onSelect={handleAddCoord}
              onChange={setCoordSearch}
              placeholder="Clique para ver lista ou digite para buscar..."
              style={{ width: '100%' }}
              notFoundContent={loadingCoord ? <Spin size="small" /> : null}
            />
          </div>
        </fieldset>
      </Space>
    </Card>
  );
}
