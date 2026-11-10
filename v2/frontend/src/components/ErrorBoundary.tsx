import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Result, Button } from 'antd';
import logger from '../utils/logger';
import { ehVersaoAntiga, recarregarSeVersaoAntiga } from '../utils/recargaVersaoNova';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  /**
   * Quando qualquer valor deste array muda (ex.: a rota atual), o boundary sai do
   * estado de erro e re-renderiza os filhos — permite recuperar navegando, sem full reload.
   */
  resetKeys?: unknown[];
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * React Error Boundary for catching render errors in child components.
 * Shows an antd Result with reload button by default, or a custom fallback.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    logger.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
    // Aba aberta de uma versão que saiu do ar: recarregar busca a versão nova (uma vez; ver o util).
    recarregarSeVersaoAntiga(error);
  }

  override componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    if (this.state.hasError && this.resetKeysChanged(prevProps.resetKeys, this.props.resetKeys)) {
      this.setState({ hasError: false, error: null });
    }
  }

  private resetKeysChanged(prev: unknown[] | undefined, next: unknown[] | undefined): boolean {
    if (prev === next) return false;
    if (!prev || !next || prev.length !== next.length) return true;
    return prev.some((value, index) => !Object.is(value, next[index]));
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      if (ehVersaoAntiga(this.state.error)) {
        return (
          <Result
            status="info"
            title="O sistema foi atualizado"
            subTitle="Recarregue a página para continuar."
            extra={
              <Button type="primary" onClick={() => window.location.reload()}>
                Recarregar página
              </Button>
            }
          />
        );
      }
      return (
        <Result
          status="error"
          title="Algo deu errado"
          subTitle={this.state.error?.message || 'Erro inesperado na aplicação'}
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              Recarregar página
            </Button>
          }
        />
      );
    }
    return this.props.children;
  }
}
