import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { concluirAcao, listAcoesByCiclo, listCiclosAcoes, registrarAncora } from '../../api/acoesNotificacao';
import type { AcaoInstancia, CicloAcoes } from '../../types/acoesNotificacao';

const { Title, Text } = Typography;

type ModalMode = 'ancora' | 'conclusao';

export default function AcoesNotificacaoPage(): JSX.Element {
  const [cycles, setCycles] = useState<CicloAcoes[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);
  const [actions, setActions] = useState<AcaoInstancia[]>([]);
  const [loadingCycles, setLoadingCycles] = useState<boolean>(false);
  const [loadingActions, setLoadingActions] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);

  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [modalMode, setModalMode] = useState<ModalMode>('ancora');
  const [selectedAction, setSelectedAction] = useState<AcaoInstancia | null>(null);
  const [form] = Form.useForm();

  const loadCycles = async () => {
    setLoadingCycles(true);
    try {
      const data = await listCiclosAcoes({ page_size: 100, ordering: '-ano' });
      setCycles(data.results);
      if (!selectedCycleId && data.results.length > 0) {
        setSelectedCycleId(data.results[0].id);
      }
    } catch (error) {
      message.error(`Erro ao carregar ciclos: ${(error as Error).message}`);
    } finally {
      setLoadingCycles(false);
    }
  };

  const loadActions = async (cycleId: number) => {
    setLoadingActions(true);
    try {
      const data = await listAcoesByCiclo(cycleId);
      setActions(data);
    } catch (error) {
      message.error(`Erro ao carregar ações: ${(error as Error).message}`);
    } finally {
      setLoadingActions(false);
    }
  };

  useEffect(() => {
    void loadCycles();
  }, []);

  useEffect(() => {
    if (selectedCycleId) {
      void loadActions(selectedCycleId);
    }
  }, [selectedCycleId]);

  const selectedCycleLabel = useMemo(() => {
    const cycle = cycles.find((item) => item.id === selectedCycleId);
    if (!cycle) {
      return '';
    }
    return `${cycle.projeto_nome} / ${cycle.municipio_nome} (${cycle.semestre}/${cycle.ano})`;
  }, [cycles, selectedCycleId]);

  const openActionModal = (mode: ModalMode, action: AcaoInstancia) => {
    setModalMode(mode);
    setSelectedAction(action);
    setModalOpen(true);
    form.resetFields();
  };

  const handleSubmit = async () => {
    if (!selectedAction) {
      return;
    }

    try {
      const values = await form.validateFields();
      setSaving(true);

      if (modalMode === 'ancora') {
        await registrarAncora(selectedAction.id, {
          data_ancora: values.data_ancora.format('YYYY-MM-DD'),
          observacao: values.observacao || '',
        });
        message.success('Âncora registrada com sucesso.');
      } else {
        await concluirAcao(selectedAction.id, {
          data_realizacao: values.data_realizacao.format('YYYY-MM-DD'),
          observacao: values.observacao,
        });
        message.success('Ação concluída com sucesso.');
      }

      setModalOpen(false);
      form.resetFields();
      if (selectedCycleId) {
        await loadActions(selectedCycleId);
      }
    } catch (error) {
      if ((error as { errorFields?: unknown }).errorFields) {
        return;
      }
      message.error(`Falha ao salvar: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const columns: ColumnsType<AcaoInstancia> = [
    {
      title: 'Ordem',
      dataIndex: 'ordem',
      width: 90,
      sorter: (a, b) => a.ordem - b.ordem,
    },
    {
      title: 'Ação',
      dataIndex: 'template_nome',
      ellipsis: true,
    },
    {
      title: 'Estado',
      dataIndex: 'estado',
      width: 160,
      render: (value: string) => {
        const color =
          value === 'CONCLUIDA' ? 'green' : value === 'ATRASADA' ? 'red' : value === 'EM_ANDAMENTO' ? 'blue' : 'gold';
        return <Tag color={color}>{value}</Tag>;
      },
    },
    {
      title: 'Âncora',
      dataIndex: 'data_ancora',
      width: 130,
      render: (value: string | null) => value || '-',
    },
    {
      title: 'Vencimento',
      dataIndex: 'data_vencimento',
      width: 130,
      render: (value: string | null) => value || '-',
    },
    {
      title: 'Realização',
      dataIndex: 'data_realizacao',
      width: 130,
      render: (value: string | null) => value || '-',
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 250,
      render: (_: unknown, record: AcaoInstancia) => (
        <Space>
          <Button size="small" onClick={() => openActionModal('ancora', record)}>
            Registrar Âncora
          </Button>
          <Button
            size="small"
            type="primary"
            disabled={record.estado === 'CONCLUIDA'}
            onClick={() => openActionModal('conclusao', record)}
          >
            Concluir
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <div>
          <Title level={3} style={{ marginBottom: 0 }}>
            Ações Internas (32 Passos)
          </Title>
          <Text type="secondary">Registro de âncora e conclusão por ciclo.</Text>
        </div>

        <Card>
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Text strong>Selecione um ciclo</Text>
            <Select
              loading={loadingCycles}
              value={selectedCycleId ?? undefined}
              onChange={(value) => setSelectedCycleId(value)}
              placeholder="Selecione o ciclo"
              options={cycles.map((cycle) => ({
                value: cycle.id,
                label: `${cycle.projeto_nome} / ${cycle.municipio_nome} (${cycle.semestre}/${cycle.ano})`,
              }))}
              style={{ width: 520, maxWidth: '100%' }}
            />
            {selectedCycleLabel && <Text type="secondary">Ciclo ativo: {selectedCycleLabel}</Text>}
          </Space>
        </Card>

        <Card>
          <Table
            rowKey="id"
            dataSource={actions}
            columns={columns}
            loading={loadingActions}
            pagination={{ pageSize: 12 }}
            scroll={{ x: 1200 }}
          />
        </Card>
      </Space>

      <Modal
        title={modalMode === 'ancora' ? 'Registrar âncora' : 'Concluir ação'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleSubmit()}
        confirmLoading={saving}
        okText="Salvar"
      >
        <Form form={form} layout="vertical">
          {modalMode === 'ancora' ? (
            <Form.Item name="data_ancora" label="Data da âncora" rules={[{ required: true, message: 'Campo obrigatório' }]}>
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
          ) : (
            <Form.Item
              name="data_realizacao"
              label="Data de realização"
              rules={[{ required: true, message: 'Campo obrigatório' }]}
            >
              <DatePicker style={{ width: '100%' }} format="DD/MM/YYYY" />
            </Form.Item>
          )}
          <Form.Item
            name="observacao"
            label="Observação"
            rules={
              modalMode === 'conclusao'
                ? [{ required: true, message: 'Observação é obrigatória para conclusão' }]
                : undefined
            }
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </main>
  );
}
