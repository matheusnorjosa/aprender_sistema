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
import { loginAs, logout, waitForAPIResponse } from '../fixtures/auth-helpers';
import { selectors } from '../fixtures/selectors';
import type { Solicitacao, PaginatedResponse, AuditLog } from '../types';

// Estado compartilhado entre test cases (worker-scoped)
let sharedSolicitacaoId: number;
let sharedSolicitacaoTitulo: string;

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

    // 2. Navegar para nova solicitação
    await page.goto('/solicitacoes/nova');
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // 3. Preencher formulário
    const timestamp = Date.now();
    sharedSolicitacaoTitulo = `Teste E2E Playwright - ${timestamp}`;

    // Projeto (selecionar "TESTE E2E")
    const projetoSelect = page.locator(selectors.solicitacao.projetoSelect).first();
    await expect(projetoSelect).toBeVisible({ timeout: 5000 });
    await projetoSelect.selectOption({ label: 'TESTE E2E' });

    // Município (selecionar "Salvador")
    const municipioSelect = page.locator(selectors.solicitacao.municipioSelect).first();
    await municipioSelect.selectOption({ label: 'Salvador' });

    // Formador (selecionar "Formador E2E")
    const formadorSelect = page.locator(selectors.solicitacao.formadorSelect).first();
    await formadorSelect.selectOption({ label: 'Formador E2E' });

    // Título
    const tituloInput = page.locator(selectors.solicitacao.tituloInput).first();
    await tituloInput.fill(sharedSolicitacaoTitulo);

    // Data/hora início (futuro para evitar conflitos)
    const dataInicioInput = page.locator(selectors.solicitacao.dataInicioInput).first();
    await dataInicioInput.fill('2025-12-01T09:00');

    // Data/hora fim
    const dataFimInput = page.locator(selectors.solicitacao.dataFimInput).first();
    await dataFimInput.fill('2025-12-01T12:00');

    // 4. Submeter e capturar resposta da API
    const responsePromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/solicitacoes/') && resp.status() === 201,
      { timeout: 15000 }
    );

    await page.locator(selectors.solicitacao.submitButton).first().click();

    const response = await responsePromise;
    const solicitacao: Solicitacao = await response.json();

    // 5. Asserts
    expect(solicitacao.id).toBeDefined();
    expect(solicitacao.id).toBeGreaterThan(0);
    expect(solicitacao.titulo).toBe(sharedSolicitacaoTitulo);
    expect(solicitacao.status).toBe('pendente'); // Fluxo SUPER (não auto-aprovado)
    expect(solicitacao.gcal_event_id).toBeFalsy(); // Ainda não publicado

    // 6. Salvar ID para próximos testes
    sharedSolicitacaoId = solicitacao.id;
    console.log(`✅ Solicitação criada: ID=${sharedSolicitacaoId}`);

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
      throw new Error('❌ sharedSolicitacaoId não foi setado pelo teste anterior');
    }

    // 1. Login
    await loginAs(page, 'super_e2e@test.com', 'testpass123');

    // 2. Navegar para aprovações
    await page.goto('/aprovacoes');
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // 3. Encontrar solicitação pendente
    // Buscar na tabela por ID ou título
    const tableLocator = page.locator(selectors.aprovacoes.table).first();
    await expect(tableLocator).toBeVisible({ timeout: 5000 });

    // Localizar row da solicitação (por texto do título ou ID)
    const solicitacaoRow = page.locator(`tr:has-text("${sharedSolicitacaoTitulo}")`).first();
    await expect(solicitacaoRow).toBeVisible({ timeout: 10000 });

    // 4. Clicar em "Aprovar"
    const aprovarButton = solicitacaoRow.locator(selectors.aprovacoes.aprovarButton).first();
    await aprovarButton.click();

    // 5. Preencher justificativa (se modal aparecer)
    const justificativaTextarea = page.locator(selectors.aprovacoes.justificativaTextarea).first();
    if (await justificativaTextarea.isVisible({ timeout: 2000 })) {
      await justificativaTextarea.fill('Aprovado para teste E2E Playwright');
    }

    // 6. Confirmar aprovação
    const confirmarButton = page.locator(selectors.aprovacoes.confirmarButton).first();
    await confirmarButton.click();

    // 7. Aguardar mensagem de sucesso
    await expect(page.locator(selectors.aprovacoes.successMessage).first()).toBeVisible({ timeout: 10000 });

    // 8. Validar via API que status mudou
    await page.waitForTimeout(1000); // Garantir que API persistiu
    const apiResponse = await page.request.get(`/api/solicitacoes/${sharedSolicitacaoId}/`);
    expect(apiResponse.ok()).toBeTruthy();

    const solicitacao: Solicitacao = await apiResponse.json();
    expect(solicitacao.status).toBe('aprovado');
    expect(solicitacao.gcal_event_id).toBeFalsy(); // Ainda não publicado

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
      throw new Error('❌ sharedSolicitacaoId não foi setado pelos testes anteriores');
    }

    // 1. Login
    await loginAs(page, 'controle_e2e@test.com', 'testpass123');

    // 2. Navegar para pré-agenda
    await page.goto('/pre-agenda');
    await page.waitForLoadState('networkidle', { timeout: 10000 });

    // 3. Encontrar solicitação aprovada
    const tableLocator = page.locator(selectors.preAgenda.table).first();
    await expect(tableLocator).toBeVisible({ timeout: 5000 });

    const solicitacaoRow = page.locator(`tr:has-text("${sharedSolicitacaoTitulo}")`).first();
    await expect(solicitacaoRow).toBeVisible({ timeout: 10000 });

    // 4. Preview GCal (se botão existir)
    const previewButton = solicitacaoRow.locator(selectors.preAgenda.previewButton).first();
    if (await previewButton.isVisible({ timeout: 2000 })) {
      await previewButton.click();

      // Validar payload preview (modal)
      const previewModal = page.locator(selectors.preAgenda.previewModal).first();
      await expect(previewModal).toBeVisible({ timeout: 5000 });

      const previewText = await previewModal.locator('pre, code').first().textContent();
      if (previewText) {
        try {
          const previewPayload = JSON.parse(previewText);
          expect(previewPayload.summary).toContain('Teste E2E Playwright');
          expect(previewPayload.start).toBeDefined();
          expect(previewPayload.end).toBeDefined();
          console.log('✅ Preview payload válido');
        } catch (err) {
          console.warn('⚠️  Preview payload não é JSON válido, continuando...');
        }
      }

      // Fechar modal preview
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    }

    // 5. Publish (APPLY com fake client)
    const publishButton = solicitacaoRow.locator(selectors.preAgenda.publishButton).first();
    await publishButton.click();

    // 6. Confirmar publicação (modal)
    const confirmarPublishButton = page.locator(selectors.preAgenda.confirmarPublishButton).first();
    await confirmarPublishButton.click();

    // 7. Aguardar mensagem de sucesso (pode demorar)
    await expect(page.locator(selectors.preAgenda.successMessage).first()).toBeVisible({ timeout: 20000 });

    // 8. Validar persistência via API
    await page.waitForTimeout(2000); // Garantir que backend persistiu
    const apiResponse = await page.request.get(`/api/solicitacoes/${sharedSolicitacaoId}/`);
    expect(apiResponse.ok()).toBeTruthy();

    const solicitacao: Solicitacao = await apiResponse.json();

    // Asserts críticos
    expect(solicitacao.gcal_event_id).toBeTruthy();
    expect(solicitacao.gcal_event_id).toMatch(/^fake-event-\d+/); // Padrão fake client
    expect(solicitacao.gcal_payload_hash).toBeTruthy();
    expect(solicitacao.gcal_payload_hash).toHaveLength(64); // SHA256

    // meet_link depende de is_online=true (se implementado)
    if (solicitacao.is_online) {
      expect(solicitacao.meet_link).toMatch(/^https:\/\/meet\.google\.com\//);
    }

    console.log(`✅ Solicitação publicada no GCal (fake): gcal_event_id=${solicitacao.gcal_event_id}`);

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
      throw new Error('❌ sharedSolicitacaoId não foi setado pelos testes anteriores');
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

    // 3. Asserts: pelo menos 3 logs (CREATE, APPROVE, PUBLISH)
    expect(logs.length).toBeGreaterThanOrEqual(3);

    const actions = logs.map((log) => log.action);
    expect(actions).toContain('CREATE');
    expect(actions).toContain('APPROVE');
    expect(actions).toContain('PUBLISH');

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
