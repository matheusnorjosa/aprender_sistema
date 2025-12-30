/**
 * PR16: PeoplePicker
 *
 * Componente para selecionar formadores e coordenadores acompanhantes
 * Usa lookup de usuários e armazena como array de {id, email, label}
 */

import { useState } from 'react';
import { Card, Space, Tag, AutoComplete, Spin, Button } from 'antd';
import { PlusOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { lookupUsuarios } from '../api/lookup';
import logger from '../utils/logger';

export default function PeoplePicker({
  value = { formadores: [], coordAcompanha: [] },
  onChange,
}) {
  const [formadoresOptions, setFormadoresOptions] = useState([]);
  const [coordOptions, setCoordOptions] = useState([]);
  const [loadingFormadores, setLoadingFormadores] = useState(false);
  const [loadingCoord, setLoadingCoord] = useState(false);
  const [formadorSearch, setFormadorSearch] = useState('');
  const [coordSearch, setCoordSearch] = useState('');

  const handleSearchFormadores = async (query) => {
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
          value: item.id,
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

  const handleSearchCoord = async (query) => {
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
          value: item.id,
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

  const handleAddFormador = (selectedValue, option) => {
    const newFormador = {
      id: option.data.id,
      email: option.data.email,
      label: option.data.label,
    };

    // Verificar se já existe
    const exists = value.formadores.some(f => f.id === newFormador.id || f.email === newFormador.email);
    if (exists) {
      return;
    }

    const updated = {
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

  const handleAddCoord = (selectedValue, option) => {
    const newCoord = {
      id: option.data.id,
      email: option.data.email,
      label: option.data.label,
    };

    // Verificar se já existe
    const exists = value.coordAcompanha.some(c => c.id === newCoord.id || c.email === newCoord.email);
    if (exists) {
      return;
    }

    const updated = {
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

  const handleRemoveFormador = (id) => {
    const updated = {
      ...value,
      formadores: value.formadores.filter((f) => f.id !== id),
    };

    if (onChange) {
      onChange(updated);
    }
  };

  const handleRemoveCoord = (id) => {
    const updated = {
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
        <div>
          <div className="mb-2 font-medium">Formadores:</div>
          <Space wrap>
            {value.formadores.map((formador) => (
              <Tag
                key={formador.id}
                closable
                onClose={() => handleRemoveFormador(formador.id)}
                color="blue"
              >
                {formador.label || formador.email}
              </Tag>
            ))}
          </Space>
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
        </div>

        {/* Coordenadores Acompanhantes */}
        <div>
          <div className="mb-2 font-medium">Coordenadores Acompanhantes:</div>
          <Space wrap>
            {value.coordAcompanha.map((coord) => (
              <Tag
                key={coord.id}
                closable
                onClose={() => handleRemoveCoord(coord.id)}
                color="green"
              >
                {coord.label || coord.email}
              </Tag>
            ))}
          </Space>
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
        </div>
      </Space>
    </Card>
  );
}
