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
  // colorLink é token SEED: o AntD descarta o valor passado e rederiva pela paleta, e o
  // darkAlgorithm mistura 85% do seed com #141414. Por isso o seed '#34BC8F' sai #2FA37D
  // (5,2:1 no #1f1f1f); passar DARK_ACCENT direto sairia #2b8e6d (4,08:1, reprova AA).
  colorLink: '#34BC8F',
  colorLinkHover: '#4FB08C',
  colorLinkActive: DARK_ACCENT,
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
  // A11y (WCAG AA): sem colorLink o AntD usa o azul #1677ff (4,10:1 no branco; hover 2,25:1).
  // A marca dá 6,5:1 e o hover escuro 10:1; o active derivado (#004537) já passa.
  colorLink: BRAND_COLORS.primary,
  colorLinkHover: BRAND_COLORS.primaryDark,
  borderRadius: 6,
  // A11y (WCAG AA): o default do Antd para texto terciário é rgba(0,0,0,0.45)=#8c8c8c,
  // que dá só 3.36:1 em branco (ex.: labels do Descriptions) e reprova 4.5:1. Escurecemos
  // para rgba(0,0,0,0.55)≈#737373 (~4.8:1). Só aumenta contraste — mudança sutil.
  colorTextTertiary: 'rgba(0, 0, 0, 0.55)',
  // A11y (WCAG AA, DEF-28): o vermelho de erro do AntD (#ff4d4f) dá 3,27:1 no branco e 2,74:1 no
  // cartão verde-claro do login. O red-7 dá 5,57:1 no branco, 4,97:1 na página e 4,66:1 no cartão
  // do login. É token SEED: o AntD deriva dele o colorErrorText (o mesmo tom), o hover e os fundos.
  colorError: '#cf1322',
  // Texto de exemplo (placeholder): o default é o quaternário rgba(0,0,0,0.25), 1,83:1 no campo.
  // O cinza do terciário dá 4,76:1 no campo e 4,63:1 na página; o texto desabilitado segue no quaternário.
  colorTextPlaceholder: 'rgba(0, 0, 0, 0.55)',
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
      // A11y (WCAG AA, DEF-28): o hover que o AntD deriva do red-7 (#db373f) dá 3,87:1 no fundo rosado
      // do botão danger de texto ("Excluir" dos modais) e 4,04:1 na página; pressionado, 1,96:1. Hover
      // entre o red-7 e o red-8 (o pressionado segue no red-8, #a8071a): 5,77:1 no rosado, 6,02:1 na
      // página e 6,75:1 com texto branco. Fundo do pressionado no red-2: 4,73:1.
      Button: isDark ? {} : {
        colorErrorHover: '#b80c1e',
        colorErrorBgActive: '#ffccc7',
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
