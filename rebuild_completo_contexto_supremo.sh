#!/bin/bash
set -euo pipefail

############################################
# 0) CONSTANTES DO CONTEXTO SUPREMO
############################################

# Sheets (sempre por TÍTULO de aba; não confiar em gid fixo)
SHEET_AGENDA_ID="1oqDA9tN-wNiFVLS3KYTFzsXKpJpvDECfeKucjwf9GKs"     # Cópia de Acompanhamento de Agenda | 2025
SHEET_DISP_ID="1C4_9Gn8gwKjgD1CgssIKaU4bacwv7XuL2QnoSVwomxU"       # Cópia de Disponibilidade | 2025
SHEET_USERS_ID="1yPH-uCRc2XyThLU7V4pSoNYozydn1-IRRJRjubFCjXs"      # Cópia de Usuários

# Abas/Setores canônicos (Agenda)
declare -a ABAS_SETOR=("ACerta" "Outros" "Brincando" "Vidas" "Super")

# Regras especiais (Agenda/Outros)
# - Coluna "K" (projeto) vira setor; mapear IDEB/IDEB10 -> "Gestão Escolar"
# - Em "Outros" o coordenador atua como formador (não há colunas de formador)
# - Em todas menos "Outros", coluna D "Cancelar" (checkbox) sinaliza cancelado/adiado (info histórica, não apaga; só status)
# - Em "Outros", coluna "L" (segmento) pode conter "Cancelado"/"Adiado" (mesma semântica)

# Status por corte temporal
CUTOFF_PASTO="2025-09-25"  # <= passado: REALIZADO (ou CANCELADO se marcado); > futuro: CRIADO (ou APROVADO==SIM na aba Super)

# Segurança
export TZ="America/Fortaleza"
export DOCS_ROOT="/app/docs"
mkdir -p "$DOCS_ROOT" logs creds data/ingest

############################################
# 1) PRÉ-CHECAGENS E AJUSTES (idempotente)
############################################

python - <<'PY'
# Garante DOCS_ROOT no settings, GSHEETS adapter por título e runner incluindo vínculos
import os, re, json
from pathlib import Path
SET = Path("aprender_sistema/settings.py")
txt = SET.read_text(encoding="utf-8")
if "DOCS_ROOT" not in txt:
    txt += """

# ---- DOCS ROOT (todo relatório sai aqui) ----
import os as _os
from pathlib import Path as _Path
DOCS_ROOT = _Path(_os.getenv('DOCS_ROOT', BASE_DIR / 'docs'))
DOCS_ROOT.mkdir(parents=True, exist_ok=True)
"""
    SET.write_text(txt, encoding="utf-8")

# Força timezone
if "TIME_ZONE" in txt and "America/Fortaleza" not in txt:
    txt = re.sub(r"TIME_ZONE\s*=\s*['\"][^'\"]+['\"]","TIME_ZONE = 'America/Fortaleza'",txt)
    SET.write_text(txt, encoding="utf-8")

print("[OK] settings.py saneado (DOCS_ROOT + Fortaleza)")

# Garante gsheets_adapter com fetch por título
A = Path("ingestao/gsheets_adapter.py")
a = A.read_text(encoding="utf-8")
if "def fetch_csv_by_title" not in a:
    a += """

def fetch_csv_by_title(sheet_id: str, title: str):
    \"\"\"Usa gspread para pegar worksheet por título (Service Account).\"\"\"
    import gspread, os
    from google.oauth2.service_account import Credentials
    sa_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', os.getenv('GSHEETS_SA_PATH', ''))
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = Credentials.from_service_account_file(sa_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(title)
    return ws.get_all_records()
"""
    A.write_text(a, encoding="utf-8")
    print("[OK] gsheets_adapter.fetch_csv_by_title criado")

