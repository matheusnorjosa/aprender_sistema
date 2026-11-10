/**
 * Página aberta de uma versão que saiu do ar.
 *
 * Depois de uma promoção, os pedaços de tela (chunks com hash no nome) da versão anterior deixam de
 * existir no servidor. Uma aba que ficou aberta continua com o index antigo e, ao abrir uma tela, pede
 * um pedaço que não existe: "Failed to fetch dynamically imported module". Recarregar busca a versão
 * nova (o service worker pede a página à rede primeiro). Para não entrar em laço se o servidor estiver
 * de fato fora, recarrega no máximo uma vez a cada 30 s; sem sessionStorage, não recarrega.
 */

const CHAVE = 'as:recarga-versao-nova';
const JANELA_MS = 30_000;
// Chrome/Edge, Safari, Firefox e a falha de preload de CSS do Vite.
const PADRAO =
  /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|Unable to preload CSS/i;

export function ehVersaoAntiga(erro: unknown): boolean {
  const mensagem = erro instanceof Error ? erro.message : typeof erro === 'string' ? erro : '';
  return PADRAO.test(mensagem);
}

interface Opcoes {
  agora?: number;
  recarregar?: () => void;
}

/** Recarrega a página uma vez quando o erro é de versão antiga. Devolve true se mandou recarregar. */
export function recarregarSeVersaoAntiga(erro: unknown, opcoes: Opcoes = {}): boolean {
  if (!ehVersaoAntiga(erro)) return false;
  const agora = opcoes.agora ?? Date.now();
  try {
    const ultima = Number(sessionStorage.getItem(CHAVE) ?? 0);
    if (agora - ultima < JANELA_MS) return false;
    sessionStorage.setItem(CHAVE, String(agora));
  } catch {
    return false;
  }
  (opcoes.recarregar ?? (() => window.location.reload()))();
  return true;
}
