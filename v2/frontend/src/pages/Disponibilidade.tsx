/**
 * Página de Gerenciamento de Disponibilidade
 *
 * Permite ao usuário:
 * - Criar bloqueios de disponibilidade (Total ou Parcial)
 * - Listar seus bloqueios existentes
 * - Excluir bloqueios com status 'pendente'
 * - Importar bloqueios em massa via CSV/XLSX
 */

import { useState, useEffect, JSX } from 'react';
import { Card, Row, Col, message, Spin, Radio, Typography } from 'antd';
import type { RadioChangeEvent } from 'antd/es/radio';
import { StopOutlined, UploadOutlined } from '@ant-design/icons';
import BlockForm from '../components/BlockForm';
import MyBlocksTable from '../components/MyBlocksTable';
import ImportUploader, { ValidationResult, ApplyResult } from '../components/ImportUploader';
import { getBlocks, createBlock as apiCreateBlock, deleteBlock as apiDeleteBlock } from '../api/availability';
import { importBloqueios } from '../api/ops';
import type { ID, AvailabilityBlock, AvailabilityBlockPayload } from '../types';

const { Title, Text } = Typography;

/** View mode type */
type ViewMode = 'bloqueios' | 'importar';

/**
 * Converte resposta do backend para formato do ImportUploader.
 */
function toValidationResult(response: Record<string, unknown>): ValidationResult {
  const stats = response.stats as Record<string, unknown> | undefined;
  const pendencias = response.pendencias as Record<string, unknown[]> | undefined;

  // Converter pendencias em erros se houver usuarios ou dates nao resolvidos
  const errors: string[] = [];
  if (pendencias?.usuarios) {
    (pendencias.usuarios as Array<{ linha: number; nome: string }>).forEach((p) => {
      errors.push(`Linha ${p.linha}: Usuario nao encontrado (${p.nome})`);
    });
  }
  if (pendencias?.dates) {
    (pendencias.dates as Array<{ linha: number; erro?: string }>).forEach((p) => {
      errors.push(`Linha ${p.linha}: Data invalida${p.erro ? ` - ${p.erro}` : ''}`);
    });
  }

  return {
    stats: {
      created: (stats?.created as number) || 0,
      updated: (stats?.updated as number) || 0,
      unchanged: (stats?.unchanged as number) || 0,
    },
    errors: errors.length > 0 ? errors : undefined,
    pendencias,
  };
}

/**
 * Converte resposta do backend para ApplyResult.
 */
function toApplyResult(response: Record<string, unknown>): ApplyResult {
  const stats = response.stats as Record<string, unknown> | undefined;
  return {
    stats: {
      created: (stats?.created as number) || 0,
      updated: (stats?.updated as number) || 0,
      unchanged: (stats?.unchanged as number) || 0,
    },
  };
}

