#!/usr/bin/env python
"""
Extrator de usuários reais das planilhas para o sistema Django existente
"""

import json
import gspread
import pandas as pd
import re
from google.oauth2.credentials import Credentials
import os
import sys
import django

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from core.models import Usuario, Setor
from django.contrib.auth.models import Group
from django.db import transaction

class ExtratorUsuariosReais:
    """Extrai e importa os 118 usuários reais das planilhas"""

    def __init__(self):
        self.usuarios_importados = 0
        self.erros = []

    def conectar_planilhas(self):
        """Conecta às planilhas Google Sheets"""
        try:
            with open('google_oauth_token.json', 'r') as f:
                token_data = json.load(f)

            creds = Credentials.from_authorized_user_info(token_data)
            self.gc = gspread.authorize(creds)
            print("✅ Conectado às planilhas Google Sheets")
            return True
        except Exception as e:
            print(f"❌ Erro na conexão: {e}")
            return False

    def validar_cpf(self, cpf_str):
        """Valida CPF com dígito verificador"""
        if not cpf_str:
            return False

        # Limpar caracteres não numéricos
        cpf = re.sub(r'\D', '', str(cpf_str))

        # Verificar se tem 11 dígitos
        if len(cpf) != 11:
            return False

        # Verificar se não são todos iguais
        if cpf == cpf[0] * 11:
            return False

        # Calcular dígitos verificadores
        def calcular_digito(cpf_parcial):
            soma = sum(int(cpf_parcial[i]) * (len(cpf_parcial) + 1 - i) for i in range(len(cpf_parcial)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto

        # Verificar primeiro dígito
        if int(cpf[9]) != calcular_digito(cpf[:9]):
            return False

        # Verificar segundo dígito
        if int(cpf[10]) != calcular_digito(cpf[:10]):
            return False

        return True

    def normalizar_email(self, email_str):
        """Normaliza e valida email"""
        if not email_str:
            return None

        email = str(email_str).strip().lower()

        # Regex básica para validar email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return email

        return None

    def mapear_cargo_para_grupo(self, cargo):
        """Mapeia cargo da planilha para grupo Django"""
        cargo_lower = str(cargo).lower().strip()

        if 'formador' in cargo_lower:
            return 'formador'
        elif 'coordenador' in cargo_lower:
            return 'coordenador'
        elif 'gerente' in cargo_lower:
            return 'gerente'
        elif 'super' in cargo_lower:
            return 'superintendencia'
        else:
            return 'formador'  # Default

    def mapear_gerencia_para_setor(self, gerencia):
        """Mapeia gerência para setor existente"""
        gerencia_str = str(gerencia).strip()

        if 'super' in gerencia_str.lower():
            return 'Superintendência'
        elif gerencia_str in ['ACerta', 'Vidas', 'Brincando', 'IDEB']:
            return 'Projetos Educacionais'
        else:
            return 'Coordenação Regional'

    def extrair_usuarios_reais(self):
        """Extrai usuários reais da aba Ativos"""

        print("📋 Extraindo usuários reais da planilha...")

        # Acessar planilha de usuários
        sheet_usuarios = self.gc.open_by_key('1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI')
        aba_ativos = sheet_usuarios.worksheet('Ativos')

        # Obter dados como DataFrame
        dados = aba_ativos.get_all_records()
        df = pd.DataFrame(dados)

        print(f"📊 Total de registros na aba Ativos: {len(df)}")

        # Filtrar registros válidos (com nome)
        df_validos = df[df['Nome'].notna() & (df['Nome'] != '')]

        print(f"📊 Registros com nome válido: {len(df_validos)}")

        usuarios_processados = []

        for _, row in df_validos.iterrows():
            try:
                # Extrair dados básicos
                nome = str(row['Nome']).strip()
                nome_completo = str(row.get('Nome Completo', '')).strip()
                cpf_raw = str(row.get('CPF', ''))
                email_raw = str(row.get('Email', ''))
                telefone = str(row.get('Telefone', '')).strip()
                cargo = str(row.get('Cargo', '')).strip()
                gerencia = str(row.get('Gerência', '')).strip()

                # Validar CPF
                cpf_valido = None
                if self.validar_cpf(cpf_raw):
                    cpf_valido = re.sub(r'\D', '', cpf_raw)

                # Validar email
                email_valido = self.normalizar_email(email_raw)

                # Gerar username único
                username = self.gerar_username(nome)

                # Mapear cargo para grupo
                grupo_nome = self.mapear_cargo_para_grupo(cargo)

                # Mapear gerência para setor
                setor_nome = self.mapear_gerencia_para_setor(gerencia)

                usuario_data = {
                    'nome': nome,
                    'nome_completo': nome_completo,
                    'username': username,
                    'cpf': cpf_valido,
                    'email': email_valido,
                    'telefone': telefone,
                    'cargo': cargo,
                    'gerencia': gerencia,
                    'grupo': grupo_nome,
                    'setor': setor_nome,
                    'row_original': dict(row)
                }

                usuarios_processados.append(usuario_data)

            except Exception as e:
                self.erros.append(f"Erro processando linha {nome}: {e}")

        print(f"📊 Usuários processados: {len(usuarios_processados)}")
        return usuarios_processados

    def gerar_username(self, nome):
        """Gera username único baseado no nome"""
        # Remover acentos e caracteres especiais
        import unicodedata
        nome_limpo = unicodedata.normalize('NFKD', nome)
        nome_limpo = ''.join([c for c in nome_limpo if not unicodedata.combining(c)])

        # Converter para lowercase e substituir espaços
        username_base = re.sub(r'[^a-zA-Z0-9]', '_', nome_limpo.lower())
        username_base = re.sub(r'_+', '_', username_base).strip('_')

        # Verificar se já existe
        username = username_base
        contador = 1

        while Usuario.objects.filter(username=username).exists():
            username = f"{username_base}_{contador}"
            contador += 1

        return username

    def importar_usuarios(self, usuarios_data):
        """Importa usuários para o Django"""

        print("💾 Importando usuários para o banco de dados...")

        for usuario_data in usuarios_data:
            try:
                with transaction.atomic():
                    # Verificar se já existe (pular admin)
                    if Usuario.objects.filter(username=usuario_data['username']).exists():
                        print(f"   ⚠️ Usuário {usuario_data['username']} já existe, pulando...")
                        continue

                    # Buscar setor
                    setor = None
                    if usuario_data['setor']:
                        setor, _ = Setor.objects.get_or_create(
                            nome=usuario_data['setor'],
                            defaults={'ativo': True}
                        )

                    # Criar usuário
                    usuario = Usuario.objects.create(
                        username=usuario_data['username'],
                        email=usuario_data['email'] or f"{usuario_data['username']}@aprender.com",
                        first_name=usuario_data['nome'].split()[0] if usuario_data['nome'] else '',
                        last_name=' '.join(usuario_data['nome'].split()[1:]) if len(usuario_data['nome'].split()) > 1 else '',
                        is_active=True
                    )

                    # Definir senha padrão
                    usuario.set_password('aprender123')
                    usuario.save()

                    # Adicionar ao grupo
                    if usuario_data['grupo']:
                        grupo, _ = Group.objects.get_or_create(name=usuario_data['grupo'])
                        usuario.groups.add(grupo)

                    self.usuarios_importados += 1

                    if self.usuarios_importados % 10 == 0:
                        print(f"   ✅ {self.usuarios_importados} usuários importados...")

            except Exception as e:
                self.erros.append(f"Erro importando {usuario_data['nome']}: {e}")
                print(f"   ❌ Erro: {usuario_data['nome']} - {e}")

        print(f"✅ Total de usuários importados: {self.usuarios_importados}")

    def gerar_relatorio(self):
        """Gera relatório da importação"""

        relatorio = {
            'timestamp': '2025-09-23',
            'usuarios_importados': self.usuarios_importados,
            'total_erros': len(self.erros),
            'erros': self.erros,
            'estatisticas': {
                'total_usuarios_sistema': Usuario.objects.count(),
                'usuarios_por_grupo': {
                    grupo.name: grupo.user_set.count()
                    for grupo in Group.objects.all()
                }
            }
        }

        with open('/app/relatorio_importacao_usuarios_reais.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

        print("📄 Relatório salvo: relatorio_importacao_usuarios_reais.json")
        return relatorio

def main():
    """Executa extração e importação de usuários reais"""

    print("👥 EXTRAÇÃO E IMPORTAÇÃO DE USUÁRIOS REAIS")
    print("=" * 60)

    extrator = ExtratorUsuariosReais()

    try:
        # Conectar
        if not extrator.conectar_planilhas():
            return False

        # Extrair dados
        usuarios_data = extrator.extrair_usuarios_reais()

        if not usuarios_data:
            print("❌ Nenhum usuário válido encontrado")
            return False

        # Importar
        extrator.importar_usuarios(usuarios_data)

        # Gerar relatório
        relatorio = extrator.gerar_relatorio()

        print("\n📊 RESUMO DA IMPORTAÇÃO:")
        print(f"   ✅ Usuários importados: {relatorio['usuarios_importados']}")
        print(f"   ❌ Erros: {relatorio['total_erros']}")
        print(f"   👥 Total no sistema: {relatorio['estatisticas']['total_usuarios_sistema']}")

        if relatorio['total_erros'] > 0:
            print(f"\n⚠️ Primeiros 5 erros:")
            for erro in relatorio['erros'][:5]:
                print(f"   - {erro}")

        print("\n🎉 IMPORTAÇÃO DE USUÁRIOS REAIS CONCLUÍDA!")
        return True

    except Exception as e:
        print(f"❌ ERRO na extração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()