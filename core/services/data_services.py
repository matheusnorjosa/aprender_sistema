"""
Data Services - Single Source of Truth para todas as queries
Centraliza lógica de negócio e elimina duplicação de código
"""

from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import Group
from typing import Optional, List, Dict, Any


class BaseService:
    """Classe base para todos os services"""

    cache_timeout = 300  # 5 minutos padrão

    @classmethod
    def get_cache_key(cls, *args):
        """Gera chave de cache consistente"""
        return f"{cls.__name__}:{':'.join(map(str, args))}"

    @classmethod
    def clear_cache(cls, *args):
        """Limpa cache específico"""
        cache_key = cls.get_cache_key(*args)
        cache.delete(cache_key)


class UsuarioService(BaseService):
    """
    Service centralizado para todas as operações com Usuario
    FONTE ÚNICA DE VERDADE - substitui queries ad-hoc
    """

    @classmethod
    def get_optimized_queryset(cls):
        """QuerySet base otimizado para Usuario"""
        from core.models import Usuario
        return Usuario.objects.select_related('setor', 'municipio', 'area_atuacao')

    @classmethod
    def ativos(cls):
        """Usuários ativos otimizados"""
        return cls.get_optimized_queryset().filter(is_active=True)

    @classmethod
    def por_cargo(cls, cargo: str):
        """Usuários por cargo específico"""
        return cls.ativos().filter(cargo=cargo)

    @classmethod
    def por_setor(cls, setor):
        """Usuários por setor específico"""
        return cls.ativos().filter(setor=setor)

    @classmethod
    def por_municipio(cls, municipio):
        """Usuários por município específico"""
        return cls.ativos().filter(municipio=municipio)


class FormadorService(BaseService):
    """
    Service para Formadores - FONTE ÚNICA UNIFICADA
    Substitui completamente o modelo Formador separado
    """

    @classmethod
    def get_formadores_queryset(cls):
        """QuerySet otimizado para formadores"""
        return UsuarioService.ativos().filter(
            formador_ativo=True,
            groups__name='formador'
        ).distinct().prefetch_related('groups')

    @classmethod
    def todos_formadores(cls) -> 'QuerySet':
        """Todos os formadores ativos (fonte única)"""
        cache_key = cls.get_cache_key('todos_formadores')
        result = cache.get(cache_key)

        if result is None:
            result = list(cls.get_formadores_queryset())
            cache.set(cache_key, result, cls.cache_timeout)

        return result

    @classmethod
    def por_area(cls, area: Optional[str] = None):
        """Formadores por área de atuação"""
        qs = cls.get_formadores_queryset()
        if area:
            qs = qs.filter(area_atuacao__name=area)
        return qs

    @classmethod
    def por_municipio(cls, municipio=None):
        """Formadores por município"""
        qs = cls.get_formadores_queryset()
        if municipio:
            qs = qs.filter(municipio=municipio)
        return qs

    @classmethod
    def com_eventos_realizados(cls):
        """Formadores com eventos realizados (otimizado)"""
        return cls.get_formadores_queryset().prefetch_related(
            Prefetch(
                'solicitacoes_como_formador',
                queryset=None  # Será definido quando importado
            )
        )

    @classmethod
    def estatisticas_formador(cls, formador_id: str) -> Dict[str, Any]:
        """Estatísticas completas de um formador"""
        cache_key = cls.get_cache_key('stats_formador', formador_id)
        result = cache.get(cache_key)

        if result is None:
            from core.models import Usuario, FormadoresSolicitacao

            try:
                formador = Usuario.objects.get(id=formador_id, formador_ativo=True)

                # Estatísticas básicas
                total_eventos = FormadoresSolicitacao.objects.filter(
                    usuario=formador
                ).count()

                eventos_realizados = FormadoresSolicitacao.objects.filter(
                    usuario=formador,
                    solicitacao__status='Aprovado'
                ).count()

                result = {
                    'nome': formador.nome_completo,
                    'email': formador.email,
                    'area_atuacao': formador.area_atuacao_display,
                    'municipio': formador.municipio.nome if formador.municipio else None,
                    'total_eventos': total_eventos,
                    'eventos_realizados': eventos_realizados,
                    'eventos_pendentes': total_eventos - eventos_realizados,
                    'ativo': formador.formador_ativo,
                }

                cache.set(cache_key, result, cls.cache_timeout)

            except Exception:
                result = {}

        return result


