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

    if (!query || query.length < 2) {
      setFormadoresOptions([]);
      return;
    }

    try {
      setLoadingFormadores(true);
      const results = await lookupUsuarios(query, 'Formador');
      setFormadoresOptions(
        results.map(item => ({
          value: item.id,
          label: item.label,
          data: item,
        }))
      );
    } catch (error) {
      console.error('Erro ao buscar formadores:', error);
    } finally {
      setLoadingFormadores(false);
    }
  };

  const handleSearchCoord = async (query) => {
    setCoordSearch(query);

    if (!query || query.length < 2) {
      setCoordOptions([]);
      return;
    }

    try {
      setLoadingCoord(true);
      const results = await lookupUsuarios(query, 'Coordenador');
      setCoordOptions(
        results.map(item => ({
          value: item.id,
          label: item.label,
          data: item,
        }))
      );
    } catch (error) {
      console.error('Erro ao buscar coordenadores:', error);
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

    // Limpar busca
    setFormadorSearch('');
    setFormadoresOptions([]);
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

    // Limpar busca
    setCoordSearch('');
    setCoordOptions([]);
  };

  const handleRemoveFormador = (index) => {
    const updated = {
      ...value,
      formadores: value.formadores.filter((_, i) => i !== index),
    };

    if (onChange) {
      onChange(updated);
    }
  };

  const handleRemoveCoord = (index) => {
    const updated = {
      ...value,
      coordAcompanha: value.coordAcompanha.filter((_, i) => i !== index),
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
          <div style={{ marginBottom: 8, fontWeight: 500 }}>Formadores:</div>
          <Space wrap>
            {value.formadores.map((formador, index) => (
              <Tag
                key={index}
                closable
                onClose={() => handleRemoveFormador(index)}
                color="blue"
              >
                {formador.label || formador.email}
              </Tag>
            ))}
          </Space>
          <div style={{ marginTop: 8 }}>
            <AutoComplete
              value={formadorSearch}
              options={formadoresOptions}
              onSearch={handleSearchFormadores}
              onSelect={handleAddFormador}
              onChange={setFormadorSearch}
              placeholder="Buscar formador por nome ou email..."
              style={{ width: '100%' }}
              notFoundContent={loadingFormadores ? <Spin size="small" /> : 'Digite pelo menos 2 caracteres'}
            />
          </div>
        </div>

        {/* Coordenadores Acompanhantes */}
        <div>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>Coordenadores Acompanhantes:</div>
          <Space wrap>
            {value.coordAcompanha.map((coord, index) => (
              <Tag
                key={index}
                closable
                onClose={() => handleRemoveCoord(index)}
                color="green"
              >
                {coord.label || coord.email}
              </Tag>
            ))}
          </Space>
          <div style={{ marginTop: 8 }}>
            <AutoComplete
              value={coordSearch}
              options={coordOptions}
              onSearch={handleSearchCoord}
              onSelect={handleAddCoord}
              onChange={setCoordSearch}
              placeholder="Buscar coordenador por nome ou email..."
              style={{ width: '100%' }}
              notFoundContent={loadingCoord ? <Spin size="small" /> : 'Digite pelo menos 2 caracteres'}
            />
          </div>
        </div>
      </Space>
    </Card>
  );
}
