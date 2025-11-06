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

import React from 'react';
import { Card, Button, Space, Tag, Typography, Popconfirm } from 'antd';
import {
  GoogleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  DisconnectOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

const GoogleIntegrationCard = ({ status, onConnect, onDisconnect }) => {
  if (!status) {
    return null;
  }

  const { connected, googleEmail, tokenExpiry, expiresInDays, isExpired } = status;

  // Estado: DESCONECTADO
  if (!connected) {
    return (
      <Card
        style={{
          borderColor: '#ff4d4f',
          backgroundColor: '#fff2f0',
          marginBottom: '16px',
        }}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space>
            <GoogleOutlined style={{ fontSize: '24px', color: '#ff4d4f' }} />
            <Title level={5} style={{ margin: 0 }}>
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
  const isExpiringSoon = expiresInDays !== null && expiresInDays <= 7;
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
      style={{
        borderColor: cardColor,
        backgroundColor: backgroundColor,
        marginBottom: '16px',
      }}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Space>
          <GoogleOutlined style={{ fontSize: '24px', color: cardColor }} />
          <Title level={5} style={{ margin: 0 }}>
            Integração Google Calendar
          </Title>
          <Tag color={isExpired ? 'error' : isExpiringSoon ? 'warning' : 'success'} icon={statusIcon}>
            {statusText}
          </Tag>
        </Space>

        <Space direction="vertical" size="small">
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
