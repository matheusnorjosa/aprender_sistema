import React from 'react';
import { apiGet } from "../lib/api";
import { Table } from "../components/Table";

type Row = {
  usuario_id:number;
  ev_a:number; ev_a_titulo:string|null; ev_a_ini:string; ev_a_fim:string; ev_a_municipio:string|null; ev_a_tipo:string|null;
  ev_b:number; ev_b_titulo:string|null; ev_b_ini:string; ev_b_fim:string; ev_b_municipio:string|null; ev_b_tipo:string|null;
};

export default function ConflitosPage(){
  const [data,setData] = React.useState<Row[]>([]);
  const [limit,setLimit] = React.useState(200);
  const [status,setStatus] = React.useState<"idle"|"loading"|"error"|"ok">("idle");

  React.useEffect(()=>{
    setStatus("loading");
    apiGet<{count:number,results:Row[]}>("/api/reports/conflitos",{limit})
      .then(d=>{ setData(d.results); setStatus("ok"); })
      .catch(()=>setStatus("error"));
  },[limit]);

  const cols = ["Usuário","Evento A","A Início","A Fim","A Município","A Tipo","Evento B","B Início","B Fim","B Município","B Tipo"];
  const rows = data.map(r=>[
    `Usuário #${r.usuario_id}`,
    r.ev_a_titulo ?? r.ev_a,
    new Date(r.ev_a_ini).toLocaleString(),
    new Date(r.ev_a_fim).toLocaleString(),
    r.ev_a_municipio ?? "-",
    r.ev_a_tipo ?? "-",
    r.ev_b_titulo ?? r.ev_b,
    new Date(r.ev_b_ini).toLocaleString(),
    new Date(r.ev_b_fim).toLocaleString(),
    r.ev_b_municipio ?? "-",
    r.ev_b_tipo ?? "-"
  ]);

  return (
    <div style={{padding:16}}>
      <h1 style={{margin:'8px 0'}}>Conflitos de Agenda</h1>
      <div style={{display:'flex',gap:12,alignItems:'center',margin:'8px 0'}}>
        <label>Limite:
          <input type="number" min={10} max={2000} value={limit} onChange={e=>setLimit(parseInt(e.target.value||"200"))}
                 style={{marginLeft:8,width:100}}/>
        </label>
        <button onClick={()=>window.location.reload()}>Recarregar</button>
      </div>
      {status==="loading" && <p>Carregando…</p>}
      {status==="error" && <p style={{color:'crimson'}}>Erro ao carregar (verifique seu login/permissões)</p>}
      {status==="ok" && <Table columns={cols} rows={rows} />}
    </div>
  );
}
