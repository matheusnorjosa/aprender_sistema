import React from 'react';
import { apiGet } from "../lib/api";
import { Table } from "../components/Table";
import { MonthRange } from "../components/MonthRange";

type Row = { usuario_id:number; mes:string; ch:number; };

export default function WorkloadPage(){
  const now = new Date();
  const mm = (n:number)=> (n<10?`0${n}`:`${n}`);
  const defTo = `${now.getFullYear()}-${mm(now.getMonth()+1)}`;
  const d2 = new Date(now); d2.setMonth(now.getMonth()-11);
  const defFrom = `${d2.getFullYear()}-${mm(d2.getMonth()+1)}`;

  const [from,setFrom] = React.useState(defFrom);
  const [to,setTo] = React.useState(defTo);
  const [data,setData] = React.useState<Row[]>([]);
  const [status,setStatus] = React.useState<"idle"|"loading"|"error"|"ok">("idle");

  const load = React.useCallback(()=>{
    setStatus("loading");
    apiGet<{count:number,results:Row[]}>("/api/reports/workload",{from,to})
      .then(d=>{ setData(d.results); setStatus("ok"); })
      .catch(()=>setStatus("error"));
  },[from,to]);

  React.useEffect(()=>{ load(); },[load]);

  const cols = ["Usuário ID","Mês","Carga (h)"];
  const rows = data.map(r=>[r.usuario_id, r.mes, r.ch.toFixed(2)]);

  return (
    <div style={{padding:16}}>
      <h1 style={{margin:'8px 0'}}>Workload Mensal</h1>
      <MonthRange from={from} to={to} setFrom={setFrom} setTo={setTo} />
      <div style={{display:'flex',gap:12,alignItems:'center',margin:'8px 0'}}>
        <button onClick={load}>Atualizar</button>
        <button onClick={()=>{
          const csv = "usuario_id,mes,ch\n"+data.map(r=>`${r.usuario_id},${r.mes},${r.ch}`).join("\n");
          const blob = new Blob([csv], {type:"text/csv;charset=utf-8"});
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = "workload.csv";
          a.click();
        }}>Baixar CSV</button>
      </div>
      {status==="loading" && <p>Carregando…</p>}
      {status==="error" && <p style={{color:'crimson'}}>Erro ao carregar (login ou permissão)</p>}
      {status==="ok" && <Table columns={cols} rows={rows} />}
    </div>
  );
}
