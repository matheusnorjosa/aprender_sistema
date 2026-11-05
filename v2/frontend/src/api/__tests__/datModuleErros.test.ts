/**
 * Mensagens de erro do módulo DAT (alinhamento das telas, 05/11/2026; P#25 · B#33 · B#40).
 *
 * O cliente do módulo trocava todo 403 por "Acesso restrito ao setor DAT." (inclusive a sessão
 * expirada e o Controle, que usa a tela) e todo 404 por "Registro nao encontrado.", apagando a
 * mensagem do servidor; o export falhava com "Export failed: HTTP <n>".
 *
 * Agora: a mensagem do servidor vence; o mapa só cobre a resposta sem mensagem, sem nomear setor.
 */
import { describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

import { deleteCompra, getAcao, exportDATRegistros } from '../datModule';
import type { ErroHttp } from '../config';

describe('módulo DAT: mensagens de erro', () => {
  test('403 com mensagem do servidor: a mensagem do servidor aparece', async () => {
    server.use(
      http.delete(apiUrl('/dat/compras-materiais/5/'), () =>
        HttpResponse.json({ detail: 'Você não tem permissão para executar essa ação.' }, { status: 403 }),
      ),
    );

    await expect(deleteCompra(5)).rejects.toThrow('Você não tem permissão para executar essa ação.');
  });

  test('403 sem mensagem: reserva sem nomear setor, mantendo o status', async () => {
    server.use(http.delete(apiUrl('/dat/compras-materiais/5/'), () => HttpResponse.json({}, { status: 403 })));

    const erro = (await deleteCompra(5).catch((e: unknown) => e)) as ErroHttp;

    expect(erro.message).toBe('Você não tem permissão para esta ação.');
    expect(erro.status).toBe(403);
  });

  test('404 sem mensagem: "Registro não encontrado." (com acento)', async () => {
    server.use(http.get(apiUrl('/dat/acoes-ciclo/9/'), () => new HttpResponse('<html>', { status: 404 })));

    await expect(getAcao(9)).rejects.toThrow('Registro não encontrado.');
  });

  test('export que falha: mensagem em pt-BR', async () => {
    server.use(http.get(apiUrl('/dat/registros/export/'), () => HttpResponse.json({}, { status: 500 })));

    await expect(exportDATRegistros()).rejects.toThrow('Não foi possível exportar o arquivo (erro 500).');
  });
});
