/**
 * Ações Internas (32 passos): registro de âncora e conclusão por ciclo.
 *
 * Sem rolagem horizontal (G30): ResponsiveTable. Sempre na linha o nome da ação (abaixo de sm, com o
 * estado embaixo) e as ações (AcoesLinha: "Registrar âncora" e "Concluir"; no celular, o menu "Mais
 * ações"); Ordem e Estado sobem a partir de sm, Vencimento de md, Âncora de lg e Realização de xl.
 * O que some vai para a linha expandida.
 */
import { useEffect, useState, type JSX } from 'react';
import {
  Card,
  DatePicker,
  Form,
  Grid,
  Input,
  Modal,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { CheckOutlined, PushpinOutlined } from '@ant-design/icons';
import dayjs, { type Dayjs } from 'dayjs';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha, type AcaoDaLinha } from '../../components/AcoesLinha';

import { concluirAcao, listAcoesByCiclo, listCiclosAcoes, registrarAncora } from '../../api/acoesNotificacao';
import type { AcaoInstancia, CicloAcoes } from '../../types/acoesNotificacao';

const { Title, Text } = Typography;

const ESTADO_LABELS: Record<string, string> = {
  AGUARDANDO_ANCORA: 'Aguardando âncora',
  EM_ANDAMENTO: 'Em andamento',
  CONCLUIDA: 'Concluída',
  ATRASADA: 'Atrasada',
};

const formatarData = (value: string | null): string => (value ? dayjs(value).format('DD/MM/YYYY') : '-');

const cycleLabel = (cycle: CicloAcoes): string =>
  `${cycle.projeto_nome} / ${cycle.municipio_nome} (${cycle.semestre}/${cycle.ano})`;

type ModalMode = 'ancora' | 'conclusao';

/** Quem a linha representa: nomeia o expandir e as ações ("Concluir: 1. Enviar kit"). */
const nomeDaAcao = (acao: AcaoInstancia): string => `${acao.ordem}. ${acao.template_nome}`;

function tagDoEstado(value: string): JSX.Element {
  const color =
    value === 'CONCLUIDA' ? 'green' : value === 'ATRASADA' ? 'red' : value === 'EM_ANDAMENTO' ? 'blue' : 'gold';
  return <Tag color={color}>{ESTADO_LABELS[value] ?? value}</Tag>;
}

interface AcaoNotificacaoFormValues {
  data_ancora: Dayjs;
  data_realizacao: Dayjs;
  observacao: string;
}

