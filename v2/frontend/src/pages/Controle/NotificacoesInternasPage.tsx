/**
 * Notificações Internas: lembretes e escalonamentos das ações.
 *
 * Sem rolagem horizontal (G30): ResponsiveTable. Sempre na linha o status, o título e as ações
 * (AcoesLinha: "Marcar lida"; no celular, o menu "Mais ações"); Referência sobe a partir de sm,
 * Prioridade de md, Fase de lg e Tipo de xxl. A mensagem fica só na linha expandida, como antes.
 */
import { useEffect, useState, type JSX } from 'react';
import { Button, Card, Grid, Space, Tag, Typography, message } from 'antd';
import { CheckOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import ResponsiveTable, { VISIVEL_A_PARTIR, type ColunaResponsiva } from '../../components/ResponsiveTable';
import { AcoesLinha, larguraAcoesLinha } from '../../components/AcoesLinha';

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
  const [markingAll, setMarkingAll] = useState<boolean>(false);
  const acoesCompactas = !Grid.useBreakpoint().sm;

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
    try {
      await marcarNotificacaoLida(notificationId);
      // O ícone do AcoesLinha não tem estado de carregando: a confirmação vem em mensagem.
      message.success('Notificação marcada como lida.');
      await loadNotifications();
      window.dispatchEvent(new Event('notificacoes:refresh'));
    } catch (error) {
      message.error(`Erro ao marcar notificação como lida: ${(error as Error).message}`);
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

  const columns: ColunaResponsiva<NotificacaoInterna>[] = [
    {
      title: 'Status',
      dataIndex: 'lida',
      key: 'lida',
      width: 80,
      render: (read: boolean) => (read ? <Tag color="default">Lida</Tag> : <Tag color="blue">Nova</Tag>),
    },
    {
      title: 'Título',
      dataIndex: 'titulo',
      key: 'titulo',
      ellipsis: true,
    },
    {
      title: 'Fase',
      dataIndex: 'fase_disparo',
      key: 'fase_disparo',
      responsive: VISIVEL_A_PARTIR.lg,
      width: 168,
      render: (value: string) => <Tag color="purple">{FASE_LABELS[value] ?? value}</Tag>,
    },
    {
      title: 'Tipo',
      dataIndex: 'tipo',
      key: 'tipo',
      responsive: VISIVEL_A_PARTIR.xxl,
      width: 130,
      render: (value: string) => TIPO_LABELS[value] ?? value,
    },
    {
      title: 'Prioridade',
      dataIndex: 'prioridade',
      key: 'prioridade',
      responsive: VISIVEL_A_PARTIR.md,
      width: 104,
      render: (value: string) => {
        const color = value === 'CRITICA' ? 'red' : value === 'ALTA' ? 'orange' : 'default';
        return <Tag color={color}>{PRIORIDADE_LABELS[value] ?? value}</Tag>;
      },
    },
    {
      title: 'Referência',
      dataIndex: 'referencia_data',
      key: 'referencia_data',
      responsive: VISIVEL_A_PARTIR.sm,
      width: 112,
      render: (value: string) => dayjs(value).format('DD/MM/YYYY'),
    },
    {
      // A mensagem abria na linha expandida e continua lá: nunca entra na linha.
      title: 'Mensagem',
      dataIndex: 'mensagem',
      key: 'mensagem',
      responsive: VISIVEL_A_PARTIR.detalhe,
      render: (value: string) => value || '-',
    },
    {
      title: 'Ações',
      key: 'actions',
      width: larguraAcoesLinha(1, acoesCompactas),
      // Já lida: nada a fazer na linha (antes, o botão ficava desabilitado).
      render: (_: unknown, record: NotificacaoInterna) =>
        record.lida ? null : (
          <AcoesLinha
            compacto={acoesCompactas}
            alvo={record.titulo}
            acoes={[
              { chave: 'marcar-lida', rotulo: 'Marcar lida', icone: <CheckOutlined />, onClick: () => void handleMarkRead(record.id) },
            ]}
          />
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
          <ResponsiveTable<NotificacaoInterna>
            rowKey="id"
            dataSource={notifications}
            columns={columns}
            loading={loading}
            pagination={{ pageSize: 12 }}
            nomeDaLinha={(notificacao) => notificacao.titulo}
          />
        </Card>
      </Space>
    </section>
  );
}
