import type { CSSProperties, ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { Alert } from 'antd';
import { Link } from 'react-router-dom';
import { getMe } from '../api/availability';
import { computePermissions } from '../hooks/usePermissions';

export const DAT_IMPORTS_CENTRALIZED_MESSAGE =
  'Importações foram centralizadas em DAT > Importações.';

interface DatImportsCentralizedBannerProps {
  className?: string;
  style?: CSSProperties;
}

export default function DatImportsCentralizedBanner({
  className,
  style,
}: DatImportsCentralizedBannerProps): JSX.Element {
  const [canAccessDatImports, setCanAccessDatImports] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadPermissions(): Promise<void> {
      try {
        const user = await getMe();
        if (active) {
          setCanAccessDatImports(computePermissions(user).canDAT);
        }
      } catch {
        if (active) {
          setCanAccessDatImports(false);
        }
      }
    }

    void loadPermissions();

    return () => {
      active = false;
    };
  }, []);

  const description: ReactNode = canAccessDatImports ? (
    <>
      Importações foram centralizadas em{' '}
      <Link to="/dat/importacoes">DAT &gt; Importações</Link>.
    </>
  ) : (
    DAT_IMPORTS_CENTRALIZED_MESSAGE
  );

  return (
    <Alert
      aria-label={DAT_IMPORTS_CENTRALIZED_MESSAGE}
      className={className}
      style={style}
      type="info"
      showIcon
      message={description}
    />
  );
}
