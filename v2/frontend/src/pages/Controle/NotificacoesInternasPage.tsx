import { useEffect, useState, type JSX } from 'react';
import { Button, Card, Space, Table, Tag, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { listNotificacoesInternas, marcarNotificacaoLida, marcarTodasNotificacoesLidas } from '../../api/acoesNotificacao';
import type { NotificacaoInterna } from '../../types/acoesNotificacao';

const { Title, Text } = Typography;

// Fases do disparo diário (prazos em dias úteis até o vencimento), ver notificacoes_acoes_service.py.
const FASE_LABELS: Record<string, string> = {
  'D-7': '7 dias úteis antes',
  'D-3': '3 dias úteis antes',
  'D-1': '1 dia útil antes',
  D0: 'No vencimento',
  'D+1': '1 dia útil depois',
  'D+3': '3 dias úteis depois',
};

const TIPO_LABELS: Record<string, string> = {
  LEMBRETE: 'Lembrete',
  VENCIMENTO: 'Vencimento',
  ATRASO: 'Atraso',
  ESCALONAMENTO: 'Escalonamento',
};

const PRIORIDADE_LABELS: Record<string, string> = {
  BAIXA: 'Baixa',
  MEDIA: 'Média',
  ALTA: 'Alta',
  CRITICA: 'Crítica',
};

export default function NotificacoesInternasPage(): JSX.Element {
  const [notifications, setNotifications] = useState<NotificacaoInterna[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [markingId, setMarkingId] = useState<number | null>(null);
  const [markingAll, setMarkingAll] = useState<boolean>(false);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const data = await listNotificacoesInternas({ page_size: 100, ordering: '-created_at' });
      setNotifications(data.results);
    } catch (error) {
      message.error(`Erro ao carregar notificações: ${(error as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadNotifications();
  }, []);

  const handleMarkRead = async (notificationId: number) => {
    setMarkingId(notificationId);
    try {
      await marcarNotificacaoLida(notificationId);
      await loadNotifications();
      window.dispatchEvent(new Event('notificacoes:refresh'));
    } catch (error) {
      message.error(`Erro ao marcar notificação como lida: ${(error as Error).message}`);
    } finally {
      setMarkingId(null);
    }
  };

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await marcarTodasNotificacoesLidas();
      await loadNotifications();
      window.dispatchEvent(new Event('notificacoes:refresh'));
    } catch (error) {
      message.error(`Erro ao marcar todas como lidas: ${(error as Error).message}`);
    } finally {
      setMarkingAll(false);
    }
  };

  const columns: ColumnsType<NotificacaoInterna> = [
    {
      title: 'Status',
      dataIndex: 'lida',
      width: 90,
      render: (read: boolean) => (read ? <Tag color="default">Lida</Tag> : <Tag color="blue">Nova</Tag>),
    },
    {
      title: 'Fase',
      dataIndex: 'fase_disparo',
      width: 150,
      render: (value: string) => <Tag color="purple">{FASE_LABELS[value] ?? value}</Tag>,
    },
    {
      title: 'Título',
      dataIndex: 'titulo',
      ellipsis: true,
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      width: 130,
      render: (value: string) => TIPO_LABELS[value] ?? value,
    },
    {
      title: 'Prioridade',
      dataIndex: 'prioridade',
      width: 110,
      render: (value: string) => {
        const color = value === 'CRITICA' ? 'red' : value === 'ALTA' ? 'orange' : 'default';
        return <Tag color={color}>{PRIORIDADE_LABELS[value] ?? value}</Tag>;
      },
    },
    {
      title: 'Referência',
      dataIndex: 'referencia_data',
      width: 120,
      render: (value: string) => dayjs(value).format('DD/MM/YYYY'),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 130,
      render: (_: unknown, record: NotificacaoInterna) => (
        <Button
          size="small"
          disabled={record.lida}
          loading={markingId === record.id}
          onClick={() => void handleMarkRead(record.id)}
        >
          Marcar lida
        </Button>
      ),
    },
  ];

  const unreadCount = notifications.filter((item) => !item.lida).length;

  return (
    <section aria-labelledby="notificacoes-internas-titulo" style={{ padding: 24 }}>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <div>
          <Title id="notificacoes-internas-titulo" level={3} style={{ marginBottom: 0 }}>
            Notificações Internas
          </Title>
          <Text type="secondary">Lembretes e escalonamentos das ações.</Text>
        </div>

        <Card>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px', alignItems: 'center' }}>
            <Text strong>Total: {notifications.length}</Text>
            <Text type="warning">
              Não lidas: {unreadCount}
            </Text>
            {unreadCount > 0 && (
              <Button
                size="small"
                loading={markingAll}
                onClick={() => void handleMarkAllRead()}
              >
                Marcar todas como lidas
              </Button>
            )}
          </div>
        </Card>

        <Card>
          <Table
            rowKey="id"
            dataSource={notifications}
            columns={columns}
            loading={loading}
            pagination={{ pageSize: 12 }}
            scroll={{ x: 760 }}
            expandable={{
              expandedRowRender: (record) => <Text>{record.mensagem}</Text>,
              rowExpandable: (record) => Boolean(record.mensagem),
            }}
          />
        </Card>
      </Space>
    </section>
  );
}
