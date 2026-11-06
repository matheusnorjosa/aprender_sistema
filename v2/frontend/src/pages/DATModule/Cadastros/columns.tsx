/**
 * Column definitions for CadastrosPage
 * Issue #303: Split large DATModule pages
 *
 * Sem rolagem horizontal (G30, padrão responsivo): colunas do ResponsiveTable. Sempre na linha o
 * município (identidade) e as ações (AcoesLinha; no celular, o menu "Mais ações"); a Coleção sobe
 * a partir de sm, as etapas de md, o link de lg e as contagens (FORMAR) e o Progresso (AVALIAR) só
 * de xxl. O que some vai para a linha expandida, onde as etapas continuam clicáveis.
 */

import { Space, Tag, Typography, Tooltip, Button, Steps } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../../components/AcoesLinha';
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

/** Quem a linha representa: nomeia o expandir e as ações ("Editar: Fortaleza - CE · Coleção X"). */
export function nomeDoCadastro(record: CadastroRecord): string {
  return `${record.municipio_nome} - ${record.uf} · ${record.projeto_geral_nome}`;
}

/** A coleção pode ter nome longo: a tag quebra linha em vez de passar da célula. */
const TAG_QUEBRA = { whiteSpace: 'normal', overflowWrap: 'anywhere' } as const;

function colunaAcoes(
  { onEdit, onDelete }: ColumnHandlers,
  acoesCompactas: boolean,
): ColunaResponsiva<CadastroRecord> {
  return {
    title: 'Ações',
    key: 'acoes',
    width: larguraAcoesLinha(2, acoesCompactas),
    render: (_, record) => (
      <AcoesLinha
        compacto={acoesCompactas}
        alvo={nomeDoCadastro(record)}
        acoes={[
          { chave: 'editar', rotulo: 'Editar', icone: <EditOutlined />, onClick: () => onEdit(record) },
          {
            chave: 'excluir',
            rotulo: 'Excluir',
            icone: <DeleteOutlined />,
            onClick: () => onDelete(record),
            perigo: true,
          },
        ]}
      />
    ),
  };
}

/**
 * Creates column definitions for FORMAR platform
 * @param handlers - Event handlers object
 * @returns Column definitions
 */
export function getColumnsFormar(handlers: ColumnHandlers, acoesCompactas = false): ColunaResponsiva<CadastroRecord>[] {
  const { onQuickStatusUpdate } = handlers;
  return [
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      render: (_, record) => (
        <Text strong>
          {record.municipio_nome} - {record.uf}
        </Text>
      ),
    },
    {
      title: 'Coleção',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto',
      responsive: VISIVEL_A_PARTIR.sm,
      render: (nome: string) => <Tag color="blue" style={TAG_QUEBRA}>{nome}</Tag>,
    },
    {
      title: 'Alunos',
      dataIndex: 'quantidade_alunos',
      key: 'alunos',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 80,
      align: 'right',
      render: (val: number | undefined) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Profs.',
      dataIndex: 'quantidade_professores',
      key: 'professores',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 80,
      align: 'right',
      render: (val: number | undefined) => val?.toLocaleString('pt-BR') || '-',
    },
    {
      title: 'Códs',
      dataIndex: 'quantidade_codigos',
      key: 'codigos',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 70,
      align: 'center',
      render: (val: number | undefined) => (val ? <Tag>{val}</Tag> : '-'),
    },
    {
      title: 'Criação Curso',
      key: 'criacao_curso',
      responsive: VISIVEL_A_PARTIR.md,
      width: 96,
      align: 'center',
      render: (_, record) => {
        const handleToggle = () => {
          const newStatus =
            record.status_criacao_curso === 'concluido' ? 'pendente' : 'concluido';
          onQuickStatusUpdate(record, 'criacao_curso', newStatus);
        };
        return (
        <Tooltip title="Clique para alterar status">
          <div
            className="cursor-pointer"
            role="button"
            aria-label="Criação Curso: clique para alterar status"
            tabIndex={0}
            onClick={handleToggle}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleToggle();
              }
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
        );
      },
    },
    {
      title: 'Chaves',
      key: 'chaves',
      responsive: VISIVEL_A_PARTIR.md,
      width: 96,
      align: 'center',
      render: (_, record) => {
        const handleToggle = () => {
          const newStatus =
            record.status_chaves === 'concluido' ? 'pendente' : 'concluido';
          onQuickStatusUpdate(record, 'chaves', newStatus);
        };
        return (
        <Tooltip title="Clique para alterar status">
          <div
            className="cursor-pointer"
            role="button"
            aria-label="Chaves: clique para alterar status"
            tabIndex={0}
            onClick={handleToggle}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleToggle();
              }
            }}
          >
            {renderStatusIcon(record.status_chaves)}
            <div className="text-[10px] text-gray-400">
              {record.data_chaves ? dayjs(record.data_chaves).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
        );
      },
    },
    {
      title: 'Instruções',
      key: 'instrucoes',
      responsive: VISIVEL_A_PARTIR.md,
      width: 96,
      align: 'center',
      render: (_, record) => {
        const handleToggle = () => {
          const newStatus =
            record.status_instrucoes === 'concluido' ? 'pendente' : 'concluido';
          onQuickStatusUpdate(record, 'instrucoes', newStatus);
        };
        return (
        <Tooltip title="Clique para alterar status">
          <div
            className="cursor-pointer"
            role="button"
            aria-label="Instruções: clique para alterar status"
            tabIndex={0}
            onClick={handleToggle}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleToggle();
              }
            }}
          >
            {renderStatusIcon(record.status_instrucoes)}
            <div className="text-[10px] text-gray-400">
              {record.data_instrucoes ? dayjs(record.data_instrucoes).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
        );
      },
    },
    {
      title: 'Envio',
      key: 'envio',
      responsive: VISIVEL_A_PARTIR.md,
      width: 96,
      align: 'center',
      render: (_, record) => {
        const handleToggle = () => {
          const newStatus =
            record.status_envio === 'concluido' ? 'pendente' : 'concluido';
          onQuickStatusUpdate(record, 'envio', newStatus);
        };
        return (
        <Tooltip title="Clique para alterar status">
          <div
            className="cursor-pointer"
            role="button"
            aria-label="Envio: clique para alterar status"
            tabIndex={0}
            onClick={handleToggle}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleToggle();
              }
            }}
          >
            {renderStatusIcon(record.status_envio)}
            <div className="text-[10px] text-gray-400">
              {record.data_envio ? dayjs(record.data_envio).format('DD/MM') : '-'}
            </div>
          </div>
        </Tooltip>
        );
      },
    },
    {
      title: 'Link',
      key: 'link',
      responsive: VISIVEL_A_PARTIR.lg,
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
    colunaAcoes(handlers, acoesCompactas),
  ];
}

