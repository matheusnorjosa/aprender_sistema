/**
 * Ratchet da lista PENDENTES do spec "sem rolagem horizontal" (Programa C, C0).
 *
 * PENDENTES é a dívida medida: rota × largura que rola hoje, rodando com `test.fail`.
 * Sem trava, uma tela nova (ou uma regressão) que passe a rolar poderia entrar na
 * lista calada e o spec ficaria verde. Este teste exige:
 * - toda combinação de PENDENTES está na LINHA_DE_BASE medida (nada novo entra);
 * - o tamanho de PENDENTES é exatamente TETO_PENDENTES, que só desce: consertou uma
 *   tela e tirou a combinação? Baixe o teto junto.
 * Mexer na linha de base ou subir o teto é decisão explícita, visível no diff deste arquivo.
 */
import { describe, expect, test } from 'vitest';

import { PENDENTES } from '../../../e2e/checklist/sem-rolagem-horizontal.rotas';

type ListaPendentes = Readonly<Record<string, readonly number[]>>;

/**
 * Medida em 2026-09-29 (main acd04afd). 112 combinações da 1ª medição, mais 14 que vieram de
 * critério e vistas novos, não de regressão: o corte sem reticências em Coordenadores (4) e as
 * vistas Coordenadores "Lista" (4) e "Por área" (2) e Mapa "Lista" (4). Não edite para acomodar
 * tela nova: conserte a tela.
 */
const LINHA_DE_BASE: ListaPendentes = {
  '/dashboards': [360, 768, 1024],
  '/dashboards/compras': [360, 768, 1024, 1280],
  '/dashboards/equipe': [360, 768, 1024, 1280],
  '/dashboards/gcal': [360, 768, 1024],
  '/mapa-brasil': [360, 768, 1024, 1280],
  '/mapa-brasil#lista': [360, 768, 1024, 1280],
  '/solicitacoes/minhas': [360, 768, 1024, 1280],
  '/solicitacoes/publicacao': [360, 768, 1024, 1280],
  '/solicitacoes/:id/editar': [360, 768],
  '/solicitacoes/aprovacoes': [360, 768, 1024, 1280],
  '/solicitacoes/disponibilidade': [360, 768, 1024],
  '/solicitacoes/bloqueios': [360, 768, 1024, 1280],
  '/solicitacoes/deslocamentos': [360, 768, 1024, 1280],
  '/solicitacoes/meus-eventos': [360, 768, 1024, 1280],
  '/controle/acoes': [360, 768, 1024, 1280],
  '/controle/compras': [360, 768, 1024, 1280],
  '/controle/coordenadores': [360, 768, 1024, 1280],
  '/controle/coordenadores#lista': [360, 768, 1024, 1280],
  '/controle/coordenadores#area': [360, 768],
  '/controle/plano-formacoes': [360, 768, 1024, 1280],
  '/controle/pre-agenda': [360, 768, 1024, 1280],
  '/acoes-notificacao': [360, 768, 1024, 1280],
  '/notificacoes-internas': [360, 768, 1024],
  '/dat/admin/usuarios': [360, 768, 1024, 1280],
  '/dat/admin/municipios': [360, 768, 1024, 1280],
  '/dat/admin/projetos': [360, 768, 1024],
  '/dat/admin/grupos': [360, 768, 1024, 1280],
  '/dat/admin/setores': [360, 768, 1024, 1280],
  '/dat/admin/funcoes': [360, 768, 1024, 1280],
  '/dat/admin/gerencias': [360, 768, 1024, 1280],
  '/dat/admin/produtos': [360, 768, 1024, 1280],
  '/dat/admin/projetos-gerais': [360, 768, 1024],
  '/dat/cadastros': [360, 768, 1024, 1280],
  '/dat/registros': [360, 768, 1024, 1280],
};

/** Tamanho atual de PENDENTES. Só desce. */
const TETO_PENDENTES = 126;

function combinacoes(lista: ListaPendentes): string[] {
  return Object.entries(lista).flatMap(([chave, larguras]) => larguras.map((l) => `${chave} @ ${l}px`));
}

function conferirRatchet(pendentes: ListaPendentes, base: ListaPendentes, teto: number): string[] {
  const atuais = combinacoes(pendentes);
  const naBase = new Set(combinacoes(base));
  const problemas = [
    ...atuais.filter((c, i) => atuais.indexOf(c) !== i).map((c) => `combinação repetida: ${c}`),
    ...atuais.filter((c) => !naBase.has(c)).map((c) => `combinação fora da linha de base: ${c}`),
  ];
  if (problemas.length > 0) return problemas;
  if (atuais.length > teto) return [`PENDENTES tem ${atuais.length} combinações e o teto é ${teto}: o teto só desce`];
  if (atuais.length < teto) return [`PENDENTES encolheu para ${atuais.length}: baixe TETO_PENDENTES de ${teto} para ${atuais.length}`];
  return [];
}

describe('ratchet de PENDENTES: controles', () => {
  const BASE: ListaPendentes = { '/a': [360, 768], '/b': [360] };

  test('combinação nova fora da linha de base reprova', () => {
    expect(conferirRatchet({ '/a': [360, 768], '/b': [360], '/nova': [1280] }, BASE, 4)).toEqual([
      'combinação fora da linha de base: /nova @ 1280px',
    ]);
  });

  test('troca 1 por 1 (conserta uma, entra outra) reprova', () => {
    expect(conferirRatchet({ '/a': [360, 1024], '/b': [360] }, BASE, 3)).toEqual([
      'combinação fora da linha de base: /a @ 1024px',
    ]);
  });

  test('lista maior que o teto reprova', () => {
    expect(conferirRatchet({ '/a': [360, 768], '/b': [360] }, BASE, 2)).toEqual([
      'PENDENTES tem 3 combinações e o teto é 2: o teto só desce',
    ]);
  });

  test('lista menor que o teto pede para baixar o teto', () => {
    expect(conferirRatchet({ '/a': [360] }, BASE, 3)).toEqual([
      'PENDENTES encolheu para 1: baixe TETO_PENDENTES de 3 para 1',
    ]);
  });

  test('combinação repetida reprova', () => {
    expect(conferirRatchet({ '/a': [360, 360, 768], '/b': [360] }, BASE, 4)).toEqual([
      'combinação repetida: /a @ 360px',
    ]);
  });

  test('lista igual à base e ao teto passa', () => {
    expect(conferirRatchet(BASE, BASE, 3)).toEqual([]);
  });
});

describe('ratchet de PENDENTES: lista real', () => {
  test('PENDENTES está dentro da linha de base e no teto', () => {
    expect(conferirRatchet(PENDENTES, LINHA_DE_BASE, TETO_PENDENTES)).toEqual([]);
  });
});
