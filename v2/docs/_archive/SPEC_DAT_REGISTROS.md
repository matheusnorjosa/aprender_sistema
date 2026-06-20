# Especificação: Módulo DAT Registros - AS v2

**Data:** 2025-12-12
**Status:** Planejamento
**Baseado em:** Prompt genérico adaptado para realidade AS v2

---

## 1. ANÁLISE DE GAP: O QUE JÁ EXISTE vs O QUE FALTA

### 1.1 Models Existentes (Reutilizar)

| Model | Campos Existentes | Observações |
|-------|-------------------|-------------|
| `Municipio` | nome, uf, ibge_code, ativo, lat, lng | ✅ Completo, falta apenas relação com Estado/Região |
| `Projeto` | nome, codigo, fluxo, gerencia_FK, is_test | ⚠️ Falta conceito de "Projeto Geral" |
| `Gerencia` | nome, nome_setor, gerente_FK | ✅ Completo |
| `AcaoDAT` | municipio, projeto, tipo_acao, responsavel, observacao, data_registro | ❌ Muito básico, precisa expandir |

### 1.2 O Que Precisa Ser Criado

#### 1.2.1 Novos Models

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOVOS MODELS NECESSÁRIOS                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Regiao (opcional)                                          │
│     - Centro-Oeste, Nordeste, Norte, Sudeste, Sul              │
│                                                                 │
│  2. Estado (opcional)                                           │
│     - 27 UFs com FK para Regiao                                │
│                                                                 │
│  3. ProjetoGeral                                               │
│     - Agrupa projetos (ex: VIDA E LINGUAGEM 6,7,8,9)           │
│     - Define: usa_avaliar, tipo_calculo_codigos                │
│                                                                 │
│  4. DATRegistro (PRINCIPAL)                                    │
│     - Substitui/expande AcaoDAT                                │
│     - Campos FORMAR + AVALIAR + contadores                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Decisão Arquitetural

**Opção A: Expandir `AcaoDAT` existente**
- Pros: Não quebra código existente, migration simples
- Cons: Model fica muito grande, mistura conceitos

**Opção B: Criar novo model `DATRegistro`** ✅ **RECOMENDADO**
- Pros: Separação clara de conceitos, mais limpo
- Cons: Novo endpoint, novo frontend

**Opção C: Adicionar `ProjetoGeral` e expandir `AcaoDAT`**
- Pros: Hierarquia correta de projetos
- Cons: Mais complexo

**Decisão:** Opção B + parcial C (criar `ProjetoGeral` para regras de negócio)

---

## 2. MODELS BACKEND (Django)

### 2.1 Model: ProjetoGeral (Novo)

```python
# apps/core/models/organizacao.py (adicionar)

class ProjetoGeral(models.Model):
    """
    Agrupa projetos relacionados e define regras de negócio.

    Exemplo:
    - ProjetoGeral: "VIDA E LINGUAGEM"
      - Projetos: VIDA E LINGUAGEM 6, 7, 8, 9
      - usa_avaliar: True
      - tipo_calculo: por_professor, multiplicador: 1.1
    """

    TIPO_CALCULO_CHOICES = [
        ('por_aluno', 'Por Aluno (qtde_alunos / divisor)'),
        ('por_professor', 'Por Professor (qtde_professores * multiplicador)'),
        ('nao_aplicavel', 'Não Aplicável (não gera códigos)'),
    ]

    nome = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Ex: ACERTA MATEMÁTICA, VIDA E LINGUAGEM"
    )
    usa_avaliar = models.BooleanField(
        default=False,
        help_text="Se o projeto utiliza a plataforma AVALIAR"
    )
    tipo_calculo_codigos = models.CharField(
        max_length=15,
        choices=TIPO_CALCULO_CHOICES,
        default='por_professor',
        help_text="Como calcular número de códigos FORMAR"
    )
    divisor_aluno = models.PositiveIntegerField(
        default=20,
        help_text="Divisor quando tipo = por_aluno"
    )
    multiplicador_professor = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.1,
        help_text="Multiplicador quando tipo = por_professor"
    )
    ativo = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_projeto_geral"
        verbose_name = "Projeto Geral"
        verbose_name_plural = "Projetos Gerais"
        ordering = ["nome"]

    def __str__(self) -> str:
        avaliar = "✅" if self.usa_avaliar else "⭕"
        return f"{self.nome} {avaliar}"
```

