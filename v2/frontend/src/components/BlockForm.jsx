/**
 * Formulário de Criação de Bloqueio
 *
 * Permite criar bloqueios de disponibilidade com:
 * - Data/hora início e fim
 * - Tipo (Total ou Parcial)
 * - Motivo (opcional)
 * - Validação de datas (início < fim)
 * - Checagem prévia de conflitos (opcional)
 */

import { useState } from 'react';
import { Form, DatePicker, Select, Input, Button, Alert, List, Tag } from 'antd';
import { CheckCircleOutlined, WarningOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getMe, checkAvailability } from '../api/availability';

const { TextArea } = Input;
const { Option } = Select;

export default function BlockForm({ onSubmit }) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [conflicts, setConflicts] = useState(null);

  /**
   * Handler para verificação prévia de conflitos.
   */
  const handleCheckAvailability = async () => {
    try {
      const values = await form.validateFields(['inicio', 'fim']);
      setChecking(true);
      setConflicts(null);

      // Buscar ID do usuário atual
      const user = await getMe();

      // Chamar API de checagem
      const result = await checkAvailability({
        usuario_id: user.id,
        inicio: values.inicio.toISOString(),
        fim: values.fim.toISOString(),
      });

      setConflicts(result);
    } catch (error) {
      console.error('Erro ao checar disponibilidade:', error);
    } finally {
      setChecking(false);
    }
  };

  /**
   * Handler para submit do formulário.
   */
  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const payload = {
        inicio: values.inicio.toISOString(),
        fim: values.fim.toISOString(),
        tipo: values.tipo,
        motivo: values.motivo || '',
      };

      await onSubmit(payload);

      // Limpar form após sucesso
      form.resetFields();
      setConflicts(null);
    } catch (error) {
      // Erro já tratado no parent (Disponibilidade.jsx)
    } finally {
      setLoading(false);
    }
  };

  /**
   * Valida que início < fim.
   */
  const validateDateRange = (_, value) => {
    const inicio = form.getFieldValue('inicio');
    const fim = form.getFieldValue('fim');

    if (inicio && fim && inicio.isAfter(fim)) {
      return Promise.reject(new Error('Início deve ser anterior ao fim!'));
    }

    return Promise.resolve();
  };

  /**
   * Renderiza lista de conflitos encontrados.
   */
  const renderConflicts = () => {
    if (!conflicts) return null;

    const conflictsList = conflicts.conflicts || [];

    if (conflictsList.length === 0) {
      return (
        <Alert
          message="Nenhum conflito encontrado"
          description="O período selecionado está disponível."
          type="success"
          icon={<CheckCircleOutlined />}
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      );
    }

    return (
      <Alert
        message="Conflitos Encontrados"
        description={
          <List
            size="small"
            dataSource={conflictsList}
            renderItem={(item) => (
              <List.Item>
                <Tag color={item.code === 'X' ? 'red' : 'orange'}>{item.code}</Tag>
                <strong>{item.title}</strong>: {item.detail}
              </List.Item>
            )}
          />
        }
        type="warning"
        icon={<WarningOutlined />}
        showIcon
        closable
        onClose={() => setConflicts(null)}
        style={{ marginBottom: 16 }}
      />
    );
  };

  return (
    <>
      {renderConflicts()}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          tipo: 'T',
        }}
      >
        {/* Data/Hora Início */}
        <Form.Item
          name="inicio"
          label="Data/Hora Início"
          rules={[
            { required: true, message: 'Informe a data/hora de início!' },
            { validator: validateDateRange },
          ]}
          help="Selecione a data e hora de início do bloqueio"
        >
          <DatePicker
            showTime
            format="DD/MM/YYYY HH:mm"
            style={{ width: '100%' }}
            placeholder="Selecione data e hora"
            disabledDate={(current) => current && current < dayjs().startOf('day')}
          />
        </Form.Item>

        {/* Data/Hora Fim */}
        <Form.Item
          name="fim"
          label="Data/Hora Fim"
          rules={[
            { required: true, message: 'Informe a data/hora de fim!' },
            { validator: validateDateRange },
          ]}
          help="Selecione a data e hora de término do bloqueio"
        >
          <DatePicker
            showTime
            format="DD/MM/YYYY HH:mm"
            style={{ width: '100%' }}
            placeholder="Selecione data e hora"
            disabledDate={(current) => current && current < dayjs().startOf('day')}
          />
        </Form.Item>

        {/* Tipo de Bloqueio */}
        <Form.Item
          name="tipo"
          label="Tipo de Bloqueio"
          rules={[{ required: true, message: 'Selecione o tipo de bloqueio!' }]}
          help="Total (T): indisponível em todo o período. Parcial (P): indisponível parcialmente"
        >
          <Select placeholder="Selecione o tipo">
            <Option value="T">Total (T)</Option>
            <Option value="P">Parcial (P)</Option>
          </Select>
        </Form.Item>

        {/* Motivo (opcional) */}
        <Form.Item
          name="motivo"
          label="Motivo (opcional)"
          help="Descreva o motivo do bloqueio (férias, compromisso, etc.)"
        >
          <TextArea rows={3} placeholder="Ex: Férias, compromisso pessoal, etc." maxLength={500} showCount />
        </Form.Item>

        {/* Botões */}
        <Form.Item>
          <Button
            type="default"
            onClick={handleCheckAvailability}
            loading={checking}
            style={{ marginRight: 8 }}
          >
            Checar Disponibilidade
          </Button>
          <Button type="primary" htmlType="submit" loading={loading}>
            Criar Bloqueio
          </Button>
        </Form.Item>
      </Form>
    </>
  );
}