class CoordinatorService(BaseService):
    """
    Service para Coordenadores - Diferenciação por vinculação
    Implementa lógica específica de coordenadores
    """

    @classmethod
    def get_coordenadores_queryset(cls):
        """QuerySet otimizado para coordenadores"""
        return UsuarioService.por_cargo('coordenador').prefetch_related(
            'groups',
            'solicitacoes_criadas'
        )

    @classmethod
    def todos_coordenadores(cls):
        """Todos os coordenadores"""
        return cls.get_coordenadores_queryset()

    @classmethod
    def superintendencia(cls):
        """Coordenadores da superintendência"""
        return cls.get_coordenadores_queryset().filter(
            setor__vinculado_superintendencia=True
        )

    @classmethod
    def outros_setores(cls):
        """Coordenadores de outros setores"""
        return cls.get_coordenadores_queryset().filter(
            setor__vinculado_superintendencia=False
        )

    @classmethod
    def por_vinculacao(cls, superintendencia_only: Optional[bool] = None):
        """
        Coordenadores filtrados por vinculação

        Args:
            superintendencia_only:
                - True: apenas superintendência
                - False: apenas outros setores
                - None: todos
        """
        qs = cls.get_coordenadores_queryset()

        if superintendencia_only is True:
            qs = qs.filter(setor__vinculado_superintendencia=True)
        elif superintendencia_only is False:
            qs = qs.filter(setor__vinculado_superintendencia=False)

        return qs

    @classmethod
    def estatisticas_coordenador(cls, coordenador_id: str) -> Dict[str, Any]:
        """Estatísticas completas de um coordenador"""
        cache_key = cls.get_cache_key('stats_coord', coordenador_id)
        result = cache.get(cache_key)

        if result is None:
            from core.models import Usuario, Solicitacao

            try:
                coordenador = Usuario.objects.get(id=coordenador_id, cargo='coordenador')

                solicitacoes = Solicitacao.objects.filter(usuario_solicitante=coordenador)

                result = {
                    'nome': coordenador.nome_completo,
                    'setor': coordenador.setor_nome,
                    'vinculacao': 'Superintendência' if coordenador.setor and coordenador.setor.vinculado_superintendencia else 'Outros Setores',
                    'total_solicitacoes': solicitacoes.count(),
                    'aprovadas': solicitacoes.filter(status='Aprovado').count(),
                    'pendentes': solicitacoes.filter(status='Pendente').count(),
                    'reprovadas': solicitacoes.filter(status='Reprovado').count(),
                }

                cache.set(cache_key, result, cls.cache_timeout)

            except Exception:
                result = {}

        return result


