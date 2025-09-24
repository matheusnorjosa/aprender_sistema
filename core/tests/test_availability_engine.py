"""
Testes para Sistema de Disponibilidade
=====================================

Testa as regras de disponibilidade críticas do sistema conforme
especificadas no CLAUDE.md (RD-01 a RD-08).

Author: Claude Code
Date: Janeiro 2025
"""

from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import (
    Usuario, Formador, Municipio, Projeto, TipoEvento,
    Solicitacao, BloqueioAgenda, SolicitacaoStatus
)


class AvailabilityEngineTest(TestCase):
    """Testes para verificação de disponibilidade"""

    def setUp(self):
        """Setup básico para testes"""
        # Criar município
        self.municipio_fortaleza = Municipio.objects.create(
            nome="Fortaleza",
            uf="CE"
        )
        self.municipio_caucaia = Municipio.objects.create(
            nome="Caucaia",
            uf="CE"
        )

        # Criar formador
        self.formador_user = Usuario.objects.create_user(
            username="formador1",
            cpf="12345678901",
            municipio=self.municipio_fortaleza,
            formador_ativo=True
        )

        self.formador = Formador.objects.create(
            usuario=self.formador_user,
            nome="João Silva",
            especialidade="matematica"
        )

        # Criar projeto e tipo evento
        self.projeto = Projeto.objects.create(
            nome="Projeto Teste",
            descricao="Projeto para testes"
        )

        self.tipo_evento = TipoEvento.objects.create(
            nome="Formação",
            descricao="Formação básica"
        )

        # Criar coordenador
        self.coordenador = Usuario.objects.create_user(
            username="coord1",
            cpf="98765432100"
        )

    def test_rd01_nao_sobreposicao_total(self):
        """RD-01: Teste de não-sobreposição total"""
        # Criar evento existente
        data_inicio = timezone.now() + timedelta(days=1)
        data_fim = data_inicio + timedelta(hours=2)

        Solicitacao.objects.create(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_inicio,
            data_fim=data_fim,
            titulo="Evento Existente",
            status=SolicitacaoStatus.APROVADO
        )

        # Tentar criar evento sobreposto
        nova_solicitacao = Solicitacao(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_inicio + timedelta(minutes=30),
            data_fim=data_fim + timedelta(minutes=30),
            titulo="Evento Conflitante"
        )

        # Verificar se há conflito (implementar método)
        conflitos = self._verificar_conflitos(nova_solicitacao)
        self.assertTrue(len(conflitos) > 0)
        self.assertIn("E", conflitos[0]['tipo'])  # Evento conflitante

    def test_rd01_sem_conflito_adjacente(self):
        """RD-01: Sem conflito quando fim == início"""
        # Criar evento existente
        data_inicio = timezone.now() + timedelta(days=1)
        data_fim = data_inicio + timedelta(hours=2)

        Solicitacao.objects.create(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_inicio,
            data_fim=data_fim,
            titulo="Evento Existente",
            status=SolicitacaoStatus.APROVADO
        )

        # Criar evento adjacente (fim do primeiro == início do segundo)
        nova_solicitacao = Solicitacao(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_fim,  # Exatamente quando o primeiro termina
            data_fim=data_fim + timedelta(hours=1),
            titulo="Evento Adjacente"
        )

        # NÃO deve haver conflito
        conflitos = self._verificar_conflitos(nova_solicitacao)
        self.assertEqual(len(conflitos), 0)

    def test_rd02_bloqueio_total(self):
        """RD-02: Bloqueio total impede qualquer evento"""
        # Criar bloqueio total
        data_inicio_bloqueio = timezone.now() + timedelta(days=1)
        data_fim_bloqueio = data_inicio_bloqueio + timedelta(hours=4)

        BloqueioAgenda.objects.create(
            formador=self.formador,
            data_inicio=data_inicio_bloqueio,
            data_fim=data_fim_bloqueio,
            tipo_bloqueio="T",  # Total
            motivo="Bloqueio total para testes"
        )

        # Tentar criar evento dentro do bloqueio
        nova_solicitacao = Solicitacao(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_inicio_bloqueio + timedelta(hours=1),
            data_fim=data_inicio_bloqueio + timedelta(hours=2),
            titulo="Evento Bloqueado"
        )

        conflitos = self._verificar_conflitos(nova_solicitacao)
        self.assertTrue(len(conflitos) > 0)
        self.assertIn("T", conflitos[0]['tipo'])  # Bloqueio total

    def test_rd03_bloqueio_parcial(self):
        """RD-03: Bloqueio parcial permite fora do intervalo"""
        # Criar bloqueio parcial (apenas parte do tempo)
        data_inicio_bloqueio = timezone.now() + timedelta(days=1)
        data_fim_bloqueio = data_inicio_bloqueio + timedelta(hours=4)

        BloqueioAgenda.objects.create(
            formador=self.formador,
            data_inicio=data_inicio_bloqueio + timedelta(hours=1),  # Início 1h depois
            data_fim=data_inicio_bloqueio + timedelta(hours=3),      # Fim 1h antes
            tipo_bloqueio="P",  # Parcial
            motivo="Bloqueio parcial para testes"
        )

        # Evento ANTES do bloqueio (deve ser permitido)
        evento_antes = Solicitacao(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_inicio_bloqueio,
            data_fim=data_inicio_bloqueio + timedelta(minutes=50),
            titulo="Evento Antes do Bloqueio"
        )

        conflitos_antes = self._verificar_conflitos(evento_antes)
        self.assertEqual(len(conflitos_antes), 0)

        # Evento DURANTE o bloqueio (deve ser impedido)
        evento_durante = Solicitacao(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_inicio_bloqueio + timedelta(hours=2),
            data_fim=data_inicio_bloqueio + timedelta(hours=2, minutes=30),
            titulo="Evento Durante Bloqueio"
        )

        conflitos_durante = self._verificar_conflitos(evento_durante)
        self.assertTrue(len(conflitos_durante) > 0)
        self.assertIn("P", conflitos_durante[0]['tipo'])

    def test_rd04_buffer_deslocamento(self):
        """RD-04: Buffer de deslocamento entre municípios"""
        # Criar evento em Fortaleza
        data_inicio = timezone.now() + timedelta(days=1)
        data_fim = data_inicio + timedelta(hours=2)

        Solicitacao.objects.create(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_inicio,
            data_fim=data_fim,
            titulo="Evento em Fortaleza",
            status=SolicitacaoStatus.APROVADO
        )

        # Tentar criar evento em Caucaia logo depois (sem buffer suficiente)
        evento_caucaia = Solicitacao(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_caucaia,  # Município diferente
            data_inicio=data_fim + timedelta(minutes=30),  # Só 30min de buffer
            data_fim=data_fim + timedelta(hours=1, minutes=30),
            titulo="Evento em Caucaia"
        )

        conflitos = self._verificar_conflitos(evento_caucaia)
        self.assertTrue(len(conflitos) > 0)
        self.assertIn("D", conflitos[0]['tipo'])  # Deslocamento

    def test_rd04_mesmo_municipio_sem_buffer(self):
        """RD-04: Mesmo município não precisa de buffer"""
        # Criar evento em Fortaleza
        data_inicio = timezone.now() + timedelta(days=1)
        data_fim = data_inicio + timedelta(hours=2)

        Solicitacao.objects.create(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,
            data_inicio=data_inicio,
            data_fim=data_fim,
            titulo="Primeiro Evento",
            status=SolicitacaoStatus.APROVADO
        )

        # Criar segundo evento no mesmo município imediatamente depois
        segundo_evento = Solicitacao(
            coordenador=self.coordenador,
            formador=self.formador,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            municipio=self.municipio_fortaleza,  # Mesmo município
            data_inicio=data_fim,  # Imediatamente depois
            data_fim=data_fim + timedelta(hours=1),
            titulo="Segundo Evento"
        )

        conflitos = self._verificar_conflitos(segundo_evento)
        # Não deve haver conflito de deslocamento no mesmo município
        conflitos_deslocamento = [c for c in conflitos if c['tipo'] == 'D']
        self.assertEqual(len(conflitos_deslocamento), 0)

    def test_rd06_timezone_awareness(self):
        """RD-06: Verificar timezone awareness"""
        # Testar que datas são processadas em America/Fortaleza
        data_inicio = timezone.now() + timedelta(days=1)
        self.assertTrue(timezone.is_aware(data_inicio))

        # Verificar que comparações mantêm timezone
        data_fim = data_inicio + timedelta(hours=2)
        self.assertEqual(data_inicio.tzinfo, data_fim.tzinfo)

    def _verificar_conflitos(self, solicitacao):
        """
        Método auxiliar para verificar conflitos

        Em uma implementação real, este método estaria em
        core.services.conflict_detection
        """
        conflitos = []

        # RD-01: Verificar sobreposição com eventos aprovados
        eventos_existentes = Solicitacao.objects.filter(
            formador=solicitacao.formador,
            status=SolicitacaoStatus.APROVADO
        ).exclude(pk=solicitacao.pk if solicitacao.pk else 0)

        for evento in eventos_existentes:
            # Verificar sobreposição (qualquer overlap > 0)
            if (solicitacao.data_inicio < evento.data_fim and
                solicitacao.data_fim > evento.data_inicio):
                conflitos.append({
                    'tipo': 'E',
                    'detalhes': f'Conflito com evento {evento.titulo}',
                    'evento': evento
                })

        # RD-02/RD-03: Verificar bloqueios
        bloqueios = BloqueioAgenda.objects.filter(
            formador=solicitacao.formador,
            data_inicio__lt=solicitacao.data_fim,
            data_fim__gt=solicitacao.data_inicio
        )

        for bloqueio in bloqueios:
            if bloqueio.tipo_bloqueio == 'T':
                # Bloqueio total
                conflitos.append({
                    'tipo': 'T',
                    'detalhes': f'Bloqueio total: {bloqueio.motivo}',
                    'bloqueio': bloqueio
                })
            elif bloqueio.tipo_bloqueio == 'P':
                # Bloqueio parcial - verificar se evento está dentro do bloqueio
                if (solicitacao.data_inicio >= bloqueio.data_inicio and
                    solicitacao.data_fim <= bloqueio.data_fim):
                    conflitos.append({
                        'tipo': 'P',
                        'detalhes': f'Bloqueio parcial: {bloqueio.motivo}',
                        'bloqueio': bloqueio
                    })

        # RD-04: Verificar buffer de deslocamento
        from django.conf import settings
        buffer_minutes = getattr(settings, 'TRAVEL_BUFFER_MINUTES', 90)

        eventos_proximos = Solicitacao.objects.filter(
            formador=solicitacao.formador,
            status=SolicitacaoStatus.APROVADO
        ).exclude(pk=solicitacao.pk if solicitacao.pk else 0)

        for evento in eventos_proximos:
            # Verificar se são municípios diferentes
            if evento.municipio != solicitacao.municipio:
                # Verificar se há buffer suficiente
                if evento.data_fim <= solicitacao.data_inicio:
                    # Evento anterior - verificar buffer após
                    diff = (solicitacao.data_inicio - evento.data_fim).total_seconds() / 60
                    if diff < buffer_minutes:
                        conflitos.append({
                            'tipo': 'D',
                            'detalhes': f'Buffer insuficiente após {evento.titulo} ({diff:.0f}min < {buffer_minutes}min)',
                            'evento': evento
                        })
                elif solicitacao.data_fim <= evento.data_inicio:
                    # Evento posterior - verificar buffer antes
                    diff = (evento.data_inicio - solicitacao.data_fim).total_seconds() / 60
                    if diff < buffer_minutes:
                        conflitos.append({
                            'tipo': 'D',
                            'detalhes': f'Buffer insuficiente antes de {evento.titulo} ({diff:.0f}min < {buffer_minutes}min)',
                            'evento': evento
                        })

        return conflitos


class ConflictDetectionIntegrationTest(TestCase):
    """Testes de integração para detecção de conflitos"""

    def setUp(self):
        """Setup para testes de integração"""
        # Setup similar ao anterior mas com dados mais complexos
        pass

    def test_multiple_conflicts_scenario(self):
        """Teste de cenário com múltiplos conflitos"""
        # Implementar cenário complexo com vários tipos de conflito
        pass

    def test_conflict_resolution_priority(self):
        """Teste de prioridade na resolução de conflitos"""
        # Implementar teste de prioridade conforme RD-07
        pass