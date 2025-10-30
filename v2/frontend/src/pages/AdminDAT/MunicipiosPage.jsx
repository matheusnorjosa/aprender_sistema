/**
 * Admin DAT - Municípios
 *
 * CRUD de municípios com indicadores (UF, ativo).
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message, Select } from 'antd';
import { EnvironmentOutlined, ReloadOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listMunicipios } from '../../api/adminDAT';

const { Title } = Typography;
const { Search } = Input;

export default function MunicipiosPage() {
  const [municipios, setMunicipios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [ufFilter, setUfFilter] = useState(undefined);

  const fetchMunicipios = async () => {
    setLoading(true);
    try {
      const data = await listMunicipios({
        search: searchText,
        uf: ufFilter,
        ordering: 'nome',
      });
      setMunicipios(data.results || data);
    } catch (error) {
      message.error(`Erro ao carregar municípios: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMunicipios();
  }, [searchText, ufFilter]);

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 300 },
    { title: 'UF', dataIndex: 'uf', key: 'uf', width: 80, render: (uf) => <Tag color="blue">{uf}</Tag> },
    { title: 'IBGE', dataIndex: 'ibge_code', key: 'ibge_code', width: 120 },
    {
      title: 'Ativo',
      dataIndex: 'ativo',
      key: 'ativo',
      width: 100,
      render: (ativo) => <Tag color={ativo ? 'green' : 'red'}>{ativo ? 'Sim' : 'Não'}</Tag>,
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 150,
      render: () => (
        <Button type="link" size="small" icon={<EditOutlined />} disabled title="Em desenvolvimento">
          Editar
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
      <div style={{ marginBottom: '16px' }}>
        <Link to="/admin-dat">← Voltar para Admin DAT</Link>
      </div>

      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <Title level={3} style={{ margin: 0 }}>
            Municípios ({municipios.length})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome ou IBGE"
              allowClear
              style={{ width: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Select
              placeholder="Filtrar por UF"
              allowClear
              style={{ width: 100 }}
              onChange={setUfFilter}
              options={['BA', 'CE', 'PE', 'RN', 'SE', 'AL', 'PB', 'PI', 'MA'].map((uf) => ({ label: uf, value: uf }))}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchMunicipios} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} disabled title="Em desenvolvimento">
              Novo Município
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={municipios}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15, showTotal: (total) => `Total: ${total}` }}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  );
}
