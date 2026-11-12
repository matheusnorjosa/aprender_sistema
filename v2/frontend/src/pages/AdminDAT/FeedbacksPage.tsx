/**
 * Feedbacks (pedido do dono, 11/11/2026): o que as pessoas enviam pelo botão "Dar feedback".
 *
 * Lista paginada no servidor, mais recentes primeiro, com filtros por tipo, nota e período (dias
 * de Fortaleza) e "Exportar CSV" com os mesmos filtros. Só o superusuário e o DAT (policy
 * `manage_admin_registries`). A pessoa aparece pelo nome; o comentário vai cortado na linha e
 * inteiro na linha expandida.
 */
import { useCallback, useEffect, useState, type JSX } from 'react';
import { Button, Card, DatePicker, Select, Typography, message } from 'antd';
import type { TablePaginationConfig } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  TIPOS_FEEDBACK,
  exportarFeedbacks,
  listFeedbacks,
  type FeedbackFiltros,
  type FeedbackRecord,
  type TipoFeedback,
} from '../../api/feedback';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { DEFAULT_PAGE_SIZE } from '../../constants';
import { formatFortaleza } from '../../utils/datetime';
import { mensagemDoErro } from './usuario_form_helpers';

const { Title } = Typography;
const { RangePicker } = DatePicker;

const ROTULO_DO_TIPO: Record<TipoFeedback, string> = Object.fromEntries(
  TIPOS_FEEDBACK.map(({ value, label }) => [value, label]),
) as Record<TipoFeedback, string>;

type Filtros = Pick<FeedbackFiltros, 'tipo' | 'nota' | 'desde' | 'ate'>;

const colunas: ColunaResponsiva<FeedbackRecord>[] = [
  {
    title: 'Data',
    dataIndex: 'created_at',
    key: 'data',
    width: 140,
    responsive: VISIVEL_A_PARTIR.md,
    render: (valor) => formatFortaleza(valor as string),
  },
  { title: 'Pessoa', dataIndex: 'pessoa', key: 'pessoa', ellipsis: true, responsive: VISIVEL_A_PARTIR.sm },
  { title: 'Nota', dataIndex: 'nota', key: 'nota', width: 64 },
  {
    title: 'Tipo',
    dataIndex: 'tipo',
    key: 'tipo',
    width: 96,
    render: (valor) => ROTULO_DO_TIPO[valor as TipoFeedback] ?? String(valor),
  },
  { title: 'Tela', dataIndex: 'pagina', key: 'pagina', ellipsis: true, responsive: VISIVEL_A_PARTIR.lg },
  {
    title: 'Comentário',
    dataIndex: 'comentario',
    key: 'comentario',
    ellipsis: true,
    render: (valor) => (valor as string) || '—',
  },
  {
    // O texto inteiro, só na linha expandida (a coluna acima corta).
    title: 'Comentário completo',
    dataIndex: 'comentario',
    key: 'comentario-completo',
    responsive: VISIVEL_A_PARTIR.detalhe,
    render: (valor) => <span style={{ whiteSpace: 'pre-wrap' }}>{(valor as string) || 'Sem comentário'}</span>,
  },
];

export default function FeedbacksPage(): JSX.Element {
  const [feedbacks, setFeedbacks] = useState<FeedbackRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [filtros, setFiltros] = useState<Filtros>({});
  const [periodo, setPeriodo] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [exportando, setExportando] = useState(false);
  const [pagination, setPagination] = useState<TablePaginationConfig>({
    current: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
  });

  const carregar = useCallback(
    async (current: number, pageSize: number): Promise<void> => {
      setLoading(true);
      try {
        const data = await listFeedbacks({ ...filtros, page: current, page_size: pageSize });
        setFeedbacks(data.results);
        setErro(null);
        setPagination((prev) => ({ ...prev, current, pageSize, total: data.count }));
      } catch (error) {
        setErro(mensagemDoErro(error));
      } finally {
        setLoading(false);
      }
    },
    [filtros],
  );

  useEffect(() => {
    void carregar(1, pagination.pageSize || DEFAULT_PAGE_SIZE);
    // A troca de filtro volta à página 1; o tamanho da página vem do estado da hora.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carregar]);

  const recarregar = (): void => {
    void carregar(pagination.current || 1, pagination.pageSize || DEFAULT_PAGE_SIZE);
  };

  const mudarPeriodo = (datas: [Dayjs | null, Dayjs | null] | null): void => {
    setPeriodo(datas);
    setFiltros((prev) => ({
      ...prev,
      desde: datas?.[0]?.format('YYYY-MM-DD'),
      ate: datas?.[1]?.format('YYYY-MM-DD'),
    }));
  };

  const exportar = async (): Promise<void> => {
    setExportando(true);
    try {
      const blob = await exportarFeedbacks(filtros);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'feedbacks.csv';
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      message.error(`Não foi possível exportar: ${(error as Error).message}`);
    } finally {
      setExportando(false);
    }
  };

  const comFiltro = Object.values(filtros).some((v) => v !== undefined);

  return (
    <section className="p-6 bg-gray-100" style={{ minHeight: 'calc(100vh - 64px)' }} aria-labelledby="feedbacks-title">
      <Card>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Title level={3} className="m-0" id="feedbacks-title">
            Feedbacks{erro ? '' : ` (${pagination.total || 0})`}
          </Title>
          <div className="flex flex-wrap items-center gap-2">
            <Select<TipoFeedback>
              placeholder="Tipo"
              aria-label="Filtrar por tipo"
              allowClear
              style={{ width: 150, maxWidth: '100%' }}
              value={filtros.tipo ?? null}
              onChange={(tipo) => setFiltros((prev) => ({ ...prev, tipo }))}
              options={[...TIPOS_FEEDBACK]}
            />
            <Select<number>
              placeholder="Nota"
              aria-label="Filtrar por nota"
              allowClear
              style={{ width: 120, maxWidth: '100%' }}
              value={filtros.nota ?? null}
              onChange={(nota) => setFiltros((prev) => ({ ...prev, nota }))}
              options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: `Nota ${n}` }))}
            />
            <RangePicker
              format="DD/MM/YYYY"
              placeholder={['Desde', 'Até']}
              aria-label="Filtrar por período"
              value={periodo}
              onChange={mudarPeriodo}
              style={{ maxWidth: '100%' }}
            />
            <Button icon={<ReloadOutlined />} onClick={recarregar} loading={loading}>
              Atualizar
            </Button>
            <Button type="primary" icon={<DownloadOutlined />} onClick={() => void exportar()} loading={exportando}>
              Exportar CSV
            </Button>
          </div>
        </header>

        <ResponsiveTable<FeedbackRecord>
          columns={colunas}
          dataSource={feedbacks}
          rowKey="id"
          nomeDaLinha={(fb) => `${fb.pessoa} em ${formatFortaleza(fb.created_at)}`}
          loading={loading}
          erro={erro}
          onTentarDeNovo={recarregar}
          locale={{ emptyText: comFiltro ? 'Nenhum feedback com esses filtros.' : 'Nenhum feedback recebido ainda.' }}
          onChange={(nova) => void carregar(nova.current || 1, nova.pageSize || DEFAULT_PAGE_SIZE)}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            pageSizeOptions: ['15', '30', '50', '100'],
            showTotal: (total) => `Total: ${total}`,
          }}
        />
      </Card>
    </section>
  );
}
