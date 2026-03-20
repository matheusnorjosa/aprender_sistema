import { useState, useCallback, useRef, useEffect } from 'react';
import { Layout, Button, Badge, Popover, List, Tag, Empty, Spin, Typography, message } from 'antd';
import { Link } from 'react-router-dom';
import {
  UserOutlined,
  LogoutOutlined,
  MenuOutlined,
  CloseOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { listNotificacoesInternas, marcarNotificacaoLida } from '../api/acoesNotificacao';
import type { NotificacaoInterna } from '../types/acoesNotificacao';

const { Header } = Layout;
const { Text } = Typography;

interface AppHeaderProps {
  user: { name?: string; username?: string };
  canAcoesInternas: boolean;
  unreadNotifications: number;
  isMobile: boolean;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  onLogout: () => void;
  colors: {
    cardBackground: string;
    borderDefault: string;
  };
}

export function AppHeader({
  user,
  canAcoesInternas,
  unreadNotifications,
  isMobile,
  sidebarCollapsed,
  toggleSidebar,
  onLogout,
  colors,
}: AppHeaderProps): JSX.Element {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [popoverNotifs, setPopoverNotifs] = useState<NotificacaoInterna[]>([]);
  const [popoverLoading, setPopoverLoading] = useState(false);

  const isMountedRef = useRef(true);
  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  const handlePopoverOpenChange = useCallback(async (open: boolean) => {
    setPopoverOpen(open);
    if (open) {
      setPopoverLoading(true);
      try {
        const data = await listNotificacoesInternas({ page_size: 8, ordering: '-created_at' });
        if (isMountedRef.current) setPopoverNotifs(data.results);
      } catch {
        // silently fail — badge still works
      } finally {
        if (isMountedRef.current) setPopoverLoading(false);
      }
    }
  }, []);

  const handlePopoverMarkRead = useCallback(async (notifId: number) => {
    try {
      await marcarNotificacaoLida(notifId);
      setPopoverNotifs((prev) => prev.map((n) => (n.id === notifId ? { ...n, lida: true } : n)));
      window.dispatchEvent(new Event('notificacoes:refresh'));
    } catch {
      message.error('Erro ao marcar notificação como lida');
    }
  }, []);

  return (
    <Header
      className="flex items-center justify-between w-full"
      aria-label="Perfil do usuario e acoes"
      style={{
        background: colors.cardBackground,
        padding: '0 24px',
        borderBottom: `1px solid ${colors.borderDefault}`,
      }}
    >
      <Button
        type="text"
        icon={sidebarCollapsed ? <MenuOutlined /> : <CloseOutlined />}
        onClick={toggleSidebar}
        aria-label={sidebarCollapsed ? 'Abrir menu' : 'Fechar menu'}
        className="mobile-menu-toggle"
        style={{
          fontSize: '18px',
          display: isMobile ? 'flex' : 'none',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      />
      <div className="flex items-center gap-4" style={{ whiteSpace: 'nowrap', marginLeft: 'auto' }}>
        <div className="flex items-center gap-2">
          <UserOutlined />
          <Text strong>{user.name || user.username || 'Usuário'}</Text>
        </div>
        {canAcoesInternas && (
          <Popover
            trigger="click"
            open={popoverOpen}
            onOpenChange={(open) => void handlePopoverOpenChange(open)}
            placement="bottomRight"
            overlayStyle={{ width: 'min(360px, calc(100vw - 16px))' }}
            overlayClassName="notif-popover"
            arrow={{ pointAtCenter: true }}
            afterOpenChange={(visible) => {
              if (visible && window.innerWidth <= 480) {
                const el = document.querySelector('.notif-popover') as HTMLElement;
                if (el) { el.style.left = '8px'; el.style.right = '8px'; }
              }
            }}
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Notificações</span>
                {unreadNotifications > 0 && <Tag color="blue">{unreadNotifications} não lida{unreadNotifications > 1 ? 's' : ''}</Tag>}
              </div>
            }
            content={
              <div>
                {popoverLoading ? (
                  <div style={{ textAlign: 'center', padding: 24 }}><Spin size="small" /></div>
                ) : popoverNotifs.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Nenhuma notificação" />
                ) : (
                  <List
                    size="small"
                    dataSource={popoverNotifs}
                    renderItem={(item: NotificacaoInterna) => (
                      <List.Item
                        style={{
                          background: item.lida ? undefined : 'rgba(0, 107, 82, 0.06)',
                          padding: '8px 12px',
                          cursor: item.lida ? 'default' : 'pointer',
                        }}
                        onClick={() => { if (!item.lida) void handlePopoverMarkRead(item.id as number); }}
                      >
                        <List.Item.Meta
                          title={
                            <span style={{ fontSize: 13 }}>
                              {!item.lida && <Badge status="processing" style={{ marginRight: 6 }} />}
                              {item.titulo}
                            </span>
                          }
                          description={
                            <span style={{ fontSize: 12 }}>
                              <Tag color="purple" style={{ fontSize: 11 }}>{item.fase_disparo}</Tag>
                              {item.prioridade === 'CRITICA' ? <Tag color="red" style={{ fontSize: 11 }}>CRÍTICA</Tag>
                                : item.prioridade === 'ALTA' ? <Tag color="orange" style={{ fontSize: 11 }}>ALTA</Tag>
                                : null}
                            </span>
                          }
                        />
                      </List.Item>
                    )}
                  />
                )}
                <div style={{ textAlign: 'center', borderTop: '1px solid #f0f0f0', paddingTop: 8, marginTop: 4 }}>
                  <Link to="/notificacoes-internas" onClick={() => setPopoverOpen(false)}>
                    Ver todas as notificações
                  </Link>
                </div>
              </div>
            }
          >
            <span style={{ cursor: 'pointer' }} aria-label="Notificações">
              <Badge count={unreadNotifications} size="small" offset={[2, 0]}>
                <BellOutlined style={{ fontSize: 18, color: unreadNotifications > 0 ? '#006B52' : undefined }} />
              </Badge>
            </span>
          </Popover>
        )}
        <Button
          type="primary"
          danger
          icon={<LogoutOutlined />}
          onClick={onLogout}
        >
          Sair
        </Button>
      </div>
    </Header>
  );
}
