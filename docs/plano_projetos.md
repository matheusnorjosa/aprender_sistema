# Plano de Projetos - Sistema Aprender

## 📊 **Inventário Completo de Projetos**

### **Vinculados à Superintendência** (14 projetos)
> ✅ **Regra**: Requerem aprovação da superintendência antes da pré-agenda

| Projeto | Setor | Código | Status | Modalidade |
|---------|-------|--------|--------|------------|
| AMMA | Superintendência | - | Ativo | Não informado |
| CATAVENTOS | Superintendência | - | Ativo | Não informado |
| CIRANDAR | Superintendência | - | Ativo | Não informado |
| ESCREVER COMUNICAR E SER | Superintendência | - | Ativo | Não informado |
| Lendo e Escrevendo | Superintendência | - | Ativo | Não informado |
| MIUDEZAS | Superintendência | - | Ativo | Não informado |
| Novo Lendo | Superintendência | - | Ativo | Não informado |
| TEMA | Superintendência | - | Ativo | Não informado |
| TRÂNSITO LEGAL ANOS FINAIS | Superintendência | - | Ativo | Não informado |
| TRÂNSITO LEGAL ANOS INICIAIS | Superintendência | - | Ativo | Não informado |
| TRÂNSITO LEGAL DECIFRA PLACAS | Superintendência | - | Ativo | Não informado |
| TRÂNSITO LEGAL GUIA | Superintendência | - | Ativo | Não informado |
| TRÂNSITO LEGAL TRILHA CIRCUITO | Superintendência | - | Ativo | Não informado |
| UNI DUNI TÊ | Superintendência | - | Ativo | Não informado |

### **Não-Vinculados à Superintendência** (13 projetos)
> ✅ **Regra**: Vão direto para pré-agenda (sem aprovação da superintendência)

#### **Setor Vidas** (3 projetos)
| Projeto | Setor | Código | Status | Modalidade |
|---------|-------|--------|--------|------------|
| Vida e Ciências | Vidas | - | Ativo | Não informado |
| Vida e Linguagem | Vidas | - | Ativo | Não informado |
| Vida e Matemática | Vidas | - | Ativo | Não informado |

#### **Setor ACerta** (2 projetos)  
| Projeto | Setor | Código | Status | Modalidade |
|---------|-------|--------|--------|------------|
| ACerta Língua Portuguesa | ACerta | - | Ativo | Não informado |
| ACerta Matemática | ACerta | - | Ativo | Não informado |

#### **Setor Brincando e Aprendendo** (1 projeto)
| Projeto | Setor | Código | Status | Modalidade |
|---------|-------|--------|--------|------------|
| Brincando e Aprendendo | Brincando e Aprendendo | - | Ativo | Não informado |

#### **Setor Fluir das Emoções** (1 projeto)
| Projeto | Setor | Código | Status | Modalidade |  
|---------|-------|--------|--------|------------|
| Fluir | Fluir das Emoções | - | Ativo | Não informado |

#### **Setor IDEB 10** (1 projeto)
| Projeto | Setor | Código | Status | Modalidade |
|---------|-------|--------|--------|------------|
| IDEB 10 | IDEB 10 | - | Ativo | Não informado |

#### **Setor Ler, Ouvir e Contar** (5 projetos)
| Projeto | Setor | Código | Status | Modalidade |
|---------|-------|--------|--------|------------|
| A Cor da Gente | Ler, Ouvir e Contar | - | Ativo | Não informado |
| Avançando Juntos | Ler, Ouvir e Contar | - | Ativo | Não informado |
| Educação Financeira | Ler, Ouvir e Contar | - | Ativo | Não informado |
| Ler, Ouvir e Contar | Ler, Ouvir e Contar | - | Ativo | Não informado |
| Sou da Paz | Ler, Ouvir e Contar | - | Ativo | Não informado |

## 🎯 **Análise da Informação Solicitada vs Disponível**

### **Dados Disponíveis no Sistema**
- ✅ **Nome do projeto** 
- ✅ **Setor vinculado**
- ✅ **Status ativo/inativo** (todos ativos)
- ✅ **Campo vinculado_superintendencia** (configurado corretamente)
- ✅ **Descrição** (campo existe, maioria vazio)

