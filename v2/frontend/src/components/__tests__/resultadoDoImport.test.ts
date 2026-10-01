/**
 * Adaptador único do resultado de importação para o ImportUploader (C2; T9 da auditoria de UX).
 *
 * O cliente (api/ops) já achata a resposta do backend em `ImportResult`; ler `stats`/`pendencias`
 * de novo dava 0/0/0 e "Validação OK" com pendência que bloqueia.
 */
import { describe, expect, test } from 'vitest';

import { __testing } from '../../api/ops';
import { aplicacaoDoImport, validacaoDoImport } from '../resultadoDoImport';

const RESULTADO = {
  created: 3,
  updated: 1,
  skipped: 2,
  errors: [{ row: 4, message: '[uf_missing] UF ausente — Cidade Fictícia' }],
  warnings: ['Linha 7: coluna grupos ignorada'],
};

describe('resultadoDoImport', () => {
  test('validação: contagens, pendência que bloqueia em errors e aviso em Pendências', () => {
    expect(validacaoDoImport(RESULTADO)).toEqual({
      stats: { created: 3, updated: 1, unchanged: 2 },
      errors: ['Linha 4: [uf_missing] UF ausente — Cidade Fictícia'],
      pendencias: { avisos: ['Linha 7: coluna grupos ignorada'] },
    });
  });

  test('validação sem avisos não cria Pendências vazias', () => {
    expect(validacaoDoImport({ ...RESULTADO, warnings: [] })).not.toHaveProperty('pendencias');
  });

  test('aplicação: as contagens do que foi gravado', () => {
    expect(aplicacaoDoImport(RESULTADO)).toEqual({ stats: { created: 3, updated: 1, unchanged: 2 } });
  });

  test('da resposta real do backend (municipios_import): o nome do município na pendência e rejeitada fora de Inalterados', () => {
    // Dry-run de um CSV com uma linha boa, uma sem UF e uma em branco (formato de services/municipios_import.py).
    const resposta = {
      stats: { created: 1, updated: 0, unchanged: 0, skipped: { nome_missing: 1, uf_missing: 1, other: 0 } },
      pendencias: {
        nome_missing: [{ linha: 3, erro: 'Nome do municipio ausente' }],
        uf_missing: [{ linha: 2, erro: 'UF ausente', municipio: 'Cidade Ficticia Dois' }],
        outros: [],
      },
      dry_run: true,
      file: '/tmp/municipios.csv',
    };

    expect(validacaoDoImport(__testing.normalizeImportResponse(resposta))).toEqual({
      stats: { created: 1, updated: 0, unchanged: 0 },
      errors: ['Linha 3: [nome_missing] Nome do municipio ausente', 'Linha 2: [uf_missing] UF ausente — Cidade Ficticia Dois'],
    });
  });
});
