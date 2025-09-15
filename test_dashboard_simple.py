#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples com Playwright - Dashboard Executivo (sem emojis)
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
    print("INICIANDO TESTES PLAYWRIGHT - DASHBOARD EXECUTIVO")
    print("="*80)
    
    async with async_playwright() as p:
        # Lançar navegador
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(10000)
        
        try:
            # Teste 1: Dashboard com admin
            print("\n1. TESTANDO DASHBOARD COM ADMIN")
            print("-" * 40)
            
            # Login
            await page.goto("http://localhost:8000/login/")
            await page.fill('input[name="username"]', 'admin')
            await page.fill('input[name="password"]', 'admin123')
            await page.click('button[type="submit"]')
            
            # Aguardar login
            await page.wait_for_url("**/", timeout=5000)
            print("Login admin realizado")
            
            # Ir para dashboard
            await page.goto("http://localhost:8000/diretoria/dashboard/")
            
            # Screenshot inicial
            timestamp = datetime.now().strftime("%H%M%S")
            await page.screenshot(path=f"dashboard_{timestamp}_admin_loading.png", full_page=True)
            print(f"Screenshot capturada: dashboard_{timestamp}_admin_loading.png")
            
            # Aguardar 5 segundos para carregamento
            await page.wait_for_timeout(5000)
            
            # Screenshot final
            await page.screenshot(path=f"dashboard_{timestamp}_admin_final.png", full_page=True)
            print(f"Screenshot capturada: dashboard_{timestamp}_admin_final.png")
            
            # Analisar página
            analysis = await page.evaluate("""
                () => {
                    // Verificar Chart.js
                    const chartAvailable = typeof Chart !== 'undefined';
                    
                    // Contar canvas ativos
                    const activeCharts = document.querySelectorAll('canvas.active').length;
                    
                    // Contar fallbacks visíveis
                    const visibleFallbacks = document.querySelectorAll('.chart-fallback:not(.hidden)').length;
                    
                    // Status indicator
                    const statusEl = document.getElementById('statusIndicator');
                    const status = statusEl ? statusEl.textContent : 'N/A';
                    
                    // Cards
                    const statCards = document.querySelectorAll('.stat-card').length;
                    const chartCards = document.querySelectorAll('.chart-card').length;
                    
                    return {
                        chartAvailable,
                        activeCharts,
                        visibleFallbacks,
                        status,
                        statCards,
                        chartCards,
                        totalDisplays: activeCharts + visibleFallbacks
                    };
                }
            """)
            
            print("RESULTADO ADMIN:")
            print(f"  Chart.js disponivel: {analysis['chartAvailable']}")
            print(f"  Graficos ativos: {analysis['activeCharts']}/6")
            print(f"  Fallbacks visiveis: {analysis['visibleFallbacks']}/6")
            print(f"  Status: {analysis['status']}")
            print(f"  Cards estatisticas: {analysis['statCards']}")
            print(f"  Cards graficos: {analysis['chartCards']}")
            print(f"  Total displays: {analysis['totalDisplays']}/6")
            
            # Teste 2: Dashboard com diretoria_teste
            print("\n2. TESTANDO DASHBOARD COM DIRETORIA_TESTE")
            print("-" * 40)
            
            # Logout e login
            await page.goto("http://localhost:8000/logout/")
            await page.goto("http://localhost:8000/login/")
            await page.fill('input[name="username"]', 'diretoria_teste')
            await page.fill('input[name="password"]', 'teste123')
            await page.click('button[type="submit"]')
            
            await page.wait_for_url("**/", timeout=5000)
            print("Login diretoria_teste realizado")
            
            # Dashboard
            await page.goto("http://localhost:8000/diretoria/dashboard/")
            
            # Screenshot
            timestamp2 = datetime.now().strftime("%H%M%S")
            await page.screenshot(path=f"dashboard_{timestamp2}_diretoria_loading.png", full_page=True)
            await page.wait_for_timeout(5000)
            await page.screenshot(path=f"dashboard_{timestamp2}_diretoria_final.png", full_page=True)
            print(f"Screenshots diretoria capturadas")
            
            # Análise diretoria
            analysis2 = await page.evaluate("""
                () => {
                    const chartAvailable = typeof Chart !== 'undefined';
                    const activeCharts = document.querySelectorAll('canvas.active').length;
                    const visibleFallbacks = document.querySelectorAll('.chart-fallback:not(.hidden)').length;
                    const statusEl = document.getElementById('statusIndicator');
                    const status = statusEl ? statusEl.textContent : 'N/A';
                    
                    return {
                        chartAvailable,
                        activeCharts,
                        visibleFallbacks,
                        status,
                        totalDisplays: activeCharts + visibleFallbacks
                    };
                }
            """)
            
            print("RESULTADO DIRETORIA:")
            print(f"  Chart.js disponivel: {analysis2['chartAvailable']}")
            print(f"  Graficos ativos: {analysis2['activeCharts']}/6")
            print(f"  Fallbacks visiveis: {analysis2['visibleFallbacks']}/6")
            print(f"  Status: {analysis2['status']}")
            print(f"  Total displays: {analysis2['totalDisplays']}/6")
            
            # Teste 3: Página standalone
            print("\n3. TESTANDO DASHBOARD STANDALONE")
            print("-" * 40)
            
            await page.goto("http://localhost:8000/diretoria/test/")
            
            timestamp3 = datetime.now().strftime("%H%M%S")
            await page.screenshot(path=f"dashboard_{timestamp3}_standalone_loading.png", full_page=True)
            await page.wait_for_timeout(5000)
            await page.screenshot(path=f"dashboard_{timestamp3}_standalone_final.png", full_page=True)
            print(f"Screenshots standalone capturadas")
            
            # Relatório final
            print("\n" + "="*80)
            print("RELATORIO FINAL")
            print("="*80)
            
            if analysis['activeCharts'] > 0 or analysis2['activeCharts'] > 0:
                print("SUCESSO! Chart.js esta funcionando!")
                print("Graficos interativos visiveis no dashboard!")
            elif analysis['visibleFallbacks'] > 0 or analysis2['visibleFallbacks'] > 0:
                print("FUNCIONAL! Fallbacks visiveis garantem dashboard funcional!")
                print("Chart.js pode ter problemas, mas interface funciona!")
            else:
                print("PROBLEMA! Nem graficos nem fallbacks estao aparecendo!")
            
            print(f"\nScreenshots geradas:")
            print(f"- dashboard_{timestamp}_admin_loading.png")
            print(f"- dashboard_{timestamp}_admin_final.png")
            print(f"- dashboard_{timestamp2}_diretoria_loading.png")
            print(f"- dashboard_{timestamp2}_diretoria_final.png")
            print(f"- dashboard_{timestamp3}_standalone_loading.png")
            print(f"- dashboard_{timestamp3}_standalone_final.png")
            
        except Exception as e:
            print(f"ERRO durante testes: {e}")
            await page.screenshot(path="dashboard_error.png", full_page=True)
        
        finally:
            await browser.close()
    
    print("\nTESTES FINALIZADOS!")

if __name__ == "__main__":
    asyncio.run(test_dashboard())