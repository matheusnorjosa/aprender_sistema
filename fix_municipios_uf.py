#!/usr/bin/env python
"""
Script para corrigir as UFs incorretas dos municípios
Todos estão com UF='CE' por padrão, mas devem extrair a UF do próprio nome
"""
import os
import django
import re

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aprender_sistema.settings')
django.setup()

from core.models import Municipio

def extrair_uf_do_nome(nome_municipio):
    """
    Extrai a UF do nome do município
    Exemplos:
    - "Antônio Gonçalves - BA" → "BA"
    - "Araranguá - SC" → "SC"
    - "Atibaia - SP" → "SP"
    - "Chorozinho - CE" → "CE"
    - "Amigos do Bem" → "CE" (padrão quando não tem UF no nome)
    """
    # Padrão para capturar UF no final do nome: " - XX"
    padrao_uf = r'\s*-\s*([A-Z]{2})$'
    match = re.search(padrao_uf, nome_municipio)
    
    if match:
        return match.group(1)
    else:
        # Se não encontrar UF no nome, manter CE como padrão
        return 'CE'

def corrigir_ufs_municipios():
    """Corrige as UFs de todos os municípios"""
    
    print("=== CORREÇÃO DAS UFs DOS MUNICÍPIOS ===")
    
    municipios = Municipio.objects.all()
    total_municipios = municipios.count()
    
    print(f"Total de municípios para corrigir: {total_municipios}")
    print()
    
    correcoes = 0
    inalterados = 0
    ufs_encontradas = set()
    
    for municipio in municipios:
        uf_extraida = extrair_uf_do_nome(municipio.nome)
        ufs_encontradas.add(uf_extraida)
        
        if municipio.uf != uf_extraida:
            print(f"Corrigindo: '{municipio.nome}' | UF: '{municipio.uf}' → '{uf_extraida}'")
            municipio.uf = uf_extraida
            municipio.save()
            correcoes += 1
        else:
            inalterados += 1
    
    print(f"\n=== RESUMO DA CORREÇÃO ===")
    print(f"Municípios corrigidos: {correcoes}")
    print(f"Municípios inalterados: {inalterados}")
    print(f"Total processado: {correcoes + inalterados}")
    print(f"UFs encontradas: {sorted(list(ufs_encontradas))}")
    
    # Verificar alguns exemplos após correção
    print(f"\n=== VERIFICAÇÃO PÓS-CORREÇÃO ===")
    exemplos = ['Antônio Gonçalves - BA', 'Araranguá - SC', 'Atibaia - SP', 'Campo Largo - PR']
    
    for nome_exemplo in exemplos:
        try:
            municipio = Municipio.objects.get(nome=nome_exemplo)
            print(f"✅ {municipio.nome} | UF: {municipio.uf} | __str__(): {str(municipio)}")
        except Municipio.DoesNotExist:
            print(f"❌ {nome_exemplo} não encontrado")

def testar_extracao_uf():
    """Testa a função de extração de UF"""
    
    print("=== TESTE DA EXTRAÇÃO DE UF ===")
    
    exemplos_teste = [
        "Antônio Gonçalves - BA",
        "Araranguá - SC", 
        "Atibaia - SP",
        "Campo Largo - PR",
        "Chorozinho - CE",
        "Amigos do Bem",  # Sem UF
        "São João do Rio do Peixe - PB",
        "Balneário Rincão - SC"
    ]
    
    for exemplo in exemplos_teste:
        uf_extraida = extrair_uf_do_nome(exemplo)
        print(f"'{exemplo}' → UF: '{uf_extraida}'")

if __name__ == "__main__":
    print("Iniciando correção das UFs dos municípios...")
    print()
    
    # Primeiro testar a extração
    testar_extracao_uf()
    print()
    
    # Confirmar antes de executar
    resposta = input("Deseja prosseguir com a correção? (s/n): ")
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        corrigir_ufs_municipios()
        print("\n✅ Correção concluída!")
    else:
        print("Correção cancelada.")