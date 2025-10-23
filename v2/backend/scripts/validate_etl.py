#!/usr/bin/env python
"""
Script de validação do ETL
Valida contagens, integridade referencial e regras de negócio
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Count, Q
from apps.core.models import (
    Usuario, Municipio, Projeto, TipoEvento,
    Solicitacao, Participation, AvailabilityBlock, Deslocamento
)


def print_section(title):
    """Print section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def validate_counts():
    """Valida contagens esperadas vs reais"""
    print_section("1. VALIDAÇÃO DE CONTAGENS")

    # Contagens esperadas baseadas na Sessão 2
    expected = {
        'Usuários': (117, 117),  # (min, max)
        'Municípios': (87, 87),
        'Projetos': (31, 31),
        'Tipos de Evento': (1, 10),  # Pelo menos 1 (default)
        'Solicitações': (1500, 1700),  # ~1625
        'Participações': (1800, 2000),  # ~1915
        'Bloqueios': (0, 100),  # Esperado 0 (sem dados na planilha)
        'Deslocamentos': (0, 100),  # Esperado 0 (sem dados na planilha)
    }

    models = {
        'Usuários': Usuario,
        'Municípios': Municipio,
        'Projetos': Projeto,
        'Tipos de Evento': TipoEvento,
        'Solicitações': Solicitacao,
        'Participações': Participation,
        'Bloqueios': AvailabilityBlock,
        'Deslocamentos': Deslocamento,
    }

    results = []
    all_ok = True

    for name, model in models.items():
        count = model.objects.count()
        min_exp, max_exp = expected[name]

        if min_exp <= count <= max_exp:
            status = "✅"
            ok = True
        else:
            status = "❌"
            ok = False
            all_ok = False

        results.append({
            'name': name,
            'count': count,
            'expected': f"{min_exp}-{max_exp}",
            'status': status,
            'ok': ok
        })

        print(f"{status} {name:20} {count:6} (esperado: {min_exp}-{max_exp})")

    total = sum(r['count'] for r in results)
    print(f"\n{'─' * 80}")
    print(f"   {'TOTAL GERAL:':20} {total:6} registros")
    print(f"{'─' * 80}")

    return all_ok


def validate_referential_integrity():
    """Valida integridade referencial (FKs órfãos)"""
    print_section("2. VALIDAÇÃO DE INTEGRIDADE REFERENCIAL")

    all_ok = True

    # 1. Solicitações sem município
    orphan_solicitacoes_municipio = Solicitacao.objects.filter(municipio__isnull=True).count()
    if orphan_solicitacoes_municipio > 0:
        print(f"❌ {orphan_solicitacoes_municipio} Solicitações sem município")
        all_ok = False
    else:
        print(f"✅ Todas solicitações têm município")

    # 2. Solicitações sem projeto
    orphan_solicitacoes_projeto = Solicitacao.objects.filter(projeto__isnull=True).count()
    if orphan_solicitacoes_projeto > 0:
        print(f"❌ {orphan_solicitacoes_projeto} Solicitações sem projeto")
        all_ok = False
    else:
        print(f"✅ Todas solicitações têm projeto")

    # 3. Solicitações sem tipo_evento
    orphan_solicitacoes_tipo = Solicitacao.objects.filter(tipo_evento__isnull=True).count()
    if orphan_solicitacoes_tipo > 0:
        print(f"❌ {orphan_solicitacoes_tipo} Solicitações sem tipo de evento")
        all_ok = False
    else:
        print(f"✅ Todas solicitações têm tipo de evento")

    # 4. Participações sem usuário (exceto convidados)
    orphan_participations = Participation.objects.filter(
        usuario__isnull=True,
        guest_email__isnull=True
    ).count()
    if orphan_participations > 0:
        print(f"❌ {orphan_participations} Participações sem usuário nem email")
        all_ok = False
    else:
        print(f"✅ Todas participações têm usuário ou email")

    # 5. Participações sem solicitação (impossível por FK, mas verificar)
    orphan_participations_sol = Participation.objects.filter(solicitacao__isnull=True).count()
    if orphan_participations_sol > 0:
        print(f"❌ {orphan_participations_sol} Participações sem solicitação")
        all_ok = False
    else:
        print(f"✅ Todas participações têm solicitação")

    return all_ok


