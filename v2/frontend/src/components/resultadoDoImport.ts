/**
 * Resultado de importação no formato do ImportUploader (Programa C, C2; T9 da auditoria de UX).
 *
 * Os clientes de `api/ops` já achatam a resposta do backend (`{stats, pendencias}`) em
 * `ImportResult`. Pendência que bloqueia vira `errors` (o uploader mostra "Validação com Erros"
 * e não libera o Aplicar); aviso que não bloqueia vai para Pendências.
 */
import type { ImportResult } from '../api/ops';
import type { ApplyResult, ValidationResult } from './ImportUploader';

/** Inalteradas de verdade: `skipped` soma também as rejeitadas, que já aparecem nos erros. */
const inalteradas = (result: ImportResult): number => result.unchanged ?? result.skipped;

export function validacaoDoImport(result: ImportResult): ValidationResult {
  return {
    stats: { created: result.created, updated: result.updated, unchanged: inalteradas(result) },
    errors: result.errors.map((e) => `Linha ${e.row}: ${e.message}`),
    ...(result.warnings.length > 0 ? { pendencias: { avisos: result.warnings } } : {}),
  };
}

export function aplicacaoDoImport(result: ImportResult): ApplyResult {
  return { stats: { created: result.created, updated: result.updated, unchanged: inalteradas(result) } };
}
