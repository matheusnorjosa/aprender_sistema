/*
 * Localizadores baratos para os testes da Nova Solicitação.
 *
 * Com o CSS do antd na página, cada `getByRole(..., { name })` custa de centenas de ms a segundos no
 * jsdom: ele calcula o estilo de cada candidato e dos ancestrais (está visível? qual é o nome?), e o
 * cache de estilo cai a cada mudança no DOM. Dentro de `waitFor`, isso se repete a cada volta, e na CI
 * (bem mais lenta) estourava o timeout. Estes atalhos acham o MESMO elemento pela mesma fonte do nome
 * acessível (o texto, o aria-label ou o aria-labelledby), conferem a tag do papel e que nenhum atributo
 * o esconde. O nome acessível calculado segue conferido onde ele é o assunto do teste
 * (getByRole/toHaveAccessibleName, contagem de regiões, diálogo).
 */
import { within } from '@testing-library/react';
import { expect } from 'vitest';

export function semEsconder<T extends HTMLElement>(el: T | null, tag: string): T {
  expect(el?.tagName).toBe(tag);
  expect(el!.closest('[hidden], [aria-hidden="true"]')).toBeNull();
  return el!;
}

/**
 * Botão cujo nome acessível é o próprio texto (nenhum aria-label nem aria-labelledby por cima). Com
 * texto exato, também nenhum ícone com nome dentro dele (o "loading" do antd mudaria o nome).
 */
export function botaoDoTexto(texto: string | RegExp, dentro: HTMLElement = document.body): HTMLElement {
  const botao = semEsconder(within(dentro).getByText(texto).closest('button'), 'BUTTON');
  expect(botao).not.toHaveAttribute('aria-label');
  expect(botao).not.toHaveAttribute('aria-labelledby');
  if (typeof texto === 'string') {
    expect(botao.textContent?.trim()).toBe(texto);
    expect([...botao.querySelectorAll('[aria-label]')].filter((el) => !el.closest('[aria-hidden="true"]'))).toHaveLength(0);
  }
  return botao;
}

/** Cabeçalho do Collapse do antd (`div[role=button]`), nomeado pelo texto. */
export function cabecalhoDoTexto(texto: string | RegExp, dentro: HTMLElement = document.body): HTMLElement {
  const cabecalho = semEsconder(within(dentro).getByText(texto).closest<HTMLElement>('[role="button"]'), 'DIV');
  expect(cabecalho).not.toHaveAttribute('aria-label');
  expect(cabecalho).not.toHaveAttribute('aria-labelledby');
  return cabecalho;
}

/** Texto do elemento que dá nome via aria-labelledby. */
export const rotuloDe = (el: Element): string =>
  document.getElementById(el.getAttribute('aria-labelledby') ?? '')?.textContent ?? '';

/** Os cartões à vista (sections nomeadas pelo título) cujo nome casa. */
export const cartoes = (nome: RegExp = /^Evento \d/): HTMLElement[] =>
  [...document.querySelectorAll<HTMLElement>('section[aria-labelledby]')].filter(
    (s) => nome.test(rotuloDe(s)) && !s.closest('[hidden], [aria-hidden="true"]')
  );

/** O cartão "Evento N". */
export function cartao(n: number): HTMLElement {
  const achados = cartoes(new RegExp(`^Evento ${n}\\b`));
  expect(achados).toHaveLength(1);
  return semEsconder(achados[0]!, 'SECTION');
}

/** O único diálogo aberto (o rc-dialog fechado deixa o invólucro com `display: none` no estilo). */
export function dialogo(): HTMLElement {
  const abertos = [...document.querySelectorAll<HTMLElement>('[role="dialog"]')].filter(
    (d) => !d.closest('[hidden], [aria-hidden="true"], [style*="display: none"]')
  );
  expect(abertos).toHaveLength(1);
  return abertos[0]!;
}

export function titulo(n: number): HTMLElement {
  const h3 = cartao(n).querySelectorAll<HTMLElement>('h3');
  expect(h3).toHaveLength(1);
  return h3[0]!;
}

export const botaoRemover = (n: number): HTMLElement => {
  const botao = semEsconder(within(cartao(n)).getByLabelText(`Remover evento ${n}`), 'BUTTON');
  expect(botao).not.toHaveAttribute('aria-labelledby');
  return botao;
};

export const PERGUNTA_ACOMPANHA = 'O coordenador responsável vai acompanhar o evento?';

/** O radiogroup nomeado pela pergunta (via aria-labelledby). */
export function grupoDaPergunta(pergunta: string | RegExp, dentro: HTMLElement = document.body): HTMLElement {
  const rotulo = within(dentro).getByText(pergunta);
  expect(rotulo.id).not.toBe('');
  const grupos = [...dentro.querySelectorAll<HTMLElement>('[role="radiogroup"]')].filter(
    (g) => g.getAttribute('aria-labelledby') === rotulo.id
  );
  expect(grupos).toHaveLength(1);
  return semEsconder(grupos[0]!, 'DIV');
}
