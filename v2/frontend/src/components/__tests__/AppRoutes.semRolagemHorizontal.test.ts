/**
 * Cobertura do spec "sem rolagem horizontal" (Programa C, C0).
 *
 * Toda rota de `AppRoutes.tsx` tem de estar no spec Playwright
 * `e2e/checklist/sem-rolagem-horizontal.spec.ts`: medida (com o perfil que a
 * abre) ou declarada como redirect/alias de uma rota medida. Rota nova sem
 * entrada reprova aqui, sem precisar de browser nem backend.
 */
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, test } from 'vitest';

import {
  LARGURAS,
  PENDENTES,
  ROTAS_MEDIDAS,
  ROTAS_NAO_MEDIDAS,
  TELA_LOGIN,
} from '../../../e2e/checklist/sem-rolagem-horizontal.rotas';

const APP_ROUTES = resolve(dirname(fileURLToPath(import.meta.url)), '../AppRoutes.tsx');

interface RotaDeclarada {
  path: string;
  /** `to` do `<Navigate>`, quando a rota é redirect. */
  redirectPara: string | undefined;
  /** Componente de página renderizado (último JSX auto-fechado do `element`). */
  componente: string | undefined;
}

/** Cada `<Route path="..." element={...} />` do AppRoutes ocupa uma linha. */
function lerRotasDoAppRoutes(): RotaDeclarada[] {
  const fonte = readFileSync(APP_ROUTES, 'utf8');
  return Array.from(fonte.matchAll(/<Route path="([^"]+)" element=\{(.+)\} \/>/g), ([, path = '', element = '']) => {
    const redirect = /<Navigate to="([^"]+)"/.exec(element);
    const autoFechados = Array.from(element.matchAll(/<([A-Z]\w*)\b[^<>]*\/>/g), (m) => m[1]);
    return { path, redirectPara: redirect?.[1], componente: autoFechados.at(-1) };
  });
}

const rotas = lerRotasDoAppRoutes();
const pathsMedidos = ROTAS_MEDIDAS.map((r) => r.path);
const porPath = new Map(rotas.map((r) => [r.path, r]));

describe('spec sem-rolagem-horizontal cobre todas as rotas do AppRoutes', () => {
  test('o leitor do AppRoutes enxerga as rotas (piso anti-vacuidade)', () => {
    // 53 rotas em 2026-09-29. Se o formato do AppRoutes mudar e a regex deixar
    // de casar, este piso reprova em vez de a cobertura passar por vazio.
    expect(rotas.length).toBeGreaterThanOrEqual(50);
  });

  test('toda rota do AppRoutes está no spec (medida ou redirect/alias)', () => {
    const faltando = rotas.map((r) => r.path).filter((p) => !pathsMedidos.includes(p) && !(p in ROTAS_NAO_MEDIDAS));
    expect(faltando, 'rota nova: adicione em ROTAS_MEDIDAS (e2e/checklist/sem-rolagem-horizontal.rotas.ts)').toEqual([]);
  });

  test('o spec não lista rota que não existe mais no AppRoutes', () => {
    const sobrando = [...pathsMedidos, ...Object.keys(ROTAS_NAO_MEDIDAS)].filter((p) => !porPath.has(p));
    expect(sobrando).toEqual([]);
  });

  test('nenhuma rota aparece duas vezes', () => {
    const todas = [...pathsMedidos, ...Object.keys(ROTAS_NAO_MEDIDAS)];
    expect(todas.filter((p, i) => todas.indexOf(p) !== i)).toEqual([]);
  });

  test('redirect e alias apontam para rota medida e dizem a verdade sobre o AppRoutes', () => {
    const erros: string[] = [];
    for (const [path, { tipo, destino }] of Object.entries(ROTAS_NAO_MEDIDAS)) {
      const rota = porPath.get(path);
      const alvo = porPath.get(destino);
      if (!pathsMedidos.includes(destino)) erros.push(`${path}: destino ${destino} não é medido`);
      if (tipo === 'redirect' && rota?.redirectPara !== destino) {
        erros.push(`${path}: não é <Navigate to="${destino}"> no AppRoutes`);
      }
      if (tipo === 'alias' && (rota?.redirectPara !== undefined || rota?.componente !== alvo?.componente)) {
        erros.push(`${path}: renderiza ${rota?.componente ?? '?'}, mas ${destino} renderiza ${alvo?.componente ?? '?'}`);
      }
    }
    expect(erros).toEqual([]);
  });

  test('PENDENTES só cita rota medida (ou a tela de login) e larguras medidas', () => {
    const invalidas = Object.entries(PENDENTES).flatMap(([chave, larguras]) => [
      ...(chave === TELA_LOGIN || pathsMedidos.includes(chave) ? [] : [`${chave}: não é rota medida`]),
      ...larguras.filter((l) => !LARGURAS.includes(l)).map((l) => `${chave}: largura ${l} não é medida`),
    ]);
    expect(invalidas).toEqual([]);
  });
});
