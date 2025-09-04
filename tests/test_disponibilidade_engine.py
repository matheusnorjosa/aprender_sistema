"""
Testes obrigatórios para o Motor de Disponibilidade E,M,D,P,T,X

Casos de Teste Padronizados (CLAUDE.md):
- test_conflict_overlap_total
- test_conflict_overlap_partial  
- test_no_conflict_adjacent_end_equals_start
- test_block_total_T_prevents_any_event
- test_block_partial_P_prevents_inside_allows_outside
- test_travel_buffer_between_cities_required
- test_same_city_allows_zero_buffer
- test_daily_capacity_M_exceeded
- test_multi_formador_any_conflict_blocks
- test_timezone_aware_fortaleza_localtime
- test_conflict_messages_include_codes_and_intervals
"""
import pytest
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from core.models import (
    Formador, Municipio, Solicitacao, DisponibilidadeFormadores,
    TipoEvento, Projeto
)
from core.services.disponibilidade_engine import (
    DisponibilidadeEngine, create_availability_engine, check_formador_availability
)


class DisponibilidadeEngineTest(TestCase):
    """Testes do Motor de Disponibilidade"""
    
    def setUp(self):
        """Configuração inicial para todos os testes"""
        # Timezone Fortaleza
        self.fortaleza_tz = timezone.get_current_timezone()
        
        # Criar municípios para testes
        self.municipio_fortaleza = Municipio.objects.create(nome="Fortaleza", ativo=True)
        self.municipio_sobral = Municipio.objects.create(nome="Sobral", ativo=True)
        
        # Criar projeto e tipo evento
        self.projeto = Projeto.objects.create(nome="ACERTA", ativo=True)
        self.tipo_evento = TipoEvento.objects.create(nome="Presencial", ativo=True)
        
        # Criar formadores para testes
        self.formador_1 = Formador.objects.create(
            nome="João Silva",
            email="joao@test.com",
            ativo=True
        )
        
        self.formador_2 = Formador.objects.create(
            nome="Maria Santos",
            email="maria@test.com", 
            ativo=True
        )
        
        # Motor de disponibilidade com configurações de teste
        self.engine = DisponibilidadeEngine(
            travel_buffer_minutes=60,  # 1 hora para testes
            daily_hour_limit=6         # 6 horas para testes
        )
        
        # Horários padrão para testes
        self.base_date = timezone.make_aware(
            datetime(2025, 1, 15, 8, 0),  # 15/01/2025 08:00
            self.fortaleza_tz
        )
    
    def _create_event(self, formador, inicio, fim, municipio=None, status='APROVADO'):
        """Helper para criar eventos de teste"""
        from core.models import Usuario  # Import no método para evitar circular import
        
        # Criar um usuário solicitante para o evento
        user, created = Usuario.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@test.com'}
        )
        
        # Criar a solicitação
        solicitacao = Solicitacao.objects.create(
            titulo_evento=f"Evento Teste {formador.nome}",
            data_inicio=inicio,
            data_fim=fim,
            usuario_solicitante=user,
            municipio=municipio or self.municipio_fortaleza,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            status=status
        )
        
        # Adicionar formador através do relacionamento M2M
        solicitacao.formadores.add(formador)
        
        return solicitacao
    
    def _create_block(self, formador, inicio, fim, tipo='T'):
        """Helper para criar bloqueios de teste"""
        return DisponibilidadeFormadores.objects.create(
            formador=formador,
            data_bloqueio=inicio.date(),
            hora_inicio=inicio.time(),
            hora_fim=fim.time(),
            tipo_bloqueio=tipo,
            motivo=f"Bloqueio {tipo} teste"
        )
    
    def test_conflict_overlap_total(self):
        """RD-01: Conflito de sobreposição total deve retornar X"""
        # Evento existente das 8h às 12h
        existing_start = self.base_date
        existing_end = self.base_date + timedelta(hours=4)
        self._create_event(self.formador_1, existing_start, existing_end)
        
        # Novo evento sobrepondo totalmente das 9h às 11h
        new_start = self.base_date + timedelta(hours=1)
        new_end = self.base_date + timedelta(hours=3)
        
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            new_start,
            new_end,
            self.municipio_fortaleza
        )
        
        self.assertFalse(result.available)
        self.assertEqual(result.code, 'X')
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(result.conflicts[0].code, 'X')
        self.assertIn('Conflito com', result.conflicts[0].message)
    
    def test_conflict_overlap_partial(self):
        """RD-01: Conflito de sobreposição parcial deve retornar X"""
        # Evento existente das 10h às 14h
        existing_start = self.base_date + timedelta(hours=2)
        existing_end = self.base_date + timedelta(hours=6)
        self._create_event(self.formador_1, existing_start, existing_end)
        
        # Novo evento sobrepondo parcialmente das 8h às 12h
        new_start = self.base_date
        new_end = self.base_date + timedelta(hours=4)
        
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            new_start,
            new_end,
            self.municipio_fortaleza
        )
        
        self.assertFalse(result.available)
        self.assertEqual(result.code, 'X')
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(result.conflicts[0].code, 'X')
    
    def test_no_conflict_adjacent_end_equals_start(self):
        """RD-01: Eventos adjacentes (fim == início) no mesmo município não devem conflitar"""
        # Evento existente das 8h às 11h no MESMO município (3 horas)
        existing_start = self.base_date
        existing_end = self.base_date + timedelta(hours=3)
        self._create_event(self.formador_1, existing_start, existing_end, self.municipio_fortaleza)
        
        # Novo evento começando exatamente quando o anterior termina (11h às 13h) no MESMO município (2 horas)
        # Total: 3h + 2h = 5h < limite de 6h diárias
        new_start = existing_end  # 11h
        new_end = new_start + timedelta(hours=2)  # 13h
        
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            new_start,
            new_end,
            self.municipio_fortaleza  # MESMO município - não deve exigir buffer
        )
        
        self.assertTrue(result.available)
        self.assertEqual(result.code, 'E')
        self.assertEqual(len(result.conflicts), 0)
    
    def test_block_total_T_prevents_any_event(self):
        """RD-02: Bloqueio total (T) deve impedir qualquer evento"""
        # Criar bloqueio total das 8h às 17h
        block_start = self.base_date
        block_end = self.base_date + timedelta(hours=9)
        self._create_block(self.formador_1, block_start, block_end, 'T')
        
        # Tentar evento das 10h às 12h (dentro do bloqueio)
        new_start = self.base_date + timedelta(hours=2)
        new_end = self.base_date + timedelta(hours=4)
        
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            new_start,
            new_end,
            self.municipio_fortaleza
        )
        
        self.assertFalse(result.available)
        self.assertEqual(result.code, 'T')
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(result.conflicts[0].code, 'T')
        self.assertIn('Bloqueio total', result.conflicts[0].message)
    
    def test_block_partial_P_prevents_inside_allows_outside(self):
        """RD-03: Bloqueio parcial (P) deve impedir apenas no intervalo bloqueado"""
        # Criar bloqueio parcial das 10h às 14h
        block_start = self.base_date + timedelta(hours=2)
        block_end = self.base_date + timedelta(hours=6)
        self._create_block(self.formador_1, block_start, block_end, 'P')
        
        # Evento dentro do bloqueio deve falhar
        inside_start = self.base_date + timedelta(hours=3)  # 11h
        inside_end = self.base_date + timedelta(hours=5)    # 13h
        
        result_inside = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            inside_start,
            inside_end,
            self.municipio_fortaleza
        )
        
        self.assertFalse(result_inside.available)
        self.assertEqual(result_inside.code, 'P')
        
        # Evento fora do bloqueio deve passar
        outside_start = self.base_date + timedelta(hours=7)  # 15h
        outside_end = self.base_date + timedelta(hours=9)    # 17h
        
        result_outside = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            outside_start,
            outside_end,
            self.municipio_fortaleza
        )
        
        self.assertTrue(result_outside.available)
        self.assertEqual(result_outside.code, 'E')
    
    def test_travel_buffer_between_cities_required(self):
        """RD-04: Buffer de deslocamento obrigatório entre municípios diferentes"""
        # Evento em Fortaleza das 8h às 12h
        fortaleza_start = self.base_date
        fortaleza_end = self.base_date + timedelta(hours=4)
        self._create_event(self.formador_1, fortaleza_start, fortaleza_end, self.municipio_fortaleza)
        
        # Tentar evento em Sobral das 12h30 às 16h30 (30 min após, menos que buffer de 60 min)
        sobral_start = fortaleza_end + timedelta(minutes=30)
        sobral_end = sobral_start + timedelta(hours=4)
        
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            sobral_start,
            sobral_end,
            self.municipio_sobral
        )
        
        self.assertFalse(result.available)
        self.assertEqual(result.code, 'D')
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(result.conflicts[0].code, 'D')
        self.assertIn('Deslocamento insuficiente', result.conflicts[0].message)
    
    def test_same_city_allows_zero_buffer(self):
        """RD-04: Mesmo município permite buffer zero"""
        # Evento em Fortaleza das 8h às 10h (2 horas)
        event1_start = self.base_date
        event1_end = self.base_date + timedelta(hours=2)
        self._create_event(self.formador_1, event1_start, event1_end, self.municipio_fortaleza)
        
        # Evento também em Fortaleza imediatamente após (10h às 13h) (3 horas)
        # Total: 2h + 3h = 5h < limite de 6h
        event2_start = event1_end  # Sem buffer
        event2_end = event2_start + timedelta(hours=3)
        
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            event2_start,
            event2_end,
            self.municipio_fortaleza
        )
        
        self.assertTrue(result.available)
        self.assertEqual(result.code, 'E')
        self.assertEqual(len(result.conflicts), 0)
    
    def test_daily_capacity_M_exceeded(self):
        """RD-05: Capacidade diária excedida deve retornar M"""
        # Evento das 8h às 13h (5 horas)
        event1_start = self.base_date
        event1_end = self.base_date + timedelta(hours=5)
        self._create_event(self.formador_1, event1_start, event1_end)
        
        # Tentar adicionar evento das 14h às 16h (2 horas) - total 7h > limite 6h
        event2_start = self.base_date + timedelta(hours=6)
        event2_end = self.base_date + timedelta(hours=8)
        
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            event2_start,
            event2_end,
            self.municipio_fortaleza
        )
        
        self.assertFalse(result.available)
        self.assertEqual(result.code, 'M')
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(result.conflicts[0].code, 'M')
        self.assertIn('Capacidade diária excedida', result.conflicts[0].message)
    
    def test_multi_formador_any_conflict_blocks(self):
        """Qualquer conflito em qualquer formador deve bloquear a solicitação"""
        # Criar conflito para formador_1 (bloqueio total)
        block_start = self.base_date
        block_end = self.base_date + timedelta(hours=8)
        self._create_block(self.formador_1, block_start, block_end, 'T')
        
        # formador_2 está livre
        # Verificar múltiplos formadores
        event_start = self.base_date + timedelta(hours=2)
        event_end = self.base_date + timedelta(hours=4)
        
        result = self.engine.check_availability(
            Formador.objects.filter(id__in=[self.formador_1.id, self.formador_2.id]),
            event_start,
            event_end,
            self.municipio_fortaleza
        )
        
        self.assertFalse(result.available)  # Bloqueado por formador_1
        self.assertEqual(result.code, 'T')
        self.assertEqual(len(result.conflicts), 1)
        self.assertIn('João Silva', [c.formador.nome for c in result.conflicts])
    
    def test_timezone_aware_fortaleza_localtime(self):
        """RD-06: Comparações devem ser timezone-aware usando America/Fortaleza"""
        # Criar datetime naive
        naive_start = datetime(2025, 1, 15, 8, 0)
        naive_end = datetime(2025, 1, 15, 12, 0)
        
        # O motor deve converter automaticamente
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            naive_start,
            naive_end,
            self.municipio_fortaleza
        )
        
        # Deve funcionar sem erro (conversão automática)
        self.assertTrue(result.available)
        self.assertEqual(result.code, 'E')
        
        # Verificar se timezone foi aplicado corretamente comparando com evento existente
        aware_start = timezone.make_aware(naive_start, self.fortaleza_tz)
        aware_end = timezone.make_aware(naive_end, self.fortaleza_tz)
        
        # Criar evento com horário aware
        self._create_event(self.formador_1, aware_start, aware_end)
        
        # Tentar sobrepor com naive (deve detectar conflito)
        result_conflict = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            naive_start,
            naive_end,
            self.municipio_fortaleza
        )
        
        self.assertFalse(result_conflict.available)
        self.assertEqual(result_conflict.code, 'X')
    
    def test_conflict_messages_include_codes_and_intervals(self):
        """RD-08: Mensagens devem incluir códigos e intervalos formatados"""
        # Criar vários tipos de conflitos
        
        # Bloqueio total
        block_start = self.base_date
        block_end = self.base_date + timedelta(hours=2)
        self._create_block(self.formador_1, block_start, block_end, 'T')
        
        # Evento conflitante
        event_start = self.base_date + timedelta(hours=3)
        event_end = self.base_date + timedelta(hours=6)
        self._create_event(self.formador_1, event_start, event_end)
        
        # Verificar conflitos
        check_start = self.base_date + timedelta(minutes=30)
        check_end = self.base_date + timedelta(hours=7)
        
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            check_start,
            check_end,
            self.municipio_fortaleza
        )
        
        self.assertFalse(result.available)
        self.assertEqual(len(result.conflicts), 2)
        
        # Verificar formatação das mensagens
        messages = [c.message for c in result.conflicts]
        
        # Deve ter mensagem de bloqueio total
        total_block_msg = next(msg for msg in messages if 'Bloqueio total' in msg)
        self.assertIn('15/01 08:00', total_block_msg)  # Data/hora formatada
        
        # Deve ter mensagem de conflito
        conflict_msg = next(msg for msg in messages if 'Conflito com' in msg)
        self.assertIn('15/01', conflict_msg)  # Data formatada
        
        # Verificar summary message
        self.assertIn('Conflitos encontrados', result.summary_message)
        self.assertIn('❌', result.summary_message)
    
    def test_availability_check_structure(self):
        """Verificar estrutura completa do AvailabilityCheck"""
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            self.base_date,
            self.base_date + timedelta(hours=4),
            self.municipio_fortaleza
        )
        
        # Verificar todos os campos obrigatórios
        self.assertIsInstance(result.available, bool)
        self.assertIsInstance(result.code, str)
        self.assertIsInstance(result.conflicts, list)
        self.assertIsInstance(result.formadores_checked, list)
        self.assertIsInstance(result.summary_message, str)
        
        # Para evento sem conflitos
        self.assertTrue(result.available)
        self.assertEqual(result.code, 'E')
        self.assertEqual(len(result.conflicts), 0)
        self.assertEqual(len(result.formadores_checked), 1)
        self.assertIn('✅', result.summary_message)
    
    def test_create_availability_engine_factory(self):
        """Testar factory function"""
        engine = create_availability_engine(
            travel_buffer_minutes=120,
            daily_hour_limit=8
        )
        
        self.assertIsInstance(engine, DisponibilidadeEngine)
        self.assertEqual(engine.travel_buffer_minutes, 120)
        self.assertEqual(engine.daily_hour_limit, 8)
        
        # Factory padrão
        default_engine = create_availability_engine()
        self.assertEqual(default_engine.travel_buffer_minutes, DisponibilidadeEngine.DEFAULT_TRAVEL_BUFFER_MINUTES)
    
    def test_check_formador_availability_convenience(self):
        """Testar função de conveniência"""
        result = check_formador_availability(
            self.formador_1,
            self.base_date,
            self.base_date + timedelta(hours=2),
            self.municipio_fortaleza
        )
        
        self.assertIsInstance(result, type(self.engine.check_availability(
            Formador.objects.filter(id=self.formador_1.id),
            self.base_date,
            self.base_date + timedelta(hours=2),
            self.municipio_fortaleza
        )))
        
        self.assertTrue(result.available)
        self.assertEqual(result.code, 'E')


