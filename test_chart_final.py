#!/usr/bin/env python3
"""
Teste final Chart.js após correções
"""

import asyncio
from playwright.async_api import async_playwright

async def test_final():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1500)
        page = await browser.new_page()
        
        await page.goto('http://localhost:8000/login/')
        await page.fill('input[name="username"]', '04215498317')
        await page.fill('input[name="password"]', 'admin123')
        await page.press('input[name="password"]', 'Enter')
        
        await page.goto('http://localhost:8000/diretoria/dashboard/')
        await page.wait_for_timeout(8000)  # 8 segundos para carregar
        
        # Verificar Chart.js
        result = await page.evaluate('typeof Chart !== "undefined"')
        print(f'Chart.js disponivel: {result}')
        
        if result:
            version = await page.evaluate('Chart.version')
            print(f'Versao Chart.js: {version}')
            
            # Contar instâncias ativas
            instances = await page.evaluate('Object.keys(Chart.instances || {}).length')
            print(f'Instancias ativas: {instances}')
            
            if instances > 0:
                print('SUCESSO! Graficos Chart.js criados!')
            else:
                print('Chart.js carregou mas graficos nao foram criados')
                
                # Tentar criar um gráfico manual
                test_chart = await page.evaluate("""
                    try {
                        const canvas = document.getElementById('monthlyChart');
                        if (canvas) {
                            const ctx = canvas.getContext('2d');
                            new Chart(ctx, {
                                type: 'bar',
                                data: {
                                    labels: ['Teste'],
                                    datasets: [{ data: [10], backgroundColor: '#667eea' }]
                                }
                            });
                            return 'Grafico teste criado!';
                        }
                        return 'Canvas nao encontrado';
                    } catch (e) {
                        return 'Erro: ' + e.message;
                    }
                """)
                print(f'Teste manual: {test_chart}')
        else:
            print('Chart.js NAO carregou')
        
        await page.screenshot(path='dashboard_test_final.png', full_page=True)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_final())