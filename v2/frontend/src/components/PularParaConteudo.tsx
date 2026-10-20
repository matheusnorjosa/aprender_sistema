import type { JSX, MouseEvent } from 'react';

/**
 * "Pular para o conteúdo" (WCAG 2.4.1). O `href="#main"` fica para quem abre em outra aba, mas o
 * clique não navega: a âncora nativa empurrava uma entrada sem o estado do roteador, e o Voltar até
 * ela escapava do `useBlocker` (a Nova Solicitação saía sem perguntar). Só move o foco.
 */
export function PularParaConteudo(): JSX.Element {
  const pular = (event: MouseEvent<HTMLAnchorElement>): void => {
    event.preventDefault();
    const conteudo = document.getElementById('main');
    if (!conteudo) return;
    if (!conteudo.hasAttribute('tabindex')) conteudo.setAttribute('tabindex', '-1');
    conteudo.focus();
  };
  return (
    <a className="skip-link" href="#main" onClick={pular}>
      Pular para o conteúdo principal
    </a>
  );
}
