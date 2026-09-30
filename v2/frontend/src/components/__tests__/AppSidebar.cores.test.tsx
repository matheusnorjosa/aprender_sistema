/**
 * Sidebar recolhida (992 a 1279 px, só ícones): a página atual precisa ficar marcada mesmo
 * quando ela está dentro de um submenu (revisão adversarial do C1, lente C).
 *
 * O AntD marca o submenu pai com `.ant-menu-submenu-selected`, mas o App.css (tema claro)
 * força título e ícone de todo submenu para branco com `!important`. O jsdom não aplica a
 * cascata de verdade (não calcula especificidade), então o teste confere as regras do
 * App.css: o título do submenu selecionado tem o mesmo fundo e a mesma cor do submenu aberto
 * e do item selecionado, com `!important`, e o seletor casa com o DOM que o AntD gera.
 * A regra nova vence a que força branco por especificidade (uma classe a mais).
 *
 * Foco visível nos links do menu (WCAG 2.4.7 e 1.4.11): o reset do AntD tira o outline do
 * <a>, e agora o foco é levado ao menu (sidebar sobreposta). O anel tem duas cores (técnica
 * C40): em qualquer fundo do menu, nos dois temas, uma delas dá 3:1 ou mais.
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { MemoryRouter } from 'react-router';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, test } from 'vitest';

import { AppSidebar } from '../AppSidebar';
import type { Permissions } from '../../hooks/usePermissions';

// `?raw` de CSS volta vazio no Vitest (CSS desligado): lê o arquivo do disco.
const css = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../../App.css'), 'utf-8');

const TEMA_CLARO = 'html:not(.dark) .ant-menu-dark';
const TITULO_SELECIONADO = `${TEMA_CLARO} .ant-menu-submenu-selected > .ant-menu-submenu-title`;

let folha: HTMLStyleElement | null = null;

afterEach(() => {
  folha?.remove();
  folha = null;
});

/** Declarações da regra do App.css que lista exatamente este seletor. */
function regra(seletor: string): CSSStyleDeclaration {
  if (!folha) {
    folha = document.createElement('style');
    folha.textContent = css;
    document.head.appendChild(folha);
  }
  const regras = Array.from(folha.sheet?.cssRules ?? []).filter(
    (r): r is CSSStyleRule => 'selectorText' in r,
  );
  const achada = regras.find((r) => r.selectorText.split(',').map((s) => s.trim()).includes(seletor));
  if (!achada) throw new Error(`App.css não tem regra para: ${seletor}`);
  return achada.style;
}

function valorImportante(seletor: string, propriedade: string): string {
  const estilo = regra(seletor);
  return `${estilo.getPropertyValue(propriedade)} ${estilo.getPropertyPriority(propriedade)}`;
}

describe('App.css — submenu da página atual na sidebar (tema claro)', () => {
  test('título: mesmo fundo do submenu aberto e mesma cor do item selecionado, com !important', () => {
    expect(valorImportante(TITULO_SELECIONADO, 'background-color')).toBe(
      valorImportante(`${TEMA_CLARO} .ant-menu-submenu-open > .ant-menu-submenu-title`, 'background-color'),
    );
    expect(valorImportante(TITULO_SELECIONADO, 'color')).toBe(
      valorImportante(`${TEMA_CLARO} .ant-menu-item-selected a`, 'color'),
    );
  });

  test('ícone e seta: mesma cor do ícone do item selecionado, com !important', () => {
    const corDoItem = valorImportante(`${TEMA_CLARO} .ant-menu-item-selected .anticon`, 'color');
    expect(valorImportante(`${TITULO_SELECIONADO} .anticon`, 'color')).toBe(corDoItem);
    expect(valorImportante(`${TITULO_SELECIONADO} .ant-menu-submenu-arrow`, 'color')).toBe(corDoItem);
  });

  test('o seletor casa com o submenu "DAT" na recolhida, em /dat/admin/usuarios', () => {
    const permissions = { canDAT: true } as Permissions;
    render(
      <MemoryRouter initialEntries={['/dat/admin/usuarios']}>
        <AppSidebar
          permissions={permissions}
          policies={['manage_admin_registries']}
          gcalErrorCount={0}
          unreadNotifications={0}
          modo="recolhida"
          sidebarCollapsed
          toggleSidebar={() => {}}
          colors={{ sidebarBackground: '#006B52', borderLight: '#303030' }}
        />
      </MemoryRouter>,
    );
    const titulos = Array.from(document.querySelectorAll(TITULO_SELECIONADO));
    expect(titulos.map((t) => t.textContent?.trim())).toEqual(['DAT']);
  });
});

/** Luminância relativa (WCAG 2.x) de #rrggbb. */
function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function contraste(a: string, b: string): number {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro! + 0.05) / (escuro! + 0.05);
}