### 2.2 Model: DATRegistro (Novo - Principal)

```python
# apps/core/models/dat_registro.py (novo arquivo)

"""
AS v2 — DAT Registro Model

Model principal para acompanhamento de turmas educacionais.
Integra dados das plataformas FORMAR e AVALIAR.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from django.db import models
from django.utils import timezone


class DATRegistro(models.Model):
    """
    Registro de acompanhamento DAT por município/projeto.

    Seções:
    1. Dados Básicos: município, projeto, quantidades
    2. Plataforma FORMAR: turma, códigos, status de envio
    3. Plataforma AVALIAR: alunos recebidos/validados/importados

    Regras de negócio:
    - nr_codigos é calculado automaticamente baseado em projeto_geral
    - usa_avaliar é derivado de projeto_geral.usa_avaliar
    - Campos AVALIAR só são relevantes quando usa_avaliar=True
    """

    STATUS_CHOICES = [
        ('concluido', 'Concluído'),
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('nao_aplicavel', 'Não Aplicável'),
        ('erro', 'Erro'),
    ]

    TURMA_STATUS_CHOICES = [
        ('criada', 'Criada'),
        ('pendente', 'Pendente'),
        ('erro', 'Erro'),
    ]

    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO 1: DADOS BÁSICOS
    # ═══════════════════════════════════════════════════════════════

    municipio = models.ForeignKey(
        "core.Municipio",
        on_delete=models.PROTECT,
        related_name="dat_registros",
        verbose_name="Município",
    )
    projeto_geral = models.ForeignKey(
        "core.ProjetoGeral",
        on_delete=models.PROTECT,
        related_name="dat_registros",
        verbose_name="Projeto Geral",
        help_text="Ex: ACERTA MATEMÁTICA, VIDA E LINGUAGEM"
    )
    projeto = models.ForeignKey(
        "core.Projeto",
        on_delete=models.PROTECT,
        related_name="dat_registros",
        verbose_name="Projeto Específico",
        help_text="Ex: VIDA E LINGUAGEM 6, ACERTA BRASIL MATEMATICA"
    )
    aluno_qtde = models.PositiveIntegerField(
        verbose_name="Quantidade de Alunos",
        help_text="Total de alunos na turma"
    )
    professor_qtde = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Quantidade de Professores",
        help_text="Total de professores (necessário para cálculo de códigos)"
    )

    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO 2: PLATAFORMA FORMAR
    # ═══════════════════════════════════════════════════════════════

    reuniao_dat = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Reunião DAT",
        help_text="Data da reunião de alinhamento DAT"
    )
    turma_formar_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="ID Turma FORMAR",
        help_text="ID do curso na plataforma FORMAR"
    )
    turma_formar_status = models.CharField(
        max_length=10,
        choices=TURMA_STATUS_CHOICES,
        default='pendente',
        verbose_name="Status Turma FORMAR"
    )

    # Calculado automaticamente
    nr_codigos = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Nº de Códigos",
        help_text="Calculado automaticamente baseado em projeto_geral"
    )

    # Status de envio FORMAR
    chaves_inscricao_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Chaves de Inscrição"
    )
    chaves_inscricao_data = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Chaves Inscrição"
    )

    instrucoes_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Instruções"
    )
    instrucoes_data = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Instruções"
    )

    envio_codigos_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Envio de Códigos"
    )
    envio_codigos_data = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data Envio Códigos"
    )

    obs_formar = models.TextField(
        blank=True,
        max_length=1000,
        verbose_name="Observações FORMAR"
    )

    # ═══════════════════════════════════════════════════════════════
    # SEÇÃO 3: PLATAFORMA AVALIAR
    # ═══════════════════════════════════════════════════════════════

    # Derivado de projeto_geral.usa_avaliar (readonly no form)
    usa_avaliar = models.BooleanField(
        default=False,
        verbose_name="Usa AVALIAR",
        help_text="Preenchido automaticamente baseado no Projeto Geral"
    )

    alunos_recebidos_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='nao_aplicavel',
        verbose_name="Alunos Recebidos"
    )
    alunos_recebidos_datas = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Datas Recebimento",
        help_text="Array de datas: ['2025-03-12', '2025-04-25']"
    )

    alunos_validados_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='nao_aplicavel',
        verbose_name="Alunos Validados"
    )
    alunos_validados_datas = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Datas Validação"
    )

    alunos_importados_status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='nao_aplicavel',
        verbose_name="Alunos Importados"
    )
    alunos_importados_datas = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Datas Importação"
    )

    obs_avaliar = models.TextField(
        blank=True,
        max_length=1000,
        verbose_name="Observações AVALIAR"
    )

    # ═══════════════════════════════════════════════════════════════
    # AUDITORIA
    # ═══════════════════════════════════════════════════════════════

    external_hash = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Hash Externo",
        help_text="Para idempotência de importação ETL"
    )
    created_by = models.ForeignKey(
        "core.Usuario",
        on_delete=models.PROTECT,
        related_name="dat_registros_criados",
        verbose_name="Criado por"
    )
    updated_by = models.ForeignKey(
        "core.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dat_registros_atualizados",
        verbose_name="Atualizado por"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_dat_registro"
        verbose_name = "Registro DAT"
        verbose_name_plural = "Registros DAT"
        ordering = ["-created_at", "municipio__nome"]
        indexes = [
            models.Index(fields=["municipio", "projeto_geral", "projeto"]),
            models.Index(fields=["projeto_geral", "usa_avaliar"]),
            models.Index(fields=["external_hash"]),
            models.Index(fields=["turma_formar_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["municipio", "projeto_geral", "projeto"],
                name="unique_dat_registro_municipio_projeto"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.municipio.nome}-{self.municipio.uf} | {self.projeto.nome}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save para calcular campos automáticos."""
        # Sincronizar usa_avaliar com projeto_geral
        if self.projeto_geral_id:
            self.usa_avaliar = self.projeto_geral.usa_avaliar

        # Calcular nr_codigos
        self.nr_codigos = self._calcular_nr_codigos()

        # Atualizar status AVALIAR se não usa
        if not self.usa_avaliar:
            self.alunos_recebidos_status = 'nao_aplicavel'
            self.alunos_validados_status = 'nao_aplicavel'
            self.alunos_importados_status = 'nao_aplicavel'

        super().save(*args, **kwargs)

    def _calcular_nr_codigos(self) -> int | None:
        """
        Calcula número de códigos baseado nas regras do projeto_geral.

        Regras:
        - por_aluno: ceil(aluno_qtde / divisor)
        - por_professor: ceil(professor_qtde * multiplicador)
        - nao_aplicavel: None
        """
        if not self.projeto_geral_id:
            return None

        tipo = self.projeto_geral.tipo_calculo_codigos

        if tipo == 'nao_aplicavel':
            return None

        if tipo == 'por_aluno':
            if self.aluno_qtde and self.projeto_geral.divisor_aluno:
                return math.ceil(self.aluno_qtde / self.projeto_geral.divisor_aluno)
            return None

        if tipo == 'por_professor':
            if self.professor_qtde and self.projeto_geral.multiplicador_professor:
                mult = float(self.projeto_geral.multiplicador_professor)
                return math.ceil(self.professor_qtde * mult)
            return None

        return None

    @property
    def turma_formar_url(self) -> str | None:
        """Gera URL da turma na plataforma FORMAR."""
        if self.turma_formar_id:
            return f"https://www.aprenderformar.com.br/plataforma/course/view.php?id={self.turma_formar_id}"
        return None

    @property
    def status_geral(self) -> str:
        """Calcula status geral do registro."""
        # Verifica campos FORMAR obrigatórios
        formar_ok = all([
            self.chaves_inscricao_status == 'concluido',
            self.instrucoes_status == 'concluido',
            self.envio_codigos_status == 'concluido',
        ])

        if not formar_ok:
            return 'pendente_formar'

        # Se usa AVALIAR, verifica campos AVALIAR
        if self.usa_avaliar:
            avaliar_ok = all([
                self.alunos_recebidos_status == 'concluido',
                self.alunos_validados_status == 'concluido',
                self.alunos_importados_status == 'concluido',
            ])
            if not avaliar_ok:
                return 'pendente_avaliar'

        return 'completo'
```