export default function Disponibilidade(): JSX.Element {
  const [viewMode, setViewMode] = useState<ViewMode>('bloqueios');
  const [blocks, setBlocks] = useState<AvailabilityBlock[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  /**
   * Carrega lista de bloqueios do usuário atual.
   */
  const fetchBlocks = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await getBlocks({ owner: 'me' });
      setBlocks(data as AvailabilityBlock[]);
    } catch (error) {
      message.error(`Erro ao carregar bloqueios: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handler para criação de novo bloqueio.
   */
  const handleCreate = async (data: AvailabilityBlockPayload): Promise<void> => {
    try {
      await apiCreateBlock(data);
      message.success('Bloqueio criado com sucesso!');
      await fetchBlocks(); // Recarregar lista
    } catch (error) {
      message.error(`Erro ao criar bloqueio: ${(error as Error).message}`);
      throw error; // Propagar erro para o form
    }
  };

  /**
   * Handler para exclusão de bloqueio.
   */
  const handleDelete = async (id: ID): Promise<void> => {
    try {
      await apiDeleteBlock(id);
      message.success('Bloqueio removido com sucesso!');
      await fetchBlocks(); // Recarregar lista
    } catch (error) {
      message.error(`Erro ao remover bloqueio: ${(error as Error).message}`);
    }
  };

  // Carregar bloqueios ao montar componente
  useEffect(() => {
    fetchBlocks();
  }, []);

  return (
    <section style={{ padding: '24px' }} aria-labelledby="disponibilidade-title">
      {/* Header com toggle */}
      <header style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Title level={2} style={{ marginBottom: 0 }}>
            <StopOutlined style={{ marginRight: 8 }} />
            Gerenciar Disponibilidade
          </Title>
          <Text type="secondary">
            {viewMode === 'bloqueios'
              ? 'Crie e gerencie bloqueios de disponibilidade (Total ou Parcial)'
              : 'Importe bloqueios em massa via arquivo CSV/XLSX'}
          </Text>
        </div>
        <Radio.Group
          value={viewMode}
          onChange={(e: RadioChangeEvent) => setViewMode(e.target.value)}
          buttonStyle="solid"
        >
          <Radio.Button value="bloqueios">Bloqueios</Radio.Button>
          <Radio.Button value="importar">Importar</Radio.Button>
        </Radio.Group>
      </header>

      {viewMode === 'bloqueios' ? (
        /* View: Bloqueios (criar + listar) */
        <Row gutter={[16, 16]}>
          {/* Card de Criacao */}
          <Col xs={24} lg={12}>
            <article aria-label="Criar novo bloqueio">
              <Card title="Criar Bloqueio" bordered={false}>
                <BlockForm onSubmit={handleCreate as unknown as (payload: { tipo: string; inicio: string; fim: string }) => Promise<void>} />
              </Card>
            </article>
          </Col>

          {/* Card de Listagem */}
          <Col xs={24} lg={12}>
            <article aria-label="Lista de meus bloqueios">
              <Card title="Meus Bloqueios" bordered={false}>
                {loading ? (
                  <div style={{ textAlign: 'center', padding: '40px 0' }} role="status" aria-live="polite">
                    <Spin size="large" tip="Carregando bloqueios..." />
                  </div>
                ) : (
                  <MyBlocksTable blocks={blocks as unknown as Array<{ id: number; tipo: 'T' | 'P'; inicio: string; fim: string; status: 'pendente' | 'aprovado' | 'reprovado' }>} onDelete={handleDelete} loading={loading} />
                )}
              </Card>
            </article>
          </Col>
        </Row>
      ) : (
        /* View: Importar em Massa */
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <article aria-label="Importar bloqueios em massa">
              <Card
                title={
                  <span>
                    <UploadOutlined style={{ marginRight: 8 }} />
                    Importar Bloqueios em Massa
                  </span>
                }
                bordered={false}
              >
                <ImportUploader
                  label="Selecione o arquivo"
                  description="CSV/XLSX com colunas: usuario, inicio, fim, tipo (T/P), motivo"
                  onDryRun={async (file: File) => toValidationResult(await importBloqueios(file, true) as unknown as Record<string, unknown>)}
                  onApply={async (file: File) => {
                    const result = await importBloqueios(file, false);
                    await fetchBlocks();
                    return toApplyResult(result as unknown as Record<string, unknown>);
                  }}
                />
              </Card>
            </article>
          </Col>

          {/* Card de Instruções */}
          <Col xs={24} lg={8}>
            <Card title="Formato do Arquivo" bordered={false}>
              <Text strong>Colunas obrigatórias:</Text>
              <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                <li><code>usuario</code> - Nome do formador</li>
                <li><code>inicio</code> - Data/hora início</li>
                <li><code>fim</code> - Data/hora fim</li>
                <li><code>tipo</code> - T (Total) ou P (Parcial)</li>
              </ul>
              <Text strong style={{ marginTop: 16, display: 'block' }}>Coluna opcional:</Text>
              <ul style={{ marginTop: 8, paddingLeft: 20 }}>
                <li><code>motivo</code> - Observação</li>
              </ul>
              <Text type="secondary" style={{ marginTop: 16, display: 'block', fontSize: 12 }}>
                Formatos de data aceitos: YYYY-MM-DD, DD/MM/YYYY, ISO 8601
              </Text>
            </Card>
          </Col>
        </Row>
      )}
    </section>
  );
}
