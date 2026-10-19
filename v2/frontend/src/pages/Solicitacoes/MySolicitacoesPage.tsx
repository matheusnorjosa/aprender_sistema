/**
 * MySolicitacoesPage - Página de listagem de solicitações do usuário
 *
 * Features:
 * - Filtro por status (Todas, Pendentes, Aprovadas, Reprovadas)
 * - Busca textual
 * - Tabela com dados principais (padrão responsivo: sem rolagem horizontal)
 * - Botão para criar nova solicitação
 */

import { useState, useEffect, useCallback, useMemo, useRef, ChangeEvent, JSX } from 'react';
import { Link, useNavigate } from 'react-router';
// antd - direct imports for tree-shaking (Issue #424)
import Card from 'antd/es/card';
import Select from 'antd/es/select';
import Input from 'antd/es/input';
import Button from 'antd/es/button';
import Space from 'antd/es/space';
import Tag from 'antd/es/tag';
import Typography from 'antd/es/typography';
import message from 'antd/es/message';
import Modal from 'antd/es/modal';
import Grid from 'antd/es/grid';
import type { TablePaginationConfig } from 'antd/es/table';
// icons - direct imports for tree-shaking (Issue #425)
import PlusOutlined from '@ant-design/icons/PlusOutlined';
import SearchOutlined from '@ant-design/icons/SearchOutlined';
import EditOutlined from '@ant-design/icons/EditOutlined';
import DeleteOutlined from '@ant-design/icons/DeleteOutlined';
import InfoCircleOutlined from '@ant-design/icons/InfoCircleOutlined';

import { listSolicitacoes, deleteSolicitacao } from '../../api/solicitacoes';
import { MeetLink } from '../../components/MeetLink';
import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha, type AcaoDaLinha } from '../../components/AcoesLinha';
import type { ID, Solicitacao, SolicitacaoStatus, FluxoType, GCalStatus, PaginatedResponse } from '../../types';
import { formadoresLabel } from '../../utils/participants';
import { formatFortaleza } from '../../utils/datetime';
import { TEXTO_DA_TAG } from '../../components/textoDaTag';

const { Title, Text } = Typography;

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

/** Tamanho de página padrão; 100 é o limite que a tela oferece. */
const PAGE_SIZE = 20;
/** Espera depois da última letra antes de buscar (uma requisição por termo, não por letra). */
const ESPERA_BUSCA_MS = 350;

/** API error response type */
interface ApiErrorResponse {
  response?: {
    data?: {
      detail?: string;
    };
  };
  status?: number;
  message?: string;
}

/** Quem a linha representa: a data e o município ("Editar: 10/05/2026 · Crato"). */
function nomeDaSolicitacao(record: Solicitacao): string {
  return `${formatFortaleza(record.inicio, 'DD/MM/YYYY')} · ${record.municipio_nome || 'sem município'}`;
}

/**
 * O que a dona pode fazer na linha e, quando não pode, por quê (texto visível por um botão, e não
 * só no Tooltip de um botão desabilitado, que o teclado e o toque não alcançam). As regras são as
 * de sempre: editar se não estiver publicado no GCal e não estiver reprovado; excluir se não
 * estiver publicado e, no fluxo SUPER, só enquanto pendente.
 */
function permissoesDaLinha(record: Solicitacao): { podeEditar: boolean; podeExcluir: boolean; motivos: string[] } {
  const isPublished = record.gcal_status === ('PUBLISHED' as GCalStatus);
  const isSuper = record.fluxo === ('SUPER' as FluxoType);
  const podeEditar = !isPublished && record.status !== 'reprovado';
  const podeExcluir = !isPublished && (!isSuper || record.status === 'pendente');
  const motivos: string[] = [];
  if (isPublished) {
    motivos.push(
      'Este evento já está no Google Agenda. Para mudar, peça ao Apoio de Coordenação da sua gerência ou ao Controle que cancele a publicação; depois disso, você consegue editar aqui.'
    );
  } else if (record.status === 'reprovado') {
    motivos.push('Solicitações reprovadas não podem ser editadas.');
  }
  // Cancelar a publicação não devolve a exclusão a uma SUPER que já saiu de pendente.
  if (isSuper && record.status !== 'pendente') {
    motivos.push('Solicitações do fluxo Superintendência só podem ser excluídas enquanto estão pendentes.');
  }
  return { podeEditar, podeExcluir, motivos };
}

