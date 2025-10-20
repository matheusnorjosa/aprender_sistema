export async function apiGet<T=any>(path: string, params?: Record<string,string|number|undefined>) : Promise<T> {
  const url = new URL(path, window.location.origin);
  if (params) Object.entries(params).forEach(([k,v]) => { if (v!==undefined) url.searchParams.set(k,String(v)); });
  const res = await fetch(url.toString(), { credentials: 'include' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}
