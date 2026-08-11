/**
 * Página de Política de Privacidade (`/politica-privacidade`) — SCAFFOLD.
 *
 * Rota autenticada; o mesmo conteúdo aparece no Drawer do aviso de transparência no login
 * (acessível ao anônimo). Ver `components/lgpd/PoliticaPrivacidadeContent`.
 */
import type { JSX } from 'react';
import { Card, Space } from 'antd';
import PoliticaPrivacidadeContent from '../../components/lgpd/PoliticaPrivacidadeContent';

export default function PoliticaPrivacidadePage(): JSX.Element {
  return (
    <section className="p-6 bg-gray-100 min-h-full" aria-labelledby="politica-title">
      <Space direction="vertical" size="large" style={{ width: '100%', maxWidth: 820 }}>
        <Card>
          <div id="politica-title">
            <PoliticaPrivacidadeContent />
          </div>
        </Card>
      </Space>
    </section>
  );
}
