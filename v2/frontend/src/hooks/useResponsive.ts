import { useState, useEffect, useCallback, useRef } from 'react';
import { LAYOUT } from '../constants';

/**
 * Modo da sidebar pela largura da janela (Programa C, sem rolagem horizontal):
 * - 'sobreposta' (< 992 px): fechada; abre por cima do conteúdo, que ocupa a largura toda;
 * - 'recolhida' (992 a 1279 px): só ícones, 80 px; também abre por cima do conteúdo;
 * - 'aberta' (>= 1280 px): 250 px, empurrando o conteúdo.
 * Os breakpoints do AntD medem a janela, não o contêiner: por isso a sidebar só ocupa
 * 250 px quando sobra largura para as colunas que a tela mostra a partir de `xl`.
 */
export type ModoSidebar = 'sobreposta' | 'recolhida' | 'aberta';

/** Id da navegação principal (o Sider): o ☰ do cabeçalho aponta para ele (`aria-controls`). */
export const ID_NAVEGACAO_PRINCIPAL = 'navegacao-principal';

/**
 * Abaixo de 1280 px, a sidebar aberta pelo ☰ fica POR CIMA do conteúdo e funciona como
 * diálogo: foco no menu, Esc fecha, cabeçalho e conteúdo inertes.
 */
export function sidebarSobrepondo(modo: ModoSidebar, sidebarCollapsed: boolean): boolean {
  return modo !== 'aberta' && !sidebarCollapsed;
}

function modoAtual(): ModoSidebar {
  const largura = typeof window !== 'undefined' ? window.innerWidth : LAYOUT.DESKTOP_BREAKPOINT;
  if (largura < LAYOUT.TABLET_BREAKPOINT) return 'sobreposta';
  if (largura < LAYOUT.DESKTOP_BREAKPOINT) return 'recolhida';
  return 'aberta';
}

interface UseResponsiveReturn {
  modo: ModoSidebar;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

/**
 * Só recolhe/abre sozinho quando o modo muda; dentro do mesmo modo, a preferência
 * manual do usuário (toggleSidebar) fica.
 */
export function useResponsive(): UseResponsiveReturn {
  const [modo, setModo] = useState(modoAtual);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => modoAtual() !== 'aberta');
  const modoAnteriorRef = useRef(modo);

  useEffect(() => {
    const handleResize = () => {
      const novo = modoAtual();
      setModo(novo);
      if (novo !== modoAnteriorRef.current) {
        setSidebarCollapsed(novo !== 'aberta');
        modoAnteriorRef.current = novo;
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev);
  }, []);

  return { modo, sidebarCollapsed, toggleSidebar };
}
