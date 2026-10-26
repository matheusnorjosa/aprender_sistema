/**
 * Column definitions for DATRegistrosPage
 * Issue #303: Split large DATModule pages
 */

import { Tag, Typography, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { ETAPA_STATUS_OPTIONS } from './constants';
import { renderStatusIcon } from './helpers';
import type { ID } from '../../../types';
import { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../../components/AcoesLinha';

const { Text } = Typography;

/**
 * DAT registro record interface
 */
export interface DATRegistroRecord {
  id: ID;
  municipio?: number;
  municipio_nome: string;
  municipio_uf: string;
  projeto_geral?: number;
  projeto_geral_nome?: string;
  projeto?: number;
  projeto_nome?: string;
  ano?: number;
  aluno_qtde?: number;
  professor_qtde?: number;
  reuniao_dat?: string;
  turma_formar_id?: string;
  nr_codigos?: number;
  chaves_inscricao_status?: string;
  envio_codigos_status?: string;
  obs_formar?: string;
  usa_avaliar?: boolean;
  alunos_recebidos_status?: string;
  alunos_validados_status?: string;
  alunos_importados_status?: string;
  obs_avaliar?: string;
  [key: string]: unknown;
}

/**
 * Column handlers interface
 */
export interface ColumnHandlers {
  onEdit: (record: DATRegistroRecord) => void;
  onDelete: (record: DATRegistroRecord) => void;
  /** Celular (abaixo de sm): o projeto vai junto do município e as ações para o menu. */
  compacto?: boolean;
}

/** Quem a linha representa (a listagem é por ano): nomeia as ações e o botão de expandir. */
export function nomeDoRegistro(record: DATRegistroRecord): string {
  return `${record.municipio_nome} - ${record.municipio_uf} · ${record.projeto_nome ?? '-'} · ${record.ano ?? 'ano pendente'}`;
}

/**
 * Creates column definitions for DAT registros table
 * @param handlers - Event handlers object
 * @returns Column definitions
 *
 * Sem rolagem horizontal (padrão responsivo, item 38): sempre na linha o município (com o projeto,
 * no celular), o ano e as ações; o resto sobe por largura e, abaixo dela, vai para a linha
 * expandida. Observações e as etapas de detalhe só entram na linha a partir de xxl.
 */
export function getColumns({ onEdit, onDelete, compacto = false }: ColumnHandlers): ColunaResponsiva<DATRegistroRecord>[] {
  return [
    // Dados Básicos
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      render: (_, record) => (
        <>
          <Text strong>
            {record.municipio_nome} - {record.municipio_uf}
          </Text>
          {compacto ? (
            <>
              <br />
              <Text type="secondary" className="break-words">{record.projeto_nome || '-'}</Text>
            </>
          ) : null}
        </>
      ),
    },
    {
      title: 'Coleção',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto_geral',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 150,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto',
      responsive: VISIVEL_A_PARTIR.sm,
      ellipsis: true,
    },
    {
      // A listagem é POR ANO (split fan-out). Sem esta coluna as linhas por-ano
      // do mesmo município+projeto pareciam duplicatas. `ano` nulo = bucket de
      // compras ainda não classificadas por ano (mostra "Pendente").
      title: 'Ano',
      dataIndex: 'ano',
      key: 'ano',
      width: 80,
      align: 'center',
      render: (val: number | undefined) =>
        val ? <Text strong>{val}</Text> : <Text type="secondary">Pendente</Text>,
    },
    {
      title: 'Alunos',
      dataIndex: 'aluno_qtde',
      key: 'aluno_qtde',
      responsive: VISIVEL_A_PARTIR.lg,
      width: 80,
      align: 'right',
      render: (val: number | undefined) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Profs.',
      dataIndex: 'professor_qtde',
      key: 'professor_qtde',
      responsive: VISIVEL_A_PARTIR.xl,
      width: 80,
      align: 'right',
      render: (val: number | undefined) => val?.toLocaleString('pt-BR') || '-',
    },
    // Detalhes FORMAR
    {
      title: 'Reunião DAT',
      dataIndex: 'reuniao_dat',
      key: 'reuniao_dat',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 110,
      render: (val: string | undefined) => (val ? dayjs(val).format('DD/MM/YYYY') : '-'),
    },
    {
      title: 'ID Turma',
      dataIndex: 'turma_formar_id',
      key: 'turma_formar_id',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 100,
      render: (val: string | undefined) =>
        val ? (
          <Text code className="text-blue-500">
            {val}
          </Text>
        ) : (
          '-'
        ),
    },
    {
      title: 'Status Turma',
      dataIndex: 'turma_formar_status',
      key: 'turma_formar_status',
      responsive: VISIVEL_A_PARTIR.md,
      width: 100,
      render: (status: string | undefined) => {
        if (!status) return <Text type="secondary">-</Text>;
        const map: Record<string, { color: string; label: string }> = {
          criada: { color: 'green', label: 'Criada' },
          pendente: { color: 'default', label: 'Pendente' },
          erro: { color: 'red', label: 'Erro' },
        };
        const it = map[status];
        return <Tag color={it?.color ?? 'default'}>{it?.label ?? status}</Tag>;
      },
    },
    {
      title: 'Códs',
      dataIndex: 'nr_codigos',
      key: 'nr_codigos',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 70,
      align: 'center',
      render: (val: number | undefined) => (val ? <Tag>{val}</Tag> : '-'),
    },
    {
      title: 'Chaves',
      dataIndex: 'chaves_inscricao_status',
      key: 'chaves',
      responsive: VISIVEL_A_PARTIR.xl,
      width: 100,
      render: (status: string | undefined) => {
        if (!status) return <Text type="secondary">-</Text>;
        // M16-08: `erro` e `nao_aplicavel` faltavam nos mapas -> Tag vazia. Fallback mostra o
        // valor cru em vez de sumir com o dado.
        const colors: Record<string, string> = {
          concluido: 'green',
          em_andamento: 'gold',
          pendente: 'default',
          nao_aplicavel: 'default',
          erro: 'red',
        };
        const labels: Record<string, string> = {
          concluido: 'Geradas',
          em_andamento: 'Pend.',
          pendente: 'Pend.',
          nao_aplicavel: 'N/A',
          erro: 'Erro',
        };
        return <Tag color={colors[status] ?? 'default'}>{labels[status] ?? status}</Tag>;
      },
    },
    {
      title: 'Envio',
      dataIndex: 'envio_codigos_status',
      key: 'envio',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 70,
      align: 'center',
      render: (status: string | undefined) => (
        <Tooltip title={ETAPA_STATUS_OPTIONS.find((s) => s.value === status)?.label || status}>
          {renderStatusIcon(status)}
        </Tooltip>
      ),
    },
    {
      title: 'Obs. FORMAR',
      dataIndex: 'obs_formar',
      key: 'obs_formar',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 150,
      ellipsis: { showTitle: false },
      render: (val: string | undefined) => (
        <Tooltip title={val}>
          <Text type="secondary">{val || '-'}</Text>
        </Tooltip>
      ),
    },
    // Detalhes AVALIAR
    {
      title: 'Usa AVALIAR',
      dataIndex: 'usa_avaliar',
      key: 'usa_avaliar',
      responsive: VISIVEL_A_PARTIR.lg,
      width: 100,
      align: 'center',
      render: (val: boolean | undefined) =>
        val ? <Tag color="green">SIM</Tag> : <Tag color="default">NÃO</Tag>,
    },
    {
      title: 'Recebidos',
      dataIndex: 'alunos_recebidos_status',
      key: 'recebidos',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 90,
      align: 'center',
      render: (status: string | undefined) => renderStatusIcon(status),
    },
    {
      title: 'Validados',
      dataIndex: 'alunos_validados_status',
      key: 'validados',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 90,
      align: 'center',
      render: (status: string | undefined) => renderStatusIcon(status),
    },
    {
      title: 'Importados',
      dataIndex: 'alunos_importados_status',
      key: 'importados',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 90,
      align: 'center',
      render: (status: string | undefined) => renderStatusIcon(status),
    },
    {
      title: 'Obs. AVALIAR',
      dataIndex: 'obs_avaliar',
      key: 'obs_avaliar',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 150,
      ellipsis: { showTitle: false },
      render: (val: string | undefined) => (
        <Tooltip title={val}>
          <Text type="secondary">{val || '-'}</Text>
        </Tooltip>
      ),
    },
    // Ações
    {
      title: 'Ações',
      key: 'acoes',
      width: larguraAcoesLinha(2, compacto),
      render: (_, record) => (
        <AcoesLinha
          compacto={compacto}
          alvo={nomeDoRegistro(record)}
          acoes={[
            { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: () => onEdit(record) },
            { chave: 'excluir', rotulo: 'Excluir', icone: <DeleteOutlined />, onClick: () => onDelete(record), perigo: true },
          ]}
        />
      ),
    },
  ];
}
