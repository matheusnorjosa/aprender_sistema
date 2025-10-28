/**
 * MeetLink - Componente reutilizável para exibir link do Google Meet
 *
 * Props:
 * - href: string | null | undefined - URL do Google Meet
 *
 * Features:
 * - Botão "Entrar na reunião" (abre em nova aba)
 * - Botão "Copiar link" (copia para clipboard)
 * - Retorna null se href não existir
 *
 * Uso:
 * <MeetLink href={solicitacao.meet_link} />
 */

import { Button, Space, message } from 'antd';
import { VideoCameraOutlined, CopyOutlined } from '@ant-design/icons';

export function MeetLink({ href }) {
  if (!href) return null;

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(href);
      message.success('Link copiado para a área de transferência!');
    } catch (error) {
      message.error('Erro ao copiar link');
    }
  };

  return (
    <Space size="small">
      <Button
        type="primary"
        size="small"
        icon={<VideoCameraOutlined />}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
      >
        Entrar na reunião
      </Button>
      <Button
        size="small"
        icon={<CopyOutlined />}
        onClick={handleCopyLink}
        title="Copiar link"
      />
    </Space>
  );
}
