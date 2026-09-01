/**
 * MySolicitacoesPage - Página de listagem de solicitações do usuário
 *
 * Features:
 * - Filtro por status (Todas, Pendentes, Aprovadas, Reprovadas)
 * - Busca textual
 * - Tabela com dados principais
 * - Botão para criar nova solicitação
 */

import { useState, useEffect, useCallback, useMemo, ChangeEvent, JSX } from 'react';
import { Link, useNavigate } from 'react-router';
// antd - direct imports for tree-shaking (Issue #424)
import Table from 'antd/es/table';
import Card from 'antd/es/card';
import Select from 'antd/es/select';
import Input from 'antd/es/input';
import Button from 'antd/es/button';
import Space from 'antd/es/space';
import Tag from 'antd/es/tag';
import Typography from 'antd/es/typography';
import message from 'antd/es/message';
import Tooltip from 'antd/es/tooltip';
import Popconfirm from 'antd/es/popconfirm';
import type { ColumnsType } from 'antd/es/table';
// icons - direct imports for tree-shaking (Issue #425)
import PlusOutlined from '@ant-design/icons/PlusOutlined';
import SearchOutlined from '@ant-design/icons/SearchOutlined';
import EditOutlined from '@ant-design/icons/EditOutlined';
import DeleteOutlined from '@ant-design/icons/DeleteOutlined';

import { listSolicitacoes, deleteSolicitacao } from '../../api/solicitacoes';
import { MeetLink } from '../../components/MeetLink';
import type { ID, Solicitacao, SolicitacaoStatus, FluxoType, GCalStatus, Participation, PaginatedResponse } from '../../types';
import { formadoresLabel } from '../../utils/participants';
import { formatFortaleza } from '../../utils/datetime';

const { Title } = Typography;

/** Status colors */
const STATUS_COLORS: Record<SolicitacaoStatus, string> = {
  pendente: 'orange',
  aprovado: 'green',
  reprovado: 'red',
};

/** Status labels */
const STATUS_LABELS: Record<SolicitacaoStatus, string> = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
};

/** API error response type */
interface ApiErrorResponse {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

export default function MySolicitacoesPage(): JSX.Element {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const [rows, setRows] = useState<Solicitacao[]>([]);
  const [total, setTotal] = useState<number>(0);

  const [statusFilter, setStatusFilter] = useState<SolicitacaoStatus | ''>(''); // '' = Todas
  const [searchTerm, setSearchTerm] = useState<string>('');

  const loadData = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      const filters: Record<string, string> = { mine: 'true' };
      if (statusFilter) filters['status'] = statusFilter;
      if (searchTerm) filters['q'] = searchTerm;

      const data = await listSolicitacoes(filters) as PaginatedResponse<Solicitacao> | Solicitacao[];
      const results = 'results' in data ? data.results : data;
      const count = 'count' in data ? data.count : (data).length;
      setRows(results || []);
      setTotal(count || 0);
    } catch (error) {
      message.error('Erro ao carregar solicitações: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleDelete = useCallback(async (id: ID): Promise<void> => {
    try {
      await deleteSolicitacao(id);
      message.success('Solicitação excluída com sucesso!');
      void loadData();
    } catch (error) {
      const apiErr = error as ApiErrorResponse;
      if (apiErr.response?.data?.detail) {
        message.error(apiErr.response.data.detail);
      } else {
        message.error('Erro ao excluir solicitação: ' + (error as Error).message);
      }
    }
  }, [loadData]);

  // Colunas memoizadas (Issue #427)
  const columns: ColumnsType<Solicitacao> = useMemo(() => [
    {
      title: 'Data/Hora',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (inicio: string) => formatFortaleza(inicio),
      width: 150,
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_evento_nome',
      key: 'tipo_evento',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      // Nome do formador (inclui convidados "que saíram" via guest_nome — sem FK). Ver utils/participants.
      render: (participations: Participation[] | undefined) => formadoresLabel(participations) || '-',
      ellipsis: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: SolicitacaoStatus) => (
        <Tag color={STATUS_COLORS[status]}>{STATUS_LABELS[status] || status}</Tag>
      ),
      width: 120,
    },
    {
      title: 'Reunião',
      dataIndex: 'meet_link',
      key: 'meet_link',
      render: (meet_link: string | null) => <MeetLink href={meet_link} />,
      width: 150,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 120,
      render: (_, record) => {
        // Pode editar se não estiver publicado no GCal e não estiver reprovado
        const canEdit = record.gcal_status !== ('PUBLISHED' as GCalStatus) && record.status !== 'reprovado';
        // Pode excluir conforme regras por fluxo:
        // - SUPER: só se pendente E não publicado no GCal
        // - NAO_SUPER: se não publicado no GCal (independente do status)
        const isPublished = record.gcal_status === ('PUBLISHED' as GCalStatus);
        const isSuper = record.fluxo === ('SUPER' as FluxoType);
        const canDelete = !isPublished && (!isSuper || record.status === 'pendente');

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
              <Tooltip title={
                isPublished
                  ? 'Solicitações publicadas no Google Calendar não podem ser excluídas'
                  : 'Solicitações do fluxo SUPER só podem ser excluídas enquanto pendentes'
              }>
                <Button type="text" icon={<DeleteOutlined />} disabled />
              </Tooltip>
            )}
          </Space>
        );
      },
    },
  ], [handleDelete, navigate]);

  return (
    <section className="p-6" aria-labelledby="minhas-solicitacoes-title">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Header semantico */}
          <header className="flex justify-between items-center">
            <Title level={2} className="m-0" id="minhas-solicitacoes-title">
              Minhas Solicitações
            </Title>
            <Link to="/solicitacoes/nova">
              <Button type="primary" icon={<PlusOutlined />}>
                Nova Solicitação
              </Button>
            </Link>
          </header>

          {/* Filtros */}
          <nav aria-label="Filtros de busca">
            <Space>
              <Select
                value={statusFilter}
                onChange={setStatusFilter}
                style={{ width: '100%', maxWidth: 200 }}
                placeholder="Status"
                aria-label="Filtrar por status"
              >
                <Select.Option value="">Todas</Select.Option>
                <Select.Option value="pendente">Pendentes</Select.Option>
                <Select.Option value="aprovado">Aprovadas</Select.Option>
                <Select.Option value="reprovado">Reprovadas</Select.Option>
              </Select>

              <Input.Search
                placeholder="Buscar por município, projeto..."
                value={searchTerm}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
                onSearch={loadData}
                enterButton={<SearchOutlined />}
                style={{ width: '100%', maxWidth: 300 }}
                allowClear
                aria-label="Buscar solicitacoes"
              />
            </Space>
          </nav>

          {/* Tabela */}
          <section aria-label="Lista de solicitacoes">
            <Table
              scroll={{ x: "max-content" }}
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
          </section>
        </Space>
      </Card>
    </section>
  );
}
