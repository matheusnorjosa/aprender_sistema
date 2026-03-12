/**
 * Column definitions for CadastrosPage
 * Issue #303: Split large DATModule pages
 */

import { Space, Tag, Typography, Tooltip, Button, Steps } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { PLATAFORMAS } from './constants';
import { renderStatusIcon, getStepStatus, getCurrentStep } from './helpers';
import type { CadastroRecord } from './types';

const { Text } = Typography;

/**
 * Column handlers interface
 */
export interface ColumnHandlers {
  onQuickStatusUpdate: (record: CadastroRecord, field: string, newStatus: string) => void;
  onEdit: (record: CadastroRecord) => void;
  onDelete: (record: CadastroRecord) => void;
}

/**
 * Creates column definitions for FORMAR platform
 * @param handlers - Event handlers object
 * @returns Column definitions
 */
export function getColumnsFormar({ onQuickStatusUpdate, onEdit, onDelete }: ColumnHandlers): ColumnsType<CadastroRecord> {
  return [
    {
      title: 'Projeto',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto',
      width: 120,
      fixed: 'left',
      render: (nome: string) => <Tag color="blue">{nome}</Tag>,
    },
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      width: 180,
      fixed: 'left',
      render: (_, record) => (
        <Text strong>
          {record.municipio_nome} - {record.uf}
        </Text>
      ),
    },
    {
      title: 'Alunos',
      dataIndex: 'quantidade_alunos',
      key: 'alunos',
      width: 80,
      align: 'right',
      render: (val: number | undefined) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Profs.',
      dataIndex: 'quantidade_professores',
      key: 'professores',
      width: 80,
      align: 'right',
      render: (val: number | undefined) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Códs',
      dataIndex: 'quantidade_codigos',
      key: 'codigos',
      width: 70,
      align: 'center',
      render: (val: number | undefined) => (val ? <Tag>{val}</Tag> : '-'),
    },
    {
      title: 'Criação Curso',
      key: 'criacao_curso',
      width: 110,
      align: 'center',
      render: (_, record) => (
        <Tooltip title="Clique para alterar status">
          <div
            className="cursor-pointer"
            onClick={() => {
              const newStatus =
                record.status_criacao_curso === 'concluido' ? 'pendente' : 'concluido';
              onQuickStatusUpdate(record, 'criacao_curso', newStatus);
            }}
          >
            {renderStatusIcon(record.status_criacao_curso)}
            <div className="text-[10px] text-gray-400">
              {record.data_criacao_curso
                ? dayjs(record.data_criacao_curso).format('DD/MM')
                : '-'}
            </div>
          </div>
        </Tooltip>
      ),
    },
    {
      title: 'Chaves',
      key: 'chaves',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Tooltip title="Clique para alterar status">
          <div
            className="cursor-pointer"
            onClick={() => {
              const newStatus =
                record.status_chaves === 'concluido' ? 'pendente' : 'concluido';
              onQuickStatusUpdate(record, 'chaves', newStatus);
            }}
          >
            {renderStatusIcon(record.status_chaves)}
            <div className="text-[10px] text-gray-400">
              {record.data_chaves ? dayjs(record.data_chaves).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
      ),
    },
    {
      title: 'Instruções',
      key: 'instrucoes',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Tooltip title="Clique para alterar status">
          <div
            className="cursor-pointer"
            onClick={() => {
              const newStatus =
                record.status_instrucoes === 'concluido' ? 'pendente' : 'concluido';
              onQuickStatusUpdate(record, 'instrucoes', newStatus);
            }}
          >
            {renderStatusIcon(record.status_instrucoes)}
            <div className="text-[10px] text-gray-400">
              {record.data_instrucoes ? dayjs(record.data_instrucoes).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
      ),
    },
    {
      title: 'Envio',
      key: 'envio',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Tooltip title="Clique para alterar status">
          <div
            className="cursor-pointer"
            onClick={() => {
              const newStatus =
                record.status_envio === 'concluido' ? 'pendente' : 'concluido';
              onQuickStatusUpdate(record, 'envio', newStatus);
            }}
          >
            {renderStatusIcon(record.status_envio)}
            <div className="text-[10px] text-gray-400">
              {record.data_envio ? dayjs(record.data_envio).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
      ),
    },
    {
      title: 'Link',
      key: 'link',
      width: 60,
      align: 'center',
      render: (_, record) =>
        record.link_planilha ? (
          <Tooltip title="Abrir planilha">
            <Button
              type="link"
              size="small"
              icon={<LinkOutlined />}
              href={record.link_planilha}
              target="_blank"
              aria-label="Abrir planilha externa"
            />
          </Tooltip>
        ) : (
          '-'
        ),
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Editar">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
              aria-label="Editar cadastro"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record)}
              aria-label="Excluir cadastro"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];
}

