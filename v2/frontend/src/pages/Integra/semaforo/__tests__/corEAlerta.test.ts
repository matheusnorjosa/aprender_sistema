/**
 * Cores do Semáforo: as do documento de requisitos do Semáforo (tabela da seção 3 e painel da seção 7).
 * O documento usa os mesmos tons do ICA (vermelho #FBE6E5/#D9473B, amarelo #FDF4E3/#E5A21C, verde #2BA84A; o fundo
 * verde da tabela, #E9F6EC, difere do #E8F5EB do ICA em 1 ponto, sem diferença visível). Por isso o Semáforo usa as
 * cores do ICA, com o mesmo ajuste de contraste (`ica/__tests__/componentes.test.tsx`).
 */
import { describe, expect, test } from 'vitest';

import { COR_ESTRATO } from '../../ica/componentes/estilos';
import { COR_SEMAFORO } from '../componentes/corEAlerta';

describe('Semáforo — cores', () => {
  test('verde, amarelo e vermelho são os tons do documento, os mesmos do ICA', () => {
    expect(COR_SEMAFORO.vermelho).toEqual({ fundo: '#FBE6E5', texto: '#C0392B', forte: '#D9473B' });
    expect(COR_SEMAFORO.amarelo).toBe(COR_ESTRATO.atencao);
    expect(COR_SEMAFORO.verde).toBe(COR_ESTRATO.adequada);
  });
});
