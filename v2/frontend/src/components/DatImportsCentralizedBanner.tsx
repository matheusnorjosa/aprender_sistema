import type { CSSProperties, JSX } from 'react';
import { useEffect, useState } from 'react';
import { Alert } from 'antd';
import { Link } from 'react-router';
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
}: DatImportsCentralizedBannerProps): JSX.Element | null {
  const [canAccessDatImports, setCanAccessDatImports] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadPermissions(): Promise<void> {
      try {
        const user = await getMe();
        if (active) {
          // Importação pela tela: só superusuário (decisão do dono, 02/10/2026).
          setCanAccessDatImports(computePermissions(user).isAdmin);
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

  // Quem não é superusuário não tem a tela DAT > Importações: o aviso não aparece.
  if (!canAccessDatImports) return null;

  return (
    <Alert
      aria-label={DAT_IMPORTS_CENTRALIZED_MESSAGE}
      {...(className !== undefined && { className })}
      {...(style !== undefined && { style })}
      type="info"
      showIcon
      message={
        <>
          Importações foram centralizadas em{' '}
          <Link to="/dat/importacoes">DAT &gt; Importações</Link>.
        </>
      }
    />
  );
}
