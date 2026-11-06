/**
 * G30 — o que saiu de NAO_MEDIDOS e passou a ser medido pelo spec "sem rolagem horizontal".
 *
 * - a Home com os perfis aprovador e superusuário (os cartões mudam por perfil), além do Controle;
 * - a Nova Solicitação com a pergunta "Você pretende avaliar o formador?" aberta (lookup de projetos e
 *   de formadores interceptado: o formador vem avaliável);
 * - a troca obrigatória de senha (o /api/me/ interceptado diz `deve_trocar_senha`), tela que ocupa o
 *   lugar do sistema, sem a casca com "Sair".
 * Os avisos de agenda da Nova Solicitação (horário com conflito) seguem fora, com o motivo.
 */
import { describe, expect, test } from 'vitest';

import {
  MARCO_TROCA_DE_SENHA,
  NAO_MEDIDOS,
  ROTAS_MEDIDAS,
  TELA_TROCA_DE_SENHA,
} from '../../../e2e/checklist/sem-rolagem-horizontal.rotas';

describe('NAO_MEDIDOS: o que o G30 passou a medir', () => {
  test('a Home é medida também com o aprovador e o superusuário', () => {
    const home = ROTAS_MEDIDAS.find((r) => r.path === '/');
    expect(home?.perfil).toBe('controle');
    expect(home?.outrosPerfis).toEqual(['aprovador', 'superusuario']);
    expect(Object.keys(NAO_MEDIDOS).filter((k) => /Home/.test(k))).toEqual([]);
  });

  test('a pergunta de avaliar da Nova Solicitação saiu de NAO_MEDIDOS; os avisos de agenda ficam, com motivo', () => {
    const daNova = Object.entries(NAO_MEDIDOS).filter(([k]) => k.startsWith('/solicitacoes/nova'));
    expect(daNova.map(([k]) => k)).toEqual(['/solicitacoes/nova (avisos de agenda)']);
    expect(daNova.flatMap(([k, motivo]) => [k, motivo]).join(' ')).not.toMatch(/pergunta de avaliar e/);
  });

  test('a troca obrigatória de senha tem chave e título próprios, fora das rotas do AppRoutes', () => {
    expect(TELA_TROCA_DE_SENHA).toBe('troca-de-senha');
    expect(MARCO_TROCA_DE_SENHA).toBe('Defina sua senha');
    expect(ROTAS_MEDIDAS.some((r) => r.path === TELA_TROCA_DE_SENHA)).toBe(false);
  });
});
