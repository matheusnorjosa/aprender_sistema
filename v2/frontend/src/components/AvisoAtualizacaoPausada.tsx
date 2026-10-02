/**
 * Aviso das telas que se atualizam sozinhas: o servidor respondeu 429 (muitas requisições)
 * e o polling foi suspenso por um prazo (hooks/usePolling.ts, `pausado`). Um aviso só,
 * discreto e lido por leitor de tela (role=status), no lugar de um erro a cada tentativa.
 */
import type { JSX } from 'react';
import { Alert } from 'antd';

export const TEXTO_ATUALIZACAO_PAUSADA = 'Atualização automática pausada por alguns instantes.';

export default function AvisoAtualizacaoPausada(): JSX.Element {
  return <Alert type="info" showIcon role="status" message={TEXTO_ATUALIZACAO_PAUSADA} />;
}
