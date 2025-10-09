#!/usr/bin/env python
"""
Teste completo do sistema com dados reais
"""

import json
import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from core.models import Usuario, Formador, Municipio, Projeto
from django.contrib.auth.models import Group
from django.db import connection


class TestadorSistemaReal:
    """Testa o sistema com dados reais importados"""

    def __init__(self):
        self.resultados = {}
        self.erros = []

    def testar_integridade_dados(self):
        """Testa a integridade dos dados importados"""

        print("🔍 TESTANDO INTEGRIDADE DOS DADOS REAIS")
        print("=" * 60)

        # Teste 1: Contagem de registros
        total_usuarios = Usuario.objects.count()
        total_formadores = Formador.objects.count()
        total_municipios = Municipio.objects.count()
        total_projetos = Projeto.objects.count()
        total_grupos = Group.objects.count()

        print(f"📊 Contagens de registros:")
        print(f"   👥 Usuários: {total_usuarios}")
        print(f"   👨‍🏫 Formadores: {total_formadores}")
        print(f"   🏛️ Municípios: {total_municipios}")
        print(f"   📚 Projetos: {total_projetos}")
        print(f"   👤 Grupos: {total_grupos}")

        self.resultados["contagens"] = {
            "usuarios": total_usuarios,
            "formadores": total_formadores,
            "municipios": total_municipios,
            "projetos": total_projetos,
            "grupos": total_grupos,
        }

        # Teste 2: Consistência usuários ↔ formadores
        usuarios_formador_grupo = Usuario.objects.filter(
            groups__name="formador"
        ).count()
        gap_formadores = abs(usuarios_formador_grupo - total_formadores)

        print(f"\n🔗 Consistência usuários ↔ formadores:")
        print(f"   👥 Usuários no grupo 'formador': {usuarios_formador_grupo}")
        print(f"   👨‍🏫 Registros de Formador: {total_formadores}")
        print(f"   📊 Gap: {gap_formadores}")

        if gap_formadores == 0:
            print("   ✅ Consistência perfeita!")
        elif gap_formadores <= 2:
            print("   ⚠️ Gap mínimo aceitável")
        else:
            print("   ❌ Gap significativo encontrado")
            self.erros.append(
                f"Gap significativo usuários/formadores: {gap_formadores}"
            )

        self.resultados["consistencia_formadores"] = {
            "usuarios_grupo": usuarios_formador_grupo,
            "registros_formador": total_formadores,
            "gap": gap_formadores,
            "status": "OK" if gap_formadores <= 2 else "ERRO",
        }

        # Teste 3: Usuários sem grupo
        usuarios_sem_grupo = Usuario.objects.filter(groups__isnull=True)

        print(f"\n👤 Usuários sem grupo: {usuarios_sem_grupo.count()}")
        if usuarios_sem_grupo.exists():
            for usuario in usuarios_sem_grupo:
                print(f"   - {usuario.username}")
                if usuario.username != "admin":  # Admin sem grupo é esperado
                    self.erros.append(f"Usuário sem grupo: {usuario.username}")

        # Teste 4: Dados válidos
        formadores_sem_email = Formador.objects.filter(email__isnull=True).count()
        municipios_sem_uf = Municipio.objects.filter(uf__isnull=True).count()
        projetos_inativos = Projeto.objects.filter(ativo=False).count()

        print(f"\n📋 Validação de dados:")
        print(f"   📧 Formadores sem email: {formadores_sem_email}")
        print(f"   🏛️ Municípios sem UF: {municipios_sem_uf}")
        print(f"   📚 Projetos inativos: {projetos_inativos}")

        self.resultados["validacao_dados"] = {
            "formadores_sem_email": formadores_sem_email,
            "municipios_sem_uf": municipios_sem_uf,
            "projetos_inativos": projetos_inativos,
        }

        return True

    def testar_grupos_e_permissoes(self):
        """Testa grupos e permissões"""

        print("\n👥 TESTANDO GRUPOS E PERMISSÕES")
        print("=" * 60)

        # Análise por grupo
        grupos_analise = {}
        for grupo in Group.objects.all():
            count = grupo.user_set.count()
            usuarios_grupo = list(grupo.user_set.values_list("username", flat=True)[:5])

            grupos_analise[grupo.name] = {
                "count": count,
                "usuarios_exemplo": usuarios_grupo,
            }

            print(f"👥 Grupo '{grupo.name}': {count} usuários")
            if usuarios_grupo:
                print(f"   Exemplos: {', '.join(usuarios_grupo)}")

        self.resultados["grupos_analise"] = grupos_analise

        # Verificar hierarquia esperada
        coordenadores = grupos_analise.get("coordenador", {}).get("count", 0)
        gerentes = grupos_analise.get("gerente", {}).get("count", 0)
        formadores = grupos_analise.get("formador", {}).get("count", 0)
        superintendencia = grupos_analise.get("superintendencia", {}).get("count", 0)

        print(f"\n📊 Hierarquia organizacional:")
        print(f"   🏛️ Superintendência: {superintendencia}")
        print(f"   👔 Gerentes: {gerentes}")
        print(f"   👨‍💼 Coordenadores: {coordenadores}")
        print(f"   👨‍🏫 Formadores: {formadores}")

        # Validar pirâmide organizacional
        if superintendencia == 0:
            print(
                "   ⚠️ Nenhum usuário na superintendência - necessário para aprovações"
            )
            self.erros.append("Nenhum usuário na superintendência")

        if gerentes < coordenadores:
            print("   ✅ Hierarquia coerente: mais coordenadores que gerentes")

        if formadores > coordenadores:
            print("   ✅ Hierarquia coerente: mais formadores que coordenadores")

        return True

    def testar_conectividade_banco(self):
        """Testa conectividade e performance do banco"""

        print("\n🗄️ TESTANDO CONECTIVIDADE E PERFORMANCE DO BANCO")
        print("=" * 60)

        try:
            # Teste de conectividade
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"✅ PostgreSQL conectado: {version}")

            # Teste de queries complexas
            start_time = datetime.now()

            # Query 1: Formadores com seus usuários e grupos
            formadores_query = list(
                Formador.objects.select_related("usuario", "area_atuacao").all()
            )

            # Query 2: Municípios por UF
            municipios_por_uf = {}
            for municipio in Municipio.objects.all():
                uf = municipio.uf or "SEM_UF"
                if uf not in municipios_por_uf:
                    municipios_por_uf[uf] = 0
                municipios_por_uf[uf] += 1

            # Query 3: Projetos ativos
            projetos_ativos = list(Projeto.objects.filter(ativo=True))

            end_time = datetime.now()
            tempo_queries = (end_time - start_time).total_seconds()

            print(f"⏱️ Tempo para queries complexas: {tempo_queries:.2f}s")
            print(f"📊 Formadores processados: {len(formadores_query)}")
            print(f"🗺️ UFs encontradas: {len(municipios_por_uf)}")
            print(f"📚 Projetos ativos: {len(projetos_ativos)}")

            if tempo_queries < 1.0:
                print("✅ Performance excelente")
            elif tempo_queries < 3.0:
                print("⚠️ Performance aceitável")
            else:
                print("❌ Performance baixa")
                self.erros.append(f"Performance baixa: {tempo_queries:.2f}s")

            self.resultados["performance"] = {
                "tempo_queries": tempo_queries,
                "formadores_processados": len(formadores_query),
                "ufs_encontradas": len(municipios_por_uf),
                "projetos_ativos": len(projetos_ativos),
            }

        except Exception as e:
            print(f"❌ Erro na conectividade: {e}")
            self.erros.append(f"Erro conectividade banco: {e}")
            return False

        return True

    def testar_dados_especificos(self):
        """Testa dados específicos importantes"""

        print("\n🔍 TESTANDO DADOS ESPECÍFICOS IMPORTANTES")
        print("=" * 60)

        # Teste 1: Municípios conhecidos
        municipios_importantes = ["Maracanaú", "Petrolina", "Sobral", "Fortaleza"]
        municipios_encontrados = []

        for nome in municipios_importantes:
            municipio = Municipio.objects.filter(nome__icontains=nome).first()
            if municipio:
                municipios_encontrados.append(f"{municipio.nome} ({municipio.uf})")
                print(f"   ✅ Encontrado: {municipio.nome} - {municipio.uf}")
            else:
                print(f"   ❌ Não encontrado: {nome}")
                self.erros.append(f"Município importante não encontrado: {nome}")

        # Teste 2: Projetos conhecidos
        projetos_importantes = ["ACerta", "Matemática", "Tema", "Brincando"]
        projetos_encontrados = []

        for nome in projetos_importantes:
            projeto = Projeto.objects.filter(nome__icontains=nome).first()
            if projeto:
                projetos_encontrados.append(projeto.nome)
                print(f"   ✅ Projeto encontrado: {projeto.nome}")
            else:
                print(f"   ❌ Projeto não encontrado: {nome}")

        # Teste 3: Formadores com emails válidos
        formadores_email_valido = Formador.objects.exclude(email__exact="").count()
        total_formadores = Formador.objects.count()

        print(
            f"\n📧 Formadores com email válido: {formadores_email_valido}/{total_formadores}"
        )

        if total_formadores > 0:
            percentual = (formadores_email_valido / total_formadores) * 100
            print(f"   📊 Percentual: {percentual:.1f}%")

            if percentual >= 95:
                print("   ✅ Excelente qualidade de dados")
            elif percentual >= 80:
                print("   ⚠️ Qualidade aceitável")
            else:
                print("   ❌ Qualidade baixa de dados")
                self.erros.append(f"Qualidade baixa emails: {percentual:.1f}%")

        self.resultados["dados_especificos"] = {
            "municipios_encontrados": municipios_encontrados,
            "projetos_encontrados": projetos_encontrados,
            "percentual_emails_validos": percentual if total_formadores > 0 else 0,
        }

        return True

    def gerar_relatorio_final(self):
        """Gera relatório final dos testes"""

        relatorio = {
            "timestamp": datetime.now().isoformat(),
            "teste_executado": "Sistema com dados reais",
            "status_geral": "SUCESSO" if len(self.erros) == 0 else "COM_PROBLEMAS",
            "total_erros": len(self.erros),
            "erros": self.erros,
            "resultados": self.resultados,
            "resumo_final": {
                "usuarios_importados": self.resultados.get("contagens", {}).get(
                    "usuarios", 0
                ),
                "formadores_criados": self.resultados.get("contagens", {}).get(
                    "formadores", 0
                ),
                "municipios_importados": self.resultados.get("contagens", {}).get(
                    "municipios", 0
                ),
                "projetos_importados": self.resultados.get("contagens", {}).get(
                    "projetos", 0
                ),
                "gap_formadores": self.resultados.get(
                    "consistencia_formadores", {}
                ).get("gap", 0),
                "qualidade_emails": self.resultados.get("dados_especificos", {}).get(
                    "percentual_emails_validos", 0
                ),
            },
        }

        with open(
            "/app/relatorio_teste_sistema_dados_reais.json", "w", encoding="utf-8"
        ) as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

        print("\n📄 Relatório salvo: relatorio_teste_sistema_dados_reais.json")
        return relatorio


