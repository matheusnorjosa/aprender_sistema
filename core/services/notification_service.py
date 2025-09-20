# core/services/notification_service.py
"""
Serviço de notificações com diferenciação de coordenadores por vinculação à superintendência.
"""

from django.db import transaction
from django.utils import timezone
from ..models import Usuario, Notificacao, LogComunicacao


class NotificationService:
    """
    Serviço para envio de notificações diferenciadas por tipo de coordenador.

    Utiliza os novos métodos do modelo Usuario para separar:
    - Coordenadores da Superintendência
    - Coordenadores de outros setores
    """

    @staticmethod
    def notificar_coordenadores_superintendencia(
        titulo, mensagem, tipo_notificacao="sistema_atualizacao", link_acao=None, entidade_id=None
    ):
        """
        Envia notificação apenas para coordenadores vinculados à superintendência.

        Args:
            titulo (str): Título da notificação
            mensagem (str): Mensagem da notificação
            tipo_notificacao (str): Tipo da notificação (choices do modelo)
            link_acao (str): URL para ação relacionada
            entidade_id (UUID): ID da entidade relacionada

        Returns:
            int: Número de notificações enviadas
        """
        coordenadores = Usuario.get_coordenadores_superintendencia()

        with transaction.atomic():
            notificacoes_criadas = []

            for coordenador in coordenadores:
                notificacao = Notificacao.objects.create(
                    usuario=coordenador,
                    tipo=tipo_notificacao,
                    titulo=titulo,
                    mensagem=mensagem,
                    link_acao=link_acao,
                    entidade_relacionada_id=entidade_id
                )
                notificacoes_criadas.append(notificacao)

                # Log da comunicação
                LogComunicacao.objects.create(
                    usuario_destinatario=coordenador,
                    grupo_destinatario="coordenador_superintendencia",
                    tipo_comunicacao="notificacao_sistema",
                    assunto=titulo,
                    conteudo=mensagem,
                    status_envio="enviado",
                    enviado_em=timezone.now(),
                    entidade_relacionada_id=entidade_id,
                    entidade_relacionada_tipo="notificacao"
                )

        return len(notificacoes_criadas)

    @staticmethod
    def notificar_coordenadores_outros_setores(
        titulo, mensagem, tipo_notificacao="sistema_atualizacao", link_acao=None, entidade_id=None
    ):
        """
        Envia notificação apenas para coordenadores de outros setores (não-superintendência).

        Args:
            titulo (str): Título da notificação
            mensagem (str): Mensagem da notificação
            tipo_notificacao (str): Tipo da notificação
            link_acao (str): URL para ação relacionada
            entidade_id (UUID): ID da entidade relacionada

        Returns:
            int: Número de notificações enviadas
        """
        coordenadores = Usuario.get_coordenadores_outros_setores()

        with transaction.atomic():
            notificacoes_criadas = []

            for coordenador in coordenadores:
                notificacao = Notificacao.objects.create(
                    usuario=coordenador,
                    tipo=tipo_notificacao,
                    titulo=titulo,
                    mensagem=mensagem,
                    link_acao=link_acao,
                    entidade_relacionada_id=entidade_id
                )
                notificacoes_criadas.append(notificacao)

                # Log da comunicação
                LogComunicacao.objects.create(
                    usuario_destinatario=coordenador,
                    grupo_destinatario="coordenador_outros_setores",
                    tipo_comunicacao="notificacao_sistema",
                    assunto=titulo,
                    conteudo=mensagem,
                    status_envio="enviado",
                    enviado_em=timezone.now(),
                    entidade_relacionada_id=entidade_id,
                    entidade_relacionada_tipo="notificacao"
                )

        return len(notificacoes_criadas)

    @staticmethod
    def notificar_todos_coordenadores(
        titulo, mensagem, tipo_notificacao="sistema_atualizacao", link_acao=None, entidade_id=None
    ):
        """
        Envia notificação para todos os coordenadores, independente da vinculação.

        Args:
            titulo (str): Título da notificação
            mensagem (str): Mensagem da notificação
            tipo_notificacao (str): Tipo da notificação
            link_acao (str): URL para ação relacionada
            entidade_id (UUID): ID da entidade relacionada

        Returns:
            dict: Estatísticas do envio
        """
        coordenadores_super = Usuario.get_coordenadores_superintendencia()
        coordenadores_outros = Usuario.get_coordenadores_outros_setores()

        with transaction.atomic():
            total_super = 0
            total_outros = 0

            # Notificar superintendência
            for coordenador in coordenadores_super:
                Notificacao.objects.create(
                    usuario=coordenador,
                    tipo=tipo_notificacao,
                    titulo=titulo,
                    mensagem=mensagem,
                    link_acao=link_acao,
                    entidade_relacionada_id=entidade_id
                )

                LogComunicacao.objects.create(
                    usuario_destinatario=coordenador,
                    grupo_destinatario="coordenador_superintendencia",
                    tipo_comunicacao="notificacao_sistema",
                    assunto=titulo,
                    conteudo=mensagem,
                    status_envio="enviado",
                    enviado_em=timezone.now(),
                    entidade_relacionada_id=entidade_id,
                    entidade_relacionada_tipo="notificacao"
                )
                total_super += 1

            # Notificar outros setores
            for coordenador in coordenadores_outros:
                Notificacao.objects.create(
                    usuario=coordenador,
                    tipo=tipo_notificacao,
                    titulo=titulo,
                    mensagem=mensagem,
                    link_acao=link_acao,
                    entidade_relacionada_id=entidade_id
                )

                LogComunicacao.objects.create(
                    usuario_destinatario=coordenador,
                    grupo_destinatario="coordenador_outros_setores",
                    tipo_comunicacao="notificacao_sistema",
                    assunto=titulo,
                    conteudo=mensagem,
                    status_envio="enviado",
                    enviado_em=timezone.now(),
                    entidade_relacionada_id=entidade_id,
                    entidade_relacionada_tipo="notificacao"
                )
                total_outros += 1

        return {
            'total': total_super + total_outros,
            'superintendencia': total_super,
            'outros_setores': total_outros
        }

    @staticmethod
    def notificar_por_vinculacao(
        superintendencia_only, titulo, mensagem, tipo_notificacao="sistema_atualizacao",
        link_acao=None, entidade_id=None
    ):
        """
        Método unificado para notificar coordenadores baseado na vinculação.

        Args:
            superintendencia_only (bool):
                - True: apenas superintendência
                - False: apenas outros setores
                - None: todos os coordenadores
            titulo (str): Título da notificação
            mensagem (str): Mensagem da notificação
            tipo_notificacao (str): Tipo da notificação
            link_acao (str): URL para ação relacionada
            entidade_id (UUID): ID da entidade relacionada

        Returns:
            dict: Resultado do envio
        """
        if superintendencia_only is True:
            count = NotificationService.notificar_coordenadores_superintendencia(
                titulo, mensagem, tipo_notificacao, link_acao, entidade_id
            )
            return {'tipo': 'superintendencia', 'total': count}

        elif superintendencia_only is False:
            count = NotificationService.notificar_coordenadores_outros_setores(
                titulo, mensagem, tipo_notificacao, link_acao, entidade_id
            )
            return {'tipo': 'outros_setores', 'total': count}

        else:
            stats = NotificationService.notificar_todos_coordenadores(
                titulo, mensagem, tipo_notificacao, link_acao, entidade_id
            )
            return {'tipo': 'todos', **stats}

    @staticmethod
    def get_estatisticas_coordenadores():
        """
        Retorna estatísticas dos coordenadores por vinculação.

        Returns:
            dict: Estatísticas detalhadas
        """
        coordenadores_super = Usuario.get_coordenadores_superintendencia()
        coordenadores_outros = Usuario.get_coordenadores_outros_setores()

        return {
            'superintendencia': {
                'total': coordenadores_super.count(),
                'coordenadores': [
                    {
                        'id': str(c.id),
                        'nome': c.nome_completo,
                        'setor': c.setor_nome,
                        'email': c.email
                    }
                    for c in coordenadores_super
                ]
            },
            'outros_setores': {
                'total': coordenadores_outros.count(),
                'coordenadores': [
                    {
                        'id': str(c.id),
                        'nome': c.nome_completo,
                        'setor': c.setor_nome,
                        'email': c.email
                    }
                    for c in coordenadores_outros
                ]
            }
        }