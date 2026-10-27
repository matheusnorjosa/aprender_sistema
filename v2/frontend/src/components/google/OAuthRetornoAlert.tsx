/**
 * Aviso da volta do OAuth do Google (?google=connected | ?google=error&reason=…).
 *
 * O backend (views_oauth.py) volta para a tela de origem com esses parâmetros, tanto do callback
 * quanto do início da conexão. As telas que iniciam a conexão (Publicar na agenda e Pré-agenda)
 * mostram o mesmo texto para o mesmo motivo.
 */
import type { JSX } from 'react';
import { Alert } from 'antd';

import type { OAuthRetorno } from '../../utils/oauthRetorno';

const OAUTH_ERROR_TEXT: Record<string, string> = {
  access_denied:
    'Você não autorizou o acesso à sua conta Google. Para publicar, conecte de novo e aceite as permissões.',
  validation:
    'Não foi possível validar essa conta Google. Conecte com a sua conta corporativa (e-mail de trabalho).',
  invalid_state: 'A conexão com o Google expirou ou foi interrompida. Tente conectar de novo.',
  // Item 38: o início do OAuth também volta com este motivo; o alerta da DAT logo abaixo diz o que fazer.
  no_setor_scope: 'A conta Google não foi conectada porque seu cadastro não tem setor vigente.',
  server_error: 'Não foi possível falar com o Google agora. Tente conectar de novo em alguns minutos.',
};
const OAUTH_ERROR_FALLBACK =
  'Não foi possível conectar sua conta Google. Tente de novo; se o erro continuar, avise o Controle.';

export function OAuthRetornoAlert({
  retorno,
  textoSucesso,
}: {
  retorno: OAuthRetorno;
  textoSucesso: string;
}): JSX.Element {
  if (retorno.ok) return <Alert type="success" role="status" showIcon message={textoSucesso} />;
  return (
    <Alert
      type="error"
      showIcon
      message={(retorno.reason && OAUTH_ERROR_TEXT[retorno.reason]) || OAUTH_ERROR_FALLBACK}
    />
  );
}
