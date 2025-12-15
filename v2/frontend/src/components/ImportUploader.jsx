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
  Spin
} from 'antd';
import {
  UploadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  FileExcelOutlined,
  ReloadOutlined
} from '@ant-design/icons';

const { Text, Title } = Typography;
const { Panel } = Collapse;
const { Dragger } = Upload;

export default function ImportUploader({ label, onDryRun, onApply, description }) {
  const [file, setFile] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [applyResult, setApplyResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);
  const [error, setError] = useState(null);

  // Estado da validação
  const isValidated = validationResult !== null && !error;
  const hasErrors = validationResult?.errors?.length > 0;
  const canApply = isValidated && !hasErrors && !applyResult;

  /**
   * Reset para nova importação
   */
  const handleReset = () => {
    setFile(null);
    setValidationResult(null);
    setApplyResult(null);
    setError(null);
  };

  /**
   * Validar importação (dry-run)
   */
  const handleValidate = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setValidationResult(null);
    setApplyResult(null);

    try {
      const report = await onDryRun(file);
      setValidationResult(report);
    } catch (err) {
      setError(err.message || 'Erro ao validar arquivo');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Realizar importação (apply)
   */
  const handleApply = async () => {
    if (!file) return;

    setLoadingApply(true);
    setError(null);

    try {
      const report = await onApply(file);
      setApplyResult(report);
      setValidationResult(null); // Limpar validação após apply
    } catch (err) {
      setError(err.message || 'Erro ao importar arquivo');
    } finally {
      setLoadingApply(false);
    }
  };

  /**
   * Props do upload
   */
  const uploadProps = {
    accept: '.csv,.xlsx,.xls',
    maxCount: 1,
    beforeUpload: (selectedFile) => {
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
    }] : [],
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
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
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
          <div style={{ marginBottom: 24 }}>
            <Title level={5} style={{ marginBottom: 12 }}>
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
            <div style={{ marginBottom: 24 }}>
              <Title level={5} style={{ marginBottom: 12 }}>
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
              style={{ marginBottom: 16 }}
            />
          )}

          {/* Step 3: Resultado da validação */}
          {validationResult && (
            <div style={{ marginBottom: 24 }}>
              <Title level={5} style={{ marginBottom: 12 }}>
                {hasErrors ? (
                  <Space>
                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                    Validação com Erros
                  </Space>
                ) : (
                  <Space>
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    Validação OK
                  </Space>
                )}
              </Title>

              {/* Estatísticas */}
              <Card size="small" style={{ marginBottom: 16 }}>
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
              {hasErrors && (
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
                  style={{ marginBottom: 16 }}
                />
              )}

              {/* Pendências (warnings) */}
              {validationResult.pendencias && Object.keys(validationResult.pendencias).length > 0 && (
                <Alert
                  message="Pendências"
                  description={
                    <Collapse ghost size="small">
                      <Panel header="Ver detalhes" key="1">
                        <pre style={{ fontSize: 11, margin: 0, overflow: 'auto' }}>
                          {JSON.stringify(validationResult.pendencias, null, 2)}
                        </pre>
                      </Panel>
                    </Collapse>
                  }
                  type="warning"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              )}

              {/* JSON completo */}
              <Collapse size="small" style={{ marginBottom: 16 }}>
                <Panel header="Ver relatório completo (JSON)" key="1">
                  <pre style={{ fontSize: 10, margin: 0, overflow: 'auto', maxHeight: 300 }}>
                    {JSON.stringify(validationResult, null, 2)}
                  </pre>
                </Panel>
              </Collapse>

              {/* Step 4: Botão de aplicar (só se validação OK) */}
              {canApply && (
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>
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
                  <Text type="secondary" style={{ display: 'block', marginTop: 8, textAlign: 'center' }}>
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
