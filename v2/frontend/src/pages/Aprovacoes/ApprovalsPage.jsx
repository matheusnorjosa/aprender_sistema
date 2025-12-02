/**
 * ApprovalsPage - Página de aprovação/reprovação de solicitações (Superintendência)
 *
 * Features:
 * - Filtra solicitações pendentes do fluxo SUPER
 * - Botões para preview, aprovar e reprovar
 * - Modal para preview de payload JSON
 * - Modal para reprovação com justificativa obrigatória
 *
 * PA-06 (Política de Aprovação Manual):
 * - Botões de aprovar/reprovar aparecem para: Superintendência, DAT, e Superusuários
 * - Verifica: is_superuser || is_superintendencia || groups.includes('Superintendência') || groups.includes('DAT')
 * - Conformidade ISO 9241-110: Controle explícito (usuário vê apenas ações permitidas)
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Card,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Typography,
  message,
  Modal,
  Form,
} from 'antd';
import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import {
  listSolicitacoes,
  approveSolicitacao,
  rejectSolicitacao,
  previewSolicitacao,
} from '../../api/solicitacoes';
import { getMe } from '../../api/availability';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

const STATUS_COLORS = {
  pendente: 'orange',
  aprovado: 'green',
  reprovado: 'red',
};

const STATUS_LABELS = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
};

export default function ApprovalsPage() {
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);

  const [statusFilter, setStatusFilter] = useState('pendente');
  const [searchTerm, setSearchTerm] = useState('');

  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  const [rejectVisible, setRejectVisible] = useState(false);
  const [rejectId, setRejectId] = useState(null);
  const [rejectForm] = Form.useForm();

  // PA-06: Estado para verificar permissão do usuário (Superintendência, DAT, Superusuários)
  const [canApprove, setCanApprove] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const filters = { flow: 'SUPER', status: statusFilter || 'pendente', q: searchTerm };

      const data = await listSolicitacoes(filters);
      setRows(data.results || data);
      setTotal(data.count || data.length);
    } catch (error) {
      message.error('Erro ao carregar solicitações: ' + error.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchTerm]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // PA-06: Carregar dados do usuário e verificar permissão
  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await getMe();

        // Verificar se usuário tem permissão para aprovar/reprovar
        // Permitido para: Superintendência, DAT, e Superusuários
        const hasApprovalPermission =
          userData?.is_superuser ||
          userData?.is_superintendencia ||
          userData?.groups?.includes('Superintendência') ||
          userData?.groups?.includes('DAT');

        setCanApprove(hasApprovalPermission);
      } catch (error) {
        console.error('Erro ao carregar usuário:', error);
        setCanApprove(false);
      }
    };
    loadUser();
  }, []);

  const handlePreview = async (id) => {
    try {
      const data = await previewSolicitacao(id);
      setPreviewData(data);
      setPreviewVisible(true);
    } catch (error) {
      message.error('Erro ao visualizar payload: ' + error.message);
    }
  };

  const handleApprove = (id) => {
    Modal.confirm({
      title: 'Confirmar Aprovação',
      content: 'Deseja aprovar esta solicitação?',
      okText: 'Aprovar',
      okType: 'primary',
      cancelText: 'Cancelar',
      onOk: async () => {
        try {
          await approveSolicitacao(id);
          message.success('Solicitação aprovada com sucesso!');
          loadData();
        } catch (error) {
          message.error('Erro ao aprovar: ' + error.message);
        }
      },
    });
  };

  const handleRejectClick = (id) => {
    setRejectId(id);
    setRejectVisible(true);
    rejectForm.resetFields();
  };

  const handleRejectConfirm = async (values) => {
    try {
      await rejectSolicitacao(rejectId, values.reason);
      message.success('Solicitação reprovada.');
      setRejectVisible(false);
      loadData();
    } catch (error) {
      message.error('Erro ao reprovar: ' + error.message);
    }
  };

  const columns = [
    {
      title: 'Data',
      dataIndex: 'inicio',
      key: 'data',
      render: (inicio) => dayjs(inicio).format('DD/MM/YYYY'),
      width: 100,
    },
    {
      title: 'Início',
      dataIndex: 'inicio',
      key: 'hora_inicio',
      render: (inicio) => dayjs(inicio).format('HH:mm'),
      width: 70,
    },
    {
      title: 'Fim',
      dataIndex: 'fim',
      key: 'hora_fim',
      render: (fim) => dayjs(fim).format('HH:mm'),
      width: 70,
    },
    {
      title: 'Município',
      dataIndex: 'municipio_nome',
      key: 'municipio_nome',
      render: (nome) => nome || '-',
      width: 150,
    },
    {
      title: 'Projeto',
      dataIndex: 'projeto_nome',
      key: 'projeto_nome',
      render: (nome) => nome || '-',
      width: 150,
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      render: (tipo) => tipo || '-',
      width: 100,
    },
    {
      title: 'Coordenador',
      dataIndex: 'coordenador_username',
      key: 'coordenador_username',
      render: (username) => username || '-',
      width: 120,
    },
    {
      title: 'Encontro',
      dataIndex: 'encontro',
      key: 'encontro',
      render: (encontro) => encontro || '-',
      width: 100,
    },
    {
      title: 'Segmento',
      dataIndex: 'segmento',
      key: 'segmento',
      render: (segmento) => segmento || '-',
      width: 100,
    },
    {
      title: 'Formadores',
      dataIndex: 'participations',
      key: 'formadores',
      render: (participations) => {
        if (!participations || participations.length === 0) return '-';
        const formadores = participations
          .filter(p => p.role === 'FORMADOR')
          .map(p => p.usuario?.first_name || p.usuario?.last_name || p.email || 'N/A')
          .filter(name => name !== 'N/A')
          .join(', ');
        return formadores || '-';
      },
      width: 200,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={STATUS_COLORS[status]}>{STATUS_LABELS[status] || status}</Tag>
      ),
      width: 100,
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record.id)}
            title="Preview"
          />
          {/* PA-06: Botões de aprovar/reprovar para Superintendência, DAT e Superusuários */}
          {record.status === 'pendente' && canApprove && (
            <>
              <Button
                size="small"
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record.id)}
                title="Aprovar"
              />
              <Button
                size="small"
                danger
                icon={<CloseOutlined />}
                onClick={() => handleRejectClick(record.id)}
                title="Reprovar"
              />
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Header */}
          <Title level={2}>Aprovações</Title>

          {/* Filtros */}
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 200 }}
              placeholder="Status"
            >
              <Select.Option value="pendente">Pendentes</Select.Option>
              <Select.Option value="aprovado">Aprovadas</Select.Option>
              <Select.Option value="reprovado">Reprovadas</Select.Option>
            </Select>

            <Input.Search
              placeholder="Buscar por município, projeto, autor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onSearch={loadData}
              style={{ width: 400 }}
              allowClear
            />
          </Space>

          {/* Contagem de pendentes */}
          {statusFilter === 'pendente' && total > 0 && (
            <Paragraph>
              <Tag color="orange">{total}</Tag> solicitações aguardando aprovação
            </Paragraph>
          )}

          {/* Tabela */}
          <Table
            columns={columns}
            dataSource={rows}
            loading={loading}
            rowKey="id"
            scroll={{ x: 1800 }}
            pagination={{
              total,
              pageSize: 20,
              showTotal: (total) => `Total: ${total} solicitações`,
            }}
          />
        </Space>
      </Card>

      {/* Modal Preview */}
      <Modal
        title="Preview do Payload GCal"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            Fechar
          </Button>,
        ]}
        width={700}
      >
        <pre style={{ maxHeight: 500, overflow: 'auto', backgroundColor: '#f5f5f5', padding: 12 }}>
          {JSON.stringify(previewData, null, 2)}
        </pre>
      </Modal>

      {/* Modal Rejeitar */}
      <Modal
        title="Reprovar Solicitação"
        open={rejectVisible}
        onCancel={() => setRejectVisible(false)}
        onOk={() => rejectForm.submit()}
        okText="Reprovar"
        okButtonProps={{ danger: true }}
      >
        <Form form={rejectForm} layout="vertical" onFinish={handleRejectConfirm}>
          <Form.Item
            label="Motivo da Reprovação"
            name="reason"
            rules={[{ required: true, message: 'O motivo é obrigatório' }]}
          >
            <TextArea rows={4} placeholder="Digite o motivo da reprovação..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
