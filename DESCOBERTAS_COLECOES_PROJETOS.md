# DESCOBERTAS: COLEÇÕES E PROJETOS NO SISTEMA

## RESUMO EXECUTIVO

**Data**: Janeiro 2025  
**Análise**: Mapeamento completo da hierarquia Produtos → Coleções → Projetos  
**Descoberta principal**: Coleções são conjuntos de produtos educacionais que definem os projetos pedagógicos  

---

## 1. HIERARQUIA IDENTIFICADA

### PRODUTOS (Base) → COLEÇÕES (Agrupamento) → PROJETOS (Implementação)

```
PRODUTOS (680+ itens)
├── "ESCREVER COMUNICAR E SER 1 LIVRO ALUNO"
├── "VIDA & MATEMÁTICA 1 ANO LIVRO ALUNO"
├── "SUPERATIVAR LINGUAGEM 2 ANO LIVRO ALUNO"
└── ...

COLEÇÕES (Auto-geradas por ano + tipo)
├── "Coleção 2026 - Material do Aluno - ACERTA"
├── "Coleção 2026 - Material do Professor - VIDAS"  
├── "Coleção 2025 - Material do Aluno - SUPER"
└── ...

PROJETOS (Implementação em eventos)
├── SUPER (1.985 eventos)
├── ACERTA (1.001 eventos)  
├── VIDAS (1.002 eventos)
├── BRINCANDO (1.000 eventos)
└── ...
```

---

## 2. ANÁLISE QUANTITATIVA POR PROJETO

### 2.1 Distribuição de Produtos por Projeto
- **ACERTA**: 202 produtos únicos
- **VIDAS**: 455 produtos únicos  
- **SUPER**: 24 produtos únicos
- **BRINCANDO**: Não identificados produtos específicos

### 2.2 Volume de Eventos por Projeto (ACOMPANHAMENTO 2025)
- **SUPER**: 1.985 eventos programados
- **VIDAS**: 1.002 eventos programados
- **ACERTA**: 1.001 eventos programados  
- **BRINCANDO**: 1.000 eventos programados

**Total**: 4.988 eventos distribuídos entre os 4 projetos principais

---

## 3. MAPEAMENTO TÉCNICO NO DJANGO

### 3.1 Modelos Implementados ✅
O sistema Django já implementou a estrutura básica:

```python
# planilhas/models.py
class Colecao(models.Model):
    nome = models.CharField(max_length=200)
    ano = models.IntegerField()
    tipo_material = models.CharField(max_length=50)
    projeto = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['ano', 'tipo_material', 'projeto']]

class Compra(models.Model):
    # ... outros campos ...
    colecao = models.ForeignKey(Colecao, on_delete=models.CASCADE, null=True, blank=True)
```

### 3.2 Auto-geração de Coleções ✅
Sistema automaticamente cria coleções baseado em:
- **Ano**: Extraído do campo "usará a coleção em YYYY"
- **Tipo Material**: "Material do Aluno" vs "Material do Professor"  
- **Projeto**: ACERTA, VIDAS, SUPER, etc.

---

## 4. PROJETOS EDUCACIONAIS IDENTIFICADOS

### 4.1 SUPER (Sistema Superativar)
- **Foco**: Linguagem e alfabetização
- **Produtos**: 24 diferentes (menor coleção)
- **Eventos**: 1.985 (maior volume de implementação)
- **Subprojetos ativos**:
  - Novo Lendo: 484 eventos
  - Tema: 369 eventos  
  - Lendo e Escrevendo: 220 eventos
  - Projeto AMMA: 92 eventos

### 4.2 VIDAS (Vida & Disciplinas)
- **Foco**: Matemática, Ciências, Linguagem
- **Produtos**: 455 diferentes (maior coleção)
- **Eventos**: 1.002 programados
- **Subprojetos ativos**:
  - Vida & Matemática: 125 eventos
  - Vida & Linguagem: 110 eventos  
  - Vida & Ciências: 35 eventos
  - Avançando Juntos Língua Portuguesa: 4 eventos

### 4.3 ACERTA (Sistema ACerta)
- **Foco**: Educação estruturada
- **Produtos**: 202 diferentes  
- **Eventos**: 1.001 programados
- **Implementação**: Projeto consolidado (456 eventos diretos)

