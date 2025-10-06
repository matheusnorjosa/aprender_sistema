import React from 'react';

export function MonthRange({from,to,setFrom,setTo}:{from:string;to:string;setFrom:(v:string)=>void;setTo:(v:string)=>void}) {
  return (
    <div style={{display:'flex',gap:12,alignItems:'center',margin:'8px 0'}}>
      <label>De: <input value={from} onChange={e=>setFrom(e.target.value)} type="month"/></label>
      <label>Até: <input value={to} onChange={e=>setTo(e.target.value)} type="month"/></label>
    </div>
  );
}
