/** Volta do OAuth do Google: `?google=connected` ou `?google=error&reason=…` (views_oauth.py). */
export type OAuthRetorno = { ok: true } | { ok: false; reason: string | null };

/** Lê o retorno do OAuth de uma query string; null quando não é uma volta do OAuth. */
export function lerOAuthRetorno(search: string): OAuthRetorno | null {
  const params = new URLSearchParams(search);
  const google = params.get('google');
  if (!google) return null;
  return google === 'connected' ? { ok: true } : { ok: false, reason: params.get('reason') };
}
