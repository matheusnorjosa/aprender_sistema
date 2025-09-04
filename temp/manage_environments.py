#!/usr/bin/env python
"""
Script para gerenciar ambientes de desenvolvimento, homologação e produção
"""

import json
import os
import subprocess
import sys
from datetime import datetime


class EnvironmentManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
    def start_development(self):
        """Inicia ambiente de desenvolvimento"""
        print("🔧 INICIANDO AMBIENTE DE DESENVOLVIMENTO")
        try:
            subprocess.run(['docker-compose', 'up', '-d'], cwd=self.base_dir, check=True)
            print("✅ Desenvolvimento iniciado: http://localhost:8000")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao iniciar desenvolvimento: {e}")

    def start_homologacao(self):
        """Inicia ambiente de homologação"""
        print("🧪 INICIANDO AMBIENTE DE HOMOLOGAÇÃO")
        try:
            subprocess.run(['docker-compose', '-f', 'docker-compose.homolog.yml', 'up', '-d'], 
                         cwd=self.base_dir, check=True)
            print("✅ Homologação iniciada: http://localhost:8001")
            print("⚠️  LEMBRE-SE: Este é um ambiente de TESTES")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao iniciar homologação: {e}")

    def stop_all(self):
        """Para todos os ambientes"""
        print("🛑 PARANDO TODOS OS AMBIENTES")
        try:
            # Parar desenvolvimento
            subprocess.run(['docker-compose', 'down'], cwd=self.base_dir)
            # Parar homologação  
            subprocess.run(['docker-compose', '-f', 'docker-compose.homolog.yml', 'down'], 
                         cwd=self.base_dir)
            print("✅ Todos os ambientes parados")
        except Exception as e:
            print(f"❌ Erro ao parar ambientes: {e}")

    def sync_dev_to_homolog(self):
        """Sincroniza dados de desenvolvimento para homologação"""
        print("🔄 SINCRONIZANDO DEV → HOMOLOG")
        
        # 1. Fazer backup de homolog
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        print(f"Fazendo backup de homolog antes da sincronização...")
        
        # 2. Copiar banco de dev para homolog
        dev_db = os.path.join(self.base_dir, 'db.sqlite3')
        homolog_db = os.path.join(self.base_dir, 'db_homolog.sqlite3')
        
        if os.path.exists(dev_db):
            # Backup do homolog atual
            if os.path.exists(homolog_db):
                backup_homolog = f"db_homolog_backup_{timestamp}.sqlite3"
                os.rename(homolog_db, backup_homolog)
                print(f"  Backup homolog salvo: {backup_homolog}")
            
            # Copiar dev para homolog
            import shutil
            shutil.copy2(dev_db, homolog_db)
            print("✅ Base de dados sincronizada")
        else:
            print("❌ Base de desenvolvimento não encontrada")

    def create_test_data_homolog(self):
        """Cria dados de teste específicos para homologação"""
        print("📝 CRIANDO DADOS DE TESTE PARA HOMOLOG")
        
        # Script para executar dentro do container de homolog
        test_script = '''
from django.contrib.auth.models import Group
from core.models import Usuario, Projeto, Municipio, TipoEvento, Formador
from django.contrib.auth import get_user_model

# Criar usuários de teste para cada grupo
grupos_teste = [
    ("coord_super", "coordenador", "Superintendência"),
    ("coord_acerta", "coordenador", "ACerta"),
    ("gerente_vidas", "gerente_aprender", "Vidas"), 
    ("controle_user", "controle", None),
    ("super_manager", "superintendencia", "Superintendência"),
    ("dir_executive", "diretoria", None)
]

User = get_user_model()

for username, grupo_nome, projeto_nome in grupos_teste:
    # Criar usuário se não existir
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': f'{username}@teste.com',
            'first_name': username.replace('_', ' ').title(),
            'is_active': True
        }
    )
    
    if created:
        user.set_password('teste123')
        user.save()
    
    # Adicionar ao grupo
    try:
        grupo = Group.objects.get(name=grupo_nome)
        user.groups.add(grupo)
        print(f"✅ {username} → {grupo_nome}")
    except Group.DoesNotExist:
        print(f"❌ Grupo {grupo_nome} não existe")

print("\\n🎯 DADOS DE TESTE CRIADOS")
print("Usuários disponíveis:")
for username, grupo, projeto in grupos_teste:
    print(f"  {username} / teste123 → {grupo} ({projeto or 'N/A'})")
'''

        # Salvar script temporário
        script_file = os.path.join(self.base_dir, 'temp_create_test_data.py')
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        try:
            # Executar no container de homolog
            subprocess.run([
                'docker-compose', '-f', 'docker-compose.homolog.yml', 
                'exec', 'web-homolog', 'python', 'manage.py', 'shell'
            ], input=test_script, text=True, cwd=self.base_dir)
            
            print("✅ Dados de teste criados em homologação")
        except Exception as e:
            print(f"❌ Erro ao criar dados de teste: {e}")
        finally:
            # Limpar arquivo temporário
            if os.path.exists(script_file):
                os.remove(script_file)

    def status(self):
        """Mostra status dos ambientes"""
        print("📊 STATUS DOS AMBIENTES")
        
        try:
            # Verificar desenvolvimento
            result = subprocess.run(['docker-compose', 'ps'], 
                                  cwd=self.base_dir, capture_output=True, text=True)
            dev_running = 'Up' in result.stdout
            print(f"🔧 Desenvolvimento: {'🟢 RODANDO' if dev_running else '🔴 PARADO'}")
            if dev_running:
                print("   → http://localhost:8000")
            
            # Verificar homologação
            result = subprocess.run(['docker-compose', '-f', 'docker-compose.homolog.yml', 'ps'], 
                                  cwd=self.base_dir, capture_output=True, text=True)
            homolog_running = 'Up' in result.stdout
            print(f"🧪 Homologação: {'🟢 RODANDO' if homolog_running else '🔴 PARADO'}")
            if homolog_running:
                print("   → http://localhost:8001")
                
        except Exception as e:
            print(f"❌ Erro ao verificar status: {e}")


def main():
    manager = EnvironmentManager()
    
    if len(sys.argv) < 2:
        print("""
🏗️  GERENCIADOR DE AMBIENTES - Sistema Aprender

Comandos disponíveis:
  python manage_environments.py dev      # Iniciar desenvolvimento
  python manage_environments.py homolog  # Iniciar homologação  
  python manage_environments.py stop     # Parar todos
  python manage_environments.py sync     # Sincronizar dev → homolog
  python manage_environments.py test-data # Criar dados de teste
  python manage_environments.py status   # Ver status dos ambientes

Ambientes:
  🔧 Desenvolvimento: http://localhost:8000 (SQLite)
  🧪 Homologação:     http://localhost:8001 (PostgreSQL)
        """)
        return
    
    command = sys.argv[1]
    
    if command == 'dev':
        manager.start_development()
    elif command == 'homolog':
        manager.start_homologacao()
    elif command == 'stop':
        manager.stop_all()
    elif command == 'sync':
        manager.sync_dev_to_homolog()
    elif command == 'test-data':
        manager.create_test_data_homolog()
    elif command == 'status':
        manager.status()
    else:
        print(f"❌ Comando desconhecido: {command}")


if __name__ == "__main__":
    main()