### 2.3 Atualizar Model Projeto

```python
# Adicionar FK para ProjetoGeral em apps/core/models/organizacao.py

class Projeto(models.Model):
    # ... campos existentes ...

    projeto_geral = models.ForeignKey(
        "core.ProjetoGeral",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projetos_especificos",
        help_text="Projeto geral pai (ex: VIDA E LINGUAGEM para VIDA E LINGUAGEM 6)"
    )
```

---

## 3. DADOS MESTRES (Seed Data)

### 3.1 Projetos Gerais

```python
# Dados para criar via migration ou ETL

PROJETOS_GERAIS = [
    {"nome": "A COR DA GENTE", "usa_avaliar": False, "tipo_calculo": "por_aluno", "divisor": 20},
    {"nome": "ACERTA MATEMÁTICA", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "ACERTA PORTUGUÊS", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "AVANÇANDO JUNTOS MATEMÁTICA", "usa_avaliar": False, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "AVANÇANDO JUNTOS PORTUGUÊS", "usa_avaliar": False, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "BRINCANDO E APRENDENDO", "usa_avaliar": False, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "CIRANDAR", "usa_avaliar": False, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "ECS", "usa_avaliar": False, "tipo_calculo": "por_aluno", "divisor": 20},
    {"nome": "ED FINANCEIRA", "usa_avaliar": False, "tipo_calculo": "por_aluno", "divisor": 20},
    {"nome": "FLUIR DAS EMOÇÕES", "usa_avaliar": False, "tipo_calculo": "nao_aplicavel"},
    {"nome": "GESTÃO ESCOLAR", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "LEIO, ESCREVO E CALCULO", "usa_avaliar": False, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "LENDO E ESCREVENDO", "usa_avaliar": False, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "LER, OUVIR E CONTAR", "usa_avaliar": False, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "NOVO LENDO", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "PROJETO AMMA", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "SUPERATIVAR - LINGUAGENS", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "SUPERATIVAR - MATEMÁTICA", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "TEMA", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "VIDA E CIÊNCIAS", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "VIDA E LINGUAGEM", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
    {"nome": "VIDA E MATEMÁTICA", "usa_avaliar": True, "tipo_calculo": "por_professor", "mult": 1.1},
]
```

