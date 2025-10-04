"""
Comando canônico de importação de eventos das abas de planilhas.
Suporta ingestão dual: Google Sheets ou CSV local.

Flags obrigatórias:
- --from: 'sheets' ou caminho para diretório CSV (ex: /app/data/ingest/dia3/abas)
- --abas: Lista separada por vírgula (ex: ACerta,Brincando,Vidas,Super,Outros)

Regras de negócio:
- derive_status: NUNCA seta AGENDADO no import; apenas {CRIADO, APROVADO, REALIZADO, CANCELADO}
- Idempotência: external_hash = sha1(f"{aba}|{municipio}|{data}|{hora_ini}|{projeto}|{coordenador}")
- Mapeio "Outros": "IDEB"/"IDEB10" → Gestão Escolar; demais projetos: coordenador é o formador
- Usuários on-the-fly: origem='planilha', is_provisorio=True
- COORDENADOR_ACOMPANHA: parse de campo booleano
"""

import datetime
import hashlib
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from backend.config import sheets_config
from core.models import (
    Formador,
    MarcadorPlanilha,
    Municipio,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
    TipoEvento,
    Usuario,
)


# --- titulo automatico e unico por (titulo_evento, data_inicio) ---
def _build_unique_title(Solicitacao, base_titulo, data_inicio, extra_hint=""):
    base = (base_titulo or "Evento").strip()
    if not base:
        base = "Evento"
    candidate = (base + (f" - {extra_hint}" if extra_hint else "")).strip()
    n = 2
    q = Solicitacao.objects.filter(titulo_evento=candidate, data_inicio=data_inicio)
    while q.exists():
        candidate_try = f"{candidate} #{n}"
        q = Solicitacao.objects.filter(
            titulo_evento=candidate_try, data_inicio=data_inicio
        )
        if not q.exists():
            candidate = candidate_try
            break
        n += 1
    return candidate


from core.signals.mapa_signals import solicitacao_signals_disabled
from ingestao.adapters import (
    CsvFolderAdapter,
    ParsedEvento,
    SheetsAdapter,
    parse_row_por_aba,
)


