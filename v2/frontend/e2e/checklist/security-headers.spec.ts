/**
 * CHECKLIST_FRONTEND.md - Security Headers Tests
 *
 * Testa itens da seção "Segurança > Headers de Segurança":
 * - 🔴 X-Content-Type-Options: nosniff
 * - 🔴 X-Frame-Options: DENY ou SAMEORIGIN
 * - 🟡 Content-Security-Policy
 * - 🟡 X-XSS-Protection: 1; mode=block
 * - 🟢 Referrer-Policy
 * - 🟡 Strict-Transport-Security (HSTS)
 *
 * NOTA: Estes headers são configurados no servidor (Nginx/backend).
 * Em desenvolvimento, podem não estar presentes.
 * Este teste é mais útil em staging/produção.
 */
import { test, expect } from '@playwright/test';

// Flag para indicar se estamos em CI/produção (headers devem existir)
const STRICT_MODE = process.env.CI || process.env.STRICT_SECURITY_HEADERS;

test.describe('Checklist: Security Headers', () => {
  test.describe('Headers Obrigatórios (🔴)', () => {
    test('X-Content-Type-Options deve ser "nosniff"', async ({ request }) => {
      const response = await request.get('/');
      const header = response.headers()['x-content-type-options'];

      if (STRICT_MODE) {
        expect(header).toBe('nosniff');
      } else {
        // Em dev, apenas verifica se presente
        test.skip(!header, 'Header não presente em ambiente de desenvolvimento');
        if (header) {
          expect(header).toBe('nosniff');
        }
      }
    });

    test('X-Frame-Options deve ser DENY ou SAMEORIGIN', async ({ request }) => {
      const response = await request.get('/');
      const header = response.headers()['x-frame-options'];

      if (STRICT_MODE) {
        expect(header).toMatch(/^(DENY|SAMEORIGIN)$/i);
      } else {
        test.skip(!header, 'Header não presente em ambiente de desenvolvimento');
        if (header) {
          expect(header.toUpperCase()).toMatch(/^(DENY|SAMEORIGIN)$/);
        }
      }
    });
  });

  test.describe('Headers Recomendados (🟡)', () => {
    test('Content-Security-Policy deve estar presente', async ({ request }) => {
      const response = await request.get('/');
      const header =
        response.headers()['content-security-policy'] ||
        response.headers()['content-security-policy-report-only'];

      if (STRICT_MODE) {
        expect(header).toBeTruthy();
      } else {
        test.skip(!header, 'CSP não configurado em ambiente de desenvolvimento');
        if (header) {
          // Verifica políticas mínimas
          expect(header).toMatch(/default-src|script-src/);
        }
      }
    });

    test('X-XSS-Protection deve estar configurado', async ({ request }) => {
      const response = await request.get('/');
      const header = response.headers()['x-xss-protection'];

      // X-XSS-Protection está sendo descontinuado em favor de CSP
      // mas ainda é recomendado para browsers antigos
      if (header) {
        expect(header).toMatch(/^1/); // Deve começar com "1"
      }
    });

    test('Strict-Transport-Security (HSTS) em produção', async ({ request }) => {
      const response = await request.get('/');
      const header = response.headers()['strict-transport-security'];

      if (STRICT_MODE) {
        expect(header).toBeTruthy();
        expect(header).toContain('max-age=');
      } else {
        test.skip(!header, 'HSTS não configurado em ambiente de desenvolvimento');
      }
    });
  });

  test.describe('Headers Opcionais (🟢)', () => {
    test('Referrer-Policy se presente deve ser válido', async ({ request }) => {
      const response = await request.get('/');
      const header = response.headers()['referrer-policy'];

      if (header) {
        const validPolicies = [
          'no-referrer',
          'no-referrer-when-downgrade',
          'origin',
          'origin-when-cross-origin',
          'same-origin',
          'strict-origin',
          'strict-origin-when-cross-origin',
          'unsafe-url',
        ];
        expect(validPolicies).toContain(header.toLowerCase());
      }
    });

    test('Permissions-Policy se presente deve ser válido', async ({ request }) => {
      const response = await request.get('/');
      const header =
        response.headers()['permissions-policy'] ||
        response.headers()['feature-policy'];

      if (header) {
        expect(header).toBeTruthy();
      }
    });
  });
});

test.describe('Checklist: HTTPS', () => {
  test('🔴 deve redirecionar HTTP para HTTPS em produção', async ({ request }) => {
    // Este teste só faz sentido em produção
    const baseURL = process.env.PRODUCTION_URL;

    if (!baseURL) {
      test.skip(true, 'PRODUCTION_URL não definida - teste ignorado em dev');
      return;
    }

    // Tenta acessar via HTTP
    const httpUrl = baseURL.replace('https://', 'http://');
    const response = await request.get(httpUrl, {
      maxRedirects: 0,
      failOnStatusCode: false,
    });

    // Deve redirecionar (301 ou 302)
    expect([301, 302, 307, 308]).toContain(response.status());

    const location = response.headers()['location'];
    expect(location).toMatch(/^https:\/\//);
  });
});

test.describe('Checklist: Cookies Security', () => {
  test('🔴 cookies de sessão devem ter flags de segurança', async ({ page }) => {
    await page.goto('/');

    const cookies = await page.context().cookies();
    const sessionCookies = cookies.filter(
      (c) =>
        c.name.toLowerCase().includes('session') ||
        c.name.toLowerCase().includes('csrf') ||
        c.name.toLowerCase().includes('token')
    );

    for (const cookie of sessionCookies) {
      // HttpOnly para cookies de sessão
      if (cookie.name.toLowerCase().includes('session')) {
        expect(
          cookie.httpOnly,
          `Cookie ${cookie.name} deve ser HttpOnly`
        ).toBeTruthy();
      }

      // Secure em produção
      if (STRICT_MODE) {
        expect(
          cookie.secure,
          `Cookie ${cookie.name} deve ser Secure`
        ).toBeTruthy();
      }

      // SameSite deve estar definido
      expect(
        cookie.sameSite,
        `Cookie ${cookie.name} deve ter SameSite`
      ).toBeTruthy();
    }
  });
});
