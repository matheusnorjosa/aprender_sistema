/**
 * AS v2 - OfflineBanner Component (Issue #416)
 *
 * Shows a warning banner when the user is offline.
 * Automatically shows/hides based on connection status.
 *
 * Usage:
 * ```jsx
 * <OfflineBanner />
 * ```
 */

import { Alert } from 'antd';
import { WifiOutlined } from '@ant-design/icons';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

/**
 * Banner that shows when user is offline.
 */
export function OfflineBanner() {
  const isOnline = useOnlineStatus();

  if (isOnline) {
    return null;
  }

  return (
    <Alert
      message="Voce esta offline"
      description="Algumas funcionalidades podem estar limitadas. Verifique sua conexao."
      type="warning"
      icon={<WifiOutlined />}
      banner
      closable={false}
      style={{ borderRadius: 0 }}
    />
  );
}

export default OfflineBanner;
