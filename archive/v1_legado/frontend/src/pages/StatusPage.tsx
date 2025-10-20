import React from 'react';
export default function StatusPage() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <div style={{ maxWidth: '768px', width: '100%', padding: '24px' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: '800', color: 'white', textAlign: 'center', marginBottom: '32px' }}>
          Sistema Aprender
        </h1>
        <div style={{ background: 'rgba(255,255,255,0.9)', borderRadius: '16px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', padding: '24px' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '700', marginBottom: '16px' }}>Status da API</h2>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, color: '#475569' }}>
            <li>Status:</li>
            <li>Django:</li>
            <li>Database:</li>
            <li>Timestamp:</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