---

## 4. API ENDPOINTS (DRF)

### 4.1 Endpoints

```
GET    /api/dat/registros/              # Lista com filtros e paginação
POST   /api/dat/registros/              # Criar registro
GET    /api/dat/registros/{id}/         # Detalhe
PATCH  /api/dat/registros/{id}/         # Atualizar parcial
DELETE /api/dat/registros/{id}/         # Excluir (soft delete ou hard?)

GET    /api/dat/registros/export/       # Exportar CSV/Excel
POST   /api/dat/registros/import/       # Importar planilha

# Auxiliares
GET    /api/projetos-gerais/            # Lista projetos gerais
GET    /api/projetos-gerais/{id}/projetos/  # Projetos de um projeto geral
```

### 4.2 Filtros Disponíveis

```python
# django-filter
class DATRegistroFilter(filters.FilterSet):
    regiao = filters.CharFilter(method='filter_by_regiao')
    uf = filters.CharFilter(field_name='municipio__uf')
    municipio = filters.NumberFilter(field_name='municipio_id')
    projeto_geral = filters.NumberFilter(field_name='projeto_geral_id')
    projeto = filters.NumberFilter(field_name='projeto_id')
    usa_avaliar = filters.BooleanFilter()
    status_geral = filters.CharFilter(method='filter_by_status')

    class Meta:
        model = DATRegistro
        fields = ['uf', 'municipio', 'projeto_geral', 'projeto', 'usa_avaliar']
```

### 4.3 Permissões

```python
# Mapeamento para RBAC existente

| Ação      | Permissão AS v2                     |
|-----------|-------------------------------------|
| Visualizar| IsAuthenticated (qualquer usuário)  |
| Criar     | IsDATOrSuper                        |
| Editar    | IsDATOrSuper                        |
| Excluir   | IsSuperintendencia                  |
| Importar  | IsDATOrSuper                        |
| Exportar  | IsAuthenticated                     |
```

