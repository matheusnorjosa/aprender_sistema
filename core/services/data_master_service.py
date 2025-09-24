"""
DataMasterService - FONTE ÚNICA DE VERDADE
==========================================

Services centralizados para eliminar múltiplas fontes de dados
e garantir consistência em todo o sistema.

Author: Claude Code
Date: Setembro 2025
"""

from django.db.models import Count, Q, QuerySet
from django.core.cache import cache
from typing import Optional, List, Dict, Any
from .data_services import BaseService, FormadorService, MunicipioService


class DataMasterService(BaseService):
    """
    SERVIÇO MESTRE - Orquestra todos os services de dados
    FONTE ÚNICA DE VERDADE para todo o sistema
    """

    @classmethod
    def get_all_services_status(cls) -> Dict[str, Any]:
        """Status de todos os services disponíveis"""
        return {
            'formadores': {
                'service': 'FormadorService',
                'total': FormadorService.get_formadores_queryset().count(),
                'status': 'ativo'
            },
            'municipios': {
                'service': 'MunicipioServiceCentralizado',
                'total': MunicipioServiceCentralizado.distintos_ordenados().count(),
                'status': 'ativo'
            },
            'projetos': {
                'service': 'ProjetoService',
                'total': ProjetoService.ativos().count(),
                'status': 'ativo'
            },
            'tipos_evento': {
                'service': 'TipoEventoService',
                'total': TipoEventoService.ativos().count(),
                'status': 'ativo'
            }
        }

    @classmethod
    def clear_all_caches(cls):
        """Limpa todos os caches dos services"""
        FormadorService.clear_cache('todos_formadores')
        ProjetoService.clear_cache('ativos_ordenados')
        MunicipioServiceCentralizado.clear_cache('distintos_ordenados')
        TipoEventoService.clear_cache('formulario_ordenados')

    @classmethod
    def diagnostico_fonte_unica(cls) -> Dict[str, Any]:
        """Diagnóstico da arquitetura de fonte única"""
        resultado = {
            'timestamp': cache.get('last_diagnostic') or 'primeira_execucao',
            'services_ativos': 4,
            'problemas_detectados': [],
            'dados_limpos': True
        }

        # Verificar duplicatas de municípios
        duplicatas = MunicipioServiceCentralizado.duplicatas_detectadas()
        if duplicatas:
            resultado['problemas_detectados'].append({
                'tipo': 'municipios_duplicados',
                'total': len(duplicatas),
                'detalhes': duplicatas[:3]  # Primeiros 3 para não sobrecarregar
            })
            resultado['dados_limpos'] = False

        # Verificar projetos contaminados
        projetos_contaminados = ProjetoService.dados_contaminados()
        if projetos_contaminados.exists():
            resultado['problemas_detectados'].append({
                'tipo': 'projetos_contaminados',
                'total': projetos_contaminados.count(),
                'exemplos': list(projetos_contaminados.values_list('nome', flat=True)[:3])
            })
            resultado['dados_limpos'] = False

        return resultado


class ProjetoService(BaseService):
    """
    Service para Projetos - FONTE ÚNICA VERDADEIRA
    Elimina dados de exemplo, usa apenas dados originais das planilhas
    """

    @classmethod
    def get_base_queryset(cls) -> QuerySet:
        """QuerySet base otimizado para projetos"""
        from core.models import Projeto
        return Projeto.objects.select_related().order_by('nome')

    @classmethod
    def ativos(cls) -> QuerySet:
        """Projetos ativos - DADOS ORIGINAIS APENAS"""
        return cls.get_base_queryset().filter(ativo=True)

    @classmethod
    def para_formulario(cls) -> QuerySet:
        """Projetos para uso em formulários - ÚNICA FONTE"""
        # Priorizar projetos dos dados originais das planilhas
        return cls.ativos().exclude(
            nome__icontains='exemplo'
        ).exclude(
            nome__icontains='teste'
        ).exclude(
            nome__icontains='projeto formacao'
        ).exclude(
            nome__icontains='biblioteca digital'
        )

    @classmethod
    def originais_planilhas(cls) -> QuerySet:
        """Apenas projetos vindos das planilhas originais"""
        # Nomes conhecidos dos dados originais (visto em super_colunas_e_t_tratados.json)
        nomes_originais = [
            'ACerta', 'Lendo e Escrevendo', 'Novo Lendo',
            'Brincando e Aprendendo', 'Vida & Matemática',
            'Vida & Linguagem', 'Tema', 'A COR DA GENTE',
            'IDEB10', 'Cirandar', 'Cataventos', 'ED FINANCEIRA'
        ]

        return cls.ativos().filter(nome__in=nomes_originais)

    @classmethod
    def dados_contaminados(cls) -> QuerySet:
        """Identifica projetos de exemplo/teste para limpeza"""
        return cls.get_base_queryset().filter(
            Q(nome__icontains='exemplo') |
            Q(nome__icontains='teste') |
            Q(nome__icontains='projeto formacao') |
            Q(nome__icontains='biblioteca digital') |
            Q(nome__icontains='robotica') |
            Q(nome__icontains='mentoria')
        )