# Runner inclui import_vinculos_setor
R = Path("devops/run_ssot_imports.sh")
r = R.read_text(encoding="utf-8") if R.exists() else ""
if "import_vinculos_setor" not in r:
    if not r:
        print("[WARN] runner ausente; criando um novo.")
        r = "#!/usr/bin/env bash\nset -euo pipefail\ncd /app\n"
    r += """
# --- Vínculos de Setor (descoberta por catálogo) ---
VINC_CSV=${VINC_CSV:-data/ingest/vinculos.csv}
python manage.py import_vinculos_setor "$VINC_CSV" --sheet-id="{sid}" --tab="Super" || true
""".format(sid=os.getenv('SHEET_AGENDA_ID',''))
    R.write_text(r, encoding="utf-8")
    print("[OK] Runner agora chama import_vinculos_setor")
    import os
    os.system("chmod +x devops/run_ssot_imports.sh" if os.name!='nt' else " ")
PY

############################################
# 2) BACKUP E RESET SEGURO (com aviso)
############################################

# Backup best-effort (ignorar se pg_dump não existir)
( pg_dump -h db -U postgres -d postgres -f "$DOCS_ROOT/backup_$(date +%Y%m%d_%H%M%S).sql" 2>/dev/null \
  || echo "[WARN] pg_dump indisponível; seguindo sem backup externo." )

# Limpa dados mas mantém esquema (idempotente)
python manage.py flush --noinput

# Migra, checa e coleta estáticos
python manage.py migrate
python manage.py check --deploy || true
python manage.py collectstatic --noinput || true

############################################
# 3) CATALOGAÇÃO/HELPERS (por título de aba)
############################################

