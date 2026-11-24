/**
 * Guarda LOCAL dos testes da Integra contra nomes de pessoas reais (ata de 23/11 e PDFs de requisitos).
 *
 * A lista não fica no repositório, nem em hash: sha256 sem sal de prenome se reverte com uma lista pública
 * de nomes. Ela fica num arquivo de texto fora do git (um nome ou apelido composto por linha), cujo caminho
 * vem da variável de ambiente `INTEGRA_NOMES_REAIS`. Sem a variável ou sem o arquivo (CI, clone limpo), os
 * testes que usam a guarda são pulados. No CI vale a garantia do gerador: `dados/__tests__/gerador.test.ts`
 * confere a lista exata de nomes fictícios, então um nome novo só entra mudando o teste na revisão.
 */
import { existsSync, readFileSync } from 'node:fs';

export const normalizar = (texto: string): string =>
  texto.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '').replace(/\s+/g, ' ').trim();

/** Os nomes do arquivo, normalizados; `null` quando não há arquivo. */
export function lerNomesReais(caminho: string | undefined): Set<string> | null {
  if (!caminho || !existsSync(caminho)) return null;
  const nomes = readFileSync(caminho, 'utf-8').split(/\r?\n/).map(normalizar).filter(Boolean);
  return nomes.length > 0 ? new Set(nomes) : null;
}

const NOMES_REAIS = lerNomesReais(process.env['INTEGRA_NOMES_REAIS']);

/** A guarda só roda onde a lista existe (na máquina de quem tem a ata). */
export const guardaDeNomesReaisAtiva = NOMES_REAIS !== null;

/**
 * Quantas palavras soltas, ou pares de palavras seguidas, do texto estão na lista. Devolve só a contagem:
 * se o teste falhar, o nome não vai para o log.
 */
export function contarNomesReais(texto: string, nomes: ReadonlySet<string> | null = NOMES_REAIS): number {
  if (!nomes) return 0;
  const palavras = normalizar(texto).split(/[^\p{L}]+/u).filter(Boolean);
  const pares = palavras.slice(1).map((p, i) => `${palavras[i]} ${p}`);
  return [...palavras, ...pares].filter((t) => nomes.has(t)).length;
}
