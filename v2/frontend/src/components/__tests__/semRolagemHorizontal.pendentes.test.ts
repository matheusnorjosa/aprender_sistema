/**
 * Ratchet da lista PENDENTES do spec "sem rolagem horizontal" (Programa C, C0).
 *
 * PENDENTES é a dívida medida: rota × largura que rola hoje, rodando com `test.fail`.
 * Sem trava, uma tela nova (ou uma regressão) que passe a rolar poderia entrar na
 * lista calada e o spec ficaria verde. Este teste exige:
 * - toda combinação de PENDENTES está na LINHA_DE_BASE medida (nada novo entra), e toda
 *   combinação de PENDENTES_SO_LINUX (diferença de fonte na CI) na LINHA_DE_BASE_SO_LINUX;
 * - o tamanho das duas listas somadas é exatamente TETO_PENDENTES, que só desce: consertou
 *   uma tela e tirou a combinação? Baixe o teto e tire-a da linha de base junto;
 * - a linha de base não tem folga: é exatamente PENDENTES (e a só-Linux, PENDENTES_SO_LINUX).
 * Mexer na linha de base ou subir o teto é decisão explícita, visível no diff deste arquivo.
 */
import { describe, expect, test } from 'vitest';

import {
  NAO_MEDIDOS,
  PENDENTES,
  PENDENTES_SO_LINUX,
  ROTAS_MEDIDAS,
  type RotaMedida,
} from '../../../e2e/checklist/sem-rolagem-horizontal.rotas';

type ListaPendentes = Readonly<Record<string, readonly number[]>>;

/** PENDENTES (todas as plataformas) e PENDENTES_SO_LINUX (só na referência, o Chromium Linux da CI). */
interface Pendencias {
  todas: ListaPendentes;
  soLinux: ListaPendentes;
}

/**
 * Medida em 2026-09-29 (main acd04afd), menos o que o Programa C consertou. 112 combinações da
 * 1ª medição, mais 14 que vieram de critério e vistas novos, não de regressão: o corte sem
 * reticências em Coordenadores (4) e as vistas Coordenadores "Lista" (4) e "Por área" (2) e Mapa
 * "Lista" (4). O C1 tirou 9 e o C2 tirou 27 (as mesmas que saíram de PENDENTES). Consertou uma tela? Tire as
 * combinações daqui também (o ratchet reprova folga: o que ficasse aqui poderia voltar a
 * PENDENTES sem ele ver). Não edite para acomodar tela nova: conserte a tela.
 */
const LINHA_DE_BASE: ListaPendentes = {
  '/dashboards': [360, 768, 1024],
  '/dashboards/compras': [360, 768, 1024, 1280],
  '/dashboards/equipe': [360, 768, 1024, 1280],
  '/dashboards/gcal': [360, 768, 1024],
  '/mapa-brasil': [360, 1024, 1280],
  '/mapa-brasil#lista': [360, 1024, 1280],
  '/solicitacoes/minhas': [360, 768, 1024, 1280],
  '/solicitacoes/publicacao': [360, 768, 1024, 1280],
  '/solicitacoes/:id/editar': [360],
  '/solicitacoes/aprovacoes': [360, 768, 1024, 1280],
  '/solicitacoes/disponibilidade': [360, 768, 1024],
  '/solicitacoes/bloqueios': [360, 768, 1024, 1280],
  '/solicitacoes/deslocamentos': [360, 768, 1024, 1280],
  '/solicitacoes/meus-eventos': [360, 768, 1024, 1280],
  '/controle/acoes': [360, 768, 1024, 1280],
  '/controle/compras': [360, 768, 1024, 1280],
  '/controle/coordenadores': [360, 768, 1024, 1280],
  '/controle/coordenadores#lista': [360, 768, 1024, 1280],
  '/controle/coordenadores#area': [360],
  '/controle/plano-formacoes': [360, 768, 1024, 1280],
  '/controle/pre-agenda': [360, 768, 1024, 1280],
  '/acoes-notificacao': [360, 768, 1024, 1280],
  '/notificacoes-internas': [360, 768],
  '/dat/admin/projetos': [360, 768, 1024],
  '/dat/cadastros': [360, 768, 1024, 1280],
  '/dat/registros': [360, 768, 1024, 1280],
};

/**
 * Linha de base de PENDENTES_SO_LINUX: medida na CI (Chromium Linux, a referência) em
 * 29/09/2026, run 36655341855. Rolam por diferença de fonte (+18 e +4 px) e não no Windows.
 */
const LINHA_DE_BASE_SO_LINUX: ListaPendentes = {
  '/dashboards': [1280],
  '/dashboards/gcal': [1280],
};

