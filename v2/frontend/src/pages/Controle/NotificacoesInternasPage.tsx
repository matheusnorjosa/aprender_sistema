import { useEffect, useState } from 'react';
import { Button, Card, Space, Table, Tag, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { listNotificacoesInternas, marcarNotificacaoLida, marcarTodasNotificacoesLidas } from '../../api/acoesNotificacao';
import type { NotificacaoInterna } from '../../types/acoesNotificacao';

const { Title, Text } = Typography;

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
      width: 90,
      render: (value: string) => <Tag color="purple">{value}</Tag>,
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
    },
    {
      title: 'Prioridade',
      dataIndex: 'prioridade',
      width: 110,
      render: (value: string) => {
        const color = value === 'CRITICA' ? 'red' : value === 'ALTA' ? 'orange' : 'default';
        return <Tag color={color}>{value}</Tag>;
      },
    },
    {
      title: 'Referência',
      dataIndex: 'referencia_data',
      width: 120,
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
    <main style={{ padding: 24 }}>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <div>
          <Title level={3} style={{ marginBottom: 0 }}>
            Notificações Internas
          </Title>
          <Text type="secondary">Inbox in-app para lembretes e escalonamentos das ações.</Text>
        </div>

        <Card>
          <Text strong>Total: {notifications.length}</Text>
          <Text style={{ marginLeft: 16 }} type="warning">
            Não lidas: {unreadCount}
          </Text>
          {unreadCount > 0 && (
            <Button
              size="small"
              style={{ marginLeft: 16 }}
              loading={markingAll}
              onClick={() => void handleMarkAllRead()}
            >
              Marcar todas como lidas
            </Button>
          )}
        </Card>

        <Card>
          <Table
            rowKey="id"
            dataSource={notifications}
            columns={columns}
            loading={loading}
            pagination={{ pageSize: 12 }}
            expandable={{
              expandedRowRender: (record) => <Text>{record.mensagem}</Text>,
              rowExpandable: (record) => Boolean(record.mensagem),
            }}
          />
        </Card>
      </Space>
    </main>
  );
}
