/**
 * Admin DAT - Projetos
 *
 * CRUD de projetos com fluxo (SUPER/NAO_SUPER) e status ativo.
 * Fase 1 Iteração 2 - Plano DAT/GCal 2025-10-29
 */

import { useState, useEffect } from 'react';
import { Table, Button, Input, Space, Tag, Typography, Card, message } from 'antd';
import { ProjectOutlined, ReloadOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { listProjetos } from '../../api/adminDAT';

const { Title } = Typography;
const { Search } = Input;

export default function ProjetosPage() {
  const [projetos, setProjetos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');

  const fetchProjetos = async () => {
    setLoading(true);
    try {
      const data = await listProjetos({
        search: searchText,
        ordering: 'nome',
      });
      setProjetos(data.results || data);
    } catch (error) {
      message.error(`Erro ao carregar projetos: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjetos();
  }, [searchText]);

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: 'Nome', dataIndex: 'nome', key: 'nome', width: 300 },
    { title: 'Código', dataIndex: 'codigo', key: 'codigo', width: 120 },
    {
      title: 'Fluxo',
      dataIndex: 'fluxo',
      key: 'fluxo',
      width: 150,
      render: (fluxo) => (
        <Tag color={fluxo === 'SUPER' ? 'gold' : 'blue'}>
          {fluxo === 'SUPER' ? 'SUPER (Manual)' : 'NAO_SUPER (Auto)'}
        </Tag>
      ),
    },
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
            Projetos ({projetos.length})
          </Title>
          <Space>
            <Search
              placeholder="Buscar por nome ou código"
              allowClear
              style={{ width: 250 }}
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchProjetos} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<PlusOutlined />} disabled title="Em desenvolvimento">
              Novo Projeto
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={projetos}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15, showTotal: (total) => `Total: ${total}` }}
          scroll={{ x: 900 }}
        />
      </Card>
    </div>
  );
}
