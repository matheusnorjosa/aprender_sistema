/**
 * MeetLink Component (PR19/RF06)
 *
 * Exibe botão para entrar em reunião do Google Meet quando meet_link presente.
 * Inclui botões:
 * - "Entrar na reunião": abre link em nova tab
 * - "Copiar link": copia URL para clipboard
 *
 * Uso:
 * <MeetLink href={solicitacao.meet_link} />
 */

import { Button, Space, message } from 'antd';
import { VideoCameraOutlined, CopyOutlined } from '@ant-design/icons';
import PropTypes from 'prop-types';

export function MeetLink({ href }) {
  if (!href) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(href)
      .then(() => {
        message.success('Link copiado para área de transferência!');
      })
      .catch(() => {
        message.error('Erro ao copiar link');
      });
  };

  return (
    <Space>
      <Button
        type="primary"
        icon={<VideoCameraOutlined />}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
      >
        Entrar na reunião
      </Button>
      <Button
        icon={<CopyOutlined />}
        onClick={handleCopy}
      >
        Copiar link
      </Button>
    </Space>
  );
}

MeetLink.propTypes = {
  href: PropTypes.string,
};

MeetLink.defaultProps = {
  href: null,
};

export default MeetLink;
