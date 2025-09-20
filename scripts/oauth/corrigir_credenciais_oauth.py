#!/usr/bin/env python
"""
Corrige arquivo de credenciais OAuth2
"""

import json
import os

def corrigir_credenciais():
    """Corrige o arquivo de credenciais OAuth2"""
    
    print("🔧 Corrigindo arquivo de credenciais OAuth2...")
    
    # Ler arquivo atual
    with open("acesso_planilhas.json", "r") as f:
        creds = json.load(f)
    
    print(f"📋 Configuração atual:")
    print(f"   Client ID: {creds['installed']['client_id']}")
    print(f"   Redirect URIs: {creds['installed']['redirect_uris']}")
    
    # Corrigir redirect_uris
    creds['installed']['redirect_uris'] = [
        "urn:ietf:wg:oauth:2.0:oob",
        "http://localhost"
    ]
    
    # Salvar arquivo corrigido
    with open("acesso_planilhas.json", "w") as f:
        json.dump(creds, f, indent=2)
    
    print(f"✅ Arquivo corrigido!")
    print(f"   Novos Redirect URIs: {creds['installed']['redirect_uris']}")
    
    return True

if __name__ == "__main__":
    corrigir_credenciais()
