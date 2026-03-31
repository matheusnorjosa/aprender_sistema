/**
 * Admin DAT - Configurações do Sistema
 *
 * Issue #187: UI para Configurações do Sistema
 *
 * Features:
 * - 4 tabs: Disponibilidade, Google Calendar, Sessões/UX, Feature Flags
 * - Form with Ant Design (InputNumber, Switch, Select)
 * - Saves to PUT /api/config/
 * - Real-time validation
 * - Loading state
 */

import { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  InputNumber,
  Switch,
  Select,
  Button,
  Space,
  Typography,
  Spin,
  Alert,
  Divider
} from 'antd';
import type { TabsProps } from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  SettingOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  FlagOutlined
} from '@ant-design/icons';
import { useConfig } from '../../hooks/useConfig';
import logger from '../../utils/logger';

const { Title, Text } = Typography;
const { Option } = Select;

/**
 * Config form values interface
 */
interface ConfigFormValues {
  // Disponibilidade
  TRAVEL_BUFFER_MINUTES: number;
  AVAILABILITY_DAILY_LIMIT_HOURS: number;
  ALLOW_ADJACENT_EVENTS: boolean;
  BLOCK_AUTO_APPROVE: boolean;
  // Google Calendar
  BATCH_SIZE: number;
  LOCK_TTL_SECONDS: number;
  AUTO_RETRY_ON_ERROR: boolean;
  MAX_RETRIES: number;
  SEND_UPDATES: 'none' | 'all' | 'externalOnly';
  // Sessions
  SESSION_COOKIE_AGE: number;
  SESSION_WARNING_THRESHOLD: number;
  AUTOCOMPLETE_DEBOUNCE_MS: number;
  // Feature Flags
  ENABLE_MULTI_CALENDAR: boolean;
  ENABLE_BATCH_ACTIONS: boolean;
  ENABLE_ADVANCED_FILTERS: boolean;
}

