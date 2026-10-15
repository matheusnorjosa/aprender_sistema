/**
 * Trava do PR 7 das permissões: em `src/`, acesso se decide só por policy (`useAcesso().caps`,
 * vindas de `/api/me/policies/`) e, onde a regra é o superusuário, por `ehSuperusuario(user)`.
 *
 * Recusa ler, fora da allowlist de exibição:
 * - `.setores`, `.funcoes`, `.groups` (organograma do /me ou de outro usuário);
 * - `is_superintendencia` e `can_approve_super` (flags legadas do /me);
 * - `.is_superuser` (o helper único é `ehSuperusuario`).
 *
 * Varredura de texto (não AST), linha a linha, ignorando comentários. Controles positivos provam
 * que cada forma é pega; a allowlist é por identidade (entrada que não lê mais nada reprova).
 */
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, test } from 'vitest';

const SRC = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

/** Leituras de identidade que não podem decidir acesso. */
const LEITURA_DE_IDENTIDADE =
  /\??\.(setores|funcoes|groups|is_superuser)\b|\bis_superintendencia\b|\bcan_approve_super\b/;

/** Comentário (linha inteira) — prosa que cita o campo não conta. */
const LINHA_DE_COMENTARIO = /^\s*(\/\/|\*|\/\*)/;

/**
 * Arquivos que leem esses campos para EXIBIR ou para gravar o cadastro, nunca para decidir acesso.
 * Cada entrada diz por quê. Só encolhe.
 */
const ALLOWLIST: Readonly<Record<string, string>> = {
  'contexts/AcessoContext.ts': 'o helper único ehSuperusuario',
  'types/usuario.ts': 'tipo e guarda do payload de /api/me/',
  'hooks/useIdentity.ts': 'exibição: rótulo de papel (badge) a partir de setor/função',
  'pages/Perfil/PerfilPage.tsx': 'exibição: o titular vê os próprios setores e funções',
  'pages/AdminDAT/UsuariosPage.tsx': 'cadastro: setores, funções e superusuário de OUTRO usuário',
  'pages/Solicitacoes/NewSolicitacaoWizard.tsx': 'PR 8: o campo coordenador opcional ainda lê a função (fora do PR 7)',
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

function leiturasDeIdentidade(codigo: string): string[] {
  return codigo
    .split('\n')
    .filter((linha) => !LINHA_DE_COMENTARIO.test(linha) && LEITURA_DE_IDENTIDADE.test(linha))
    .map((linha) => linha.trim());
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
  ])('controle positivo: %s é pego (%s)', (codigo) => {
    expect(leiturasDeIdentidade(codigo)).toEqual([codigo]);
  });

  test.each([
    ['// o front lia user.setores aqui', 'comentário'],
    [' * `can_approve_super` saiu do front', 'JSDoc'],
    ["const { caps } = useAcesso(); if (caps.canAccessTravel) abrir();", 'policy'],
    ['if (ehSuperusuario(user)) mostrar();', 'helper'],
    ['setSetoresProduto(meta.setores_produto);', 'outro campo com prefixo parecido'],
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

  test('toda entrada da allowlist ainda lê algum desses campos (senão, saia dela)', () => {
    const semLeitura = Object.keys(ALLOWLIST).filter(
      (a) => leiturasDeIdentidade(readFileSync(join(SRC, a), 'utf8')).length === 0,
    );
    expect(semLeitura).toEqual([]);
  });
});