### **Dados Faltantes** (requerem planilhas externas)
- ❌ **Coordenador(es) + e-mails** - Não disponível no sistema atual
- ❌ **Formador(es) vinculados** - Relacionamento existe mas precisa ser populado
- ❌ **Gerente(s) responsáveis** - Relacionamento usuario-setor precisa ser melhorado
- ❌ **Modalidade** (Presencial, Online, Workshop, Acompanhamento) - Campo existe em TipoEvento
- ❌ **Código produto** - Campos existem mas não populados

## 🗂️ **Fontes de Dados Necessárias**

### **Planilhas Mencionadas**
1. **produtos.xlsx** - Colunas: Nome, Projeto, Tipo
2. **superintendencia.xlsx** - Dados da superintendência
3. **Usuários.xlsx** - Mapeamento usuários ↔ projetos ↔ funções

### **Comandos de Importação Disponíveis**
```python
# Já implementados no sistema
python manage.py import_projetos  # Importa dados de projetos
python manage.py import_organizational_structure  # Estrutura organizacional
python manage.py create_basic_setores  # Setores básicos
```

## 👥 **Estrutura de Responsabilidades**

### **Modelo Atual (Por Inferência)**
```python
# Relacionamentos existentes no sistema
Usuario.setor → Setor  # Usuário pertence a um setor
Projeto.setor → Setor  # Projeto pertence a um setor  
Formador.usuario → Usuario  # Formador tem usuário vinculado
```

### **Mapeamento de Responsabilidades** (Requer população)
- **Coordenadores**: `Usuario.objects.filter(groups__name='coordenador', setor=projeto.setor)`
- **Gerentes**: `Usuario.objects.filter(groups__name='gerente', setor=projeto.setor)`
- **Formadores**: `Formador.objects.filter(usuario__setor=projeto.setor)`

## 🔧 **Funcionalidade de Vinculação de Formadores**

### **Página para Coordenador** (Solicitada)
**Objetivo**: Coordenador vinculado à superintendência gerencia vínculos formadores ↔ projetos ↔ municípios

### **Implementação Sugerida**
```python
# View necessária
class FormadorVinculacaoView(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = "core.change_formador"
    
    def get_queryset(self):
        # Apenas coordenadores de projetos vinculados à superintendência
        if self.request.user.setor and self.request.user.setor.vinculado_superintendencia:
            return Formador.objects.filter(ativo=True)
        return Formador.objects.none()
```

### **Relacionamentos para Vínculos**
```python
# Modelos que suportam a funcionalidade
FormadoresSolicitacao  # Many-to-many Formador ↔ Solicitacao
Usuario.municipio      # Formador ↔ Município  
Usuario.setor         # Formador ↔ Setor/Projeto
```

## 📈 **Estatísticas do Sistema**

### **Distribuição de Projetos**
- **Total**: 27 projetos
- **Vinculados à superintendência**: 14 (51.9%)
- **Não vinculados**: 13 (48.1%)
- **Status ativo**: 27 (100%)

### **Distribuição por Setor**
- **Superintendência**: 14 projetos (51.9%)
- **Ler, Ouvir e Contar**: 5 projetos (18.5%)
- **Vidas**: 3 projetos (11.1%)
- **ACerta**: 2 projetos (7.4%)
- **Outros setores**: 3 projetos (11.1%)

## ✅ **Validação do Sistema Atual**

### **Estrutura de Dados**
- ✅ **Modelo Projeto**: Suporta todas as funcionalidades necessárias
- ✅ **Vinculação superintendência**: Corretamente implementada
- ✅ **Relacionamentos**: Existem mas precisam ser populados
- ✅ **Classificação**: 100% dos projetos classificados corretamente

### **Funcionalidades Faltantes**
- ⚠️ **Dados de responsáveis**: Dependem de importação das planilhas
- ⚠️ **Interface de vinculação**: Precisa ser desenvolvida
- ⚠️ **Modalidades**: Campo TipoEvento existe mas não está populado

## 🎯 **Recomendações**

1. **Imediato**: Sistema está funcionalmente completo para os fluxos de aprovação
2. **Curto prazo**: Importar dados das planilhas (coordenadores, formadores, modalidades)
3. **Médio prazo**: Desenvolver interface de vinculação formadores ↔ projetos ↔ municípios
4. **Longo prazo**: Dashboard analítico de distribuição de responsabilidades