/**
 * SyncIndicator — Visual feedback for real-time data sync.
 *
 * Shows a subtle green dot (pulsing) + "updated X ago" timestamp.
 * Clicking the refresh icon triggers an immediate refetch.
 *
 * @module components/SyncIndicator
 * @see Epic #1032, Issue #1036
 */

import { SyncOutlined, CheckCircleFilled } from '@ant-design/icons';
import { Tooltip, Space } from 'antd';
import { useEffect, useState } from 'react';

interface SyncIndicatorProps {
  /** Timestamp of last successful data fetch (Date.now()) */
  lastUpdated: number | null;
  /** True while a fetch is in progress */
  loading?: boolean;
  /** Callback to trigger immediate refetch */
  onRefresh?: () => void;
}

function formatElapsed(timestamp: number | null): string {
  if (!timestamp) return 'Aguardando...';
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 5) return 'Agora';
  if (seconds < 60) return `há ${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `há ${minutes}min`;
  return `há ${Math.floor(minutes / 60)}h`;
}

export default function SyncIndicator({ lastUpdated, loading, onRefresh }: SyncIndicatorProps) {
  const [elapsed, setElapsed] = useState(() => formatElapsed(lastUpdated));

  // Update elapsed every 5s
  useEffect(() => {
    setElapsed(formatElapsed(lastUpdated));
    const id = setInterval(() => setElapsed(formatElapsed(lastUpdated)), 5_000);
    return () => clearInterval(id);
  }, [lastUpdated]);

  return (
    <Tooltip title={`Sincronização automática ativa — atualizado ${elapsed}`}>
      <Space size={4} style={{ fontSize: 12, color: '#8c8c8c', cursor: 'default' }}>
        {loading ? (
          <SyncOutlined spin style={{ color: '#1890ff', fontSize: 12 }} />
        ) : (
          <CheckCircleFilled style={{ color: '#52c41a', fontSize: 10 }} />
        )}
        <span>{elapsed}</span>
        {onRefresh && (
          <SyncOutlined
            onClick={onRefresh}
            style={{ cursor: 'pointer', color: '#1890ff', fontSize: 12, marginLeft: 4 }}
          />
        )}
      </Space>
    </Tooltip>
  );
}