export default function MySolicitacoesPage(): JSX.Element {
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const [rows, setRows] = useState<Solicitacao[]>([]);
  const [total, setTotal] = useState<number>(0);
  // Falha ao carregar: o motivo e "Tentar de novo" no lugar das linhas (não as da carga anterior).
  const [erro, setErro] = useState<string | null>(null);
  // Paginação no servidor: antes a tela recebia as 100 primeiras e paginava no cliente.
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(PAGE_SIZE);
  // Celular (< 576 px): as ações vão todas para o menu "Mais ações".
  const acoesCompactas = !Grid.useBreakpoint().sm;
  const listaRef = useRef<HTMLElement>(null);

  const [statusFilter, setStatusFilter] = useState<SolicitacaoStatus | ''>(''); // '' = Todas
  const [searchTerm, setSearchTerm] = useState<string>('');
  // O termo que vai ao servidor: o digitado, depois de a pessoa parar de digitar.
  const [termoBuscado, setTermoBuscado] = useState<string>('');
  // A última carga vence: uma resposta antiga não substitui a lista do filtro atual.
  const seqRef = useRef(0);

  useEffect(() => {
    const espera = setTimeout(() => setTermoBuscado(searchTerm), ESPERA_BUSCA_MS);
    return () => clearTimeout(espera);
  }, [searchTerm]);

  const loadData = useCallback(async (): Promise<void> => {
    const seq = ++seqRef.current;
    try {
      setLoading(true);
      const filters: Record<string, string | number> = { mine: 'true' };
      if (statusFilter) filters['status'] = statusFilter;
      if (termoBuscado) filters['q'] = termoBuscado;
      filters['page'] = page;
      filters['page_size'] = pageSize;

      const data = await listSolicitacoes(filters) as PaginatedResponse<Solicitacao> | Solicitacao[];
      if (seq !== seqRef.current) return;
      const results = 'results' in data ? data.results : data;
      const count = 'count' in data ? data.count : (data).length;
      setRows(results || []);
      setTotal(count || 0);
      setErro(null);
    } catch (error) {
      if (seq !== seqRef.current) return;
      // A página deixou de existir (ex.: o último item dela foi excluído): volta uma.
      if ((error as ApiErrorResponse).status === 404 && page > 1) {
        setPage((p) => Math.max(1, p - 1));
        return;
      }
      setErro((error as Error).message || 'Tente de novo em instantes.');
    } finally {
      if (seq === seqRef.current) setLoading(false);
    }
  }, [statusFilter, termoBuscado, page, pageSize]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleTableChange = (pagination: TablePaginationConfig): void => {
    const novoTamanho = pagination.pageSize ?? pageSize;
    setPage(novoTamanho !== pageSize ? 1 : (pagination.current ?? 1));
    setPageSize(novoTamanho);
  };

  const handleDelete = useCallback(async (id: ID): Promise<void> => {
    try {
      await deleteSolicitacao(id);
      message.success('Solicitação excluída com sucesso!');
      // A linha (e o botão que tinha o foco) sai: o foco vai para a lista, e não para o body.
      listaRef.current?.focus();
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

  // Ação destrutiva: cita a solicitação e começa no Cancelar (ux-principios).
  const confirmarExclusao = useCallback((record: Solicitacao): void => {
    const quando = formatFortaleza(record.inicio, 'DD/MM/YYYY HH:mm');
    Modal.confirm({
      title: 'Excluir solicitação?',
      content: `${quando} · ${record.municipio_nome || 'sem município'} · ${record.projeto_nome || 'sem projeto'}. Esta ação não pode ser desfeita.`,
      okText: 'Sim, excluir',
      okType: 'danger',
      cancelText: 'Cancelar',
      autoFocusButton: 'cancel',
      onOk: () => handleDelete(record.id),
    });
  }, [handleDelete]);

  // Sem rolagem horizontal (padrão responsivo): sempre na linha a data, o status e as ações; o
  // município também (no celular, junto da data). O resto sobe por largura e, abaixo dela, vai
  // para a linha expandida.
  const columns: ColunaResponsiva<Solicitacao>[] = useMemo(() => [
    {
      title: 'Data/Hora',
      dataIndex: 'inicio',
      key: 'inicio',
      // No celular, a coluna leva também o município: fica com a largura que sobra.
      ...(acoesCompactas ? {} : { width: 112 }),
      render: (_, record) => (
        <>
          {formatFortaleza(record.inicio, 'DD/MM/YYYY')}
          <br />
          <Text type="secondary">{formatFortaleza(record.inicio, 'HH:mm')}</Text>
          {acoesCompactas ? (
            <>
              <br />
              <Text className="min-w-0 max-w-full break-words">{record.municipio_nome || '-'}</Text>
            </>
          ) : null}
        </>
      ),
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio',
      responsive: VISIVEL_A_PARTIR.sm,
      render: (_, record) => <Text className="min-w-0 max-w-full break-words">{record.municipio_nome || '-'}</Text>,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      responsive: VISIVEL_A_PARTIR.md,
      ellipsis: true,
      render: (_, record) => record.projeto_nome || '-',
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo_evento_nome',
      key: 'tipo_evento',
      responsive: VISIVEL_A_PARTIR.xl,
      ellipsis: true,
      render: (_, record) => record.tipo_evento_nome || '-',
    },
    {
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      responsive: VISIVEL_A_PARTIR.xl,
      // Nome do formador (inclui convidados "que saíram" via guest_nome — sem FK). Ver utils/participants.
      render: (_, record) => formadoresLabel(record.participations) || '-',
      ellipsis: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 104,
      render: (_, record) => (
        <Space direction="vertical" size={4}>
          <Tag
            color={STATUS_COLORS[record.status]}
            style={{ marginInlineEnd: 0, color: TEXTO_DA_TAG[STATUS_COLORS[record.status]] }}
          >
            {STATUS_LABELS[record.status] || record.status}
          </Tag>
          {record.gcal_status === ('PUBLISHED' as GCalStatus) ? (
            <Tag color="blue" style={{ marginInlineEnd: 0 }}>Na agenda</Tag>
          ) : null}
        </Space>
      ),
    },
    {
      title: 'Reunião',
      dataIndex: 'meet_link',
      key: 'meet_link',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 200,
      render: (_, record) => <MeetLink href={record.meet_link} />,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: larguraAcoesLinha(2, acoesCompactas),
      render: (_, record) => {
        const { podeEditar, podeExcluir, motivos } = permissoesDaLinha(record);
        const acoes: AcaoDaLinha[] = [];
        if (podeEditar) {
          acoes.push({
            chave: 'editar',
            rotulo: 'Editar',
            icone: <EditOutlined />,
            onClick: () => void navigate(`/solicitacoes/${record.id}/editar`),
          });
        }
        if (podeExcluir) {
          acoes.push({
            chave: 'excluir',
            rotulo: 'Excluir',
            icone: <DeleteOutlined />,
            onClick: () => confirmarExclusao(record),
            perigo: true,
          });
        }
        if (motivos.length > 0) {
          const titulo = !podeEditar && !podeExcluir
            ? 'Por que não dá para editar nem excluir'
            : !podeEditar
              ? 'Por que não dá para editar'
              : 'Por que não dá para excluir';
          acoes.push({
            chave: 'motivo',
            rotulo: titulo,
            icone: <InfoCircleOutlined />,
            onClick: () => {
              Modal.info({ title: `${titulo}?`, content: motivos.join(' '), okText: 'Entendi' });
            },
          });
        }
        return <AcoesLinha compacto={acoesCompactas} alvo={nomeDaSolicitacao(record)} acoes={acoes} />;
      },
    },
  ], [acoesCompactas, confirmarExclusao, navigate]);

  return (
    <section className="p-6" aria-labelledby="minhas-solicitacoes-title">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Header semantico */}
          <header className="flex flex-wrap justify-between items-center gap-3">
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
            <Space wrap>
              <Select
                value={statusFilter}
                onChange={(valor: SolicitacaoStatus | '') => {
                  setStatusFilter(valor);
                  setPage(1);
                }}
                style={{ width: 200, maxWidth: '100%' }}
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
                onChange={(e: ChangeEvent<HTMLInputElement>) => {
                  setSearchTerm(e.target.value);
                  setPage(1);
                }}
                // Enter ou o botão buscam na hora, sem esperar.
                onSearch={(valor: string) => {
                  setTermoBuscado(valor);
                  setPage(1);
                }}
                enterButton={<SearchOutlined />}
                style={{ width: 300, maxWidth: '100%' }}
                allowClear
                aria-label="Buscar solicitações"
              />
            </Space>
          </nav>

          {/* Tabela. tabIndex -1: recebe o foco depois de excluir (fora do Tab). */}
          <section aria-label="Lista de solicitações" ref={listaRef} tabIndex={-1}>
            <ResponsiveTable<Solicitacao>
              columns={columns}
              dataSource={rows}
              loading={loading}
              rowKey="id"
              nomeDaLinha={nomeDaSolicitacao}
              erro={erro}
              onTentarDeNovo={() => void loadData()}
              onChange={handleTableChange}
              pagination={{
                current: page,
                pageSize,
                total,
                showSizeChanger: true,
                pageSizeOptions: ['20', '50', '100'],
                showTotal: (totalCount) => `Total: ${totalCount} solicitações`,
              }}
            />
          </section>
        </Space>
      </Card>
    </section>
  );
}
