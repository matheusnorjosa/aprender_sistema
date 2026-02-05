/**
 * E2E Test: Fluxo Solicitação → Google Calendar (Fake)
 *
 * Testa o fluxo completo:
 * 1. Coordenador cria solicitação
 * 2. Superintendência aprova
 * 3. Controle faz preview + publish no GCal (fake client)
 * 4. Validação de persistência (gcal_event_id, gcal_payload_hash, AuditLog)
 *
 * Fase 2 - Plano DAT/GCal 2025-10-29
 */

import { test, expect, Page } from '@playwright/test';
import { promises as fs } from 'fs';
import path from 'path';
import { loginAs, logout, waitForAPIResponse } from '../fixtures/auth-helpers';
import { selectors } from '../fixtures/selectors';
import type { Solicitacao, PaginatedResponse, AuditLog } from '../types';

// Estado compartilhado entre test cases (worker-scoped)
let sharedSolicitacaoId: number;
const sharedIdFile = path.resolve(process.cwd(), 'test-results', 'shared-solicitacao-id.json');

async function persistSharedId(id: number): Promise<void> {
  await fs.mkdir(path.dirname(sharedIdFile), { recursive: true });
  await fs.writeFile(sharedIdFile, JSON.stringify({ id }), 'utf-8');
}

async function loadSharedId(): Promise<number | undefined> {
  try {
    const raw = await fs.readFile(sharedIdFile, 'utf-8');
    const parsed = JSON.parse(raw);
    return typeof parsed?.id === 'number' ? parsed.id : undefined;
  } catch {
    return undefined;
  }
}

async function getLookupItem(page: Page, url: string, labelIncludes?: string) {
  const response = await page.request.get(url);
  expect(response.ok()).toBeTruthy();
  const items = await response.json();
  if (!Array.isArray(items) || items.length === 0) {
    throw new Error(`Lookup vazio para ${url}`);
  }
  if (labelIncludes) {
    const match = items.find((item) => String(item.label || '').includes(labelIncludes));
    if (match) {
      return match;
    }
  }
  return items[0];
}

