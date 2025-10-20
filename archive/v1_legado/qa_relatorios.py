#!/usr/bin/env python3
"""
DAT-P05-v1: qa_relatorios.py
Consolida pendências e gera relatórios de qualidade a partir dos artefatos ETL anteriores.

Autor: Engenheiro de Dados/Back-end DAT (Aprender)
Stack: Python 3.13 | Django 5.2 | PostgreSQL 15
Timezone: America/Fortaleza
Execução: Docker (docker compose exec -T web python qa_relatorios.py)

ENTRADAS (CSV):
  Obrigatórios:
    - events.csv (do DAT-P01-v2)
    - event_people.csv (do DAT-P01-v2)
    - pendencias.csv (do DAT-P01-v2)
    - pre_agenda.csv (do DAT-P04-v2)
    - pre_agenda_pendencias.csv (do DAT-P04-v2)
  Opcional:
    - controle_unificado.csv (do DAT-P03-v2)

SAÍDAS:
  1. qa_pendencias_unificadas.csv
     - União de P01 pendencias.csv + P04 pre_agenda_pendencias.csv
     - Normaliza motivos: not_found_email → email_nao_encontrado, etc.
     - Ordenação: origem, motivo, nome_original

  2. qa_eventos_sem_emails.csv
     - Eventos sem solicitante_email ou attendees_emails vazios
     - Ordenação: data, hora_inicio, municipio

  3. qa_duplicados.csv
     - Eventos com external_hash duplicado (count > 1)
     - Ordenação: external_hash, data, hora_inicio

  4. qa_resumo.md
     - Tabela de contagens por origem/motivo
     - Eventos sem emails
     - Duplicados
     - Top 10 nomes problemáticos

USO:
  python qa_relatorios.py [--unificado controle_unificado.csv] [--test]

REGRAS CANÔNICAS:
  - Solicitante = Coordenador
  - Normalização NFKD → ASCII → lower
  - Idempotência garantida
  - Timezone: America/Fortaleza (UTC-3)
"""

import argparse
import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# =============================================================================
# NORMALIZAÇÃO E UTILITÁRIOS
# =============================================================================


def normalize_string(s: str) -> str:
    """
    Normaliza string: NFKD → ASCII (strip accents) → lower → strip.
    """
    import unicodedata

    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().strip()


def normalize_motivo(motivo: str) -> str:
    """
    Normaliza motivos de P01 para padrão unificado.

    Mapeamento:
      not_found_email → email_nao_encontrado
      multiple_match_email → multiplos_emails_encontrados
      not_found_formador → formador_nao_encontrado
      multiple_match_formador → multiplos_formadores_encontrados
      Outros → mantém original
    """
    motivo_lower = motivo.strip().lower()

    mapping = {
        "not_found_email": "email_nao_encontrado",
        "multiple_match_email": "multiplos_emails_encontrados",
        "not_found_formador": "formador_nao_encontrado",
        "multiple_match_formador": "multiplos_formadores_encontrados",
    }

    return mapping.get(motivo_lower, motivo)


# =============================================================================
# LEITURA DE CSVs
# =============================================================================


def read_csv_safe(filepath: Path, required: bool = True) -> List[Dict[str, Any]]:
    """
    Lê CSV com DictReader, retorna lista de dicts.
    Se required=False e arquivo não existe, retorna lista vazia.
    """
    if not filepath.exists():
        if required:
            raise FileNotFoundError(f"Arquivo obrigatório não encontrado: {filepath}")
        return []

    rows = []
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def write_csv(filepath: Path, rows: List[Dict[str, Any]], fieldnames: List[str]):
    """
    Escreve CSV com DictWriter.
    """
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# =============================================================================
# PROCESSAMENTO - PENDÊNCIAS UNIFICADAS
# =============================================================================


def build_pendencias_unificadas(
    pendencias_p01: List[Dict], pendencias_p04: List[Dict]
) -> List[Dict]:
    """
    Une pendencias.csv (P01) + pre_agenda_pendencias.csv (P04).

    Estrutura de saída:
      - origem: "P01" ou "P04"
      - motivo: normalizado
      - nome_original: valor original que causou a pendência
      - contexto: informações adicionais (linha, coluna, etc.)

    Ordenação: origem, motivo, nome_original
    """
    unified = []

    # P01: pendencias.csv
    # Campos esperados: linha, coluna, nome_original, motivo, contexto
    for row in pendencias_p01:
        unified.append(
            {
                "origem": "P01",
                "motivo": normalize_motivo(row.get("motivo", "")),
                "nome_original": row.get("nome_original", "").strip(),
                "contexto": row.get("contexto", "").strip(),
            }
        )

    # P04: pre_agenda_pendencias.csv
    # Campos esperados: event_id, motivo, detalhes
    for row in pendencias_p04:
        unified.append(
            {
                "origem": "P04",
                "motivo": normalize_motivo(row.get("motivo", "")),
                "nome_original": row.get("event_id", "").strip(),
                "contexto": row.get("detalhes", "").strip(),
            }
        )

    # Ordenação: origem, motivo, nome_original
    unified.sort(key=lambda x: (x["origem"], x["motivo"], x["nome_original"]))

    return unified


