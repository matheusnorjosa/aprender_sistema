#!/usr/bin/env python3
"""
IMPORTADOR CONSOLIDADO - TODAS AS PLANILHAS
==========================================

Script consolidado para importar dados de todas as 4 planilhas
conforme o contexto supremo fornecido.

Planilhas:
1. Acompanhamento de Agenda | 2025
2. Disponibilidade | 2025
3. Planilha de Controle - 2025
4. Usuários

Autor: Claude Code
Data: Janeiro 2025
"""

import os
import sys
import django
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ImportadorConsolidadoContextoSupremo:
    """
    Importador consolidado de todas as planilhas
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.scripts = {
            "agenda_2025": "import_agenda_2025_contexto_supremo.py",
            "disponibilidade_2025": "import_disponibilidade_2025_contexto_supremo.py",
            "controle_2025": "import_controle_2025_contexto_supremo.py",
            "usuarios": "import_usuarios_contexto_supremo.py",
        }

        # Estatísticas consolidadas
        self.estatisticas_consolidadas = {
            "inicio": datetime.now().isoformat(),
            "fim": None,
            "duracao_segundos": 0,
            "planilhas_processadas": 0,
            "total_registros": 0,
            "total_erros": 0,
            "planilhas": {},
        }

    def executar_script(self, script_name: str, script_path: str) -> Dict[str, Any]:
        """
        Executar um script de importação
        """
        logger.info(f"🚀 Executando script: {script_name}")

        try:
            import subprocess

            # Comando para executar o script
            if self.dry_run:
                cmd = ["python", script_path, "--dry-run"]
            else:
                cmd = ["python", script_path, "--execute"]

            # Executar o script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )

            # Verificar se o script foi executado com sucesso
            if result.returncode == 0:
                logger.info(f"✅ Script {script_name} executado com sucesso")

                # Tentar carregar o relatório JSON se existir
                relatorio_path = f"relatorio_importacao_{script_name}.json"
                if os.path.exists(relatorio_path):
                    with open(relatorio_path, "r", encoding="utf-8") as f:
                        relatorio = json.load(f)
                        return {
                            "status": "sucesso",
                            "relatorio": relatorio,
                            "output": result.stdout,
                        }
                else:
                    return {
                        "status": "sucesso",
                        "relatorio": None,
                        "output": result.stdout,
                    }
            else:
                logger.error(f"❌ Erro ao executar script {script_name}")
                return {
                    "status": "erro",
                    "erro": result.stderr,
                    "output": result.stdout,
                }

        except Exception as e:
            logger.error(f"❌ Exceção ao executar script {script_name}: {str(e)}")
            return {"status": "erro", "erro": str(e), "output": ""}

    def executar_importacao_completa(
        self, planilhas_especificas: Optional[List[str]] = None
    ):
        """
        Executar importação completa de todas as planilhas
        """
        logger.info("🚀 INICIANDO IMPORTAÇÃO CONSOLIDADA - CONTEXTO SUPREMO")
        logger.info("=" * 80)

        if self.dry_run:
            logger.info("🔍 MODO DRY RUN - Nenhum dado será salvo no banco")
        else:
            logger.info("💾 MODO EXECUÇÃO REAL - Dados serão salvos no banco")

        # Determinar quais planilhas processar
        planilhas_para_processar = planilhas_especificas or list(self.scripts.keys())

        logger.info(
            f"📋 Planilhas a serem processadas: {', '.join(planilhas_para_processar)}"
        )

        # Processar cada planilha
        for planilha in planilhas_para_processar:
            if planilha in self.scripts:
                logger.info(f"\n{'='*60}")
                logger.info(f"🔄 PROCESSANDO PLANILHA: {planilha.upper()}")
                logger.info(f"{'='*60}")

                script_path = self.scripts[planilha]

                # Verificar se o script existe
                if not os.path.exists(script_path):
                    logger.error(f"❌ Script não encontrado: {script_path}")
                    self.estatisticas_consolidadas["planilhas"][planilha] = {
                        "status": "erro",
                        "erro": f"Script não encontrado: {script_path}",
                    }
                    continue

                # Executar o script
                resultado = self.executar_script(planilha, script_path)

                # Salvar resultado nas estatísticas
                self.estatisticas_consolidadas["planilhas"][planilha] = resultado

                # Atualizar estatísticas consolidadas
                if resultado["status"] == "sucesso":
                    self.estatisticas_consolidadas["planilhas_processadas"] += 1

                    if (
                        resultado["relatorio"]
                        and "estatisticas" in resultado["relatorio"]
                    ):
                        stats = resultado["relatorio"]["estatisticas"]
                        self.estatisticas_consolidadas["total_registros"] += stats.get(
                            "total_registros", 0
                        )
                        self.estatisticas_consolidadas["total_erros"] += stats.get(
                            "erros", 0
                        )
                else:
                    self.estatisticas_consolidadas["total_erros"] += 1

                logger.info(f"✅ Planilha {planilha} processada")
            else:
                logger.warning(f"⚠️ Planilha {planilha} não configurada")

        # Finalizar estatísticas
        self.estatisticas_consolidadas["fim"] = datetime.now().isoformat()
        inicio = datetime.fromisoformat(self.estatisticas_consolidadas["inicio"])
        fim = datetime.fromisoformat(self.estatisticas_consolidadas["fim"])
        self.estatisticas_consolidadas["duracao_segundos"] = (
            fim - inicio
        ).total_seconds()

        # Gerar relatório final
        self.gerar_relatorio_consolidado()

        return self.estatisticas_consolidadas

    def gerar_relatorio_consolidado(self):
        """
        Gerar relatório consolidado final
        """
        logger.info("\n" + "=" * 80)
        logger.info("📊 RELATÓRIO CONSOLIDADO FINAL")
        logger.info("=" * 80)

        logger.info(
            f"⏱️ DURAÇÃO TOTAL: {self.estatisticas_consolidadas['duracao_segundos']:.2f} segundos"
        )
        logger.info(
            f"📋 PLANILHAS PROCESSADAS: {self.estatisticas_consolidadas['planilhas_processadas']}/{len(self.scripts)}"
        )
        logger.info(
            f"📊 TOTAL DE REGISTROS: {self.estatisticas_consolidadas['total_registros']}"
        )
        logger.info(
            f"❌ TOTAL DE ERROS: {self.estatisticas_consolidadas['total_erros']}"
        )

        logger.info(f"\n📋 DETALHAMENTO POR PLANILHA:")
        for planilha, resultado in self.estatisticas_consolidadas["planilhas"].items():
            logger.info(f"\n🔸 {planilha.upper()}:")
            logger.info(f"   Status: {resultado['status']}")

            if resultado["status"] == "sucesso" and resultado["relatorio"]:
                stats = resultado["relatorio"]["estatisticas"]
                logger.info(f"   Registros: {stats.get('total_registros', 0)}")
                logger.info(f"   Erros: {stats.get('erros', 0)}")
            elif resultado["status"] == "erro":
                logger.info(f"   Erro: {resultado.get('erro', 'Erro desconhecido')}")

        # Salvar relatório consolidado
        relatorio_path = "relatorio_importacao_consolidado_contexto_supremo.json"
        with open(relatorio_path, "w", encoding="utf-8") as f:
            json.dump(
                self.estatisticas_consolidadas,
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        logger.info(f"\n💾 Relatório consolidado salvo em: {relatorio_path}")

        # Resumo final
        if self.estatisticas_consolidadas["total_erros"] == 0:
            logger.info("\n🎉 TODAS AS PLANILHAS FORAM PROCESSADAS COM SUCESSO!")
        else:
            logger.info(
                f"\n⚠️ PROCESSAMENTO CONCLUÍDO COM {self.estatisticas_consolidadas['total_erros']} ERRO(S)"
            )


def main():
    """
    Função principal
    """
    import argparse

    parser = argparse.ArgumentParser(description="Importar dados de todas as planilhas")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Executar em modo de teste (padrão)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Executar importação real (salvar no banco)",
    )
    parser.add_argument(
        "--planilhas",
        nargs="+",
        choices=["agenda_2025", "disponibilidade_2025", "controle_2025", "usuarios"],
        help="Processar apenas planilhas específicas",
    )

    args = parser.parse_args()

    # Determinar modo de execução
    dry_run = not args.execute

    # Criar importador consolidado
    importador = ImportadorConsolidadoContextoSupremo(dry_run=dry_run)

    # Executar importação completa
    resultado = importador.executar_importacao_completa(
        planilhas_especificas=args.planilhas
    )

    if resultado["total_erros"] == 0:
        logger.info("🎉 IMPORTAÇÃO CONSOLIDADA CONCLUÍDA COM SUCESSO!")
        sys.exit(0)
    else:
        logger.error(
            f"❌ IMPORTAÇÃO CONSOLIDADA CONCLUÍDA COM {resultado['total_erros']} ERRO(S)!"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
