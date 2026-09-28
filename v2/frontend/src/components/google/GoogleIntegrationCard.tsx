/**
 * AS v2 — Google Integration Card (Sprint 1 - Issue #1)
 *
 * Componente para exibir status da integração OAuth Google Calendar.
 *
 * Estados:
 * - DESCONECTADO: Card vermelho com botão "Conectar conta Google"; se o sistema
 *   removeu a conexão (`reconnectRequired`, Google revogou o acesso — #2039),
 *   mostra antes um aviso de revogação.
 * - CONECTADO: Card verde com email, seletor de calendário e "Desconectar".
 *   Sem alarme de expiração: o access token dura 1h e o refresh token o renova sozinho.
 *
 * Props:
 * - status: { connected, googleEmail, defaultCalendarId, reconnectRequired, ... }
 * - onConnect: Função chamada ao clicar "Conectar"
 * - onDisconnect: Função chamada ao clicar "Desconectar"
 *
 * Refs:
 * - Sprint 1 (Issue #1): Frontend UI
 * - PA-06: Controle explícito (ISO 9241-110)
 */

import { useState, useEffect, type JSX } from 'react';
import { Alert, Card, Button, Space, Tag, Typography, Popconfirm, Select, message } from 'antd';
import {
  GoogleOutlined,
  CheckCircleOutlined,
  DisconnectOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import { fetchAPI } from '../../api/config';
import logger from '../../utils/logger';
import type { GoogleIntegrationStatus } from '../../types/gcal';

// Re-export do tipo de domínio (SSOT em types/gcal) para os consumidores que
// historicamente importavam `GoogleIntegrationStatus` deste módulo (ex.: testes).
export type { GoogleIntegrationStatus } from '../../types/gcal';

const { Text, Title } = Typography;

/**
 * Calendar item interface
 */
interface CalendarItem {
  id: string;
  summary: string;
  primary?: boolean;
}

/**
 * Calendário-sentinela do Google para o calendário principal do usuário.
 * Usado como fallback quando não há `defaultCalendarId` salvo — nunca o email,
 * pois email ≠ calendarId.
 */
const PRIMARY_CALENDAR_ID = 'primary';

/**
 * GoogleIntegrationCard props interface
 */
export interface GoogleIntegrationCardProps {
  status: GoogleIntegrationStatus | null;
  onConnect: () => void;
  onDisconnect: () => void;
  /**
   * Destino de publicação fixado pelo servidor (calendário oficial da organização, #1656):
   * sem seletor de calendário (nem chamada a `/calendars/`).
   */
  fixedCalendar?: boolean;
}

const GoogleIntegrationCard = ({
  status,
  onConnect,
  onDisconnect,
  fixedCalendar = false,
}: GoogleIntegrationCardProps): JSX.Element | null => {
  const [calendars, setCalendars] = useState<CalendarItem[]>([]);
  const [loadingCalendars, setLoadingCalendars] = useState(false);
  const [selectedCalendar, setSelectedCalendar] = useState<string | null>(null);
  const [savingCalendar, setSavingCalendar] = useState(false);
  // Extrair valores de status (ou usar defaults se status for null). `status`
  // pode ser null antes do fetch inicial; a renderização real só ocorre após o
  // early return abaixo, mas os hooks precisam rodar incondicionalmente.
  // `isExpired`/`expiresInDays`/`tokenExpiry` do status NÃO são usados: descrevem o
  // access token de 1h, que o refresh token renova sozinho — mostrá-los só empurrava
  // reconexões inúteis. Conta morta de verdade chega como `reconnectRequired` (#2039).
  const { connected, googleEmail, defaultCalendarId, reconnectRequired } = status ?? {
    connected: false,
    googleEmail: null,
    defaultCalendarId: null,
    reconnectRequired: false,
  };

  // Carregar calendários quando conectado (no modo fixo não há o que escolher)
  useEffect(() => {
    if (connected && !fixedCalendar) {
      void loadCalendars();
    }
  }, [connected, fixedCalendar]);

  // Atualizar calendário selecionado quando defaultCalendarId mudar.
  // Sem defaultCalendarId salvo, cair para o calendário principal ('primary'),
  // NUNCA o email — email ≠ calendarId (isso exibiria o email como se fosse um
  // calendário selecionado).
  useEffect(() => {
    setSelectedCalendar(defaultCalendarId || PRIMARY_CALENDAR_ID);
  }, [defaultCalendarId]);

  // Early return após todos os hooks
  if (!status) {
    return null;
  }

  const loadCalendars = async (): Promise<void> => {
    try {
      setLoadingCalendars(true);
      const data = await fetchAPI<{ calendars: CalendarItem[] }>('/integrations/google/calendars/');
      setCalendars(data.calendars || []);
    } catch (error) {
      logger.error('Erro ao carregar calendários:', error);
      const httpStatus = (error as { response?: { status?: number } }).response?.status;
      if (httpStatus === 503) {
        message.error('O Google Calendar demorou a responder. Tente novamente em instantes.');
      } else {
        message.error('Não foi possível carregar seus calendários');
      }
    } finally {
      setLoadingCalendars(false);
    }
  };

  const handleCalendarChange = async (calendarId: string): Promise<void> => {
    try {
      setSavingCalendar(true);
      await fetchAPI('/integrations/google/select-calendar/', {
        method: 'POST',
        body: JSON.stringify({ calendar_id: calendarId }),
      });
      setSelectedCalendar(calendarId);
      message.success('Calendário selecionado com sucesso');
    } catch (error) {
      logger.error('Erro ao salvar calendário:', error);
      message.error('Não foi possível salvar o calendário selecionado');
    } finally {
      setSavingCalendar(false);
    }
  };

  // Estado: DESCONECTADO
  if (!connected) {
    return (
      <Card
        className="mb-4"
        style={{
          borderColor: '#ff4d4f',
          backgroundColor: '#fff2f0',
        }}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space>
            <GoogleOutlined style={{ fontSize: '24px', color: '#ff4d4f' }} />
            <Title level={5} className="m-0">
              Integração Google Calendar
            </Title>
          </Space>

          {reconnectRequired && (
            <Alert
              type="warning"
              showIcon
              message="O Google revogou o acesso da sua conta ao sistema, então ela foi desconectada. Conecte de novo para voltar a publicar."
            />
          )}

          <Text type="secondary">
            Para publicar eventos no Google Calendar, conecte sua conta corporativa do Google.
          </Text>

          <Button
            type="primary"
            icon={<GoogleOutlined />}
            onClick={onConnect}
            size="large"
          >
            Conectar conta Google
          </Button>
        </Space>
      </Card>
    );
  }

  // Estado: CONECTADO
  const cardColor = '#52c41a'; // verde

  return (
    <Card
      className="mb-4"
      style={{
        borderColor: cardColor,
        backgroundColor: '#f6ffed', // verde claro
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Space>
          <GoogleOutlined style={{ fontSize: '24px', color: cardColor }} />
          <Title level={5} className="m-0">
            Integração Google Calendar
          </Title>
          <Tag color="success" icon={<CheckCircleOutlined style={{ color: cardColor }} />}>
            Conectado
          </Tag>
        </Space>

        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text>
            <strong>Conta conectada:</strong> {googleEmail}
          </Text>

          {/* Seletor de calendário (no modo fixo, só o destino oficial) */}
          {fixedCalendar ? (
            <Text>
              <CalendarOutlined /> Os eventos são publicados no calendário oficial da organização.
            </Text>
          ) : (
            <div className="mt-2">
              <Text strong className="block mb-2">
                <CalendarOutlined /> Calendário para eventos:
              </Text>
              <Select
                style={{ width: '100%' }}
                placeholder="Selecione um calendário"
                value={selectedCalendar}
                onChange={handleCalendarChange}
                loading={loadingCalendars || savingCalendar}
                options={calendars.map((cal) => ({
                  value: cal.id,
                  label: (
                    <span>
                      {cal.summary}
                      {cal.primary && <Tag color="blue" className="ml-2">Principal</Tag>}
                    </span>
                  ),
                }))}
                notFoundContent={loadingCalendars ? 'Carregando...' : 'Nenhum calendário encontrado'}
              />
              {!defaultCalendarId && (
                <Text type="secondary" className="block mt-1" style={{ fontSize: '12px' }}>
                  Usando calendário principal por padrão
                </Text>
              )}
            </div>
          )}
        </Space>

        <Space>
          <Popconfirm
            title="Desconectar conta Google?"
            description="Você não poderá publicar eventos até reconectar."
            onConfirm={onDisconnect}
            okText="Sim, desconectar"
            cancelText="Cancelar"
            okButtonProps={{ danger: true }}
          >
            <Button icon={<DisconnectOutlined />}>
              Desconectar
            </Button>
          </Popconfirm>
        </Space>
      </Space>
    </Card>
  );
};

export default GoogleIntegrationCard;
