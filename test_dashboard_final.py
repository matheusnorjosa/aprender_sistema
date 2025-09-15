#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste FINAL com Playwright - Dashboard Executivo - Credenciais corretas
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
    print("TESTE FINAL - DASHBOARD EXECUTIVO COM CREDENCIAIS CORRETAS")
    print("="*80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(15000)
        
        try:
            print("\n1. FAZENDO LOGIN COM CPF CORRETO")
            print("-" * 50)
            
            # Login
            await page.goto("http://localhost:8000/login/")
            await page.wait_for_selector('input[name="username"]')
            
            # Usar CPF como username
            await page.fill('input[name="username"]', '04215498317')
            await page.fill('input[name="password"]', 'admin123')
            
            print("Credenciais preenchidas: 04215498317 / admin123")
            
            # Submit
            await page.press('input[name="password"]', 'Enter')
            
            # Aguardar redirecionamento
            await page.wait_for_timeout(3000)
            current_url = page.url
            print(f"URL após login: {current_url}")
            
            # Ir para dashboard
            print("\n2. ACESSANDO DASHBOARD")
            await page.goto("http://localhost:8000/diretoria/dashboard/")
            await page.wait_for_timeout(2000)
            
            current_url = page.url
            print(f"URL dashboard: {current_url}")
            
            timestamp = datetime.now().strftime("%H%M%S")
            
            if "login" in current_url:
                print("AINDA NA TELA DE LOGIN!")
                await page.screenshot(path=f"login_problem_{timestamp}.png", full_page=True)
            else:
                print("SUCESSO! Acessou o dashboard!")
                
                # Screenshot inicial
                await page.screenshot(path=f"dashboard_loading_{timestamp}.png", full_page=True)
                
                # Aguardar carregamento do dashboard
                print("\n3. AGUARDANDO CARREGAMENTO DO DASHBOARD")
                await page.wait_for_timeout(8000)  # 8 segundos para Chart.js tentar carregar
                
                # Screenshot final
                await page.screenshot(path=f"dashboard_final_{timestamp}.png", full_page=True)
                
                # Análise completa
                analysis = await page.evaluate("""
                    () => {
                        const results = {
                            title: document.title,
                            url: window.location.href,
                            chartJsAvailable: typeof Chart !== 'undefined',
                            chartJsVersion: typeof Chart !== 'undefined' ? (Chart.version || 'unknown') : null
                        };
                        
                        // Contar elementos
                        results.statCards = document.querySelectorAll('.stat-card').length;
                        results.chartCards = document.querySelectorAll('.chart-card').length;
                        
                        // Gráficos Chart.js
                        results.canvasElements = document.querySelectorAll('canvas').length;
                        results.activeCharts = document.querySelectorAll('canvas.active').length;
                        
                        // Fallbacks
                        results.fallbackElements = document.querySelectorAll('.chart-fallback').length;
                        results.visibleFallbacks = document.querySelectorAll('.chart-fallback:not(.hidden)').length;
                        
                        // Status indicator
                        const statusEl = document.getElementById('statusIndicator');
                        results.statusText = statusEl ? statusEl.textContent : 'Não encontrado';
                        results.statusVisible = statusEl ? !statusEl.style.display.includes('none') : false;
                        
                        // Total de displays funcionando
                        results.totalDisplays = results.activeCharts + results.visibleFallbacks;
                        
                        // Verificar conteúdo dos cards de estatísticas
                        const statNumbers = [];
                        document.querySelectorAll('.stat-number').forEach(el => {
                            statNumbers.push(el.textContent.trim());
                        });
                        results.statNumbers = statNumbers;
                        
                        // Verificar se há conteúdo nos fallbacks
                        results.fallbacksWithContent = 0;
                        document.querySelectorAll('.chart-fallback:not(.hidden)').forEach(fallback => {
                            if (fallback.textContent.trim().length > 50) {
                                results.fallbacksWithContent++;
                            }
                        });
                        
                        return results;
                    }
                """)
                
                print("\n" + "="*60)
                print("ANALISE COMPLETA DO DASHBOARD")
                print("="*60)
                print(f"Titulo da pagina: {analysis['title']}")
                print(f"URL: {analysis['url']}")
                print(f"Chart.js disponivel: {analysis['chartJsAvailable']}")
                if analysis['chartJsVersion']:
                    print(f"Chart.js versao: {analysis['chartJsVersion']}")
                
                print(f"\nELEMENTOS DA INTERFACE:")
                print(f"  Cards de estatisticas: {analysis['statCards']}/4")
                print(f"  Cards de graficos: {analysis['chartCards']}/6")
                print(f"  Numeros das estatisticas: {analysis['statNumbers']}")
                
                print(f"\nGRAFICOS CHART.JS:")
                print(f"  Canvas elements: {analysis['canvasElements']}")
                print(f"  Graficos ativos: {analysis['activeCharts']}/6")
                
                print(f"\nFALLBACKS VISUAIS:")
                print(f"  Elementos fallback: {analysis['fallbackElements']}")
                print(f"  Fallbacks visiveis: {analysis['visibleFallbacks']}/6")
                print(f"  Fallbacks com conteudo: {analysis['fallbacksWithContent']}/6")
                
                print(f"\nSTATUS DO SISTEMA:")
                print(f"  Indicador status: {analysis['statusText']}")
                print(f"  Indicador visivel: {analysis['statusVisible']}")
                print(f"  Total displays funcionando: {analysis['totalDisplays']}/6")
                
                # CONCLUSÃO
                print("\n" + "="*60)
                print("CONCLUSAO FINAL")
                print("="*60)
                
                if analysis['activeCharts'] >= 6:
                    print("SUCESSO COMPLETO! Todos os 6 graficos Chart.js estao funcionando!")
                    print("Dashboard com graficos interativos totalmente funcional!")
                elif analysis['activeCharts'] > 0:
                    print(f"SUCESSO PARCIAL! {analysis['activeCharts']}/6 graficos Chart.js funcionando!")
                    print(f"Restante com fallbacks: {analysis['visibleFallbacks']}/6")
                elif analysis['visibleFallbacks'] >= 6:
                    print("FUNCIONAL! Todos os 6 fallbacks visuais estao ativos!")
                    print("Dashboard totalmente funcional com displays alternativos ricos!")
                elif analysis['visibleFallbacks'] > 0:
                    print(f"PARCIALMENTE FUNCIONAL! {analysis['visibleFallbacks']}/6 displays funcionando!")
                elif analysis['statCards'] >= 4:
                    print("BASICAMENTE FUNCIONAL! Estatisticas carregaram, mas graficos nao!")
                else:
                    print("PROBLEMA GRAVE! Dashboard nao carregou corretamente!")
                
                print(f"\nScreenshots gerados:")
                print(f"- dashboard_loading_{timestamp}.png (carregando)")
                print(f"- dashboard_final_{timestamp}.png (resultado final)")
                
        except Exception as e:
            print(f"ERRO: {e}")
            await page.screenshot(path="error_final.png", full_page=True)
        
        finally:
            await browser.close()
    
    print("\nTESTE FINAL CONCLUIDO!")

if __name__ == "__main__":
    asyncio.run(test_dashboard())