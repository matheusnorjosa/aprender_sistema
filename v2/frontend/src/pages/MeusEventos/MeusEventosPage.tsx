/**
 * MeusEventosPage — Página /meus-eventos
 *
 * Issue #1225 (Epic 2 RBAC Realignment): lista eventos onde o usuário
 * autenticado é participante. Caso primário: Formador (única página
 * acessível por intent matrix); qualquer user autenticado pode consumir.
 *
 * Backend: GET /api/me/events/ (PR #1237). Lê apenas Solicitacoes
 * aprovadas onde request.user é participante. Ordenação: -inicio.
 */

import { useState, useEffect, useCallback, useMemo, JSX } from 'react';
// antd — direct imports for tree-shaking (Issue #424)
import Table from 'antd/es/table';
import Card from 'antd/es/card';
import Empty from 'antd/es/empty';
import Space from 'antd/es/space';
import Tag from 'antd/es/tag';
import Typography from 'antd/es/typography';
import message from 'antd/es/message';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import dayjs from 'dayjs';

import { getMyEvents, type MeEvent } from '../../api/me';
import { MeetLink } from '../../components/MeetLink';

const { Title, Text } = Typography;

const PAGE_SIZE = 20;

export default function MeusEventosPage(): JSX.Element {
  const [loading, setLoading] = useState<boolean>(false);
  const [rows, setRows] = useState<MeEvent[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);

  const loadData = useCallback(async (pageNumber: number): Promise<void> => {
    try {
      setLoading(true);
      const data = await getMyEvents({ page: pageNumber, page_size: PAGE_SIZE });
      setRows(data.results);
      setTotal(data.count);
    } catch (error) {
      message.error('Erro ao carregar seus eventos: ' + (error as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData(page);
  }, [loadData, page]);

  const handleTableChange = useCallback((pagination: TablePaginationConfig): void => {
    if (pagination.current && pagination.current !== page) {
      setPage(pagination.current);
    }
  }, [page]);

  const columns: ColumnsType<MeEvent> = useMemo(() => [
    {
      title: 'Data',
      dataIndex: 'inicio',
      key: 'data',
      render: (inicio: string) => dayjs(inicio).format('DD/MM/YYYY'),
      width: 110,
    },
    {
      title: 'Horário',
      key: 'horario',
      render: (_, record: MeEvent) =>
        `${dayjs(record.inicio).format('HH:mm')} – ${dayjs(record.fim).format('HH:mm')}`,
      width: 130,
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
      key: 'tipo',
      render: (nome: string | null) => nome || '-',
    },
    {
      title: 'Local',
      dataIndex: 'local',
      key: 'local',
      render: (local: string, record: MeEvent) =>
        record.is_online ? (
          <Tag color="blue">Online</Tag>
        ) : (
          local || <Text type="secondary">—</Text>
        ),
      ellipsis: true,
    },
    {
      title: 'Formadores',
      dataIndex: 'formadores',
      key: 'formadores',
      render: (formadores: string[]) =>
        formadores.length > 0 ? formadores.join(', ') : <Text type="secondary">—</Text>,
      ellipsis: true,
    },
    {
      title: 'Reunião',
      dataIndex: 'meet_link',
      key: 'meet_link',
      render: (meet_link: string | null) => <MeetLink href={meet_link} />,
      width: 150,
    },
  ], []);

  return (
    <section className="p-6" aria-labelledby="meus-eventos-title">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <header>
            <Title level={2} className="m-0" id="meus-eventos-title">
              Meus Eventos
            </Title>
            <Text type="secondary">
              Lista de eventos aprovados em que você é participante.
            </Text>
          </header>

          <section aria-label="Tabela de eventos">
            <Table
              scroll={{ x: 'max-content' }}
              columns={columns}
              dataSource={rows}
              loading={loading}
              rowKey="id"
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="Você não tem eventos agendados."
                  />
                ),
              }}
              pagination={{
                current: page,
                total,
                pageSize: PAGE_SIZE,
                showSizeChanger: false,
                showTotal: (totalCount) => `Total: ${totalCount} eventos`,
              }}
              onChange={handleTableChange}
            />
          </section>
        </Space>
      </Card>
    </section>
  );
}
