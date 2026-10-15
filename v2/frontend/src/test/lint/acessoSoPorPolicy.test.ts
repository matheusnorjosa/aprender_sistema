/**
 * Trava do PR 7 das permissões: em `src/`, acesso se decide só por policy (`useAcesso().caps`,
 * vindas de `/api/me/policies/`) e, onde a regra é o superusuário, por `ehSuperusuario(user)`.
 *
 * Recusa ler, fora da allowlist de exibição:
 * - `setores`, `funcoes`, `groups` (organograma do /me ou de outro usuário), `permissions` (as
 *   capacidades cruas do /me) e `is_superuser` (o helper único é `ehSuperusuario`), por ponto, por
 *   colchete (aspas ou crase) ou desestruturados, inclusive aninhados;
 * - `is_superintendencia` e `can_approve_super` (flags legadas do /me);
 * - `useIdentity`/`computeIdentity` (flags de organograma: `inDAT`, `isCoordenador`...).
 *
 * Varredura de texto (não AST), ignorando comentários. Controles positivos provam que cada forma é
 * pega. A allowlist fixa quantas leituras cada arquivo tem: leitura nova num arquivo da allowlist
 * reprova, e quem lê menos tem de baixar o número (só encolhe).
 */
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, test } from 'vitest';

const SRC = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

const CAMPO = '(?:setores|funcoes|groups|permissions|is_superuser)';

/** Leituras de identidade que não podem decidir acesso. */
const LEITURA_DE_IDENTIDADE = new RegExp(
  [
    String.raw`\??\.${CAMPO}\b`, // user.setores, me?.is_superuser
    String.raw`\[\s*['"\`]${CAMPO}['"\`]\s*\]`, // user['setores'], user[`setores`]
    // const { setores } = user; ({ is_superuser }) => ...; ({ funcoes }: CurrentUser) — pode quebrar
    // linha. Aninhado ({ user: { setores } }: P): depois do `}` de dentro, os `}` de fora.
    String.raw`\{[^{}]*(?<![\w'"\`./-])${CAMPO}\b(?!['"\`])[^{}]*\}(?:[^{}]*\})*\s*(?:=(?![=>])|\)|:)`,
    String.raw`\bis_superintendencia\b`,
    String.raw`\bcan_approve_super\b`,
    String.raw`\b(?:useIdentity|computeIdentity)\b`,
  ].join('|'),
  'g',
);

/** Comentário (linha inteira) — prosa que cita o campo não conta. */
const LINHA_DE_COMENTARIO = /^\s*(\/\/|\*|\/\*)/;

/**
 * Arquivos que leem esses campos para EXIBIR ou para gravar o cadastro, nunca para decidir acesso:
 * o motivo e o número exato de leituras. Só encolhe.
 */
const ALLOWLIST: Readonly<Record<string, { motivo: string; leituras: number }>> = {
  'contexts/AcessoContext.ts': { motivo: 'o helper único ehSuperusuario', leituras: 1 },
  'types/usuario.ts': { motivo: 'tipo e guarda do payload de /api/me/', leituras: 9 },
  'pages/AdminDAT/GruposPage.tsx': {
    motivo: 'exibição: permissões de um GRUPO agrupadas por categoria (só leitura)',
    leituras: 2,
  },
  'hooks/useIdentity.ts': { motivo: 'exibição: rótulo de papel (badge) a partir de setor/função', leituras: 7 },
  'pages/Perfil/PerfilPage.tsx': { motivo: 'exibição: o titular vê os próprios setores e funções', leituras: 2 },
  'pages/AdminDAT/UsuariosPage.tsx': {
    motivo: 'cadastro: setores, funções e superusuário de OUTRO usuário',
    leituras: 8,
  },
  'pages/AdminDAT/usuario_form_helpers.ts': {
    motivo: 'cadastro: monta o payload (superusuário, funções) de OUTRO usuário',
    leituras: 4,
  },
  'pages/Solicitacoes/NewSolicitacaoWizard.tsx': {
    motivo: 'PR 8: o campo coordenador opcional ainda lê a função (fora do PR 7)',
    leituras: 1,
  },
};

function arquivosDoSrc(dir = SRC): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entrada) => {
    const caminho = join(dir, entrada.name);
    if (entrada.isDirectory()) {
      return entrada.name === '__tests__' || entrada.name === 'test' ? [] : arquivosDoSrc(caminho);
    }
    if (!/\.(ts|tsx)$/.test(entrada.name) || /\.(test|spec)\.tsx?$/.test(entrada.name)) return [];
    return [relative(SRC, caminho).split('\\').join('/')];
  });
}