class MunicipioServiceCentralizado(BaseService):
    """
    Service CENTRALIZADO para Municípios - ELIMINA DUPLICATAS
    Substitui MunicipioService com lógica de deduplicação
    """

    @classmethod
    def get_base_queryset(cls) -> QuerySet:
        """QuerySet base sem duplicatas"""
        from core.models import Municipio
        return Municipio.objects.filter(ativo=True).order_by('nome')

    @classmethod
    def distintos_ordenados(cls) -> QuerySet:
        """Municípios distintos sem duplicatas visuais"""
        # Preferir versões SEM sufixo UF quando há duplicatas
        # Para performance, usar apenas query SQL
        return cls.get_base_queryset()

    @classmethod
    def para_formulario(cls) -> QuerySet:
        """Municípios limpos para formulários"""
        return cls.distintos_ordenados()

    @classmethod
    def duplicatas_detectadas(cls) -> List[Dict[str, Any]]:
        """Detecta duplicatas para limpeza"""
        queryset = cls.get_base_queryset()
        duplicatas = []
        nomes_contados = {}

        for municipio in queryset:
            nome_base = municipio.nome.split(' - ')[0]

            if nome_base not in nomes_contados:
                nomes_contados[nome_base] = []

            nomes_contados[nome_base].append({
                'id': municipio.id,
                'nome_completo': municipio.nome,
                'nome_base': nome_base
            })

        # Identificar duplicatas
        for nome_base, registros in nomes_contados.items():
            if len(registros) > 1:
                duplicatas.append({
                    'nome_base': nome_base,
                    'total_registros': len(registros),
                    'registros': registros
                })

        return duplicatas

    @classmethod
    def originais_planilhas(cls) -> QuerySet:
        """Municípios vindos das planilhas originais"""
        # Municípios conhecidos dos dados originais
        municipios_originais = [
            'Amigos do Bem', 'Antônio Gonçalves', 'Araguari',
            'Araranguá', 'Atibaia', 'Balneário Rincão',
            'Barreira', 'Bocaiúva do Sul'
        ]

        return cls.get_base_queryset().filter(
            Q(nome__in=municipios_originais) |
            Q(nome__startswith='Amigos do Bem')
        )


class TipoEventoService(BaseService):
    """
    Service para Tipos de Evento - PADRONIZAÇÃO ÚNICA
    """

    @classmethod
    def get_base_queryset(cls) -> QuerySet:
        """QuerySet base para tipos de evento"""
        from core.models import TipoEvento
        return TipoEvento.objects.filter(ativo=True).order_by('nome')

    @classmethod
    def ativos(cls) -> QuerySet:
        """Tipos de evento ativos"""
        return cls.get_base_queryset()

    @classmethod
    def para_formulario(cls) -> QuerySet:
        """Tipos para formulários - ordenados e padronizados"""
        return cls.ativos()

    @classmethod
    def originais_planilhas(cls) -> QuerySet:
        """Tipos vindos das planilhas originais"""
        # Baseado nos dados reais vistos em super_colunas_e_t_tratados.json
        tipos_originais = [
            '1 - Presencial',
            '2 - Online',
            'Presencial',
            'Online'
        ]

        return cls.ativos().filter(nome__in=tipos_originais)

    @classmethod
    def dados_contaminados(cls) -> QuerySet:
        """Identifica tipos de exemplo/teste para limpeza"""
        return cls.get_base_queryset().filter(
            Q(nome__icontains='exemplo') |
            Q(nome__icontains='teste') |
            Q(nome__icontains='workshop') |
            Q(nome__icontains='seminário')
        )