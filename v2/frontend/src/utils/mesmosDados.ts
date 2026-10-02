/**
 * Compara duas respostas da API pelo conteúdo (JSON). As telas com atualização automática
 * usam isto para só trocar o estado quando algo mudou: resposta igual mantém a mesma
 * referência e a tela não é redesenhada.
 */
export function mesmosDados(a: unknown, b: unknown): boolean {
  return a === b || JSON.stringify(a) === JSON.stringify(b);
}
