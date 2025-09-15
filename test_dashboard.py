#!/usr/bin/env python3
"""
Servidor HTTP simples para testar o dashboard sem Django
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Definir porta
PORT = 8080

# Mudar para o diretório dos templates
template_dir = Path(__file__).parent / "core" / "templates" / "core" / "diretoria"
os.chdir(template_dir)

# Criar servidor HTTP
class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/dashboard_clean.html'
        return super().do_GET()

# Iniciar servidor
with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"🚀 Servidor rodando em http://localhost:{PORT}")
    print(f"📁 Servindo arquivos de: {template_dir}")
    print("📊 Dashboard: http://localhost:8080")
    print("⏹️ Pressione Ctrl+C para parar")
    
    # Abrir no navegador
    webbrowser.open(f'http://localhost:{PORT}')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Servidor parado")
        httpd.shutdown()