/**
 * Tamanho atual de PENDENTES mais PENDENTES_SO_LINUX (90 + 2). Só desce. C0: 126 + 2; o C1
 * tirou 9 (as 4 de Usuários e 5 que a sidebar nova liberou a 768 e 1024); o C2 tirou 27 (Admin
 * DAT: grupos, setores, funções, gerências, municípios, produtos e projetos gerais).
 */
const TETO_PENDENTES = 92;

const SO_LINUX = ' (só Linux)';

function listar(lista: ListaPendentes, sufixo = ''): string[] {
  return Object.entries(lista).flatMap(([chave, larguras]) => larguras.map((l) => `${chave} @ ${l}px${sufixo}`));
}

/** As combinações só-Linux levam o sufixo: passar uma de lista também é mudança de linha de base. */
function combinacoes(pendencias: Pendencias): string[] {
  return [...listar(pendencias.todas), ...listar(pendencias.soLinux, SO_LINUX)];
}

function conferirRatchet(pendentes: Pendencias, base: Pendencias, teto: number): string[] {
  const atuais = combinacoes(pendentes);
  const naBase = new Set(combinacoes(base));
  const todas = new Set(listar(pendentes.todas));
  const problemas = [
    ...listar(pendentes.soLinux)
      .filter((c) => todas.has(c))
      .map((c) => `combinação nas duas listas (PENDENTES e PENDENTES_SO_LINUX): ${c}`),
    ...atuais.filter((c, i) => atuais.indexOf(c) !== i).map((c) => `combinação repetida: ${c}`),
    ...atuais.filter((c) => !naBase.has(c)).map((c) => `combinação fora da linha de base: ${c}`),
  ];
  if (problemas.length > 0) return problemas;
  if (atuais.length > teto) return [`PENDENTES tem ${atuais.length} combinações e o teto é ${teto}: o teto só desce`];
  if (atuais.length < teto) {
    return [
      `PENDENTES encolheu para ${atuais.length}: baixe TETO_PENDENTES de ${teto} para ${atuais.length} ` +
        'e tire da LINHA_DE_BASE o que foi consertado',
    ];
  }
  // Sem folga: a base é exatamente PENDENTES. O que sobrasse nela poderia voltar sem o ratchet ver.
  const pendentesAgora = new Set(atuais);
  return [...naBase]
    .filter((c) => !pendentesAgora.has(c))
    .map(
      (c) =>
        `folga na linha de base: ${c} não está em PENDENTES. Consertou a tela? Tire a combinação da ` +
        'LINHA_DE_BASE (a só-Linux, da LINHA_DE_BASE_SO_LINUX)'
    );
}

