/**
 * Aviso das telas que se atualizam sozinhas: o servidor respondeu 429 (muitas requisições)
 * e o polling foi suspenso por um prazo (hooks/usePolling.ts, `pausado`). Um aviso só,
 * discreto e lido por leitor de tela (role=status), no lugar de um erro a cada tentativa.
 *
 * `cargaFalhou`: o 429 veio numa carga que a própria pessoa pediu (abrir a tela, filtrar,
 * trocar de página, recarregar depois de uma ação). Aí o aviso diz que a lista não carregou
 * e que a tela pode não corresponder ao pedido (role=alert).
 */
import type { JSX } from 'react';
import { Alert } from 'antd';

export const TEXTO_ATUALIZACAO_PAUSADA = 'Atualização automática pausada por alguns instantes.';
export const TEXTO_CARGA_NAO_ATENDIDA =
  'Não foi possível carregar agora: muitos pedidos em pouco tempo. O que está na tela pode estar ' +
  'desatualizado ou não corresponder ao filtro. A tela tenta de novo sozinha em instantes.';

interface AvisoAtualizacaoPausadaProps {
  cargaFalhou?: boolean;
}

export default function AvisoAtualizacaoPausada({ cargaFalhou = false }: AvisoAtualizacaoPausadaProps): JSX.Element {
  if (cargaFalhou) {
    return <Alert type="warning" showIcon role="alert" message={TEXTO_CARGA_NAO_ATENDIDA} />;
  }
  return <Alert type="info" showIcon role="status" message={TEXTO_ATUALIZACAO_PAUSADA} />;
}