export default function ConfiguracoesPage(): JSX.Element {
  const { config, loading, saveConfig, reload } = useConfig();
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<ConfigFormValues>();

  // Update form when config loads
  useEffect(() => {
    if (config) {
      form.setFieldsValue(config as unknown as ConfigFormValues);
    }
  }, [config, form]);

  const handleSave = async (): Promise<void> => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await saveConfig(values as unknown as Record<string, unknown>);
      // Success message is shown by useConfig hook
    } catch (error) {
      logger.error('Form validation error:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = (): void => {
    if (config) {
      form.setFieldsValue(config as unknown as ConfigFormValues);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center" style={{ minHeight: '400px' }}>
        <Spin size="large" tip="Carregando configurações..." />
      </div>
    );
  }

  const tabItems: TabsProps['items'] = [
    {
      key: '1',
      label: (
        <span>
          <SettingOutlined />
          Disponibilidade
        </span>
      ),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Alert
            message="Disponibilidade"
            description="Configure os limites de horário e deslocamento dos formadores."
            type="info"
            showIcon
          />

          <Form.Item
            label="Buffer de Deslocamento (minutos)"
            name="TRAVEL_BUFFER_MINUTES"
            tooltip="Tempo mínimo entre eventos em municípios diferentes"
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'number', min: 0, message: 'Valor deve ser ≥ 0' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              step={10}
              addonAfter="minutos"
            />
          </Form.Item>

          <Form.Item
            label="Limite Diário de Horas"
            name="AVAILABILITY_DAILY_LIMIT_HOURS"
            tooltip="Máximo de horas de eventos por dia por formador"
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'number', min: 1, max: 12, message: 'Valor deve estar entre 1 e 12' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              max={12}
              step={1}
              addonAfter="horas"
            />
          </Form.Item>

          <Form.Item
            label="Permitir Eventos Adjacentes"
            name="ALLOW_ADJACENT_EVENTS"
            valuePropName="checked"
            tooltip="Quando ativado, permite eventos consecutivos sem intervalo entre eles"
          >
            <Switch checkedChildren="Sim" unCheckedChildren="Não" />
          </Form.Item>

          <Form.Item
            label="Bloquear Auto-Aprovação"
            name="BLOCK_AUTO_APPROVE"
            valuePropName="checked"
            tooltip="Quando ativado, todas as solicitações precisam de aprovação manual"
          >
            <Switch checkedChildren="Sim" unCheckedChildren="Não" />
          </Form.Item>
        </Space>
      )
    },
    {
      key: '2',
      label: (
        <span>
          <CalendarOutlined />
          Google Calendar
        </span>
      ),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Alert
            message="Google Calendar"
            description="Configure a sincronização e publicação de eventos no Google Calendar."
            type="info"
            showIcon
          />

          <Form.Item
            label="Eventos por Lote"
            name="BATCH_SIZE"
            tooltip="Quantidade de eventos enviados ao Google Calendar por vez"
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'number', min: 50, max: 500, message: 'Valor deve estar entre 50 e 500' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={50}
              max={500}
              step={50}
              addonAfter="eventos"
            />
          </Form.Item>

          <Form.Item
            label="Tempo Máximo de Processamento"
            name="LOCK_TTL_SECONDS"
            tooltip="Tempo máximo que uma sincronização pode levar antes de ser cancelada"
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'number', min: 60, max: 600, message: 'Valor deve estar entre 60 e 600' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={60}
              max={600}
              step={30}
              addonAfter="segundos"
            />
          </Form.Item>

          <Form.Item
            label="Auto-Retry em Erro"
            name="AUTO_RETRY_ON_ERROR"
            valuePropName="checked"
            tooltip="Quando ativado, tenta novamente automaticamente em caso de erro"
          >
            <Switch checkedChildren="Sim" unCheckedChildren="Não" />
          </Form.Item>

          <Form.Item
            label="Máximo de Tentativas"
            name="MAX_RETRIES"
            tooltip="Número máximo de tentativas em caso de erro"
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'number', min: 1, max: 5, message: 'Valor deve estar entre 1 e 5' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              max={5}
              step={1}
            />
          </Form.Item>

          <Form.Item
            label="Enviar Notificações"
            name="SEND_UPDATES"
            tooltip="Controla o envio de notificações ao criar ou alterar eventos"
            rules={[{ required: true, message: 'Campo obrigatório' }]}
          >
            <Select style={{ width: '100%' }}>
              <Option value="none">Nenhuma</Option>
              <Option value="all">Todas</Option>
              <Option value="externalOnly">Apenas externas</Option>
            </Select>
          </Form.Item>
        </Space>
      )
    },
    {
      key: '3',
      label: (
        <span>
          <ClockCircleOutlined />
          Sessões e UX
        </span>
      ),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Alert
            message="Sessões e Interface"
            description="Configure o tempo de sessão e o comportamento da interface."
            type="info"
            showIcon
          />

          <Form.Item
            label="Duração da Sessão"
            name="SESSION_COOKIE_AGE"
            tooltip="Tempo máximo de inatividade antes do logout (segundos)"
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'number', min: 300, message: 'Valor deve ser ≥ 300 (5 minutos)' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={300}
              step={300}
              addonAfter="segundos"
            />
          </Form.Item>

          <Form.Item
            label="Aviso de Expiração"
            name="SESSION_WARNING_THRESHOLD"
            tooltip="Quando mostrar aviso de expiração de sessão (segundos antes)"
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'number', min: 60, message: 'Valor deve ser ≥ 60 (1 minuto)' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={60}
              step={60}
              addonAfter="segundos"
            />
          </Form.Item>

          <Form.Item
            label="Tempo de Espera do Autocomplete"
            name="AUTOCOMPLETE_DEBOUNCE_MS"
            tooltip="Tempo de espera antes de buscar sugestões nos campos de pesquisa"
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'number', min: 100, max: 1000, message: 'Valor deve estar entre 100 e 1000' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={100}
              max={1000}
              step={100}
              addonAfter="ms"
            />
          </Form.Item>
        </Space>
      )
    },
    {
      key: '4',
      label: (
        <span>
          <FlagOutlined />
          Experimental
        </span>
      ),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Alert
            message="Funcionalidades Experimentais"
            description="Ative ou desative funcionalidades em fase de testes."
            type="warning"
            showIcon
          />

          <Form.Item
            label="Multi-Calendar"
            name="ENABLE_MULTI_CALENDAR"
            valuePropName="checked"
            tooltip="Permite publicar eventos em múltiplos calendários Google"
          >
            <Switch checkedChildren="Habilitado" unCheckedChildren="Desabilitado" />
          </Form.Item>

          <Form.Item
            label="Ações em Lote"
            name="ENABLE_BATCH_ACTIONS"
            valuePropName="checked"
            tooltip="Permite executar ações em vários itens de uma vez"
          >
            <Switch checkedChildren="Habilitado" unCheckedChildren="Desabilitado" />
          </Form.Item>

          <Form.Item
            label="Filtros Avançados"
            name="ENABLE_ADVANCED_FILTERS"
            valuePropName="checked"
            tooltip="Habilita filtros avançados em listas e tabelas"
          >
            <Switch checkedChildren="Habilitado" unCheckedChildren="Desabilitado" />
          </Form.Item>
        </Space>
      )
    }
  ];

  return (
    <section className="p-6" aria-labelledby="configuracoes-title">
      <Card>
        <header className="mb-6">
          <Title level={2} id="configuracoes-title">
            <SettingOutlined aria-hidden="true" /> Configurações do Sistema
          </Title>
          <Text type="secondary">
            Ajuste as configurações do sistema. As mudanças são aplicadas imediatamente.
          </Text>
        </header>

        <Divider />

        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          initialValues={(config as unknown as ConfigFormValues) || {}}
        >
          <Tabs items={tabItems} />

          <Divider />

          <Space>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
              size="large"
            >
              Salvar Configurações
            </Button>

            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              disabled={saving}
              size="large"
            >
              Restaurar Valores
            </Button>

            <Button
              icon={<ReloadOutlined />}
              onClick={reload}
              disabled={saving}
              size="large"
            >
              Recarregar do Servidor
            </Button>
          </Space>
        </Form>
      </Card>
    </section>
  );
}
