/**
 * AS v2 - useOnlineStatus Hook (Issue #416)
 *
 * Hook to track browser online/offline status.
 * Uses navigator.onLine and online/offline events.
 *
 * Usage:
 * ```jsx
 * const isOnline = useOnlineStatus();
 *
 * if (!isOnline) {
 *   return <OfflineBanner />;
 * }
 * ```
 */

import { useState, useEffect } from 'react';

/**
 * Track browser online/offline status.
 * @returns {boolean} Whether the browser is online
 */
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

export default useOnlineStatus;
