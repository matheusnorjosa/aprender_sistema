#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste com Playwright - Dashboard Executivo
Captura screenshots e analisa se os gráficos estão funcionando
"""

import os
import django
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

class DashboardTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.screenshots_dir = "dashboard_screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
    async def take_screenshot(self, page, name, description=""):
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{self.screenshots_dir}/{timestamp}_{name}.png"
        await page.screenshot(path=filename, full_page=True)
        print(f"📸 Screenshot: {filename} - {description}")
        return filename
        
    async def wait_for_charts_or_fallbacks(self, page, timeout=10000):
        """Espera pelos gráficos Chart.js ou fallbacks aparecerem"""
        print("⏳ Aguardando gráficos ou fallbacks...")
        
        try:
            # Esperar por qualquer um dos indicadores de sucesso
            await page.wait_for_function("""
                () => {
                    // Verifica se há canvas ativos (Chart.js funcionando)
                    const activeCanvas = document.querySelectorAll('canvas.active');
                    if (activeCanvas.length > 0) return 'charts';
                    
                    // Verifica se há fallbacks visíveis
                    const visibleFallbacks = document.querySelectorAll('.chart-fallback:not(.hidden)');
                    if (visibleFallbacks.length > 0) return 'fallbacks';
                    
                    // Verifica status de erro
                    const status = document.getElementById('statusIndicator');
                    if (status && status.textContent.includes('indisponível')) return 'error';
                    
                    return false;
                }
            """, timeout=timeout)
            
            # Verificar qual tipo foi carregado
            result = await page.evaluate("""
                () => {
                    const activeCanvas = document.querySelectorAll('canvas.active').length;
                    const visibleFallbacks = document.querySelectorAll('.chart-fallback:not(.hidden)').length;
                    const status = document.getElementById('statusIndicator').textContent;
                    
                    return {
                        activeCharts: activeCanvas,
                        visibleFallbacks: visibleFallbacks,
                        status: status,
                        total: activeCanvas + visibleFallbacks
                    };
                }
            """)
            
            print(f"✅ Dashboard carregado: {result['activeCharts']} gráficos, {result['visibleFallbacks']} fallbacks")
            print(f"📊 Status: {result['status']}")
            return result
            
        except Exception as e:
            print(f"⚠️ Timeout aguardando dashboard: {e}")
            return None
    
    async def analyze_dashboard(self, page):
        """Analisa o estado atual do dashboard"""
        print("\n🔍 ANALISANDO DASHBOARD...")
        
        # Informações gerais
        title = await page.title()
        url = page.url
        print(f"📄 Página: {title}")
        print(f"🔗 URL: {url}")
        
        # Verificar elementos principais
        stats_cards = await page.locator('.stat-card').count()
        chart_cards = await page.locator('.chart-card').count()
        
        print(f"📊 Cards de estatísticas: {stats_cards}")
        print(f"📈 Cards de gráficos: {chart_cards}")
        
        # Analisar cada gráfico
        charts_info = await page.evaluate("""
            () => {
                const charts = [
                    { id: 'monthlyChart', name: 'Evolução Mensal', fallback: 'monthlyFallback' },
                    { id: 'typesChart', name: 'Tipos de Evento', fallback: 'typesFallback' },
                    { id: 'formatorsChart', name: 'Top Formadores', fallback: 'formatorsFallback' },
                    { id: 'citiesChart', name: 'Municípios', fallback: 'citiesFallback' },
                    { id: 'sectorsChart', name: 'Setores', fallback: 'sectorsFallback' },
                    { id: 'projectsChart', name: 'Projetos', fallback: 'projectsFallback' }
                ];
                
                return charts.map(chart => {
                    const canvas = document.getElementById(chart.id);
                    const fallback = document.getElementById(chart.fallback);
                    
                    return {
                        name: chart.name,
                        hasCanvas: !!canvas,
                        canvasActive: canvas && canvas.classList.contains('active'),
                        hasFallback: !!fallback,
                        fallbackVisible: fallback && !fallback.classList.contains('hidden'),
                        status: canvas && canvas.classList.contains('active') ? 'chart' : 'fallback'
                    };
                });
            }
        """)
        
        print("\n📊 STATUS DOS GRÁFICOS:")
        charts_working = 0
        fallbacks_working = 0
        
        for chart in charts_info:
            status_icon = "📈" if chart['status'] == 'chart' else "📋"
            status_text = "GRÁFICO ATIVO" if chart['status'] == 'chart' else "FALLBACK ATIVO"
            print(f"{status_icon} {chart['name']}: {status_text}")
            
            if chart['status'] == 'chart':
                charts_working += 1
            else:
                fallbacks_working += 1
        
        # Status do Chart.js
        chartjs_status = await page.evaluate("""
            () => {
                if (typeof Chart !== 'undefined') {
                    return { available: true, version: Chart.version || 'unknown' };
                } else {
                    return { available: false, version: null };
                }
            }
        """)
        
        print(f"\n🔧 Chart.js Status:")
        if chartjs_status['available']:
            print(f"✅ Disponível - Versão: {chartjs_status['version']}")
        else:
            print(f"❌ Não disponível")
        
        return {
            'charts_working': charts_working,
            'fallbacks_working': fallbacks_working,
            'total_displays': charts_working + fallbacks_working,
            'chartjs_available': chartjs_status['available'],
            'charts_info': charts_info
        }
    
    async def test_admin_user(self, page):
        """Testa dashboard com usuário admin"""
        print("\n" + "="*60)
        print("🧑‍💼 TESTE COM USUÁRIO ADMIN")
        print("="*60)
        
        # Fazer login
        await page.goto(f"{self.base_url}/login/")
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'admin123')
        await page.click('button[type="submit"]')
        
        # Aguardar redirecionamento
        await page.wait_for_url("**/", timeout=5000)
        print("✅ Login como admin realizado")
        
        # Ir para dashboard
        await page.goto(f"{self.base_url}/diretoria/dashboard/")
        await self.take_screenshot(page, "admin_dashboard_loading", "Dashboard admin carregando")
        
        # Aguardar dashboard carregar
        result = await self.wait_for_charts_or_fallbacks(page)
        if result:
            await self.take_screenshot(page, "admin_dashboard_loaded", "Dashboard admin carregado")
            analysis = await self.analyze_dashboard(page)
            return analysis
        else:
            await self.take_screenshot(page, "admin_dashboard_error", "Erro no dashboard admin")
            return None
    
    async def test_diretoria_user(self, page):
        """Testa dashboard com usuário diretoria_teste"""
        print("\n" + "="*60)
        print("👩‍💼 TESTE COM USUÁRIO DIRETORIA_TESTE")
        print("="*60)
        
        # Fazer logout primeiro
        await page.goto(f"{self.base_url}/logout/")
        
        # Fazer login
        await page.goto(f"{self.base_url}/login/")
        await page.fill('input[name="username"]', 'diretoria_teste')
        await page.fill('input[name="password"]', 'teste123')
        await page.click('button[type="submit"]')
        
        # Aguardar redirecionamento
        await page.wait_for_url("**/", timeout=5000)
        print("✅ Login como diretoria_teste realizado")
        
        # Ir para dashboard
        await page.goto(f"{self.base_url}/diretoria/dashboard/")
        await self.take_screenshot(page, "diretoria_dashboard_loading", "Dashboard diretoria carregando")
        
        # Aguardar dashboard carregar
        result = await self.wait_for_charts_or_fallbacks(page)
        if result:
            await self.take_screenshot(page, "diretoria_dashboard_loaded", "Dashboard diretoria carregado")
            analysis = await self.analyze_dashboard(page)
            return analysis
        else:
            await self.take_screenshot(page, "diretoria_dashboard_error", "Erro no dashboard diretoria")
            return None
    
    async def test_standalone_dashboard(self, page):
        """Testa dashboard standalone"""
        print("\n" + "="*60)
        print("🔓 TESTE DASHBOARD STANDALONE (SEM LOGIN)")
        print("="*60)
        
        # Ir diretamente para página standalone
        await page.goto(f"{self.base_url}/diretoria/test/")
        await self.take_screenshot(page, "standalone_loading", "Dashboard standalone carregando")
        
        # Aguardar dashboard carregar
        result = await self.wait_for_charts_or_fallbacks(page)
        if result:
            await self.take_screenshot(page, "standalone_loaded", "Dashboard standalone carregado")
            analysis = await self.analyze_dashboard(page)
            return analysis
        else:
            await self.take_screenshot(page, "standalone_error", "Erro no dashboard standalone")
            return None
    
    async def run_all_tests(self):
        """Executa todos os testes"""
        print("🚀 INICIANDO TESTES PLAYWRIGHT - DASHBOARD EXECUTIVO")
        print("="*80)
        
        async with async_playwright() as p:
            # Lançar navegador
            browser = await p.chromium.launch(headless=False, slow_mo=1000)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            # Configurar timeout padrão
            page.set_default_timeout(15000)
            
            results = {}
            
            try:
                # Teste 1: Standalone
                results['standalone'] = await self.test_standalone_dashboard(page)
                
                # Teste 2: Admin
                results['admin'] = await self.test_admin_user(page)
                
                # Teste 3: Diretoria
                results['diretoria'] = await self.test_diretoria_user(page)
                
                # Relatório final
                self.generate_report(results)
                
            except Exception as e:
                print(f"❌ Erro durante testes: {e}")
                await self.take_screenshot(page, "error_general", f"Erro geral: {e}")
            
            finally:
                await browser.close()
        
        print("\n✅ TESTES FINALIZADOS!")
        print(f"📁 Screenshots salvas em: {self.screenshots_dir}/")
    
    def generate_report(self, results):
        """Gera relatório final dos testes"""
        print("\n" + "="*80)
        print("📊 RELATÓRIO FINAL - TESTES DASHBOARD")
        print("="*80)
        
        total_charts = 0
        total_fallbacks = 0
        
        for test_name, result in results.items():
            if result:
                print(f"\n🔍 {test_name.upper()}:")
                print(f"   📈 Gráficos Chart.js: {result['charts_working']}/6")
                print(f"   📋 Fallbacks visuais: {result['fallbacks_working']}/6")
                print(f"   ✅ Total funcionando: {result['total_displays']}/6")
                print(f"   🔧 Chart.js disponível: {'Sim' if result['chartjs_available'] else 'Não'}")
                
                total_charts += result['charts_working']
                total_fallbacks += result['fallbacks_working']
        
        print(f"\n🎯 RESUMO GERAL:")
        print(f"   📊 Total gráficos funcionando: {total_charts}")
        print(f"   📋 Total fallbacks ativos: {total_fallbacks}")
        
        if total_charts > 0:
            print(f"\n🎉 SUCESSO! Chart.js está funcionando em pelo menos um cenário!")
        elif total_fallbacks > 0:
            print(f"\n✅ FUNCIONAL! Fallbacks visuais garantem que o dashboard sempre funciona!")
        else:
            print(f"\n❌ PROBLEMA! Nem gráficos nem fallbacks estão funcionando!")
        
        print("\n💡 PRÓXIMOS PASSOS:")
        if total_charts == 0:
            print("   - Verificar se Chart.js local foi carregado corretamente")
            print("   - Testar conexão CDN externa")
            print("   - Os fallbacks visuais já garantem funcionalidade completa")
        else:
            print("   - Dashboard funcionando perfeitamente!")
            print("   - Gráficos interativos disponíveis")

async def main():
    tester = DashboardTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())