/**
 * Creates column definitions for AVALIAR platform
 * @param handlers - Event handlers object
 * @returns Column definitions
 */
export function getColumnsAvaliar({ onQuickStatusUpdate, onEdit, onDelete }: ColumnHandlers): ColumnsType<CadastroRecord> {
  return [
    {
      title: 'Projeto',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto',
      width: 120,
      fixed: 'left',
      render: (nome: string) => <Tag color="green">{nome}</Tag>,
    },
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      width: 180,
      fixed: 'left',
      render: (_, record) => (
        <Text strong>
          {record.municipio_nome} - {record.uf}
        </Text>
      ),
    },
    {
      title: 'Recebidos',
      key: 'recebidos',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              className="cursor-pointer"
              onClick={() => {
                const newStatus =
                  record.status_recebidos === 'concluido' ? 'pendente' : 'concluido';
                onQuickStatusUpdate(record, 'recebidos', newStatus);
              }}
            >
              {renderStatusIcon(record.status_recebidos)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_recebidos || 0}</Text>
        </Space>
      ),
    },
    {
      title: 'Validados',
      key: 'validados',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              className="cursor-pointer"
              onClick={() => {
                const newStatus =
                  record.status_validados === 'concluido' ? 'pendente' : 'concluido';
                onQuickStatusUpdate(record, 'validados', newStatus);
              }}
            >
              {renderStatusIcon(record.status_validados)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_validados || 0}</Text>
        </Space>
      ),
    },
    {
      title: 'Importados',
      key: 'importados',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              className="cursor-pointer"
              onClick={() => {
                const newStatus =
                  record.status_importados === 'concluido' ? 'pendente' : 'concluido';
                onQuickStatusUpdate(record, 'importados', newStatus);
              }}
            >
              {renderStatusIcon(record.status_importados)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_importados || 0}</Text>
        </Space>
      ),
    },
    {
      title: 'Progresso',
      key: 'progresso',
      width: 300,
      render: (_, record) => {
        const etapas = PLATAFORMAS.AVALIAR.etapas;
        const current = getCurrentStep(record, etapas);

        return (
          <Steps
            size="small"
            current={current}
            items={etapas.map((etapa) => ({
              title: etapa.label,
              status: getStepStatus(record[`status_${etapa.key}` as keyof CadastroRecord] as string | undefined),
            }))}
          />
        );
      },
    },
    {
      title: 'Link',
      key: 'link',
      width: 60,
      align: 'center',
      render: (_, record) =>
        record.link_plataforma ? (
          <Tooltip title="Abrir plataforma">
            <Button
              type="link"
              size="small"
              icon={<LinkOutlined />}
              href={record.link_plataforma}
              target="_blank"
              aria-label="Abrir plataforma externa"
            />
          </Tooltip>
        ) : (
          '-'
        ),
    },
    {
      title: 'Ações',
      key: 'acoes',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Editar">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
              aria-label="Editar avaliação"
            />
          </Tooltip>
          <Tooltip title="Excluir">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(record)}
              aria-label="Excluir avaliação"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];
}
