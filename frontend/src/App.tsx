import React, { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ReportsConflitos from "./pages/ReportsConflitos";
import ReportsWorkload from "./pages/ReportsWorkload";

// Landing antiga → agora em /status
interface HealthStatus {
  status: string;
  django_version: string;
  database: string;
  timestamp: string;
}

function StatusPage() {
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
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <div style={{ maxWidth: '48rem', width: '100%', padding: '1.5rem' }}>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 800, color: 'white', textAlign: 'center', marginBottom: '2rem' }}>🎓 Sistema Aprender</h1>
        <div style={{ display: 'grid', gap: '1.5rem' }}>
          <div style={{ background: 'rgba(255,255,255,0.9)', borderRadius: '1rem', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', padding: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem' }}>Status da API</h2>
            {loading && <p>Carregando...</p>}
            {error && <p style={{ color: '#dc2626' }}>{error}</p>}
            {health && (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, color: '#475569' }}>
                <li>✅ Status: <strong>{health.status}</strong></li>
                <li>🐍 Django: <strong>{health.django_version}</strong></li>
                <li>💾 Database: <strong>{health.database}</strong></li>
                <li>🕐 Timestamp: <strong>{health.timestamp}</strong></li>
              </ul>
            )}
          </div>
          <div style={{ background: 'rgba(255,255,255,0.9)', borderRadius: '1rem', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', padding: '1.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem' }}>Acessos rápidos</h2>
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <Link to="/dashboard" style={{ textDecoration: 'underline', color: '#4f46e5' }}>Dashboard Executivo</Link>
              <Link to="/reports/conflitos" style={{ textDecoration: 'underline', color: '#4f46e5' }}>Relatório de Conflitos</Link>
              <Link to="/reports/workload" style={{ textDecoration: 'underline', color: '#4f46e5' }}>Workload</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Novo dashboard oficial */}
        <Route path="/dashboard" element={<Dashboard />} />
        {/* Relatórios */}
        <Route path="/reports/conflitos" element={<ReportsConflitos />} />
        <Route path="/reports/workload" element={<ReportsWorkload />} />
        {/* Landing antiga vai para /status */}
        <Route path="/status" element={<StatusPage />} />
        {/* Raiz redireciona para o dashboard novo */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        {/* Qualquer coisa desconhecida → dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}
