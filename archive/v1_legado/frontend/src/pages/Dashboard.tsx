import React, { useEffect, useState } from 'react';

type Kpis = {
  total_solicitacoes: number;
  total_conflitos: number;
  total_usuarios: number;
  overload_users: number;
  por_status: { CRIADO: number; APROVADO: number; REALIZADO: number; CANCELADO: number };
};

export default function Dashboard() {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/reports/kpis', { credentials: 'include' })
      .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
      .then(setKpis)
      .catch(e => setErr(String(e)));
  }, []);

  return (
    <div style={{ minHeight: '100vh', padding: '24px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: 'white', marginBottom: '24px' }}>
          Dashboard Executivo
        </h1>
        {err && (
          <div style={{ background: '#fef2f2', color: '#dc2626', padding: '12px', borderRadius: '8px', marginBottom: '16px' }}>
            Erro: {err}
          </div>
        )}
        {!kpis && !err && (
          <div style={{ background: 'rgba(255,255,255,0.9)', padding: '16px', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
            Carregando KPIs...
          </div>
        )}
        {kpis && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <Card title='SolicitaÃ§Ãµes' value={kpis.total_solicitacoes} />
            <Card title='Conflitos' value={kpis.total_conflitos} />
            <Card title='UsuÃ¡rios' value={kpis.total_usuarios} />
            <Card title='Sobrecarga (â‰¥110h)' value={kpis.overload_users} />
            <Card title='Criado' value={kpis.por_status.CRIADO} />
            <Card title='Aprovado' value={kpis.por_status.APROVADO} />
            <Card title='Realizado' value={kpis.por_status.REALIZADO} />
            <Card title='Cancelado' value={kpis.por_status.CANCELADO} />
          </div>
        )}
      </div>
    </div>
  );
}

function Card({ title, value }: { title: string; value: number }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.95)', borderRadius: '16px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', padding: '16px' }}>
      <div style={{ color: '#64748b', fontSize: '14px' }}>{title}</div>
      <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{value}</div>
    </div>
  );
}
