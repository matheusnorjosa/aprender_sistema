#!/usr/bin/env python3
"""
Validate that all endpoints in API_REFERENCE.md have status badges.

Usage:
    python scripts/validate_api_badges.py

Exit codes:
    0 - All endpoints have badges
    1 - Some endpoints missing badges
"""
import re
import sys
from pathlib import Path


def validate_api_reference() -> bool:
    """Validate that all endpoints have status badges."""
    api_ref_path = Path("v2/docs/API_REFERENCE.md")

    if not api_ref_path.exists():
        print("[ERROR] API_REFERENCE.md nao encontrado")
        return False

    api_ref = api_ref_path.read_text(encoding="utf-8")

    # Find all table rows with endpoints
    # Format: | METHOD | `/endpoint/` | ... |
    endpoint_pattern = r"\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \|"
    endpoints = re.findall(endpoint_pattern, api_ref)

    if not endpoints:
        print("[WARN] Nenhum endpoint encontrado no formato esperado")
        return True

    # Badge pattern - matches shields.io badges
    badge_pattern = r"!\[.*?\]\(https://img\.shields\.io/badge/[^)]+\)"

    missing_badges = []
    has_badges = []

    for method, endpoint in endpoints:
        # Find the complete table row for this endpoint
        # The row should have: | METHOD | `endpoint` | STATUS | DESC | PERM |
        escaped_endpoint = re.escape(endpoint)
        row_pattern = rf"\| {method} \| `{escaped_endpoint}` \|([^\n]*)\|"
        match = re.search(row_pattern, api_ref)

        if match:
            row_content = match.group(1)
            if re.search(badge_pattern, row_content):
                has_badges.append(f"{method} {endpoint}")
            else:
                missing_badges.append(f"{method} {endpoint}")

    # Report results
    total = len(endpoints)
    with_badges = len(has_badges)
    without_badges = len(missing_badges)

    print(f"\n=== Resultado da Validacao ===")
    print(f"    Total de endpoints: {total}")
    print(f"    Com badge: {with_badges}")
    print(f"    Sem badge: {without_badges}")

    if missing_badges:
        print(f"\n[ERROR] Endpoints sem badge de status ({without_badges}):")
        for ep in missing_badges[:20]:  # Limit output
            print(f"   - {ep}")
        if len(missing_badges) > 20:
            print(f"   ... e mais {len(missing_badges) - 20}")
        return False

    print(f"\n[OK] Todos os {total} endpoints tem badge de status")
    return True


if __name__ == "__main__":
    success = validate_api_reference()
    sys.exit(0 if success else 1)
