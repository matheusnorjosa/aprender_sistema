/**
 * DEF-33: os diálogos estáticos (Modal.confirm/error/..., message, notification) abrem fora do
 * <ConfigProvider theme> do App e usavam o tema padrão do antd. O "Sim, excluir" saía com texto branco
 * no vermelho antigo (3,27:1) e o botão primário no azul padrão. `aplicarTemaNosDialogos` registra o
 * mesmo tema no `holderRender` do antd.
 *
 * Prova: a classe de hash do CSS-in-JS do antd identifica o tema. O botão de perigo do diálogo tem de
 * sair com a MESMA classe do botão de perigo dentro do ConfigProvider do sistema; sem o registro, sai
 * com a do tema padrão.
 */
// Como no main.tsx: sem o patch, os métodos estáticos do antd 5 não renderizam no React 19.
import '@ant-design/v5-patch-for-react-19';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, test } from 'vitest';
import { Button, ConfigProvider, Modal, theme, type ThemeConfig } from 'antd';

import { ThemeProvider, useTheme, type ThemeContextValue } from '../ThemeContext';
import { aplicarTemaNosDialogos } from '../temaNosDialogos';

function configDoSistema(): ThemeConfig {
  let valor: ThemeContextValue | undefined;
  function Leitor(): null {
    valor = useTheme();
    return null;
  }
  render(
    <ThemeProvider>
      <Leitor />
    </ThemeProvider>,
  );
  return valor!.antThemeConfig;
}

function classeDoTema(el: Element): string {
  const c = [...el.classList].find((x) => x.startsWith('css-'));
  expect(c, 'o botão não tem a classe de hash do tema').toBeDefined();
  return c!;
}

async function classeDoDialogo(rotulo: string): Promise<string> {
  // Rótulo diferente a cada abertura: o diálogo anterior ainda some animando e ficaria no DOM.
  Modal.confirm({ title: 'Excluir?', okText: rotulo, okButtonProps: { danger: true } });
  // O diálogo fica fora da árvore acessível enquanto anima; procura o botão pela classe do antd.
  const botao = await waitFor(() => {
    const el = [...document.querySelectorAll('.ant-modal-confirm-btns .ant-btn-dangerous')].find(
      (b) => b.textContent === rotulo,
    );
    expect(el, `diálogo "${rotulo}" não abriu`).toBeDefined();
    return el!;
  });
  const classe = classeDoTema(botao);
  Modal.destroyAll();
  return classe;
}

function luminancia(hex: string): number {
  const n = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((i) => {
    const v = parseInt(n.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

afterEach(() => {
  Modal.destroyAll();
  ConfigProvider.config({ holderRender: undefined });
});

describe('diálogos estáticos herdam o tema do sistema (DEF-33)', () => {
  test('o botão de perigo do Modal.confirm sai com o tema do sistema, não o padrão', async () => {
    const config = configDoSistema();
    render(
      <ConfigProvider theme={config}>
        <Button danger type="primary">
          No sistema
        </Button>
      </ConfigProvider>,
    );
    const doSistema = classeDoTema(screen.getByRole('button', { name: 'No sistema' }));

    const semRegistro = await classeDoDialogo('Sim, excluir (sem tema)');
    expect(semRegistro, 'o cenário não reproduz: o diálogo já usava o tema').not.toBe(doSistema);

    aplicarTemaNosDialogos(config);
    expect(await classeDoDialogo('Sim, excluir')).toBe(doSistema);
  });

  test('o vermelho do tema dá 4,5:1 com o texto branco do botão de perigo', () => {
    const { colorError } = theme.getDesignToken(configDoSistema());
    const razao = (luminancia('#ffffff') + 0.05) / (luminancia(colorError) + 0.05);
    expect(razao).toBeGreaterThanOrEqual(4.5);
  });

  test('o App registra o tema ativo nos diálogos, de novo a cada troca de tema', () => {
    // Guarda da ligação: sem ela, apagar o useEffect do App deixaria toda a suíte verde e o DEF-33 voltaria.
    const app = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../../App.tsx'), 'utf-8');
    expect(app).toMatch(/useEffect\(\(\) => \{\s*aplicarTemaNosDialogos\(antThemeConfig\);\s*\}, \[antThemeConfig\]\);/);
  });
});