/** Linhas (sem espaço nas pontas) onde começa cada leitura; a desestruturação pode quebrar linha. */
function leiturasDeIdentidade(codigo: string): string[] {
  const linhas = codigo.split('\n');
  const semComentario = linhas.map((linha) => (LINHA_DE_COMENTARIO.test(linha) ? '' : linha)).join('\n');
  const inicios = new Set(
    [...semComentario.matchAll(LEITURA_DE_IDENTIDADE)].map(
      (m) => semComentario.slice(0, m.index).split('\n').length - 1,
    ),
  );
  return [...inicios].sort((a, b) => a - b).map((i) => (linhas[i] ?? '').trim());
}

describe('lint: acesso só por policy (PR 7 das permissões)', () => {
  test.each([
    ["if (user.setores.includes('DAT')) return true;", '.setores'],
    ["const coord = (me.funcoes ?? []).includes('Coordenador');", '.funcoes'],
    ["const isDat = user?.groups?.includes('DAT');", '?.groups'],
    ['const sup = user.is_superintendencia === true;', 'is_superintendencia'],
    ['const pode = me.can_approve_super;', 'can_approve_super'],
    ['const { can_approve_super } = me;', 'can_approve_super desestruturado'],
    ['if (auth.user?.is_superuser) mostrar();', '?.is_superuser'],
    ["const { setores, funcoes } = user; if (setores.includes('DAT')) abrir();", 'desestruturado'],
    ['const { is_superuser: su } = me;', 'desestruturado com outro nome'],
    ['const pode = usuarios.some(({ is_superuser }) => is_superuser);', 'desestruturado no parâmetro'],
    ["if (user['is_superuser']) mostrar();", 'colchete'],
    ['const grupos = me["groups"];', 'colchete com aspas duplas'],
    ['if (useIdentity(user).inDAT) abrir();', 'useIdentity'],
    ['if (computeIdentity(me).isAdmin) abrir();', 'computeIdentity'],
    ["export function Menu({ user: { setores } }: Props) { return setores.includes('DAT'); }", 'aninhado no parâmetro'],
    ['const { me: { funcoes } } = props;', 'aninhado'],
    ['const { me: { funcoes }, id } = props;', 'aninhado com chave depois'],
    ["if (user[`setores`].includes('DAT')) abrir();", 'colchete com crase'],
    ["const pode = me.permissions.includes('core.view_x');", '.permissions do /me'],
  ])('controle positivo: %s é pego (%s)', (codigo) => {
    expect(leiturasDeIdentidade(codigo)).toEqual([codigo]);
  });

  test('controle positivo: desestruturação em várias linhas é pega na linha que abre', () => {
    const codigo = ['const {', '  id,', '  setores,', '} = user;'].join('\n');
    expect(leiturasDeIdentidade(codigo)).toEqual(['const {']);
  });

  test.each([
    ['// o front lia user.setores aqui', 'comentário'],
    [' * `can_approve_super` saiu do front', 'JSDoc'],
    ["const { caps } = useAcesso(); if (caps.canAccessTravel) abrir();", 'policy'],
    ['if (ehSuperusuario(user)) mostrar();', 'helper'],
    ['setSetoresProduto(meta.setores_produto);', 'outro campo com prefixo parecido'],
    ["{ key: 'setores', path: '/dat/admin/setores' },", 'texto que cita o campo'],
    ['const { caps, ehSuperusuario } = useAcesso();', 'desestruturação de outro objeto'],
    ['type Props = { user: { setores: string[] } };', 'tipo aninhado que declara o campo'],
  ])('não pega: %s (%s)', (codigo) => {
    expect(leiturasDeIdentidade(codigo)).toEqual([]);
  });

  test('src/ não lê identidade para decidir acesso fora da allowlist', () => {
    const arquivos = arquivosDoSrc();
    // Piso anti-vacuidade: se a varredura não achar src/, passaria por vazio.
    expect(arquivos.length).toBeGreaterThan(100);
    const violacoes = arquivos
      .filter((a) => !(a in ALLOWLIST))
      .flatMap((a) => leiturasDeIdentidade(readFileSync(join(SRC, a), 'utf8')).map((l) => `${a}: ${l}`));
    expect(
      violacoes,
      'Decida por policy (useAcesso().caps) ou, se a regra é o superusuário, por ehSuperusuario(user).',
    ).toEqual([]);
  });

  test('cada arquivo da allowlist lê exatamente o número registrado (leitura nova reprova)', () => {
    const contagem = Object.fromEntries(
      Object.keys(ALLOWLIST).map((a) => [a, leiturasDeIdentidade(readFileSync(join(SRC, a), 'utf8')).length]),
    );
    const registrado = Object.fromEntries(Object.entries(ALLOWLIST).map(([a, { leituras }]) => [a, leituras]));
    expect(contagem).toEqual(registrado);
  });

  test('toda entrada da allowlist ainda lê algum desses campos (senão, saia dela)', () => {
    expect(Object.entries(ALLOWLIST).filter(([, { leituras }]) => leituras === 0)).toEqual([]);
  });
});
