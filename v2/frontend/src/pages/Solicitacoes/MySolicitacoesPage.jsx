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
import { Link, useNavigate } from 'react-router-dom';
import { Table, Card, Select, Input, Button, Space, Tag, Typography, message, Tooltip, Popconfirm } from 'antd';
import { PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import { listSolicitacoes, deleteSolicitacao } from '../../api/solicitacoes';
import { MeetLink } from '../../components/MeetLink';

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
  const navigate = useNavigate();
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

  const handleDelete = async (id) => {
    try {
      await deleteSolicitacao(id);
      message.success('Solicitação excluída com sucesso!');
      loadData(); // Recarrega a lista
    } catch (error) {
      if (error.response?.data?.detail) {
        message.error(error.response.data.detail);
      } else {
        message.error('Erro ao excluir solicitação: ' + error.message);
      }
    }
  };

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
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      render: (participations) => {
        if (!participations || !Array.isArray(participations)) return '-';
        const formadores = participations
          .filter(p => p.role === 'FORMADOR' && p.usuario)
          .map(p => p.usuario.first_name || p.usuario.username);
        return formadores.length > 0 ? formadores.join(', ') : '-';
      },
      ellipsis: true,
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
      render: (meet_link) => <MeetLink href={meet_link} />,
      width: 150,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 120,
      render: (_, record) => {
        // Pode editar se não estiver publicado no GCal e não estiver reprovado
        const canEdit = record.gcal_status !== 'PUBLISHED' && record.status !== 'reprovado';
        // Pode excluir se não estiver publicado no GCal
        const canDelete = record.gcal_status !== 'PUBLISHED';

        return (
          <Space size="small">
            {canEdit ? (
              <Tooltip title="Editar solicitação">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => navigate(`/solicitacoes/${record.id}/editar`)}
                />
              </Tooltip>
            ) : (
              <Tooltip title={
                record.status === 'reprovado'
                  ? 'Solicitações reprovadas não podem ser editadas'
                  : 'Solicitações publicadas no Google Calendar não podem ser editadas'
              }>
                <Button type="text" icon={<EditOutlined />} disabled />
              </Tooltip>
            )}

            {canDelete ? (
              <Popconfirm
                title="Excluir solicitação"
                description="Tem certeza que deseja excluir esta solicitação? Esta ação não pode ser desfeita."
                onConfirm={() => handleDelete(record.id)}
                okText="Sim, excluir"
                cancelText="Cancelar"
                okButtonProps={{ danger: true }}
              >
                <Tooltip title="Excluir solicitação">
                  <Button type="text" icon={<DeleteOutlined />} danger />
                </Tooltip>
              </Popconfirm>
            ) : (
              <Tooltip title="Solicitações publicadas no Google Calendar não podem ser excluídas">
                <Button type="text" icon={<DeleteOutlined />} disabled />
              </Tooltip>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div className="p-6">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Header */}
          <div className="flex justify-between items-center">
            <Title level={2} className="m-0">
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