---

## 5. FRONTEND (React + Ant Design)

### 5.1 Estrutura de Arquivos

```
v2/frontend/src/
├── pages/
│   └── AdminDAT/
│       ├── DATRegistrosPage.jsx      # Página principal (lista + filtros)
│       ├── DATRegistroForm.jsx       # Formulário criar/editar
│       ├── DATRegistroImport.jsx     # Modal de importação
│       └── components/
│           ├── DATRegistroTable.jsx  # Tabela com colunas agrupadas
│           ├── DATRegistroFilters.jsx
│           ├── StatusBadge.jsx       # ✅ ⭕ ⚠️ ❌
│           └── MultiDatePicker.jsx   # Para datas AVALIAR
├── services/
│   └── datRegistroService.js         # API calls
└── hooks/
    └── useDATRegistros.js            # Custom hook com filtros
```

### 5.2 Componentes Ant Design a Utilizar

```javascript
// Lista de componentes Ant Design para o módulo

import {
  Table,           // Tabela principal com columns agrupados
  Form,            // Formulário
  Input,           // Campos texto
  InputNumber,     // Campos numéricos
  Select,          // Dropdowns (Projeto, Município)
  DatePicker,      // Datas simples
  Switch,          // Toggle status concluído/pendente
  Tag,             // Status badges
  Tooltip,         // Observações
  Button,          // Ações
  Space,           // Agrupamento
  Card,            // Seções do formulário
  Divider,         // Separador FORMAR/AVALIAR
  Upload,          // Importação de arquivo
  Modal,           // Confirmações e imports
  message,         // Feedback
  Spin,            // Loading
  Badge,           // Contadores
  Typography,      // Títulos seções
} from 'antd';

// Ícones
import {
  CheckCircleOutlined,   // ✅ Concluído
  CloseCircleOutlined,   // ⭕ Não usa
  ExclamationCircleOutlined, // ⚠️ Pendente
  CloseOutlined,         // ❌ Erro
  LinkOutlined,          // 🔗 Link FORMAR
  CommentOutlined,       // 💬 Observações
  UploadOutlined,        // Upload
  DownloadOutlined,      // Download
  FilterOutlined,        // Filtros
  PlusOutlined,          // Novo registro
} from '@ant-design/icons';
```

### 5.3 Colunas da Tabela (Agrupadas)

```javascript
const columns = [
  // SEÇÃO 1: DADOS BÁSICOS
  {
    title: 'Município - UF',
    dataIndex: ['municipio', 'nome_completo'],
    fixed: 'left',
    width: 180,
  },
  {
    title: 'Projeto Geral',
    dataIndex: ['projeto_geral', 'nome'],
    width: 200,
  },
  {
    title: 'Projeto',
    dataIndex: ['projeto', 'nome'],
    width: 220,
  },
  {
    title: 'Alunos',
    dataIndex: 'aluno_qtde',
    align: 'right',
    width: 100,
    render: (val) => val?.toLocaleString('pt-BR'),
  },
  {
    title: 'Professores',
    dataIndex: 'professor_qtde',
    align: 'right',
    width: 100,
    render: (val) => val?.toLocaleString('pt-BR') || '-',
  },

  // SEÇÃO 2: FORMAR (agrupada)
  {
    title: '⬆️ DETALHES FORMAR',
    children: [
      { title: 'Reunião DAT', dataIndex: 'reuniao_dat', width: 100, render: formatDate },
      {
        title: 'Turma FORMAR',
        dataIndex: 'turma_formar_id',
        width: 100,
        render: (id, record) => id ? (
          <a href={record.turma_formar_url} target="_blank" rel="noopener">
            🔗 {id}
          </a>
        ) : '-'
      },
      { title: 'Nº Códigos', dataIndex: 'nr_codigos', width: 80, align: 'right' },
      { title: 'Chaves', dataIndex: 'chaves_inscricao_status', width: 80, render: renderStatus },
      { title: 'Instruções', dataIndex: 'instrucoes_status', width: 80, render: renderStatus },
      { title: 'Envio', dataIndex: 'envio_codigos_status', width: 80, render: renderStatus },
      { title: 'Obs', dataIndex: 'obs_formar', width: 40, render: renderObsTooltip },
    ],
  },

  // SEÇÃO 3: AVALIAR (agrupada)
  {
    title: '⬆️ DETALHES AVALIAR',
    children: [
      { title: 'Usa', dataIndex: 'usa_avaliar', width: 60, render: (v) => v ? '✅' : '⭕' },
      { title: 'Recebidos', dataIndex: 'alunos_recebidos_status', width: 100, render: renderStatusWithDates },
      { title: 'Validados', dataIndex: 'alunos_validados_status', width: 100, render: renderStatusWithDates },
      { title: 'Importados', dataIndex: 'alunos_importados_status', width: 100, render: renderStatusWithDates },
      { title: 'Obs', dataIndex: 'obs_avaliar', width: 40, render: renderObsTooltip },
    ],
  },
];
```

