/**
 * Theme Context - Gerenciamento de tema claro/escuro
 *
 * Permite ao usuário alternar entre tema claro e escuro.
 * A preferência é salva no localStorage.
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { theme } from 'antd';

const ThemeContext = createContext();

// Cores customizadas para o tema escuro (baseado no design de referência)
const darkThemeTokens = {
  colorPrimary: '#ea2a33',
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
  colorPrimary: '#1890ff',
  borderRadius: 6,
};

export function ThemeProvider({ children }) {
  // Verificar preferência salva ou preferência do sistema
  const getInitialTheme = () => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved;
    // Verificar preferência do sistema
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  };

  const [themeMode, setThemeMode] = useState(getInitialTheme);

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

  const toggleTheme = () => {
    setThemeMode((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const isDark = themeMode === 'dark';

  // Configuração do Ant Design theme
  const antThemeConfig = {
    algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: isDark ? darkThemeTokens : lightThemeTokens,
    components: {
      Menu: isDark ? {
        darkItemBg: '#141414',
        darkSubMenuItemBg: '#1f1f1f',
        darkItemSelectedBg: '#ea2a33',
      } : {},
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

  const value = {
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

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export default ThemeContext;