/** `rgb(r, g, b)` (como o CSSOM devolve) ou `#rrggbb` para `#rrggbb`. */
function hexDe(cor: string): string {
  const rgb = /rgb\((\d+),\s*(\d+),\s*(\d+)\)/.exec(cor);
  if (!rgb) return cor.trim().toLowerCase();
  return `#${rgb.slice(1).map((n) => Number(n).toString(16).padStart(2, '0')).join('')}`;
}

/** Fundos de item do menu (tokens `Menu` do ThemeContext): normal, submenu aberto e selecionado. */
const FUNDOS_DO_MENU = {
  claro: ['#006B52', '#004B3D', '#C6E6C3'],
  escuro: ['#141414', '#1f1f1f', '#2FA37D'],
};

const ITEM_EM_FOCO = '.ant-menu-dark .ant-menu-item:has(a:focus-visible)';
/** O título de submenu recebe o foco ele mesmo; o anel do AntD (verde sobre verde) dá 1,7:1. */
const SUBMENU_EM_FOCO = '.ant-menu-dark .ant-menu-submenu-title:focus-visible';
/** "Fechar menu", no cabeçalho da navegação (fundo da sidebar): o anel do AntD dá 1,73:1. */
const FECHAR_EM_FOCO = '.sidebar-fechar-menu:focus-visible';
/** O <ul> raiz do menu é parada de Tab (tabindex=0 do rc-menu): o anel do AntD dá 1,73:1. */
const RAIZ_EM_FOCO = '.ant-menu-dark.ant-menu-root:focus-visible';

/** O seletor sem a pseudo-classe, para conferir no DOM do jsdom (que não tem foco por teclado). */
const semFoco = (seletor: string): string => seletor.replace(':focus-visible', '');

describe('App.css — foco visível nos links do menu lateral', () => {
  test('anel de duas cores (outline + sombra interna), sem sair do item', () => {
    const estilo = regra(ITEM_EM_FOCO);
    expect(estilo.getPropertyValue('outline-style')).toBe('solid');
    expect(parseFloat(estilo.getPropertyValue('outline-width'))).toBeGreaterThanOrEqual(2);
    // offset negativo: o Sider tem overflow e cortaria um anel por fora
    expect(parseFloat(estilo.getPropertyValue('outline-offset'))).toBeLessThan(0);
    expect(estilo.getPropertyValue('box-shadow')).toMatch(/^inset /);
    expect(regra(SUBMENU_EM_FOCO)).toBe(estilo); // o título de submenu tem o mesmo anel
  });

  test.each(Object.entries(FUNDOS_DO_MENU))('tema %s: em cada fundo do menu, uma das duas cores dá 3:1', (_tema, fundos) => {
    const estilo = regra(ITEM_EM_FOCO);
    const anel = hexDe(estilo.getPropertyValue('outline-color'));
    const sombra = hexDe(/#[0-9a-f]{6}|rgb\([^)]*\)/i.exec(estilo.getPropertyValue('box-shadow'))?.[0] ?? '');
    expect(contraste(anel, sombra)).toBeGreaterThanOrEqual(9); // C40: as duas cores entre si
    for (const fundo of fundos) {
      expect(Math.max(contraste(anel, fundo), contraste(sombra, fundo)), `fundo ${fundo}`).toBeGreaterThanOrEqual(3);
    }
  });

  test('o seletor casa com o DOM do menu: o link fica num .ant-menu-item de um .ant-menu-dark', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <AppSidebar
          permissions={{} as Permissions}
          policies={[]}
          gcalErrorCount={0}
          unreadNotifications={0}
          modo="aberta"
          sidebarCollapsed={false}
          toggleSidebar={() => {}}
          colors={{ sidebarBackground: '#006B52', borderLight: '#303030' }}
        />
      </MemoryRouter>,
    );
    const link = screen.getByRole('link', { name: 'Página Inicial' });
    expect(link.closest('.ant-menu-dark .ant-menu-item')).not.toBeNull();
  });

  test('"Fechar menu" e o <ul> raiz do menu têm o mesmo anel', () => {
    const estilo = regra(ITEM_EM_FOCO);
    expect(regra(FECHAR_EM_FOCO)).toBe(estilo);
    expect(regra(RAIZ_EM_FOCO)).toBe(estilo);
  });

  test('os dois seletores casam com o DOM da navegação por cima do conteúdo', () => {
    render(
      <MemoryRouter initialEntries={['/home']}>
        <AppSidebar
          permissions={{} as Permissions}
          policies={[]}
          gcalErrorCount={0}
          unreadNotifications={0}
          modo="sobreposta"
          sidebarCollapsed={false}
          toggleSidebar={() => {}}
          colors={{ sidebarBackground: '#006B52', borderLight: '#303030' }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: 'Fechar menu' }).matches(semFoco(FECHAR_EM_FOCO))).toBe(true);
    const raiz = screen.getByRole('menu');
    expect(raiz.matches(semFoco(RAIZ_EM_FOCO))).toBe(true);
    expect(raiz.getAttribute('tabindex')).toBe('0'); // é parada de Tab, por isso precisa do anel
  });
});
