import { ConfigProvider, Spin } from 'antd';

import type { JSX } from "react";

// A11y (WCAG AA): o AntD pinta o "Carregando..." em branco sobre a máscara (colorBgMask),
// rgba(0,0,0,0.45). Sobre a página branca ela vira #8c8c8c e o texto dá só 3,35:1. Com 0.55
// (mesma régua do colorTextTertiary no ThemeContext) vira #737373: 4,76:1. A página branca é
// o pior caso; fundo mais escuro só aumenta o contraste. Só no Spin, nos dois temas.
const MASCARA = 'rgba(0, 0, 0, 0.55)';

export function FullscreenLoader(): JSX.Element {
  return (
    <ConfigProvider theme={{ components: { Spin: { colorBgMask: MASCARA } } }}>
      <Spin size="large" tip="Carregando..." fullscreen />
    </ConfigProvider>
  );
}