describe('ratchet de PENDENTES: controles', () => {
  const BASE: Pendencias = { todas: { '/a': [360, 768], '/b': [360] }, soLinux: { '/c': [1280] } };
  const so = (todas: ListaPendentes, soLinux: ListaPendentes = { '/c': [1280] }): Pendencias => ({ todas, soLinux });

  test('combinação nova fora da linha de base reprova', () => {
    expect(conferirRatchet(so({ '/a': [360, 768], '/b': [360], '/nova': [1280] }), BASE, 5)).toEqual([
      'combinação fora da linha de base: /nova @ 1280px',
    ]);
  });

  test('entrada só Linux nova precisa estar na linha de base', () => {
    expect(conferirRatchet(so(BASE.todas, { '/c': [1280], '/d': [1024] }), BASE, 5)).toEqual([
      'combinação fora da linha de base: /d @ 1024px (só Linux)',
    ]);
  });

  test('passar uma combinação de todas as plataformas para só Linux reprova', () => {
    expect(conferirRatchet(so({ '/a': [360], '/b': [360] }, { '/a': [768], '/c': [1280] }), BASE, 4)).toEqual([
      'combinação fora da linha de base: /a @ 768px (só Linux)',
    ]);
  });

  test('a mesma combinação nas duas listas reprova', () => {
    expect(conferirRatchet(so(BASE.todas, { '/a': [360], '/c': [1280] }), BASE, 5)).toEqual([
      'combinação nas duas listas (PENDENTES e PENDENTES_SO_LINUX): /a @ 360px',
      'combinação fora da linha de base: /a @ 360px (só Linux)',
    ]);
  });

  test('troca 1 por 1 (conserta uma, entra outra) reprova', () => {
    expect(conferirRatchet(so({ '/a': [360, 1024], '/b': [360] }), BASE, 4)).toEqual([
      'combinação fora da linha de base: /a @ 1024px',
    ]);
  });

  test('lista maior que o teto reprova (só Linux conta no teto)', () => {
    expect(conferirRatchet(BASE, BASE, 3)).toEqual(['PENDENTES tem 4 combinações e o teto é 3: o teto só desce']);
  });

  test('lista menor que o teto pede para baixar o teto e limpar a linha de base', () => {
    expect(conferirRatchet(so({ '/a': [360] }), BASE, 4)).toEqual([
      'PENDENTES encolheu para 2: baixe TETO_PENDENTES de 4 para 2 e tire da LINHA_DE_BASE o que foi consertado',
    ]);
  });

  test('combinação consertada que volta a PENDENTES reprova', () => {
    // '/b @ 360' foi consertada e saiu da base; voltar com ela, mesmo com o teto folgado, reprova.
    const semB: Pendencias = { todas: { '/a': [360, 768] }, soLinux: { '/c': [1280] } };
    expect(conferirRatchet(BASE, semB, 4)).toEqual(['combinação fora da linha de base: /b @ 360px']);
  });

  test('combinação repetida reprova', () => {
    expect(conferirRatchet(so({ '/a': [360, 360, 768], '/b': [360] }), BASE, 5)).toEqual([
      'combinação repetida: /a @ 360px',
    ]);
  });

  test('folga na linha de base reprova: consertou, baixou o teto e esqueceu a base', () => {
    // '/a @ 768' saiu de PENDENTES e o teto desceu, mas a combinação ficou na base: ela
    // poderia voltar a PENDENTES (com o teto de volta a 4) sem o ratchet ver.
    expect(conferirRatchet(so({ '/a': [360], '/b': [360] }), BASE, 3)).toEqual([
      'folga na linha de base: /a @ 768px não está em PENDENTES. Consertou a tela? Tire a combinação da ' +
        'LINHA_DE_BASE (a só-Linux, da LINHA_DE_BASE_SO_LINUX)',
    ]);
  });

  test('folga na linha de base só Linux também reprova', () => {
    expect(conferirRatchet(so(BASE.todas, {}), BASE, 3)).toEqual([
      'folga na linha de base: /c @ 1280px (só Linux) não está em PENDENTES. Consertou a tela? Tire a ' +
        'combinação da LINHA_DE_BASE (a só-Linux, da LINHA_DE_BASE_SO_LINUX)',
    ]);
  });

  test('lista igual à base e ao teto passa', () => {
    expect(conferirRatchet(BASE, BASE, 4)).toEqual([]);
  });
});

/** Devolve `chave @ largura` a PENDENTES, com o teto folgado em 1, e confere o ratchet real. */
function devolverAPendentes(chave: string, largura: number): string[] {
  const devolta = { ...PENDENTES, [chave]: [...(PENDENTES[chave] ?? []), largura] };
  return conferirRatchet(
    { todas: devolta, soLinux: PENDENTES_SO_LINUX },
    { todas: LINHA_DE_BASE, soLinux: LINHA_DE_BASE_SO_LINUX },
    TETO_PENDENTES + 1
  );
}

describe('ratchet de PENDENTES: lista real', () => {
  test('PENDENTES está dentro da linha de base e no teto', () => {
    expect(
      conferirRatchet(
        { todas: PENDENTES, soLinux: PENDENTES_SO_LINUX },
        { todas: LINHA_DE_BASE, soLinux: LINHA_DE_BASE_SO_LINUX },
        TETO_PENDENTES
      )
    ).toEqual([]);
  });

  // O que o C1 consertou (30/09/2026) saiu da linha de base: voltar a rolar e voltar a
  // PENDENTES reprova, mesmo baixando o teto de menos ("troca 1 por 1" com a lista real).
  test.each([
    ['/dat/admin/usuarios', 360],
    ['/dat/admin/usuarios', 768],
    ['/dat/admin/usuarios', 1024],
    ['/dat/admin/usuarios', 1280],
    ['/mapa-brasil', 768],
    ['/mapa-brasil#lista', 768],
    ['/solicitacoes/:id/editar', 768],
    ['/controle/coordenadores#area', 768],
    ['/notificacoes-internas', 1024],
  ] as const)('%s @ %ipx, consertada no C1, não volta a PENDENTES', (chave, largura) => {
    expect(devolverAPendentes(chave, largura)).toEqual([`combinação fora da linha de base: ${chave} @ ${largura}px`]);
  });

  // O que o C2 consertou (30/09/2026, Admin DAT) também saiu da linha de base.
  const CONSERTADAS_NO_C2: ListaPendentes = {
    '/dat/admin/grupos': [360, 768, 1024, 1280],
    '/dat/admin/setores': [360, 768, 1024, 1280],
    '/dat/admin/funcoes': [360, 768, 1024, 1280],
    '/dat/admin/gerencias': [360, 768, 1024, 1280],
    '/dat/admin/municipios': [360, 768, 1024, 1280],
    '/dat/admin/produtos': [360, 768, 1024, 1280],
    '/dat/admin/projetos-gerais': [360, 768, 1024],
  };
  test.each(Object.entries(CONSERTADAS_NO_C2).flatMap(([chave, larguras]) => larguras.map((l) => [chave, l] as const)))(
    '%s @ %ipx, consertada no C2, não volta a PENDENTES',
    (chave, largura) => {
      expect(devolverAPendentes(chave, largura)).toEqual([`combinação fora da linha de base: ${chave} @ ${largura}px`]);
    }
  );
});