class Command(BaseCommand):
    help = """
    Importa eventos de abas (Google Sheets ou CSV local).

    Uso:
      # Google Sheets
      python manage.py import_eventos_abas --from sheets --abas ACerta,Brincando --dry-run

      # CSV local
      python manage.py import_eventos_abas --from /app/data/ingest/dia3/abas --abas ACerta --dry-run
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--from",
            dest="source",
            type=str,
            default="sheets",
            help="Fonte de dados: 'sheets' ou caminho para diretório CSV",
        )
        parser.add_argument(
            "--abas",
            type=str,
            required=True,
            help="Lista de abas separadas por vírgula (ex: ACerta,Brincando,Vidas,Super,Outros)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula importação sem salvar no banco",
        )
        parser.add_argument(
            "--verbose", action="store_true", help="Exibe logs detalhados"
        )

    def handle(self, *args, **options):
        source = options["source"]
        abas_str = options["abas"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        # Parse abas (case-insensitive)
        abas = [aba.strip() for aba in abas_str.split(",")]

        self.stdout.write(self.style.SUCCESS(f"🚀 Import eventos - Fonte: {source}"))
        self.stdout.write(f"   Abas: {', '.join(abas)}")
        self.stdout.write(f"   Dry-run: {dry_run}")
        self.stdout.write("")

        # Determinar adapter
        if source == "sheets":
            adapter = SheetsAdapter()
            self.stdout.write(
                f"📊 Usando Google Sheets: {sheets_config.AGENDA_2025_ID}"
            )
        else:
            adapter = CsvFolderAdapter(source)
            self.stdout.write(f"📁 Usando CSV local: {source}")

        total_created = 0
        total_skipped = 0
        total_errors = 0

        for aba in abas:
            self.stdout.write(f"\n📋 Processando aba: {aba}")

            # Obter GID ou caminho CSV
            if source == "sheets":
                gid = sheets_config.get_aba_gid(aba)
                if not gid:
                    self.stdout.write(
                        self.style.WARNING(
                            f"   ⚠️  GID vazio para aba '{aba}' - pulando"
                        )
                    )
                    continue

                rows_iter = adapter.rows(sheets_config.AGENDA_2025_ID, gid)
            else:
                # CSV local: assumir arquivo <aba>.csv
                csv_path = f"{aba}.csv"
                rows_iter = adapter.rows(csv_path)

            # Processar linhas
            created, skipped, errors = self._process_rows(
                aba, rows_iter, dry_run, verbose
            )

            total_created += created
            total_skipped += skipped
            total_errors += errors

            self.stdout.write(
                f"   ✅ Criados: {created} | ⏭️  Pulados: {skipped} | ❌ Erros: {errors}"
            )

        # Resumo final
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"📊 RESUMO FINAL:")
        self.stdout.write(f"   Criados: {total_created}")
        self.stdout.write(f"   Pulados (duplicados): {total_skipped}")
        self.stdout.write(f"   Erros: {total_errors}")
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY-RUN: Nenhuma alteração foi salva no banco")
            )

        return 0

    def _process_rows(self, aba, rows_iter, dry_run, verbose):
        """Processa linhas de uma aba e retorna (created, skipped, errors)."""
        created = 0
        skipped = 0
        errors = 0
        today = timezone.localdate()
        tz = timezone.get_current_timezone()

        for row in rows_iter:
            try:
                # Usar parser novo
                parsed = parse_row_por_aba(aba, row)
                if not parsed:
                    skipped += 1
                    continue

                # Derivar status (NUNCA AGENDADO!)
                if parsed.cancelado:
                    status = SolicitacaoStatus.CANCELADO
                elif parsed.data and parsed.data < today:
                    status = SolicitacaoStatus.REALIZADO
                else:
                    status = (
                        SolicitacaoStatus.APROVADO
                        if (aba.lower() == "super" and parsed.aprovado)
                        else SolicitacaoStatus.CRIADO
                    )

                # Gerar external_hash para idempotência
                h_ini_str = (
                    parsed.hora_ini.strftime("%H:%M") if parsed.hora_ini else "00:00"
                )
                hash_input = f"{aba}|{parsed.municipio}|{parsed.data.isoformat()}|{h_ini_str}|{(parsed.projeto or '').strip()}|{(parsed.coordenador or '').strip()}"
                external_hash = hashlib.sha1(hash_input.encode("utf-8")).hexdigest()

                # --- construir titulo_evento base (sempre nao-vazio) ---
                titulo_base = f"{parsed.municipio} - {parsed.projeto or 'Evento'}"
                titulo_tipo = (parsed.tipo or aba).strip()
                titulo_seed = f"{titulo_base} - {titulo_tipo}".strip()
                extra_hint = ""
                try:
                    if parsed.encontro:
                        extra_hint = f"Encontro {parsed.encontro}"
                    elif parsed.hora_ini:
                        extra_hint = str(parsed.hora_ini)
                except Exception:
                    pass

                # Verificar se já existe (via observacoes contendo hash)
                if Solicitacao.objects.filter(
                    observacoes__contains=external_hash
                ).exists():
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f"   ⏭️  Já existe: {parsed.municipio} | {parsed.data} | {parsed.projeto}"
                            )
                        )
                    skipped += 1
                    continue

                if verbose:
                    self.stdout.write(
                        f"   📝 {parsed.municipio} | {parsed.data} {parsed.hora_ini} | {parsed.projeto} | status={status.name} | hash={external_hash[:8]}..."
                    )

                if not dry_run:
                    with transaction.atomic(), solicitacao_signals_disabled():
                        # Buscar/criar município
                        municipio_obj, _ = Municipio.objects.get_or_create(
                            nome=parsed.municipio,
                            defaults={"uf": "CE"},  # Default CE, ajustar depois
                        )

                        # Buscar/criar projeto
                        projeto_obj = None
                        if parsed.projeto:
                            projeto_obj, _ = Projeto.objects.get_or_create(
                                nome=parsed.projeto
                            )

                        # Buscar/criar tipo evento
                        tipo_obj = None
                        if parsed.tipo:
                            tipo_obj, _ = TipoEvento.objects.get_or_create(
                                nome=parsed.tipo
                            )

                        # Buscar/criar coordenador (usuario_solicitante)
                        if parsed.coordenador:
                            coordenador_obj, _ = Usuario.objects.get_or_create(
                                username=parsed.coordenador[
                                    :150
                                ],  # Django username max 150 chars
                                defaults={
                                    "first_name": (
                                        parsed.coordenador.split()[0]
                                        if parsed.coordenador.split()
                                        else ""
                                    ),
                                    "last_name": (
                                        " ".join(parsed.coordenador.split()[1:])
                                        if len(parsed.coordenador.split()) > 1
                                        else ""
                                    ),
                                    "origem": "planilha",
                                    "is_provisorio": True,
                                },
                            )
                        else:
                            # Usar usuário "Sistema" como fallback
                            coordenador_obj, _ = Usuario.objects.get_or_create(
                                username="sistema_import",
                                defaults={
                                    "first_name": "Sistema",
                                    "last_name": "Importação",
                                    "origem": "sistema",
                                    "is_provisorio": False,
                                    "is_staff": True,
                                },
                            )

                        # Combinar data + hora para datetime timezone-aware
                        h_ini = parsed.hora_ini or datetime.time(8, 0)
                        dt_ini_naive = datetime.datetime.combine(parsed.data, h_ini)
                        data_inicio_dt = timezone.make_aware(dt_ini_naive, tz)

                        # Resolver unicidade por (titulo_evento, data_inicio)
                        titulo_evento = _build_unique_title(
                            Solicitacao, titulo_seed, data_inicio_dt, extra_hint
                        )

                        if parsed.hora_fim:
                            dt_fim_naive = datetime.datetime.combine(
                                parsed.data, parsed.hora_fim
                            )
                            data_fim_dt = timezone.make_aware(dt_fim_naive, tz)
                        else:
                            data_fim_dt = data_inicio_dt + datetime.timedelta(hours=2)

                        # Encontro (inteiro se possível)
                        try:
                            encontro_n = (
                                int((parsed.encontro or "").strip())
                                if parsed.encontro
                                else None
                            )
                        except:
                            encontro_n = None

                        # Criar solicitação
                        solicitacao = Solicitacao.objects.create(
                            municipio=municipio_obj,
                            titulo_evento=titulo_evento,
                            projeto=projeto_obj,
                            tipo_evento=tipo_obj,
                            data_inicio=data_inicio_dt,
                            data_fim=data_fim_dt,
                            status=status,
                            numero_encontro_formativo=encontro_n,
                            usuario_solicitante=coordenador_obj,
                            observacoes=f"Importado da aba {aba} | hash:{external_hash}",
                        )

                        # Associar formadores (M2M) - solicitacao.formadores espera Usuario
                        for formador_nome in parsed.formadores:
                            if not formador_nome:
                                continue
                            formador_usuario, _ = Usuario.objects.get_or_create(
                                username=formador_nome[:150],
                                defaults={
                                    "first_name": (
                                        formador_nome.split()[0]
                                        if formador_nome.split()
                                        else ""
                                    ),
                                    "last_name": (
                                        " ".join(formador_nome.split()[1:])
                                        if len(formador_nome.split()) > 1
                                        else ""
                                    ),
                                    "origem": "planilha",
                                    "is_provisorio": True,
                                },
                            )
                            # Garantir que existe Formador (com nome e email nullable)
                            Formador.objects.get_or_create(
                                usuario=formador_usuario,
                                defaults={
                                    "nome": formador_nome,
                                    "email": None,  # Nullable agora
                                    "ativo": True,
                                },
                            )
                            # Adicionar usuario ao M2M
                            solicitacao.formadores.add(formador_usuario)

                        # TODO: Criar marcador de planilha (schema divergente no momento)
                        # Por agora, idempotência via hash check feito antes de criar
                        pass

                created += 1

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"   ❌ Erro ao processar linha: {e}")
                )
                if verbose:
                    import traceback

                    self.stdout.write(f"      Traceback: {traceback.format_exc()}")

        return created, skipped, errors