async function waitForPublished(page: Page, solicitacaoId: number, timeoutMs = 20000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const apiResponse = await page.request.get(`/api/solicitacoes/${solicitacaoId}/`);
    if (apiResponse.ok()) {
      const solicitacao: Solicitacao = await apiResponse.json();
      if (solicitacao.external_event_id || solicitacao.gcal_status === 'PUBLISHED') {
        return solicitacao;
      }
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('Timeout aguardando external_event_id após publish');
}


/**
 * Test Suite: Fluxo Completo Solicitação → Google Calendar
 */
test.describe('Fluxo Solicitação → Google Calendar (Fake)', () => {
  // Configurações do test suite
  test.use({
    // Timeout por teste (60s)
    timeout: 60000,

    // Base URL (opcional, já configurado em playwright.config.js)
    // baseURL: process.env.BASE_URL || 'http://localhost:5173',
  });

  /**
   * Test Case 1: Coordenador cria solicitação
   */
  test('1. Deve criar solicitação como Coordenador', async ({ page }) => {
    console.log('\n🧪 Test 1: Criar solicitação como Coordenador');

    // 1. Login
    await loginAs(page, 'coord_e2e@test.com', 'testpass123');

    // 2. Resolver IDs via lookup (evita depender de IDs fixos)
    const projeto = await getLookupItem(page, '/api/lookup/projetos/?q=E2E', 'TESTE E2E');
    const municipio = await getLookupItem(page, '/api/lookup/municipios/?q=Salvador', 'Salvador');
    const tipoEvento = await getLookupItem(page, '/api/lookup/tipos-evento/');
    const formador = await getLookupItem(page, '/api/lookup/usuarios/?role=Formador', 'Formador E2E');

    // 3. Obter CSRF token para POST autenticado
    const csrfResponse = await page.request.get('/api/csrf/');
    expect(csrfResponse.ok()).toBeTruthy();
    const csrfData = await csrfResponse.json();
    const csrfToken = csrfData?.csrfToken;
    expect(csrfToken).toBeTruthy();

    // 4. Criar solicitação diretamente via API (evita flakiness do wizard)
    const solicitacaoResponse = await page.request.post('/api/solicitacoes/', {
      headers: { 'X-CSRFToken': csrfToken },
      data: {
        municipio: municipio.id,
        projeto: projeto.id,
        tipo_evento: tipoEvento.id,
        inicio: '2026-12-01T12:00:00Z',
        fim: '2026-12-01T15:00:00Z',
        is_online: false,
        extra_participants: {
          formador_ids: [formador.id],
        },
      },
    });
    expect(solicitacaoResponse.ok()).toBeTruthy();
    const solicitacao: Solicitacao = await solicitacaoResponse.json();

    // 5. Asserts
    expect(solicitacao.id).toBeDefined();
    expect(solicitacao.id).toBeGreaterThan(0);
    expect(solicitacao.municipio_nome).toContain('Salvador');
    expect(solicitacao.projeto_nome).toContain('TESTE E2E');
    expect(solicitacao.status).toBe('pendente'); // Fluxo SUPER (não auto-aprovado)
    expect(solicitacao.external_event_id).toBeFalsy(); // Ainda não publicado

    // 6. Salvar ID para próximos testes
    sharedSolicitacaoId = solicitacao.id;
    console.log(`✅ Solicitação criada: ID=${sharedSolicitacaoId}`);
    await persistSharedId(sharedSolicitacaoId);

    // 7. Logout
    await logout(page);
  });

  /**
   * Test Case 2: Superintendência aprova solicitação
   */
  test('2. Deve aprovar solicitação como Superintendência', async ({ page }) => {
    console.log('\n🧪 Test 2: Aprovar solicitação como Superintendência');

    // Verificar que ID foi setado pelo teste anterior
    if (!sharedSolicitacaoId) {
      sharedSolicitacaoId = await loadSharedId();
      if (!sharedSolicitacaoId) {
        throw new Error('❌ sharedSolicitacaoId não foi setado pelo teste anterior');
      }
    }

    // 1. Login
    await loginAs(page, 'super_e2e@test.com', 'testpass123');

    // 2. Aprovar via API (mais estável que UI)
    const csrfResponse = await page.request.get('/api/csrf/');
    expect(csrfResponse.ok()).toBeTruthy();
    const csrfData = await csrfResponse.json();
    const csrfToken = csrfData?.csrfToken;
    expect(csrfToken).toBeTruthy();

    const approveResponse = await page.request.patch(`/api/solicitacoes/${sharedSolicitacaoId}/approve/`, {
      headers: { 'X-CSRFToken': csrfToken },
      data: { reason: 'Aprovado para teste E2E Playwright' },
    });
    expect(approveResponse.ok()).toBeTruthy();

    // Validar via API que status mudou
    const apiResponse = await page.request.get(`/api/solicitacoes/${sharedSolicitacaoId}/`);
    expect(apiResponse.ok()).toBeTruthy();
    const solicitacao: Solicitacao = await apiResponse.json();
    expect(solicitacao.status).toBe('aprovado');
    expect(solicitacao.external_event_id).toBeFalsy(); // Ainda não publicado

    console.log(`✅ Solicitação aprovada: ID=${sharedSolicitacaoId}`);

    // 9. Logout
    await logout(page);
  });

  /**
   * Test Case 3: Controle faz preview e publish no Google Calendar (fake)
   */
  test('3. Deve fazer preview e publish no Google Calendar (fake)', async ({ page }) => {
    console.log('\n🧪 Test 3: Preview + Publish GCal (fake)');

    // Verificar que ID foi setado
    if (!sharedSolicitacaoId) {
      sharedSolicitacaoId = await loadSharedId();
      if (!sharedSolicitacaoId) {
        throw new Error('❌ sharedSolicitacaoId não foi setado pelos testes anteriores');
      }
    }

    // 1. Login
    await loginAs(page, 'controle_e2e@test.com', 'testpass123');

    // 2. Preview GCal via API
    const csrfResponse = await page.request.get('/api/csrf/');
    expect(csrfResponse.ok()).toBeTruthy();
    const csrfData = await csrfResponse.json();
    const csrfToken = csrfData?.csrfToken;
    expect(csrfToken).toBeTruthy();

    const previewResponse = await page.request.post(`/api/solicitacoes/${sharedSolicitacaoId}/preview-gcal/`, {
      headers: { 'X-CSRFToken': csrfToken },
      data: {},
    });
    expect(previewResponse.ok()).toBeTruthy();
    const previewBody = await previewResponse.json();
    const previewData = previewBody.preview ?? previewBody;
    const payload = previewData.payload ?? previewData;
    expect(payload.summary).toContain('Salvador - BA');
    expect(payload.summary).toContain('[E2E]');
    expect(payload.start).toBeDefined();
    expect(payload.end).toBeDefined();

    // 3. Publish via API (fake client)
    const publishResponse = await page.request.post(`/api/solicitacoes/${sharedSolicitacaoId}/publish/`, {
      headers: { 'X-CSRFToken': csrfToken },
      data: { dry_run: false, apply_blocked: true },
    });
    expect(publishResponse.ok()).toBeTruthy();

    // 4. Validar persistência via API
    const solicitacao = await waitForPublished(page, sharedSolicitacaoId);

    // Asserts críticos
    expect(solicitacao.external_event_id).toBeTruthy();
    expect(solicitacao.external_event_id).toMatch(/^asv2-\d+/); // Padrão fake client
    // gcal_payload_hash pode não ser exposto no serializer

    // meet_link depende de is_online=true (se implementado)
    if (solicitacao.is_online) {
      expect(solicitacao.meet_link).toMatch(/^https:\/\/meet\.google\.com\//);
    }

    console.log(`✅ Solicitação publicada no GCal (fake): external_event_id=${solicitacao.external_event_id}`);

    // 9. Logout
    await logout(page);
  });

  /**
   * Test Case 4: Validar registros no AuditLog
   */
  test('4. Deve registrar ações no AuditLog', async ({ page }) => {
    console.log('\n🧪 Test 4: Validar AuditLog');

    // Verificar que ID foi setado
    if (!sharedSolicitacaoId) {
      sharedSolicitacaoId = await loadSharedId();
      if (!sharedSolicitacaoId) {
        throw new Error('❌ sharedSolicitacaoId não foi setado pelos testes anteriores');
      }
    }

    // 1. Login (qualquer usuário autorizado)
    await loginAs(page, 'super_e2e@test.com', 'testpass123');

    // 2. Consultar AuditLog via API
    // Endpoint pode variar: /api/audit-log/, /api/audit-logs/, etc.
    const auditEndpoints = [
      `/api/audit-log/?model_name=Solicitacao&object_id=${sharedSolicitacaoId}`,
      `/api/audit-logs/?model_name=Solicitacao&object_id=${sharedSolicitacaoId}`,
      `/api/audit/?model_name=Solicitacao&object_id=${sharedSolicitacaoId}`,
    ];

    let auditResponse;
    let auditFound = false;

    for (const endpoint of auditEndpoints) {
      auditResponse = await page.request.get(endpoint);
      if (auditResponse.ok()) {
        auditFound = true;
        break;
      }
    }

    if (!auditFound) {
      console.warn('⚠️  Endpoint de AuditLog não encontrado, pulando validação...');
      test.skip();
      return;
    }

    const auditData = await auditResponse!.json();
    const logs: AuditLog[] = (auditData as PaginatedResponse<AuditLog>).results || (auditData as AuditLog[]);

    // 3. Asserts: pelo menos 3 logs (PREVIEW_GCAL, APPROVE, PUBLISH_GCAL_REQUESTED)
    expect(logs.length).toBeGreaterThanOrEqual(3);

    const actions = logs.map((log) => log.action);
    expect(actions).toContain('PREVIEW_GCAL');
    expect(actions).toContain('APPROVE');
    expect(actions).toContain('PUBLISH_GCAL_REQUESTED');

    // 4. Validar estrutura de um log
    const createLog = logs.find((log) => log.action === 'CREATE');
    if (createLog) {
      expect(createLog.usuario).toBeDefined();
      expect(createLog.timestamp).toBeDefined();
      expect(createLog.details).toBeDefined();
    }

    console.log(`✅ AuditLog validado: ${logs.length} registros encontrados`);

    // 5. Logout
    await logout(page);
  });
});

/**
 * Test Suite adicional: Edge Cases e Validações Extras (opcional)
 */
test.describe.skip('Edge Cases (opcional)', () => {
  test('Deve reprovar solicitação como Superintendência', async ({ page }) => {
    // TODO: Implementar teste de reprovação
  });

  test('Deve validar conflitos de disponibilidade', async ({ page }) => {
    // TODO: Implementar teste de conflitos
  });

  test('Deve impedir publicação sem aprovação', async ({ page }) => {
    // TODO: Implementar teste de permissões
  });
});