/**
 * Exceções à medição: rota com relógio do navegador fixo (`relogio`) e rota × largura que o spec
 * não mede (`naoMedirEm`). As duas podem esconder dívida (um mês sem evento faz a Grade caber; uma
 * largura fora da medição não reprova nunca), por isso seguem a regra da LINHA_DE_BASE: a lista
 * é exatamente esta, nada entra sem mudar este arquivo, e quem volta a ser medido sai daqui.
 * Toda largura não medida tem o motivo em NAO_MEDIDOS (chave `path @ largura px`) e não pode
 * estar também em PENDENTES.
 */
const EXCECOES_DA_MEDICAO: readonly string[] = [
  // 01/10/2026: a Grade desenha o mês de hoje do navegador, e a largura dela mudava com o dia em
  // que a CI rodava (detalhe no comentário da rota e em NAO_MEDIDOS). O C4 redesenha a Grade.
  '/solicitacoes/disponibilidade: relógio fixo em 2026-01-15T12:00:00-03:00',
  '/solicitacoes/disponibilidade @ 1280px: não medida',
];

type RotaComExcecao = Pick<RotaMedida, 'path' | 'relogio' | 'naoMedirEm'>;

function conferirExcecoes(
  rotas: readonly RotaComExcecao[],
  base: readonly string[],
  naoMedidos: Readonly<Record<string, string>>,
  pendentes: Pendencias
): string[] {
  const atuais = rotas.flatMap((r) => [
    ...(r.relogio ? [`${r.path}: relógio fixo em ${r.relogio}`] : []),
    ...(r.naoMedirEm ?? []).map((l) => `${r.path} @ ${l}px: não medida`),
  ]);
  const pendente = (path: string, largura: number) =>
    [pendentes.todas, pendentes.soLinux].some((lista) =>
      Object.entries(lista).some(([chave, ls]) => (chave === path || chave.startsWith(`${path}#`)) && ls.includes(largura))
    );
  const naoMedidas = new Set(rotas.flatMap((r) => (r.naoMedirEm ?? []).map((l) => `${r.path} @ ${l}px`)));
  return [
    ...atuais.filter((e) => !base.includes(e)).map((e) => `exceção fora da linha de base: ${e}`),
    ...base.filter((e) => !atuais.includes(e)).map((e) => `folga na linha de base de exceções: ${e} (tire-a de EXCECOES_DA_MEDICAO)`),
    ...rotas.flatMap((r) =>
      (r.naoMedirEm ?? []).flatMap((l) => [
        ...(naoMedidos[`${r.path} @ ${l}px`] ? [] : [`sem motivo em NAO_MEDIDOS: ${r.path} @ ${l}px`]),
        ...(pendente(r.path, l) ? [`não medida e em PENDENTES ao mesmo tempo: ${r.path} @ ${l}px`] : []),
      ])
    ),
    // O relógio fixo existe para medir o pior caso de colunas: mês de 31 dias.
    ...rotas
      .filter((r) => r.relogio && diasNoMes(r.relogio) !== 31)
      .map((r) => `relógio fixo num mês sem 31 dias: ${r.path} (${r.relogio})`),
    // Motivo sem largura correspondente desmentiria o código quando a rota voltar a ser medida.
    ...Object.keys(naoMedidos)
      .filter((k) => /^\S+ @ \d+px$/.test(k) && !naoMedidas.has(k))
      .map((k) => `motivo órfão em NAO_MEDIDOS: ${k} (a rota é medida nessa largura)`),
  ];
}

function diasNoMes(iso: string): number {
  const [ano, mes] = iso.slice(0, 7).split('-').map(Number);
  return new Date(Date.UTC(ano ?? 0, mes ?? 0, 0)).getUTCDate();
}

