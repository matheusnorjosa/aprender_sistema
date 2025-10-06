import React from 'react';
import { apiGet } from '../lib/api';

type KPIs = {
  total_solicitacoes: number;
  by_status: Record<string, number>;
  conflitos_total: number;
  overload_users: number;
  usuarios_total: number;
  municipios_total: number;
  projetos_total: number;
  disp_staging_total: number;
};

export default function Dashboard() {
  const [kpis, setKpis] = React.useState<KPIs | null>(null);
  const [err, setErr] = React.useState<string | null>(null);

  React.useEffect(() => {
    apiGet('/api/reports/kpis')
      .then(setKpis)
      .catch(e => setErr(String(e)));
  }, []);

  return (
    <div style={{ padding: 16 }}>
      <h1>Dashboard Executivo</h1>
      {err && <p style={{ color: 'crimson' }}>Erro: {err}</p>}
      {!kpis && !err && <p>Carregando…</p>}
      {kpis && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, margin: '12px 0' }}>
            <Card title="Solicitações">{kpis.total_solicitacoes}</Card>
            <Card title="Conflitos">{kpis.conflitos_total}</Card>
            <Card title="Usuários">{kpis.usuarios_total}</Card>
            <Card title="Overload (≥110h)">{kpis.overload_users}</Card>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
            <Card title="CRIADO">{kpis.by_status?.CRIADO ?? 0}</Card>
            <Card title="APROVADO">{kpis.by_status?.APROVADO ?? 0}</Card>
            <Card title="REALIZADO">{kpis.by_status?.REALIZADO ?? 0}</Card>
            <Card title="CANCELADO">{kpis.by_status?.CANCELADO ?? 0}</Card>
          </div>
          <div style={{ marginTop: 16 }}>
            <small>
              Municípios: {kpis.municipios_total} • Projetos: {kpis.projetos_total} • Disp (staging): {kpis.disp_staging_total}
            </small>
          </div>
        </>
      )}
    </div>
  );
}

function Card({ title, children }: { title: string; children: any }) {
  return (
    <div style={{ border: '1px solid #eee', borderRadius: 12, padding: 16, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <div style={{ fontSize: 12, opacity: 0.7 }}>{title}</div>
      <div style={{ fontSize: 24, fontWeight: 700 }}>{children}</div>
    </div>
  );
}