### 4.4 BRINCANDO (Brincando e Aprendendo)  
- **Foco**: Educação lúdica
- **Produtos**: Não mapeados nos dados de COMPRAS
- **Eventos**: 1.000 programados
- **Implementação**: 100% eventos diretos do projeto

---

## 5. PADRÕES DE NOMENCLATURA DESCOBERTOS

### 5.1 Produtos
Formato: `[COLEÇÃO] [SÉRIE] [TIPO] [PÚBLICO]`

Exemplos:
- `ESCREVER COMUNICAR E SER 1 LIVRO ALUNO`
- `VIDA & MATEMÁTICA 3 ANO LIVRO PROFESSOR`  
- `SUPERATIVAR LINGUAGEM 1 ANO CADERNO ALUNO`

### 5.2 Coleções (Auto-geradas)
Formato: `Coleção [ANO] - [TIPO_MATERIAL] - [PROJETO]`

Exemplos:
- `Coleção 2026 - Material do Aluno - ACERTA`
- `Coleção 2025 - Material do Professor - VIDAS`

### 5.3 Projetos (Implementação)
- Usam nomes diretos: SUPER, ACERTA, VIDAS, BRINCANDO
- Podem ter subprojetos (ex: "Novo Lendo", "Vida & Matemática")

---

## 6. RELAÇÃO COM EVENTOS/FORMAÇÕES

### 6.1 Fluxo Identificado
```
COMPRA DE PRODUTO
    ↓ (auto-associa)
COLEÇÃO CRIADA/ENCONTRADA  
    ↓ (planificação)
EVENTOS PROGRAMADOS
    ↓ (implementação)
FORMAÇÕES REALIZADAS
```

### 6.2 Campos de Conexão
**Planilha COMPRAS**:
- Campo "Usará a coleção em": Define ANO da implementação
- Campo "Projeto": Define a linha pedagógica  
- Campo "Produto": Define o material específico

**Planilha ACOMPANHAMENTO**:  
- Eventos separados por abas de projeto (Super, ACerta, Vidas, Brincando)
- Campo "projeto": Especifica subprojeto dentro da linha principal
- Coordenadores e formadores específicos por projeto

---

## 7. IMPLICAÇÕES PARA O SISTEMA DJANGO

### 7.1 Funcionalidades Já Implementadas ✅
- Modelo Coleção com auto-criação
- Associação automática Compra → Coleção  
- Campos de controle temporal (ano de uso)

### 7.2 Funcionalidades Pendentes
- **Integração Coleção → Solicitação**: Eventos devem referenciar coleções
- **Relatórios por Projeto**: Agrupar eventos/formações por linha pedagógica
- **Validação de Consistência**: Formador especializado por tipo de projeto
- **Dashboard Executivo**: Visão consolidada por coleção/projeto

### 7.3 Próximas Implementações Recomendadas
1. **Campo projeto em core.models.Solicitacao**
2. **Relacionamento Coleção ↔ TipoEvento**  
3. **Filtros por projeto nas views de eventos**
4. **Relatórios de uso de coleções por ano**

---

## 8. DESCOBERTA CRÍTICA: PLANEJAMENTO TEMPORAL

### 8.1 Padrão Identificado
O sistema trabalha com **planejamento anual antecipado**:

- **2024**: Compras realizadas para uso em 2025/2026
- **2025**: Ano de implementação atual dos eventos  
- **2026**: Próximo ciclo de implementação já sendo planejado

### 8.2 Implicação Técnica
O Django deve suportar:
- **Compras multianuais** (hoje compro, uso ano que vem)
- **Eventos de implementação** (ano corrente)  
- **Relatórios por ciclo** (ciclo 2024→2025, ciclo 2025→2026)

---

## CONCLUSÕES

1. **Coleções = Produtos agrupados** por ano, tipo e projeto pedagógico
2. **Projetos = Implementação** das coleções através de eventos/formações  
3. **Sistema Django já implementa** a base técnica necessária
4. **Próximo passo**: Conectar coleções com sistema de eventos/solicitações
5. **Planejamento temporal** é aspecto crítico para relatórios e controle

**Status**: Sistema preparado para expansão completa do módulo coleções → projetos → eventos.