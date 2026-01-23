/**
 * SessionExpiryWarning Component (CP5 - Issue #164)
 *
 * Exibe modal de aviso quando sessão está prestes a expirar (<5 min).
 *
 * Comportamento:
 * - Aparece automaticamente quando timeLeft < 300s
 * - Mostra countdown em tempo real
 * - Botões:
 *   - "Continuar logado": Renova sessão via /api/auth/ping/
 *   - "Sair agora": Logout imediato
 *
 * Uso:
 * ```tsx
 * import useSessionMonitor from '../hooks/useSessionMonitor';
 * import SessionExpiryWarning from '../components/SessionExpiryWarning';
 *
 * function App() {
 *   const session = useSessionMonitor();
 *
 *   return (
 *     <>
 *       <SessionExpiryWarning {...session} />
 *       {/ * resto da aplicação * /}
 *     </>
 *   );
 * }
 * ```
 *
 * Refs:
 * - CP5 (Issue #164): Monitor de sessão
 * - CP2: SESSION_COOKIE_AGE=7200 (2 horas)
 * - PA-06: Controle explícito (ISO 9241-110)
 */

import { Modal, Button, Space, Typography } from 'antd';
import { ClockCircleOutlined, LogoutOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text, Title } = Typography;

/**
 * SessionExpiryWarning props interface
 */
export interface SessionExpiryWarningProps {
  showWarning: boolean;
  timeLeft: number;
  renewSession: () => Promise<boolean>;
}

export function SessionExpiryWarning({ showWarning, timeLeft, renewSession }: SessionExpiryWarningProps): JSX.Element {
  const navigate = useNavigate();

  /**
   * Formata tempo restante em MM:SS.
   */
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  /**
   * Handler para renovar sessão.
   */
  const handleRenew = async (): Promise<void> => {
    const success = await renewSession();
    if (!success) {
      // Se falhar, redirecionar para login
      navigate('/login');
    }
  };

  /**
   * Handler para logout imediato.
   */
  const handleLogout = (): void => {
    navigate('/logout');
  };

  return (
    <Modal
      open={showWarning}
      closable={false}
      footer={null}
      centered
      maskClosable={false}
      width={400}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ textAlign: 'center' }}>
          <ClockCircleOutlined
            style={{ fontSize: 48, color: '#faad14' }}
          />
          <Title level={4} className="mt-4">
            Sua sessão está prestes a expirar
          </Title>
        </div>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            Tempo restante:
          </Text>
          <div>
            <Text
              strong
              style={{ fontSize: 32, color: '#faad14' }}
            >
              {formatTime(timeLeft)}
            </Text>
          </div>
        </div>

        <div style={{ textAlign: 'center' }}>
          <Text type="secondary">
            Deseja continuar conectado?
          </Text>
        </div>

        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={handleRenew}
            block
            size="large"
          >
            Continuar logado
          </Button>

          <Button
            danger
            icon={<LogoutOutlined />}
            onClick={handleLogout}
            block
          >
            Sair agora
          </Button>
        </Space>
      </Space>
    </Modal>
  );
}

export default SessionExpiryWarning;
