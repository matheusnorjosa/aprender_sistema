import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Result, Button } from 'antd';
import logger from '../utils/logger';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
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
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
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
