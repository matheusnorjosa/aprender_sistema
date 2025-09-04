"""
Comando para verificar configuração e acesso ao Google Calendar.
Diagnóstica credenciais, feature flags e conectividade.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica configuração e acesso ao Google Calendar"

    def add_arguments(self, parser):
        parser.add_argument(
            "--write-test",
            action="store_true",
            help="Cria e remove evento de teste (requer autenticação)",
        )
        parser.add_argument(
            "--list-events",
            type=int,
            metavar="N",
            help="Lista os próximos N eventos do calendário (padrão: 10)",
        )
        parser.add_argument(
            "--check-conflicts",
            action="store_true",
            help="Verifica conflitos entre solicitações aprovadas e eventos no Calendar",
        )
        parser.add_argument(
            "--sync-stats",
            action="store_true",
            help="Mostra estatísticas de sincronização",
        )
        parser.add_argument(
            "--validate-quota",
            action="store_true",
            help="Valida limites de quota da API Google",
        )
        parser.add_argument(
            "--calendar-id",
            type=str,
            help="Usar calendar ID específico para testes (sobrescreve setting)",
        )

    def handle(self, *args, **options):
        self.stdout.write("=== DIAGNÓSTICO GOOGLE CALENDAR ===\n")

        # 1. Verificar feature flag
        sync_enabled = getattr(settings, "FEATURE_GOOGLE_SYNC", False)
        status_sync = "OK Habilitado" if sync_enabled else "ERRO Desabilitado"
        self.stdout.write(f"Feature Google Sync: {status_sync}")

        if not sync_enabled:
            self.stdout.write(
                self.style.WARNING(
                    "AVISO: Sincronização desabilitada. Configure FEATURE_GOOGLE_SYNC=True"
                )
            )

        # 2. Verificar variáveis de ambiente
        calendar_id = getattr(settings, "GOOGLE_CALENDAR_CALENDAR_ID", None)
        if calendar_id:
            self.stdout.write(f"Calendar ID: {calendar_id}")
        else:
            self.stdout.write("Calendar ID: ERRO Não configurado")
            self.stdout.write(
                self.style.WARNING("Configure GOOGLE_CALENDAR_CALENDAR_ID no settings")
            )

        # 3. Verificar credenciais
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path:
            self.stdout.write(f"Credentials Path: {credentials_path}")

            if os.path.exists(credentials_path):
                self.stdout.write("OK Arquivo de credenciais existe")

                # Verificar se é um arquivo JSON válido
                try:
                    import json

                    with open(credentials_path, "r") as f:
                        creds_data = json.load(f)
                        if "client_email" in creds_data:
                            email = creds_data["client_email"]
                            self.stdout.write(f"OK Service Account: {email}")
                        else:
                            self.stdout.write(
                                "⚠️ Arquivo não parece ser service account"
                            )
                except json.JSONDecodeError:
                    self.stdout.write(
                        "ERRO Arquivo de credenciais inválido (JSON malformado)"
                    )
                except Exception as e:
                    self.stdout.write(f"ERRO Erro ao ler credenciais: {e}")
            else:
                self.stdout.write("ERRO Arquivo de credenciais não encontrado")
        else:
            self.stdout.write("Credentials Path: ERRO Não configurado")
            self.stdout.write(
                self.style.WARNING(
                    "Configure GOOGLE_APPLICATION_CREDENTIALS environment variable"
                )
            )

        # 4. Verificar se as bibliotecas estão disponíveis
        try:
            import google.auth
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            self.stdout.write("OK Google APIs client libraries instaladas")
        except ImportError as e:
            self.stdout.write(f"ERRO Biblioteca Google não encontrada: {e}")
            self.stdout.write(
                self.style.WARNING(
                    "Instale: pip install google-api-python-client google-auth"
                )
            )

        # 5. Teste de conectividade (se solicitado)
        if options["write_test"] and sync_enabled and credentials_path:
            self.stdout.write("\n🧪 EXECUTANDO TESTE DE CONECTIVIDADE...")

            if not os.path.exists(credentials_path):
                self.stdout.write("ERRO Não é possível testar sem credenciais válidas")
                return

            try:
                # Usar nosso serviço real para teste
                from core.services.integrations.google_calendar import (
                    GoogleCalendarService,
                )

                service = GoogleCalendarService()

                # Testar listagem de eventos (operação read-only)
                events = service.list_events(max_results=5)

                self.stdout.write(f"OK Autenticação bem-sucedida")
                self.stdout.write(f"📅 Eventos encontrados: {len(events)}")

                if events:
                    self.stdout.write("🗓️ Últimos eventos:")
                    for event in events[:3]:
                        title = event.get("summary", "Sem título")
                        start = event.get("start", {}).get("dateTime", "Sem data")
                        self.stdout.write(f"   - {title} ({start[:16]})")

                # Teste adicional: tentar criar e deletar um evento de teste
                if calendar_id:
                    self.stdout.write("\n🧪 Testando criação/exclusão de evento...")

                    # Criar evento de teste simples
                    from datetime import datetime, timedelta

                    from core.services.integrations.calendar_types import GoogleEvent

                    now = datetime.now()
                    test_event = GoogleEvent(
                        title="[TESTE] Sistema Aprender - Verificação",
                        description="Evento de teste criado automaticamente",
                        start_iso=(now + timedelta(hours=1)).isoformat(),
                        end_iso=(now + timedelta(hours=2)).isoformat(),
                        location="",
                        conference=False,
                    )

                    # Criar evento
                    result = service.create_event(test_event)
                    test_event_id = result.get("id")

                    if test_event_id:
                        self.stdout.write("OK Evento de teste criado com sucesso")

                        # Deletar evento de teste imediatamente
                        service.delete_event(test_event_id)
                        self.stdout.write("OK Evento de teste removido com sucesso")

                        self.stdout.write(
                            "🎉 Teste completo de criação/exclusão bem-sucedido!"
                        )
                    else:
                        self.stdout.write("⚠️ Falha ao criar evento de teste")

            except ImportError:
                self.stdout.write("ERRO Bibliotecas Google não instaladas")
            except Exception as e:
                self.stdout.write(f"ERRO Erro no teste de conectividade: {e}")
                if "quota" in str(e).lower():
                    self.stdout.write(
                        "💡 Dica: Verifique se você não excedeu a quota da API"
                    )

        # 6. Resumo e recomendações
        self.stdout.write("\n📋 RESUMO:")

        if not sync_enabled:
            self.stdout.write("🔧 Configure FEATURE_GOOGLE_SYNC=True no settings")

        if not credentials_path or not os.path.exists(credentials_path):
            self.stdout.write("🔧 Configure credenciais do service account")

        if not calendar_id:
            self.stdout.write("🔧 Configure GOOGLE_CALENDAR_CALENDAR_ID")

        # 7. Funcionalidades adicionais
        if options.get("calendar_id"):
            calendar_id = options["calendar_id"]
            self.stdout.write(f"\n🔄 Usando Calendar ID personalizado: {calendar_id}")

        # Listar eventos
        if options.get("list_events") is not None or options.get("list_events"):
            count = options.get("list_events", 10) if options.get("list_events") else 10
            self._list_calendar_events(
                calendar_id, count, sync_enabled, credentials_path
            )

        # Verificar conflitos
        if options.get("check_conflicts"):
            self._check_conflicts(calendar_id, sync_enabled, credentials_path)

        # Estatísticas de sync
        if options.get("sync_stats"):
            self._show_sync_stats()

        # Validar quota
        if options.get("validate_quota"):
            self._validate_quota(calendar_id, sync_enabled, credentials_path)

        self.stdout.write("\nOK Diagnóstico concluído!")

        if sync_enabled and credentials_path and calendar_id:
            self.stdout.write("🎉 Sistema parece estar configurado corretamente!")
        else:
            self.stdout.write("⚠️ Configuração incompleta - consulte documentação")

    def _list_calendar_events(self, calendar_id, count, sync_enabled, credentials_path):
        """Lista eventos do calendário"""
        self.stdout.write(f"\n📅 LISTANDO PRÓXIMOS {count} EVENTOS...")

        if not sync_enabled or not credentials_path:
            self.stdout.write("ERRO Sincronização desabilitada ou credenciais ausentes")
            return

        try:
            from core.services.integrations.google_calendar import GoogleCalendarService

            service = GoogleCalendarService()
            events = service.list_events(max_results=count)

            if events:
                self.stdout.write(f"OK Encontrados {len(events)} eventos:")
                for i, event in enumerate(events, 1):
                    title = event.get("summary", "Sem título")
                    start = event.get("start", {}).get("dateTime", "Sem data")[:16]
                    location = event.get("location", "Local não definido")
                    self.stdout.write(f"   {i:2d}. {title}")
                    self.stdout.write(f"       📅 {start} | 📍 {location}")
            else:
                self.stdout.write("📅 Nenhum evento encontrado")

        except Exception as e:
            self.stdout.write(f"ERRO Erro ao listar eventos: {e}")

    def _check_conflicts(self, calendar_id, sync_enabled, credentials_path):
        """Verifica conflitos entre sistema e Google Calendar"""
        self.stdout.write("\n🔍 VERIFICANDO CONFLITOS...")

        if not sync_enabled or not credentials_path:
            self.stdout.write("ERRO Sincronização desabilitada ou credenciais ausentes")
            return

        try:
            from datetime import datetime, timedelta

            from core.models import EventoGoogleCalendar, Solicitacao, SolicitacaoStatus

            # Solicitações aprovadas sem evento no calendar
            aprovadas_sem_evento = (
                Solicitacao.objects.filter(
                    status=SolicitacaoStatus.PRE_AGENDA,
                    data_inicio__gte=datetime.now() - timedelta(days=7),
                )
                .exclude(
                    id__in=EventoGoogleCalendar.objects.values_list(
                        "solicitacao_id", flat=True
                    )
                )
                .count()
            )

            # Eventos do calendar sem solicitação
            eventos_sem_solicitacao = EventoGoogleCalendar.objects.filter(
                solicitacao__isnull=True
            ).count()

            self.stdout.write(
                f"📊 Solicitações aprovadas sem evento no Calendar: {aprovadas_sem_evento}"
            )
            self.stdout.write(
                f"📊 Eventos no Calendar sem solicitação: {eventos_sem_solicitacao}"
            )

            if aprovadas_sem_evento == 0 and eventos_sem_solicitacao == 0:
                self.stdout.write("OK Nenhum conflito encontrado")
            else:
                self.stdout.write("⚠️ Conflitos detectados - recomenda-se investigação")

        except Exception as e:
            self.stdout.write(f"ERRO Erro ao verificar conflitos: {e}")

    def _show_sync_stats(self):
        """Mostra estatísticas de sincronização"""
        self.stdout.write("\n📊 ESTATÍSTICAS DE SINCRONIZAÇÃO...")

        try:
            from datetime import datetime, timedelta

            from django.db.models import Count

            from core.models import (
                EventoGoogleCalendar,
                LogAuditoria,
                Solicitacao,
                SolicitacaoStatus,
            )

            # Stats básicas
            total_solicitacoes = Solicitacao.objects.count()
            aprovadas = Solicitacao.objects.filter(
                status=SolicitacaoStatus.PRE_AGENDA
            ).count()
            eventos_criados = EventoGoogleCalendar.objects.count()

            # Stats últimos 30 dias
            last_30_days = datetime.now() - timedelta(days=30)
            recent_solicitacoes = Solicitacao.objects.filter(
                data_solicitacao__gte=last_30_days
            ).count()
            recent_approvals = LogAuditoria.objects.filter(
                data_hora__gte=last_30_days, acao__icontains="RF04"
            ).count()

            self.stdout.write(f"📈 Total de solicitações: {total_solicitacoes}")
            self.stdout.write(f"OK Solicitações aprovadas: {aprovadas}")
            self.stdout.write(f"📅 Eventos criados no Calendar: {eventos_criados}")
            self.stdout.write(f"🕒 Solicitações últimos 30 dias: {recent_solicitacoes}")
            self.stdout.write(f"🕒 Aprovações últimos 30 dias: {recent_approvals}")

            # Taxa de conversão
            if total_solicitacoes > 0:
                taxa_aprovacao = (aprovadas / total_solicitacoes) * 100
                self.stdout.write(f"📊 Taxa de aprovação: {taxa_aprovacao:.1f}%")

            if aprovadas > 0:
                taxa_sync = (eventos_criados / aprovadas) * 100
                self.stdout.write(f"📊 Taxa de sincronização: {taxa_sync:.1f}%")

        except Exception as e:
            self.stdout.write(f"ERRO Erro ao gerar estatísticas: {e}")

    def _validate_quota(self, calendar_id, sync_enabled, credentials_path):
        """Valida limites de quota da API"""
        self.stdout.write("\n📊 VALIDANDO QUOTA DA API...")

        if not sync_enabled or not credentials_path:
            self.stdout.write("ERRO Sincronização desabilitada ou credenciais ausentes")
            return

        try:
            import time

            from core.services.integrations.google_calendar import GoogleCalendarService

            service = GoogleCalendarService()

            # Testar múltiplas chamadas para verificar rate limits
            start_time = time.time()
            for i in range(5):
                events = service.list_events(max_results=1)
                time.sleep(0.1)  # Pequena pausa entre chamadas
            end_time = time.time()

            duration = end_time - start_time
            self.stdout.write(f"OK 5 chamadas à API completadas em {duration:.2f}s")

            # Informações sobre limites conhecidos
            self.stdout.write("📋 Limites da API Google Calendar:")
            self.stdout.write("   • Queries per day: 1,000,000")
            self.stdout.write("   • Queries per 100 seconds per user: 20,000")
            self.stdout.write("   • Queries per 100 seconds: 50,000")

            if duration < 1.0:
                self.stdout.write("OK API respondendo rapidamente")
            elif duration < 3.0:
                self.stdout.write("⚠️ API com latência moderada")
            else:
                self.stdout.write("ERRO API com alta latência - possível throttling")

        except Exception as e:
            self.stdout.write(f"ERRO Erro ao validar quota: {e}")
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                self.stdout.write(
                    "🚫 Quota da API excedida - aguarde ou aumente limites"
                )
