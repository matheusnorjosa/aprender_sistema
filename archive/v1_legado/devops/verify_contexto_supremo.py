#!/usr/bin/env python
"""
Verificação completa do Contexto Supremo (read-only, sem flush)
Valida invariantes, RBAC, status, vínculos, views, idempotência
"""
import json
import os
import pathlib
import sys
from collections import defaultdict
from datetime import date, datetime

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
import django

django.setup()

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import connection
from django.db.models import Count

from core.models import (
    MarcadorPlanilha,
    Setor,
    Solicitacao,
    Usuario,
    VinculoUsuarioSetor,
)

DOCS_ROOT = pathlib.Path(getattr(settings, "DOCS_ROOT", "/app/docs"))
DOCS_ROOT.mkdir(parents=True, exist_ok=True)
OUT_MD = (
    DOCS_ROOT
    / f"VERIFICACAO_CONTEXTO_SUPREMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
)
OUT_JSON = (
    DOCS_ROOT
    / f"VERIFICACAO_CONTEXTO_SUPREMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)

CUTOFF_DATE = date(2025, 9, 25)
PAPEIS_PERMITIDOS = {"GERENTE", "COORDENADOR", "FORMADOR", "CONTROLE", "SUPER"}
GRUPOS_MINIMOS = {"coordenador", "formador", "controle", "superintendencia", "gerente"}

results = {"status": "PASS", "items": {}, "metrics": {}, "errors": []}


def check(name, condition, error_msg=""):
    """Helper para registrar verificação"""
    passed = bool(condition)
    results["items"][name] = {"pass": passed, "error": error_msg if not passed else ""}
    if not passed:
        results["status"] = "FAIL"
        results["errors"].append(f"{name}: {error_msg}")
    return passed


def sql_scalar(query):
    """Executar query e retornar valor escalar"""
    with connection.cursor() as cur:
        cur.execute(query)
        row = cur.fetchone()
        return row[0] if row else None


print("=" * 80)
print("VERIFICACAO CONTEXTO SUPREMO - Docker (read-only)")
print("=" * 80)

# === A) CONFIG BASICA ===
print("\n[A] CONFIG BASICA")
tz_ok = check(
    "TIME_ZONE",
    settings.TIME_ZONE == "America/Fortaleza",
    f"Esperado America/Fortaleza, obtido {settings.TIME_ZONE}",
)
print(f"  TIME_ZONE: {settings.TIME_ZONE} {'✅' if tz_ok else '❌'}")

docs_ok = check("DOCS_ROOT", DOCS_ROOT.exists(), f"DOCS_ROOT {DOCS_ROOT} nao existe")
print(f"  DOCS_ROOT: {DOCS_ROOT} {'✅' if docs_ok else '❌'}")

# === B) RBAC & VINCULOS ===
print("\n[B] RBAC & VINCULOS")
grupos_db = set(Group.objects.values_list("name", flat=True))
grupos_faltando = GRUPOS_MINIMOS - grupos_db
grupos_ok = check(
    "Grupos minimos", len(grupos_faltando) == 0, f"Grupos faltando: {grupos_faltando}"
)
print(f"  Grupos DB: {grupos_db}")
print(f"  Grupos minimos OK: {'✅' if grupos_ok else '❌'}")

# Papéis em VinculoUsuarioSetor
papeis_db = set(VinculoUsuarioSetor.objects.values_list("papel", flat=True).distinct())
papeis_invalidos = papeis_db - PAPEIS_PERMITIDOS
papeis_ok = check(
    "Papeis permitidos",
    len(papeis_invalidos) == 0,
    f"Papeis invalidos: {papeis_invalidos}",
)
print(f"  Papeis DB: {papeis_db}")
print(f"  Papeis OK: {'✅' if papeis_ok else '❌'}")

# Contagens por papel
vinculos_por_papel = dict(
    VinculoUsuarioSetor.objects.values("papel")
    .annotate(total=Count("id"))
    .values_list("papel", "total")
)
results["metrics"]["vinculos_por_papel"] = vinculos_por_papel
print(f"  Vinculos por papel: {vinculos_por_papel}")

# Contagens por setor
vinculos_por_setor = dict(
    VinculoUsuarioSetor.objects.select_related("setor")
    .values("setor__nome")
    .annotate(total=Count("id"))
    .values_list("setor__nome", "total")
)
results["metrics"]["vinculos_por_setor"] = vinculos_por_setor
top_setores = dict(sorted(vinculos_por_setor.items(), key=lambda x: -x[1])[:5])
print(f"  Vinculos por setor (top 5): {top_setores}")

# === C) EVENTOS / STATUS ===
print("\n[C] EVENTOS / STATUS")
total_eventos = Solicitacao.objects.count()
results["metrics"]["total_eventos"] = total_eventos

# AGENDADO por ingestão (FAIL se > 0)
# Nota: campo 'origem' pode não existir; verifica apenas observacoes
agendado_ingestao = sql_scalar(
    """
    SELECT COUNT(*) FROM core_solicitacao
    WHERE status='AGENDADO'
    AND (observacoes ILIKE '%import%' OR observacoes ILIKE '%ingest%')
"""
)
agendado_ok = check(
    "AGENDADO por ingestao",
    agendado_ingestao == 0,
    f"Encontrados {agendado_ingestao} AGENDADO por ingestao",
)
print(
    f"  AGENDADO por ingestao: {agendado_ingestao} {'✅' if agendado_ok else '❌ FAIL'}"
)

# Contagem por status
eventos_por_status = dict(
    Solicitacao.objects.values("status")
    .annotate(total=Count("id"))
    .values_list("status", "total")
)
results["metrics"]["eventos_por_status"] = eventos_por_status
print(f"  Eventos por status: {eventos_por_status}")

# === D) SOLICITANTE (amostra) ===
print("\n[D] SOLICITANTE = COORDENADOR (amostra)")
sample_size = min(30, total_eventos)
sample = list(
    Solicitacao.objects.select_related("usuario_solicitante").order_by("?")[
        :sample_size
    ]
)
conformes = 0
for sol in sample:
    if sol.usuario_solicitante:
        # Verificar se tem vínculo COORDENADOR
        tem_vinculo = VinculoUsuarioSetor.objects.filter(
            usuario=sol.usuario_solicitante, papel="COORDENADOR"
        ).exists()
        if tem_vinculo:
            conformes += 1

pct_conforme = (conformes / sample_size * 100) if sample_size > 0 else 0
solicitante_ok = check(
    "Solicitante conformidade",
    pct_conforme >= 95.0,
    f"Apenas {pct_conforme:.1f}% conforme (esperado >= 95%)",
)
print(f"  Amostra: {sample_size} eventos")
print(
    f"  Conformes: {conformes} ({pct_conforme:.1f}%) {'✅' if solicitante_ok else '❌'}"
)
results["metrics"]["solicitante_conformidade_pct"] = pct_conforme

# === E) DISPONIBILIDADES / VIEWS ===
print("\n[E] DISPONIBILIDADES / VIEWS")
views_esperadas = [
    "vw_disp_normalizada",
    "vw_disp_anual_agregada",
    "vw_disp_desloc_agregada",
    "vw_disp_bloq_agregada",
]
views_existentes = []
for vname in views_esperadas:
    try:
        count = sql_scalar(f"SELECT COUNT(*) FROM {vname}")
        views_existentes.append(vname)
        print(f"  {vname}: {count} registros ✅")
        results["metrics"][f"{vname}_count"] = count
    except Exception as e:
        print(f"  {vname}: ERRO ❌ ({e})")
        results["errors"].append(f"View {vname} nao acessivel: {e}")

views_ok = check(
    "Views disponibilidades",
    len(views_existentes) == len(views_esperadas),
    f"Views faltando: {set(views_esperadas) - set(views_existentes)}",
)

# === F) IDEMPOTENCIA / MARCADORES ===
print("\n[F] IDEMPOTENCIA / MARCADORES")
total_marcadores = MarcadorPlanilha.objects.count()
results["metrics"]["total_marcadores"] = total_marcadores

# Verificar UNIQUE em external_hash
duplicados = sql_scalar(
    """
    SELECT COUNT(*) FROM (
        SELECT external_hash FROM core_marcadorplanilha
        GROUP BY external_hash HAVING COUNT(*) > 1
    ) sub
"""
)
marcadores_ok = check(
    "MarcadorPlanilha UNIQUE",
    duplicados == 0,
    f"Encontrados {duplicados} hashes duplicados",
)
print(f"  Total marcadores: {total_marcadores}")
print(f"  Hashes duplicados: {duplicados} {'✅' if marcadores_ok else '❌'}")

# === METRICAS GERAIS ===
results["metrics"]["total_usuarios"] = Usuario.objects.count()
results["metrics"]["total_vinculos"] = VinculoUsuarioSetor.objects.count()
results["metrics"]["total_setores"] = Setor.objects.count()

print("\n" + "=" * 80)
if results["status"] == "PASS":
    print("[OK] Paridade 100% com Contexto Supremo (auditoria sem flush, CSV local)")
    exit_code = 0
else:
    print(f"[FAIL] {len(results['errors'])} erro(s) encontrado(s)")
    for err in results["errors"]:
        print(f"  - {err}")
    exit_code = 1

# Salvar relatórios
OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False))
print(f"\n✅ JSON: {OUT_JSON}")

# Markdown
md_lines = [
    "# Verificação Contexto Supremo",
    f"**Data:** {datetime.now().isoformat()}",
    f"**Status:** {results['status']}\n",
    "## Itens Verificados\n",
]
for item_name, item_data in results["items"].items():
    status = "✅ PASS" if item_data["pass"] else "❌ FAIL"
    md_lines.append(f"- **{item_name}**: {status}")
    if item_data["error"]:
        md_lines.append(f"  - Erro: {item_data['error']}")

md_lines.append("\n## Métricas\n")
for key, val in results["metrics"].items():
    md_lines.append(f"- **{key}**: {val}")

if results["errors"]:
    md_lines.append("\n## Erros\n")
    for err in results["errors"]:
        md_lines.append(f"- {err}")

OUT_MD.write_text("\n".join(md_lines))
print(f"✅ MD: {OUT_MD}")
print("=" * 80)
sys.exit(exit_code)
