/**
 * Formulário de Criação de Bloqueio
 *
 * Permite criar bloqueios de disponibilidade com:
 * - Data/hora início e fim
 * - Tipo (Total ou Parcial)
 * - Motivo (opcional)
 * - Validação de datas (início < fim)
 *
 * Nota: Decisão de disponibilidade é feita manualmente pela Superintendência
 * através da Grade Mensal (/disponibilidade), não há checagem em tempo real.
 */

import { useState } from 'react';
import { Form, DatePicker, Select, Input, Button } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';

const { TextArea } = Input;
const { Option } = Select;

/**
 * Block form values interface
 */
interface BlockFormValues {
  inicio: Dayjs;
  fim: Dayjs;
  tipo: 'T' | 'P';
  motivo?: string;
}

/**
 * Block payload interface
 */
export interface BlockPayload {
  inicio: string;
  fim: string;
  tipo: 'T' | 'P';
  motivo: string;
}

/**
 * BlockForm props interface
 */
export interface BlockFormProps {
  onSubmit: (payload: BlockPayload) => Promise<void>;
}

export default function BlockForm({ onSubmit }: BlockFormProps): JSX.Element {
  const [form] = Form.useForm<BlockFormValues>();
  const [loading, setLoading] = useState(false);

  /**
   * Handler para submit do formulário.
   */
  const handleSubmit = async (values: BlockFormValues): Promise<void> => {
    setLoading(true);
    try {
      const payload: BlockPayload = {
        inicio: values.inicio.toISOString(),
        fim: values.fim.toISOString(),
        tipo: values.tipo,
        motivo: values.motivo || '',
      };

      await onSubmit(payload);

      // Limpar form após sucesso
      form.resetFields();
    } catch {
      // Erro já tratado no parent (Disponibilidade.jsx)
    } finally {
      setLoading(false);
    }
  };

  /**
   * Valida que início < fim.
   */
  const validateDateRange = (): Promise<void> => {
    const inicio = form.getFieldValue('inicio') as Dayjs | undefined;
    const fim = form.getFieldValue('fim') as Dayjs | undefined;

    if (inicio && fim && inicio.isAfter(fim)) {
      return Promise.reject(new Error('Início deve ser anterior ao fim!'));
    }

    return Promise.resolve();
  };

  return (
    <Form
        form={form}
        layout="vertical"
        autoComplete="off"
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
          <Button type="primary" htmlType="submit" loading={loading}>
            Criar Bloqueio
          </Button>
        </Form.Item>
      </Form>
  );
}
