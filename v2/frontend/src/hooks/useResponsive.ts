import { useState, useEffect, useCallback, useRef } from 'react';
import { LAYOUT } from '../constants';

const getIsMobile = () =>
  typeof window !== 'undefined' && window.innerWidth < LAYOUT.MOBILE_BREAKPOINT;

interface UseResponsiveReturn {
  isMobile: boolean;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

/**
 * Responsive layout hook that tracks mobile breakpoint
 * without overriding the user's manual sidebar preference.
 *
 * Only auto-collapses/expands on actual mobile↔desktop transitions.
 */
export function useResponsive(): UseResponsiveReturn {
  const [isMobile, setIsMobile] = useState(getIsMobile);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(getIsMobile);
  const prevMobileRef = useRef(isMobile);

  useEffect(() => {
    const handleResize = () => {
      const mobile = getIsMobile();
      setIsMobile(mobile);

      // Only auto-toggle sidebar on actual mobile↔desktop transition
      if (mobile !== prevMobileRef.current) {
        setSidebarCollapsed(mobile);
        prevMobileRef.current = mobile;
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  return { isMobile, sidebarCollapsed, toggleSidebar };
}
