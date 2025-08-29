#!/usr/bin/env python3

import urllib.request
import urllib.parse
import http.cookiejar

def test_menu_formador():
    base_url = "http://localhost:8000"
    
    print("🔍 Testando aparição do menu para formador...")
    
    # Criar um jar de cookies para manter a sessão
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    urllib.request.install_opener(opener)
    
    try:
        # 1. Acessar qualquer página para verificar o menu
        home_url = f"{base_url}/"
        
        request = urllib.request.Request(home_url)
        response = urllib.request.urlopen(request)
        page_content = response.read().decode('utf-8')
        
        print("✅ Página home acessível")
        
        # 2. Verificar estrutura do menu
        checks = [
            ("Seção Formador existe", 'nav-section-title">Formador' in page_content),
            ("Link Meus Eventos existe", 'Meus Eventos' in page_content),
            ("URL formador_eventos existe", '/formador/eventos/' in page_content),
            ("Ícone person-workspace existe", 'bi-person-workspace' in page_content),
            ("Seção Coordenação existe", 'nav-section-title">Coordenação' in page_content),
        ]
        
        print("\n📋 Verificações do menu:")
        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
            if not check_result:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False

if __name__ == "__main__":
    try:
        success = test_menu_formador()
        if success:
            print("\n🎉 MENU DO FORMADOR FUNCIONANDO!")
            print("📝 Verificações:")
            print("   ✅ Seção 'Formador' aparece no menu lateral")
            print("   ✅ Link 'Meus Eventos' está presente")
            print("   ✅ URL /formador/eventos/ está configurada")
            print("   ✅ Ícone person-workspace está presente")
            print("\n📋 Observação:")
            print("   O menu só aparecerá para usuários logados com papel 'formador'")
        else:
            print("\n❌ Alguns problemas foram encontrados no menu")
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")