/**
 * Componente Reutilizável para Upload de Importação.
 *
 * Fluxo:
 * 1. Selecionar arquivo
 * 2. "Validar Importação" → dry-run
 * 3. Se validação OK → mostrar "Realizar Importação"
 * 4. Apply persiste no banco
 */

import { useState } from 'react';
import {
  Upload,
  Button,
  Card,
  Alert,
  Statistic,
  Row,
  Col,
  Typography,
  Space,
  Collapse,
  Tag,
  Result,
} from 'antd';
import {
  UploadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileExcelOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';

const { Text, Title } = Typography;
const { Panel } = Collapse;
const { Dragger } = Upload;

/**
 * Validation/Apply result stats
 */
export interface ImportStats {
  created?: number;
  updated?: number;
  unchanged?: number;
}

/**
 * Validation result interface
 */
export interface ValidationResult {
  stats?: ImportStats;
  errors?: string[];
  pendencias?: Record<string, unknown>;
  [key: string]: unknown;
}

/**
 * Apply result interface
 */
export interface ApplyResult {
  stats?: ImportStats;
  [key: string]: unknown;
}

/**
 * ImportUploader props interface
 */
export interface ImportUploaderProps {
  label: string;
  onDryRun: (file: File) => Promise<ValidationResult>;
  onApply: (file: File) => Promise<ApplyResult>;
  description?: string;
}

export default function ImportUploader({ label, onDryRun, onApply, description }: ImportUploaderProps): JSX.Element {
  const [file, setFile] = useState<File | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [applyResult, setApplyResult] = useState<ApplyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Estado da validação
  const isValidated = validationResult !== null && !error;
  const hasErrors = (validationResult?.errors?.length ?? 0) > 0;
  const canApply = isValidated && !hasErrors && !applyResult;

  /**
   * Reset para nova importação
   */
  const handleReset = (): void => {
    setFile(null);
    setValidationResult(null);
    setApplyResult(null);
    setError(null);
  };

  /**
   * Validar importação (dry-run)
   */
  const handleValidate = async (): Promise<void> => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setValidationResult(null);
    setApplyResult(null);

    try {
      const report = await onDryRun(file);
      setValidationResult(report);
    } catch (err) {
      const httpStatus = (err as { response?: { status?: number } }).response?.status;
      if (httpStatus === 429) {
        setError('Muitas importações em pouco tempo. Aguarde um instante e tente novamente.');
      } else {
        setError((err as Error).message || 'Erro ao validar arquivo');
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * Realizar importação (apply)
   */
  const handleApply = async (): Promise<void> => {
    if (!file) return;

    setLoadingApply(true);
    setError(null);

    try {
      const report = await onApply(file);
      setApplyResult(report);
      setValidationResult(null); // Limpar validação após apply
    } catch (err) {
      const httpStatus = (err as { response?: { status?: number } }).response?.status;
      if (httpStatus === 429) {
        setError('Muitas importações em pouco tempo. Aguarde um instante e tente novamente.');
      } else {
        setError((err as Error).message || 'Erro ao importar arquivo');
      }
    } finally {
      setLoadingApply(false);
    }
  };

  /**
   * Props do upload
   */
  const uploadProps: UploadProps = {
    accept: '.csv,.xlsx,.xls',
    maxCount: 1,
    beforeUpload: (selectedFile: File) => {
      setFile(selectedFile);
      setValidationResult(null);
      setApplyResult(null);
      setError(null);
      return false; // Prevent auto upload
    },
    onRemove: () => {
      handleReset();
    },
    fileList: file ? [{
      uid: '-1',
      name: file.name,
      status: 'done',
      size: file.size
    } as UploadFile] : [],
  };

  return (
    <Card
      title={
        <Space>
          <FileExcelOutlined />
          <span>{label}</span>
        </Space>
      }
      extra={
        (validationResult || applyResult) && (
          <Button
            icon={<ReloadOutlined />}
            onClick={handleReset}
            size="small"
          >
            Nova Importação
          </Button>
        )
      }
    >
      {/* Descrição */}
      {description && (
        <Text type="secondary" className="block mb-4">
          {description}
        </Text>
      )}

      {/* Resultado do Apply (sucesso final) */}
      {applyResult && (
        <Result
          status="success"
          title="Importação Realizada com Sucesso!"
          subTitle={
            <Space direction="vertical">
              <Text>
                <Tag color="green">{applyResult.stats?.created || 0}</Tag> registros criados
              </Text>
              <Text>
                <Tag color="blue">{applyResult.stats?.updated || 0}</Tag> registros atualizados
              </Text>
              <Text>
                <Tag>{applyResult.stats?.unchanged || 0}</Tag> registros inalterados
              </Text>
            </Space>
          }
          extra={
            <Button type="primary" onClick={handleReset}>
              Nova Importação
            </Button>
          }
        />
      )}

      {/* Fluxo de importação (quando não tem applyResult) */}
      {!applyResult && (
        <>
          {/* Step 1: Upload de arquivo */}
          <div className="mb-6">
            <Title level={5} className="mb-3">
              1. Selecione o arquivo
            </Title>
            <Dragger {...uploadProps} disabled={loading || loadingApply}>
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">
                Clique ou arraste o arquivo aqui
              </p>
              <p className="ant-upload-hint">
                Formatos aceitos: CSV, XLSX, XLS
              </p>
            </Dragger>
          </div>

          {/* Step 2: Botão de validação */}
          {file && !validationResult && (
            <div className="mb-6">
              <Title level={5} className="mb-3">
                2. Validar dados
              </Title>
              <Button
                type="primary"
                size="large"
                icon={<CheckCircleOutlined />}
                onClick={handleValidate}
                loading={loading}
                block
              >
                {loading ? 'Validando...' : 'Validar Importação'}
              </Button>
            </div>
          )}

          {/* Erro */}
          {error && (
            <Alert
              message="Erro"
              description={error}
              type="error"
              showIcon
              closable
              onClose={() => setError(null)}
              className="mb-4"
            />
          )}

          {/* Step 3: Resultado da validação */}
          {validationResult && (
            <div className="mb-6">
              <Title level={5} className="mb-3">
                {hasErrors ? (
                  <Space>
                    <CloseCircleOutlined className="text-red-500" />
                    Validação com Erros
                  </Space>
                ) : (
                  <Space>
                    <CheckCircleOutlined className="text-green-500" />
                    Validação OK
                  </Space>
                )}
              </Title>

              {/* Estatísticas */}
              <Card size="small" className="mb-4">
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="Serão Criados"
                      value={validationResult.stats?.created || 0}
                      valueStyle={{ color: '#3f8600' }}
                      prefix={<CheckCircleOutlined />}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Serão Atualizados"
                      value={validationResult.stats?.updated || 0}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Inalterados"
                      value={validationResult.stats?.unchanged || 0}
                      valueStyle={{ color: '#8c8c8c' }}
                    />
                  </Col>
                </Row>
              </Card>

              {/* Erros bloqueantes */}
              {hasErrors && validationResult.errors && (
                <Alert
                  message="Erros encontrados"
                  description={
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {validationResult.errors.slice(0, 10).map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                      {validationResult.errors.length > 10 && (
                        <li>... e mais {validationResult.errors.length - 10} erros</li>
                      )}
                    </ul>
                  }
                  type="error"
                  showIcon
                  className="mb-4"
                />
              )}

              {/* Pendências (warnings) */}
              {validationResult.pendencias && Object.keys(validationResult.pendencias).length > 0 && (
                <Alert
                  message="Pendências"
                  description={
                    <Collapse ghost size="small">
                      <Panel header="Ver detalhes" key="1">
                        <pre style={{ fontSize: 12, margin: 0, overflow: 'auto' }}>
                          {JSON.stringify(validationResult.pendencias, null, 2)}
                        </pre>
                      </Panel>
                    </Collapse>
                  }
                  type="warning"
                  showIcon
                  className="mb-4"
                />
              )}

              {/* JSON completo */}
              <Collapse size="small" className="mb-4">
                <Panel header="Ver relatório completo (JSON)" key="1">
                  <pre style={{ fontSize: 10, margin: 0, overflow: 'auto', maxHeight: 300 }}>
                    {JSON.stringify(validationResult, null, 2)}
                  </pre>
                </Panel>
              </Collapse>

              {/* Step 4: Botão de aplicar (só se validação OK) */}
              {canApply && (
                <div>
                  <Title level={5} className="mb-3">
                    3. Confirmar importação
                  </Title>
                  <Button
                    type="primary"
                    size="large"
                    icon={<CheckCircleOutlined />}
                    onClick={handleApply}
                    loading={loadingApply}
                    block
                    style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
                  >
                    {loadingApply ? 'Importando...' : 'Realizar Importação'}
                  </Button>
                  <Text type="secondary" className="block mt-2 text-center">
                    Esta ação irá persistir os dados no banco
                  </Text>
                </div>
              )}

              {/* Se tem erros, mostrar botão para tentar novamente */}
              {hasErrors && (
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleReset}
                  block
                >
                  Corrigir arquivo e tentar novamente
                </Button>
              )}
            </div>
          )}
        </>
      )}
    </Card>
  );
}
