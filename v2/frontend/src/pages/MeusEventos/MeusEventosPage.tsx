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
import Card from 'antd/es/card';
import Space from 'antd/es/space';
import Tag from 'antd/es/tag';
import Typography from 'antd/es/typography';
import type { TablePaginationConfig } from 'antd/es/table';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';

import { formatFortaleza } from '../../utils/datetime';
import { getMyEvents, type MeEvent } from '../../api/me';
import { formadoresNomes } from '../../utils/participants';
import { MeetLink } from '../../components/MeetLink';

const { Title, Text } = Typography;

const PAGE_SIZE = 20;

/** Quem a linha representa: a data e o município ("Expandir linha de 10/05/2026 · Crato"). */
function nomeDoEvento(evento: MeEvent): string {
  return `${formatFortaleza(evento.inicio, 'DD/MM/YYYY')} · ${evento.municipio_nome || 'sem município'}`;
}

export default function MeusEventosPage(): JSX.Element {
  const [loading, setLoading] = useState<boolean>(false);
  const [rows, setRows] = useState<MeEvent[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  // Falha ao carregar: o motivo e "Tentar de novo" no lugar das linhas (não "você não tem eventos").
  const [erro, setErro] = useState<string | null>(null);

  const loadData = useCallback(async (pageNumber: number): Promise<void> => {
    try {
      setLoading(true);
      const data = await getMyEvents({ page: pageNumber, page_size: PAGE_SIZE });
      setRows(data.results);
      setTotal(data.count);
      setErro(null);
    } catch (error) {
      setErro((error as Error).message || 'Tente de novo em instantes.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData(page);
  }, [loadData, page]);

  const handleTableChange = useCallback((pagination: TablePaginationConfig): void => {
    if (pagination.current && pagination.current !== page) {
      setPage(pagination.current);
    }
  }, [page]);

  // Sem rolagem horizontal (padrão responsivo): sempre na linha a data e o município; o resto
  // sobe por largura e, abaixo dela, vai para a linha expandida.
  const columns: ColunaResponsiva<MeEvent>[] = useMemo(() => [
    {
      title: 'Data e horário',
      dataIndex: 'inicio',
      key: 'data',
      width: 116,
      render: (_, record: MeEvent) => (
        <>
          {formatFortaleza(record.inicio, 'DD/MM/YYYY')}
          <br />
          <Text type="secondary">
            {`${formatFortaleza(record.inicio, 'HH:mm')} – ${formatFortaleza(record.fim, 'HH:mm')}`}
          </Text>
        </>
      ),
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio',
      render: (_, record: MeEvent) => (
        <Text className="min-w-0 max-w-full break-words">{record.municipio_nome || '-'}</Text>
      ),
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      responsive: VISIVEL_A_PARTIR.md,
      ellipsis: true,
      render: (_, record: MeEvent) => record.projeto_nome || '-',
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_evento_nome',
      key: 'tipo',
      responsive: VISIVEL_A_PARTIR.xxl,
      ellipsis: true,
      render: (_, record: MeEvent) => record.tipo_evento_nome || '-',
    },
    {
      title: 'Local',
      dataIndex: 'local',
      key: 'local',
      responsive: VISIVEL_A_PARTIR.lg,
      render: (_, record: MeEvent) =>
        record.is_online ? (
          <Tag color="blue">Online</Tag>
        ) : (
          record.local || <Text type="secondary">—</Text>
        ),
      ellipsis: true,
    },
    {
      title: 'Formadores',
      dataIndex: 'participantes',
      key: 'formadores',
      responsive: VISIVEL_A_PARTIR.xl,
      // #1945: usa `participantes` (inclui quem saiu, via guest_nome) filtrando FORMADOR — no lugar
      // do `formadores` legado (só usuário). Mesmo padrão das outras telas. Ver utils/participants.
      render: (_, record: MeEvent) =>
        formadoresNomes(record.participantes) || <Text type="secondary">—</Text>,
      ellipsis: true,
    },
    {
      title: 'Reunião',
      dataIndex: 'meet_link',
      key: 'meet_link',
      responsive: VISIVEL_A_PARTIR.xl,
      // Sem link, "—" como as outras colunas vazias (o rótulo ficava sozinho na linha expandida).
      render: (_, record: MeEvent) =>
        record.meet_link ? <MeetLink href={record.meet_link} /> : <Text type="secondary">—</Text>,
      width: 200,
    },
  ], []);

  return (
    <section className="p-6" aria-labelledby="meus-eventos-title">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <header className="flex flex-wrap items-center gap-3">
            <Title level={2} className="m-0" id="meus-eventos-title">
              Meus Eventos
            </Title>
            <Text type="secondary">
              Lista de eventos aprovados em que você é participante.
            </Text>
          </header>

          <section aria-label="Tabela de eventos">
            <ResponsiveTable<MeEvent>
              columns={columns}
              dataSource={rows}
              loading={loading}
              rowKey="id"
              nomeDaLinha={nomeDoEvento}
              erro={erro}
              onTentarDeNovo={() => void loadData(page)}
              locale={{ emptyText: 'Você não tem eventos agendados.' }}
              pagination={{
                current: page,
                total,
                pageSize: PAGE_SIZE,
                showSizeChanger: false,
                showTotal: (totalCount) => `Total: ${totalCount} ${totalCount === 1 ? 'evento' : 'eventos'}`,
              }}
              onChange={handleTableChange}
            />
          </section>
        </Space>
      </Card>
    </section>
  );
}
