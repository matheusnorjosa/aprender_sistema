/**
 * Admin DAT - Configurações do Sistema
 *
 * Issue #187: UI para Configurações do Sistema
 *
 * Mostra só os 2 parâmetros que o sistema lê: Buffer de deslocamento (RD-04) e Aviso de horas
 * por dia (RD-05, só avisa desde 02/10/2026), os mesmos que a checagem de disponibilidade
 * aplica. Os outros 13 campos do `/api/config/` não têm leitor e saíram da tela por decisão do dono (01/10); o backend os
 * guarda como estão (ver pages.spec.md, "Configurações").
 *
 * Salva via PUT /api/config/ só o que mudou (o backend mescla com o vigente).
 */

import { useState, useEffect, type JSX } from 'react';
import { Card, Form, InputNumber, Button, Space, Typography, Spin, Alert, Divider, message } from 'antd';
import { SaveOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import { useConfig } from '../../hooks/useConfig';
import type { SystemConfig } from '../../api/systemConfig';

const { Title, Text } = Typography;

interface ConfigFormValues {
  TRAVEL_BUFFER_MINUTES: number;
  AVAILABILITY_DAILY_LIMIT_HOURS: number;
}

/** Só os campos da tela: as outras chaves do config não entram no form nem no PUT. */
function valoresDoForm(config: SystemConfig): ConfigFormValues {
  return {
    TRAVEL_BUFFER_MINUTES: config['TRAVEL_BUFFER_MINUTES'] as number,
    AVAILABILITY_DAILY_LIMIT_HOURS: config['AVAILABILITY_DAILY_LIMIT_HOURS'] as number,
  };
}

export default function ConfiguracoesPage(): JSX.Element {
  const { config, loading, loadError, saveConfig, reload } = useConfig();
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm<ConfigFormValues>();

  useEffect(() => {
    if (config) {
      form.setFieldsValue(valoresDoForm(config));
    }
  }, [config, form]);

  const handleSave = async (): Promise<void> => {
    if (!config) return;
    let values: ConfigFormValues;
    try {
      values = await form.validateFields();
    } catch {
      return; // o erro aparece no próprio campo
    }

    // Só o que mudou (auditoria UX 30/09, rodada 2): o backend mescla com o vigente, o
    // AuditLog lista só o que mudou e duas pessoas editando não desfazem uma à outra.
    const alterados = Object.fromEntries(
      Object.entries(values).filter(([campo, valor]) => config[campo] !== valor),
    );
    if (Object.keys(alterados).length === 0) {
      message.info('Nenhuma alteração para salvar.');
      return;
    }

    setSaving(true);
    try {
      await saveConfig(alterados);
      // Sucesso e erro (com o motivo) são mostrados pelo useConfig.
    } finally {
      setSaving(false);
    }
  };

  const handleReset = (): void => {
    if (config) {
      form.setFieldsValue(valoresDoForm(config));
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center gap-3" style={{ minHeight: '400px' }} role="status">
        <Spin size="large" />
        <Text type="secondary">Carregando configurações…</Text>
      </div>
    );
  }

  return (
    <section className="p-6" aria-labelledby="configuracoes-title">
      <Card>
        <header className="mb-6">
          <Title level={2} id="configuracoes-title">
            <SettingOutlined aria-hidden="true" /> Configurações do Sistema
          </Title>
          <Text type="secondary">
            Parâmetros que a checagem de disponibilidade dos formadores aplica. A mudança vale assim que você salva.
          </Text>
        </header>

        <Divider />

        {loadError && (
          <Alert
            type="error"
            showIcon
            className="mb-4"
            message="Não foi possível carregar as configurações"
            description={`${loadError} — o Salvar fica desabilitado até carregar. Use "Recarregar do Servidor".`}
          />
        )}

        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          initialValues={config ? valoresDoForm(config) : {}}
        >
          <Form.Item
            label="Buffer de deslocamento"
            name="TRAVEL_BUFFER_MINUTES"
            extra="Tempo mínimo entre o fim de um evento e o início do seguinte em outro município."
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'integer', min: 0, message: 'Use um número inteiro maior ou igual a 0.' }
            ]}
          >
            <InputNumber style={{ width: '100%' }} min={0} step={10} addonAfter="minutos" />
          </Form.Item>

          <Form.Item
            label="Aviso de horas por dia"
            name="AVAILABILITY_DAILY_LIMIT_HOURS"
            extra="Quando os eventos de uma pessoa no mesmo dia somam mais que este número de horas, o sistema avisa quem está criando. O aviso não impede o evento."
            rules={[
              { required: true, message: 'Campo obrigatório' },
              { type: 'integer', min: 1, max: 12, message: 'Use um número inteiro entre 1 e 12.' }
            ]}
          >
            <InputNumber style={{ width: '100%' }} min={1} max={12} step={1} addonAfter="horas" />
          </Form.Item>

          <Divider />

          <Space wrap>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
              disabled={!config || !!loadError}
              size="large"
            >
              Salvar Configurações
            </Button>

            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              disabled={saving || !config}
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
