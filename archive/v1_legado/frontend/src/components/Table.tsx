import React from 'react';

export function Table({columns, rows}:{columns:string[], rows:(string|number|null|undefined)[][]}) {
  return (
    <div className="overflow-auto">
      <table style={{width:'100%',borderCollapse:'collapse'}}>
        <thead>
          <tr>{columns.map((c,i)=><th key={i} style={{textAlign:'left',padding:8,borderBottom:'1px solid #ddd'}}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r,ri)=>(
            <tr key={ri}>
              {r.map((v,ci)=><td key={ci} style={{padding:8,borderBottom:'1px solid #f0f0f0',fontSize:14}}>{v as any}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
