import '@ant-design/v5-patch-for-react-19';
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import logger from './utils/logger'
import { recarregarSeVersaoAntiga } from './utils/recargaVersaoNova'
import { clearApiCaches } from './services/swCache'

// Falha do Vite ao pré-carregar um pedaço de tela da versão que saiu do ar: recarrega uma vez antes
// de a tela quebrar. Se não recarregar (2ª vez em 30 s), o erro segue para o ErrorBoundary.
window.addEventListener('vite:preloadError', (event) => {
  if (recarregarSeVersaoAntiga((event as Event & { payload?: unknown }).payload)) {
    event.preventDefault();
  }
});

// Issue #416: Register Service Worker for offline support
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    // SEG-54: apaga sobras de cache de API de versões antigas do SW a cada carregamento.
    void clearApiCaches();
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        logger.log('[SW] Registered:', registration.scope);
      })
      .catch((error) => {
        logger.error('[SW] Registration failed:', error);
      });
  });
}

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
