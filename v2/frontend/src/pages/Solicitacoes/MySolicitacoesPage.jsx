/**
 * MySolicitacoesPage - Página de listagem de solicitações do usuário
 *
 * Features:
 * - Filtro por status (Todas, Pendentes, Aprovadas, Reprovadas)
 * - Busca textual
 * - Tabela com dados principais
 * - Botão para criar nova solicitação
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Table, Card, Select, Input, Button, Space, Tag, Typography, message } from 'antd';
import { PlusOutlined, SearchOutlined, VideoCameraOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import { listSolicitacoes } from '../../api/solicitacoes';

const { Title } = Typography;

const STATUS_COLORS = {
  pendente: 'orange',
  aprovado: 'green',
  reprovado: 'red',
};

const STATUS_LABELS = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
};

export default function MySolicitacoesPage() {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);

  const [statusFilter, setStatusFilter] = useState(''); // '' = Todas
  const [searchTerm, setSearchTerm] = useState('');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const filters = { mine: 'true' };
      if (statusFilter) filters.status = statusFilter;
      if (searchTerm) filters.q = searchTerm;

      const data = await listSolicitacoes(filters);
      setRows(data.results || data); // Paginated or direct array
      setTotal(data.count || data.length);
    } catch (error) {
      message.error('Erro ao carregar solicitações: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const columns = [
    {
      title: 'Data/Hora',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (inicio) => dayjs(inicio).format('DD/MM/YYYY HH:mm'),
      width: 150,
    },
    {
      title: 'Município',
      dataIndex: 'municipio',
      key: 'municipio',
      render: (municipio) => municipio?.nome || '-',
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto',
      key: 'projeto',
      render: (projeto) => projeto?.nome || '-',
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_evento',
      key: 'tipo_evento',
      render: (tipo) => tipo?.nome || '-',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={STATUS_COLORS[status]}>{STATUS_LABELS[status] || status}</Tag>
      ),
      width: 120,
    },
    {
      title: 'Reunião',
      dataIndex: 'meet_link',
      key: 'meet_link',
      render: (meet_link) =>
        meet_link ? (
          <Button
            size="small"
            type="link"
            icon={<VideoCameraOutlined />}
            href={meet_link}
            target="_blank"
            rel="noopener noreferrer"
          >
            Entrar
          </Button>
        ) : (
          '-'
        ),
      width: 100,
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={2} style={{ margin: 0 }}>
              Minhas Solicitações
            </Title>
            <Link to="/solicitacoes/nova">
              <Button type="primary" icon={<PlusOutlined />}>
                Nova Solicitação
              </Button>
            </Link>
          </div>

          {/* Filtros */}
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 200 }}
              placeholder="Status"
            >
              <Select.Option value="">Todas</Select.Option>
              <Select.Option value="pendente">Pendentes</Select.Option>
              <Select.Option value="aprovado">Aprovadas</Select.Option>
              <Select.Option value="reprovado">Reprovadas</Select.Option>
            </Select>

            <Input.Search
              placeholder="Buscar por município, projeto..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onSearch={loadData}
              enterButton={<SearchOutlined />}
              style={{ width: 300 }}
              allowClear
            />
          </Space>

          {/* Tabela */}
          <Table
            columns={columns}
            dataSource={rows}
            loading={loading}
            rowKey="id"
            pagination={{
              total,
              pageSize: 20,
              showTotal: (total) => `Total: ${total} solicitações`,
            }}
          />
        </Space>
      </Card>
    </div>
  );
}
