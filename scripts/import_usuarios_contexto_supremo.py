#!/usr/bin/env python3
"""
IMPORTADOR USUÁRIOS - CONTEXTO SUPREMO
=====================================

Script para importar dados da planilha "Usuários"
conforme o contexto supremo fornecido.

Estrutura:
- Aba Ativos: Funcionários da empresa (Formadores, Coordenadores e Gerentes)
- Colunas: Nome, Nome Completo, CPF, Telefone, Email, Cargo, Gerência
- Gerências especiais: "Outros" com mapeamentos específicos

Autor: Claude Code
Data: Janeiro 2025
"""

import os
import sys
import django
import json
import logging
from datetime import datetime, time, date
from typing import Dict, List, Any, Optional

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from core.models import (
    Usuario, Municipio, Projeto, TipoEvento, Solicitacao,
    SolicitacaoStatus, Setor, FormadoresSolicitacao, Formador
)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

User = get_user_model()


class ImportadorUsuariosContextoSupremo:
    """
    Importador da planilha Usuários com contexto supremo
    """
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.planilha_id = '1yPH-uCRc2XyThLU7V4pSoNYozydn1-IRRJRjubFCjXs'
        
        # Configuração da aba
        self.aba_config = {
            'Ativos': {
                'colunas': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
                'nomes_colunas': [
                    'Nome', 'Nome Completo', 'CPF', 'Telefone', 'Email', 'Cargo', 'Gerência'
                ],
                'descricao': 'Funcionários da empresa - Formadores, Coordenadores e Gerentes'
            }
        }
        
        # Mapeamento de gerências especiais
        self.gerencias_especiais = {
            'A COR DA GENTE': 'Daniele Cristina',
            'ED FINANCEIRA': 'Amanda Arruda',
            'LER, OUVIR E CONTAR': 'Lourene Pinheiro',
            'SOU DA PAZ': 'Rafael Rabelo',
            'IDEB10': 'Vinicius Albuquerque',
            'LEIO ESCREVO E CALCULO': 'Ellen Damares',
            'IDEB10 - ESQUENTA SAEB': 'Vinicius Albuquerque'
        }
        
        # Mapeamento de cargos para grupos Django
        self.cargo_para_grupo = {
            'Formador': 'Formadores',
            'Coordenador': 'Coordenadores',
            'Gerente': 'Gerentes',
            'Superintendente': 'Superintendentes'
        }
        
        # Estatísticas
        self.estatisticas = {
            'total_registros': 0,
            'usuarios_importados': 0,
            'formadores_importados': 0,
            'coordenadores_importados': 0,
            'gerentes_importados': 0,
            'gerencias_especiais_mapeadas': 0,
            'erros': 0,
            'por_cargo': {}
        }

    def conectar_google_sheets(self):
        """
        Conectar ao Google Sheets
        """
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            
            # Configurar credenciais
            creds_path = os.path.join(os.path.dirname(__file__), 'google_service_account.json')
            if not os.path.exists(creds_path):
                logger.error("❌ Arquivo de credenciais não encontrado: google_service_account.json")
                return None
            
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            creds = Credentials.from_service_account_file(creds_path, scopes=scope)
            client = gspread.authorize(creds)
            
            # Abrir planilha
            spreadsheet = client.open_by_key(self.planilha_id)
            logger.info(f"✅ Conectado à planilha: {spreadsheet.title}")
            
            return spreadsheet
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar Google Sheets: {str(e)}")
            return None

    def validar_cpf(self, cpf: str) -> bool:
        """
        Validar CPF
        """
        if not cpf:
            return False
        
        # Remover caracteres não numéricos
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Verificar se tem 11 dígitos
        if len(cpf) != 11:
            return False
        
        # Verificar se todos os dígitos são iguais
        if cpf == cpf[0] * 11:
            return False
        
        # Validar dígitos verificadores
        def calcular_digito(cpf, posicoes):
            soma = sum(int(cpf[i]) * posicoes[i] for i in range(len(posicoes)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        # Primeiro dígito verificador
        if int(cpf[9]) != calcular_digito(cpf, list(range(10, 1, -1))):
            return False
        
        # Segundo dígito verificador
        if int(cpf[10]) != calcular_digito(cpf, list(range(11, 1, -1))):
            return False
        
        return True

    def formatar_cpf(self, cpf: str) -> str:
        """
        Formatar CPF
        """
        if not cpf:
            return ''
        
        # Remover caracteres não numéricos
        cpf = ''.join(filter(str.isdigit, cpf))
        
        # Formatar como XXX.XXX.XXX-XX
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        
        return cpf

    def processar_gerencia_especial(self, gerencia: str) -> Dict[str, str]:
        """
        Processar gerência especial
        """
        if gerencia == 'Outros':
            return {
                'tipo': 'especial',
                'mapeamentos': self.gerencias_especiais
            }
        else:
            return {
                'tipo': 'normal',
                'gerencia': gerencia
            }

    def importar_usuario(self, usuario_data: Dict) -> bool:
        """
        Importar um usuário para o banco de dados
        """
        try:
            if self.dry_run:
                logger.info(f"🔍 [DRY RUN] Usuário: {usuario_data.get('Nome', 'N/A')} - {usuario_data.get('Cargo', 'N/A')}")
                return True
            
            # Validar dados obrigatórios
            nome = usuario_data.get('Nome', '').strip()
            nome_completo = usuario_data.get('Nome Completo', '').strip()
            cpf = usuario_data.get('CPF', '').strip()
            email = usuario_data.get('Email', '').strip()
            cargo = usuario_data.get('Cargo', '').strip()
            gerencia = usuario_data.get('Gerência', '').strip()
            
            if not nome or not nome_completo:
                logger.warning("⚠️ Nome ou Nome Completo não informado, pulando usuário")
                return False
            
            # Validar CPF
            if cpf and not self.validar_cpf(cpf):
                logger.warning(f"⚠️ CPF inválido para {nome}: {cpf}")
                cpf = ''  # Limpar CPF inválido
            
            # Formatar CPF
            cpf_formatado = self.formatar_cpf(cpf)
            
            # Gerar username único
            username = nome.lower().replace(' ', '_').replace('.', '').replace('-', '')
            
            # Gerar email se não fornecido
            if not email:
                email = f"{username}@aprender.com"
            
            # Processar gerência especial
            gerencia_info = self.processar_gerencia_especial(gerencia)
            
            # Criar ou atualizar usuário
            usuario, created = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    'nome': nome,
                    'nome_completo': nome_completo,
                    'cpf': cpf_formatado,
                    'telefone': usuario_data.get('Telefone', '').strip(),
                    'email': email,
                    'cargo': cargo,
                    'gerencia': gerencia,
                    'is_active': True,
                    'is_staff': cargo in ['Gerente', 'Superintendente'],
                    'is_superuser': cargo == 'Superintendente'
                }
            )
            
            if not created:
                # Atualizar dados existentes
                usuario.nome = nome
                usuario.nome_completo = nome_completo
                usuario.cpf = cpf_formatado
                usuario.telefone = usuario_data.get('Telefone', '').strip()
                usuario.email = email
                usuario.cargo = cargo
                usuario.gerencia = gerencia
                usuario.is_active = True
                usuario.is_staff = cargo in ['Gerente', 'Superintendente']
                usuario.is_superuser = cargo == 'Superintendente'
                usuario.save()
            
            # Adicionar ao grupo apropriado
            if cargo in self.cargo_para_grupo:
                from django.contrib.auth.models import Group
                grupo_nome = self.cargo_para_grupo[cargo]
                grupo, _ = Group.objects.get_or_create(name=grupo_nome)
                usuario.groups.add(grupo)
            
            # Processar gerência especial
            if gerencia_info['tipo'] == 'especial':
                self.estatisticas['gerencias_especiais_mapeadas'] += 1
                logger.info(f"🏢 Gerência especial mapeada para {nome}: {gerencia_info['mapeamentos']}")
            
            # Atualizar estatísticas por cargo
            if cargo not in self.estatisticas['por_cargo']:
                self.estatisticas['por_cargo'][cargo] = 0
            self.estatisticas['por_cargo'][cargo] += 1
            
            # Atualizar estatísticas gerais
            if cargo == 'Formador':
                self.estatisticas['formadores_importados'] += 1
            elif cargo == 'Coordenador':
                self.estatisticas['coordenadores_importados'] += 1
            elif cargo in ['Gerente', 'Superintendente']:
                self.estatisticas['gerentes_importados'] += 1
            
            self.estatisticas['usuarios_importados'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar usuário {usuario_data.get('Nome', 'N/A')}: {str(e)}")
            return False

    def processar_aba_ativos(self, spreadsheet):
        """
        Processar aba Ativos
        """
        logger.info("👥 Processando aba Ativos - Funcionários da empresa...")
        
        try:
            worksheet = spreadsheet.worksheet('Ativos')
            config = self.aba_config['Ativos']
            
            # Obter dados da planilha
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("⚠️ Aba Ativos está vazia")
                return
            
            # Primeira linha são os cabeçalhos
            headers = all_values[0]
            data_rows = all_values[1:]
            
            logger.info(f"📋 Cabeçalhos: {config['nomes_colunas']}")
            
            # Processar dados
            for i, row in enumerate(data_rows):
                if not any(row):  # Pular linhas vazias
                    continue
                
                # Extrair dados da linha
                usuario_data = {}
                for j, coluna in enumerate(config['colunas']):
                    if j < len(row):
                        nome_coluna = config['nomes_colunas'][j]
                        usuario_data[nome_coluna] = row[j].strip()
                
                # Adicionar informações da aba
                usuario_data['aba_origem'] = 'Ativos'
                usuario_data['linha_planilha'] = i + 2
                
                # Importar usuário
                if self.importar_usuario(usuario_data):
                    self.estatisticas['total_registros'] += 1
                else:
                    self.estatisticas['erros'] += 1
            
            logger.info("✅ Aba Ativos processada com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar aba Ativos: {str(e)}")
            self.estatisticas['erros'] += 1

    def executar_importacao(self):
        """
        Executar importação completa
        """
        logger.info("🚀 INICIANDO IMPORTAÇÃO USUÁRIOS - CONTEXTO SUPREMO")
        logger.info("=" * 70)
        
        if self.dry_run:
            logger.info("🔍 MODO DRY RUN - Nenhum dado será salvo no banco")
        
        # Conectar Google Sheets
        spreadsheet = self.conectar_google_sheets()
        if not spreadsheet:
            logger.error("❌ Não foi possível conectar ao Google Sheets")
            return False
        
        try:
            with transaction.atomic():
                # Processar aba Ativos
                self.processar_aba_ativos(spreadsheet)
                
                if self.dry_run:
                    logger.info("🔍 [DRY RUN] Transação seria commitada aqui")
                    raise transaction.TransactionManagementError("Dry run - rollback")
            
        except transaction.TransactionManagementError:
            if self.dry_run:
                logger.info("🔍 [DRY RUN] Rollback executado conforme esperado")
            else:
                logger.error("❌ Erro na transação")
                return False
        except Exception as e:
            logger.error(f"❌ Erro durante a importação: {str(e)}")
            return False
        
        # Relatório final
        self.gerar_relatorio_final()
        
        return True

    def gerar_relatorio_final(self):
        """
        Gerar relatório final da importação
        """
        logger.info("\n" + "=" * 70)
        logger.info("📊 RELATÓRIO FINAL DA IMPORTAÇÃO USUÁRIOS")
        logger.info("=" * 70)
        
        logger.info(f"📈 ESTATÍSTICAS GERAIS:")
        logger.info(f"   - Total de registros: {self.estatisticas['total_registros']}")
        logger.info(f"   - Usuários importados: {self.estatisticas['usuarios_importados']}")
        logger.info(f"   - Formadores importados: {self.estatisticas['formadores_importados']}")
        logger.info(f"   - Coordenadores importados: {self.estatisticas['coordenadores_importados']}")
        logger.info(f"   - Gerentes importados: {self.estatisticas['gerentes_importados']}")
        logger.info(f"   - Gerências especiais mapeadas: {self.estatisticas['gerencias_especiais_mapeadas']}")
        logger.info(f"   - Erros: {self.estatisticas['erros']}")
        
        logger.info(f"\n📋 ESTATÍSTICAS POR CARGO:")
        for cargo, quantidade in self.estatisticas['por_cargo'].items():
            logger.info(f"   - {cargo}: {quantidade}")
        
        logger.info(f"\n🏢 GERÊNCIAS ESPECIAIS MAPEADAS:")
        for gerencia, responsavel in self.gerencias_especiais.items():
            logger.info(f"   - {gerencia}: {responsavel}")
        
        # Salvar relatório em arquivo
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': self.dry_run,
            'estatisticas': self.estatisticas,
            'gerencias_especiais': self.gerencias_especiais
        }
        
        with open('relatorio_importacao_usuarios.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"\n💾 Relatório salvo em: relatorio_importacao_usuarios.json")


def main():
    """
    Função principal
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Importar dados da planilha Usuários')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Executar em modo de teste (padrão)')
    parser.add_argument('--execute', action='store_true',
                       help='Executar importação real (salvar no banco)')
    
    args = parser.parse_args()
    
    # Determinar modo de execução
    dry_run = not args.execute
    
    # Criar importador
    importador = ImportadorUsuariosContextoSupremo(dry_run=dry_run)
    
    # Executar importação
    sucesso = importador.executar_importacao()
    
    if sucesso:
        logger.info("🎉 IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    else:
        logger.error("❌ IMPORTAÇÃO FALHOU!")
        sys.exit(1)


if __name__ == '__main__':
    main()