### 5.4 Formulário (Seções)

```javascript
// DATRegistroForm.jsx - Estrutura

<Form layout="vertical" onFinish={handleSubmit}>
  {/* SEÇÃO 1: DADOS BÁSICOS */}
  <Card title="Dados Básicos" bordered={false}>
    <Row gutter={16}>
      <Col span={8}>
        <Form.Item name="municipio_id" label="Município" rules={[{ required: true }]}>
          <RemoteSelect endpoint="/api/municipios/" placeholder="Digite para buscar..." />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item name="projeto_geral_id" label="Projeto Geral" rules={[{ required: true }]}>
          <Select options={projetosGerais} onChange={handleProjetoGeralChange} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item name="projeto_id" label="Projeto" rules={[{ required: true }]}>
          <Select options={projetosFiltrados} disabled={!projetoGeralSelecionado} />
        </Form.Item>
      </Col>
    </Row>
    <Row gutter={16}>
      <Col span={6}>
        <Form.Item name="aluno_qtde" label="Qtde Alunos" rules={[{ required: true }]}>
          <InputNumber min={0} max={99999} style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="professor_qtde" label="Qtde Professores">
          <InputNumber min={0} max={9999} style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item label="Nº de Códigos (calculado)">
          <InputNumber value={nrCodigosCalculado} disabled style={{ width: '100%' }} />
        </Form.Item>
      </Col>
    </Row>
  </Card>

  <Divider />

  {/* SEÇÃO 2: FORMAR */}
  <Card title="⬆️ Plataforma FORMAR" bordered={false}>
    <Row gutter={16}>
      <Col span={6}>
        <Form.Item name="reuniao_dat" label="Data Reunião DAT">
          <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="turma_formar_id" label="ID Turma FORMAR">
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="turma_formar_status" label="Status Turma">
          <Select options={[
            { value: 'criada', label: 'Criada' },
            { value: 'pendente', label: 'Pendente' },
            { value: 'erro', label: 'Erro' },
          ]} />
        </Form.Item>
      </Col>
    </Row>

    {/* Status com toggle + data */}
    <Row gutter={16}>
      <Col span={8}>
        <StatusDateField name="chaves_inscricao" label="Chaves de Inscrição" />
      </Col>
      <Col span={8}>
        <StatusDateField name="instrucoes" label="Instruções" />
      </Col>
      <Col span={8}>
        <StatusDateField name="envio_codigos" label="Envio de Códigos" />
      </Col>
    </Row>

    <Form.Item name="obs_formar" label="Observações FORMAR">
      <Input.TextArea rows={3} maxLength={1000} showCount />
    </Form.Item>
  </Card>

  <Divider />

  {/* SEÇÃO 3: AVALIAR (condicional) */}
  <Card
    title="⬆️ Plataforma AVALIAR"
    bordered={false}
    extra={<Tag color={usaAvaliar ? 'green' : 'default'}>{usaAvaliar ? '✅ Ativo' : '⭕ Não usa'}</Tag>}
  >
    {usaAvaliar ? (
      <>
        <Row gutter={16}>
          <Col span={8}>
            <MultiStatusDateField name="alunos_recebidos" label="Alunos Recebidos" />
          </Col>
          <Col span={8}>
            <MultiStatusDateField name="alunos_validados" label="Alunos Validados" />
          </Col>
          <Col span={8}>
            <MultiStatusDateField name="alunos_importados" label="Alunos Importados" />
          </Col>
        </Row>

        <Form.Item name="obs_avaliar" label="Observações AVALIAR">
          <Input.TextArea rows={3} maxLength={1000} showCount />
        </Form.Item>
      </>
    ) : (
      <Typography.Text type="secondary">
        Este projeto não utiliza a plataforma AVALIAR.
      </Typography.Text>
    )}
  </Card>

  <Divider />

  {/* BOTÕES */}
  <Space>
    <Button type="primary" htmlType="submit">Salvar</Button>
    <Button onClick={handleSaveAndNew}>Salvar e Novo</Button>
    <Button onClick={handleCancel}>Cancelar</Button>
  </Space>
</Form>
```

