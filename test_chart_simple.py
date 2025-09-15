#!/usr/bin/env python3
"""
Teste simples para verificar Chart.js funcionando
"""

import os
import django
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

async def test_chart_simple():
    print("TESTE SIMPLES - CHART.JS")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        page.set_default_timeout(30000)  # 30 segundos timeout
        
        try:
            print("\n1. LOGIN")
            await page.goto("http://localhost:8000/login/")
            await page.wait_for_selector('input[name="username"]')
            
            await page.fill('input[name="username"]', '04215498317')
            await page.fill('input[name="password"]', 'admin123')
            await page.press('input[name="password"]', 'Enter')
            
            print("Login realizado")
            
            print("\n2. DASHBOARD")
            await page.goto("http://localhost:8000/diretoria/dashboard/")
            
            # Aguardar muito tempo para Chart.js carregar
            print("Aguardando 15 segundos para Chart.js...")
            await page.wait_for_timeout(15000)
            
            # Verificar Chart.js
            chart_available = await page.evaluate("typeof Chart !== 'undefined'")
            print(f"Chart.js disponível: {chart_available}")
            
            if chart_available:
                version = await page.evaluate("Chart.version")
                print(f"Chart.js versão: {version}")
                
                # Contar gráficos ativos
                active_charts = await page.evaluate("""
                    document.querySelectorAll('canvas.active').length
                """)
                print(f"Gráficos Chart.js ativos: {active_charts}")
                
                if active_charts > 0:
                    print("✅ SUCESSO! Chart.js funcionando com gráficos!")
                else:
                    print("⚠️ Chart.js carregou mas gráficos não foram criados")
            else:
                print("❌ Chart.js não carregou")
            
            # Screenshot
            timestamp = datetime.now().strftime("%H%M%S")
            await page.screenshot(path=f"test_chart_{timestamp}.png", full_page=True)
            print(f"Screenshot: test_chart_{timestamp}.png")
            
        except Exception as e:
            print(f"ERRO: {e}")
            await page.screenshot(path="test_chart_error.png", full_page=True)
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_chart_simple())