/**
 * Theme Context - Gerenciamento de tema claro/escuro
 *
 * Permite ao usuário alternar entre tema claro e escuro.
 * A preferência é salva no localStorage.
 */

/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, type ReactNode, type JSX } from 'react';
import { theme, type ThemeConfig } from 'antd';

/**
 * Theme mode type
 */
export type ThemeMode = 'light' | 'dark';

/**
 * Brand colors interface
 */
export interface BrandColors {
  primary: string;
  primaryDark: string;
  primaryLight: string;
  pageBackground: string;
  cardBackground: string;
  sidebarBackground: string;
  borderLight: string;
  borderDefault: string;
  success: string;
  warning: string;
  error: string;
  info: string;
  successBg: string;
  warningBg: string;
  errorBg: string;
}

/**
 * Theme context value interface
 */
export interface ThemeContextValue {
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
  toggleTheme: () => void;
  isDark: boolean;
  antThemeConfig: ThemeConfig;
}

/**
 * Theme provider props
 */
interface ThemeProviderProps {
  children: ReactNode;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

// ============================================================================
// Issue #439: Centralized Brand Colors
// ============================================================================
export const BRAND_COLORS: BrandColors = {
  // Primary brand colors
  primary: '#006B52',
  primaryDark: '#004B3D',
  primaryLight: '#E5EDE5',

  // Backgrounds
  pageBackground: '#f0f2f5',
  cardBackground: '#ffffff',
  sidebarBackground: '#006B52',

  // Borders
  borderLight: 'rgba(255, 255, 255, 0.1)',
  borderDefault: '#d9d9d9',

  // Status colors (Ant Design tokens)
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  info: '#1890ff',

  // Status backgrounds
  successBg: '#f6ffed',
  warningBg: '#fffbe6',
  errorBg: '#fff2f0',
};

// Acento de interação do tema ESCURO (colorPrimary → hover/focus/ativo/selecionado
// que o AntD deriva). Antes era '#ea2a33' (vermelho): criava conflito semântico
// (vermelho = erro/danger) e divergia da marca verde. O verde da marca cru (#006B52)
// REPROVA WCAG no fundo dark (~2.5:1); este é o verde clareado p/ 5.2:1 sobre #1f1f1f
// — mantém a marca e libera o vermelho só para erro. Espelha a CSS var
// `--as-primary-dark-accent` em index.css.
const DARK_ACCENT = '#2FA37D';

// Cores customizadas para o tema escuro (baseado no design de referência)
const darkThemeTokens = {
  colorPrimary: DARK_ACCENT,
  colorBgContainer: '#1f1f1f',
  colorBgElevated: '#262626',
  colorBgLayout: '#141414',
  colorBgSpotlight: '#262626',
  colorBorder: '#424242',
  colorBorderSecondary: '#303030',
  colorText: 'rgba(255, 255, 255, 0.88)',
  colorTextSecondary: 'rgba(255, 255, 255, 0.65)',
  colorTextTertiary: 'rgba(255, 255, 255, 0.45)',
  borderRadius: 6,
};

// Cores customizadas para o tema claro
const lightThemeTokens = {
  colorPrimary: '#006B52',
  borderRadius: 6,
  // A11y (WCAG AA): o default do Antd para texto terciário é rgba(0,0,0,0.45)=#8c8c8c,
  // que dá só 3.36:1 em branco (ex.: labels do Descriptions) e reprova 4.5:1. Escurecemos
  // para rgba(0,0,0,0.55)≈#737373 (~4.8:1). Só aumenta contraste — mudança sutil.
  colorTextTertiary: 'rgba(0, 0, 0, 0.55)',
};

export function ThemeProvider({ children }: ThemeProviderProps): JSX.Element {
  // Issue #XXX: Forçar tema claro como padrão
  // Ignora preferência salva no localStorage e sempre inicia com 'light'
  const getInitialTheme = (): ThemeMode => {
    // Limpa qualquer preferência anterior de tema escuro
    const saved = localStorage.getItem('theme') as ThemeMode | null;
    if (saved === 'dark') {
      localStorage.setItem('theme', 'light');
    }
    return 'light';
  };

  const [themeMode, setThemeMode] = useState<ThemeMode>(getInitialTheme);

  // Salvar preferência quando mudar
  useEffect(() => {
    localStorage.setItem('theme', themeMode);
    // Atualizar classe no HTML para estilos globais
    document.documentElement.setAttribute('data-theme', themeMode);
    if (themeMode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [themeMode]);

  const toggleTheme = (): void => {
    setThemeMode((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const isDark = themeMode === 'dark';

  // Configuração do Ant Design theme
  const antThemeConfig: ThemeConfig = {
    algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: isDark ? darkThemeTokens : lightThemeTokens,
    components: {
      Menu: isDark ? {
        darkItemBg: '#141414',
        darkSubMenuItemBg: '#1f1f1f',
        darkItemSelectedBg: DARK_ACCENT,
      } : {
        darkItemBg: '#006B52',
        darkSubMenuItemBg: '#004B3D',
        darkItemSelectedBg: '#C6E6C3',
        darkItemColor: '#ffffff',
        darkItemHoverColor: '#ffffff',
        darkItemSelectedColor: '#000000',
        darkPopupBg: '#006B52',
        itemColor: '#ffffff',
        itemHoverColor: '#ffffff',
        itemSelectedColor: '#000000',
        groupTitleColor: '#ffffff',
        iconSize: 16,
        collapsedIconSize: 16,
      },
      Table: isDark ? {
        headerBg: '#1f1f1f',
        rowHoverBg: '#262626',
      } : {},
      Card: isDark ? {
        colorBgContainer: '#1f1f1f',
      } : {},
      Modal: isDark ? {
        contentBg: '#1f1f1f',
        headerBg: '#1f1f1f',
      } : {},
    },
  };

  const value: ThemeContextValue = {
    themeMode,
    setThemeMode,
    toggleTheme,
    isDark,
    antThemeConfig,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

/**
 * Issue #439: Hook to access brand colors with dark mode support.
 *
 * Returns BRAND_COLORS with overrides for dark mode backgrounds.
 */
export function useBrandColors(): BrandColors {
  const { isDark } = useTheme();
  return {
    ...BRAND_COLORS,
    // Override for dark mode
    pageBackground: isDark ? '#141414' : BRAND_COLORS.pageBackground,
    cardBackground: isDark ? '#1f1f1f' : BRAND_COLORS.cardBackground,
    sidebarBackground: isDark ? '#141414' : BRAND_COLORS.sidebarBackground,
  };
}

export default ThemeContext;
