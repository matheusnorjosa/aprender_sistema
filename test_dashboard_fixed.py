#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste corrigido com Playwright - Dashboard Executivo
"""

import os
import django
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

async def test_dashboard():
    print("INICIANDO TESTES CORRIGIDOS - DASHBOARD EXECUTIVO")
    print("="*80)
    
    async with async_playwright() as p:
        # Lançar navegador
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(15000)
        
        try:
            print("\n1. TESTANDO LOGIN E DASHBOARD COM ADMIN")
            print("-" * 50)
            
            # Ir para página de login
            await page.goto("http://localhost:8000/login/")
            await page.wait_for_load_state('networkidle')
            
            # Aguardar formulário aparecer
            await page.wait_for_selector('input[name="username"]', timeout=10000)
            await page.wait_for_selector('input[name="password"]', timeout=10000)
            
            # Preencher formulário
            await page.fill('input[name="username"]', 'admin')
            await page.fill('input[name="password"]', 'admin123')
            
            print("Credenciais preenchidas")
            
            # Submit com Enter ou clique
            await page.press('input[name="password"]', 'Enter')
            
            # Aguardar redirecionamento após login
            try:
                await page.wait_for_url("**/", timeout=10000)
                print("Login realizado com sucesso!")
            except:
                # Se não redirecionou, pode ter dado erro
                current_url = page.url
                print(f"URL atual após login: {current_url}")
                
                # Screenshot da tela de login
                await page.screenshot(path="login_error.png", full_page=True)
                print("Screenshot do login salva: login_error.png")
                
                # Verificar se há mensagens de erro
                error_msgs = await page.locator('.alert, .error, .messages').all_text_contents()
                if error_msgs:
                    print(f"Mensagens de erro: {error_msgs}")
            
            # Tentar ir para dashboard de qualquer forma
            print("\n2. ACESSANDO DASHBOARD")
            await page.goto("http://localhost:8000/diretoria/dashboard/")
            
            # Screenshot após ir para dashboard
            timestamp = datetime.now().strftime("%H%M%S")
            await page.screenshot(path=f"dashboard_attempt_{timestamp}.png", full_page=True)
            print(f"Screenshot dashboard: dashboard_attempt_{timestamp}.png")
            
            # Verificar se ainda está na página de login
            current_url = page.url
            print(f"URL atual: {current_url}")
            
            if "login" in current_url:
                print("AINDA NA TELA DE LOGIN - Problema de autenticacao!")
                
                # Vamos tentar login direto via JavaScript
                print("Tentando login alternativo via JavaScript...")
                
                await page.goto("http://localhost:8000/login/")
                await page.wait_for_selector('input[name="username"]')
                
                # Obter token CSRF
                csrf_token = await page.get_attribute('input[name="csrfmiddlewaretoken"]', 'value')
                print(f"CSRF Token obtido: {csrf_token[:10]}...")
                
                # Tentar submit via JavaScript
                await page.evaluate(f"""
                    document.querySelector('input[name="username"]').value = 'admin';
                    document.querySelector('input[name="password"]').value = 'admin123';
                    document.querySelector('form').submit();
                """)
                
                await page.wait_for_timeout(3000)
                final_url = page.url
                print(f"URL final após JS: {final_url}")
                
            else:
                print("SUCESSO! Dashboard carregado!")
                
                # Aguardar elementos do dashboard
                await page.wait_for_timeout(5000)
                
                # Análise do dashboard
                analysis = await page.evaluate("""
                    () => {
                        // Verificar Chart.js
                        const chartAvailable = typeof Chart !== 'undefined';
                        
                        // Contar elementos
                        const statCards = document.querySelectorAll('.stat-card').length;
                        const chartCards = document.querySelectorAll('.chart-card').length;
                        const activeCharts = document.querySelectorAll('canvas.active').length;
                        const fallbacks = document.querySelectorAll('.chart-fallback:not(.hidden)').length;
                        
                        // Status
                        const statusEl = document.getElementById('statusIndicator');
                        const status = statusEl ? statusEl.textContent : 'Não encontrado';
                        
                        // Title
                        const title = document.title;
                        
                        return {
                            chartAvailable,
                            statCards,
                            chartCards,
                            activeCharts,
                            fallbacks,
                            status,
                            title,
                            totalDisplays: activeCharts + fallbacks
                        };
                    }
                """)
                
                print("\nRESULTADO DO DASHBOARD:")
                print(f"  Titulo: {analysis['title']}")
                print(f"  Chart.js disponivel: {analysis['chartAvailable']}")
                print(f"  Cards estatisticas: {analysis['statCards']}")
                print(f"  Cards graficos: {analysis['chartCards']}")
                print(f"  Graficos ativos: {analysis['activeCharts']}/6")
                print(f"  Fallbacks visiveis: {analysis['fallbacks']}/6")
                print(f"  Status: {analysis['status']}")
                print(f"  Total displays: {analysis['totalDisplays']}/6")
                
                # Screenshot final
                await page.screenshot(path=f"dashboard_success_{timestamp}.png", full_page=True)
                print(f"Screenshot final: dashboard_success_{timestamp}.png")
                
                # Conclusão
                if analysis['activeCharts'] > 0:
                    print("\nSUCESSO COMPLETO! Chart.js funcionando com graficos interativos!")
                elif analysis['fallbacks'] > 0:
                    print("\nSUCESSO PARCIAL! Fallbacks visiveis, dashboard funcional!")
                elif analysis['statCards'] > 0:
                    print("\nPROBLEMA PARCIAL! Dashboard carrega mas graficos nao aparecem")
                else:
                    print("\nPROBLEMA GRAVE! Dashboard nao carregou corretamente")
        
        except Exception as e:
            print(f"ERRO geral: {e}")
            await page.screenshot(path="error_geral.png", full_page=True)
        
        finally:
            await browser.close()
    
    print("\nTESTES FINALIZADOS!")

if __name__ == "__main__":
    asyncio.run(test_dashboard())