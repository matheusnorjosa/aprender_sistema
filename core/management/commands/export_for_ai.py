"""
Command para exportar dados do Aprender Sistema para alimentar o Oráculo AI
"""

import csv
import json
import os
from datetime import date, datetime
from typing import Any, Dict, List

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q

from core.models import Formador, Municipio, Projeto, TipoEvento, Usuario


class BusinessJSONEncoder(DjangoJSONEncoder):
    """Encoder customizado para dados de negócio"""

    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class Command(BaseCommand):
    """
    Exporta dados estruturados do Aprender Sistema para alimentar o Oráculo AI

    Uso:
        python manage.py export_for_ai --domain=usuarios --format=json
        python manage.py export_for_ai --domain=all --format=csv --output=/path/
        python manage.py export_for_ai --domain=business_context --for-oraculo
    """

    help = "Exporta dados estruturados para alimentar Oráculo AI"

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            type=str,
            choices=[
                "usuarios",
                "municipios",
                "formadores",
                "projetos",
                "business_context",
                "all",
            ],
            default="business_context",
            help="Domínio de dados para exportar",
        )

        parser.add_argument(
            "--format",
            type=str,
            choices=["json", "csv", "business_summary"],
            default="business_summary",
            help="Formato de exportação",
        )

        parser.add_argument(
            "--output", type=str, help="Diretório de saída (default: pasta atual)"
        )

        parser.add_argument(
            "--for-oraculo",
            action="store_true",
            help="Otimizar exportação para consumo pelo Oráculo",
        )

        parser.add_argument(
            "--anonymize",
            action="store_true",
            help="Anonimizar dados sensíveis (CPF, emails completos)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== EXPORTAÇÃO PARA ORÁCULO AI ==="))

        domain = options["domain"]
        format_type = options["format"]
        output_dir = options.get("output") or "."
        for_oraculo = options.get("for_oraculo", False)
        anonymize = options.get("anonymize", False)

        if domain == "all":
            return self.export_all_domains(
                format_type, output_dir, for_oraculo, anonymize
            )

        # Exportar domínio específico
        export_data = self.get_domain_data(domain, anonymize)

        if format_type == "business_summary" or for_oraculo:
            return self.export_business_summary(export_data, domain, output_dir)
        elif format_type == "json":
            return self.export_json(export_data, domain, output_dir)
        elif format_type == "csv":
            return self.export_csv(export_data, domain, output_dir)

    def get_domain_data(self, domain: str, anonymize: bool = False) -> Dict[str, Any]:
        """Obtém dados estruturados por domínio"""

        if domain == "usuarios":
            return self.get_usuarios_data(anonymize)
        elif domain == "municipios":
            return self.get_municipios_data()
        elif domain == "formadores":
            return self.get_formadores_data(anonymize)
        elif domain == "projetos":
            return self.get_projetos_data()
        elif domain == "business_context":
            return self.get_business_context()

        return {}

    def get_usuarios_data(self, anonymize: bool = False) -> Dict[str, Any]:
        """Dados estruturados de usuários para IA"""

        usuarios = Usuario.objects.select_related("municipio").prefetch_related(
            "groups"
        )

        # Estatísticas gerais
        stats = {
            "total_usuarios": usuarios.count(),
            "usuarios_ativos": usuarios.filter(is_active=True).count(),
            "usuarios_por_grupo": {},
        }

        # Contar por grupos
        for group in Group.objects.all():
            count = usuarios.filter(groups=group).count()
            if count > 0:
                stats["usuarios_por_grupo"][group.name] = count

        # Lista de usuários (anonimizada se solicitado)
        usuarios_data = []
        for user in usuarios:
            user_data = {
                "id": user.id,
                "nome": user.first_name,
                "nome_completo": user.nome_completo,
                "email": self.anonymize_email(user.email) if anonymize else user.email,
                "cpf": (
                    self.anonymize_cpf(user.cpf) if anonymize and user.cpf else user.cpf
                ),
                "telefone": user.telefone,
                "municipio": user.municipio.nome if user.municipio else None,
                "grupos": list(user.groups.values_list("name", flat=True)),
                "ativo": user.is_active,
                "data_cadastro": user.date_joined,
            }
            usuarios_data.append(user_data)

        return {
            "dominio": "usuarios",
            "data_exportacao": datetime.now().isoformat(),
            "estatisticas": stats,
            "usuarios": usuarios_data,
            "anonimizado": anonymize,
        }

    def get_municipios_data(self) -> Dict[str, Any]:
        """Dados de municípios e cobertura geográfica"""

        municipios = Municipio.objects.all()

        municipios_data = []
        for municipio in municipios:
            # Contar usuários por município
            usuarios_count = Usuario.objects.filter(municipio=municipio).count()

            municipio_data = {
                "id": str(municipio.id),
                "nome": municipio.nome,
                "estado": getattr(municipio, "estado", None),
                "regiao": getattr(municipio, "regiao", None),
                "usuarios_vinculados": usuarios_count,
                "ativo": getattr(municipio, "ativo", True),
            }
            municipios_data.append(municipio_data)

        return {
            "dominio": "municipios",
            "data_exportacao": datetime.now().isoformat(),
            "total_municipios": len(municipios_data),
            "municipios": municipios_data,
        }

    def get_formadores_data(self, anonymize: bool = False) -> Dict[str, Any]:
        """Dados específicos de formadores"""

        formadores = Formador.objects.select_related("usuario", "municipio_base")

        formadores_data = []
        for formador in formadores:
            formador_data = {
                "id": str(formador.id),
                "nome": formador.nome,
                "email": (
                    self.anonymize_email(formador.email)
                    if anonymize
                    else formador.email
                ),
                "municipio_base": (
                    formador.municipio_base.nome if formador.municipio_base else None
                ),
                "especialidades": getattr(formador, "especialidades", []),
                "ativo": formador.ativo,
                "data_cadastro": (
                    formador.created_at if hasattr(formador, "created_at") else None
                ),
            }
            formadores_data.append(formador_data)

        return {
            "dominio": "formadores",
            "data_exportacao": datetime.now().isoformat(),
            "total_formadores": len(formadores_data),
            "formadores": formadores_data,
            "anonimizado": anonymize,
        }

    def get_projetos_data(self) -> Dict[str, Any]:
        """Dados de projetos e tipos de evento"""

        projetos = Projeto.objects.all()
        tipos_evento = TipoEvento.objects.all()

        projetos_data = []
        for projeto in projetos:
            projeto_data = {
                "id": str(projeto.id),
                "nome": projeto.nome,
                "descricao": getattr(projeto, "descricao", ""),
                "ativo": getattr(projeto, "ativo", True),
            }
            projetos_data.append(projeto_data)

        tipos_data = []
        for tipo in tipos_evento:
            tipo_data = {
                "id": str(tipo.id),
                "nome": tipo.nome,
                "descricao": getattr(tipo, "descricao", ""),
                "cor": getattr(tipo, "cor", "#000000"),
            }
            tipos_data.append(tipo_data)

        return {
            "dominio": "projetos_eventos",
            "data_exportacao": datetime.now().isoformat(),
            "projetos": projetos_data,
            "tipos_evento": tipos_data,
        }

    def get_business_context(self) -> Dict[str, Any]:
        """Contexto de negócio consolidado para IA"""

        # Métricas gerais do sistema
        context = {
            "empresa": {
                "nome": "Aprender Sistema",
                "ramo": "Educação e Formação",
                "descricao": "Sistema de gestão de formações educacionais com controle de agenda, aprovações e recursos",
            },
            "metricas_sistema": {
                "total_usuarios": Usuario.objects.count(),
                "usuarios_ativos": Usuario.objects.filter(is_active=True).count(),
                "total_municipios": Municipio.objects.count(),
                "total_formadores": Formador.objects.count(),
                "total_projetos": Projeto.objects.count(),
            },
            "perfis_sistema": {
                grupo.name: Usuario.objects.filter(groups=grupo).count()
                for grupo in Group.objects.all()
            },
            "cobertura_geografica": {
                "municipios_ativos": list(
                    Municipio.objects.values_list("nome", flat=True)
                ),
                "distribuicao_usuarios": {
                    mun.nome: Usuario.objects.filter(municipio=mun).count()
                    for mun in Municipio.objects.all()
                    if Usuario.objects.filter(municipio=mun).exists()
                },
            },
            "capacidades_sistema": [
                "Gestão de usuários por perfil (superintendência, coordenadores, formadores)",
                "Controle de disponibilidade e conflitos de agenda",
                "Sistema de aprovações hierárquico",
                "Integração com Google Calendar para eventos",
                "Controle de deslocamentos entre municípios",
                "Auditoria completa de operações",
                "Dashboard de disponibilidade mensal",
            ],
            "fluxos_principais": {
                "solicitacao_evento": "Coordenador → Solicitação → Verificação de Conflitos → Aprovação Superintendência → Google Calendar",
                "bloqueio_agenda": "Formador → Bloqueio (Total/Parcial) → Sistema atualiza disponibilidade",
                "gestao_usuarios": "Admin → Cadastro → Vinculação a Grupos → Ativação",
            },
            "dados_historicos": {
                "origem": "Migração de planilhas Google Sheets",
                "periodo": "2025",
                "total_registros_migrados": "73.168 registros",
                "qualidade_dados": "99.1% taxa de sucesso na migração",
            },
        }

        return {
            "dominio": "business_context",
            "data_exportacao": datetime.now().isoformat(),
            "contexto": context,
        }

    def export_business_summary(
        self, data: Dict[str, Any], domain: str, output_dir: str
    ) -> str:
        """Exporta resumo de negócio otimizado para IA"""

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        filename = f"oraculo_business_data_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = f"{output_dir}/{filename}"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=== DADOS APRENDER SISTEMA PARA ORÁCULO AI ===\n\n")
            f.write(f"Domínio: {domain.upper()}\n")
            f.write(f"Data de Exportação: {data.get('data_exportacao', 'N/A')}\n\n")

            if domain == "business_context":
                self._write_business_context(f, data["contexto"])
            elif domain == "usuarios":
                self._write_usuarios_context(f, data)
            elif domain == "municipios":
                self._write_municipios_context(f, data)
            elif domain == "formadores":
                self._write_formadores_context(f, data)
            elif domain == "projetos_eventos":
                self._write_projetos_context(f, data)

        self.stdout.write(
            self.style.SUCCESS(f"OK Business summary exportado: {filepath}")
        )
        return filepath

    def _write_business_context(self, file, context):
        """Escreve contexto de negócio formatado para IA"""

        file.write("CONTEXTO EMPRESARIAL:\n")
        empresa = context["empresa"]
        file.write(f"- Empresa: {empresa['nome']}\n")
        file.write(f"- Ramo: {empresa['ramo']}\n")
        file.write(f"- Descrição: {empresa['descricao']}\n\n")

        file.write("MÉTRICAS DO SISTEMA:\n")
        metricas = context["metricas_sistema"]
        for metric, value in metricas.items():
            file.write(f"- {metric.replace('_', ' ').title()}: {value}\n")

        file.write("\nPERFIS DE USUÁRIO:\n")
        for perfil, count in context["perfis_sistema"].items():
            file.write(f"- {perfil.title()}: {count} usuários\n")

        file.write("\nCOBERTURA GEOGRÁFICA:\n")
        municipios = context["cobertura_geografica"]["municipios_ativos"]
        file.write(f"- Total de municípios atendidos: {len(municipios)}\n")
        file.write(f"- Principais municípios: {', '.join(municipios[:10])}\n")

        file.write("\nCAPACIDADES DO SISTEMA:\n")
        for capacidade in context["capacidades_sistema"]:
            file.write(f"- {capacidade}\n")

        file.write("\nFLUXOS OPERACIONAIS:\n")
        for fluxo, descricao in context["fluxos_principais"].items():
            file.write(f"- {fluxo.replace('_', ' ').title()}: {descricao}\n")

    def _write_usuarios_context(self, file, data):
        """Escreve contexto de usuários para IA"""

        stats = data["estatisticas"]
        file.write("USUÁRIOS DO SISTEMA:\n")
        file.write(f"- Total: {stats['total_usuarios']}\n")
        file.write(f"- Ativos: {stats['usuarios_ativos']}\n\n")

        file.write("DISTRIBUIÇÃO POR PERFIL:\n")
        for grupo, count in stats["usuarios_por_grupo"].items():
            file.write(f"- {grupo.title()}: {count} usuários\n")

        file.write(f"\nAmostra de usuários cadastrados:\n")
        for user in data["usuarios"][:10]:  # Primeiros 10
            grupos = ", ".join(user["grupos"]) if user["grupos"] else "Sem grupo"
            municipio = user["municipio"] or "Não informado"
            file.write(f"- {user['nome_completo']} ({grupos}) - {municipio}\n")

    def _write_municipios_context(self, file, data):
        """Escreve contexto de municípios para IA"""

        file.write("COBERTURA MUNICIPAL:\n")
        file.write(f"- Total de municípios: {data['total_municipios']}\n\n")

        file.write("MUNICÍPIOS ATENDIDOS:\n")
        for municipio in data["municipios"]:
            usuarios = municipio["usuarios_vinculados"]
            file.write(f"- {municipio['nome']}: {usuarios} usuários vinculados\n")

    def _write_formadores_context(self, file, data):
        """Escreve contexto de formadores para IA"""

        file.write("EQUIPE DE FORMADORES:\n")
        file.write(f"- Total: {data['total_formadores']}\n\n")

        file.write("FORMADORES CADASTRADOS:\n")
        for formador in data["formadores"]:
            base = formador["municipio_base"] or "Base não definida"
            status = "Ativo" if formador["ativo"] else "Inativo"
            file.write(f"- {formador['nome']} - {base} ({status})\n")

    def _write_projetos_context(self, file, data):
        """Escreve contexto de projetos para IA"""

        file.write("PROJETOS E EVENTOS:\n")
        file.write(f"- Total de projetos: {len(data['projetos'])}\n")
        file.write(f"- Tipos de evento: {len(data['tipos_evento'])}\n\n")

        file.write("PROJETOS ATIVOS:\n")
        for projeto in data["projetos"]:
            file.write(f"- {projeto['nome']}\n")

        file.write("\nTIPOS DE EVENTO:\n")
        for tipo in data["tipos_evento"]:
            file.write(f"- {tipo['nome']}\n")

    def export_json(self, data: Dict[str, Any], domain: str, output_dir: str) -> str:
        """Exporta dados em formato JSON estruturado"""

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        filename = (
            f"aprender_sistema_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        filepath = f"{output_dir}/{filename}"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=BusinessJSONEncoder)

        self.stdout.write(self.style.SUCCESS(f"OK JSON exportado: {filepath}"))
        return filepath

    def export_all_domains(
        self, format_type: str, output_dir: str, for_oraculo: bool, anonymize: bool
    ):
        """Exporta todos os domínios"""

        domains = [
            "business_context",
            "usuarios",
            "municipios",
            "formadores",
            "projetos",
        ]
        exported_files = []

        self.stdout.write("Exportando todos os domínios...")

        for domain in domains:
            data = self.get_domain_data(domain, anonymize)

            if for_oraculo or format_type == "business_summary":
                filepath = self.export_business_summary(data, domain, output_dir)
            else:
                filepath = self.export_json(data, domain, output_dir)

            exported_files.append(filepath)

        # Criar arquivo consolidado para Oráculo
        if for_oraculo:
            self.create_oraculo_consolidated_file(exported_files, output_dir)

        self.stdout.write(
            self.style.SUCCESS(
                f"\nOK Exportação completa! {len(exported_files)} arquivos gerados"
            )
        )

        return f"Exportados: {', '.join(exported_files)}"

    def create_oraculo_consolidated_file(
        self, exported_files: List[str], output_dir: str
    ):
        """Cria arquivo consolidado otimizado para o Oráculo"""

        consolidated_file = f"{output_dir}/oraculo_aprender_sistema_complete.txt"

        with open(consolidated_file, "w", encoding="utf-8") as consolidated:
            consolidated.write("=== KNOWLEDGE BASE COMPLETA - APRENDER SISTEMA ===\n\n")
            consolidated.write(
                "Este arquivo contém todos os dados estruturados do Aprender Sistema\n"
            )
            consolidated.write(
                "para alimentar o Oráculo AI como assistente de negócios inteligente.\n\n"
            )
            consolidated.write("=" * 80 + "\n\n")

            for filepath in exported_files:
                domain = filepath.split("_")[-3]  # Extrair domínio do nome do arquivo

                consolidated.write(f"SEÇÃO: {domain.upper()}\n")
                consolidated.write("-" * 40 + "\n")

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        consolidated.write(f.read())
                    consolidated.write("\n\n" + "=" * 80 + "\n\n")
                except Exception as e:
                    consolidated.write(f"Erro ao incluir {filepath}: {e}\n\n")

            consolidated.write("=== FIM DA KNOWLEDGE BASE ===\n")

        self.stdout.write(
            self.style.SUCCESS(f"OK Arquivo consolidado criado: {consolidated_file}")
        )

    def anonymize_email(self, email: str) -> str:
        """Anonimiza email mantendo domínio"""
        if not email or "@" not in email:
            return email

        local, domain = email.split("@", 1)
        masked_local = local[:2] + "*" * (len(local) - 2) if len(local) > 2 else "***"
        return f"{masked_local}@{domain}"

    def anonymize_cpf(self, cpf: str) -> str:
        """Anonimiza CPF mantendo padrão"""
        if not cpf or len(cpf) != 11:
            return cpf

        return f"{cpf[:3]}*****{cpf[-2:]}"
