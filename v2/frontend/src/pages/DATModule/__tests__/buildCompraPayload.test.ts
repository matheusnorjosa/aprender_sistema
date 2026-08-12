import { describe, it, expect } from 'vitest';
import dayjs from 'dayjs';

import { buildCompraPayload } from '../ComprasPage';

/**
 * M15-10: o form de Nova Compra enviava `uf` (inexistente no serializer) e `status_uso`
 * (read-only, recalculado no backend — enviar 'esgotado' gravava 'em_uso'), e nunca
 * mandava `valor_unitario` de forma confiável. Estas asserções travam o contrato do payload.
 */
describe('buildCompraPayload (M15-10)', () => {
  const base = { projeto: 1, produto: 2, municipio: 3, quantidade: 10, uf: 'CE' };

  it('não envia uf (o municipio já carrega a UF)', () => {
    expect(buildCompraPayload({ ...base })).not.toHaveProperty('uf');
  });

  it('não envia status_uso (read-only, recalculado no backend)', () => {
    expect(buildCompraPayload({ ...base, status_uso: 'esgotado' })).not.toHaveProperty('status_uso');
  });

  it('envia valor_unitario (destrava o dashboard financeiro)', () => {
    expect(buildCompraPayload({ ...base, valor_unitario: 12.5 }).valor_unitario).toBe(12.5);
  });

  it('formata data_compra para YYYY-MM-DD (nunca datetime ISO)', () => {
    const p = buildCompraPayload({ ...base, data_compra: dayjs('2026-03-10') });
    expect(p.data_compra).toBe('2026-03-10');
    expect(String(p.data_compra)).not.toMatch(/T\d{2}:/);
  });

  it('#1637: nao envia procurement (do Controle) nem codigo_produto (derivado do Produto)', () => {
    const p = buildCompraPayload({
      ...base,
      codigo_produto: 'KIT-001',
      fornecedor: 'Editora X',
      numero_nota_fiscal: 'NF-123',
      data_entrega: dayjs('2026-04-01'),
    });
    expect(p).not.toHaveProperty('codigo_produto');
    expect(p).not.toHaveProperty('fornecedor');
    expect(p).not.toHaveProperty('numero_nota_fiscal');
    expect(p).not.toHaveProperty('data_entrega');
  });

  it('preserva os demais campos (projeto, produto, municipio, quantidade)', () => {
    const p = buildCompraPayload({ ...base });
    expect(p.projeto).toBe(1);
    expect(p.produto).toBe(2);
    expect(p.municipio).toBe(3);
    expect(p.quantidade).toBe(10);
  });
});
