#!/usr/bin/env python
"""
Mapear usuários para grupos corretos e criar registros de Formador
"""

import json
import os
import sys

import django

# Configurar Django
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.contrib.auth.models import Group
from django.db import transaction

from core.models import Formador, Municipio, Usuario


class MapeadorUsuariosGrupos:
    """Mapeia usuários para grupos corretos e cria registros de Formador"""

    def __init__(self):
        self.formadores_criados = 0
        self.usuarios_mapeados = 0
        self.erros = []

    def analisar_estado_atual(self):
        """Analisa o estado atual dos usuários e grupos"""

        print("📊 ANALISANDO ESTADO ATUAL DOS USUÁRIOS E GRUPOS")
        print("=" * 60)

        # Contar usuários por grupo
        grupos_stats = {}
        for grupo in Group.objects.all():
            count = grupo.user_set.count()
            grupos_stats[grupo.name] = count
            print(f"👥 Grupo '{grupo.name}': {count} usuários")

        # Contar registros de Formador
        total_formadores = Formador.objects.count()
        total_usuarios = Usuario.objects.count()
        total_municipios = Municipio.objects.count()

        print(f"\n📊 ESTATÍSTICAS GERAIS:")
        print(f"   👤 Total usuários: {total_usuarios}")
        print(f"   👨‍🏫 Total formadores (registros): {total_formadores}")
        print(f"   🏛️ Total municípios: {total_municipios}")

        # Identificar gap
        usuarios_formador_grupo = grupos_stats.get("formador", 0)
        gap_formadores = usuarios_formador_grupo - total_formadores

        print(f"\n⚠️ GAP IDENTIFICADO:")
        print(f"   👥 Usuários no grupo 'formador': {usuarios_formador_grupo}")
        print(f"   👨‍🏫 Registros de Formador existentes: {total_formadores}")
        print(f"   📊 Gap a ser preenchido: {gap_formadores}")

        return {
            "grupos_stats": grupos_stats,
            "gap_formadores": gap_formadores,
            "total_usuarios": total_usuarios,
            "total_municipios": total_municipios,
        }

    def criar_formadores_faltantes(self):
        """Cria registros de Formador para usuários no grupo 'formador'"""

        print("\n👨‍🏫 CRIANDO REGISTROS DE FORMADOR FALTANTES...")

        try:
            # Buscar grupo formador
            grupo_formador = Group.objects.get(name="formador")

            # Buscar usuários no grupo que não têm registro de Formador
            usuarios_formador = grupo_formador.user_set.all()

            print(
                f"   👥 Encontrados {usuarios_formador.count()} usuários no grupo 'formador'"
            )

            # Verificar quais já têm registro de Formador
            usuarios_sem_formador = []
            for usuario in usuarios_formador:
                if not Formador.objects.filter(usuario=usuario).exists():
                    usuarios_sem_formador.append(usuario)

            print(
                f"   📊 Usuários sem registro de Formador: {len(usuarios_sem_formador)}"
            )

            # Criar registros de Formador
            for i, usuario in enumerate(usuarios_sem_formador):
                try:
                    with transaction.atomic():
                        # Determinar área de atuação baseada no nome do usuário
                        area_atuacao = self.determinar_area_atuacao(usuario.username)

                        # Criar registro de Formador
                        formador = Formador.objects.create(
                            usuario=usuario,
                            nome=usuario.get_full_name() or usuario.username,
                            area_atuacao=area_atuacao,
                            email=usuario.email,
                            ativo=True,
                        )

                        self.formadores_criados += 1

                        if self.formadores_criados % 10 == 0:
                            print(
                                f"   ✅ {self.formadores_criados} formadores criados..."
                            )

                except Exception as e:
                    self.erros.append(
                        f"Erro criando formador para {usuario.username}: {e}"
                    )
                    print(f"   ❌ Erro criando formador para {usuario.username}: {e}")

            print(f"✅ Total de formadores criados: {self.formadores_criados}")

        except Group.DoesNotExist:
            self.erros.append("Grupo 'formador' não encontrado")
            print("❌ Grupo 'formador' não encontrado")

    def determinar_area_atuacao(self, username):
        """Determina área de atuação baseada no username e retorna Group"""

        username_lower = username.lower()

        # Mapear nomes para grupos existentes ou criar grupos de área
        area_nome = None

        if any(
            termo in username_lower
            for termo in ["mat", "matematica", "calculo", "numero"]
        ):
            area_nome = "area_matematica"
        elif any(
            termo in username_lower
            for termo in ["port", "lingua", "texto", "escrita", "leitura"]
        ):
            area_nome = "area_lingua_portuguesa"
        elif any(
            termo in username_lower
            for termo in ["cien", "bio", "fis", "quim", "natura"]
        ):
            area_nome = "area_ciencias"
        elif any(
            termo in username_lower for termo in ["inf", "crianca", "bebe", "pequeno"]
        ):
            area_nome = "area_educacao_infantil"
        elif any(
            termo in username_lower for termo in ["arte", "music", "danca", "teatro"]
        ):
            area_nome = "area_artes"
        elif any(
            termo in username_lower for termo in ["hist", "geo", "social", "humana"]
        ):
            area_nome = "area_ciencias_humanas"
        else:
            area_nome = "area_geral"

        # Buscar ou criar o grupo
        grupo, created = Group.objects.get_or_create(name=area_nome)
        if created:
            print(f"      ✅ Criado grupo de área: {area_nome}")

        return grupo

    def validar_mapeamento_grupos(self):
        """Valida se todos os usuários estão nos grupos corretos"""

        print("\n✅ VALIDANDO MAPEAMENTO DE GRUPOS...")

        # Verificar se todos os usuários estão em pelo menos um grupo
        usuarios_sem_grupo = Usuario.objects.filter(groups__isnull=True)

        if usuarios_sem_grupo.exists():
            print(f"   ⚠️ {usuarios_sem_grupo.count()} usuários sem grupo:")
            for usuario in usuarios_sem_grupo[:5]:  # Mostrar apenas os primeiros 5
                print(f"      - {usuario.username}")

        # Verificar consistência Formador x Grupo
        formadores_sem_grupo = []
        for formador in Formador.objects.all():
            if not formador.usuario.groups.filter(name="formador").exists():
                formadores_sem_grupo.append(formador)

        if formadores_sem_grupo:
            print(
                f"   ⚠️ {len(formadores_sem_grupo)} formadores cujo usuário não está no grupo 'formador'"
            )

        # Verificar grupos órfãos (usuários em grupos sem registros correspondentes)
        grupo_formador = Group.objects.filter(name="formador").first()
        if grupo_formador:
            usuarios_grupo_formador = grupo_formador.user_set.count()
            registros_formador = Formador.objects.count()

            print(f"   📊 Usuários no grupo 'formador': {usuarios_grupo_formador}")
            print(f"   📊 Registros de Formador: {registros_formador}")

            if usuarios_grupo_formador == registros_formador:
                print(
                    "   ✅ Mapeamento grupo 'formador' ↔ registros Formador: CONSISTENTE"
                )
            else:
                print(
                    "   ⚠️ Mapeamento grupo 'formador' ↔ registros Formador: INCONSISTENTE"
                )

    def gerar_relatorio(self, analise_inicial):
        """Gera relatório do mapeamento"""

        # Nova análise após as mudanças
        analise_final = self.analisar_estado_atual()

        relatorio = {
            "timestamp": "2025-09-23",
            "formadores_criados": self.formadores_criados,
            "usuarios_mapeados": self.usuarios_mapeados,
            "total_erros": len(self.erros),
            "erros": self.erros,
            "antes": analise_inicial,
            "depois": analise_final,
            "mudancas": {
                "gap_formadores_resolvido": analise_inicial["gap_formadores"]
                - analise_final.get("gap_formadores", 0)
            },
        }

        with open(
            "/app/relatorio_mapeamento_usuarios_grupos.json", "w", encoding="utf-8"
        ) as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

        print("\n📄 Relatório salvo: relatorio_mapeamento_usuarios_grupos.json")
        return relatorio


