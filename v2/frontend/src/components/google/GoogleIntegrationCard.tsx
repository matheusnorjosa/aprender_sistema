/**
 * AS v2 — Google Integration Card (Sprint 1 - Issue #1)
 *
 * Componente para exibir status da integração OAuth Google Calendar.
 *
 * Estados:
 * - DESCONECTADO: Card vermelho com botão "Conectar conta Google"
 * - CONECTADO: Card verde com email, data, botão "Gerenciar"
 *
 * Props:
 * - status: { connected, googleEmail, tokenExpiry, expiresInDays, isExpired }
 * - onConnect: Função chamada ao clicar "Conectar"
 * - onDisconnect: Função chamada ao clicar "Desconectar"
 *
 * Refs:
 * - Sprint 1 (Issue #1): Frontend UI
 * - PA-06: Controle explícito (ISO 9241-110)
 */

import { useState, useEffect } from 'react';
import { Card, Button, Space, Tag, Typography, Popconfirm, Select, message } from 'antd';
import {
  GoogleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  DisconnectOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import api from '../../api';
import logger from '../../utils/logger';

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
 * Google integration status interface
 */
export interface GoogleIntegrationStatus {
  connected: boolean;
  googleEmail?: string | null;
  tokenExpiry?: string | null;
  expiresInDays?: number | null;
  isExpired?: boolean;
  defaultCalendarId?: string | null;
}

/**
 * GoogleIntegrationCard props interface
 */
export interface GoogleIntegrationCardProps {
  status: GoogleIntegrationStatus | null;
  onConnect: () => void;
  onDisconnect: () => void;
}

const GoogleIntegrationCard = ({ status, onConnect, onDisconnect }: GoogleIntegrationCardProps): JSX.Element | null => {
  const [calendars, setCalendars] = useState<CalendarItem[]>([]);
  const [loadingCalendars, setLoadingCalendars] = useState(false);
  const [selectedCalendar, setSelectedCalendar] = useState<string | null>(null);
  const [savingCalendar, setSavingCalendar] = useState(false);

  // Extrair valores de status (ou usar defaults se status for null)
  const { connected, googleEmail, tokenExpiry, expiresInDays, isExpired, defaultCalendarId } = status || {};

  // Carregar calendários quando conectado
  useEffect(() => {
    if (connected && !isExpired) {
      loadCalendars();
    }
  }, [connected, isExpired]);

  // Atualizar calendário selecionado quando defaultCalendarId mudar
  useEffect(() => {
    if (defaultCalendarId) {
      setSelectedCalendar(defaultCalendarId);
    } else if (googleEmail) {
      // Se não houver defaultCalendarId, usar email como fallback
      setSelectedCalendar(googleEmail);
    }
  }, [defaultCalendarId, googleEmail]);

  // Early return após todos os hooks
  if (!status) {
    return null;
  }

  const loadCalendars = async (): Promise<void> => {
    try {
      setLoadingCalendars(true);
      const response = await api.get<{ calendars: CalendarItem[] }>('/integrations/google/calendars/');
      setCalendars(response.data.calendars || []);
    } catch (error) {
      logger.error('Erro ao carregar calendários:', error);
      message.error('Não foi possível carregar seus calendários');
    } finally {
      setLoadingCalendars(false);
    }
  };

  const handleCalendarChange = async (calendarId: string): Promise<void> => {
    try {
      setSavingCalendar(true);
      await api.post('/integrations/google/select-calendar/', {
        calendar_id: calendarId,
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
  const isExpiringSoon = expiresInDays !== null && expiresInDays !== undefined && expiresInDays <= 7;
  const cardColor = isExpired
    ? '#ff4d4f' // vermelho
    : isExpiringSoon
    ? '#faad14' // amarelo
    : '#52c41a'; // verde

  const backgroundColor = isExpired
    ? '#fff2f0' // vermelho claro
    : isExpiringSoon
    ? '#fffbe6' // amarelo claro
    : '#f6ffed'; // verde claro

  const statusText = isExpired
    ? 'Expirado (reconecte sua conta)'
    : isExpiringSoon
    ? `Expira em ${expiresInDays} dias`
    : 'Conectado';

  const statusIcon = isExpired ? (
    <WarningOutlined style={{ color: cardColor }} />
  ) : (
    <CheckCircleOutlined style={{ color: cardColor }} />
  );

  return (
    <Card
      className="mb-4"
      style={{
        borderColor: cardColor,
        backgroundColor: backgroundColor,
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Space>
          <GoogleOutlined style={{ fontSize: '24px', color: cardColor }} />
          <Title level={5} className="m-0">
            Integração Google Calendar
          </Title>
          <Tag color={isExpired ? 'error' : isExpiringSoon ? 'warning' : 'success'} icon={statusIcon}>
            {statusText}
          </Tag>
        </Space>

        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text>
            <strong>Conta conectada:</strong> {googleEmail}
          </Text>
          {tokenExpiry && (
            <Text type="secondary">
              <strong>Token expira em:</strong>{' '}
              {new Date(tokenExpiry).toLocaleDateString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          )}

          {/* Seletor de calendário */}
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
              disabled={isExpired}
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
        </Space>

        <Space>
          {isExpired && (
            <Button
              type="primary"
              icon={<GoogleOutlined />}
              onClick={onConnect}
              danger
            >
              Reconectar conta
            </Button>
          )}

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
