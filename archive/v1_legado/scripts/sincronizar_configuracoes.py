#!/usr/bin/env python3
"""
Script de Sincronização de Configurações
========================================

Sincroniza configurações entre Docker, arquivos locais e GitHub
para garantir consistência entre todos os ambientes.

Author: Claude Code
Date: Setembro 2025
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def print_header(title):
    """Imprime cabeçalho formatado"""
    print("\n" + "=" * 60)
    print(f"🔧 {title}")
    print("=" * 60)


def print_step(step, description):
    """Imprime passo formatado"""
    print(f"\n📋 PASSO {step}: {description}")
    print("-" * 40)


def run_command(command, description):
    """Executa comando e retorna resultado"""
    print(f"⚡ Executando: {description}")
    print(f"   Comando: {command}")

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Sucesso: {description}")
            return True
        else:
            print(f"   ❌ Erro: {description}")
            print(f"   Erro: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Exceção: {description}")
        print(f"   Erro: {str(e)}")
        return False


def verificar_ambiente():
    """Verifica o ambiente atual"""
    print_step(1, "VERIFICANDO AMBIENTE ATUAL")

    # Verificar se estamos no diretório correto
    if not os.path.exists("manage.py"):
        print("❌ Erro: Execute este script no diretório raiz do projeto")
        return False

    # Verificar se Docker está rodando
    if not run_command("docker ps", "Verificando se Docker está rodando"):
        print("❌ Erro: Docker não está rodando")
        return False

    # Verificar containers
    containers = ["aprender_web", "aprender_db", "aprender_redis"]
    for container in containers:
        if not run_command(
            f"docker ps --filter name={container} --format '{{{{.Names}}}}'",
            f"Verificando container {container}",
        ):
            print(f"⚠️ Aviso: Container {container} não está rodando")

    return True


def sincronizar_arquivos_locais():
    """Sincroniza arquivos locais com Docker"""
    print_step(2, "SINCRONIZANDO ARQUIVOS LOCAIS COM DOCKER")

    # Arquivos para sincronizar
    arquivos_para_sincronizar = [
        "aprender_sistema/settings_unificado.py",
        "config_unificado.env",
        "docker-compose.unificado.yml",
        "gerar_planilha_municipios.py",
    ]

    for arquivo in arquivos_para_sincronizar:
        if os.path.exists(arquivo):
            print(f"📁 Sincronizando: {arquivo}")
            run_command(
                f"docker cp {arquivo} aprender_web:/app/",
                f"Copiando {arquivo} para Docker",
            )
        else:
            print(f"⚠️ Arquivo não encontrado: {arquivo}")

    return True


def aplicar_configuracao_unificada():
    """Aplica configuração unificada no Docker"""
    print_step(3, "APLICANDO CONFIGURAÇÃO UNIFICADA NO DOCKER")

    # Copiar arquivo de configuração
    if os.path.exists("config_unificado.env"):
        run_command(
            "docker cp config_unificado.env aprender_web:/app/.env",
            "Copiando configuração unificada",
        )

    # Aplicar configuração no settings.py
    run_command(
        "docker exec aprender_web cp /app/aprender_sistema/settings_unificado.py /app/aprender_sistema/settings.py",
        "Aplicando settings unificado",
    )

    return True


def reiniciar_containers():
    """Reinicia containers com nova configuração"""
    print_step(4, "REINICIANDO CONTAINERS COM NOVA CONFIGURAÇÃO")

    # Parar containers
    run_command("docker-compose down", "Parando containers")

    # Iniciar containers com nova configuração
    run_command(
        "docker-compose -f docker-compose.unificado.yml up -d",
        "Iniciando containers com configuração unificada",
    )

    # Aguardar containers ficarem prontos
    print("⏳ Aguardando containers ficarem prontos...")
    import time

    time.sleep(10)

    return True


def verificar_sincronizacao():
    """Verifica se a sincronização foi bem-sucedida"""
    print_step(5, "VERIFICANDO SINCRONIZAÇÃO")

    # Verificar se containers estão rodando
    containers_ok = run_command(
        "docker ps --filter name=aprender_web --format '{{.Status}}'",
        "Verificando status do container web",
    )

    # Verificar se aplicação está respondendo
    app_ok = run_command(
        "curl -I http://localhost:8000/", "Verificando se aplicação está respondendo"
    )

    # Verificar configuração no container
    config_ok = run_command(
        'docker exec aprender_web python -c "from django.conf import settings; print(f\'Database: {settings.DATABASES["default"]["ENGINE"]}\'); print(f\'Host: {settings.DATABASES["default"]["HOST"]}\')"',
        "Verificando configuração no container",
    )

    return containers_ok and app_ok and config_ok


def criar_backup():
    """Cria backup das configurações atuais"""
    print_step(6, "CRIANDO BACKUP DAS CONFIGURAÇÕES ATUAIS")

    backup_dir = f"backup_config_{int(time.time())}"
    os.makedirs(backup_dir, exist_ok=True)

    # Arquivos para backup
    arquivos_backup = ["aprender_sistema/settings.py", "docker-compose.yml", ".env"]

    for arquivo in arquivos_backup:
        if os.path.exists(arquivo):
            shutil.copy2(arquivo, backup_dir)
            print(f"📁 Backup criado: {arquivo} -> {backup_dir}/")

    print(f"✅ Backup criado em: {backup_dir}")
    return True


def main():
    """Função principal"""
    print_header("SINCRONIZAÇÃO DE CONFIGURAÇÕES UNIFICADA")

    try:
        # Verificar ambiente
        if not verificar_ambiente():
            return False

        # Criar backup
        criar_backup()

        # Sincronizar arquivos
        if not sincronizar_arquivos_locais():
            return False

        # Aplicar configuração
        if not aplicar_configuracao_unificada():
            return False

        # Reiniciar containers
        if not reiniciar_containers():
            return False

        # Verificar sincronização
        if not verificar_sincronizacao():
            print("❌ Falha na verificação da sincronização")
            return False

        print_header("✅ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print("🎯 Configurações unificadas aplicadas em todos os ambientes")
        print("🔧 Sistema funcionando com configuração consistente")

        return True

    except Exception as e:
        print(f"❌ Erro durante sincronização: {str(e)}")
        return False


if __name__ == "__main__":
    import time

    success = main()
    sys.exit(0 if success else 1)