describe('exceções à medição: controles', () => {
  const RELOGIO = '2026-01-15T12:00:00-03:00';
  const ROTA: RotaComExcecao = { path: '/a', relogio: RELOGIO, naoMedirEm: [1280] };
  const BASE = [`/a: relógio fixo em ${RELOGIO}`, '/a @ 1280px: não medida'];
  const MOTIVO = { '/a @ 1280px': 'motivo' };
  const SEM_PENDENTES: Pendencias = { todas: {}, soLinux: {} };

  test('largura não medida fora da linha de base reprova', () => {
    expect(conferirExcecoes([ROTA, { path: '/b', naoMedirEm: [1024] }], BASE, { ...MOTIVO, '/b @ 1024px': 'x' }, SEM_PENDENTES)).toEqual([
      'exceção fora da linha de base: /b @ 1024px: não medida',
    ]);
  });

  test('relógio fixo em rota fora da linha de base reprova', () => {
    expect(conferirExcecoes([ROTA, { path: '/b', relogio: RELOGIO }], BASE, MOTIVO, SEM_PENDENTES)).toEqual([
      `exceção fora da linha de base: /b: relógio fixo em ${RELOGIO}`,
    ]);
  });

  test('largura não medida sem motivo em NAO_MEDIDOS reprova', () => {
    expect(conferirExcecoes([ROTA], BASE, {}, SEM_PENDENTES)).toEqual(['sem motivo em NAO_MEDIDOS: /a @ 1280px']);
  });

  test('largura não medida que também está em PENDENTES (ou num estado da rota) reprova', () => {
    expect(conferirExcecoes([ROTA], BASE, MOTIVO, { todas: { '/a#lista': [1280] }, soLinux: {} })).toEqual([
      'não medida e em PENDENTES ao mesmo tempo: /a @ 1280px',
    ]);
  });

  test('trocar a data do relógio muda a exceção: reprova até a linha de base mudar', () => {
    const outra = '2026-03-15T12:00:00-03:00';
    expect(conferirExcecoes([{ ...ROTA, relogio: outra }], BASE, MOTIVO, SEM_PENDENTES)).toEqual([
      `exceção fora da linha de base: /a: relógio fixo em ${outra}`,
      `folga na linha de base de exceções: /a: relógio fixo em ${RELOGIO} (tire-a de EXCECOES_DA_MEDICAO)`,
    ]);
  });

  test('relógio fixo num mês sem 31 dias reprova', () => {
    const fev = '2026-02-15T12:00:00-03:00';
    expect(
      conferirExcecoes([{ ...ROTA, relogio: fev }], [`/a: relógio fixo em ${fev}`, '/a @ 1280px: não medida'], MOTIVO, SEM_PENDENTES)
    ).toEqual([`relógio fixo num mês sem 31 dias: /a (${fev})`]);
  });

  test('motivo de largura não medida que sobrou em NAO_MEDIDOS reprova', () => {
    expect(conferirExcecoes([ROTA], BASE, { ...MOTIVO, '/c @ 768px': 'velho' }, SEM_PENDENTES)).toEqual([
      'motivo órfão em NAO_MEDIDOS: /c @ 768px (a rota é medida nessa largura)',
    ]);
  });

  test('voltou a medir e esqueceu a linha de base e o motivo: os dois reprovam', () => {
    expect(conferirExcecoes([{ path: '/a', relogio: RELOGIO }], BASE, MOTIVO, SEM_PENDENTES)).toEqual([
      'folga na linha de base de exceções: /a @ 1280px: não medida (tire-a de EXCECOES_DA_MEDICAO)',
      'motivo órfão em NAO_MEDIDOS: /a @ 1280px (a rota é medida nessa largura)',
    ]);
  });

  test('exceções iguais à linha de base, com motivo e fora de PENDENTES, passam', () => {
    expect(conferirExcecoes([ROTA, { path: '/b' }], BASE, MOTIVO, SEM_PENDENTES)).toEqual([]);
  });
});

describe('exceções à medição: lista real', () => {
  test('a Grade medida no mês fixo (sem evento) não sai de PENDENTES: só o C4, medindo com evento', () => {
    // Sem evento é a Grade mais estreita; caber assim não prova que a tela com dados reais cabe.
    expect(PENDENTES['/solicitacoes/disponibilidade']).toEqual([360, 768, 1024]);
  });

  test('relógio fixo e larguras não medidas são exatamente a linha de base, com motivo', () => {
    expect(
      conferirExcecoes(ROTAS_MEDIDAS, EXCECOES_DA_MEDICAO, NAO_MEDIDOS, { todas: PENDENTES, soLinux: PENDENTES_SO_LINUX })
    ).toEqual([]);
  });
});