# =============================================================================
# PROCESSAMENTO - EVENTOS SEM EMAILS
# =============================================================================


def build_eventos_sem_emails(
    events: List[Dict], event_people: List[Dict]
) -> List[Dict]:
    """
    Detecta eventos sem solicitante_email ou sem attendees_emails.

    Critérios:
      - solicitante_email vazio/ausente
      - OU nenhum registro em event_people com email preenchido

    Ordenação: data, hora_inicio, municipio
    """
    # Index event_people por event_id
    people_by_event = defaultdict(list)
    for person in event_people:
        event_id = person.get("event_id", "").strip()
        email = person.get("email", "").strip()
        if event_id:
            people_by_event[event_id].append(email)

    sem_emails = []

    for event in events:
        event_id = event.get("event_id", "").strip()
        solicitante_email = event.get("solicitante_email", "").strip()

        # Emails de attendees
        attendees_emails = [e for e in people_by_event.get(event_id, []) if e]

        # Verifica se falta email
        if not solicitante_email or not attendees_emails:
            sem_emails.append(
                {
                    "event_id": event_id,
                    "data": event.get("data", ""),
                    "hora_inicio": event.get("hora_inicio", ""),
                    "hora_fim": event.get("hora_fim", ""),
                    "municipio": event.get("municipio", ""),
                    "projeto": event.get("projeto", ""),
                    "tipo": event.get("tipo", ""),
                    "solicitante_email": solicitante_email,
                    "attendees_count": str(len(attendees_emails)),
                    "problema": (
                        "sem_solicitante" if not solicitante_email else "sem_attendees"
                    ),
                }
            )

    # Ordenação: data, hora_inicio, municipio
    sem_emails.sort(key=lambda x: (x["data"], x["hora_inicio"], x["municipio"]))

    return sem_emails


# =============================================================================
# PROCESSAMENTO - DUPLICADOS
# =============================================================================


def build_duplicados(events: List[Dict]) -> List[Dict]:
    """
    Detecta eventos com external_hash duplicado (count > 1).

    Ordenação: external_hash, data, hora_inicio
    """
    # Conta ocorrências de external_hash
    hash_counts = Counter(
        e.get("external_hash", "") for e in events if e.get("external_hash")
    )

    duplicados = []

    for event in events:
        external_hash = event.get("external_hash", "").strip()
        if not external_hash:
            continue

        count = hash_counts[external_hash]
        if count > 1:
            duplicados.append(
                {
                    "external_hash": external_hash,
                    "event_id": event.get("event_id", ""),
                    "data": event.get("data", ""),
                    "hora_inicio": event.get("hora_inicio", ""),
                    "hora_fim": event.get("hora_fim", ""),
                    "municipio": event.get("municipio", ""),
                    "projeto": event.get("projeto", ""),
                    "tipo": event.get("tipo", ""),
                    "duplicatas_count": str(count),
                }
            )

    # Ordenação: external_hash, data, hora_inicio
    duplicados.sort(key=lambda x: (x["external_hash"], x["data"], x["hora_inicio"]))

    return duplicados


# =============================================================================
# GERAÇÃO DO RESUMO MARKDOWN
# =============================================================================