def main():
    """Executa mapeamento de usuários para grupos"""

    print("👥 MAPEAMENTO DE USUÁRIOS PARA GRUPOS CORRETOS")
    print("=" * 60)

    mapeador = MapeadorUsuariosGrupos()

    try:
        # Analisar estado atual
        analise_inicial = mapeador.analisar_estado_atual()

        # Criar formadores faltantes
        if analise_inicial["gap_formadores"] > 0:
            mapeador.criar_formadores_faltantes()
        else:
            print("\n✅ Não há gap de formadores a ser preenchido")

        # Validar mapeamento
        mapeador.validar_mapeamento_grupos()

        # Gerar relatório
        relatorio = mapeador.gerar_relatorio(analise_inicial)

        print("\n📊 RESUMO DO MAPEAMENTO:")
        print(f"   ✅ Formadores criados: {relatorio['formadores_criados']}")
        print(f"   👥 Usuários mapeados: {relatorio['usuarios_mapeados']}")
        print(f"   ❌ Erros: {relatorio['total_erros']}")

        if relatorio["mudancas"]["gap_formadores_resolvido"] > 0:
            print(
                f"   🔧 Gap de formadores resolvido: {relatorio['mudancas']['gap_formadores_resolvido']}"
            )

        if relatorio["total_erros"] > 0:
            print(f"\n⚠️ Primeiros 3 erros:")
            for erro in relatorio["erros"][:3]:
                print(f"   - {erro}")

        print("\n🎉 MAPEAMENTO DE USUÁRIOS CONCLUÍDO!")
        return True

    except Exception as e:
        print(f"❌ ERRO no mapeamento: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