/**
 * Creates column definitions for AVALIAR platform
 * @param handlers - Event handlers object
 * @returns Column definitions
 */
export function getColumnsAvaliar(handlers: ColumnHandlers, acoesCompactas = false): ColunaResponsiva<CadastroRecord>[] {
  const { onQuickStatusUpdate } = handlers;
  return [
    {
      title: 'Município - UF',
      key: 'municipio_uf',
      render: (_, record) => (
        <Text strong>
          {record.municipio_nome} - {record.uf}
        </Text>
      ),
    },
    {
      title: 'Coleção',
      dataIndex: 'projeto_geral_nome',
      key: 'projeto',
      responsive: VISIVEL_A_PARTIR.sm,
      render: (nome: string) => <Tag color="green" style={TAG_QUEBRA}>{nome}</Tag>,
    },
    {
      title: 'Recebidos',
      key: 'recebidos',
      responsive: VISIVEL_A_PARTIR.md,
      width: 96,
      render: (_, record) => {
        const handleToggle = () => {
          const newStatus =
            record.status_recebidos === 'concluido' ? 'pendente' : 'concluido';
          onQuickStatusUpdate(record, 'recebidos', newStatus);
        };
        return (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              className="cursor-pointer"
              role="button"
              aria-label="Recebidos: clique para alterar status"
              tabIndex={0}
              onClick={handleToggle}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleToggle();
                }
              }}
            >
              {renderStatusIcon(record.status_recebidos)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_recebidos || 0}</Text>
        </Space>
        );
      },
    },
    {
      title: 'Validados',
      key: 'validados',
      responsive: VISIVEL_A_PARTIR.md,
      width: 96,
      render: (_, record) => {
        const handleToggle = () => {
          const newStatus =
            record.status_validados === 'concluido' ? 'pendente' : 'concluido';
          onQuickStatusUpdate(record, 'validados', newStatus);
        };
        return (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              className="cursor-pointer"
              role="button"
              aria-label="Validados: clique para alterar status"
              tabIndex={0}
              onClick={handleToggle}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleToggle();
                }
              }}
            >
              {renderStatusIcon(record.status_validados)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_validados || 0}</Text>
        </Space>
        );
      },
    },
    {
      title: 'Importados',
      key: 'importados',
      responsive: VISIVEL_A_PARTIR.md,
      width: 96,
      render: (_, record) => {
        const handleToggle = () => {
          const newStatus =
            record.status_importados === 'concluido' ? 'pendente' : 'concluido';
          onQuickStatusUpdate(record, 'importados', newStatus);
        };
        return (
        <Space direction="vertical" size={0} align="center">
          <Tooltip title="Clique para alterar status">
            <div
              className="cursor-pointer"
              role="button"
              aria-label="Importados: clique para alterar status"
              tabIndex={0}
              onClick={handleToggle}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleToggle();
                }
              }}
            >
              {renderStatusIcon(record.status_importados)}
            </div>
          </Tooltip>
          <Text type="secondary">{record.quantidade_importados || 0}</Text>
        </Space>
        );
      },
    },
    {
      title: 'Progresso',
      key: 'progresso',
      responsive: VISIVEL_A_PARTIR.xxl,
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
      responsive: VISIVEL_A_PARTIR.lg,
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
    colunaAcoes(handlers, acoesCompactas),
  ];
}