def validate_business_rules():
    """Valida regras de negócio"""
    print_section("3. VALIDAÇÃO DE REGRAS DE NEGÓCIO")

    all_ok = True

    # 1. Datas inválidas (fim < início)
    invalid_dates = Solicitacao.objects.filter(fim__lt=Q(inicio=Q(inicio))).count()
    if invalid_dates > 0:
        print(f"❌ {invalid_dates} Solicitações com data fim < início")
        all_ok = False
    else:
        print(f"✅ Todas solicitações têm datas válidas (fim >= início)")

    # 2. Solicitações sem participações
    no_participations = Solicitacao.objects.annotate(
        num_parts=Count('participations')
    ).filter(num_parts=0).count()

    if no_participations > 0:
        print(f"⚠️  {no_participations} Solicitações sem participações (pode ser normal)")
    else:
        print(f"✅ Todas solicitações têm pelo menos 1 participação")

    # 3. CPFs duplicados
    duplicate_cpfs = Usuario.objects.exclude(cpf='').values('cpf').annotate(
        count=Count('id')
    ).filter(count__gt=1).count()

    if duplicate_cpfs > 0:
        print(f"❌ {duplicate_cpfs} CPFs duplicados")
        all_ok = False
    else:
        print(f"✅ Nenhum CPF duplicado")

    # 4. Emails duplicados
    duplicate_emails = Usuario.objects.values('email').annotate(
        count=Count('id')
    ).filter(count__gt=1).count()

    if duplicate_emails > 0:
        print(f"❌ {duplicate_emails} Emails duplicados")
        all_ok = False
    else:
        print(f"✅ Nenhum email duplicado")

    # 5. Municípios sem UF (pode ser normal para alguns casos como "AMIGOS DO BEM")
    no_uf = Municipio.objects.filter(Q(uf='') | Q(uf__isnull=True)).count()
    if no_uf > 0:
        print(f"ℹ️  {no_uf} Municípios sem UF (pode ser normal)")
    else:
        print(f"✅ Todos municípios têm UF")

    return all_ok


def generate_statistics():
    """Gera estatísticas sobre os dados importados"""
    print_section("4. ESTATÍSTICAS DOS DADOS IMPORTADOS")

    # 1. Solicitações por status
    print("📊 Solicitações por status:")
    for status in Solicitacao.objects.values('status').annotate(
        total=Count('id')
    ).order_by('-total'):
        print(f"   {status['status']:15} {status['total']:5}")

    # 2. Top 5 projetos
    print("\n📊 Top 5 projetos com mais solicitações:")
    for proj in Solicitacao.objects.values('projeto__nome').annotate(
        total=Count('id')
    ).order_by('-total')[:5]:
        print(f"   {proj['projeto__nome']:30} {proj['total']:5}")

    # 3. Top 5 municípios
    print("\n📊 Top 5 municípios com mais solicitações:")
    for mun in Solicitacao.objects.values('municipio__nome', 'municipio__uf').annotate(
        total=Count('id')
    ).order_by('-total')[:5]:
        uf = mun['municipio__uf'] or '??'
        print(f"   {mun['municipio__nome']:25} - {uf:2}  {mun['total']:5}")

    # 4. Participações por solicitação
    stats = Solicitacao.objects.annotate(
        num_parts=Count('participations')
    ).values('num_parts').annotate(count=Count('id')).order_by('num_parts')

    if stats:
        total_parts = sum(s['num_parts'] * s['count'] for s in stats)
        total_sols = sum(s['count'] for s in stats)
        avg_parts = total_parts / total_sols if total_sols > 0 else 0

        print(f"\n📊 Participações por solicitação:")
        print(f"   Média: {avg_parts:.1f} participações/solicitação")

        # Distribuição
        print(f"\n   Distribuição:")
        for s in stats[:10]:  # Mostrar primeiros 10
            print(f"   {s['num_parts']:2} participações: {s['count']:5} solicitações")

    # 5. Usuários mais ativos (top formadores)
    print("\n📊 Top 5 formadores mais ativos:")
    for user in Participation.objects.filter(role='FORMADOR').values(
        'usuario__first_name', 'usuario__last_name'
    ).annotate(total=Count('id')).order_by('-total')[:5]:
        nome = f"{user['usuario__first_name']} {user['usuario__last_name']}"
        print(f"   {nome:30} {user['total']:5} participações")


def main():
    """Executa todas as validações"""
    print("\n" + "=" * 80)
    print("  VALIDAÇÃO DO ETL - Aprender Sistema v2")
    print("=" * 80)

    results = []

    # Executar validações
    results.append(("Contagens", validate_counts()))
    results.append(("Integridade Referencial", validate_referential_integrity()))
    results.append(("Regras de Negócio", validate_business_rules()))

    # Gerar estatísticas
    generate_statistics()

    # Resumo final
    print_section("5. RESUMO FINAL")

    all_ok = all(ok for _, ok in results)

    for name, ok in results:
        status = "✅ PASSOU" if ok else "❌ FALHOU"
        print(f"{status:12} {name}")

    print(f"\n{'─' * 80}")
    if all_ok:
        print("✅ TODAS AS VALIDAÇÕES PASSARAM!")
        print("📊 O ETL está pronto para produção.")
        exit_code = 0
    else:
        print("❌ ALGUMAS VALIDAÇÕES FALHARAM")
        print("⚠️  Revisar problemas acima antes do deploy.")
        exit_code = 1

    print(f"{'─' * 80}\n")

    return exit_code


if __name__ == '__main__':
    exit(main())