---

## 6. ROTAS E NAVEGAÇÃO

### 6.1 Rotas Frontend

```javascript
// App.jsx - adicionar rotas

<Route path="/admin-dat/registros" element={<DATRegistrosPage />} />
<Route path="/admin-dat/registros/novo" element={<DATRegistroForm />} />
<Route path="/admin-dat/registros/:id" element={<DATRegistroForm />} />
<Route path="/admin-dat/registros/import" element={<DATRegistroImport />} />
```

### 6.2 Menu

```javascript
// Adicionar ao menu AdminDAT existente

{
  key: 'dat-registros',
  icon: <TableOutlined />,
  label: <Link to="/admin-dat/registros">Registros DAT</Link>,
}
```

---

## 7. PERMISSÕES RBAC

### 7.1 Mapeamento

| Setor AS v2 | Permissões DAT Registros |
|-------------|--------------------------|
| **DAT** | CRUD completo, importar |
| **Superintendência** | CRUD completo, importar, excluir |
| **Controle** | Visualizar, exportar |
| **Gerência** | Visualizar, exportar |
| **Formador** | Visualizar próprios (se aplicável) |

### 7.2 Implementação Frontend (PA-06)

```javascript
// Ocultar botões baseado em permissão

const { canEdit, canDelete, canImport } = useDATPermissions();

{canEdit && <Button onClick={handleEdit}>Editar</Button>}
{canDelete && <Button danger onClick={handleDelete}>Excluir</Button>}
{canImport && <Button icon={<UploadOutlined />}>Importar</Button>}
```

---

## 8. CRONOGRAMA SUGERIDO

### Sprint 1: Backend (2-3 dias)
- [ ] Criar model `ProjetoGeral`
- [ ] Criar model `DATRegistro`
- [ ] Migration com seed data
- [ ] Serializers e ViewSet
- [ ] Testes unitários

### Sprint 2: Frontend - Lista (2-3 dias)
- [ ] Página `DATRegistrosPage.jsx`
- [ ] Componente `DATRegistroTable.jsx` com colunas agrupadas
- [ ] Componente `DATRegistroFilters.jsx`
- [ ] Service e hooks

### Sprint 3: Frontend - Formulário (2-3 dias)
- [ ] Componente `DATRegistroForm.jsx`
- [ ] Campos calculados (nr_codigos, usa_avaliar)
- [ ] Validações
- [ ] Componentes auxiliares (StatusDateField, MultiDatePicker)

### Sprint 4: Importação/Exportação (2-3 dias)
- [ ] Backend: endpoint de import
- [ ] Frontend: `DATRegistroImport.jsx`
- [ ] Template de importação
- [ ] Exportação CSV/Excel

### Sprint 5: Testes e Refinamento (1-2 dias)
- [ ] Testes E2E
- [ ] Ajustes de UX
- [ ] Documentação

**Total estimado:** 9-14 dias

---

## 9. REFERÊNCIAS

- **Prompt Original:** Especificação genérica do sistema DAT
- **Models Existentes:** `apps/core/models/workflow.py`, `organizacao.py`
- **Padrões Frontend:** `ApprovalsPage.jsx`, `PreAgendaPage.jsx`
- **RBAC:** `.claude/PLANO_RBAC_SETOR_FUNCAO.md`
- **Ant Design:** https://ant.design/components/overview

---

**Documento criado em:** 2025-12-12
**Autor:** Claude Code
**Status:** Pronto para implementação
