import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import './App.css';
import ReportsConflitos from './pages/ReportsConflitos';
import ReportsWorkload from './pages/ReportsWorkload';

interface HealthStatus {
  status: string;
  django_version: string;
  database: string;
  timestamp: string;
}

function HomePage() {
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
            <li>✅ FASE 3: React + Docker</li>
            <li>✅ FASE 4: API de Reports (Conflitos & Workload)</li>
            <li>✅ FASE 5: Componentes React para Reports</li>
          </ul>
        </div>

        <nav style={{display:"flex",gap:16,margin:"16px 0",justifyContent:"center"}}>
          <Link to="/reports/conflitos" style={{padding:"8px 16px",background:"#61dafb",color:"#282c34",borderRadius:4,textDecoration:"none"}}>
            📊 Conflitos
          </Link>
          <Link to="/reports/workload" style={{padding:"8px 16px",background:"#61dafb",color:"#282c34",borderRadius:4,textDecoration:"none"}}>
            ⏱️ Workload
          </Link>
        </nav>
      </header>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/reports/conflitos" element={<ReportsConflitos />} />
        <Route path="/reports/workload" element={<ReportsWorkload />} />
      </Routes>
    </Router>
  );
}

export default App;
