/**
 * Componente de Legenda Melhorada.
 *
 * Design: paginadisponibilidade/screen.png
 * - Exibe códigos de disponibilidade com cores e ícones
 * - Layout responsivo e organizado
 */

import { Card, Tag, Space, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  StopOutlined,
  MinusCircleOutlined,
  CarOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { CODE_LABEL } from './codes';

const { Text } = Typography;

// Mapeamento de códigos para cores e ícones
const CODE_CONFIG = {
  'T': { color: '#ff4d4f', label: 'Bloqueio Total', icon: <StopOutlined /> },
  'P': { color: '#fa8c16', label: 'Bloqueio Parcial', icon: <MinusCircleOutlined /> },
  'D': { color: '#1890ff', label: 'Deslocamento', icon: <CarOutlined /> },
  'X': { color: '#f5222d', label: 'Conflito', icon: <CloseCircleOutlined /> },
  'E': { color: '#52c41a', label: 'Evento', icon: <CheckCircleOutlined /> },
  'M': { color: '#faad14', label: 'Mais de um evento', icon: <ClockCircleOutlined /> },
  '': { color: '#d9d9d9', label: 'Vazio', icon: <WarningOutlined /> },
};

export default function Legend({ legend }) {
  // Usar legend do backend ou fallback local
  const map = legend ?? CODE_LABEL;

  return (
    <Card
      title="Legenda"
      size="small"
      style={{ marginBottom: 16 }}
      bodyStyle={{ padding: '12px' }}
    >
      <Space wrap size={[8, 8]}>
        {Object.entries(map).map(([code, label]) => {
          // Pular código vazio se não estiver na config
          if (!code && !CODE_CONFIG['']) return null;

          const config = CODE_CONFIG[code] || CODE_CONFIG[''];

          return (
            <Tag
              key={code || 'empty'}
              icon={config.icon}
              style={{
                borderColor: config.color,
                color: config.color,
                fontSize: '14px',
                padding: '4px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Text strong style={{ color: config.color }}>{code || '∅'}</Text>
              <Text style={{ color: config.color }}>
                {label || config.label}
              </Text>
            </Tag>
          );
        })}
      </Space>
    </Card>
  );
}
