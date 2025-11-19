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
import {
  SaveOutlined,
  ReloadOutlined,
  SettingOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  FlagOutlined
} from '@ant-design/icons';
import { useConfig } from '../../hooks/useConfig';

const { Title, Text } = Typography;
const { Option } = Select;

export default function ConfiguracoesPage() {
  const { config, loading, saveConfig, reload } = useConfig();
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  // Update form when config loads
  useEffect(() => {
    if (config) {
      form.setFieldsValue(config);
    }
  }, [config, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const success = await saveConfig(values);
      if (success) {
        // Success message is shown by useConfig hook
      }
    } catch (error) {
      console.error('Form validation error:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (config) {
      form.setFieldsValue(config);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <Spin size="large" tip="Carregando configurações..." />
      </div>
    );
  }

  const tabItems = [
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
            message="Regras de Disponibilidade (RD-04, RD-05)"
            description="Configure parâmetros de validação de conflitos e capacidade diária dos formadores."
            type="info"
            showIcon
          />

          <Form.Item
            label="Buffer de Deslocamento (minutos)"
            name="TRAVEL_BUFFER_MINUTES"
            tooltip="Tempo mínimo entre eventos em municípios diferentes (RD-04)"
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
            tooltip="Máximo de horas de eventos por dia por formador (RD-05)"
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
            tooltip="Se true, eventos com fim==início de outro são permitidos (sem overlap)"
          >
            <Switch checkedChildren="Sim" unCheckedChildren="Não" />
          </Form.Item>

          <Form.Item
            label="Bloquear Auto-Aprovação"
            name="BLOCK_AUTO_APPROVE"
            valuePropName="checked"
            tooltip="Se true, nenhuma solicitação é auto-aprovada (PA-01)"
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
            message="Integração Google Calendar (RF05/RF06)"
            description="Configure parâmetros de sincronização e publicação de eventos."
            type="info"
            showIcon
          />

          <Form.Item
            label="Batch Size"
            name="BATCH_SIZE"
            tooltip="Quantidade de eventos processados por lote"
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
            label="Lock TTL (segundos)"
            name="LOCK_TTL_SECONDS"
            tooltip="Tempo de vida do lock Redis para operações GCal"
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
            tooltip="Se true, tenta novamente automaticamente em caso de erro"
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
            tooltip="Define se/como enviar notificações do Google Calendar"
            rules={[{ required: true, message: 'Campo obrigatório' }]}
          >
            <Select style={{ width: '100%' }}>
              <Option value="none">Nenhuma (none)</Option>
              <Option value="all">Todas (all)</Option>
              <Option value="externalOnly">Apenas externas (externalOnly)</Option>
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
            message="Configurações de Sessão e Experiência do Usuário"
            description="Configure timeouts de sessão e parâmetros de interface."
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
            label="Debounce Autocomplete"
            name="AUTOCOMPLETE_DEBOUNCE_MS"
            tooltip="Delay antes de buscar opções em campos autocomplete (milissegundos)"
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
          Feature Flags
        </span>
      ),
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Alert
            message="Feature Flags (Funcionalidades Experimentais)"
            description="Ative/desative features em desenvolvimento ou beta."
            type="warning"
            showIcon
          />

          <Form.Item
            label="Multi-Calendar"
            name="ENABLE_MULTI_CALENDAR"
            valuePropName="checked"
            tooltip="Permite publicar eventos em múltiplos calendários Google (BETA)"
          >
            <Switch checkedChildren="Habilitado" unCheckedChildren="Desabilitado" />
          </Form.Item>

          <Form.Item
            label="Ações em Lote"
            name="ENABLE_BATCH_ACTIONS"
            valuePropName="checked"
            tooltip="Permite operações em lote na interface (BETA)"
          >
            <Switch checkedChildren="Habilitado" unCheckedChildren="Desabilitado" />
          </Form.Item>

          <Form.Item
            label="Filtros Avançados"
            name="ENABLE_ADVANCED_FILTERS"
            valuePropName="checked"
            tooltip="Habilita filtros avançados em listas e tabelas (BETA)"
          >
            <Switch checkedChildren="Habilitado" unCheckedChildren="Desabilitado" />
          </Form.Item>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: 24 }}>
          <Title level={2}>
            <SettingOutlined /> Configurações do Sistema
          </Title>
          <Text type="secondary">
            Ajuste parâmetros operacionais sem necessidade de deploy. Mudanças são aplicadas imediatamente.
          </Text>
        </div>

        <Divider />

        <Form
          form={form}
          layout="vertical"
          initialValues={config || {}}
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
    </div>
  );
}
