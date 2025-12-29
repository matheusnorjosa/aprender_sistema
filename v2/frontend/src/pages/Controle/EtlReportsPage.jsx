/**
 * Página de Relatórios ETL - Observabilidade de importações
 *
 * Features:
 * - Listagem de relatórios ETL (out_etl/) com metadados
 * - Filtros: tipo de arquivo, limite de resultados
 * - Download individual de relatórios
 * - Formatação de tamanho (bytes → KB/MB) e data (ISO → local)
 *
 * Permissions: Controle ou Superintendência
 * Fase 5 - Desligamento gradual de planilhas
 */

import { useState, useEffect, useCallback } from 'react';
import { Table, Select, InputNumber, Button, Tag, Space, Alert, Spin } from 'antd';
import {
  FileTextOutlined,
  FileExcelOutlined,
  FileUnknownOutlined,
  DownloadOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { listLatestReports, getReportDownloadUrl } from '../../api/etl';
import logger from '../../utils/logger';

const { Option } = Select;

/**
 * Formatar tamanho em bytes para formato legível (KB, MB)
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * Ícone por tipo de arquivo
 */
function getFileIcon(kind) {
  switch (kind) {
    case 'json':
      return <FileTextOutlined style={{ color: '#52c41a' }} />;
    case 'csv':
      return <FileExcelOutlined style={{ color: '#1890ff' }} />;
    case 'txt':
      return <FileTextOutlined style={{ color: '#8c8c8c' }} />;
    default:
      return <FileUnknownOutlined style={{ color: '#d9d9d9' }} />;
  }
}

/**
 * Tag de tipo de arquivo com cor
 */
function FileTypeTag({ kind }) {
  const colors = {
    json: 'green',
    csv: 'blue',
    txt: 'default',
    other: 'default',
  };

  return <Tag color={colors[kind] || 'default'}>{kind.toUpperCase()}</Tag>;
}

export default function EtlReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [count, setCount] = useState(0);

  // Filtros
  const [limit, setLimit] = useState(20);
  const [filterKind, setFilterKind] = useState('all'); // all, json, csv, txt, other

  /**
   * Calcular limite efetivo (garantir entre 1-100, fallback 20)
   */
  const effectiveLimit = Math.max(1, Math.min(limit ?? 20, 100));

  /**
   * Buscar relatórios do backend
   */
  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listLatestReports(effectiveLimit);
      setCount(data.count);
      setReports(data.reports || []);
    } catch (err) {
      logger.error('Erro ao buscar relatórios ETL:', err);

      // Tratar erro 403 (permissão)
      if (err.message.includes('403') || err.message.includes('Forbidden')) {
        setError(
          'Você não tem permissão para acessar relatórios ETL. Apenas grupos Controle e Superintendência podem visualizar.'
        );
      } else {
        setError(err.message || 'Erro ao carregar relatórios. Tente novamente.');
      }
    } finally {
      setLoading(false);
    }
  }, [effectiveLimit]);

  /**
   * Carregar ao montar e quando limit mudar
   */
  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  /**
   * Filtrar reports por tipo (client-side)
   */
  const filteredReports = filterKind === 'all'
    ? reports
    : reports.filter((r) => r.kind === filterKind);

  /**
   * Colunas da tabela
   */
  const columns = [
    {
      title: 'Arquivo',
      dataIndex: 'filename',
      key: 'filename',
      width: '40%',
      render: (filename, record) => (
        <Space>
          {getFileIcon(record.kind)}
          <span className="font-mono text-sm">{filename}</span>
        </Space>
      ),
    },
    {
      title: 'Tipo',
      dataIndex: 'kind',
      key: 'kind',
      width: '10%',
      render: (kind) => <FileTypeTag kind={kind} />,
    },
    {
      title: 'Tamanho',
      dataIndex: 'size_bytes',
      key: 'size',
      width: '15%',
      render: (bytes) => <span className="text-gray-600">{formatBytes(bytes)}</span>,
    },
    {
      title: 'Data/Hora',
      dataIndex: 'mtime_iso',
      key: 'mtime',
      width: '20%',
      render: (isoDate) => (
        <span className="text-gray-600">
          {dayjs(isoDate).format('DD/MM/YYYY HH:mm')}
        </span>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: '15%',
      render: (_, record) => (
        <Button
          type="link"
          icon={<DownloadOutlined />}
          href={getReportDownloadUrl(record.path_rel)}
          target="_blank"
          rel="noopener noreferrer"
        >
          Download
        </Button>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      {/* Título */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Relatórios ETL</h1>
        <p className="text-sm text-gray-600 mt-1">
          Visualize e baixe relatórios gerados pelas importações de dados (acompanhamento, deslocamento, ações, etc.)
        </p>
      </div>

      {/* Filtros */}
      <div className="bg-white p-4 rounded-lg shadow space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">Filtros</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Filtro: Tipo de Arquivo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de Arquivo
            </label>
            <Select
              value={filterKind}
              onChange={setFilterKind}
              className="w-full"
              placeholder="Selecione o tipo"
            >
              <Option value="all">Todos</Option>
              <Option value="json">JSON</Option>
              <Option value="csv">CSV</Option>
              <Option value="txt">TXT</Option>
              <Option value="other">Outro</Option>
            </Select>
          </div>

          {/* Filtro: Limite */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Limite de Resultados
            </label>
            <InputNumber
              min={1}
              max={100}
              value={limit}
              onChange={(value) => setLimit(value ?? 20)}
              className="w-full"
              placeholder="1-100"
            />
          </div>

          {/* Botão Atualizar */}
          <div className="flex items-end">
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={fetchReports}
              loading={loading}
              className="w-full"
            >
              Atualizar
            </Button>
          </div>
        </div>
      </div>

      {/* Erro */}
      {error && (
        <Alert
          message="Erro ao carregar relatórios"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
        />
      )}

      {/* Contador */}
      {!error && !loading && (
        <div className="text-sm text-gray-600">
          Exibindo {filteredReports.length} de {count} relatórios
          {filterKind !== 'all' && ` (filtrado por tipo: ${filterKind.toUpperCase()})`}
        </div>
      )}

      {/* Tabela */}
      <div className="bg-white rounded-lg shadow">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Spin size="large" />
          </div>
        ) : (
          <Table
            dataSource={filteredReports}
            columns={columns}
            rowKey="filename"
            pagination={{
              pageSize: Math.min(effectiveLimit, filteredReports.length || effectiveLimit),
              showSizeChanger: false,
              showTotal: (total) => `Total: ${total} arquivos`,
            }}
            locale={{
              emptyText: filterKind === 'all'
                ? 'Nenhum relatório ETL encontrado. Execute comandos de importação para gerar relatórios.'
                : `Nenhum relatório do tipo ${filterKind.toUpperCase()} encontrado.`,
            }}
          />
        )}
      </div>

      {/* Ajuda */}
      <Alert
        message="Como usar esta página"
        description={
          <ul className="list-disc list-inside text-sm space-y-1">
            <li>Os relatórios são gerados automaticamente pelos comandos ETL (python manage.py etl_upsert_*, etl_import_*)</li>
            <li>Arquivos JSON contêm dados estruturados (resultados de importação, erros, etc.)</li>
            <li>Arquivos CSV podem ser abertos no Excel para análise</li>
            <li>Use o filtro de tipo para visualizar apenas relatórios específicos</li>
            <li>Clique em "Download" para baixar um relatório individual</li>
          </ul>
        }
        type="info"
        showIcon
        className="mt-4"
      />
    </div>
  );
}