def build_resumo_md(
    pendencias_unificadas: List[Dict], sem_emails: List[Dict], duplicados: List[Dict]
) -> str:
    """
    Gera relatório Markdown com:
      - Contagens por origem/motivo
      - Eventos sem emails
      - Duplicados
      - Top 10 nomes problemáticos
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append("# Relatório de Qualidade - ETL Aprender Sistema (DAT)")
    md.append("")
    md.append(f"**Gerado em:** {now}")
    md.append("")
    md.append("---")
    md.append("")

    # 1. Pendências Unificadas
    md.append("## 1. Pendências Unificadas (P01 + P04)")
    md.append("")

    # Contagens por origem e motivo
    origem_counts = Counter(p["origem"] for p in pendencias_unificadas)
    motivo_counts = Counter(p["motivo"] for p in pendencias_unificadas)

    md.append(f"**Total de pendências:** {len(pendencias_unificadas)}")
    md.append("")
    md.append("### Por Origem:")
    md.append("")
    md.append("| Origem | Quantidade |")
    md.append("|--------|------------|")
    for origem, count in sorted(origem_counts.items()):
        md.append(f"| {origem} | {count} |")
    md.append("")

    md.append("### Por Motivo:")
    md.append("")
    md.append("| Motivo | Quantidade |")
    md.append("|--------|------------|")
    for motivo, count in sorted(motivo_counts.items(), key=lambda x: -x[1]):
        md.append(f"| {motivo} | {count} |")
    md.append("")

    # Top 10 nomes problemáticos
    nome_counts = Counter(
        p["nome_original"] for p in pendencias_unificadas if p["nome_original"]
    )
    top10_nomes = nome_counts.most_common(10)

    md.append("### Top 10 Nomes Problemáticos:")
    md.append("")
    md.append("| Nome Original | Ocorrências |")
    md.append("|---------------|-------------|")
    for nome, count in top10_nomes:
        md.append(f"| {nome} | {count} |")
    md.append("")

    # 2. Eventos Sem Emails
    md.append("---")
    md.append("")
    md.append("## 2. Eventos Sem Emails")
    md.append("")
    md.append(f"**Total:** {len(sem_emails)}")
    md.append("")

    sem_solicitante = sum(1 for e in sem_emails if e["problema"] == "sem_solicitante")
    sem_attendees = sum(1 for e in sem_emails if e["problema"] == "sem_attendees")

    md.append("| Problema | Quantidade |")
    md.append("|----------|------------|")
    md.append(f"| Sem solicitante_email | {sem_solicitante} |")
    md.append(f"| Sem attendees_emails | {sem_attendees} |")
    md.append("")

    if sem_emails:
        md.append("### Primeiros 10 eventos:")
        md.append("")
        md.append("| Data | Hora | Município | Projeto | Problema |")
        md.append("|------|------|-----------|---------|----------|")
        for event in sem_emails[:10]:
            md.append(
                f"| {event['data']} | {event['hora_inicio']} | "
                f"{event['municipio']} | {event['projeto']} | {event['problema']} |"
            )
        md.append("")

    # 3. Duplicados
    md.append("---")
    md.append("")
    md.append("## 3. Eventos Duplicados (por external_hash)")
    md.append("")

    # Conta hashes únicos duplicados
    unique_hashes = set(d["external_hash"] for d in duplicados)
    md.append(f"**Total de eventos duplicados:** {len(duplicados)}")
    md.append(f"**Hashes únicos duplicados:** {len(unique_hashes)}")
    md.append("")

    if duplicados:
        md.append("### Primeiros 10 duplicados:")
        md.append("")
        md.append(
            "| Hash (primeiros 8) | Data | Hora | Município | Projeto | Duplicatas |"
        )
        md.append(
            "|-------------------|------|------|-----------|---------|-----------|"
        )
        for dup in duplicados[:10]:
            hash_short = dup["external_hash"][:8]
            md.append(
                f"| {hash_short} | {dup['data']} | {dup['hora_inicio']} | "
                f"{dup['municipio']} | {dup['projeto']} | {dup['duplicatas_count']} |"
            )
        md.append("")

    md.append("---")
    md.append("")
    md.append("## Conclusão")
    md.append("")
    md.append(
        "Este relatório consolida as pendências e problemas de qualidade identificados"
    )
    md.append(
        "durante o processamento ETL das planilhas originais (Agenda, Disponibilidade,"
    )
    md.append("Controle) para o sistema Aprender.")
    md.append("")
    md.append("**Próximos passos:**")
    md.append("- Resolver pendências de matching (emails não encontrados)")
    md.append("- Corrigir eventos sem emails (solicitante ou attendees)")
    md.append("- Investigar e resolver duplicados")
    md.append("")

    return "\n".join(md)


# =============================================================================
# TESTES (--test)
# =============================================================================


def run_tests():
    """
    Executa testes unitários para validar normalização de motivos,
    detecção de emails ausentes, detecção de duplicados e ordenação.
    """
    print("🧪 Executando testes...")

    # Test 1: Normalização de motivos
    assert normalize_motivo("not_found_email") == "email_nao_encontrado"
    assert normalize_motivo("NOT_FOUND_EMAIL") == "email_nao_encontrado"
    assert normalize_motivo("multiple_match_email") == "multiplos_emails_encontrados"
    assert normalize_motivo("not_found_formador") == "formador_nao_encontrado"
    assert (
        normalize_motivo("multiple_match_formador")
        == "multiplos_formadores_encontrados"
    )
    assert normalize_motivo("outro_motivo") == "outro_motivo"
    print("  ✅ Normalização de motivos OK")

    # Test 2: Detecção de eventos sem emails
    events_test = [
        {
            "event_id": "E001",
            "data": "2025-01-15",
            "hora_inicio": "08:00:00",
            "municipio": "Fortaleza",
            "projeto": "ACerta",
            "tipo": "Formação",
            "solicitante_email": "",
            "external_hash": "abc123",
        },
        {
            "event_id": "E002",
            "data": "2025-01-16",
            "hora_inicio": "09:00:00",
            "municipio": "Sobral",
            "projeto": "Vida",
            "tipo": "Workshop",
            "solicitante_email": "coord@example.com",
            "external_hash": "def456",
        },
    ]

    people_test = [
        {"event_id": "E002", "email": "form1@example.com"},
    ]

    # E001: sem solicitante_email
    # E002: tem solicitante E tem 1 attendee → NÃO deve aparecer
    sem_emails_test = build_eventos_sem_emails(events_test, people_test)
    assert len(sem_emails_test) == 1
    assert sem_emails_test[0]["event_id"] == "E001"
    assert sem_emails_test[0]["problema"] == "sem_solicitante"

    # Teste sem attendees: ambos devem aparecer
    sem_emails_test2 = build_eventos_sem_emails(events_test, [])
    assert len(sem_emails_test2) == 2  # E001 sem solicitante, E002 sem attendees
    print("  ✅ Detecção de eventos sem emails OK")

    # Test 3: Detecção de duplicados
    events_dup_test = [
        {
            "event_id": "E001",
            "external_hash": "hash1",
            "data": "2025-01-15",
            "hora_inicio": "08:00:00",
            "municipio": "Fortaleza",
            "projeto": "ACerta",
            "tipo": "Formação",
        },
        {
            "event_id": "E002",
            "external_hash": "hash1",
            "data": "2025-01-15",
            "hora_inicio": "08:00:00",
            "municipio": "Fortaleza",
            "projeto": "ACerta",
            "tipo": "Formação",
        },
        {
            "event_id": "E003",
            "external_hash": "hash2",
            "data": "2025-01-16",
            "hora_inicio": "09:00:00",
            "municipio": "Sobral",
            "projeto": "Vida",
            "tipo": "Workshop",
        },
    ]

    duplicados_test = build_duplicados(events_dup_test)
    assert len(duplicados_test) == 2  # E001 e E002 são duplicados
    assert all(d["external_hash"] == "hash1" for d in duplicados_test)
    assert duplicados_test[0]["duplicatas_count"] == "2"
    print("  ✅ Detecção de duplicados OK")

    # Test 4: Ordenação de pendências
    pend_test = [
        {
            "origem": "P04",
            "motivo": "email_nao_encontrado",
            "nome_original": "Zeca",
            "contexto": "",
        },
        {
            "origem": "P01",
            "motivo": "formador_nao_encontrado",
            "nome_original": "Ana",
            "contexto": "",
        },
        {
            "origem": "P01",
            "motivo": "email_nao_encontrado",
            "nome_original": "Bruno",
            "contexto": "",
        },
    ]
    pend_test.sort(key=lambda x: (x["origem"], x["motivo"], x["nome_original"]))
    assert pend_test[0]["nome_original"] == "Bruno"  # P01, email_nao_encontrado
    assert pend_test[1]["nome_original"] == "Ana"  # P01, formador_nao_encontrado
    assert pend_test[2]["nome_original"] == "Zeca"  # P04, email_nao_encontrado
    print("  ✅ Ordenação de pendências OK")

    print("✅ Todos os testes passaram!")


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="DAT-P05: Consolida pendências e gera relatórios de qualidade",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--unificado",
        type=str,
        default="",
        help="Caminho opcional para controle_unificado.csv (não usado nesta versão)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Executa testes unitários e sai",
    )

    args = parser.parse_args()

    if args.test:
        run_tests()
        sys.exit(0)

    print("📊 DAT-P05: Consolidação de Pendências e Relatórios de Qualidade")
    print("=" * 70)

    # Caminhos dos arquivos
    base_path = Path(".")

    events_csv = base_path / "events.csv"
    event_people_csv = base_path / "event_people.csv"
    pendencias_p01_csv = base_path / "pendencias.csv"
    pre_agenda_csv = base_path / "pre_agenda.csv"
    pre_agenda_pendencias_csv = base_path / "pre_agenda_pendencias.csv"

    # Opcional
    controle_unificado_csv = base_path / args.unificado if args.unificado else None

    # Saídas
    out_pendencias = base_path / "qa_pendencias_unificadas.csv"
    out_sem_emails = base_path / "qa_eventos_sem_emails.csv"
    out_duplicados = base_path / "qa_duplicados.csv"
    out_resumo_md = base_path / "qa_resumo.md"

    # Leitura de CSVs obrigatórios
    print("\n📂 Lendo arquivos de entrada...")

    events = read_csv_safe(events_csv, required=True)
    print(f"  ✅ events.csv: {len(events)} registros")

    event_people = read_csv_safe(event_people_csv, required=True)
    print(f"  ✅ event_people.csv: {len(event_people)} registros")

    pendencias_p01 = read_csv_safe(pendencias_p01_csv, required=True)
    print(f"  ✅ pendencias.csv: {len(pendencias_p01)} registros")

    pre_agenda = read_csv_safe(pre_agenda_csv, required=True)
    print(f"  ✅ pre_agenda.csv: {len(pre_agenda)} registros")

    pre_agenda_pendencias = read_csv_safe(pre_agenda_pendencias_csv, required=True)
    print(f"  ✅ pre_agenda_pendencias.csv: {len(pre_agenda_pendencias)} registros")

    # Opcional
    if controle_unificado_csv and controle_unificado_csv.exists():
        controle_unificado = read_csv_safe(controle_unificado_csv, required=False)
        print(f"  ✅ controle_unificado.csv: {len(controle_unificado)} registros")
    else:
        print("  ℹ️  controle_unificado.csv: não fornecido (opcional)")

    # 1. Pendências Unificadas
    print("\n🔄 Processando pendências unificadas...")
    pendencias_unificadas = build_pendencias_unificadas(
        pendencias_p01, pre_agenda_pendencias
    )
    print(f"  ✅ {len(pendencias_unificadas)} pendências unificadas")

    # 2. Eventos Sem Emails
    print("\n🔄 Detectando eventos sem emails...")
    sem_emails = build_eventos_sem_emails(events, event_people)
    print(f"  ✅ {len(sem_emails)} eventos sem emails")

    # 3. Duplicados
    print("\n🔄 Detectando eventos duplicados...")
    duplicados = build_duplicados(events)
    print(f"  ✅ {len(duplicados)} eventos duplicados")

    # 4. Resumo Markdown
    print("\n🔄 Gerando resumo Markdown...")
    resumo_md = build_resumo_md(pendencias_unificadas, sem_emails, duplicados)

    # Escrita de CSVs
    print("\n💾 Escrevendo arquivos de saída...")

    if pendencias_unificadas:
        write_csv(
            out_pendencias,
            pendencias_unificadas,
            ["origem", "motivo", "nome_original", "contexto"],
        )
        print(f"  ✅ {out_pendencias}")
    else:
        print(f"  ⚠️  Nenhuma pendência para escrever")

    if sem_emails:
        write_csv(
            out_sem_emails,
            sem_emails,
            [
                "event_id",
                "data",
                "hora_inicio",
                "hora_fim",
                "municipio",
                "projeto",
                "tipo",
                "solicitante_email",
                "attendees_count",
                "problema",
            ],
        )
        print(f"  ✅ {out_sem_emails}")
    else:
        print(f"  ⚠️  Nenhum evento sem email para escrever")

    if duplicados:
        write_csv(
            out_duplicados,
            duplicados,
            [
                "external_hash",
                "event_id",
                "data",
                "hora_inicio",
                "hora_fim",
                "municipio",
                "projeto",
                "tipo",
                "duplicatas_count",
            ],
        )
        print(f"  ✅ {out_duplicados}")
    else:
        print(f"  ⚠️  Nenhum duplicado para escrever")

    # Escrever Markdown
    with open(out_resumo_md, "w", encoding="utf-8") as f:
        f.write(resumo_md)
    print(f"  ✅ {out_resumo_md}")

    print("\n" + "=" * 70)
    print("✅ Processamento concluído com sucesso!")
    print("\n📊 Resumo:")
    print(f"  - Pendências unificadas: {len(pendencias_unificadas)}")
    print(f"  - Eventos sem emails: {len(sem_emails)}")
    print(f"  - Eventos duplicados: {len(duplicados)}")
    print(f"\n📄 Veja detalhes em: {out_resumo_md}")
    print("=" * 70)


if __name__ == "__main__":
    main()
