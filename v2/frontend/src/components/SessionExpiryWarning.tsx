/**
 * SessionExpiryWarning Component (CP5 - Issue #164)
 *
 * Exibe modal de aviso quando sessão está prestes a expirar (<5 min).
 *
 * Comportamento:
 * - Aparece automaticamente quando timeLeft < 300s
 * - Mostra countdown em tempo real
 * - Botões:
 *   - "Continuar logado": Renova sessão via /api/auth/ping/ (loading enquanto renova; se
 *     falhar por rede/5xx, o aviso continua e mostra o motivo — renewError)
 *   - "Sair agora": Logout imediato pelo mesmo caminho do "Sair" do cabeçalho (onLogout)
 *
 * Uso:
 * ```tsx
 * import useSessionMonitor from '../hooks/useSessionMonitor';
 * import SessionExpiryWarning from '../components/SessionExpiryWarning';
 *
 * function App() {
 *   const session = useSessionMonitor(handleLogout);
 *
 *   return (
 *     <>
 *       <SessionExpiryWarning {...session} onLogout={handleLogout} />
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

import { useState, type JSX } from 'react';
import { Modal, Button, Space, Typography, Alert } from 'antd';
import { ClockCircleOutlined, LogoutOutlined, CheckCircleOutlined } from '@ant-design/icons';

const { Text, Title } = Typography;

/**
 * SessionExpiryWarning props interface
 */
export interface SessionExpiryWarningProps {
  showWarning: boolean;
  timeLeft: number;
  renewSession: () => Promise<boolean>;
  /** Motivo da última falha ao renovar (rede/5xx); null quando não há. */
  renewError: string | null;
  /** Logout real do App (API de logout + limpa caches + tela de login). */
  onLogout: () => void;
}

export function SessionExpiryWarning({ showWarning, timeLeft, renewSession, renewError, onLogout }: SessionExpiryWarningProps): JSX.Element {
  const [renovando, setRenovando] = useState(false);

  /**
   * Formata tempo restante em MM:SS.
   */
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  /**
   * Handler para renovar sessão. Sessão já encerrada no servidor (401/403) é tratada pelo
   * useSessionMonitor (o App leva ao login); rede/5xx volta em renewError.
   */
  const handleRenew = async (): Promise<void> => {
    setRenovando(true);
    try {
      await renewSession();
    } finally {
      setRenovando(false);
    }
  };

  return (
    <Modal
      open={showWarning}
      closable={false}
      footer={null}
      centered
      maskClosable={false}
      width={400}
      aria-labelledby="session-expiry-title"
      aria-describedby="session-expiry-description"
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }} role="alertdialog">
        <div style={{ textAlign: 'center' }}>
          <ClockCircleOutlined
            style={{ fontSize: 48, color: '#faad14' }}
            aria-hidden="true"
          />
          <Title level={4} className="mt-4" id="session-expiry-title">
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

        <div style={{ textAlign: 'center' }} id="session-expiry-description">
          <Text type="secondary">
            Deseja continuar conectado?
          </Text>
        </div>

        {renewError && (
          <Alert
            type="error"
            showIcon
            message="Não foi possível renovar a sessão"
            description={renewError}
          />
        )}

        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            onClick={handleRenew}
            loading={renovando}
            block
            size="large"
          >
            Continuar logado
          </Button>

          <Button
            danger
            icon={<LogoutOutlined />}
            onClick={onLogout}
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