class DashboardService(BaseService):
    """
    Service para Dashboard - Queries otimizadas e padronizadas
    Centraliza todas as queries do dashboard executivo
    """

    @classmethod
    def get_estatisticas_gerais(cls) -> Dict[str, Any]:
        """Estatísticas gerais do sistema"""
        cache_key = cls.get_cache_key('stats_gerais')
        result = cache.get(cache_key)

        if result is None:
            from core.models import Usuario, Solicitacao, Municipio, Projeto

            agora = timezone.now()
            inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

            result = {
                'usuarios_total': Usuario.objects.filter(is_active=True).count(),
                'formadores_ativos': FormadorService.get_formadores_queryset().count(),
                'coordenadores_total': CoordinatorService.get_coordenadores_queryset().count(),
                'coordenadores_superintendencia': CoordinatorService.superintendencia().count(),
                'coordenadores_outros_setores': CoordinatorService.outros_setores().count(),
                'municipios_ativos': Municipio.objects.filter(ativo=True).count(),
                'projetos_ativos': Projeto.objects.filter(ativo=True).count(),
                'solicitacoes_ano': Solicitacao.objects.filter(data_inicio__gte=inicio_ano).count(),
                'solicitacoes_aprovadas_ano': Solicitacao.objects.filter(
                    data_inicio__gte=inicio_ano,
                    status='Aprovado'
                ).count(),
                'data_atualizacao': agora.isoformat(),
            }

            # Calcular taxa de aprovação
            total_ano = result['solicitacoes_ano']
            aprovadas_ano = result['solicitacoes_aprovadas_ano']
            result['taxa_aprovacao_ano'] = round(
                (aprovadas_ano / total_ano * 100) if total_ano > 0 else 0, 1
            )

            cache.set(cache_key, result, cls.cache_timeout)

        return result

    @classmethod
    def get_coordenadores_por_municipio(cls) -> List[Dict[str, Any]]:
        """
        Dados dos coordenadores agrupados por município
        OTIMIZADO para dashboard executivo
        """
        cache_key = cls.get_cache_key('coords_municipio')
        result = cache.get(cache_key)

        if result is None:
            from core.models import Solicitacao

            # Query unificada e otimizada - CORRIGIDA para evitar duplicação
            solicitacoes_por_coordenador = (
                Solicitacao.objects
                .values(
                    'municipio__nome',
                    'municipio__uf',
                    'usuario_solicitante__first_name',
                    'usuario_solicitante__last_name',
                    'usuario_solicitante__username',
                    'usuario_solicitante__cargo',
                    'usuario_solicitante__setor__nome',
                    'usuario_solicitante__setor__vinculado_superintendencia'
                )
                .annotate(total_eventos=Count('id'))
                .order_by('municipio__uf', 'municipio__nome', '-total_eventos')
            )

            # Agrupar por município
            municipios = {}
            totais = {
                'coordenadores': 0,
                'eventos': 0,
                'superintendencia': 0,
                'outros_setores': 0
            }

            for item in solicitacoes_por_coordenador:
                municipio_nome = item['municipio__nome']
                municipio_uf = item['municipio__uf']

                # Limpar nome do município
                if municipio_uf and f" - {municipio_uf}" in municipio_nome:
                    municipio_nome = municipio_nome.replace(f" - {municipio_uf}", "")

                municipio_key = f"{municipio_nome} - {municipio_uf}"

                # Criar município se não existe
                if municipio_key not in municipios:
                    municipios[municipio_key] = {
                        'municipio': municipio_nome,
                        'uf': municipio_uf,
                        'coordenadores': [],
                        'total_eventos': 0,
                        'total_coordenadores': 0
                    }

                # Determinar tipo de coordenador
                cargo = item['usuario_solicitante__cargo']
                vinculado_super = item['usuario_solicitante__setor__vinculado_superintendencia']

                if cargo == 'coordenador' and vinculado_super:
                    tipo_coordenador = 'superintendencia'
                    vinculacao = 'Superintendência'
                    totais['superintendencia'] += 1
                elif cargo == 'coordenador' and not vinculado_super:
                    tipo_coordenador = 'outros_setores'
                    vinculacao = item['usuario_solicitante__setor__nome'] or 'Outros Setores'
                    totais['outros_setores'] += 1
                else:
                    tipo_coordenador = 'outro_cargo'
                    vinculacao = 'N/A'

                # Nome do coordenador
                first_name = item['usuario_solicitante__first_name'] or ''
                last_name = item['usuario_solicitante__last_name'] or ''
                nome = f"{first_name} {last_name}".strip()
                if not nome:
                    nome = item['usuario_solicitante__username']

                # Verificar se coordenador já existe no município
                username = item['usuario_solicitante__username']
                coordenador_existente = None
                
                for coord in municipios[municipio_key]['coordenadores']:
                    if coord['username'] == username:
                        coordenador_existente = coord
                        break
                
                if coordenador_existente:
                    # Atualizar eventos do coordenador existente
                    coordenador_existente['eventos'] += item['total_eventos']
                else:
                    # Adicionar novo coordenador
                    municipios[municipio_key]['coordenadores'].append({
                        'nome': nome,
                        'username': username,
                        'eventos': item['total_eventos'],
                        'tipo_coordenador': tipo_coordenador,
                        'vinculacao': vinculacao
                    })
                    municipios[municipio_key]['total_coordenadores'] += 1
                    totais['coordenadores'] += 1

                # Atualizar totais
                municipios[municipio_key]['total_eventos'] += item['total_eventos']
                totais['eventos'] += item['total_eventos']

            # Ordenar coordenadores por eventos
            for municipio_data in municipios.values():
                municipio_data['coordenadores'].sort(key=lambda x: x['eventos'], reverse=True)

            # Converter para lista ordenada
            municipios_lista = sorted(
                municipios.values(),
                key=lambda x: (-x['total_eventos'], x['uf'], x['municipio'])
            )

            result = {
                'municipios': municipios_lista,
                'estatisticas': totais,
                'diferenciacao': {
                    'superintendencia': {
                        'total': totais['superintendencia'],
                        'descricao': 'Coordenadores vinculados à superintendência'
                    },
                    'outros_setores': {
                        'total': totais['outros_setores'],
                        'descricao': 'Coordenadores de outros setores'
                    }
                }
            }

            cache.set(cache_key, result, cls.cache_timeout)

        return result


class MunicipioService(BaseService):
    """
    Service para Municípios - Queries otimizadas
    """

    @classmethod
    def ativos(cls):
        """Municípios ativos otimizados"""
        from core.models import Municipio
        return Municipio.objects.filter(ativo=True).order_by('nome', 'uf')

    @classmethod
    def por_uf(cls, uf: str):
        """Municípios por UF"""
        return cls.ativos().filter(uf=uf)

    @classmethod
    def com_eventos(cls):
        """Municípios que têm eventos"""
        return cls.ativos().filter(solicitacao__isnull=False).distinct()

    @classmethod
    def estatisticas_municipio(cls, municipio_id: str) -> Dict[str, Any]:
        """Estatísticas de um município"""
        cache_key = cls.get_cache_key('stats_municipio', municipio_id)
        result = cache.get(cache_key)

        if result is None:
            from core.models import Municipio, Solicitacao

            try:
                municipio = Municipio.objects.get(id=municipio_id)
                solicitacoes = Solicitacao.objects.filter(municipio=municipio)

                result = {
                    'nome': municipio.nome,
                    'uf': municipio.uf,
                    'total_eventos': solicitacoes.count(),
                    'eventos_aprovados': solicitacoes.filter(status='Aprovado').count(),
                    'eventos_pendentes': solicitacoes.filter(status='Pendente').count(),
                    'coordenadores_unicos': solicitacoes.values('usuario_solicitante').distinct().count(),
                }

                cache.set(cache_key, result, cls.cache_timeout)

            except Exception:
                result = {}

        return result