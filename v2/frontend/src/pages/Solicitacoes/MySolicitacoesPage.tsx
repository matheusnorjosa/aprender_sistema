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
import { Link, useNavigate } from 'react-router-dom';
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
import dayjs from 'dayjs';

import { listSolicitacoes, deleteSolicitacao } from '../../api/solicitacoes';
import { MeetLink } from '../../components/MeetLink';
import type { ID, Solicitacao, SolicitacaoStatus, FluxoType, GCalStatus, Participation, PaginatedResponse } from '../../types';

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

/** Municipio nested type */
interface MunicipioNested {
  nome?: string;
}

/** Projeto nested type */
interface ProjetoNested {
  nome?: string;
}

/** TipoEvento nested type */
interface TipoEventoNested {
  nome?: string;
}

/** Extended solicitacao with nested objects */
interface SolicitacaoExtended extends Omit<Solicitacao, 'municipio' | 'projeto' | 'tipo_evento'> {
  municipio?: MunicipioNested | number | null;
  projeto?: ProjetoNested | number | null;
  tipo_evento?: TipoEventoNested | number | null;
}

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
  const [rows, setRows] = useState<SolicitacaoExtended[]>([]);
  const [total, setTotal] = useState<number>(0);

  const [statusFilter, setStatusFilter] = useState<SolicitacaoStatus | ''>(''); // '' = Todas
  const [searchTerm, setSearchTerm] = useState<string>('');

  const loadData = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      const filters: Record<string, string> = { mine: 'true' };
      if (statusFilter) filters.status = statusFilter;
      if (searchTerm) filters.q = searchTerm;

      const data = await listSolicitacoes(filters) as PaginatedResponse<SolicitacaoExtended> | SolicitacaoExtended[];
      const results = 'results' in data ? data.results : data;
      const count = 'count' in data ? data.count : (data as SolicitacaoExtended[]).length;
      setRows(results || []);
      setTotal(count || 0);
    } catch (error) {
      message.error('Erro ao carregar solicitações: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDelete = useCallback(async (id: ID): Promise<void> => {
    try {
      await deleteSolicitacao(id);
      message.success('Solicitação excluída com sucesso!');
      loadData();
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
  const columns: ColumnsType<SolicitacaoExtended> = useMemo(() => [
    {
      title: 'Data/Hora',
      dataIndex: 'inicio',
      key: 'inicio',
      render: (inicio: string) => dayjs(inicio).format('DD/MM/YYYY HH:mm'),
      width: 150,
    },
    {
      title: 'Município',
      dataIndex: 'municipio',
      key: 'municipio',
      render: (municipio: MunicipioNested | ID | null) => {
        if (municipio && typeof municipio === 'object' && 'nome' in municipio) {
          return municipio.nome || '-';
        }
        return '-';
      },
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto',
      key: 'projeto',
      render: (projeto: ProjetoNested | ID | null) => {
        if (projeto && typeof projeto === 'object' && 'nome' in projeto) {
          return projeto.nome || '-';
        }
        return '-';
      },
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_evento',
      key: 'tipo_evento',
      render: (tipo: TipoEventoNested | ID | null) => {
        if (tipo && typeof tipo === 'object' && 'nome' in tipo) {
          return tipo.nome || '-';
        }
        return '-';
      },
    },
    {
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      render: (participations: Participation[] | undefined) => {
        if (!participations || !Array.isArray(participations)) return '-';
        const formadores = participations
          .filter(p => p.role === 'FORMADOR' && p.usuario)
          .map(p => p.usuario!.first_name || p.usuario!.username);
        return formadores.length > 0 ? formadores.join(', ') : '-';
      },
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
              onChange={(e: ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
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