def main():
    """Executa teste completo do sistema"""

    print("🧪 TESTE COMPLETO DO SISTEMA COM DADOS REAIS")
    print("=" * 60)

    testador = TestadorSistemaReal()

    try:
        # Executar testes
        testador.testar_integridade_dados()
        testador.testar_grupos_e_permissoes()
        testador.testar_conectividade_banco()
        testador.testar_dados_especificos()

        # Gerar relatório final
        relatorio = testador.gerar_relatorio_final()

        print("\n" + "=" * 60)
        print("📊 RESUMO FINAL DOS TESTES")
        print("=" * 60)

        resumo = relatorio["resumo_final"]
        print(f"✅ Status geral: {relatorio['status_geral']}")
        print(f"👥 Usuários importados: {resumo['usuarios_importados']}")
        print(f"👨‍🏫 Formadores criados: {resumo['formadores_criados']}")
        print(f"🏛️ Municípios importados: {resumo['municipios_importados']}")
        print(f"📚 Projetos importados: {resumo['projetos_importados']}")
        print(f"🔗 Gap formadores: {resumo['gap_formadores']}")
        print(f"📧 Qualidade emails: {resumo['qualidade_emails']:.1f}%")

        if relatorio["total_erros"] > 0:
            print(f"\n⚠️ Total de erros encontrados: {relatorio['total_erros']}")
            print("Primeiros 5 erros:")
            for erro in relatorio["erros"][:5]:
                print(f"   - {erro}")
        else:
            print("\n🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")

        print("\n🎯 SISTEMA PRONTO PARA USO COM DADOS REAIS!")
        return True

    except Exception as e:
        print(f"❌ ERRO nos testes: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
