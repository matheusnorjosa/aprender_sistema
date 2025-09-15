#!/usr/bin/env python3
"""
Teste específico para Chart.js funcionando em staging
"""

import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

async def test_chart_staging():
    print("TESTE CHART.JS - STAGING")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Apenas logs importantes (sem emojis ou caracteres especiais)
        console_logs = []
        def log_console(msg):
            console_logs.append(f"{msg.type}: {msg.text}")
        page.on('console', log_console)
        
        try:
            print("\n1. LOGIN")
            await page.goto("http://localhost:8000/login/")
            await page.fill('input[name="username"]', '04215498317')
            await page.fill('input[name="password"]', 'admin123')
            await page.press('input[name="password"]', 'Enter')
            
            print("\n2. DASHBOARD")
            await page.goto("http://localhost:8000/diretoria/dashboard/")
            
            # Aguardar muito tempo para o Chart.js carregar
            print("Aguardando 10 segundos...")
            await page.wait_for_timeout(10000)
            
            # Verificar se Chart.js carregou
            chart_available = await page.evaluate("typeof Chart !== 'undefined'")
            print(f"Chart.js disponível: {chart_available}")
            
            if chart_available:
                version = await page.evaluate("Chart.version")
                print(f"Chart.js versão: {version}")
                
                # Criar um gráfico de teste
                test_result = await page.evaluate("""
                    try {
                        const canvas = document.getElementById('monthlyChart');
                        if (canvas) {
                            const ctx = canvas.getContext('2d');
                            new Chart(ctx, {
                                type: 'bar',
                                data: {
                                    labels: ['Jan', 'Fev', 'Mar'],
                                    datasets: [{
                                        data: [10, 20, 15],
                                        backgroundColor: '#667eea'
                                    }]
                                }
                            });
                            return 'SUCESSO: Gráfico criado!';
                        } else {
                            return 'ERRO: Canvas não encontrado';
                        }
                    } catch (e) {
                        return 'ERRO: ' + e.message;
                    }
                """)
                print(f"Teste gráfico: {test_result}")
                
                # Verificar instâncias Chart
                instances = await page.evaluate("Object.keys(Chart.instances || {}).length")
                print(f"Instâncias Chart: {instances}")
                
            else:
                print("Chart.js NÃO carregou - verificando motivo...")
                
                # Verificar se o script local carregou
                local_loaded = await page.evaluate("""
                    const scripts = Array.from(document.scripts);
                    scripts.some(s => s.src.includes('chart.min.js'))
                """)
                print(f"Script local presente: {local_loaded}")
                
            # Screenshot
            timestamp = datetime.now().strftime("%H%M%S")
            await page.screenshot(path=f"test_staging_{timestamp}.png", full_page=True)
            print(f"Screenshot: test_staging_{timestamp}.png")
            
        except Exception as e:
            print(f"ERRO: {e}")
            await page.screenshot(path="test_staging_error.png")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_chart_staging())