export default function AcoesNotificacaoPage(): JSX.Element {
  const [cycles, setCycles] = useState<CicloAcoes[]>([]);
  const [cycleSearch, setCycleSearch] = useState<string>('');
  // Guarda o ciclo escolhido inteiro: a busca troca a lista e ele pode sair dela.
  const [selectedCycle, setSelectedCycle] = useState<CicloAcoes | null>(null);
  const selectedCycleId = selectedCycle?.id ?? null;
  const [actions, setActions] = useState<AcaoInstancia[]>([]);
  const [loadingCycles, setLoadingCycles] = useState<boolean>(false);
  const [loadingActions, setLoadingActions] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);

  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [modalMode, setModalMode] = useState<ModalMode>('ancora');
  const [selectedAction, setSelectedAction] = useState<AcaoInstancia | null>(null);
  const [form] = Form.useForm<AcaoNotificacaoFormValues>();
  const acoesCompactas = !Grid.useBreakpoint().sm;

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

  // Busca no servidor (projeto e município): a lista traz até 100 ciclos por vez.
  useEffect(() => {
    let ignore = false;
    const timer = window.setTimeout(
      () => {
        setLoadingCycles(true);
        listCiclosAcoes({ page_size: 100, ordering: '-ano', search: cycleSearch })
          .then((data) => {
            if (ignore) return;
            setCycles(data.results);
            const firstCycle = data.results[0];
            if (firstCycle) {
              setSelectedCycle((current) => current ?? firstCycle);
            }
          })
          .catch((error: unknown) => {
            if (!ignore) message.error(`Erro ao carregar ciclos: ${(error as Error).message}`);
          })
          .finally(() => {
            if (!ignore) setLoadingCycles(false);
          });
      },
      cycleSearch ? 300 : 0,
    );
    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [cycleSearch]);

  useEffect(() => {
    if (selectedCycleId) {
      void loadActions(selectedCycleId);
    }
  }, [selectedCycleId]);

  const selectedCycleLabel = selectedCycle ? cycleLabel(selectedCycle) : '';
  const cycleOptions =
    selectedCycle && !cycles.some((cycle) => cycle.id === selectedCycle.id) ? [selectedCycle, ...cycles] : cycles;

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

  const columns: ColunaResponsiva<AcaoInstancia>[] = [
    {
      title: 'Ordem',
      dataIndex: 'ordem',
      key: 'ordem',
      responsive: VISIVEL_A_PARTIR.sm,
      width: 80,
      sorter: (a, b) => a.ordem - b.ordem,
    },
    {
      // Identidade: quebra linha em vez de cortar. Abaixo de sm, o estado vai embaixo do nome.
      title: 'Ação',
      dataIndex: 'template_nome',
      key: 'template_nome',
      render: (_: unknown, record: AcaoInstancia) => (
        <>
          <div>{record.template_nome}</div>
          {acoesCompactas && tagDoEstado(record.estado)}
        </>
      ),
    },
    {
      title: 'Estado',
      dataIndex: 'estado',
      key: 'estado',
      responsive: VISIVEL_A_PARTIR.sm,
      width: 152,
      render: (value: string) => tagDoEstado(value),
    },
    {
      title: 'Âncora',
      dataIndex: 'data_ancora',
      key: 'data_ancora',
      responsive: VISIVEL_A_PARTIR.lg,
      width: 112,
      render: formatarData,
    },
    {
      title: 'Vencimento',
      dataIndex: 'data_vencimento',
      key: 'data_vencimento',
      responsive: VISIVEL_A_PARTIR.md,
      width: 112,
      render: formatarData,
    },
    {
      title: 'Realização',
      dataIndex: 'data_realizacao',
      key: 'data_realizacao',
      responsive: VISIVEL_A_PARTIR.xl,
      width: 112,
      render: formatarData,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: larguraAcoesLinha(2, acoesCompactas),
      render: (_: unknown, record: AcaoInstancia) => {
        const acoes: AcaoDaLinha[] = [
          { chave: 'ancora', rotulo: 'Registrar âncora', icone: <PushpinOutlined />, onClick: () => openActionModal('ancora', record) },
          // Concluída: sem "Concluir" (antes, o botão ficava desabilitado).
          ...(record.estado === 'CONCLUIDA'
            ? []
            : [{ chave: 'concluir', rotulo: 'Concluir', icone: <CheckOutlined />, onClick: () => openActionModal('conclusao', record) }]),
        ];
        return <AcoesLinha compacto={acoesCompactas} alvo={nomeDaAcao(record)} acoes={acoes} />;
      },
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
              aria-label="Ciclo"
              loading={loadingCycles}
              value={selectedCycleId ?? undefined}
              onChange={(value) => setSelectedCycle(cycleOptions.find((cycle) => cycle.id === value) ?? null)}
              placeholder="Busque por projeto ou município"
              showSearch
              filterOption={false}
              onSearch={setCycleSearch}
              notFoundContent={loadingCycles ? 'Buscando...' : 'Nenhum ciclo encontrado'}
              options={cycleOptions.map((cycle) => ({ value: cycle.id, label: cycleLabel(cycle) }))}
              style={{ width: 520, maxWidth: '100%' }}
            />
            {selectedCycleLabel && <Text type="secondary">Ciclo ativo: {selectedCycleLabel}</Text>}
          </Space>
        </Card>

        <Card>
          <ResponsiveTable<AcaoInstancia>
            rowKey="id"
            dataSource={actions}
            columns={columns}
            loading={loadingActions}
            pagination={{ pageSize: 12 }}
            nomeDaLinha={nomeDaAcao}
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
        <Form form={form} layout="vertical" autoComplete="off">
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
            {...(modalMode === 'conclusao' && {
              rules: [{ required: true, message: 'Observação é obrigatória para conclusão' }],
            })}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </main>
  );
}