class DisponibilidadeEngineIntegrationTest(TestCase):
    """Testes de integração do motor com modelos Django"""
    
    def setUp(self):
        """Setup para testes de integração"""
        self.municipio = Municipio.objects.create(nome="Fortaleza", ativo=True)
        self.projeto = Projeto.objects.create(nome="ACERTA", ativo=True)
        self.tipo_evento = TipoEvento.objects.create(nome="Presencial", ativo=True)
        
        self.formador = Formador.objects.create(
            nome="João Silva",
            email="joao@test.com",
            ativo=True
        )
        
        self.engine = DisponibilidadeEngine()
        
        self.base_date = timezone.make_aware(
            datetime(2025, 1, 15, 8, 0),
            timezone.get_current_timezone()
        )
    
    def test_integration_with_solicitacao_model(self):
        """Integração com modelo Solicitacao"""
        from core.models import Usuario
        
        # Criar usuário solicitante
        user, created = Usuario.objects.get_or_create(
            username='test_integration',
            defaults={'email': 'test_integration@test.com'}
        )
        
        # Criar evento via modelo
        evento = Solicitacao.objects.create(
            titulo_evento="Evento Teste",
            data_inicio=self.base_date,
            data_fim=self.base_date + timedelta(hours=4),
            usuario_solicitante=user,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            status='APROVADO'
        )
        evento.formadores.add(self.formador)
        
        # Verificar conflito
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador.id),
            self.base_date + timedelta(hours=2),
            self.base_date + timedelta(hours=6),
            self.municipio
        )
        
        self.assertFalse(result.available)
        self.assertEqual(result.code, 'X')
        self.assertEqual(result.conflicts[0].conflicting_event.id, evento.id)
    
    def test_integration_with_bloqueio_model(self):
        """Integração com modelo DisponibilidadeFormadores"""
        # Criar bloqueio via modelo
        bloqueio = DisponibilidadeFormadores.objects.create(
            formador=self.formador,
            data_bloqueio=self.base_date.date(),
            hora_inicio=self.base_date.time(),
            hora_fim=(self.base_date + timedelta(hours=8)).time(),
            tipo_bloqueio='T',
            motivo="Bloqueio teste"
        )
        
        # Verificar conflito
        result = self.engine.check_availability(
            Formador.objects.filter(id=self.formador.id),
            self.base_date + timedelta(hours=2),
            self.base_date + timedelta(hours=4),
            self.municipio
        )
        
        self.assertFalse(result.available)
        self.assertEqual(result.code, 'T')
        self.assertEqual(result.conflicts[0].conflicting_block.id, bloqueio.id)