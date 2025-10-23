/**
 * ParticipantsPicker - Componente para selecionar participantes do evento
 *
 * Props:
 * - currentUser: { id, first_name, last_name, email } - Usuário atual (coordenador)
 * - value: { formadorIds, formadorEmails, coordAcompanhaIds, coordAcompanhaEmails }
 * - onChange: (value) => void
 * - usuariosOptions: Array<{id, first_name, last_name, email}> - Lista de usuários disponíveis
 */

import { useState } from 'react';
import { Card, Space, Typography, Select, Input, Button, Tag } from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';

const { Text, Title } = Typography;

export default function ParticipantsPicker({
  currentUser,
  value = { formadorIds: [], formadorEmails: [], coordAcompanhaIds: [], coordAcompanhaEmails: [] },
  onChange,
  usuariosOptions = [],
}) {
  const [formadorType, setFormadorType] = useState('id'); // 'id' ou 'email'
  const [coordType, setCoordType] = useState('id'); // 'id' ou 'email'

  const handleAddFormador = (item) => {
    const updated = { ...value };
    if (formadorType === 'id') {
      if (!updated.formadorIds.includes(item)) {
        updated.formadorIds = [...updated.formadorIds, item];
      }
    } else {
      if (!updated.formadorEmails.includes(item)) {
        updated.formadorEmails = [...updated.formadorEmails, item];
      }
    }
    onChange?.(updated);
  };

  const handleRemoveFormador = (item, type) => {
    const updated = { ...value };
    if (type === 'id') {
      updated.formadorIds = updated.formadorIds.filter((id) => id !== item);
    } else {
      updated.formadorEmails = updated.formadorEmails.filter((email) => email !== item);
    }
    onChange?.(updated);
  };

  const handleAddCoord = (item) => {
    const updated = { ...value };
    if (coordType === 'id') {
      if (!updated.coordAcompanhaIds.includes(item)) {
        updated.coordAcompanhaIds = [...updated.coordAcompanhaIds, item];
      }
    } else {
      if (!updated.coordAcompanhaEmails.includes(item)) {
        updated.coordAcompanhaEmails = [...updated.coordAcompanhaEmails, item];
      }
    }
    onChange?.(updated);
  };

  const handleRemoveCoord = (item, type) => {
    const updated = { ...value };
    if (type === 'id') {
      updated.coordAcompanhaIds = updated.coordAcompanhaIds.filter((id) => id !== item);
    } else {
      updated.coordAcompanhaEmails = updated.coordAcompanhaEmails.filter((email) => email !== item);
    }
    onChange?.(updated);
  };

  const getUserLabel = (userId) => {
    const user = usuariosOptions.find((u) => u.id === userId);
    return user ? `${user.first_name} ${user.last_name}` : `ID ${userId}`;
  };

  return (
    <Card title="Participantes" size="small">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Coordenador (read-only) */}
        <div>
          <Text strong>Coordenador:</Text>
          <div style={{ marginTop: 8 }}>
            <Tag color="blue">
              {currentUser ? `${currentUser.first_name} ${currentUser.last_name} (você)` : 'Você'}
            </Tag>
          </div>
        </div>

        {/* Formadores */}
        <div>
          <Title level={5}>Formadores</Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <Select
                value={formadorType}
                onChange={setFormadorType}
                style={{ width: 120 }}
                options={[
                  { label: 'Por usuário', value: 'id' },
                  { label: 'Por email', value: 'email' },
                ]}
              />
              {formadorType === 'id' ? (
                <Select
                  placeholder="Selecione um formador"
                  style={{ width: 300 }}
                  showSearch
                  filterOption={(input, option) =>
                    option.label.toLowerCase().includes(input.toLowerCase())
                  }
                  options={usuariosOptions.map((u) => ({
                    label: `${u.first_name} ${u.last_name} (${u.email})`,
                    value: u.id,
                  }))}
                  onSelect={handleAddFormador}
                />
              ) : (
                <Input.Search
                  placeholder="Digite o email"
                  style={{ width: 300 }}
                  onSearch={handleAddFormador}
                  enterButton={<PlusOutlined />}
                />
              )}
            </Space>
            {/* Lista de formadores adicionados */}
            <div>
              {value.formadorIds.map((id) => (
                <Tag
                  key={`formador-id-${id}`}
                  closable
                  onClose={() => handleRemoveFormador(id, 'id')}
                  style={{ marginBottom: 4 }}
                >
                  {getUserLabel(id)}
                </Tag>
              ))}
              {value.formadorEmails.map((email) => (
                <Tag
                  key={`formador-email-${email}`}
                  closable
                  onClose={() => handleRemoveFormador(email, 'email')}
                  style={{ marginBottom: 4 }}
                  color="orange"
                >
                  {email}
                </Tag>
              ))}
            </div>
          </Space>
        </div>

        {/* Coordenadores Acompanhantes */}
        <div>
          <Title level={5}>Coordenadores Acompanhantes</Title>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Space>
              <Select
                value={coordType}
                onChange={setCoordType}
                style={{ width: 120 }}
                options={[
                  { label: 'Por usuário', value: 'id' },
                  { label: 'Por email', value: 'email' },
                ]}
              />
              {coordType === 'id' ? (
                <Select
                  placeholder="Selecione um coordenador"
                  style={{ width: 300 }}
                  showSearch
                  filterOption={(input, option) =>
                    option.label.toLowerCase().includes(input.toLowerCase())
                  }
                  options={usuariosOptions.map((u) => ({
                    label: `${u.first_name} ${u.last_name} (${u.email})`,
                    value: u.id,
                  }))}
                  onSelect={handleAddCoord}
                />
              ) : (
                <Input.Search
                  placeholder="Digite o email"
                  style={{ width: 300 }}
                  onSearch={handleAddCoord}
                  enterButton={<PlusOutlined />}
                />
              )}
            </Space>
            {/* Lista de coordenadores acompanhantes adicionados */}
            <div>
              {value.coordAcompanhaIds.map((id) => (
                <Tag
                  key={`coord-id-${id}`}
                  closable
                  onClose={() => handleRemoveCoord(id, 'id')}
                  style={{ marginBottom: 4 }}
                  color="purple"
                >
                  {getUserLabel(id)}
                </Tag>
              ))}
              {value.coordAcompanhaEmails.map((email) => (
                <Tag
                  key={`coord-email-${email}`}
                  closable
                  onClose={() => handleRemoveCoord(email, 'email')}
                  style={{ marginBottom: 4 }}
                  color="magenta"
                >
                  {email}
                </Tag>
              ))}
            </div>
          </Space>
        </div>
      </Space>
    </Card>
  );
}
