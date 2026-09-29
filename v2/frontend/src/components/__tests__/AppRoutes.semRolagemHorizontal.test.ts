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

import ts from 'typescript';
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
  /** Componente de página renderizado (último JSX do `element` que não é involucro do gate). */
  componente: string | undefined;
}

/** Componentes que só embrulham a página (o gate), não são a página. */
const INVOLUCROS = new Set(['RequirePolicy']);

function atributo(elemento: ts.JsxAttributes, nome: string): ts.JsxAttribute | undefined {
  return elemento.properties.find((p): p is ts.JsxAttribute => ts.isJsxAttribute(p) && p.name.getText() === nome);
}

/** Valor literal de `nome="x"`, `nome='x'`, `nome={'x'}` ou `nome={`x`}`; qualquer outra forma reprova. */
function literal(atr: ts.JsxAttribute | undefined, onde: string): string | undefined {
  if (atr === undefined) return undefined;
  const valor = atr.initializer;
  const expr = valor && ts.isJsxExpression(valor) ? valor.expression : valor;
  if (expr && (ts.isStringLiteral(expr) || ts.isNoSubstitutionTemplateLiteral(expr))) return expr.text;
  throw new Error(`${onde}: ${atr.name.getText()} não é literal (${atr.getText()}); o leitor não consegue conferir a cobertura`);
}

/**
 * Lê os `<Route>` pela árvore do compilador TypeScript (não por regex de uma linha):
 * formato, quebra de linha, aspas e ordem dos atributos não importam. O que o leitor
 * não sabe interpretar (path não literal, rota aninhada, rota sem path) reprova.
 */
function lerRotas(fonte: string): RotaDeclarada[] {
  const arquivo = ts.createSourceFile('AppRoutes.tsx', fonte, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const rotas: RotaDeclarada[] = [];

  const lerElement = (expr: ts.Node): Pick<RotaDeclarada, 'redirectPara' | 'componente'> => {
    let redirectPara: string | undefined;
    const componentes: string[] = [];
    const visitar = (no: ts.Node): void => {
      if (ts.isJsxSelfClosingElement(no) || ts.isJsxOpeningElement(no)) {
        const tag = no.tagName.getText(arquivo);
        if (tag === 'Navigate') redirectPara = literal(atributo(no.attributes, 'to'), 'Navigate');
        else if (!INVOLUCROS.has(tag)) componentes.push(tag);
      }
      ts.forEachChild(no, visitar);
    };
    visitar(expr);
    return { redirectPara, componente: componentes.at(-1) };
  };

  const visitar = (no: ts.Node): void => {
    if (ts.isJsxElement(no) && no.openingElement.tagName.getText(arquivo) === 'Route') {
      const filhos = no.children.filter((f) => !ts.isJsxText(f) || f.getText(arquivo).trim() !== '');
      if (filhos.length > 0) throw new Error(`rota aninhada não suportada pelo leitor: ${no.openingElement.getText(arquivo)}`);
    }
    if ((ts.isJsxSelfClosingElement(no) || ts.isJsxOpeningElement(no)) && no.tagName.getText(arquivo) === 'Route') {
      const path = literal(atributo(no.attributes, 'path'), 'Route');
      if (path === undefined) throw new Error(`Route sem path: ${no.getText(arquivo)}`);
      const element = atributo(no.attributes, 'element')?.initializer;
      rotas.push({ path, ...(element ? lerElement(element) : { redirectPara: undefined, componente: undefined }) });
      return;
    }
    ts.forEachChild(no, visitar);
  };
  visitar(arquivo);
  return rotas;
}

const rotas = lerRotas(readFileSync(APP_ROUTES, 'utf8'));
const pathsMedidos = ROTAS_MEDIDAS.map((r) => r.path);
const porPath = new Map(rotas.map((r) => [r.path, r]));

describe('leitor do AppRoutes: controles de formato', () => {
  const FONTE = [
    'export function Rotas() {',
    '  return (',
    '    <Routes>',
    '      <Route',
    '        path="/varias-linhas"',
    '        element={<RequirePolicy policy="p" policies={policies}><PaginaA /></RequirePolicy>}',
    '      />',
    "      <Route path='/aspas-simples' element={<PaginaB />} />",
    '      <Route element={<PaginaC />} path="/element-antes" />',
    "      <Route path={'/expressao'} element={<Navigate to='/varias-linhas' replace />} />",
    '    </Routes>',
    '  );',
    '}',
  ].join('\n');

  test('lê rota em várias linhas, com aspas simples, com element antes de path e path em expressão', () => {
    expect(lerRotas(FONTE)).toEqual([
      { path: '/varias-linhas', redirectPara: undefined, componente: 'PaginaA' },
      { path: '/aspas-simples', redirectPara: undefined, componente: 'PaginaB' },
      { path: '/element-antes', redirectPara: undefined, componente: 'PaginaC' },
      { path: '/expressao', redirectPara: '/varias-linhas', componente: undefined },
    ]);
  });

  test('path que não é literal reprova em vez de sumir da cobertura', () => {
    expect(() => lerRotas('const x = <Route path={ROTA} element={<PaginaA />} />;')).toThrow(/path/);
  });

  test('rota aninhada (Route com filhos) reprova em vez de sumir da cobertura', () => {
    expect(() =>
      lerRotas('const x = <Route path="/a" element={<Layout />}><Route path="b" element={<PaginaA />} /></Route>;')
    ).toThrow(/aninhada/);
  });
});

describe('spec sem-rolagem-horizontal cobre todas as rotas do AppRoutes', () => {
  test('o leitor do AppRoutes enxerga as rotas (piso anti-vacuidade)', () => {
    // 53 rotas em 2026-09-29. Se o formato do AppRoutes mudar e o leitor deixar
    // de enxergar as rotas, este piso reprova em vez de a cobertura passar por vazio.
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