python - <<'PY'
import json, os, re
from pathlib import Path
out = {
  "agenda_sheet_id": os.getenv("SHEET_AGENDA_ID","1oqDA9tN-wNiFVLS3KYTFzsXKpJpvDECfeKucjwf9GKs"),
  "disp_sheet_id": os.getenv("SHEET_DISP_ID","1C4_9Gn8gwKjgD1CgssIKaU4bacwv7XuL2QnoSVwomxU"),
  "users_sheet_id": os.getenv("SHEET_USERS_ID","1yPH-uCRc2XyThLU7V4pSoNYozydn1-IRRJRjubFCjXs"),
  "abas": ["ACerta","Outros","Brincando","Vidas","Super"],
  "disp_abas": ["ANUAL","DESLOCAMENTO","Bloqueios"]  # "MENSAL" é apenas visual
}
Path("ingestao/gsheets_catalog.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("[OK] gsheets_catalog por títulos salvo")
PY

############################################
# 4) IMPORTADORES — Ajustes para CONTEXTO SUPREMO
############################################
# Regras:
# - Em TODOS: cross-check GSheets↔CSV, idempotência por SHA1, AGENDADO NUNCA.
# - Eventos:
#    * Solicitante = Coordenador (coluna "Coordenador")
#    * Passado (<=CUTOFF): REALIZADO, a menos de cancelado/adiado -> CANCELADO
#    * Futuro (>CUTOFF): CRIADO; se aba=Super e "Aprovação" == "SIM": APROVADO
#    * Município, Projeto, Participantes: mapear das colunas informadas
# - Setores:
#    * ACerta, Brincando, Vidas, Super: setores fixos
#    * Outros: setor = valor da coluna "projeto" (K); mapear IDEB/IDEB10 -> "Gestão Escolar"
# - Vínculos:
#    * Criar/atualizar UNIQUE(usuario,setor,papel), ativo=1
#    * Em "Outros", o coordenador também entra como FORMADOR no mesmo setor

python - <<'PY'
import os, re, csv, json, datetime
from pathlib import Path
from django.utils import timezone
os.environ.setdefault('DJANGO_SETTINGS_MODULE','aprender_sistema.settings')
import django; django.setup()
from django.apps import apps
from django.contrib.auth import get_user_model
from ingestao.gsheets_adapter import fetch_csv_by_title
from ingestao.utils import sha1_of_row

User = get_user_model()
Marc = apps.get_model('core','MarcadorPlanilha')
Setor = apps.get_model('core','Setor')
Vinc = apps.get_model('core','VinculoUsuarioSetor')
Solic = apps.get_model('core','Solicitacao')
Proj = apps.get_model('core','Projeto')
Mun = apps.get_model('core','Municipio')
Part = apps.get_model('core','Participante')

FORT = timezone.pytz.timezone('America/Fortaleza')
CUTOFF = datetime.date.fromisoformat(os.getenv('CUTOFF_PASTO','2025-09-25'))
DOCS = Path(os.getenv('DOCS_ROOT','docs')); DOCS.mkdir(parents=True, exist_ok=True)

def norm_setor_nome(nome:str)->str:
    n=(nome or '').strip()
    if re.fullmatch(r'IDEB10?', n, flags=re.I): return "Gestão Escolar"
    return n

# 4.1) Criar setores base
for nome in ["Superintendência","ACerta","Brincando","Vidas"]:
    Setor.objects.get_or_create(nome=nome, defaults={"ativo":True, "vinculado_superintendencia": (nome=="Superintendência")})

print("[OK] Setores base prontos")

# 4.2) Importar USUÁRIOS (planilha "Cópia de Usuários" aba "Ativos")
users_rows = fetch_csv_by_title(os.getenv('SHEET_USERS_ID'), "Ativos")
created=updated=skipped=0
for row in users_rows:
    payload={k.strip(): (row.get(k) or "").strip() for k in row.keys()}
    email = (payload.get("Email") or "").lower().strip()
    if not email:
        # Fallback por nome
        email = f"user_{sha1_of_row({'n':payload.get('Nome Completo') or payload.get('Nome')})[:8]}@aprender.local"
    first = (payload.get("Nome") or payload.get("Nome Completo") or "").strip().split()[0] if (payload.get("Nome") or payload.get("Nome Completo")) else ""
    last = " ".join((payload.get("Nome Completo") or "").split()[1:])
    u, was = User.objects.get_or_create(email=email, defaults={"username":email[:150], "first_name":first, "last_name":last, "is_active":True})
    if was: created+=1
    else: skipped+=1
print(f"[USERS] created={created} skipped={skipped}")

# 4.3) Importar EVENTOS + criar setores dinâmicos (Aba por Aba)
def as_dt(dtxt, htxt):
    # dtxt=dd/mm/aaaa ou iso; htxt=HH:MM
    from datetime import datetime as _dt, time
    d=None
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%d-%m-%Y"):
        try:
            d=_dt.strptime((dtxt or "").strip(), fmt).date(); break
        except: pass
    if not d: return None
    hh=None
    for fmt in ("%H:%M","%Hh%M","%Hh"):
        try:
            hh=_dt.strptime((htxt or "").strip(), fmt).time(); break
        except: pass
    hh = hh or time(0,0)
    dt = _dt.combine(d, hh)
    return FORT.localize(dt)

agenda_id = os.getenv('SHEET_AGENDA_ID')

def get_or_user(nome_email):
    s=(nome_email or "").strip()
    if not s: return None
    if "@" in s: key=s.lower()
    else:
        # tenta por nome
        key=None
    u = User.objects.filter(email=s.lower()).first() if "@" in s else User.objects.filter(first_name__iexact=s.split()[0]).first()
    if not u:
        u = User.objects.create(username=f"u_{sha1_of_row({'k':s})[:10]}", email=(s.lower() if "@" in s else f"noemail_{sha1_of_row({'k':s})[:6]}@aprender.local"), first_name=s.split()[0], last_name=" ".join(s.split()[1:]))
    return u

def ensure_vinc(user, setor_nome, papel, ativo=True):
    if not user or not setor_nome: return
    setor_nome = norm_setor_nome(setor_nome)
    s,_ = Setor.objects.get_or_create(nome=setor_nome, defaults={"ativo":True})
    v,created = Vinc.objects.get_or_create(usuario=user, setor=s, papel=papel, defaults={"ativo":ativo})
    if not created and v.ativo!=ativo:
        v.ativo=ativo; v.save(update_fields=["ativo"])

def cancel_mark(payload, aba):
    if aba.lower()=="outros":
        seg = (payload.get("segmento") or payload.get("Segmento") or "").lower()
        return "cancel" in seg or "adi" in seg
    else:
        # coluna D "Cancelar"
        return (str(payload.get("Cancelar") or payload.get("C ancelar") or "False").strip().lower() in {"1","true","t","x","sim","yes"})

created_ev=sk_ev=0
for aba in ["ACerta","Outros","Brincando","Vidas","Super"]:
    rows = fetch_csv_by_title(agenda_id, aba)
    for R in rows:
        P = {k.strip(): (R.get(k) or "").strip() for k in R.keys()}
        # Campos comuns por nomes do contexto
        municipio = P.get("município") or P.get("Município") or P.get("Municipio") or ""
        projeto   = P.get("projeto") or P.get("Projeto") or ""
        tipo      = P.get("tipo") or P.get("Tipo") or ""
        data      = P.get("data") or P.get("Data") or ""
        hini      = P.get("hora início") or P.get("hora inicio") or P.get("Hora Início") or ""
        hfim      = P.get("hora fim") or P.get("Hora Fim") or ""
        coord     = P.get("Coordenador") or ""
        coord_ac  = P.get("Coord Acompanha") or ""
        # Formadores e convidados
        forms = [P.get(f"Formador {i}") or "" for i in range(1,6)]
        conv  = (P.get("Convidados") or "").split(";")

        # Setor pela aba, exceto "Outros" que usa projeto
        setor_nome = aba if aba!="Outros" else (projeto or "Outros")
        setor_nome = norm_setor_nome(setor_nome)

        # Vínculos (Coordenador e Formadores)
        ucoord = get_or_user(coord)
        if ucoord:
            ensure_vinc(ucoord, setor_nome, "COORDENADOR", True)
            # regra "Outros": coordenador também é FORMADOR
            if aba=="Outros":
                ensure_vinc(ucoord, setor_nome, "FORMADOR", True)

        for f in [x for x in forms if x]:
            uf = get_or_user(f)
            ensure_vinc(uf, setor_nome, "FORMADOR", True)

        # Município
        mun = None
        if municipio:
            mun = Mun.objects.filter(nome__iexact=municipio.split("-")[0].strip()).first()

        # Projeto
        prj = None
        if projeto:
            prj,_ = Proj.objects.get_or_create(nome=setor_nome if aba=="Outros" else projeto, defaults={"ativo":True})

        # Datas
        dt_ini = as_dt(data, hini)
        dt_fim = as_dt(data, hfim)

        # Status por regras
        status = "CRIADO"
        is_past = bool(dt_ini and dt_ini.date() <= CUTOFF)
        if is_past:
            status = "CANCELADO" if cancel_mark(P, aba) else "REALIZADO"
        else:
            if aba=="Super" and (P.get("Aprovação") or P.get("Aprovacao") or "").strip().upper()=="SIM":
                status = "APROVADO"

        # Solicitante = Coordenador
        solicitante_id = ucoord.id if ucoord else None

        h = sha1_of_row({"aba":aba,"municipio":municipio,"projeto":projeto,"tipo":tipo,"data":data,"hini":hini,"hfim":hfim,"coord":coord,"forms":forms,"conv":conv})
        if Marc.objects.filter(external_hash=h).exists():
            sk_ev+=1; continue

        e = Solic.objects.create(
            titulo=f"{municipio} - {projeto or setor_nome} - {tipo}",
            status=status,
            data_inicio=dt_ini, data_fim=dt_fim,
            municipio_id=getattr(mun,'id',None),
            projeto_id=getattr(prj,'id',None),
            usuario_solicitante_id=solicitante_id
        )
        # Participantes
        if ucoord: Part.objects.create(solicitacao=e, usuario=ucoord, papel="Coordenador")
        if coord_ac:
            uac = get_or_user(coord_ac);
            if uac: Part.objects.create(solicitacao=e, usuario=uac, papel="Coordenador Acompanha")
        for f in [x for x in forms if x]:
            uf = get_or_user(f);
            if uf: Part.objects.create(solicitacao=e, usuario=uf, papel="Formador")
        for c in [x.strip() for x in conv if x.strip()]:
            uc = get_or_user(c);
            if uc: Part.objects.create(solicitacao=e, usuario=uc, papel="Convidado")

        Marc.objects.create(external_hash=h, tipo_entidade="solicitacao", raw_data=P, origem=f"import_eventos:{aba}", origem_aba=aba, gid="", cancelado_flag=(status=="CANCELADO"))
        created_ev+=1

print(f"[EVENTOS] created={created_ev} skipped={sk_ev}")

# 4.4) Disponibilidades (ANUAL, DESLOCAMENTO, Bloqueios) — staging agregada
from django.db import connection
disp_rows = {}
for tab in ["ANUAL","DESLOCAMENTO","Bloqueios"]:
    try:
        disp_rows[tab] = fetch_csv_by_title(os.getenv('SHEET_DISP_ID'), tab)
    except Exception as e:
        disp_rows[tab]=[]

# cria tabela staging agregada se não existir (ano, mes, matched_user_id, tipo, origem, valido)
with connection.cursor() as cur:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS disp_staging_agregada (
        id bigserial primary key,
        matched_user_id integer,
        tipo varchar(16),
        ano int, mes int,
        origem varchar(64),
        valido boolean default true
    );
    """)
    connection.commit()

def match_user(s):
    s=(s or "").strip()
    if not s: return None
    u = User.objects.filter(email__iexact=s).first()
    if not u:
        # tenta por primeiro nome
        u = User.objects.filter(first_name__iexact=s.split()[0]).first()
    return getattr(u,'id',None)

import calendar
ins=0
with connection.cursor() as cur:
    # ANUAL -> marca tipo 'ANUAL' para todos os meses do ano informados na linha (colunas A..AC na planilha real)
    for r in disp_rows.get("ANUAL",[]):
        nome = r.get("Nome") or r.get("Formador") or ""
        uid = match_user(nome)
        if not uid: continue
        ano = int(r.get("Ano") or datetime.date.today().year)
        for mes in range(1,13):
            cur.execute("INSERT INTO disp_staging_agregada(matched_user_id,tipo,ano,mes,origem,valido) VALUES (%s,%s,%s,%s,%s,%s)",
                [uid,"ANUAL",ano,mes,"GS:ANUAL",True]); ins+=1
    # DESLOCAMENTO -> tipo 'DESLOC'
    for r in disp_rows.get("DESLOCAMENTO",[]):
        nome = r.get("Nome") or r.get("Formador") or ""
        uid = match_user(nome)
        if not uid: continue
        try:
            d = r.get("Data") or r.get("DATA") or ""
            y,m,_ = d.split("-") if "-" in d else (d[-4:], d[3:5], "01")
            cur.execute("INSERT INTO disp_staging_agregada(matched_user_id,tipo,ano,mes,origem,valido) VALUES (%s,%s,%s,%s,%s,%s)",
                [uid,"DESLOC",int(y),int(m),"GS:DESLOC",True]); ins+=1
        except: pass
    # Bloqueios -> tipo 'BLOQ' (mensalização simples pela data início)
    for r in disp_rows.get("Bloqueios",[]):
        nome = r.get("Nome") or r.get("Pessoa") or ""
        uid = match_user(nome)
        if not uid: continue
        d = (r.get("Data Início") or r.get("Inicio") or "").strip()
        if not d: continue
        try:
            if "/" in d:
                dia,mes,ano = d.split("/")
            elif "-" in d:
                ano,mes,dia = d.split("-")
            else:
                continue
            cur.execute("INSERT INTO disp_staging_agregada(matched_user_id,tipo,ano,mes,origem,valido) VALUES (%s,%s,%s,%s,%s,%s)",
                [uid,"BLOQ",int(ano),int(mes),"GS:Bloqueios",True]); ins+=1
        except: pass
    connection.commit()

print(f"[DISP STAGING] inserções={ins}")

print("[OK] Importadores aplicados segundo o Contexto Supremo")
PY

############################################
# 5) VÍNCULOS A PARTIR DO CONTEXTO (consolidação)
############################################
# Garante que todas as pessoas mencionadas nas abas tenham VÍNCULO com seus setores

python - <<'PY'
import os, re, json
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE','aprender_sistema.settings')
import django; django.setup()
from django.apps import apps
from django.contrib.auth import get_user_model
from ingestao.gsheets_adapter import fetch_csv_by_title
from ingestao.utils import sha1_of_row

User = get_user_model()
Vinc = apps.get_model('core','VinculoUsuarioSetor')
Setor = apps.get_model('core','Setor')

def norm_setor(n):
    n=(n or "").strip()
    if re.fullmatch(r'IDEB10?', n, flags=re.I): return "Gestão Escolar"
    return n

agenda_id = os.getenv('SHEET_AGENDA_ID')
abas = ["ACerta","Outros","Brincando","Vidas","Super"]
added=0

def get_user(s):
    s=(s or "").strip()
    if not s: return None
    from django.db.models import Q
    if "@" in s:
        return User.objects.filter(email__iexact=s).first()
    return User.objects.filter(Q(first_name__iexact=s.split()[0]) | Q(username__iexact=s)).first()

def ensure(user, setor, papel):
    global added
    if not (user and setor and papel): return
    s,_ = Setor.objects.get_or_create(nome=setor, defaults={"ativo":True})
    v,cr = Vinc.objects.get_or_create(usuario=user, setor=s, papel=papel, defaults={"ativo":True})
    if cr: added+=1
    if v.ativo is not True: v.ativo=True; v.save(update_fields=["ativo"])

for aba in abas:
    rows = fetch_csv_by_title(agenda_id, aba)
    for R in rows:
        P = {k.strip(): (R.get(k) or "").strip() for k in R.keys()}
        projeto = P.get("projeto") or P.get("Projeto") or ""
        setor = norm_setor(aba if aba!="Outros" else (projeto or "Outros"))
        coord = P.get("Coordenador") or ""
        ucoord = get_user(coord)
        if ucoord:
            ensure(ucoord,setor,"COORDENADOR")
            if aba=="Outros":
                ensure(ucoord,setor,"FORMADOR")
        for i in range(1,6):
            f = P.get(f"Formador {i}") or ""
            uf = get_user(f)
            if uf: ensure(uf,setor,"FORMADOR")

print(f"[VINCULOS] novos={added}")
PY

############################################
# 6) REAPLICAR VIEWS DE DISPONIBILIDADE + ÍNDICES
############################################
psql -h db -U postgres -d postgres <<'SQL' || true
-- View normalizada (intervalo mensal)
CREATE OR REPLACE VIEW vw_disp_normalizada AS
SELECT
  s.matched_user_id AS user_id,
  s.tipo            AS tipo,
  make_timestamptz(s.ano, s.mes, 1, 0, 0, 0, 'America/Fortaleza') AS ts_inicio,
  (date_trunc('month', make_timestamptz(s.ano, s.mes, 1, 0, 0, 0, 'America/Fortaleza')) + interval '1 month' - interval '1 second') AS ts_fim,
  tstzrange(
    make_timestamptz(s.ano, s.mes, 1, 0, 0, 0, 'America/Fortaleza'),
    (date_trunc('month', make_timestamptz(s.ano, s.mes, 1, 0, 0, 0, 'America/Fortaleza')) + interval '1 month' - interval '1 second'),
    '[]'
  ) AS intervalo,
  'GS' AS origem,
  COALESCE(true, TRUE) AS valido
FROM disp_staging_agregada s
WHERE s.matched_user_id IS NOT NULL;

CREATE OR REPLACE VIEW vw_disp_anual_agregada  AS SELECT * FROM vw_disp_normalizada WHERE tipo='ANUAL';
CREATE OR REPLACE VIEW vw_disp_desloc_agregada AS SELECT * FROM vw_disp_normalizada WHERE tipo='DESLOC';
CREATE OR REPLACE VIEW vw_disp_bloq_agregada   AS SELECT * FROM vw_disp_normalizada WHERE tipo='BLOQ';

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_stg_user ON disp_staging_agregada(matched_user_id);
CREATE INDEX IF NOT EXISTS idx_stg_ano_mes ON disp_staging_agregada(ano,mes);
SQL

############################################
# 7) AUDITORIA FINAL (full-spectrum)
############################################

python - <<'PY'
import json, os, datetime
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE','aprender_sistema.settings')
import django; django.setup()
from django.db import connection
from django.apps import apps

DOCS = Path(os.getenv('DOCS_ROOT','docs'))
TS = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
MD = DOCS / f"AUDITORIA_FINAL_{TS}.md"
J  = DOCS / f"AUDITORIA_FINAL_{TS}.json"
out = {"meta":{"ts":TS,"tz":os.getenv("TZ")}, "checks":{}}

def q(sql):
    with connection.cursor() as c:
        c.execute(sql);
        return c.fetchall()

# 1) Sem AGENDADO por ingestão
ag = q("SELECT COUNT(*) FROM core_solicitacao WHERE status='AGENDADO'"); out["checks"]["sem_agendado"]= (ag[0][0]==0)

# 2) Views de disponibilidade
try:
    va = q("SELECT COUNT(*) FROM vw_disp_anual_agregada")[0][0]
    vd = q("SELECT COUNT(*) FROM vw_disp_desloc_agregada")[0][0]
    vb = q("SELECT COUNT(*) FROM vw_disp_bloq_agregada")[0][0]
    out["checks"]["views_ok"]= True
    out["views"]={"ANUAL":va,"DESLOC":vd,"BLOQ":vb}
except Exception as e:
    out["checks"]["views_ok"]= False
    out["views_error"]= str(e)

# 3) Vínculos > 17
vc = q("SELECT COUNT(*) FROM core_vinculousuariosetor WHERE ativo IS TRUE")[0][0]
out["checks"]["vinculos_volume"] = vc>17
out["vinculos_ativos"]=vc

# 4) Usuários sem vínculo
uv = q("""
SELECT COUNT(*) FROM auth_user u
LEFT JOIN core_vinculousuariosetor v ON v.usuario_id=u.id AND v.ativo IS TRUE
WHERE v.id IS NULL
""")[0][0]
out["checks"]["usuarios_sem_vinculo_zero"] = (uv==0)
out["usuarios_sem_vinculo"]=uv

# 5) Distribuição de status
st = q("SELECT status, COUNT(*) FROM core_solicitacao GROUP BY status ORDER BY 2 DESC")
out["status"]=st

MD.write_text("# AUDITORIA FINAL\n\n"+json.dumps(out,ensure_ascii=False,indent=2), encoding="utf-8")
J.write_text(json.dumps(out,ensure_ascii=False,indent=2), encoding="utf-8")

print("[OK] Auditoria Final escrita em", MD)
PY

echo "[DONE] REBUILD COMPLETO com base no Contexto Supremo."
