import React, { useEffect, useState } from 'react';
import './App.css';

interface HealthStatus {
  status: string;
  django_version: string;
  database: string;
  timestamp: string;
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Testar conexão com API Django
    fetch('http://localhost:8000/api/health/')
      .then(res => res.json())
      .then(data => {
        setHealth(data);
        setLoading(false);
      })
      .catch(err => {
        setError('Erro ao conectar com API Django');
        setLoading(false);
        console.error(err);
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎓 Sistema Aprender</h1>
        <p>Frontend React + Backend Django</p>

        <div className="status-card">
          <h2>Status da API</h2>
          {loading && <p>Carregando...</p>}
          {error && <p className="error">{error}</p>}
          {health && (
            <div className="health-info">
              <p>✅ Status: <strong>{health.status}</strong></p>
              <p>🐍 Django: <strong>{health.django_version}</strong></p>
              <p>💾 Database: <strong>{health.database}</strong></p>
              <p>🕐 Timestamp: <strong>{health.timestamp}</strong></p>
            </div>
          )}
        </div>

        <div className="info-card">
          <h3>🚀 Próximos Passos</h3>
          <ul>
            <li>✅ FASE 1: Apps e REST Framework</li>
            <li>✅ FASE 2: Testar Sistema Docker</li>
            <li>🔄 FASE 3: React + Docker (em andamento)</li>
            <li>⏳ FASE 4: Implementar API completa</li>
            <li>⏳ FASE 5: Criar componentes React</li>
          </ul>
        </div>
      </header>
    </div>
  );
}

export default App;
