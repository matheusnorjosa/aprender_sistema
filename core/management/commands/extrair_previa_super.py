"""
Comando Django para extrair e mostrar prévia dos dados da aba Super
da planilha Acompanhamento de Agenda | 2025

Este comando simula a extração dos dados da aba Super mostrando como 
eles ficariam tratados antes da importação real.

Uso:
python manage.py extrair_previa_super
"""

import logging
import json
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from datetime import datetime

class Command(BaseCommand):
    help = 'Extrai e mostra prévia dos dados tratados da aba Super'

    def setup_logging(self):
        """Configura logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def simular_dados_aba_super(self):
        """Simula dados da aba Super baseados na análise da planilha"""
        # Dados simulados baseados na análise da planilha real
        # Aba Super tem 1.985 registros com aprovações da superintendência
        
        dados_exemplo = [
            {
                'A': '15/01/2025',  # Data do Evento
                'B': 'Maria José Santos Silva',  # Nome do Formador  
                'C': 'Fortaleza',  # Município
                'D': 'Alfabetização Baseada na Ciência',  # Projeto
                'E': 'Formação Continuada',  # Tipo de Evento
                'F': '08:00',  # Horário Início
                'G': '17:00',  # Horário Fim
                'H': 'Evento aprovado pela superintendência - Turma A',  # Observações
                'I': 'APROVADO',  # Status Aprovação
                'J': 'Coordenador Regional',  # Solicitante
                'K': 'Presencial',  # Modalidade
                'L': '40',  # Carga Horária
                'M': 'Escola Municipal João Silva',  # Local
                'N': '25',  # Número de Participantes
                'O': 'Professores da rede municipal',  # Público Alvo
                'P': 'Material didático fornecido',  # Recursos
                'Q': 'Certificação obrigatória',  # Observações Adicionais
                'R': 'joao.coordenador@educacao.ce.gov.br',  # Email Contato
                'S': '(85) 99999-1234',  # Telefone Contato  
                'T': 'Superintendente João Silva'  # Aprovador
            },
            {
                'A': '22/01/2025',
                'B': 'Ana Carolina Oliveira',
                'C': 'Caucaia',
                'D': 'Matemática nos Anos Iniciais',
                'E': 'Workshop',
                'F': '14:00',
                'G': '18:00',
                'H': 'Workshop sobre metodologias ativas',
                'I': 'APROVADO',
                'J': 'Maria Coordenadora',
                'K': 'Híbrido',
                'L': '4',
                'M': 'Centro de Formação Caucaia',
                'N': '15',
                'O': 'Coordenadores pedagógicos',
                'P': 'Computadores e projetor',
                'Q': 'Gravação autorizada',
                'R': 'maria.coord@caucaia.ce.gov.br',
                'S': '(85) 98888-5678',
                'T': 'Superintendente Ana Maria'
            },
            {
                'A': '28/01/2025',
                'B': 'José Carlos Mendes',
                'C': 'Sobral',
                'D': 'Ciências da Natureza',
                'E': 'Formação Inicial',
                'F': '09:00',
                'G': '16:00',
                'H': 'Primeira formação do projeto - módulo básico',
                'I': 'PENDENTE',
                'J': 'Pedro Supervisor',
                'K': 'Presencial',
                'L': '7',
                'M': 'Auditório da Secretaria de Educação',
                'N': '50',
                'O': 'Professores recém-contratados',
                'P': 'Apostilas e certificados',
                'Q': 'Lista de presença obrigatória',
                'R': 'pedro.supervisor@sobral.ce.gov.br',
                'S': '(88) 97777-9876',
                'T': ''
            }
        ]
        
        return dados_exemplo

    def parse_data(self, data_str):
        """Converte string de data para objeto date"""
        if not data_str:
            return None
            
        try:
            return datetime.strptime(data_str, '%d/%m/%Y').date()
        except ValueError:
            return None

    def processar_e_mostrar_dados(self):
        """Processa e mostra como os dados ficam tratados"""
        dados_brutos = self.simular_dados_aba_super()
        
        self.logger.info("=" * 80)
        self.logger.info("PREVIA DOS DADOS EXTRAIDOS DA ABA SUPER")
        self.logger.info("=" * 80)
        self.logger.info(f"Total de registros simulados: {len(dados_brutos)}")
        self.logger.info("Colunas mapeadas: A até T (20 colunas)")
        self.logger.info("")
        
        dados_tratados = []
        
        for i, linha in enumerate(dados_brutos, 1):
            # Processar dados da linha
            data_evento = self.parse_data(linha.get('A', ''))
            formador_nome = linha.get('B', '').strip()
            municipio_nome = linha.get('C', '').strip()
            projeto_nome = linha.get('D', '').strip()
            tipo_evento_nome = linha.get('E', '').strip()
            horario_inicio = linha.get('F', '').strip()
            horario_fim = linha.get('G', '').strip()
            observacoes = linha.get('H', '').strip()
            status_aprovacao = linha.get('I', '').strip()
            solicitante = linha.get('J', '').strip()
            modalidade = linha.get('K', '').strip()
            carga_horaria = linha.get('L', '').strip()
            local = linha.get('M', '').strip()
            num_participantes = linha.get('N', '').strip()
            publico_alvo = linha.get('O', '').strip()
            recursos = linha.get('P', '').strip()
            obs_adicionais = linha.get('Q', '').strip()
            email_contato = linha.get('R', '').strip()
            telefone_contato = linha.get('S', '').strip()
            aprovador = linha.get('T', '').strip()
            
            # Determinar status
            if 'APROVADO' in status_aprovacao.upper():
                status_final = 'APROVADO'
            elif 'PENDENTE' in status_aprovacao.upper():
                status_final = 'PENDENTE'
            else:
                status_final = 'PENDENTE'
            
            dados_tratado = {
                'linha_original': i,
                'data_evento': data_evento.strftime('%Y-%m-%d') if data_evento else 'INVÁLIDA',
                'formador': formador_nome,
                'municipio': municipio_nome,
                'projeto': projeto_nome,
                'tipo_evento': tipo_evento_nome,
                'periodo': f"{horario_inicio} às {horario_fim}",
                'status': status_final,
                'solicitante': solicitante,
                'observacoes_completas': f"{observacoes}. {obs_adicionais}".strip('. '),
                'modalidade': modalidade,
                'carga_horaria': carga_horaria,
                'local': local,
                'participantes': num_participantes,
                'publico_alvo': publico_alvo,
                'recursos': recursos,
                'contato': f"{email_contato} | {telefone_contato}",
                'aprovador': aprovador if aprovador else 'Não definido'
            }
            
            dados_tratados.append(dados_tratado)
            
            # Mostrar detalhes de cada registro
            self.logger.info(f"REGISTRO {i}:")
            self.logger.info(f"  Data do Evento: {dados_tratado['data_evento']}")
            self.logger.info(f"  Formador: {dados_tratado['formador']}")
            self.logger.info(f"  Município: {dados_tratado['municipio']}")
            self.logger.info(f"  Projeto: {dados_tratado['projeto']}")
            self.logger.info(f"  Tipo: {dados_tratado['tipo_evento']}")
            self.logger.info(f"  Período: {dados_tratado['periodo']}")
            self.logger.info(f"  Status: {dados_tratado['status']}")
            self.logger.info(f"  Modalidade: {dados_tratado['modalidade']}")
            self.logger.info(f"  Local: {dados_tratado['local']}")
            self.logger.info(f"  Participantes: {dados_tratado['participantes']}")
            self.logger.info(f"  Aprovador: {dados_tratado['aprovador']}")
            self.logger.info("")
        
        # Estatísticas
        aprovados = len([d for d in dados_tratados if d['status'] == 'APROVADO'])
        pendentes = len([d for d in dados_tratados if d['status'] == 'PENDENTE'])
        
        self.logger.info("=" * 80)
        self.logger.info("ESTATISTICAS DOS DADOS TRATADOS")
        self.logger.info("=" * 80)
        self.logger.info(f"Total de registros processados: {len(dados_tratados)}")
        self.logger.info(f"Status APROVADO: {aprovados}")
        self.logger.info(f"Status PENDENTE: {pendentes}")
        self.logger.info("")
        
        # Formadores únicos
        formadores = set(d['formador'] for d in dados_tratados if d['formador'])
        self.logger.info(f"Formadores únicos identificados: {len(formadores)}")
        for formador in sorted(formadores):
            self.logger.info(f"  - {formador}")
        self.logger.info("")
        
        # Municípios únicos
        municipios = set(d['municipio'] for d in dados_tratados if d['municipio'])
        self.logger.info(f"Municípios únicos identificados: {len(municipios)}")
        for municipio in sorted(municipios):
            self.logger.info(f"  - {municipio}")
        self.logger.info("")
        
        # Projetos únicos
        projetos = set(d['projeto'] for d in dados_tratados if d['projeto'])
        self.logger.info(f"Projetos únicos identificados: {len(projetos)}")
        for projeto in sorted(projetos):
            self.logger.info(f"  - {projeto}")
        self.logger.info("")
        
        self.logger.info("=" * 80)
        self.logger.info("ESTRUTURA FINAL PARA IMPORTACAO NO SISTEMA")
        self.logger.info("=" * 80)
        self.logger.info("Cada registro será mapeado para:")
        self.logger.info("  • Tabela 'Solicitacao' (evento principal)")
        self.logger.info("  • Tabela 'Formador' (instrutor responsável)")
        self.logger.info("  • Tabela 'Municipio' (localização)")
        self.logger.info("  • Tabela 'Projeto' (programa educacional)")
        self.logger.info("  • Tabela 'TipoEvento' (categoria da atividade)")
        self.logger.info("  • Tabela 'Aprovacao' (histórico de aprovações)")
        self.logger.info("  • Tabela 'LogAuditoria' (rastreamento de mudanças)")
        self.logger.info("=" * 80)
        
        return dados_tratados

    def handle(self, *args, **options):
        self.setup_logging()
        
        self.logger.info("Iniciando extração da prévia da aba Super")
        self.logger.info("Planilha: Acompanhamento de Agenda | 2025")
        self.logger.info("Aba: Super (1.985 registros reais)")
        self.logger.info("")
        
        try:
            dados_tratados = self.processar_e_mostrar_dados()
            
            # Salvar prévia em arquivo JSON para análise
            with open('dados_planilhas_originais/previa_aba_super.json', 'w', encoding='utf-8') as f:
                json.dump(dados_tratados, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Prévia salva em: dados_planilhas_originais/previa_aba_super.json")
            self.logger.info("Extração da prévia concluída com sucesso!")
            
        except Exception as e:
            self.logger.error(f"Erro durante extração: {e}")
            raise