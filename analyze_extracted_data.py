#!/usr/bin/env python
"""
Análise detalhada dos dados extraídos para padronização
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


class SimpleJSONLoader:
    """Loader simples para análise sem dependências Django"""

    def __init__(self):
        self.base_path = Path(".")

    def load_extracted_data(self, filename):
        with open(self.base_path / filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_records_as_dicts(self, filename, worksheet_name):
        data = self.load_extracted_data(filename)
        worksheet_data = data["worksheets"][worksheet_name]
        headers = worksheet_data["headers"]
        records = worksheet_data["data"]

        result = []
        for record in records:
            record_dict = {}
            for i, header in enumerate(headers):
                value = record[i] if i < len(record) else ""
                record_dict[header] = (
                    value.strip() if isinstance(value, str) else str(value)
                )
            result.append(record_dict)

        return result


json_loader = SimpleJSONLoader()


def analyze_usuarios_structure():
    """Analisa estrutura detalhada dos dados de usuários"""

    print("=== ANÁLISE ESTRUTURAL: USUÁRIOS ===\n")

    try:
        # Carregar dados
        data = json_loader.load_extracted_data("extracted_usuarios.json")
        worksheets = data.get("worksheets", {})

        all_fields = set()
        field_samples = defaultdict(list)

        for ws_name, ws_data in worksheets.items():
            print(f"--- ABA: {ws_name} ---")
            headers = ws_data.get("headers", [])
            records = ws_data.get("data", [])

            print(f"Headers: {headers}")
            print(f"Registros: {len(records)}")

            # Coletar todos os campos únicos
            all_fields.update(headers)

            # Samples de cada campo
            for record in records[:3]:  # Primeiros 3 registros
                for i, field in enumerate(headers):
                    value = record[i] if i < len(record) else ""
                    if value and field not in field_samples:
                        field_samples[field].append(value)

            print()

        # Resumo de todos os campos
        print("=== TODOS OS CAMPOS ENCONTRADOS ===")
        for field in sorted(all_fields):
            samples = field_samples.get(field, ["N/A"])
            print(f"{field}: {samples[0] if samples else 'N/A'}")

        return all_fields, field_samples

    except Exception as e:
        print(f"ERRO: {e}")
        return set(), {}


def analyze_data_quality():
    """Analisa qualidade dos dados para migração"""

    print("\n=== ANÁLISE DE QUALIDADE DOS DADOS ===\n")

    try:
        records = json_loader.get_records_as_dicts("extracted_usuarios.json", "Ativos")

        # Estatísticas por campo
        stats = defaultdict(
            lambda: {
                "total": 0,
                "preenchidos": 0,
                "vazios": 0,
                "unicos": set(),
                "samples": [],
            }
        )

        for record in records:
            for field, value in record.items():
                stats[field]["total"] += 1

                if value and str(value).strip():
                    stats[field]["preenchidos"] += 1
                    stats[field]["unicos"].add(value)
                    if len(stats[field]["samples"]) < 3:
                        stats[field]["samples"].append(value)
                else:
                    stats[field]["vazios"] += 1

        # Relatório por campo
        for field, data in stats.items():
            preenchimento = (
                (data["preenchidos"] / data["total"]) * 100 if data["total"] > 0 else 0
            )
            unicidade = len(data["unicos"])

            print(f"{field}:")
            print(f"  Total: {data['total']}")
            print(f"  Preenchidos: {data['preenchidos']} ({preenchimento:.1f}%)")
            print(f"  Valores únicos: {unicidade}")
            print(f"  Samples: {data['samples'][:2]}")
            print()

        return stats

    except Exception as e:
        print(f"ERRO: {e}")
        return {}


def analyze_cpf_patterns():
    """Analisa padrões de CPF para validação"""

    print("=== ANÁLISE DE CPF ===\n")

    try:
        records = json_loader.get_records_as_dicts("extracted_usuarios.json", "Ativos")

        cpf_patterns = {
            "com_pontuacao": 0,
            "sem_pontuacao": 0,
            "invalidos": 0,
            "duplicados": Counter(),
            "samples": [],
        }

        for record in records:
            cpf = record.get("CPF", "").strip()

            if not cpf:
                continue

            # Contar padrão
            if re.match(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$", cpf):
                cpf_patterns["com_pontuacao"] += 1
            elif re.match(r"^\d{11}$", cpf):
                cpf_patterns["sem_pontuacao"] += 1
            else:
                cpf_patterns["invalidos"] += 1

            # CPF limpo para detectar duplicatas
            cpf_limpo = re.sub(r"[^\d]", "", cpf)
            cpf_patterns["duplicados"][cpf_limpo] += 1

            # Amostras
            if len(cpf_patterns["samples"]) < 5:
                cpf_patterns["samples"].append(cpf)

        print(f"CPFs com pontuação: {cpf_patterns['com_pontuacao']}")
        print(f"CPFs sem pontuação: {cpf_patterns['sem_pontuacao']}")
        print(f"CPFs inválidos: {cpf_patterns['invalidos']}")

        duplicados = [
            cpf for cpf, count in cpf_patterns["duplicados"].items() if count > 1
        ]
        print(f"CPFs duplicados: {len(duplicados)}")
        if duplicados:
            print(f"Exemplos: {duplicados[:3]}")

        print(f"Samples: {cpf_patterns['samples']}")

        return cpf_patterns

    except Exception as e:
        print(f"ERRO: {e}")
        return {}


def analyze_email_patterns():
    """Analisa padrões de email"""

    print("\n=== ANÁLISE DE EMAIL ===\n")

    try:
        records = json_loader.get_records_as_dicts("extracted_usuarios.json", "Ativos")

        email_stats = {
            "total": 0,
            "validos": 0,
            "invalidos": 0,
            "dominios": Counter(),
            "duplicados": Counter(),
            "samples_invalidos": [],
        }

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        for record in records:
            email = record.get("Email", "").strip().lower()

            if not email:
                continue

            email_stats["total"] += 1

            if re.match(email_pattern, email):
                email_stats["validos"] += 1
                dominio = email.split("@")[1] if "@" in email else "unknown"
                email_stats["dominios"][dominio] += 1
            else:
                email_stats["invalidos"] += 1
                if len(email_stats["samples_invalidos"]) < 3:
                    email_stats["samples_invalidos"].append(email)

            email_stats["duplicados"][email] += 1

        print(f"Total de emails: {email_stats['total']}")
        print(f"Emails válidos: {email_stats['validos']}")
        print(f"Emails inválidos: {email_stats['invalidos']}")

        duplicados = [
            email for email, count in email_stats["duplicados"].items() if count > 1
        ]
        print(f"Emails duplicados: {len(duplicados)}")

        print(f"Domínios mais comuns:")
        for dominio, count in email_stats["dominios"].most_common(5):
            print(f"  {dominio}: {count}")

        if email_stats["samples_invalidos"]:
            print(f"Samples inválidos: {email_stats['samples_invalidos']}")

        return email_stats

    except Exception as e:
        print(f"ERRO: {e}")
        return {}


def analyze_perfil_distribution():
    """Analisa distribuição de perfis/roles"""

    print("\n=== ANÁLISE DE PERFIS ===\n")

    try:
        # Analisar todas as abas para entender perfis
        data = json_loader.load_extracted_data("extracted_usuarios.json")
        worksheets = data.get("worksheets", {})

        perfis_por_aba = {}

        for ws_name, ws_data in worksheets.items():
            print(f"--- ABA: {ws_name} ---")

            records = json_loader.get_records_as_dicts(
                "extracted_usuarios.json", ws_name
            )

            # Contar registros por aba (isso já indica o perfil)
            perfis_por_aba[ws_name] = len(records)

            # Verificar se tem campo Perfil explícito
            perfis_explicitos = Counter()
            for record in records:
                perfil = record.get("Perfil", "").strip()
                if perfil:
                    perfis_explicitos[perfil] += 1

            print(f"Total: {len(records)}")
            if perfis_explicitos:
                print(f"Perfis explícitos: {dict(perfis_explicitos)}")
            else:
                print("Perfil implícito pela aba")
            print()

        # Mapeamento sugerido
        mapeamento_sugerido = {
            "Ativos": "coordenador",  # Padrão mais restritivo
            "Inativos": "coordenador",
            "Pendentes": "coordenador",
        }

        print("=== MAPEAMENTO SUGERIDO PARA DJANGO GROUPS ===")
        for aba, perfil in mapeamento_sugerido.items():
            count = perfis_por_aba.get(aba, 0)
            print(f"{aba} ({count} usuários) → Group '{perfil}'")

        return perfis_por_aba, mapeamento_sugerido

    except Exception as e:
        print(f"ERRO: {e}")
        return {}, {}


def generate_transformation_strategy():
    """Gera estratégia de transformação baseada na análise"""

    print("\n=== ESTRATÉGIA DE TRANSFORMAÇÃO ===\n")

    strategy = {
        "model_extensions": [
            "cpf = models.CharField(max_length=11, unique=True, blank=True)",
            "telefone = models.CharField(max_length=15, blank=True)",
            'municipio = models.ForeignKey("Municipio", null=True, blank=True, on_delete=models.SET_NULL)',
        ],
        "field_mapping": {
            "Nome Completo → first_name + last_name": "Dividir em partes",
            "Email → username + email": "Email como username único",
            "CPF → cpf": "Limpar formato (apenas números)",
            "Telefone → telefone": "Padronizar formato",
            "Aba → groups": "Mapear para Django Groups",
        },
        "data_cleaning": [
            "Normalizar CPF (remover pontuação)",
            "Validar formato de email",
            "Padronizar telefones (DDD + número)",
            "Dividir nome completo adequadamente",
            "Tratar valores vazios",
        ],
        "groups_creation": ["superintendencia", "coordenador", "formador", "admin"],
    }

    for category, items in strategy.items():
        print(f"{category.upper().replace('_', ' ')}:")
        for item in items:
            if isinstance(item, dict):
                for k, v in item.items():
                    print(f"  {k}: {v}")
            else:
                print(f"  - {item}")
        print()

    return strategy


if __name__ == "__main__":
    print("Iniciando análise completa dos dados extraídos...\n")

    # Executar todas as análises
    fields, samples = analyze_usuarios_structure()
    quality_stats = analyze_data_quality()
    cpf_analysis = analyze_cpf_patterns()
    email_analysis = analyze_email_patterns()
    perfis, mapping = analyze_perfil_distribution()
    strategy = generate_transformation_strategy()

    print("\n" + "=" * 50)
    print("ANÁLISE COMPLETA FINALIZADA")
    print("=" * 50)
    print("Próximo passo: Implementar pipeline de transformação")
