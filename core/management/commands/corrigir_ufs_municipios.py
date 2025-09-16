"""
Comando Django para corrigir as UFs incorretas dos municípios
Todos estão com UF='CE' por padrão, mas devem extrair a UF do próprio nome
"""

import re
from django.core.management.base import BaseCommand
from core.models import Municipio


class Command(BaseCommand):
    help = 'Corrige as UFs incorretas dos municípios'

    def extrair_uf_do_nome(self, nome_municipio):
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

    def handle(self, *args, **options):
        self.stdout.write("=== CORREÇÃO DAS UFs DOS MUNICÍPIOS ===")
        
        municipios = Municipio.objects.all()
        total_municipios = municipios.count()
        
        self.stdout.write(f"Total de municípios para corrigir: {total_municipios}")
        
        correcoes = 0
        inalterados = 0
        ufs_encontradas = set()
        
        for municipio in municipios:
            uf_extraida = self.extrair_uf_do_nome(municipio.nome)
            ufs_encontradas.add(uf_extraida)
            
            if municipio.uf != uf_extraida:
                self.stdout.write(f"Corrigindo: '{municipio.nome}' | UF: '{municipio.uf}' → '{uf_extraida}'")
                municipio.uf = uf_extraida
                municipio.save()
                correcoes += 1
            else:
                inalterados += 1
        
        self.stdout.write(f"\n=== RESUMO DA CORREÇÃO ===")
        self.stdout.write(f"Municípios corrigidos: {correcoes}")
        self.stdout.write(f"Municípios inalterados: {inalterados}")
        self.stdout.write(f"Total processado: {correcoes + inalterados}")
        self.stdout.write(f"UFs encontradas: {sorted(list(ufs_encontradas))}")
        
        # Verificar alguns exemplos após correção
        self.stdout.write(f"\n=== VERIFICAÇÃO PÓS-CORREÇÃO ===")
        exemplos = ['Antônio Gonçalves - BA', 'Araranguá - SC', 'Atibaia - SP', 'Campo Largo - PR']
        
        for nome_exemplo in exemplos:
            try:
                municipio = Municipio.objects.get(nome=nome_exemplo)
                self.stdout.write(f"✅ {municipio.nome} | UF: {municipio.uf} | __str__(): {str(municipio)}")
            except Municipio.DoesNotExist:
                self.stdout.write(f"❌ {nome_exemplo} não encontrado")
        
        self.stdout.write(self.style.SUCCESS("\n✅ Correção concluída!"))